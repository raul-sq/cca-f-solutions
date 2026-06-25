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
  *en disputa*.

## Cómo ejecutarlo

Requiere **Node.js 18+** y la CLI de Claude Code, que el SDK de Python necesita
por debajo:

```powershell
npm install -g @anthropic-ai/claude-code   # la CLI (requiere Node.js)
py -m pip install claude-agent-sdk
claude login                               # iniciar sesión con la suscripción (Max/Pro)
py cca_f_exercise_4_agentsdk.py
```

La autenticación recomendada para uso local es el `claude login` con tu cuenta de
suscripción: así el consumo sale de tu plan. Si `ANTHROPIC_API_KEY` está definida
en el entorno, tiene prioridad sobre el login de suscripción, así que para usar el
plan conviene que no esté puesta (`$env:ANTHROPIC_API_KEY = $null` en esa sesión
de PowerShell). De forma alternativa, exportar `ANTHROPIC_API_KEY` factura el
consumo a la cuenta de API.

> Verificado en local (Windows, PowerShell): los cinco pasos del ejercicio se
> demuestran en una sola ejecución — *spawn* en paralelo, contexto pasado
> explícitamente, atribución por fuente, propagación del subagente sin datos como
> laguna de cobertura, y las dos cifras en conflicto (WHO 4,2 % / OECD 5,1 %)
> mantenidas ambas bajo *en disputa*, sin elegir ni promediar.

Ejecutado varias veces con resultados consistentes: como el modelo no es
determinista, la redacción del informe varía entre ejecuciones, pero la estructura de
fondo se mantiene estable — las dos cifras divergentes siempre acaban bajo
*en disputa* (nunca promediadas ni descartadas) y la afirmación cualitativa
compartida (la tendencia al alza) bajo *establecido*. Esa estabilidad de la
separación establecido/disputado pese a la variación de redacción es justo la
señal de robustez que el Paso 5 busca.
