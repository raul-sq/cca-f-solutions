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

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...        # en PowerShell: $env:ANTHROPIC_API_KEY="..."
python cca_f_exercise_1.py
```

Cada paso del enunciado está etiquetado en el código con un comentario `# STEP n`.
