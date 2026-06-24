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

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # PowerShell: $env:ANTHROPIC_API_KEY="..."

python run_demo.py                  # barato: extracción de un solo doc sobre 3 muestras (Pasos 1,2,3,5)
python run_demo.py --batch          # construye los payloads del lote de 100 SIN enviarlos
python run_demo.py --batch --submit # envía el lote real (Paso 4; cuesta dinero, asíncrono)
```
