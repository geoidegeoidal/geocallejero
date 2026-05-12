# geocallejero/core/geocoder.py

from __future__ import annotations

from typing import List, Dict, Any, Optional

from geocallejero.core.address_parser import AddressParser
from geocallejero.core.street_index import StreetIndex
from geocallejero.core.matcher import AddressMatcher
from geocallejero.core.interpolator import LinearInterpolator
from geocallejero.utils.text_utils import normalize_text

try:
    from qgis.core import (
        QgsTask,
        QgsVectorLayer,
        QgsFeatureRequest,
        QgsGeometry,
        QgsPointXY,
    )
    from qgis.PyQt.QtCore import pyqtSignal
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


class GeocodingTask(QgsTask):
    """
    QgsTask que ejecuta la geocodificación en background sin bloquear la UI.

    Orquesta:
    1. AddressParser para normalizar cada dirección
    2. StreetIndex + AddressMatcher para buscar en Maestro de Calles
    3. OsmProvider para búsqueda por cercanía (Nivel 2)
    4. Fallback a centroide (Nivel 3)

    Emite señales de progreso para la UI.
    """

    progress = pyqtSignal(int)
    status_message = pyqtSignal(str)
    finished_with_results = pyqtSignal(list)
    finished_with_error = pyqtSignal(str)

    def __init__(
        self,
        rows: List[Dict[str, str]],
        maestro_layer: Optional[QgsVectorLayer] = None,
        osm_provider=None,
    ):
        super().__init__("Geocodificando direcciones", QgsTask.CanCancel)
        self.rows = rows
        self.osm_provider = osm_provider
        self.parser = AddressParser()
        self.results: List[Dict[str, Any]] = []
        self.error_message: Optional[str] = None

        self.matcher: Optional[AddressMatcher] = None
        if maestro_layer is not None and maestro_layer.isValid():
            street_index = StreetIndex()
            street_index.build_index(maestro_layer)
            self.matcher = AddressMatcher(street_index, maestro_layer, osm_provider)

    def run(self) -> bool:
        total = len(self.rows)
        if total == 0:
            self.error_message = "No hay direcciones para geocodificar"
            return False

        for i, row in enumerate(self.rows):
            if self.isCanceled():
                return False

            try:
                result = self._geocode_row(row)
                self.results.append(result)
            except Exception as e:
                result = self._error_result(row, str(e))
                self.results.append(result)

            pct = int((i + 1) / total * 100)
            self.progress.emit(pct)
            self.status_message.emit(
                f"Geocodificando {i + 1}/{total} — {row.get('row_id', '?')}"
            )

        return True

    def _geocode_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        raw_address = row.get("raw_address", "")
        raw_comuna = row.get("raw_comuna", "")

        parsed = self.parser.parse(raw_address, raw_comuna)

        result = {
            "row_id": row.get("row_id", ""),
            "raw_address": raw_address,
            "raw_comuna": raw_comuna,
            "gc_tipo_via": parsed.get("tipo_via") or "",
            "gc_nombre": parsed.get("nombre_calle", ""),
            "gc_numero": parsed.get("numero"),
            "gc_comuna": parsed.get("comuna") or "",
            "gc_source": "sin_match",
            "gc_score": 0.0,
            "gc_lat": None,
            "gc_lon": None,
            "geometry": None,
        }

        if self.matcher is not None:
            match_result = self.matcher.match(parsed)
            if match_result["status"] == "MATCHED" and match_result["point"]:
                result["gc_source"] = match_result["source"]
                result["gc_score"] = match_result["score"] / 100.0
                result["gc_lat"] = match_result["point"].y()
                result["gc_lon"] = match_result["point"].x()
                result["geometry"] = QgsGeometry.fromPointXY(match_result["point"])
                return result

        result = self._try_osm_match(parsed, result)

        return result

    def _try_osm_match(
        self, parsed: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.osm_provider is None or not self.osm_provider.has_index():
            return result

        if parsed.get("numero") is None:
            return result

        street_name = normalize_text(parsed.get("nombre_calle", ""))
        if not street_name:
            return result

        return result

    def _error_result(
        self, row: Dict[str, str], error: str
    ) -> Dict[str, Any]:
        return {
            "row_id": row.get("row_id", ""),
            "raw_address": row.get("raw_address", ""),
            "raw_comuna": row.get("raw_comuna", ""),
            "gc_tipo_via": "",
            "gc_nombre": "",
            "gc_numero": None,
            "gc_comuna": "",
            "gc_source": f"error: {error[:50]}",
            "gc_score": 0.0,
            "gc_lat": None,
            "gc_lon": None,
            "geometry": None,
        }

    def finished(self, success: bool):
        if success:
            self.finished_with_results.emit(self.results)
        else:
            msg = self.error_message or "Geocodificación cancelada o fallida"
            self.finished_with_error.emit(msg)
