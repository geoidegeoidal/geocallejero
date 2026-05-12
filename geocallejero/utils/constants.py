# geocallejero/utils/constants.py

import re

# Diccionario de homologación de tipos de vías (Standard del Maestro de Calles)
TIPOS_VIA_MAP = {
    "AVENIDA": "AVENIDA", "AV": "AVENIDA", "AV.": "AVENIDA", "AVDA": "AVENIDA", "AVDA.": "AVENIDA",
    "CALLE": "CALLE", "C.": "CALLE", "C/": "CALLE",
    "PASAJE": "PASAJE", "PJE": "PASAJE", "PJE.": "PASAJE", "PJ": "PASAJE",
    "CAMINO": "CAMINO", "CNO": "CAMINO", "CNO.": "CAMINO",
    "CARRETERA": "CARRETERA", "CARR": "CARRETERA",
    "PEATONAL": "PEATONAL", "PASEO": "PEATONAL",
    "ESCALA": "ESCALA", "ESCALERA": "ESCALA",
    "HUELLA": "HUELLA",
    "PASARELA": "PASARELA",
    "PRINCIPAL": "PRINCIPAL",
    "PRIVADO": "PRIVADO",
    "PUENTE": "PUENTE", "PTE": "PUENTE", "PTE.": "PUENTE",
    "SECUNDARIO": "SECUNDARIO",
    "SENDERO": "SENDERO",
    "BAJONIVEL": "BAJONIVEL",
    "SOBRENIVEL": "SOBRENIVEL",
    "RUTA": "CARRETERA" # Frecuente en input de usuario
}

# Tipos de vías conocidos (valores normalizados)
KNOWN_TIPOS = set(TIPOS_VIA_MAP.values())

# Regex para extraer el número domiciliario (busca el último bloque de dígitos de la cadena, posiblemente antecedido de N, Nº, #)
# Ejemplos: "Arturo Prat 1234", "Sargento Aldea N° 12", "Los Aromos # 45"
RE_NUMERO = re.compile(r'(?:N[º°]?(?:\s|/|-)*|#\s*)?(\d+)[a-zA-Z]?(?:\s|,|$)', re.IGNORECASE)

# Basura común a limpiar del final o inicio
BASURA_REGEX = re.compile(r'\b(ESQ|ESQUINA|DE|LA|LAS|EL|LOS)\b', re.IGNORECASE)
