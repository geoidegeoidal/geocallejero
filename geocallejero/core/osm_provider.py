# geocallejero/core/osm_provider.py

from __future__ import annotations

import os
import hashlib
import shutil
import subprocess
from typing import Optional, List, Dict, Any

try:
    from qgis.core import (
        QgsSpatialIndex,
        QgsVectorLayer,
        QgsFeature,
        QgsGeometry,
        QgsPointXY,
        QgsTask,
        QgsApplication,
    )
    from qgis.PyQt.QtCore import pyqtSignal
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


class OsmProvider:
    """
    Provider de OpenStreetMap usando GDAL/ogr2ogr y caché GPKG local.

    Convierte archivos OSM PBF (~323MB) a GPKG ligero (~50MB) filtrando:
      - Puntos con etiqueta addr:housenumber
      - Líneas con etiqueta addr:interpolation

    Construye un índice espacial QgsSpatialIndex en memoria para consultas rápidas.
    """

    POINTS_LAYER = "osm_points"
    INTERPOLATION_LAYER = "osm_interpolation"
    HASH_FILENAME = "osm_cache.sha256"
    CACHE_FILENAME = "osm_cache.gpkg"

    def __init__(self, pbf_path: str, cache_dir: Optional[str] = None):
        if not os.path.exists(pbf_path):
            raise FileNotFoundError(f"Archivo PBF no encontrado: {pbf_path}")

        self.pbf_path = os.path.abspath(pbf_path)
        self.cache_dir = cache_dir or os.path.dirname(self.pbf_path)
        self.cache_path = os.path.join(self.cache_dir, self.CACHE_FILENAME)
        self.hash_path = os.path.join(self.cache_dir, self.HASH_FILENAME)

        self._spatial_index: Optional[QgsSpatialIndex] = None
        self._features_cache: Dict[int, QgsFeature] = {}
        self._points_layer: Optional[QgsVectorLayer] = None

    def _find_ogr2ogr(self) -> str:
        """Encuentra el ejecutable ogr2ogr en el entorno QGIS."""
        candidates = ["ogr2ogr", "ogr2ogr.exe"]

        if QGIS_AVAILABLE:
            try:
                prefix = QgsApplication.prefixPath()
                candidates.insert(0, os.path.join(prefix, "bin", "ogr2ogr.exe"))
            except Exception:
                pass

        for candidate in candidates:
            if shutil.which(candidate) or os.path.exists(candidate):
                return candidate

        raise RuntimeError(
            "No se encontró ogr2ogr. Asegúrese de que QGIS/GDAL esté instalado."
        )

    def compute_pbf_hash(self) -> str:
        """Calcula hash SHA256 del archivo PBF para validación de caché."""
        sha256 = hashlib.sha256()
        with open(self.pbf_path, "rb") as f:
            while True:
                chunk = f.read(131072)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()

    def _read_cached_hash(self) -> Optional[str]:
        """Lee el hash almacenado del PBF original que generó el caché."""
        if not os.path.exists(self.hash_path):
            return None
        with open(self.hash_path, "r") as f:
            return f.read().strip()

    def _write_cache_hash(self, hash_value: str):
        """Guarda el hash del PBF que generó el caché actual."""
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.hash_path, "w") as f:
            f.write(hash_value)

    def is_cache_valid(self) -> bool:
        """Verifica si el GPKG cacheado coincide con el PBF actual."""
        if not os.path.exists(self.cache_path):
            return False
        cached_hash = self._read_cached_hash()
        if cached_hash is None:
            return False
        return self.compute_pbf_hash() == cached_hash

    def convert_to_gpkg(self) -> str:
        """
        Convierte PBF a GPKG usando ogr2ogr en un subproceso.

        Extrae puntos con addr:housenumber y líneas con addr:interpolation.
        Retorna la ruta del GPKG generado.
        """
        ogr2ogr = self._find_ogr2ogr()
        os.makedirs(self.cache_dir, exist_ok=True)

        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)

        points_sql = (
            "SELECT osm_id, addr_housenumber, addr_street, "
            "addr_city, addr_postcode, other_tags "
            "FROM points "
            "WHERE addr_housenumber IS NOT NULL AND addr_housenumber <> ''"
        )

        result = subprocess.run(
            [
                ogr2ogr,
                "-f", "GPKG",
                self.cache_path,
                self.pbf_path,
                "-sql", points_sql,
                "-nln", self.POINTS_LAYER,
                "-overwrite",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ogr2ogr falló en capa de puntos: {result.stderr}")

        lines_sql = (
            "SELECT osm_id, addr_interpolation, addr_street, other_tags "
            "FROM lines "
            "WHERE addr_interpolation IS NOT NULL AND addr_interpolation <> ''"
        )

        result = subprocess.run(
            [
                ogr2ogr,
                "-f", "GPKG",
                self.cache_path,
                self.pbf_path,
                "-sql", lines_sql,
                "-nln", self.INTERPOLATION_LAYER,
                "-append",
            ],
            capture_output=True,
            text=True,
        )

        self._write_cache_hash(self.compute_pbf_hash())
        return self.cache_path

    def load_or_convert(self) -> str:
        """Carga el caché GPKG si es válido; si no, convierte el PBF."""
        if self.is_cache_valid():
            return self.cache_path
        return self.convert_to_gpkg()

    def build_spatial_index(self) -> "QgsSpatialIndex":
        """
        Construye índice espacial QgsSpatialIndex en memoria desde el GPKG.

        Carga la capa de puntos OSM y agrega cada feature al índice.
        También almacena las features en un dict por ID para consulta rápida.
        """
        if not QGIS_AVAILABLE:
            raise RuntimeError("QGIS no disponible para construir índice espacial")

        gpkg_path = self.load_or_convert()

        uri = f"{gpkg_path}|layername={self.POINTS_LAYER}"
        layer = QgsVectorLayer(uri, self.POINTS_LAYER, "ogr")

        if not layer.isValid():
            raise RuntimeError(f"No se pudo cargar la capa OSM: {uri}")

        self._points_layer = layer
        self._spatial_index = QgsSpatialIndex()
        self._features_cache.clear()

        for feature in layer.getFeatures():
            self._spatial_index.addFeature(feature)
            self._features_cache[feature.id()] = feature

        return self._spatial_index

    def has_index(self) -> bool:
        """Indica si el índice espacial ya fue construido."""
        return self._spatial_index is not None

    def nearest_points(
        self,
        x: float,
        y: float,
        max_results: int = 5,
        max_distance: float = 0.005,
    ) -> List[Dict[str, Any]]:
        """
        Busca los puntos OSM con número de casa más cercanos a (x, y).

        Retorna lista ordenada por distancia con campos:
        osm_id, housenumber, street, city, postcode, distance, source.
        """
        if self._spatial_index is None:
            raise RuntimeError("Llame a build_spatial_index() antes de consultar.")

        point = QgsPointXY(x, y)
        neighbor_ids = self._spatial_index.nearestNeighbor(point, max_results)

        results = []
        for fid in neighbor_ids:
            feature = self._features_cache.get(fid)
            if feature is None:
                continue

            geom = feature.geometry()
            if geom.isEmpty():
                continue

            feature_point = geom.asPoint()
            dist = point.distance(feature_point)

            if dist > max_distance:
                continue

            results.append(
                {
                    "osm_id": feature["osm_id"],
                    "housenumber": feature["addr_housenumber"],
                    "street": feature["addr_street"],
                    "city": feature["addr_city"],
                    "postcode": feature["addr_postcode"],
                    "geometry": geom,
                    "distance": dist,
                    "source": "osm_exact",
                }
            )

        results.sort(key=lambda r: r["distance"])
        return results

    @property
    def feature_count(self) -> int:
        """Cantidad de features en el índice espacial."""
        if self._points_layer is None:
            return 0
        return self._points_layer.featureCount()


if QGIS_AVAILABLE:

    class OsmConversionTask(QgsTask):
        """
        QgsTask para convertir OSM PBF a GPKG en background sin bloquear la UI de QGIS.
        """

        progressChanged = pyqtSignal(int, str)
        conversionFinished = pyqtSignal(str)
        conversionFailed = pyqtSignal(str)

        def __init__(self, provider: OsmProvider):
            super().__init__(
                "Convirtiendo OSM PBF a GPKG",
                QgsTask.CanCancel,
            )
            self.provider = provider
            self.result_path: Optional[str] = None
            self.error_message: Optional[str] = None

        def run(self):
            try:
                self.result_path = self.provider.convert_to_gpkg()
                return True
            except Exception as e:
                self.error_message = str(e)
                return False

        def finished(self, result: bool):
            if result:
                self.conversionFinished.emit(self.result_path)
            else:
                self.conversionFailed.emit(self.error_message or "Error desconocido")

        def cancel(self):
            super().cancel()
