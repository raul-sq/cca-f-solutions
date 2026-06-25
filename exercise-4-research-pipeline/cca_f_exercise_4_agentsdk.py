"""
CCA-F · Exercise 4 (Claude Agent SDK version)
=============================================

The same multi-agent research pipeline, expressed with the CLAUDE AGENT SDK's
native primitives instead of a hand-built Task tool. This is the Domain 1
target: subagent spawning via the Agent/Task tool, allowed_tools configuration,
and coordinator-subagent orchestration with context passed explicitly.

How it maps to the exercise:
  STEP 1 - the coordinator delegates to subagents defined with AgentDefinition;
           allowed_tools includes the spawning tool ("Agent"/"Task"). Subagents
           start with a BLANK context, so the coordinator must pass everything in
           the spawn prompt (the SDK gives no implicit inheritance).
  STEP 2 - the coordinator is told to spawn multiple subagents in one step; the
           SDK runs them in parallel. SubagentStart/Stop hooks make this visible.
  STEP 3 - subagents are instructed to return findings as CLAIM / EVIDENCE /
           SOURCE / DATE; the synthesizer must preserve attribution.
  STEP 4 - a SubagentStop hook observes completions/failures; the coordinator is
           told to proceed on partial results and annotate coverage gaps. (For a
           fully deterministic timeout + partial-result injection, see the raw
           Messages API version of Exercise 4, which controls the dispatch loop.)
  STEP 5 - two conflicting sources are handed in; the synthesizer must keep BOTH
           values with attribution and split established vs contested.

Prerequisites:
  npm install -g @anthropic-ai/claude-code   (the Claude Code CLI; requires Node.js)
  pip install claude-agent-sdk               (the Python SDK; it drives the CLI above)
  Authentication: run `claude login` to use a Claude subscription (recommended for
  local use; consumption goes to your plan). Alternatively set ANTHROPIC_API_KEY,
  which takes precedence over the subscription login if both are present.
Run:
  py cca_f_exercise_4_agentsdk.py
"""

from __future__ import annotations

import asyncio

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AgentDefinition,
    HookMatcher,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

COORDINATOR_MODEL = "claude-sonnet-4-6"
SUBAGENT_MODEL = "claude-haiku-4-5-20251001"

# Two CREDIBLE but CONFLICTING sources (Step 5): same trend, different headline %.
SOURCE_A = (
    "WHO Report 2023 (2023-05): Global adoption of technology X has risen steadily "
    "since 2010. We estimate current global adoption at 4.2%."
)
SOURCE_B = (
    "OECD Brief 2023 (2023-09): Adoption of X has increased over the past decade. "
    "Our 2023 figure places global adoption at 5.1%."
)

# STEP 1 - subagents defined programmatically. Each has its OWN prompt + tools and
# starts with a blank context window.
AGENTS = {
    "web-researcher": AgentDefinition(
        description="Searches the web for evidence on a question and reports findings "
                    "with sources and dates. Use for current/online facts.",
        prompt=(
            "You are a web research subagent. Research ONLY the task handed to you. "
            "Report each finding on its own as: CLAIM / EVIDENCE / SOURCE (URL) / DATE. "
            "Never fabricate a source. If you find nothing solid, say so."
        ),
        tools=["WebSearch"],
        model=SUBAGENT_MODEL,
    ),
    "doc-analyst": AgentDefinition(
        description="Analyzes the source documents provided in its prompt and extracts "
                    "findings with attribution. Use when source text is supplied.",
        prompt=(
            "You are a document-analysis subagent. Analyze ONLY the documents given to "
            "you in the prompt - you have no other context. Extract each finding as: "
            "CLAIM / EVIDENCE / SOURCE (document name) / DATE. Do not invent anything."
        ),
        tools=[],          # reasons over the prompt text; no external tools needed
        model=SUBAGENT_MODEL,
    ),
    "synthesizer": AgentDefinition(
        description="Combines findings into a report, preserving every source and "
                    "separating well-established from contested claims.",
        prompt=(
            "You are a synthesis subagent. Combine the findings handed to you. Rules: "
            "keep EVERY source attribution; put well-corroborated, non-conflicting "
            "claims under ESTABLISHED (list supporting sources); when sources give "
            "DIFFERENT values for the same quantity, put them under CONTESTED with each "
            "value AND its source - never pick or average; end with COVERAGE GAPS for "
            "anything the research could not cover."
        ),
        tools=[],
        model=SUBAGENT_MODEL,
    ),
}

# STEP 1/2 - the coordinator may spawn subagents (Agent/Task) but does no research
# itself. Both tool names are allow-listed so the example works across SDK builds
# (current Python SDK spawns via "Agent"; "Task" is the Claude Code name).
COORDINATOR_SYSTEM = (
    "You are a research coordinator. You do NOT research directly. Delegate to "
    "subagents by spawning them, and spawn the independent research angles TOGETHER "
    "so they run in parallel. Each subagent has a blank context, so put everything it "
    "needs (the question, and for doc-analyst the full source text) into its spawn "
    "prompt. After the research subagents return, spawn the synthesizer with ALL their "
    "findings. If a subagent fails or returns nothing, proceed with what you have and "
    "tell the synthesizer which angle is missing so it becomes a coverage gap."
)

OPTIONS = ClaudeAgentOptions(
    model=COORDINATOR_MODEL,
    system_prompt=COORDINATOR_SYSTEM,
    agents=AGENTS,
    allowed_tools=["Agent", "Task", "WebSearch"],   # allow spawning + web search
    hooks={
        # Observe subagent lifecycle (Step 2 parallelism, Step 4 failure visibility).
        "SubagentStart": [HookMatcher(hooks=[lambda i, t, c: _log("SubagentStart", i)])],
        "SubagentStop": [HookMatcher(hooks=[lambda i, t, c: _log("SubagentStop", i)])],
    },
)


async def _log(event: str, input_data: dict) -> dict:
    agent = input_data.get("agent_type") or input_data.get("agent_id") or "?"
    print(f"  [{event}] {agent}")
    return {}


def _build_question() -> str:
    return (
        "Research question: What is the current global adoption rate of technology X, "
        "and is it rising?\n\n"
        "Use the web-researcher for any recent online estimate, and the doc-analyst for "
        "these two provided sources (hand each source's full text to the analyst):\n\n"
        f"[Source A] {SOURCE_A}\n\n[Source B] {SOURCE_B}\n\n"
        "Then synthesize: established vs contested, with attribution, plus coverage gaps."
    )


async def main() -> None:
    async with ClaudeSDKClient(options=OPTIONS) as client:
        print("=" * 72 + "\nCOORDINATOR allowed_tools = ['Agent','Task','WebSearch']\n" + "=" * 72)
        await client.query(_build_question())
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
                    elif type(block).__name__ == "ToolUseBlock":
                        # The Agent/Task tool call is the coordinator spawning a subagent.
                        print(f"  [SPAWN] {block.name} -> {block.input}")
            elif isinstance(msg, ResultMessage):
                pass


if __name__ == "__main__":
    asyncio.run(main())
