# geocallejero/__init__.py
# Entry point del plugin GeoCallejero para QGIS

def classFactory(iface):
    """Entry point requerido por QGIS para cargar el plugin."""
    from geocallejero.plugin import GeoCallejeroPlugin
    return GeoCallejeroPlugin(iface)
