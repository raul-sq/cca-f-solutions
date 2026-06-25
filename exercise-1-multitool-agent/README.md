# Ejercicio 1 · Agente multi-herramienta con lógica de escalado

Un bucle agéntico sobre la **Messages API cruda** que inspecciona `stop_reason`
para decidir entre seguir ejecutando herramientas o entregar la respuesta final,
con manejo de errores estructurado, reintentos y un *hook* que impone una regla
de negocio (escalado por encima de un umbral).

> Se usa la Messages API directamente (en lugar del Agent SDK) **a propósito**:
> el ejercicio gira en torno al manejo de `stop_reason`, que el SDK abstrae.

**Dominios:** D1 (arquitectura agéntica y orquestación) · D2 (diseño de
herramientas e integración MCP) · D5 (gestión de contexto y fiabilidad).

## Qué demuestra

- 3-4 herramientas con descripciones cuidadosamente diferenciadas (incluidas dos
  similares, para evitar confusión de selección).
- Bucle que distingue `stop_reason` `"tool_use"` de `"end_turn"`.
- Errores estructurados (`errorCategory` transient/validation/permission,
  `isRetryable`, descripción legible) y reintentos solo de lo reintentable.
- *Hook* programático que intercepta la llamada y redirige al flujo de escalado.
- Mensaje con varias preocupaciones: descomposición, manejo y síntesis unificada.

## Cómo ejecutarlo

Usa el SDK de Python `anthropic` sobre la Messages API, así que el consumo se
factura a la **cuenta de API** (necesita `ANTHROPIC_API_KEY` en el entorno). El
gasto es mínimo: son unas pocas llamadas cortas.

```powershell
py -m pip install anthropic
$env:ANTHROPIC_API_KEY = "sk-ant-..."
py cca_f_exercise_1.py
```

Cada paso del enunciado está etiquetado en el código con un comentario `# STEP n`.

## Verificación en local

Verificado en Windows (PowerShell). Una sola ejecución demuestra los cinco pasos:

- **Bucle con `stop_reason` (Paso 2):** cada turno alterna `iter 0` con
  `stop_reason = tool_use` (ejecuta herramientas) e `iter 1` con `end_turn`
  (entrega la respuesta final).
- **Errores estructurados y reintento selectivo (Paso 3):** un error *transient*
  en `get_order_status` se reintenta automáticamente (`retry 1/2`) hasta
  resolverse; un error *permission* con `isRetryable: false` (reembolso no
  elegible) **no** se reintenta — se explica al usuario y se ofrecen alternativas.
- **Hook de regla de negocio + escalado (Paso 4):** un reembolso de 800 € se
  intercepta antes de ejecutarse por superar el umbral de 500 €, abre un ticket
  de revisión humana y devuelve un error estructurado confirmando que *no se ha
  movido dinero*.
- **Mensaje multi-preocupación (Paso 5):** una petición con tres asuntos se
  resuelve en una sola pasada, emitiendo las tres llamadas a herramienta y
  sintetizando una respuesta unificada que trata cada asunto por separado
  (procesado / en tránsito / escalado).
- **Selección entre herramientas similares (Paso 1):** cuando el reembolso a
  tarjeta no es elegible, el agente cambia correctamente a `issue_store_credit`
  para emitir un vale, distinguiendo entre las dos herramientas parecidas.
