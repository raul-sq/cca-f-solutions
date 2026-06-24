# Ejercicio 2 · Claude Code para un flujo de trabajo de equipo

Configuración completa de un proyecto para que **Claude Code** se comporte de
forma consistente entre todos los miembros de un equipo: estándares universales,
reglas por área de código, una skill aislada, y servidores MCP de equipo y
personales conviviendo a la vez.

**Dominios:** D3 (configuración y flujos de trabajo de Claude Code) ·
D2 (diseño de herramientas e integración MCP).

## Mapa de archivos

```
team-workflow/
├── CLAUDE.md                              Estándares universales del proyecto (se cargan siempre)
├── .claude/
│   ├── rules/
│   │   ├── api-conventions.md             Regla con glob paths: ["src/api/**/*"]
│   │   └── testing-conventions.md         Regla con glob paths: ["**/*.test.*"]
│   ├── skills/
│   │   └── coverage-audit/SKILL.md        Skill con context: fork y allowed-tools restringidos
│   └── commands/
│       └── review.md                      Slash command personalizado
├── .mcp.json                             Servidores MCP de equipo (con expansión de ${VAR})
├── .env.example                          Variables que alimentan .mcp.json (copiar a .env)
└── user-scope-mcp.sample.json            Ejemplo de MCP personal en ~/.claude.json
```

## Qué demuestra

- Jerarquía de `CLAUDE.md`: instrucciones de proyecto aplicadas a todo el equipo.
- Reglas en `.claude/rules/` con *frontmatter* YAML y patrones glob que solo
  cargan al editar archivos coincidentes.
- Skill de proyecto con `context: fork` que se ejecuta aislada sin contaminar el
  contexto principal.
- `.mcp.json` con expansión de variables de entorno para credenciales, más un
  MCP personal/experimental en `~/.claude.json`, ambos disponibles a la vez.
- Discusión de *plan mode* vs. ejecución directa según la complejidad de la tarea.

## Cómo usarlo

Es configuración, no un script. Para probarla, copia el contenido de
`team-workflow/` a la raíz de un proyecto, define las variables del `.env`
(a partir de `.env.example`) y lanza `claude` en esa carpeta. Los detalles paso
a paso están en [`docs/informe-unificado.txt`](../docs/informe-unificado.txt).

> El `.env.example` contiene solo marcadores de posición. Nunca subas el `.env`
> real (ya está en `.gitignore`).
