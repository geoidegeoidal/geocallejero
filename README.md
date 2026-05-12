# GeoCallejero — Geocodificador Chileno de Direcciones para QGIS

![QGIS Plugin](https://img.shields.io/badge/QGIS-3.34%20%7C%203.40%20%7C%204.x-green?logo=qgis)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-GPL--3.0-yellow)
![Status](https://img.shields.io/badge/Status-Experimental-orange)
![Tests](https://img.shields.io/badge/Tests-23%2F23%20passing-brightgreen)

**Plugin de QGIS para geocodificación masiva de direcciones chilenas con estrategia híbrida de 3 niveles, normalizador NLP y cero dependencias externas.**

---

## Tabla de Contenidos

- [Características](#características)
- [Estrategia de Geocodificación](#estrategia-de-geocodificación)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Arquitectura](#arquitectura)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Desarrollo](#desarrollo)
- [Roadmap](#roadmap)
- [Créditos](#créditos)
- [Licencia](#licencia)

---

## Características

- **Normalizador NLP ligero** — Convierte `"Pje. Los Ángeles N° 1234, Iquique"` en `{tipo_via: "PASAJE", nombre: "LOS ANGELES", numero: 1234, comuna: "IQUIQUE"}` automáticamente.
- **Geocodificación híbrida de 3 niveles** — Cada dirección se resuelve por la fuente más precisa disponible.
- **Caché GPKG inteligente** — Convierte archivos OSM PBF (~323 MB) en un GPKG ligero (~50 MB) con verificación SHA256.
- **Interpolación lineal por paridad** — Usa los campos `INI_IZQ`, `INI_DER`, `TER_IZQ`, `TER_DER` del Maestro de Calles del INE.
- **Índice espacial en memoria** — `QgsSpatialIndex` para consultas O(√n) sin depender de PostGIS.
- **Background processing** — `QgsTask` + `subprocess` para no bloquear la UI de QGIS.
- **Cero dependencias externas** — 100% sobre la API nativa de QGIS: `QgsVectorLayer`, `QgsSpatialIndex`, GDAL/`ogr2ogr`, `QgsTask`.
- **Score de confianza por resultado** — Cada match incluye `gc_source` (maestro_exacto, osm_exacto, maestro_centroide) y score numérico.
- **Soporte para inputs sucios** — CSV, XLSX, columnas separadas o direcciones en texto libre.
- **Multiplataforma** — Windows, Linux, macOS.

---

## Estrategia de Geocodificación

```
┌─────────────────────────────────────────────────────┐
│              DIRECCIÓN DE ENTRADA                    │
│   "Av. Arturo Prat N° 1234, Iquique"                │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│         1. NORMALIZADOR NLP (address_parser)         │
│  tipo_via: AVENIDA | nombre: ARTURO PRAT | num: 1234│
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │   NIVEL 1: MAESTRO     │
         │   Interpolación Lineal │
         │   por paridad (29.6%)  │
         └───────────┬────────────┘
                     │ ¿match exacto?
                     ▼
         ┌────────────────────────┐
         │   NIVEL 2: OSM PBF     │
         │   addr:housenumber     │
         │   (caché GPKG + índice)│
         └───────────┬────────────┘
                     │ ¿match exacto?
                     ▼
         ┌────────────────────────┐
         │   NIVEL 3: FALLBACK    │
         │   Centroide de calle   │
         │   (Maestro de Calles)  │
         └────────────────────────┘
```

### Fuentes de Datos

| Fuente | Formato | Contenido | Precisión |
|--------|---------|-----------|-----------|
| **Maestro de Calles 2022 (INE)** | SHP | Ejes viales con numeración INI_IZQ, TER_IZQ, INI_DER, TER_DER | Alta (interpolación) |
| **OpenStreetMap PBF** | PBF | Puntos con `addr:housenumber`, líneas con `addr:interpolation` | Muy Alta (exacto GPS) |
| **Fallback Centroide** | — | Centroide del eje de calle cuando no hay numeración | Baja (referencial) |

---

## Requisitos

| Componente | Versión | Notas |
|-----------|---------|-------|
| **QGIS** | ≥ 3.34 LTR | Compatible con 4.x |
| **Python** | ≥ 3.9 | Incluido en QGIS |
| **GDAL** | ≥ 3.8 | Incluido en QGIS (`ogr2ogr`) |
| **Maestro de Calles 2022** | — | Shapefile del INE (NO incluido en el plugin) |
| **OSM PBF** | — | Descargable de Geofabrik o BBBike (NO incluido) |

> El plugin **no requiere instalar dependencias adicionales**. Todo corre sobre la instalación estándar de QGIS.

---

## Instalación

### Desde QGIS Plugin Manager (próximamente)

1. Abre QGIS
2. Ve a `Complementos > Administrar e instalar complementos`
3. Busca **GeoCallejero**
4. Haz clic en **Instalar**

### Instalación Manual (desarrollo)

```bash
# Clonar el repositorio
git clone https://github.com/geoidegeoidal/geocallejero.git

# Copiar a la carpeta de plugins de QGIS
# Windows
cp -r geocallejero/geocallejero "%APPDATA%/QGIS/QGIS3/profiles/default/python/plugins/geocallejero"

# Linux
cp -r geocallejero/geocallejero ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/geocallejero

# macOS
cp -r geocallejero/geocallejero ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/geocallejero
```

### Preparar datos

1. **Maestro de Calles**: Descarga el shapefile del INE (Maestro de Calles 2022) y colócalo en una carpeta conocida.
2. **OSM PBF**: Descarga el archivo `.osm.pbf` de tu región de interés desde [Geofabrik](https://download.geofabrik.de/south-america/chile.html) o [BBBike](https://extract.bbbike.org/).

---

## Uso

### 1. Abrir el plugin

Desde QGIS: `Complementos > GeoCallejero > GeoCallejero`

### 2. Wizard de 3 pasos

| Paso | Acción |
|------|--------|
| **Paso 1: Datos** | Carga tu archivo CSV/XLSX con direcciones. Mapea columnas (dirección, comuna). |
| **Paso 2: Fuentes** | Selecciona el shapefile del Maestro de Calles y/o el archivo OSM PBF. |
| **Paso 3: Ejecutar** | Haz clic en **Geocodificar**. El progreso se muestra en tiempo real. |

### 3. Resultado

Se genera una capa vectorial en memoria con los campos:

| Campo | Descripción |
|-------|-------------|
| `gc_tipo_via` | Tipo de vía normalizado (AVENIDA, CALLE, PASAJE, etc.) |
| `gc_nombre` | Nombre de la calle normalizado |
| `gc_numero` | Número domiciliario extraído |
| `gc_comuna` | Comuna normalizada |
| `gc_source` | Fuente del match: `maestro_exacto`, `osm_exacto`, `maestro_centroide` |
| `gc_score` | Score de confianza (0.0 — 1.0) |
| `gc_lat` / `gc_lon` | Coordenadas del punto geocodificado |

---

## Arquitectura

```
┌──────────────────────────────────────────────────┐
│                  UI (Qt/PyQt)                     │
│  main_dialog.py  │  wizard  │  progress           │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────┐
│                    CORE                            │
│  address_parser.py  │  matcher.py                  │
│  street_index.py    │  interpolator.py             │
│  osm_provider.py    │  geocoder.py (QgsTask)       │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────┐
│                    I/O                             │
│  CSV/XLSX Reader  │  Layer Writer                  │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────┐
│                    UTILS                           │
│  constants.py  │  text_utils.py                    │
└──────────────────────────────────────────────────┘
```

**Principios de diseño**:
- **Clean Architecture**: UI desacoplada del Core lógico.
- **Lazy loading**: El Maestro de Calles y el índice OSM se cargan una sola vez al iniciar la geocodificación.
- **Inmutabilidad**: Los resultados son diccionarios inmutables. No hay side effects en el parser.
- **Fail-fast**: Validación temprana de archivos de entrada, tipos de datos y compatibilidad de CRS.

---

## Estructura del Proyecto

```
geocallejero/
├── metadata.txt              # Metadatos del plugin QGIS
├── icon.png                  # Ícono del plugin (128x128)
├── __init__.py               # Entry point: classFactory()
├── plugin.py                 # Orquestador principal
│
├── core/
│   ├── __init__.py
│   ├── address_parser.py     # [FASE 1 ✓] Parser NLP de direcciones chilenas
│   ├── osm_provider.py       # [FASE 2 ✓] Provider OSM + caché GPKG + índice espacial
│   ├── street_index.py       # [FASE 3] Índice del Maestro de Calles
│   ├── interpolator.py       # [FASE 3] Interpolación lineal por paridad
│   ├── matcher.py            # [FASE 3] Motor de matching 3 niveles
│   └── geocoder.py           # [FASE 4] QgsTask worker orquestador
│
├── io/
│   ├── __init__.py           # [FASE 4]
│   ├── reader.py             # [FASE 4] Lector de CSV/XLSX
│   └── writer.py             # [FASE 4] Escritor de layers
│
├── ui/
│   ├── __init__.py           # [FASE 4]
│   └── main_dialog.py        # [FASE 4] Wizard Qt de 3 pasos
│
├── utils/
│   ├── __init__.py
│   ├── constants.py          # [FASE 1 ✓] Tipos de vía, regex
│   └── text_utils.py         # [FASE 1 ✓] Normalización de texto
│
└── tests/
    ├── __init__.py
    ├── test_parser.py        # [FASE 1 ✓] Tests del parser NLP
    └── test_osm_provider.py  # [FASE 2 ✓] Tests del provider OSM
```

---

## Desarrollo

### Clonar y configurar

```bash
git clone https://github.com/geoidegeoidal/geocallejero.git
cd geocallejero
```

### Ejecutar tests

```bash
# Todos los tests
python -m pytest geocallejero/tests/ -v

# Solo tests de parser
python -m pytest geocallejero/tests/test_parser.py -v

# Solo tests de OSM provider
python -m pytest geocallejero/tests/test_osm_provider.py -v
```

### Estilo de código

- Python 3.9+, type hints en funciones públicas
- Docstrings y comentarios en español
- PEP 8 con 88 caracteres por línea
- Arquitectura limpia: sin lógica de UI en `core/`

---

## Roadmap

| Fase | Componente | Estado |
|------|-----------|--------|
| **Fase 1** | Core de Normalización y Parser NLP | ✅ Completado |
| **Fase 2** | Provider OSM y Caché GPKG | ✅ Completado |
| **Fase 3** | Motor de Matching, Índices e Interpolación Lineal | 🔨 En progreso |
| **Fase 4** | UI Premium (Wizard) y Orquestador QgsTask | ⏳ Pendiente |

---

## Créditos

- **Autor**: GeoIdeoGeoidal
- **Email**: geoidegeoidal@gmail.com
- **Repositorio**: [github.com/geoidegeoidal/geocallejero](https://github.com/geoidegeoidal/geocallejero)
- **Datos INE**: Maestro de Calles 2022 — Instituto Nacional de Estadísticas de Chile
- **Datos OSM**: © Colaboradores de OpenStreetMap (ODbL)

---

## Licencia

Este proyecto está licenciado bajo **GNU General Public License v3.0 (GPL-3.0)**.

Ver archivo [LICENSE](LICENSE) para más detalles.

---

*Hecho con QGIS y pasión por la cartografía chilena.*
