# Geocallejero CL — Geocodificador Híbrido Chileno para QGIS

**Geocallejero CL** es un plugin robusto para QGIS (compatible con 3.34 LTR y 4.x) que permite geocodificar masivamente listados de direcciones chilenas (CSV/XLSX) con la mayor precisión posible sin depender de servicios web ni APIs externas, garantizando la **privacidad total** de tus datos.

Creado por **Jorge Ulloa Roa** (jorge.ulloa.roa@gmail.com).

## 🚀 Estrategia Híbrida de 3 Niveles
Geocallejero CL no falla fácilmente. Emplea un motor en cascada para maximizar la tasa de éxito:

1. **Maestro de Calles (Interpolación Lineal)**: Si la dirección tiene numeración, el motor verifica la paridad (izquierda/derecha) usando los rangos oficiales (`INI_IZQ`, `TER_DER`, etc.) e interpola matemáticamente la geometría.
2. **OpenStreetMap PBF (Match Exacto)**: Si la numeración no está disponible en los rangos del Maestro, se busca complementariamente el nodo exacto en OSM usando `addr:housenumber`.
3. **Fallback a Centroide**: Si la calle no posee numeración en ninguna fuente, el sistema se rescata asignando el centroide del segmento vial para que ningún registro quede sin georreferenciación.

## ✨ Características Principales
* **100% Offline (Plug & Play)**: El usuario no necesita buscar capas base por la web. El plugin incluye un gestor de descarga integrado que obtiene automáticamente (~124MB) los datos base del *Maestro de Calles* y los aloja seguros en la carpeta de configuración de QGIS.
* **Normalizador NLP Chileno**: Motor integrado de parseo heurístico de direcciones que entiende, normaliza y limpia textos sucios (ej. `"Av.", "Pje.", "Esq", "N°"`) mitigando tildes y caracteres especiales.
* **Cero Bloqueos de Interfaz (Async)**: Procesamiento masivo de miles de puntos gestionado vía `QgsTask` en *background threads*, con barra de progreso.
* **Ciberseguridad Incorporada**: Extracción de archivos en formato Zip totalmente mitigada contra vulnerabilidades de *Path Traversal (Zip Slip)*.
* **Arquitectura de Alto Rendimiento**: Empleo de `QgsSpatialIndex` en memoria y conversiones eficientes de PBF a *GeoPackage* (GPKG) empleando motores `GDAL` subyacentes nativos de QGIS. Ninguna librería externa como `osmium` es necesaria.

## 🛠 Instalación y Uso
1. Instala el plugin desde el repositorio o clonando esta carpeta dentro de tu directorio de *plugins* de QGIS.
2. Abre la herramienta desde el menú vectorial o barra de herramientas de QGIS.
3. El Wizard consta de 3 pasos:
   * **Paso 1**: Sube tu archivo CSV/XLSX e indica las columnas que contienen la *Dirección* y (opcionalmente) la *Comuna*.
   * **Paso 2**: El plugin te informará si requiere descargar los datos base. Si es primera vez, haz clic en el botón de descarga.
   * **Paso 3**: Revisa tu configuración y presiona "Geocodificar". ¡Listo! Se generará una nueva capa de puntos.

## 💼 Arquitectura "Clean" (Para Desarrolladores)
El código fue diseñado modularmente siguiendo estrictas convenciones de diseño y estándares "Elite Pragmatic":
* `core/`: Contiene `address_parser`, `interpolator`, `matcher`, y manejo paralelo.
* `io/`: Maneja I/O de CSV/Excel.
* `ui/`: Implementa las vistas en Qt puro mediante clases en capas separadas para fácil mantención.

## 📄 Licencia
Este proyecto es código abierto. Los resultados derivados de OSM mantienen su debida licencia ODbL a nivel de metadata.
