# geocallejero/io/writer.py

from typing import List, Dict, Any, Optional

try:
    from qgis.core import (
        QgsVectorLayer,
        QgsFeature,
        QgsField,
        QgsGeometry,
        QgsPointXY,
        QgsProject,
    )
    from qgis.PyQt.QtCore import QVariant
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


OUTPUT_FIELDS = [
    QgsField("row_id", QVariant.String),
    QgsField("raw_address", QVariant.String),
    QgsField("raw_comuna", QVariant.String),
    QgsField("gc_tipo_via", QVariant.String),
    QgsField("gc_nombre", QVariant.String),
    QgsField("gc_numero", QVariant.Int),
    QgsField("gc_comuna", QVariant.String),
    QgsField("gc_source", QVariant.String),
    QgsField("gc_score", QVariant.Double),
    QgsField("gc_lat", QVariant.Double),
    QgsField("gc_lon", QVariant.Double),
]


def create_output_layer(layer_name: str = "geocallejero_resultados") -> QgsVectorLayer:
    """
    Crea una capa vectorial en memoria con los campos de resultado de geocodificación.
    """
    if not QGIS_AVAILABLE:
        raise RuntimeError("QGIS no disponible para crear capa de salida")

    layer = QgsVectorLayer("Point?crs=EPSG:4326", layer_name, "memory")
    if not layer.isValid():
        raise RuntimeError("No se pudo crear la capa de resultados")

    dp = layer.dataProvider()
    dp.addAttributes(OUTPUT_FIELDS)
    layer.updateFields()

    return layer


def write_results(
    layer: QgsVectorLayer,
    results: List[Dict[str, Any]],
    add_to_project: bool = True,
) -> QgsVectorLayer:
    """
    Escribe los resultados de geocodificación en una capa vectorial.

    Cada resultado debe tener:
    - row_id, raw_address, raw_comuna
    - gc_tipo_via, gc_nombre, gc_numero, gc_comuna
    - gc_source, gc_score
    - geometry (QgsGeometry) o gc_lat/gc_lon
    """
    if not QGIS_AVAILABLE:
        raise RuntimeError("QGIS no disponible para escribir resultados")

    dp = layer.dataProvider()
    features = []

    for r in results:
        feat = QgsFeature(layer.fields())

        feat.setAttribute("row_id", str(r.get("row_id", "")))
        feat.setAttribute("raw_address", str(r.get("raw_address", "")))
        feat.setAttribute("raw_comuna", str(r.get("raw_comuna", "")))
        feat.setAttribute("gc_tipo_via", str(r.get("gc_tipo_via", "")))
        feat.setAttribute("gc_nombre", str(r.get("gc_nombre", "")))

        num = r.get("gc_numero")
        if num is not None:
            feat.setAttribute("gc_numero", int(num))

        feat.setAttribute("gc_comuna", str(r.get("gc_comuna", "")))
        feat.setAttribute("gc_source", str(r.get("gc_source", "sin_match")))
        feat.setAttribute("gc_score", float(r.get("gc_score", 0.0)))

        lat = r.get("gc_lat")
        lon = r.get("gc_lon")
        geom = r.get("geometry")

        if geom is not None:
            feat.setGeometry(geom)
        elif lat is not None and lon is not None:
            feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        else:
            feat.setGeometry(QgsGeometry())

        features.append(feat)

    dp.addFeatures(features)
    layer.updateExtents()

    if add_to_project:
        QgsProject.instance().addMapLayer(layer)

    return layer
