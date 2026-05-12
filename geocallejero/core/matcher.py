# geocallejero/core/matcher.py

from typing import Dict, Any, Optional
from .street_index import StreetIndex, StreetFeature
from .interpolator import LinearInterpolator

class AddressMatcher:
    """
    Motor de Matching multi-nivel (Cascada).
    Nivel 1: Maestro Exacto + Interpolación
    Nivel 2: OSM Exacto (Opcional, si osm_provider está disponible)
    Nivel 3: Maestro Centroide (Fallback)
    """
    
    def __init__(self, street_index: StreetIndex, maestro_layer, osm_provider=None):
        self.index = street_index
        self.layer = maestro_layer
        self.osm_provider = osm_provider
        
    def match(self, parsed_address: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la cascada para una dirección parseada.
        Retorna un dict con:
        {
            "status": "MATCHED" | "UNMATCHED",
            "source": "MAESTRO_INTERPOLADO" | "OSM_EXACTO" | "MAESTRO_CENTROIDE" | None,
            "score": float (0-100),
            "point": QgsPointXY | None,
            "calle_match": str
        }
        """
        comuna = parsed_address.get("comuna", "")
        calle = parsed_address.get("nombre_calle", "")
        numero = parsed_address.get("numero", None)
        
        result = {
            "status": "UNMATCHED",
            "source": None,
            "score": 0.0,
            "point": None,
            "calle_match": ""
        }
        
        if not comuna or not calle:
            return result
            
        # --- BÚSQUEDA DE CALLES (Exacta o Fuzzy) ---
        candidates = self.index.find_exact(comuna, calle)
        score_base = 100.0
        
        if not candidates:
            # Fallback a Fuzzy
            candidates = self.index.find_fuzzy(comuna, calle, threshold=0.85)
            score_base = 85.0 # Penalización por ser match fuzzy
            
        if not candidates:
            return result # Totalmente UNMATCHED en Maestro
            
        # --- NIVEL 1: MAESTRO INTERPOLADO ---
        if numero is not None:
            # Filtrar candidatos que tengan algún rango definido
            ranged_candidates = [c for c in candidates if c.has_ranges()]
            
            best_point = None
            best_score = 0.0
            best_calle = ""
            
            for candidate in ranged_candidates:
                # Obtener la geometría real desde la capa usando el FID
                feat = self.layer.getFeature(candidate.fid)
                if feat.isValid() and feat.hasGeometry():
                    geom = feat.geometry()
                    pt, local_score = LinearInterpolator.interpolate(geom, candidate, numero, offset_meters=0.0)
                    
                    if pt and local_score > best_score:
                        best_point = pt
                        best_score = local_score
                        best_calle = candidate.nombre_calle
                        
            if best_point:
                result["status"] = "MATCHED"
                result["source"] = "MAESTRO_INTERPOLADO"
                # Promediamos el score del match de texto con el éxito de interpolación
                result["score"] = (score_base + best_score) / 2.0 
                result["point"] = best_point
                result["calle_match"] = best_calle
                return result
                
        # --- NIVEL 2: OSM EXACTO (addr:housenumber) ---
        if self.osm_provider and numero is not None:
            # TODO: Consultar índice OSM para buscar el nodo exacto
            # pt_osm, score_osm = self.osm_provider.find_exact_node(comuna, calle, numero)
            # if pt_osm:
            #     return { status: "MATCHED", source: "OSM_EXACTO", score: 95.0, point: pt_osm, calle_match: calle }
            pass
            
        # --- NIVEL 3: MAESTRO CENTROIDE (Fallback) ---
        # Si llegamos aquí:
        # a) El usuario no dio número.
        # b) Dio número, pero la calle en el Maestro no tiene rangos de numeración (y OSM no lo tiene).
        # c) El número dado cae muy fuera de los rangos definidos.
        
        # Tomamos el primer candidato de la lista de matches (podría mejorarse ordenando por longitud de calle, etc)
        fallback_candidate = candidates[0]
        feat = self.layer.getFeature(fallback_candidate.fid)
        
        if feat.isValid() and feat.hasGeometry():
            geom = feat.geometry()
            centroid = geom.centroid().asPoint()
            
            result["status"] = "MATCHED"
            result["source"] = "MAESTRO_CENTROIDE"
            # Penalización fuerte del score porque es solo el centro de la calle, no la casa exacta.
            result["score"] = score_base * 0.50 
            result["point"] = centroid
            result["calle_match"] = fallback_candidate.nombre_calle
            
        return result
