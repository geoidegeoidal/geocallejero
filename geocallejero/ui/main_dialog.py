# geocallejero/ui/main_dialog.py

import os
from typing import Optional, List, Dict

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QFormLayout,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QFont, QIcon

from geocallejero.io.reader import read_file
from geocallejero.core.osm_provider import OsmProvider
from geocallejero.core.geocoder import GeocodingTask
from geocallejero.io.writer import create_output_layer, write_results

try:
    from qgis.core import QgsTaskManager, QgsApplication, QgsVectorLayer
    from qgis.PyQt.QtCore import QCoreApplication
except ImportError:
    pass

STEPS = ["1. Datos", "2. Fuentes", "3. Ejecutar"]

QSS = """
QDialog {
    background-color: #f5f7fa;
}
QGroupBox {
    font-weight: bold;
    border: 2px solid #d1d5db;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #1a5276;
}
QPushButton {
    background-color: #1a5276;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    min-width: 100px;
}
QPushButton:hover {
    background-color: #2471a3;
}
QPushButton:pressed {
    background-color: #154360;
}
QPushButton:disabled {
    background-color: #bdc3c7;
    color: #7f8c8d;
}
QPushButton#secondary {
    background-color: #ecf0f1;
    color: #2c3e50;
    border: 1px solid #bdc3c7;
}
QPushButton#secondary:hover {
    background-color: #d5dbdb;
}
QPushButton#danger {
    background-color: #e74c3c;
}
QPushButton#danger:hover {
    background-color: #c0392b;
}
QPushButton#success {
    background-color: #27ae60;
}
QPushButton#success:hover {
    background-color: #229954;
}
QLineEdit, QComboBox {
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 6px 10px;
    background-color: #ffffff;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #1a5276;
}
QLabel {
    font-size: 13px;
    color: #2c3e50;
}
QLabel#step_indicator {
    font-size: 14px;
    font-weight: bold;
    color: #1a5276;
}
QProgressBar {
    border: 1px solid #d1d5db;
    border-radius: 6px;
    text-align: center;
    height: 24px;
    background-color: #ecf0f1;
}
QProgressBar::chunk {
    background-color: #1a5276;
    border-radius: 5px;
}
QTableWidget {
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background-color: #ffffff;
    gridline-color: #ecf0f1;
}
QTableWidget::item {
    padding: 4px 8px;
}
QTableWidget::item:selected {
    background-color: #d4e6f1;
    color: #1a5276;
}
QHeaderView::section {
    background-color: #1a5276;
    color: white;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QTextEdit {
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background-color: #ffffff;
    font-family: monospace;
    font-size: 12px;
}
"""


class WizardStep(QWidget):
    """Widget base para cada paso del wizard."""

    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(16)

        title_label = QLabel(title)
        title_label.setObjectName("step_indicator")
        title_label.setStyleSheet("font-size: 18px; color: #1a5276; font-weight: bold;")
        self.layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        self.layout.addWidget(desc_label)


class Step1Data(WizardStep):
    """Paso 1: Selección de archivo y mapeo de columnas."""

    def __init__(self, parent=None):
        super().__init__(
            "Paso 1: Cargar Datos",
            "Seleccione su archivo CSV o XLSX con las direcciones a geocodificar.",
            parent,
        )

        self.file_path = ""
        self.address_column: Optional[str] = None
        self.comuna_column: Optional[str] = None
        self.id_column: Optional[str] = None

        self._build_ui()

    def _build_ui(self):
        group = QGroupBox("Archivo de Entrada")
        form = QFormLayout()

        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("Seleccione un archivo CSV o XLSX...")

        browse_btn = QPushButton("Examinar")
        browse_btn.setObjectName("secondary")
        browse_btn.clicked.connect(self._browse_file)
        browse_btn.setFixedWidth(100)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_edit)
        file_layout.addWidget(browse_btn)
        form.addRow("Archivo:", file_layout)

        self.format_label = QLabel("")
        self.format_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        form.addRow("Detectado:", self.format_label)

        group.setLayout(form)
        self.layout.addWidget(group)

        col_group = QGroupBox("Mapeo de Columnas")
        col_form = QFormLayout()

        self.address_combo = QComboBox()
        self.address_combo.addItem("-- Seleccione --")
        col_form.addRow("Columna Dirección:", self.address_combo)

        self.comuna_combo = QComboBox()
        self.comuna_combo.addItem("-- Ninguna --")
        col_form.addRow("Columna Comuna:", self.comuna_combo)

        self.id_combo = QComboBox()
        self.id_combo.addItem("-- Automático --")
        col_form.addRow("Columna ID:", self.id_combo)

        col_group.setLayout(col_form)
        self.layout.addWidget(col_group)

        self.preview_label = QLabel("Vista previa aparecerá aquí...")
        self.preview_label.setStyleSheet("color: #95a5a6; font-style: italic;")
        self.layout.addWidget(self.preview_label)

        self.layout.addStretch()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de direcciones",
            "",
            "Archivos de datos (*.csv *.xlsx *.xls);;Todos (*.*)",
        )
        if path:
            self.file_path = path
            self.file_edit.setText(path)
            self._load_columns(path)

    def _load_columns(self, path: str):
        try:
            _, headers = read_file(path)
            self.format_label.setText(
                f"{len(headers)} columnas detectadas — {os.path.splitext(path)[1].upper()}"
            )

            self.address_combo.clear()
            self.address_combo.addItem("-- Seleccione --")
            self.address_combo.addItems(headers)

            self.comuna_combo.clear()
            self.comuna_combo.addItem("-- Ninguna --")
            self.comuna_combo.addItems(headers)

            self.id_combo.clear()
            self.id_combo.addItem("-- Automático --")
            self.id_combo.addItems(headers)

            self.preview_label.setText(
                f"Headers: {', '.join(headers[:8])}{'...' if len(headers) > 8 else ''}"
            )
        except Exception as e:
            self.format_label.setText(f"Error: {str(e)}")
            self.format_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def get_mappings(self):
        addr = self.address_combo.currentText()
        com = self.comuna_combo.currentText()
        id_ = self.id_combo.currentText()

        return {
            "file_path": self.file_path,
            "address_col": addr if addr != "-- Seleccione --" else None,
            "comuna_col": com if com != "-- Ninguna --" else None,
            "id_col": id_ if id_ != "-- Automático --" else None,
        }

    def is_valid(self) -> bool:
        if not self.file_path:
            QMessageBox.warning(self, "Error", "Seleccione un archivo de entrada.")
            return False
        addr = self.address_combo.currentText()
        if addr == "-- Seleccione --":
            QMessageBox.warning(self, "Error", "Seleccione la columna de dirección.")
            return False
        return True


class Step2Sources(WizardStep):
    """Paso 2: Selección de fuentes de datos (Maestro de Calles, OSM PBF)."""

    def __init__(self, parent=None):
        super().__init__(
            "Paso 2: Configurar Fuentes",
            "Seleccione las fuentes de datos para la geocodificación.",
            parent,
        )

        self.maestro_path: Optional[str] = None
        self.pbf_path: Optional[str] = None
        self.use_osm = True

        self._build_ui()

    def _build_ui(self):
        osm_group = QGroupBox("OpenStreetMap (PBF)")
        osm_layout = QFormLayout()

        self.osm_check = QComboBox()
        self.osm_check.addItem("Sí — Usar OSM como fuente")
        self.osm_check.addItem("No — Solo Maestro de Calles")
        osm_layout.addRow("Habilitar OSM:", self.osm_check)

        self.osm_edit = QLineEdit()
        self.osm_edit.setReadOnly(True)
        self.osm_edit.setPlaceholderText("Seleccione archivo .osm.pbf...")

        osm_browse = QPushButton("Examinar")
        osm_browse.setObjectName("secondary")
        osm_browse.clicked.connect(self._browse_pbf)
        osm_browse.setFixedWidth(100)

        osm_file_layout = QHBoxLayout()
        osm_file_layout.addWidget(self.osm_edit)
        osm_file_layout.addWidget(osm_browse)
        osm_layout.addRow("Archivo PBF:", osm_file_layout)

        self.osm_status = QLabel("Sin archivo seleccionado")
        self.osm_status.setStyleSheet("color: #95a5a6;")
        osm_layout.addRow("Estado:", self.osm_status)

        osm_group.setLayout(osm_layout)
        self.layout.addWidget(osm_group)

        maestro_group = QGroupBox("Maestro de Calles (SHP)")
        maestro_layout = QFormLayout()

        self.maestro_edit = QLineEdit()
        self.maestro_edit.setReadOnly(True)
        self.maestro_edit.setPlaceholderText("Seleccione shapefile del Maestro de Calles...")

        maestro_browse = QPushButton("Examinar")
        maestro_browse.setObjectName("secondary")
        maestro_browse.clicked.connect(self._browse_maestro)
        maestro_browse.setFixedWidth(100)

        maestro_file_layout = QHBoxLayout()
        maestro_file_layout.addWidget(self.maestro_edit)
        maestro_file_layout.addWidget(maestro_browse)
        maestro_layout.addRow("Shapefile:", maestro_file_layout)

        self.maestro_status = QLabel("Sin archivo seleccionado (opcional)")
        self.maestro_status.setStyleSheet("color: #95a5a6;")
        maestro_layout.addRow("Estado:", self.maestro_status)

        maestro_group.setLayout(maestro_layout)
        self.layout.addWidget(maestro_group)

        info = QLabel(
            "Nota: El Maestro de Calles se usará para interpolación lineal y fallback. "
            "OSM proporciona puntos exactos con addr:housenumber."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d; font-size: 11px; font-style: italic;")
        self.layout.addWidget(info)

        self.layout.addStretch()

    def _browse_pbf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo OSM PBF", "", "OSM PBF (*.osm.pbf *.pbf);;Todos (*.*)"
        )
        if path:
            self.pbf_path = path
            self.osm_edit.setText(path)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            self.osm_status.setText(f"PBF cargado: {size_mb:.1f} MB")
            self.osm_status.setStyleSheet("color: #27ae60; font-weight: bold;")

    def _browse_maestro(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Maestro de Calles SHP", "", "Shapefile (*.shp);;Todos (*.*)"
        )
        if path:
            self.maestro_path = path
            self.maestro_edit.setText(path)
            self.maestro_status.setText("Shapefile cargado")
            self.maestro_status.setStyleSheet("color: #27ae60; font-weight: bold;")

    def get_config(self) -> dict:
        return {
            "use_osm": self.osm_check.currentIndex() == 0,
            "pbf_path": self.pbf_path,
            "maestro_path": self.maestro_path,
        }

    def is_valid(self) -> bool:
        if self.osm_check.currentIndex() == 0 and not self.pbf_path:
            QMessageBox.warning(self, "Error", "Seleccione un archivo PBF de OSM.")
            return False
        return True


class Step3Execute(WizardStep):
    """Paso 3: Ejecución y resultados."""

    def __init__(self, parent=None):
        super().__init__(
            "Paso 3: Geocodificar",
            "Revise la configuración y ejecute la geocodificación.",
            parent,
        )

        self._build_ui()

    def _build_ui(self):
        self.config_group = QGroupBox("Configuración")
        self.config_layout = QFormLayout()

        self.lbl_file = QLabel("")
        self.config_layout.addRow("Archivo:", self.lbl_file)

        self.lbl_cols = QLabel("")
        self.config_layout.addRow("Columnas:", self.lbl_cols)

        self.lbl_osm = QLabel("")
        self.config_layout.addRow("OSM PBF:", self.lbl_osm)

        self.lbl_maestro = QLabel("")
        self.config_layout.addRow("Maestro:", self.lbl_maestro)

        self.config_group.setLayout(self.config_layout)
        self.layout.addWidget(self.config_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        self.layout.addWidget(self.status_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["ID", "Dirección", "Resultado", "Fuente", "Score"]
        )
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setVisible(False)
        self.layout.addWidget(self.results_table)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(120)
        self.log_edit.setVisible(False)
        self.layout.addWidget(self.log_edit)

        self.layout.addStretch()

    def update_config(self, data_config: dict, sources_config: dict):
        self.lbl_file.setText(os.path.basename(data_config.get("file_path", "")))
        self.lbl_cols.setText(
            f"Dir: {data_config.get('address_col', '?')} | "
            f"Com: {data_config.get('comuna_col', 'N/A')}"
        )
        self.lbl_osm.setText(
            os.path.basename(sources_config.get("pbf_path", ""))
            if sources_config.get("use_osm")
            else "Desactivado"
        )
        self.lbl_maestro.setText(
            os.path.basename(sources_config.get("maestro_path", ""))
            if sources_config.get("maestro_path")
            else "No seleccionado"
        )

    def set_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def show_results(self, results: list):
        self.results_table.setVisible(True)
        self.results_table.setRowCount(len(results))

        total_score = 0.0
        for i, r in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(str(r.get("row_id", ""))))
            self.results_table.setItem(i, 1, QTableWidgetItem(str(r.get("raw_address", ""))))

            source = r.get("gc_source", "sin_match")
            score = r.get("gc_score", 0.0)
            total_score += score

            if source.startswith("osm"):
                self.results_table.setItem(i, 2, QTableWidgetItem("Match OSM"))
            elif source.startswith("maestro"):
                self.results_table.setItem(i, 2, QTableWidgetItem("Match Maestro"))
            elif source == "sin_match":
                self.results_table.setItem(i, 2, QTableWidgetItem("Sin match"))
            else:
                self.results_table.setItem(i, 2, QTableWidgetItem(source))

            self.results_table.setItem(i, 3, QTableWidgetItem(source))
            self.results_table.setItem(i, 4, QTableWidgetItem(f"{score:.2f}"))

        avg = total_score / len(results) if results else 0
        self.status_label.setText(
            f"Completado: {len(results)} direcciones | Score promedio: {avg:.2f}"
        )
        self.progress_bar.setValue(100)


class MainDialog(QDialog):
    """
    Diálogo principal tipo Wizard de 3 pasos para GeoCallejero.
    """

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("GeoCallejero — Geocodificador Chileno")
        self.setMinimumSize(650, 520)
        self.resize(700, 580)

        self.osm_provider = None
        self.geocoding_task = None

        self._build_ui()
        self._apply_styles()
        self._go_to_step(0)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        self.stacked = QStackedWidget()

        self.step1 = Step1Data(self)
        self.step2 = Step2Sources(self)
        self.step3 = Step3Execute(self)

        self.stacked.addWidget(self.step1)
        self.stacked.addWidget(self.step2)
        self.stacked.addWidget(self.step3)

        main_layout.addWidget(self.stacked)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(12)

        self.btn_back = QPushButton("Anterior")
        self.btn_back.setObjectName("secondary")
        self.btn_back.clicked.connect(self._prev_step)

        self.btn_next = QPushButton("Siguiente")
        self.btn_next.clicked.connect(self._next_step)

        self.btn_run = QPushButton("Geocodificar")
        self.btn_run.setObjectName("success")
        self.btn_run.clicked.connect(self._run_geocoding)
        self.btn_run.setVisible(False)

        self.btn_close = QPushButton("Cerrar")
        self.btn_close.setObjectName("secondary")
        self.btn_close.clicked.connect(self.close)

        nav_layout.addWidget(self.btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        nav_layout.addWidget(self.btn_run)
        nav_layout.addWidget(self.btn_close)

        main_layout.addLayout(nav_layout)

    def _apply_styles(self):
        self.setStyleSheet(QSS)

    def _go_to_step(self, index: int):
        self.stacked.setCurrentIndex(index)

        self.btn_back.setVisible(index > 0)
        self.btn_next.setVisible(index < 2)
        self.btn_run.setVisible(index == 2)

        if index == 2:
            self.step3.update_config(self.step1.get_mappings(), self.step2.get_config())

    def _next_step(self):
        current = self.stacked.currentIndex()
        if current == 0 and not self.step1.is_valid():
            return
        if current == 1 and not self.step2.is_valid():
            return
        self._go_to_step(current + 1)

    def _prev_step(self):
        current = self.stacked.currentIndex()
        if current > 0:
            self._go_to_step(current - 1)

    def _run_geocoding(self):
        data_config = self.step1.get_mappings()
        sources_config = self.step2.get_config()

        try:
            rows, _ = read_file(
                data_config["file_path"],
                data_config["address_col"],
                data_config["comuna_col"],
                data_config["id_col"],
            )
        except Exception as e:
            QMessageBox.critical(self, "Error de lectura", str(e))
            return

        if not rows:
            QMessageBox.warning(self, "Sin datos", "El archivo no contiene filas válidas.")
            return

        maestro_layer = None
        if sources_config.get("maestro_path"):
            try:
                maestro_layer = QgsVectorLayer(
                    sources_config["maestro_path"], "maestro_calles", "ogr"
                )
                if not maestro_layer.isValid():
                    maestro_layer = None
                    self.step3.status_label.setText("Advertencia: Maestro de Calles inválido")
            except Exception as e:
                self.step3.status_label.setText(f"Advertencia: {str(e)}")

        if sources_config.get("use_osm") and sources_config.get("pbf_path"):
            try:
                self.osm_provider = OsmProvider(sources_config["pbf_path"])
                self.step3.status_label.setText("Cargando índice OSM...")
                self.osm_provider.load_or_convert()
                self.osm_provider.build_spatial_index()
                count = self.osm_provider.feature_count
                self.step3.status_label.setText(f"Índice OSM cargado: {count:,} puntos")
            except Exception as e:
                QMessageBox.warning(
                    self, "Error OSM", f"No se pudo cargar el índice OSM:\n{str(e)}"
                )
                self.osm_provider = None

        self.step3.progress_bar.setVisible(True)
        self.step3.results_table.setVisible(False)
        self.step3.log_edit.setVisible(False)
        self.btn_run.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_back.setEnabled(False)

        self.geocoding_task = GeocodingTask(
            rows=rows,
            maestro_layer=maestro_layer,
            osm_provider=self.osm_provider,
        )

        self.geocoding_task.progress.connect(self.step3.set_progress)
        self.geocoding_task.status_message.connect(
            lambda msg: self.step3.status_label.setText(msg)
        )
        self.geocoding_task.finished_with_results.connect(self._on_finished)
        self.geocoding_task.finished_with_error.connect(self._on_error)

        QgsApplication.taskManager().addTask(self.geocoding_task)

    def _on_finished(self, results: list):
        self.btn_run.setEnabled(True)
        self.btn_next.setEnabled(True)
        self.btn_back.setEnabled(True)

        try:
            layer = create_output_layer("geocallejero_resultados")
            write_results(layer, results, add_to_project=True)
        except Exception as e:
            QMessageBox.warning(self, "Error al escribir", str(e))

        self.step3.show_results(results)
        self.iface.messageBar().pushSuccess(
            "GeoCallejero", f"Geocodificación completada: {len(results)} direcciones"
        )

    def _on_error(self, error: str):
        self.btn_run.setEnabled(True)
        self.btn_next.setEnabled(True)
        self.btn_back.setEnabled(True)
        self.step3.status_label.setText(f"Error: {error}")
        self.step3.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error de geocodificación", error)

    def closeEvent(self, event):
        if self.geocoding_task and self.geocoding_task.isRunning():
            self.geocoding_task.cancel()
        super().closeEvent(event)
