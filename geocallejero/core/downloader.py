# geocallejero/core/downloader.py

import os
import urllib.request
import zipfile
from typing import Optional

try:
    from qgis.core import QgsTask, QgsApplication
    from qgis.PyQt.QtCore import pyqtSignal
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


def get_data_dir() -> str:
    """Retorna la ruta de la carpeta donde se guardarán los datos base."""
    if QGIS_AVAILABLE:
        base_path = QgsApplication.qgisSettingsDirPath()
    else:
        # Fallback para tests fuera de QGIS
        base_path = os.path.expanduser("~")
        
    data_dir = os.path.join(base_path, "geocallejero_data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def get_maestro_path() -> Optional[str]:
    """Busca el shapefile del maestro en el directorio de datos."""
    data_dir = get_data_dir()
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith('.shp') and "maestro" in file.lower():
                return os.path.join(root, file)
    return None

def get_osm_path() -> Optional[str]:
    """Busca el GPKG de OSM en el directorio de datos."""
    data_dir = get_data_dir()
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.lower().endswith('.gpkg') and "osm" in file.lower():
                return os.path.join(root, file)
    return None

def has_data() -> bool:
    """Verifica si ya existen los datos descargados y descomprimidos."""
    return get_maestro_path() is not None

if QGIS_AVAILABLE:
    class DownloadTask(QgsTask):
        """
        QgsTask para descargar y descomprimir archivos pesados en background.
        """
        progressChanged = pyqtSignal(int, str)
        downloadFinished = pyqtSignal(bool, str)

        def __init__(self, url: str, dest_dir: str):
            super().__init__("Descargando Datos de GeoCallejero", QgsTask.CanCancel)
            self.url = url
            self.dest_dir = dest_dir
            self.zip_path = os.path.join(dest_dir, "datos_temporales.zip")
            self.error_msg = ""
            self._is_canceled = False

        def run(self):
            try:
                # Callback para progreso de descarga
                def reporthook(count, block_size, total_size):
                    if self._is_canceled:
                        raise Exception("Descarga cancelada por el usuario.")
                    
                    if total_size > 0:
                        percent = int(count * block_size * 100 / total_size)
                        # Cap at 95% para dejar el 5% para la extracción
                        self.setProgress(min(95, percent))
                        mb_downloaded = (count * block_size) / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        msg = f"Descargando: {mb_downloaded:.1f} MB de {mb_total:.1f} MB"
                        self.progressChanged.emit(min(95, percent), msg)
                
                self.progressChanged.emit(0, "Iniciando conexión...")
                urllib.request.urlretrieve(self.url, self.zip_path, reporthook)
                
                if self._is_canceled:
                    return False
                    
                self.progressChanged.emit(95, "Descomprimiendo archivos...")
                
                # Descomprimir de forma segura (Mitigación Zip Slip)
                with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                    for member in zip_ref.namelist():
                        member_path = os.path.abspath(os.path.join(self.dest_dir, member))
                        if not member_path.startswith(os.path.abspath(self.dest_dir)):
                            raise Exception("Alerta de seguridad: Intento de Path Traversal (Zip Slip) bloqueado.")
                    zip_ref.extractall(self.dest_dir)
                    
                # Limpiar zip temporal
                try:
                    os.remove(self.zip_path)
                except:
                    pass
                    
                self.progressChanged.emit(100, "¡Archivos listos!")
                return True
                
            except Exception as e:
                self.error_msg = str(e)
                return False

        def finished(self, result: bool):
            if result:
                self.downloadFinished.emit(True, "Descarga y extracción exitosa.")
            else:
                self.downloadFinished.emit(False, f"Error: {self.error_msg}")

        def cancel(self):
            self._is_canceled = True
            super().cancel()
