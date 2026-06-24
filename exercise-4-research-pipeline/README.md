# Ejercicio 4 · Tubería de investigación multiagente

Un coordinador que delega en subagentes (investigación web y análisis de
documentos) y un sintetizador que preserva la atribución de fuentes, expresado
con los primitivos nativos del **Claude Agent SDK** (`AgentDefinition`,
`allowed_tools`, *hooks* de ciclo de vida de subagentes).

> Se elige la implementación con el Agent SDK porque el ejercicio usa
> vocabulario nativo del SDK (subagentes, `Task`/`Agent`, `allowed_tools`). El
> docstring del archivo apunta también a una variante con la Messages API cruda
> para un control determinista del *timeout* y los resultados parciales.

**Dominios:** D1 (arquitectura agéntica y orquestación) ·
D2 (diseño de herramientas e integración MCP) · D5 (gestión de contexto y fiabilidad).

## Qué demuestra

- Coordinador con `allowed_tools` que incluye la herramienta de *spawn*
  (`Agent`/`Task`); cada subagente arranca con **contexto en blanco**, así que el
  coordinador le pasa todo lo necesario en el prompt de spawn (sin herencia
  implícita).
- Ejecución en **paralelo**: el coordinador lanza varios subagentes en un mismo
  paso; los *hooks* `SubagentStart`/`SubagentStop` lo hacen visible.
- Salida estructurada de subagentes (`CLAIM / EVIDENCE / SOURCE / DATE`) que el
  sintetizador conserva con atribución.
- Propagación de errores: ante un subagente que falla o no devuelve nada, el
  coordinador continúa con resultados parciales y anota las lagunas de cobertura.
- Dos fuentes creíbles pero **en conflicto**: el sintetizador mantiene ambos
  valores con su fuente (sin elegir ni promediar) y separa lo *establecido* de lo
  *contestado*.

## Cómo ejecutarlo

```bash
pip install claude-agent-sdk        # incluye la CLI de Claude Code; requiere Node.js
export ANTHROPIC_API_KEY=...        # PowerShell: $env:ANTHROPIC_API_KEY="..."
python cca_f_exercise_4_agentsdk.py
```
