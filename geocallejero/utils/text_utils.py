# geocallejero/utils/text_utils.py

import re
import unicodedata

def normalize_text(text: str) -> str:
    """
    Normaliza el texto: mayúsculas, sin acentos, sin puntuación extraña.
    """
    if not text:
        return ""
    
    # 1. Quitar acentos (NFD separa la letra del acento, luego filtramos los "Mn" que son los acentos)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # 2. Mayúsculas
    text = text.upper()
    
    # 3. Reemplazar puntuación común por espacio, excepto # que puede ser indicador de número
    text = re.sub(r'[.,;\'\"_]', ' ', text)
    
    # 4. Reducir múltiples espacios a uno solo y trim
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def clean_street_name(name: str) -> str:
    """
    Limpia palabras basura del nombre de la calle, pero solo si no dejan el nombre vacío.
    """
    # Si la calle se llama "LA LUNA", quitar "LA" dejaría "LUNA", lo cual está bien para fuzzy matching.
    # Pero no queremos quitar "LOS" si la calle se llama literalmente "LOS ALAMOS" y es un match exacto,
    # El fuzzy matcher se encargará mejor. Por ahora, solo limpiamos espacios.
    return normalize_text(name)
