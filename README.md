<p align="center">
  <img src="geocallejero/icon.svg" width="88" alt="Icono de Geocallejero CL">
</p>

# Geocallejero CL
**Direcciones chilenas → resultados geográficos en QGIS**

Plugin experimental para geocodificar listados CSV/XLSX a partir del **Maestro de Calles**, con normalización de direcciones, interpolación y una capa de resultados para revisar en QGIS.

**[Instalación](#instalación) · [Primer uso](#primer-uso) · [Alcance y resultados](#alcance-y-resultados) · [Desarrollo](#desarrollo)**

> **Estado:** versión 0.1.0 experimental. La metadata declara QGIS 3.34–4.99; ese rango no sustituye una prueba en tu instalación. La búsqueda exacta de direcciones en OSM aún está pendiente de integración en el motor.

## Antes de empezar

| Necesitas | Para qué |
| :--- | :--- |
| QGIS y el plugin instalado | Ejecutar el asistente y visualizar la capa de salida |
| CSV/XLSX con dirección y comuna | Identificar la calle dentro de su comuna; el motor necesita ambos datos para buscar en el Maestro |
| Datos base del Maestro de Calles | Interpolar o localizar el segmento vial |
| Conexión para la descarga inicial | Obtener los datos base desde el gestor integrado |

**Procesamiento local no significa instalación sin conexión.** El gestor descarga los datos y los conserva en `geocallejero_data`, dentro del perfil de QGIS. Una vez disponibles, el motor trabaja con las fuentes locales. Esto no constituye una garantía general de privacidad o seguridad de todo el entorno QGIS.

## Instalación

1. Descarga o clona este repositorio.
2. Copia la carpeta interna [`geocallejero/`](geocallejero/) —la que contiene `metadata.txt` y `__init__.py`— al directorio de plugins del perfil de QGIS. No copies el repositorio completo como si fuera el plugin.
3. Reinicia QGIS y activa **Geocallejero CL** desde el administrador de complementos.
4. Abre **Geocallejero CL** desde el menú de complementos o su icono en la barra de herramientas.

## Primer uso

| Paso | Acción | Qué revisar |
| :--- | :--- | :--- |
| **1 · Datos** | Selecciona el CSV/XLSX y asigna las columnas de dirección, comuna e identificador | Que la comuna esté informada y las direcciones sean reconocibles |
| **2 · Fuentes** | Descarga los datos base si todavía no están disponibles | Que el Maestro de Calles se haya cargado correctamente |
| **3 · Ejecución** | Revisa la configuración y pulsa **Geocodificar** | La tabla de resultados, su fuente y su puntuación |

Al terminar, el plugin intenta añadir la capa **`geocallejero_resultados`** al proyecto. Revisa los resultados antes de usarlos en un análisis o exportarlos.

## Alcance y resultados

El motor normaliza abreviaturas como `Av.`, `Pje.` y `N°`, busca candidatos de calle y aplica la siguiente estrategia:

| Método | Estado actual | Interpretación |
| :--- | :--- | :--- |
| **Maestro · interpolación** | Implementado | Estima la posición con rangos de numeración y paridad; no equivale a una ubicación predial verificada |
| **OSM · dirección exacta** | Pendiente de integración en el matcher | Existe infraestructura de carga/caché PBF/GPKG, pero no debe asumirse que este nivel resuelva direcciones |
| **Maestro · centroide** | Implementado como alternativa | Asigna el centroide del segmento candidato; no la ubicación exacta del domicilio |
| **Sin coincidencia** | Resultado posible | Una calle no encontrada, datos incompletos o errores pueden dejar el registro sin geometría |

La salida incluye `gc_source`, `gc_score`, `gc_lat` y `gc_lon`, además de la dirección original y sus campos normalizados. **El score es una heurística del motor, no una probabilidad calibrada de acierto.** Prioriza la revisión de centroides, coincidencias aproximadas y registros `sin_match`.

## Desarrollo

El procesamiento utiliza tareas `QgsTask` con señales de progreso. La integración geoespacial se apoya en la API de QGIS y en GDAL para la preparación de fuentes OSM.

| Carpeta | Responsabilidad |
| :--- | :--- |
| [`geocallejero/core/`](geocallejero/core/) | Normalización, búsqueda de calles, interpolación, descarga y procesamiento |
| [`geocallejero/io/`](geocallejero/io/) | Lectura de archivos y escritura de resultados |
| [`geocallejero/ui/`](geocallejero/ui/) | Asistente de tres pasos en Qt |
| [`geocallejero/tests/`](geocallejero/tests/) | Pruebas del proyecto |

Para reportar un problema, abre un [issue](https://github.com/geoidegeoidal/geocallejero/issues) con tu versión de QGIS y un ejemplo anonimizado. No publiques direcciones personales ni archivos sensibles.

## Autoría y licencia

Creado por **Jorge Ulloa Roa** · [jorge.ulloa.roa@gmail.com](mailto:jorge.ulloa.roa@gmail.com).

El código incluye la [GNU GPL v3](LICENSE). Los datos utilizados conservan sus licencias y atribuciones propias; para OpenStreetMap corresponde considerar la ODbL.
