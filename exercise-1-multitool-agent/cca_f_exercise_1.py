"""
CCA-F - Exercise 1: Multi-Tool Agent with Escalation Logic
==========================================================

Domains reinforced:
  - Domain 1: Agentic Architecture & Orchestration -> the loop that inspects stop_reason
  - Domain 2: Tool Design & MCP Integration         -> TOOLS + carefully differentiated descriptions
  - Domain 5: Context Management & Reliability        -> structured errors + retries + hook

Prerequisites:
  - ANTHROPIC_API_KEY environment variable already set.
  - pip install anthropic

To run it:
  python cca_f_exercise_1.py

File map (each step of the exercise is tagged with a "# STEP n" comment):
  STEP 1 -> definition of 3-4 tools, two of them deliberately similar
  STEP 2 -> agentic loop that distinguishes stop_reason "tool_use" vs "end_turn"
  STEP 3 -> structured errors (errorCategory / isRetryable / description) + retries
  STEP 4 -> programmatic hook that intercepts the call and redirects to the escalation flow
  STEP 5 -> multi-concern message to verify decomposition and synthesis
"""

import json
import time

import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

MODEL = "claude-sonnet-4-6"   # Sonnet is more than enough and cheap; you can drop to "claude-haiku-4-5-20251001"
THRESHOLD = 500.0             # business threshold: above this we do NOT execute, we escalate


# =====================================================================
# Simulated backend (would be a real database in an actual system)
# =====================================================================

ORDERS = {
    "A-1001": {"status": "delivered",  "total": 50.0,  "refundable": True,  "age_days": 5},
    "A-2002": {"status": "in_transit", "total": 120.0, "refundable": False, "age_days": 1},
    "A-3003": {"status": "delivered",  "total": 800.0, "refundable": True,  "age_days": 10},
}

# To VISIBLY demonstrate the retry of transient errors:
# the first status lookup for each order "fails" (simulated timeout) and the second succeeds.
_flaky_attempts = {}


def _ok(data):
    return {"ok": True, "data": data}


def _err(category, retryable, description):
    """Homogeneous error structure for ALL tools (STEP 3)."""
    return {
        "ok": False,
        "error": {
            "errorCategory": category,    # "transient" | "validation" | "permission"
            "isRetryable": retryable,     # bool
            "description": description,    # human-readable / for the model to explain
        },
    }


# =====================================================================
# STEP 1 - Tool definitions
# ---------------------------------------------------------------------
# Four tools. issue_refund and issue_store_credit are near-twins on
# purpose: the only way for the model to choose correctly is a carefully
# written boundary description. That is the "selection confusion" exercise.
# =====================================================================

TOOLS = [
    {
        "name": "get_order_status",
        "description": (
            "READ-ONLY lookup. Returns the shipping status of an order given its order_id "
            "(e.g. 'delivered', 'in_transit'). It does not modify anything nor move money. "
            "Use it when the customer only asks where their order is or what state it is in. "
            "Do NOT use it for refunds or anything that alters the order."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order identifier, format 'A-NNNN'."}
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "issue_refund",
        "description": (
            "Returns money to the customer's ORIGINAL PAYMENT METHOD (their card). The money LEAVES "
            "the store. Use it ONLY when the customer explicitly asks for the money back on their "
            "card/account. Requires the order to be refundable. "
            "If the customer accepts store credit/voucher instead of money, use issue_store_credit, "
            "NOT this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order being refunded."},
                "amount": {"type": "number", "description": "Amount in euros to return to the card."},
            },
            "required": ["order_id", "amount"],
        },
    },
    {
        "name": "issue_store_credit",
        "description": (
            "Credits INTERNAL BALANCE (voucher/wallet) to the customer's account. The money does NOT "
            "leave the store: it stays as credit for future purchases. Use it when the customer accepts "
            "a voucher instead of money, or as a goodwill gesture (compensation, apology). "
            "If the customer demands the money back on their card, that is issue_refund, NOT this one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order associated with the credit."},
                "amount": {"type": "number", "description": "Amount in euros to credit as internal balance."},
            },
            "required": ["order_id", "amount"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Opens a ticket for a human agent. Use it only when an operation cannot be resolved "
            "automatically and requires approval or manual intervention."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for the escalation."},
                "order_id": {"type": "string", "description": "Order involved, if applicable."},
            },
            "required": ["reason"],
        },
    },
]


# =====================================================================
# Actual implementation of each tool (they return the STEP 3 structure)
# =====================================================================

def tool_get_order_status(order_id):
    # TRANSIENT error simulation: the first attempt for each order "fails" with a timeout.
    attempts = _flaky_attempts.get(order_id, 0) + 1
    _flaky_attempts[order_id] = attempts
    if attempts == 1:
        return _err("transient", True, "Temporary timeout while querying the orders service.")

    order = ORDERS.get(order_id)
    if not order:
        return _err("validation", False, f"No order exists with id '{order_id}'.")
    return _ok({"order_id": order_id, "status": order["status"]})


def _do_money_op(order_id, amount, kind):
    order = ORDERS.get(order_id)
    if not order:
        return _err("validation", False, f"No order exists with id '{order_id}'.")
    if amount <= 0:
        return _err("validation", False, "The amount must be greater than zero.")
    # Business rule: only issue_refund requires refundability; internal credit is more flexible.
    if kind == "refund" and not order["refundable"]:
        return _err("permission", False,
                    f"Order '{order_id}' is not eligible for a refund to card.")
    if amount > order["total"]:
        return _err("validation", False,
                    f"The amount ({amount} EUR) exceeds the order total ({order['total']} EUR).")
    return _ok({"order_id": order_id, "amount": amount, "method": kind, "result": "completed"})


def tool_issue_refund(order_id, amount):
    return _do_money_op(order_id, amount, "refund")


def tool_issue_store_credit(order_id, amount):
    return _do_money_op(order_id, amount, "store_credit")


def tool_escalate_to_human(reason, order_id=None):
    ticket = f"TICKET-{abs(hash((reason, order_id))) % 10000:04d}"
    return _ok({"ticket_id": ticket, "status": "open", "reason": reason, "order_id": order_id})


TOOL_FUNCS = {
    "get_order_status": tool_get_order_status,
    "issue_refund": tool_issue_refund,
    "issue_store_credit": tool_issue_store_credit,
    "escalate_to_human": tool_escalate_to_human,
}


# =====================================================================
# STEP 4 - Programmatic hook that intercepts the call BEFORE executing it
# ---------------------------------------------------------------------
# If a money operation exceeds the threshold, it is NOT executed: a ticket
# is opened and an "escalation" result is returned so the model can explain
# it to the customer. This is the business safety net.
# =====================================================================

def enforce_business_rules(name, tool_input):
    """Return a result dict if the call must be blocked/escalated, or None if it may proceed."""
    if name in ("issue_refund", "issue_store_credit"):
        amount = tool_input.get("amount", 0) or 0
        if amount > THRESHOLD:
            order_id = tool_input.get("order_id")
            print(f"  [HOOK] Blocked {name}({order_id}, {amount} EUR): exceeds the {THRESHOLD} EUR threshold.")
            ticket = tool_escalate_to_human(
                reason=f"Operation {name} of {amount} EUR exceeds the automatic approval threshold.",
                order_id=order_id,
            )["data"]
            print(f"  [ESCALATION] Ticket {ticket['ticket_id']} opened for human review.")
            return {
                "ok": False,
                "escalated": True,
                "error": {
                    "errorCategory": "permission",
                    "isRetryable": False,
                    "description": (
                        f"The {amount} EUR operation exceeds the automatic approval limit "
                        f"({THRESHOLD} EUR). Ticket {ticket['ticket_id']} has been opened so a "
                        f"human agent can review it. No money has been moved."
                    ),
                },
            }
    return None


# =====================================================================
# STEP 3 (continued) - Executor with retry of transient errors
# ---------------------------------------------------------------------
# Transient errors (isRetryable=True) are retried here, transparently to the
# model. Validation/permission errors are returned as-is so the agent can
# explain them to the user.
# =====================================================================

def execute_tool(name, tool_input, max_retries=2):
    # The hook has priority: it can veto the execution.
    blocked = enforce_business_rules(name, tool_input)
    if blocked is not None:
        return blocked

    fn = TOOL_FUNCS[name]
    attempt = 0
    while True:
        result = fn(**tool_input)
        if result.get("ok"):
            return result
        err = result["error"]
        if err["isRetryable"] and err["errorCategory"] == "transient" and attempt < max_retries:
            attempt += 1
            print(f"  [RETRY] {name} returned a transient error; retry {attempt}/{max_retries}...")
            time.sleep(0.4)
            continue
        return result  # non-recoverable error: hand it to the model so it can explain it


# =====================================================================
# STEP 2 - Agentic loop that inspects stop_reason
# ---------------------------------------------------------------------
# The heart of the exercise. While stop_reason is "tool_use", we execute the
# tools and return the tool_result blocks. When it is "end_turn", we print the
# final response and exit.
# =====================================================================

SYSTEM_PROMPT = (
    "You are a customer-support agent for an online store. Resolve each request using the available "
    "tools. If a message contains several distinct requests, decompose it, handle each one separately, "
    "and at the end deliver a unified, clear response. Carefully distinguish between returning money to "
    "the card (issue_refund) and crediting internal balance (issue_store_credit): use each one according "
    "to what the customer asks for. If an operation is escalated to a human, explain it to the customer "
    "with the ticket number and make it clear that no money has been moved."
)


def run_agent(user_message, max_iterations=8):
    print("\n" + "=" * 70)
    print("USER:", user_message)
    print("=" * 70)

    messages = [{"role": "user", "content": user_message}]

    for i in range(max_iterations):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        print(f"\n[LOOP iter {i}] stop_reason = {resp.stop_reason}")

        if resp.stop_reason == "tool_use":
            # Save the assistant turn (it may contain text + several tool_use blocks).
            messages.append({"role": "assistant", "content": resp.content})

            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    print(f"  [TOOL] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                    result = execute_tool(block.name, block.input)
                    print(f"  [RESULT] {json.dumps(result, ensure_ascii=False)}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

            messages.append({"role": "user", "content": tool_results})
            continue  # call the model again with the results

        elif resp.stop_reason == "end_turn":
            final_text = "".join(b.text for b in resp.content if b.type == "text")
            print("\nAGENT (final response):\n" + final_text)
            return final_text

        else:
            # Other possible stop_reason values (max_tokens, etc.): treat them as end defensively.
            print(f"\n[WARNING] Unexpected stop_reason: {resp.stop_reason}. Ending the loop.")
            return None

    print("\n[WARNING] Reached the maximum number of iterations without end_turn.")
    return None


# =====================================================================
# STEP 5 - Tests
# ---------------------------------------------------------------------
# The second message is multi-concern: three requests in one. One of them
# (800 EUR) triggers the hook and is escalated. Check in the trace that the
# agent decomposes them, handles each one, and delivers a unified synthesis.
# =====================================================================

if __name__ == "__main__":
    # Simple case: status lookup (you will see the retry of the transient error).
    run_agent("What is the status of my order A-1001?")

    # Multi-concern case with escalation:
    run_agent(
        "I have three things: 1) order A-1001 arrived damaged, I want the 50 EUR back on my card; "
        "2) tell me the status of order A-2002; and 3) for order A-3003 I want a 800 EUR refund to "
        "my card."
    )

    # Permission business error: A-2002 is not refundable, so the refund is rejected
    # (non-retryable) and the agent must explain the business reason to the customer.
    run_agent("I want a 60 EUR refund to my card for order A-2002.")

    # Taking a store voucher instead of money: this is a near-twin of the previous case, but the model must choose the correct tool.
    run_agent("I'll take a store voucher for 30 EUR on order A-1001 instead.")
