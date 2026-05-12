# geocallejero/core/street_index.py

from typing import Dict, List, Optional
import difflib

class StreetFeature:
    """
    Representa un segmento de calle indexado en memoria.
    Evita mantener todo el QgsFeature en memoria, solo guarda lo estrictamente necesario.
    """
    def __init__(self, fid: int, comuna: str, nombre_calle: str, tipo_via: str, 
                 ini_izq: float, ini_der: float, ter_izq: float, ter_der: float,
                 nombre_aux: str = ""):
        self.fid = fid
        self.comuna = comuna
        self.nombre_calle = nombre_calle
        self.tipo_via = tipo_via
        self.ini_izq = ini_izq
        self.ini_der = ini_der
        self.ter_izq = ter_izq
        self.ter_der = ter_der
        self.nombre_aux = nombre_aux
        
    def has_ranges(self) -> bool:
        """Verifica si el segmento tiene al menos un rango de numeración válido (> 0)"""
        return self.ini_izq > 0 or self.ini_der > 0 or self.ter_izq > 0 or self.ter_der > 0

class StreetIndex:
    """
    Índice en memoria estructurado jerárquicamente para búsquedas O(1) 
    o fuzzy matching eficiente sobre el Maestro de Calles.
    
    Estructura: Dict[comuna, Dict[nombre_calle_normalizado, List[StreetFeature]]]
    """
    def __init__(self):
        self._index: Dict[str, Dict[str, List[StreetFeature]]] = {}
        self.is_loaded = False

    def build_index(self, layer, progress_callback=None):
        """
        Lee el QgsVectorLayer del Maestro de Calles y construye el índice.
        """
        # Limpiar índice previo
        self._index.clear()
        
        feature_count = layer.featureCount()
        if feature_count == 0:
            return

        from qgis.core import QgsFeatureRequest
        
        # Iterar sobre las features, se extraen los atributos clave
        # Asumimos que la capa ya viene validada con los campos requeridos
        request = QgsFeatureRequest()
        request.setSubsetOfAttributes(['COMUNA', 'NOMBRE_MAE', 'TIPO_VIA', 'INI_IZQ', 'INI_DER', 'TER_IZQ', 'TER_DER', 'NOMBRE_AUX'], layer.fields())
        request.setFlags(QgsFeatureRequest.NoGeometry)
        
        step = max(1, feature_count // 100)
        
        for idx, feat in enumerate(layer.getFeatures(request)):
            if progress_callback and idx % step == 0:
                progress_callback(int((idx / feature_count) * 100))
                
            comuna = str(feat['COMUNA']).upper().strip()
            calle = str(feat['NOMBRE_MAE']).upper().strip()
            
            if not comuna or not calle:
                continue
                
            if comuna not in self._index:
                self._index[comuna] = {}
                
            if calle not in self._index[comuna]:
                self._index[comuna][calle] = []
                
            sf = StreetFeature(
                fid=feat.id(),
                comuna=comuna,
                nombre_calle=calle,
                tipo_via=str(feat['TIPO_VIA']).upper().strip() if feat['TIPO_VIA'] else "",
                ini_izq=float(feat['INI_IZQ'] or 0.0),
                ini_der=float(feat['INI_DER'] or 0.0),
                ter_izq=float(feat['TER_IZQ'] or 0.0),
                ter_der=float(feat['TER_DER'] or 0.0),
                nombre_aux=str(feat['NOMBRE_AUX']).upper().strip() if feat['NOMBRE_AUX'] else ""
            )
            self._index[comuna][calle].append(sf)

        self.is_loaded = True
        if progress_callback:
            progress_callback(100)

    def find_exact(self, comuna: str, nombre_calle: str) -> List[StreetFeature]:
        """Búsqueda exacta (O(1))"""
        if not self.is_loaded or comuna not in self._index:
            return []
        return self._index[comuna].get(nombre_calle, [])

    def find_fuzzy(self, comuna: str, nombre_calle: str, threshold: float = 0.80) -> List[StreetFeature]:
        """Búsqueda difusa usando difflib.SequenceMatcher. Limitada a la comuna específica."""
        if not self.is_loaded or comuna not in self._index:
            return []
        
        best_matches = []
        highest_ratio = 0.0
        
        calles_comuna = self._index[comuna]
        for candidate_calle in calles_comuna.keys():
            ratio = difflib.SequenceMatcher(None, nombre_calle, candidate_calle).ratio()
            
            if ratio >= threshold:
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    best_matches = calles_comuna[candidate_calle]
                elif ratio == highest_ratio:
                    # Empate en similitud, agregar a la lista
                    best_matches.extend(calles_comuna[candidate_calle])
                    
        return best_matches
