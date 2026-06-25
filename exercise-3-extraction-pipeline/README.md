# Ejercicio 3 · Tubería de extracción de datos estructurados

Extracción de campos estructurados desde documentos no estructurados usando
`tool_use`, con un esquema JSON cuidadoso, un bucle de validación-reintento con
Pydantic, ejemplos *few-shot*, procesamiento por lotes y enrutamiento a revisión
humana por confianza.

**Dominios:** D4 (ingeniería de prompts y salida estructurada) ·
D5 (gestión de contexto y fiabilidad).

## Mapa de archivos

```
extraction_pipeline/
├── run_demo.py                 Punto de entrada de extremo a extremo
├── requirements.txt            anthropic, pydantic
└── extraction/
    ├── schema.py               Esquema JSON: requeridos/opcionales, enum con "other"+detalle, campos nullable
    ├── extract.py              Llamada con tool_use + bucle de validación-reintento
    ├── fewshot.py              Ejemplos few-shot para variedad estructural
    ├── documents.py            Documentos de muestra + datos "gold" para evaluar
    ├── batch.py                Estrategia de lotes (Message Batches API) por custom_id
    └── analysis.py             Precisión por tipo/campo + resumen de enrutamiento
```

## Qué demuestra

- Esquema con campos requeridos y opcionales, un enum con patrón
  `"other"` + cadena de detalle, y campos *nullable*: el modelo devuelve `null`
  en vez de inventar cuando la información no está en el documento.
- Bucle de validación-reintento: ante un fallo de validación, se reenvía el
  documento, la extracción fallida y el error concreto; se distingue lo
  resoluble por reintento (formato) de lo no resoluble (información ausente).
- *Few-shot* con formatos variados (citas en línea vs. bibliografías, narrativa
  vs. tablas) para mejorar el manejo de la variedad estructural.
- Lotes de ~100 documentos con manejo de fallos por `custom_id`, reenvío de los
  fallidos (p. ej. troceando los grandes) y cálculo de tiempo frente a la SLA.
- Puntuaciones de confianza por campo y enrutamiento de las extracciones de baja
  confianza a revisión humana, con análisis de precisión por tipo de documento.

## Cómo ejecutarlo

A diferencia del ejercicio 4 (que se autentica con la suscripción vía Claude
Code), este usa el SDK de Python `anthropic` directamente y la **Message Batches
API**, así que el consumo se factura a la **cuenta de API**, no al plan Max. Por
tanto necesita una `ANTHROPIC_API_KEY` definida en el entorno.

```powershell
py -m pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # se factura a la cuenta de API (no a Max)

py run_demo.py                  # barato: extracción real sobre 3 documentos de muestra (Pasos 1,2,3,5)
py run_demo.py --batch          # GRATIS: construye los payloads del lote de 100 SIN enviarlos (dry run)
py run_demo.py --batch --submit # envía el lote real a la API (Paso 4; se factura y es asíncrono)
```

Sobre los tres modos: el básico hace extracciones reales pero solo sobre tres
documentos. `--batch` se queda en *dry run* — arma el lote completo (asignación de
`custom_id`, detección de documentos sobredimensionados para trocear) sin llamar a
la API, así que no cuesta nada. `--batch --submit` es el único que rompe esa
barrera: hace un `POST` real a `https://api.anthropic.com/v1/messages/batches`,
con lo que los 100 documentos se procesan en la infraestructura de Anthropic de
forma **asíncrona** (resultados dentro de una ventana de hasta 24 h, normalmente
mucho antes) y con **descuento del 50 %** sobre el precio estándar, facturado a tu
cuenta de API. Para ejecutarlo y demostrar el Paso 4 no hace falta el `--submit`:
toda la *lógica* de la estrategia de lotes se observa ya en el *dry run*.

## Verificación en local

Verificado en Windows (PowerShell), con estos resultados:

- **Modo básico:** los tres documentos se extrajeron a la primera (`attempts=1`,
  sin reintento). Los campos ausentes salieron `null` en vez de fabricarse (Paso
  1); el tipo fuera del enum cayó en `other` con su `detail` (Paso 1); el bucle de
  validación no necesitó corrección (Paso 2); el *few-shot* manejó los tres
  formatos dispares sin fallos (Paso 3); el enrutamiento auto-aceptó los tres
  (`review_rate 0.0`) con precisión del 100 % por campo y por tipo (Paso 5).
- **`--batch` (dry run):** construyó el lote de 100 e identificó el documento
  sobredimensionado (`oversized_docs`) para troceado, sin llamar a la API (Paso 4,
  parte de estrategia).
- **`--submit`:** no ejecutado a propósito. No aporta nada conceptualmente nuevo
  sobre lo ya demostrado, y evita el gasto y la espera del ciclo asíncrono real.
