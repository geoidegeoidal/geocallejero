# geocallejero/plugin.py
# Orquestador principal del plugin GeoCallejero

from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
import os


class GeoCallejeroPlugin:
    """Plugin QGIS: GeoCallejero — Geocodificador Chileno de Direcciones."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu_name = "GeoCallejero"
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = QIcon()

        action = QAction(icon, "GeoCallejero", self.iface.mainWindow())
        action.triggered.connect(self.run)
        action.setEnabled(True)

        self.iface.addPluginToMenu(self.menu_name, action)
        self.iface.addToolBarIcon(action)
        self.actions.append(action)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu_name, action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        if self.dialog is None:
            from geocallejero.ui.main_dialog import MainDialog
            self.dialog = MainDialog(self.iface, self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
