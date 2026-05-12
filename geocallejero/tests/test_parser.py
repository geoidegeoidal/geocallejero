# geocallejero/tests/test_parser.py

import sys
import os
import pytest

# Agregar el directorio raíz al path para que pueda encontrar el módulo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from geocallejero.core.address_parser import AddressParser

def test_parse_simple_address():
    parser = AddressParser()
    res = parser.parse("Sargento Aldea 1234", "Iquique")
    
    assert res["tipo_via"] is None
    assert res["nombre_calle"] == "SARGENTO ALDEA"
    assert res["numero"] == 1234
    assert res["comuna"] == "IQUIQUE"

def test_parse_with_tipo_via_abbr():
    parser = AddressParser()
    res = parser.parse("Av. Arturo Prat 567", "Iquique")
    
    assert res["tipo_via"] == "AVENIDA"
    assert res["nombre_calle"] == "ARTURO PRAT"
    assert res["numero"] == 567

def test_parse_with_tipo_via_full():
    parser = AddressParser()
    res = parser.parse("PASAJE LOS AROMOS 12", "Iquique")
    
    assert res["tipo_via"] == "PASAJE"
    assert res["nombre_calle"] == "LOS AROMOS"
    assert res["numero"] == 12

def test_parse_with_number_prefix():
    parser = AddressParser()
    res = parser.parse("Avenida Siempre Viva N° 742")
    
    assert res["tipo_via"] == "AVENIDA"
    assert res["nombre_calle"] == "SIEMPRE VIVA"
    assert res["numero"] == 742
    assert res["comuna"] is None

def test_parse_comuna_in_string():
    parser = AddressParser()
    res = parser.parse("Calle 1 # 45, Alto Hospicio")
    
    assert res["tipo_via"] == "CALLE"
    assert res["nombre_calle"] == "1"
    assert res["numero"] == 45
    assert res["comuna"] == "ALTO HOSPICIO"

def test_parse_accented_and_dirty():
    parser = AddressParser()
    res = parser.parse(" Pje.  Los Ángeles   Nº1234  , Concepción ")
    
    assert res["tipo_via"] == "PASAJE"
    assert res["nombre_calle"] == "LOS ANGELES"
    assert res["numero"] == 1234
    assert res["comuna"] == "CONCEPCION"
