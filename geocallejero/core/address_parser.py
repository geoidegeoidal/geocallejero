# geocallejero/core/address_parser.py

import re
from typing import Dict, Optional, Tuple
from geocallejero.utils.text_utils import normalize_text, clean_street_name
from geocallejero.utils.constants import TIPOS_VIA_MAP, KNOWN_TIPOS, RE_NUMERO

class AddressParser:
    """
    Parser NLP ligero para extraer componentes de direcciones chilenas sucias.
    """

    def __init__(self):
        pass

    def parse(self, raw_address: str, raw_comuna: Optional[str] = None) -> Dict[str, any]:
        """
        Intenta parsear una dirección cruda. Si se entrega la comuna por separado, la usa.
        Si no, intenta extraerla de la coma final si existe (ej. "Calle 1, Iquique").
        
        Retorna un dict con:
        - tipo_via (str|None)
        - nombre_calle (str)
        - numero (int|None)
        - comuna (str|None)
        """
        result = {
            "tipo_via": None,
            "nombre_calle": "",
            "numero": None,
            "comuna": None
        }

        if not raw_address:
            return result

        # 1. Tratar la comuna si viene en la cadena (separada por coma)
        if raw_comuna:
            result["comuna"] = normalize_text(raw_comuna)
        else:
            parts = raw_address.split(',')
            if len(parts) > 1:
                result["comuna"] = normalize_text(parts[-1])
                raw_address = " ".join(parts[:-1]) # Todo menos lo último

        norm_address = normalize_text(raw_address)
        
        # 2. Extraer número domiciliario
        matches = list(RE_NUMERO.finditer(norm_address))
        if matches:
            # Tomar el último número encontrado como el número de casa
            last_match = matches[-1]
            try:
                result["numero"] = int(last_match.group(1))
                # Limpiar el número y sus prefijos del nombre de la calle
                norm_address = norm_address[:last_match.start()] + norm_address[last_match.end():]
            except ValueError:
                pass

        # 3. Extraer tipo de vía al principio
        tokens = norm_address.split()
        if tokens:
            first_token = tokens[0]
            # Revisar si el primer token es un tipo de vía conocido
            if first_token in TIPOS_VIA_MAP:
                result["tipo_via"] = TIPOS_VIA_MAP[first_token]
                tokens.pop(0)
            else:
                # Tratar de ver si los dos primeros forman un tipo (poco probable en nuestro map, pero por si acaso)
                pass
                
        # 4. Lo que queda es el nombre de la calle
        nombre_calle = " ".join(tokens)
        
        # Limpiar basuras finales comunes como "N" (de "N°" que quedó trunco)
        nombre_calle = re.sub(r'\bN\b$', '', nombre_calle).strip()
        
        result["nombre_calle"] = clean_street_name(nombre_calle)
        
        return result
