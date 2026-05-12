# geocallejero/core/interpolator.py

import math
from typing import Optional, Tuple
from .street_index import StreetFeature

# Para asegurar que no falle fuera de QGIS en tests unitarios, importamos defensivamente
try:
    from qgis.core import QgsGeometry, QgsPointXY
except ImportError:
    pass

class LinearInterpolator:
    """
    Maneja la interpolación matemática sobre geometrías lineales basándose 
    en rangos de numeración duales (Izquierda/Derecha).
    """

    @staticmethod
    def interpolate(geometry, feature: StreetFeature, number: int, offset_meters: float = 0.0):
        """
        Calcula la coordenada exacta a lo largo de la geometría para un número dado.
        Retorna (QgsPointXY, float_score) o (None, 0.0)
        """
        # Determinar paridad
        is_even = (number % 2 == 0)
        
        # En Chile, típicamente la numeración par está en un lado (ej. izquierda) y la impar en el otro (ej. derecha).
        # Sin embargo, esto puede variar. Debemos ver qué lado contiene nuestro número.
        
        side = None
        from_num = 0.0
        to_num = 0.0
        
        # Función auxiliar para chequear si el número cae en un rango (considerando ascendente o descendente)
        def in_range(n, ini, ter):
            if ini == 0 and ter == 0: return False
            return min(ini, ter) <= n <= max(ini, ter)
            
        # Revisar lado izquierdo
        if in_range(number, feature.ini_izq, feature.ter_izq):
            side = 'IZQ'
            from_num = feature.ini_izq
            to_num = feature.ter_izq
        # Revisar lado derecho
        elif in_range(number, feature.ini_der, feature.ter_der):
            side = 'DER'
            from_num = feature.ini_der
            to_num = feature.ter_der
            
        if not side:
            # Si el número no cae estrictamente en ningún lado pero el segmento tiene rangos, 
            # podemos forzarlo al lado cuya paridad coincida con el número (heurística fallback)
            # O simplemente retornar None y dejar que el Fallback a Centroide actúe.
            # Para mejor precisión en bordes, dejaremos que retorne None y caiga a Nivel 3 (Centroide).
            return None, 0.0
            
        # Calcular porcentaje a lo largo del segmento
        rango_total = abs(to_num - from_num)
        if rango_total == 0:
            percent_along = 0.5 # Rango inválido pero matched (ej. 100 a 100), usar punto medio
        else:
            # Si es descendente (from_num > to_num), el porcentaje se invierte naturalmente 
            # si restamos number - from_num y dividimos por to_num - from_num
            percent_along = (number - from_num) / (to_num - from_num)
            
        # Asegurar límites [0.0, 1.0]
        percent_along = max(0.0, min(1.0, percent_along))
        
        # Interpolación geométrica nativa de QGIS
        length = geometry.length()
        distance_along = length * percent_along
        
        # Punto sobre la línea
        interpolated_point_geom = geometry.interpolate(distance_along)
        if not interpolated_point_geom or interpolated_point_geom.isEmpty():
            return None, 0.0
            
        base_point = interpolated_point_geom.asPoint()
        
        # Offset perpendicular (si se requiere > 0.0)
        if offset_meters > 0.0:
            # Calcular ángulo tangente en el punto
            # TODO: Implementar lógica de vertex extraction y angulo para offset
            # QgsGeometry.offsetCurve() puede ser costoso para una simple interpolación
            # Por ahora, devolvemos el punto base.
            pass
            
        # Score de interpolación lineal pura = 100
        return base_point, 100.0
