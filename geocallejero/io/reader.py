# geocallejero/io/reader.py

import os
import csv
from typing import List, Dict, Optional, Tuple


ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"]


def _detect_encoding(filepath: str) -> str:
    """Detecta el encoding del archivo probando encodings comunes."""
    for enc in ENCODINGS:
        try:
            with open(filepath, "r", encoding=enc) as f:
                f.read(8192)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def _detect_delimiter(filepath: str, encoding: str) -> str:
    """Detecta el delimitador del CSV (coma, punto y coma, tab)."""
    with open(filepath, "r", encoding=encoding) as f:
        sample = f.read(4096)

    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=";,\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _auto_detect_columns(headers: List[str]) -> Dict[str, Optional[str]]:
    """
    Intenta mapear automáticamente las columnas del CSV a los campos esperados.

    Retorna dict con claves: address, comuna, id
    """
    mapping: Dict[str, Optional[str]] = {
        "address": None,
        "comuna": None,
        "id": None,
    }

    address_keywords = [
        "direccion", "dirección", "address", "calle", "street",
        "dir", "direc", "ubicacion", "ubicación", "full_address",
        "direccion_completa", "address_line",
    ]
    comuna_keywords = [
        "comuna", "comune", "city", "ciudad", "district",
        "distrito", "localidad", "municipality",
    ]
    id_keywords = [
        "id", "codigo", "código", "folio", "num", "numero",
        "número", "row_id", "index",
    ]

    for h in headers:
        h_lower = h.lower().strip()
        if mapping["address"] is None and any(k in h_lower for k in address_keywords):
            mapping["address"] = h
        elif mapping["comuna"] is None and any(k in h_lower for k in comuna_keywords):
            mapping["comuna"] = h
        elif mapping["id"] is None and any(k in h_lower for k in id_keywords):
            mapping["id"] = h

    if mapping["address"] is None and headers:
        mapping["address"] = headers[0]

    return mapping


def read_csv(
    filepath: str,
    address_col: Optional[str] = None,
    comuna_col: Optional[str] = None,
    id_col: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Lee un archivo CSV y retorna una lista de dicts con las columnas mapeadas.

    Retorna:
        - Lista de dicts con claves: raw_address, raw_comuna, row_id
        - Lista de headers originales del CSV
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    encoding = _detect_encoding(filepath)
    delimiter = _detect_delimiter(filepath, encoding)

    with open(filepath, "r", encoding=encoding) as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = reader.fieldnames or []

        if not headers:
            raise ValueError("El CSV no tiene headers")

        if address_col is None or comuna_col is None or id_col is None:
            auto = _auto_detect_columns(headers)
            if address_col is None:
                address_col = auto["address"]
            if comuna_col is None:
                comuna_col = auto["comuna"]
            if id_col is None:
                id_col = auto["id"]

        if address_col is None or address_col not in headers:
            raise ValueError(
                f"Columna de dirección no encontrada. "
                f"Headers disponibles: {headers}"
            )

        rows = []
        for i, row in enumerate(reader):
            rows.append(
                {
                    "raw_address": row.get(address_col, "").strip(),
                    "raw_comuna": row.get(comuna_col, "").strip() if comuna_col else "",
                    "row_id": row.get(id_col, str(i + 1)).strip() if id_col else str(i + 1),
                }
            )

    return rows, headers


def read_xlsx(
    filepath: str,
    address_col: Optional[str] = None,
    comuna_col: Optional[str] = None,
    id_col: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Lee un archivo XLSX usando la API de QGIS (sin dependencias externas).

    Usa QgsVectorLayer para leer el XLSX como capa vectorial.
    """
    try:
        from qgis.core import QgsVectorLayer
    except ImportError:
        raise ImportError("QGIS no disponible para lectura de XLSX")

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    layer = QgsVectorLayer(filepath, "xlsx_input", "ogr")
    if not layer.isValid():
        raise ValueError(f"No se pudo leer el archivo XLSX: {filepath}")

    headers = [field.name() for field in layer.fields()]

    if address_col is None or comuna_col is None or id_col is None:
        auto = _auto_detect_columns(headers)
        if address_col is None:
            address_col = auto["address"]
        if comuna_col is None:
            comuna_col = auto["comuna"]
        if id_col is None:
            id_col = auto["id"]

    if address_col is None or address_col not in headers:
        raise ValueError(
            f"Columna de dirección no encontrada. "
            f"Headers disponibles: {headers}"
        )

    rows = []
    for i, feature in enumerate(layer.getFeatures()):
        attrs = {field.name(): str(feature[field.name()] or "") for field in layer.fields()}
        rows.append(
            {
                "raw_address": attrs.get(address_col, "").strip(),
                "raw_comuna": attrs.get(comuna_col, "").strip() if comuna_col else "",
                "row_id": attrs.get(id_col, str(i + 1)).strip() if id_col else str(i + 1),
            }
        )

    return rows, headers


def read_file(
    filepath: str,
    address_col: Optional[str] = None,
    comuna_col: Optional[str] = None,
    id_col: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Lee un archivo CSV o XLSX automáticamente según la extensión.
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return read_csv(filepath, address_col, comuna_col, id_col)
    elif ext in (".xlsx", ".xls"):
        return read_xlsx(filepath, address_col, comuna_col, id_col)
    else:
        raise ValueError(f"Formato no soportado: {ext}. Use .csv o .xlsx")
