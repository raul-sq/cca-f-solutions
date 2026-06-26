# Soluciones a los ejercicios de preparación · CCA-F

Mis implementaciones de los cuatro ejercicios de preparación de la certificación
**Claude Certified Architect – Foundations (CCA-F)** de Anthropic. Cada ejercicio
es una implementación ejecutable, verificada contra la documentación oficial
vigente (Claude API docs y `code.claude.com/docs`).

> [!IMPORTANT]
> **Este repositorio contiene únicamente mi propio trabajo.** No reproduce los
> enunciados oficiales de los ejercicios: esos materiales son propiedad de
> Anthropic y están marcados como confidenciales (*Need to Know*). Para
> consultarlos, accede por el canal oficial — el portal de Anthropic Academy /
> Skilljar de la certificación. Aquí encontrarás, por cada ejercicio, una
> descripción de alto nivel escrita por mí de lo que aborda, más la solución.

## Los cuatro ejercicios

| # | Ejercicio | Dominios reforzados |
|---|-----------|---------------------|
| 1 | Agente multi-herramienta con lógica de escalado | D1 Arquitectura agéntica · D2 Diseño de herramientas/MCP · D5 Contexto y fiabilidad |
| 2 | Configuración de Claude Code para un flujo de equipo | D3 Configuración y flujos de Claude Code · D2 Diseño de herramientas/MCP |
| 3 | Tubería de extracción de datos estructurados | D4 Ingeniería de prompts y salida estructurada · D5 Contexto y fiabilidad |
| 4 | Tubería de investigación multiagente | D1 Arquitectura agéntica · D2 Diseño de herramientas/MCP · D5 Contexto y fiabilidad |

Una descripción más detallada de cada uno, con las decisiones técnicas, está en
[`docs/informe-unificado.txt`](docs/informe-unificado.txt).

## Estructura del repositorio

```
.
├── docs/
│   └── informe-unificado.txt            Informe único (ES) de los cuatro ejercicios
├── exercise-1-multitool-agent/          Agente + bucle agéntico + escalado (Messages API cruda)
├── exercise-2-team-workflow/            Configuración de Claude Code para equipo (CLAUDE.md, reglas, MCP)
├── exercise-3-extraction-pipeline/      Extracción estructurada + validación-reintento + lotes
├── exercise-4-research-pipeline/        Coordinador-subagentes con el Claude Agent SDK
├── casos-practicos/                     (En crecimiento) Casos prácticos propios que vayan surgiendo
└── recursos/
    └── enlaces.md                       Enlaces de referencia para la preparación
```

Cada carpeta tiene su propio `README.md` con objetivo, mapa de archivos y cómo ejecutarla.

## Requisitos generales

- **Python 3.10+**
- Dependencias por ejercicio (ver el README de cada carpeta). En general:
  `pip install anthropic` y, para el ejercicio 3, también `pydantic`.
- **Autenticación.** Los ejercicios 1 y 3 usan el SDK `anthropic` y se facturan a
  la cuenta de API (necesitan `ANTHROPIC_API_KEY` en el entorno). El **ejercicio
  4** usa el Claude Agent SDK y se autentica preferentemente con `claude login`
  (suscripción Max/Pro); `ANTHROPIC_API_KEY` es la alternativa y, si está
  definida, tiene prioridad sobre el login de suscripción.
- El **ejercicio 4** requiere además **Node.js** y la CLI de Claude Code
  (`npm install -g @anthropic-ai/claude-code`), que el SDK de Python necesita por
  debajo (no la incluye; a diferencia del SDK de TypeScript).

> Las credenciales nunca están en el código: los ejemplos leen la clave o el login
> del entorno. Copia el `.env.example` correspondiente a `.env` (ignorado por git)
> y rellena tus valores.

## Notas

- El código y los identificadores técnicos están en inglés; la documentación y el
  informe, en español.
- Material de referencia oficial: documentación de la
  [Claude API](https://docs.anthropic.com) y de
  [Claude Code](https://code.claude.com/docs), y la
  [especificación de MCP](https://modelcontextprotocol.io).
