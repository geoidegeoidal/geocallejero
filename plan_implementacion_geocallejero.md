# GeoCallejero — Plan de Implementación por Fases (QGIS Plugin)

Estrategia **Híbrida de 3 niveles**: 
1. **Maestro de Calles (Interpolación Lineal)** para ejes con numeración (29.6%).
2. **OpenStreetMap PBF (`addr:housenumber`)** como complemento exacto.
3. **Fallback a Centroide** para calles sin numeración en ninguna fuente.
Además, incluye un **Normalizador Inteligente de Direcciones** para procesar inputs sucios (ej. `"Av. Arturo Prat N° 1234, Iquique"`).

## Especificaciones de Arquitectura y Estándares
- **Stack**: Python 3.9+, PyQt5/PyQt6 (vía `qgis.PyQt` shim para compatibilidad QGIS 3.34 LTR y 4.x), GDAL (nativo QGIS).
- **Cero Dependencias Externas**: Todo corre sobre la API base de QGIS (`QgsTask`, `QgsVectorLayer`, `ogr2ogr`).
- **Arquitectura**: Clean Architecture (UI desacoplada del Core lógico).
- **Estructura de Directorios (A crear en la raíz del plugin `geocallejero/`)**:
  - `core/`: Lógica de geocodificación, parser, interpolador, motor de matching.
  - `io/`: Lectores de CSV/XLSX y escritores de resultados.
  - `ui/`: Vistas Qt, diálogos y widgets.
  - `utils/`: Constantes, utilidades de texto.
  - `tests/`: Pruebas unitarias de Pytest.

---

## FASE 1: Core de Normalización y Parser NLP Ligero
**Objetivo**: Construir el motor que entiende direcciones chilenas sucias y extrae sus componentes lógicos, vital para el paso 3 (fallback).
**Modelo Asignado**: `gemini 3.1 pro high` (Para diseño robusto de regex y heurísticas NLP).

### Contexto de Desarrollo (Inputs y Outputs):
Se requiere parsear cadenas de texto libres como `"Pje. Los Aromos 123, Iquique"` a un diccionario estructurado: 
`{"tipo_via": "PASAJE", "nombre_calle": "LOS AROMOS", "numero": 123, "comuna": "IQUIQUE"}`.
Se debe considerar que a veces la comuna puede no venir en el texto si el usuario la pasa en una columna separada.

### Tareas:
1. Crear `geocallejero/utils/constants.py`:
   - Diccionarios de homologación chilena: `TIPOS_VIA` ("Pasaje" -> "PASAJE", "Avenida" -> "AVENIDA", "Av." -> "AVENIDA", "Pje" -> "PASAJE").
   - Constantes regex para limpieza.
2. Crear `geocallejero/utils/text_utils.py`:
   - `normalize_text(text: str) -> str`: Convierte a mayúsculas, elimina acentos (á->A), remueve caracteres especiales.
3. Crear `geocallejero/core/address_parser.py`:
   - Lógica de extracción de `tipo_via`, `nombre_calle`, `numero`, `comuna` usando expresiones regulares.
   - Limpieza de prefijos basura como "N°", "Esquina", "Esq".
4. Crear Pruebas Unitarias del Parser (`geocallejero/tests/test_parser.py`) y verificarlas con `pytest`.

---

## FASE 2: Provider OSM y Caché GeoPackage
**Objetivo**: Procesar el enorme PBF de OSM (~323MB) en un caché GPKG ligero (~50MB) usando solo herramientas nativas de QGIS/GDAL.
**Modelo Asignado**: `opencode-go/deepseek-v4-pro` (Especialista en scripts bash/gdal y optimización de I/O).

### Contexto de Desarrollo:
No se debe bloquear el main thread de QGIS. Se utilizará `QgsTask` o `subprocess` para llamar a `ogr2ogr`.
Las geometrías requeridas de OSM son puntos con `addr:housenumber` y líneas con `addr:interpolation`.

### Tareas:
1. Crear `geocallejero/core/osm_provider.py`:
   - Implementar wrapper sobre GDAL ejecutado en background.
   - Filtrar capas PBF y guardarlas como `.gpkg` local.
   - Generar hash SHA256 del PBF original para caching.
2. Construir el índice espacial `QgsSpatialIndex` en memoria a partir del GPKG cacheado para consultas rápidas.

---

## FASE 3: Motor de Matching, Índices e Interpolación Lineal
**Objetivo**: Construir el cerebro espacial que une las direcciones parseadas con el Maestro de Calles o OSM.
**Modelo Asignado**: `gemini 3.1 pro high` (Para lógica algorítmica compleja, interpolación de geometrías y manejo de estado).

### Contexto de Desarrollo:
El Maestro de Calles posee los campos `INI_IZQ`, `INI_DER`, `TER_IZQ`, `TER_DER`. Se debe interpolar según paridad.

### Tareas:
1. Crear `geocallejero/core/street_index.py`:
   - Carga lazy del SHP del Maestro de Calles a un diccionario `Dict[Comuna][Calle]`.
2. Crear `geocallejero/core/interpolator.py`:
   - Lógica de paridad y matemáticas de interpolación lineal (`QgsGeometry.interpolate()`).
   - Aplicación de offset perpendicular opcional.
3. Crear `geocallejero/core/matcher.py`:
   - Nivel 1: Maestro exacto.
   - Nivel 2: OSM exacto.
   - Nivel 3: Maestro Centroide.
4. Asignar score de confianza y campo `gc_source`.

---

## FASE 4: UI Premium (Wizard) y Orquestador de Tareas
**Objetivo**: Interfaz moderna tipo Wizard.
**Modelo Asignado**: `opencode-go/qwen3.6-plus` (Experto en PyQt5/PyQt6, manejo de UI threads y CSS/QSS styling).

### Tareas:
1. Crear I/O para lectura de CSV y escritura de layers.
2. Crear `geocallejero/core/geocoder.py` (`QgsTask` worker).
3. Construir `geocallejero/ui/main_dialog.py` (Wizard de 3 pasos).
4. Configurar el Entry Point del plugin en `__init__.py` y `plugin.py`.
