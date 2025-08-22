#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visor de Imágenes moderno con barra de herramientas estilo Dock.

Requisitos (Debian/Mint):
    sudo apt-get update && sudo apt-get install -y python3-pyqt5 python3-pil

Ejecución:
    python3 dock_image_viewer.py [carpeta|archivo]

Características:
 - Abrir carpeta o archivos sueltos
 - Miniaturas laterales
 - Navegación anterior/siguiente (mouse wheel, teclas ← →)
 - Zoom +/-/100% y Ajuste a ventana
 - Rotar izquierda/derecha
 - Pantalla completa (F11)
 - Presentación (slideshow)
 - Arrastrar y soltar archivos/carpeta
 - Eliminar archivo a la papelera (opcional) o borrar permanente
 - Atajos de teclado
 - Barra inferior estilo "Dock" con íconos grandes y efecto flotante

Nota: Para mover archivos a la papelera se intenta usar 'gio' (GNOME). Si no está,
     se ofrece eliminación permanente con confirmación.
"""

import os
import sys
import math
import time
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
try:
    from PIL import Image
except Exception:
    Image = None  # PIL solo se usa para rotaciones sin pérdida (opcional)

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tif', '.tiff'}

def human_sort_key(p: Path):
    # Natural sort: img2 < img10
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', p.name)]

class ImageLabel(QtWidgets.QLabel):
    """Etiqueta que muestra la imagen con mejor calidad de escalado."""
    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setBackgroundRole(QtGui.QPalette.Base)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.setScaledContents(False)

class DockToolbar(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal(str)

    def __init__(self, actions):
        super().__init__()
        self.setObjectName("DockToolbar")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(12)
        layout.addStretch(1)

        for act in actions:
            btn = QtWidgets.QToolButton(self)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
            btn.setIcon(act.icon())
            btn.setIconSize(QtCore.QSize(28, 28))
            btn.setAutoRaise(True)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            btn.setToolTip(act.toolTip())
            btn.clicked.connect(act.trigger)

            # Estilo "dock" (círculo, sombra, efecto hover)
            btn.setProperty('dock', True)
            layout.addWidget(btn)
        layout.addStretch(1)

        # Estilo moderno con transparencia y blur simulado
        self.setStyleSheet('''
        #DockToolbar {
            background: rgba(20,20,28,0.65);
            border-radius: 16px;
        }
        QToolButton[dock="true"] {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 8px;
        }
        QToolButton[dock="true"]:hover {
            background: rgba(255,255,255,0.14);
        }
        QToolButton[dock="true"]:pressed {
            background: rgba(255,255,255,0.22);
        }
        ''')

class ImageViewer(QtWidgets.QMainWindow):
    def __init__(self, start_path: Path = None):
        super().__init__()
        self.setWindowTitle("Visor de Imágenes")
        self.resize(1200, 800)
        self.setStyleSheet("QMainWindow{background:#0f1115;color:#E6E6F0;} QListWidget{background:#0b0d11;color:#cfd3e7;border:none;} QScrollArea{border:none}")

        self.image_label = ImageLabel()
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidget(self.image_label)
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(QtCore.Qt.AlignCenter)
        self.setCentralWidget(self.scroll)

        # Lista de miniaturas
        self.thumb_list = QtWidgets.QListWidget()
        self.thumb_list.setViewMode(QtWidgets.QListView.IconMode)
        self.thumb_list.setResizeMode(QtWidgets.QListView.Adjust)
        self.thumb_list.setIconSize(QtCore.QSize(96, 96))
        self.thumb_list.setMovement(QtWidgets.QListView.Static)
        self.thumb_list.setSpacing(8)
        self.thumb_list.setFixedWidth(160)
        self.thumb_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.thumb_list.itemClicked.connect(self.on_thumb_clicked)

        # Dock lateral
        side = QtWidgets.QDockWidget("Miniaturas", self)
        side.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        side.setTitleBarWidget(QtWidgets.QWidget())
        side.setWidget(self.thumb_list)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, side)

        # Estado
        self.files = []  # type: list[Path]
        self.index = -1
        self.scale = 1.0
        self.fit_to_window = False
        self.rotation_deg = 0
        self.slideshow_timer = QtCore.QTimer(self)
        self.slideshow_timer.timeout.connect(self.next_image)

        # Acciones
        self.create_actions()
        self.create_menus()
        self.create_dock_toolbar()

        # Arrastrar y soltar
        self.setAcceptDrops(True)

        # Teclas rápidas
        self.setup_shortcuts()

        # Cargar ruta inicial
        if start_path:
            self.open_path(start_path)

        # Mostrar ayuda inicial
        QtCore.QTimer.singleShot(500, self.show_welcome)

    # ---------- UI helpers ----------
    def create_actions(self):
        s = self.style()
        self.act_open = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_DialogOpenButton), "Abrir (Ctrl+O)", self)
        self.act_open.triggered.connect(self.open_dialog)

        self.act_open_folder = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_DirOpenIcon), "Abrir carpeta (Ctrl+Shift+O)", self)
        self.act_open_folder.triggered.connect(self.open_folder_dialog)

        self.act_prev = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_ArrowBack), "Anterior (←)", self)
        self.act_prev.triggered.connect(self.prev_image)
        self.act_next = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_ArrowForward), "Siguiente (→)", self)
        self.act_next.triggered.connect(self.next_image)

        self.act_zoom_in = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_ArrowUp), "Zoom + (Ctrl+)", self)
        self.act_zoom_in.triggered.connect(lambda: self.apply_zoom(1.15))
        self.act_zoom_out = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_ArrowDown), "Zoom - (Ctrl-)", self)
        self.act_zoom_out.triggered.connect(lambda: self.apply_zoom(1/1.15))
        self.act_zoom_reset = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_BrowserReload), "100% (Ctrl+0)", self)
        self.act_zoom_reset.triggered.connect(self.reset_zoom)

        self.act_fit = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_DesktopIcon), "Ajustar a ventana (F)", self)
        self.act_fit.setCheckable(True)
        self.act_fit.triggered.connect(self.toggle_fit)

        self.act_rotate_left = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_ArrowBack), "Rotar -90° (L)", self)
        self.act_rotate_left.triggered.connect(lambda: self.rotate(-90))
        self.act_rotate_right = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_ArrowForward), "Rotar +90° (R)", self)
        self.act_rotate_right.triggered.connect(lambda: self.rotate(90))

        self.act_fullscreen = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_TitleBarMaxButton), "Pantalla completa (F11)", self)
        self.act_fullscreen.triggered.connect(self.toggle_fullscreen)

        self.act_slideshow = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_MediaPlay), "Presentación (Espacio)", self)
        self.act_slideshow.setCheckable(True)
        self.act_slideshow.triggered.connect(self.toggle_slideshow)

        self.act_delete = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_TrashIcon), "Eliminar (Supr)", self)
        self.act_delete.triggered.connect(self.delete_current)

        self.act_save_as = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_DialogSaveButton), "Guardar como… (Ctrl+S)", self)
        self.act_save_as.triggered.connect(self.save_as)

        self.act_quit = QtWidgets.QAction(s.standardIcon(QtWidgets.QStyle.SP_DialogCloseButton), "Salir (Ctrl+Q)", self)
        self.act_quit.triggered.connect(self.close)

    def create_menus(self):
        menu = self.menuBar()
        archivo = menu.addMenu("Archivo")
        archivo.addAction(self.act_open)
        archivo.addAction(self.act_open_folder)
        archivo.addSeparator()
        archivo.addAction(self.act_save_as)
        archivo.addSeparator()
        archivo.addAction(self.act_quit)

        ver = menu.addMenu("Ver")
        ver.addAction(self.act_prev)
        ver.addAction(self.act_next)
        ver.addSeparator()
        ver.addAction(self.act_zoom_in)
        ver.addAction(self.act_zoom_out)
        ver.addAction(self.act_zoom_reset)
        ver.addAction(self.act_fit)
        ver.addSeparator()
        ver.addAction(self.act_rotate_left)
        ver.addAction(self.act_rotate_right)
        ver.addSeparator()
        ver.addAction(self.act_fullscreen)
        ver.addAction(self.act_slideshow)

        acciones = menu.addMenu("Acciones")
        acciones.addAction(self.act_delete)

    def create_dock_toolbar(self):
        actions = [
            self.act_open_folder, self.act_open, self.act_prev, self.act_next,
            self.act_zoom_out, self.act_zoom_in, self.act_zoom_reset,
            self.act_fit, self.act_rotate_left, self.act_rotate_right,
            self.act_slideshow, self.act_fullscreen, self.act_delete
        ]

        self.dock = DockToolbar(actions)
        self.dock.setFixedHeight(80)

        container = QtWidgets.QWidget(self)
        v = QtWidgets.QVBoxLayout(container)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(0)
        v.addStretch(1)
        v.addWidget(self.dock, alignment=QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)

        # Overlay: colocar el dock flotando sobre el centro inferior
        overlay = QtWidgets.QWidget(self)
        overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        lay = QtWidgets.QVBoxLayout(overlay)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(container)

        # Stacked layout para superponer dock sobre el scroll
        stack = QtWidgets.QStackedLayout()
        w = QtWidgets.QWidget()
        w.setLayout(stack)
        stack.addWidget(self.scroll)
        stack.addWidget(overlay)
        self.setCentralWidget(w)

    def setup_shortcuts(self):
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self, activated=self.open_dialog)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+O"), self, activated=self.open_folder_dialog)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, activated=self.close)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, activated=self.save_as)

        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), self, activated=self.prev_image)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), self, activated=self.next_image)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), self, activated=self.toggle_slideshow)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl++"), self, activated=lambda: self.apply_zoom(1.15))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+-"), self, activated=lambda: self.apply_zoom(1/1.15))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+0"), self, activated=self.reset_zoom)
        QtWidgets.QShortcut(QtGui.QKeySequence("F"), self, activated=self.toggle_fit)
        QtWidgets.QShortcut(QtGui.QKeySequence("R"), self, activated=lambda: self.rotate(90))
        QtWidgets.QShortcut(QtGui.QKeySequence("L"), self, activated=lambda: self.rotate(-90))
        QtWidgets.QShortcut(QtGui.QKeySequence("F11"), self, activated=self.toggle_fullscreen)
        QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Delete), self, activated=self.delete_current)

    # ---------- Drag & Drop ----------
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e: QtGui.QDropEvent):
        urls = [u.toLocalFile() for u in e.mimeData().urls()]
        if not urls:
            return
        p = Path(urls[0])
        self.open_path(p)

    # ---------- Abrir ----------
    def open_dialog(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Abrir imágenes", str(Path.home()),
                                                          "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)")
        if files:
            self.load_files([Path(f) for f in files])

    def open_folder_dialog(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Abrir carpeta", str(Path.home()))
        if folder:
            self.open_path(Path(folder))

    def open_path(self, path: Path):
        if path.is_dir():
            files = [p for p in sorted(path.iterdir(), key=human_sort_key) if p.suffix.lower() in SUPPORTED_EXTS]
            self.load_files(files)
        else:
            self.load_files([p for p in [path] + list(Path(path.parent).iterdir()) if p.suffix.lower() in SUPPORTED_EXTS])
            # Colocar índice en el archivo inicial
            for i, p in enumerate(self.files):
                if p.resolve() == path.resolve():
                    self.index = i
                    break
            self.show_current()

    def load_files(self, files):
        self.files = [Path(f) for f in files if Path(f).exists()]
        self.index = 0 if self.files else -1
        self.populate_thumbs()
        self.show_current()

    # ---------- Miniaturas ----------
    def populate_thumbs(self):
        self.thumb_list.clear()
        for p in self.files:
            item = QtWidgets.QListWidgetItem()
            item.setToolTip(p.name)
            item.setData(QtCore.Qt.UserRole, str(p))
            # Cargar miniatura segura
            icon = self.make_thumbnail_icon(p)
            item.setIcon(icon)
            item.setText("")
            self.thumb_list.addItem(item)

    def make_thumbnail_icon(self, path: Path) -> QtGui.QIcon:
        try:
            reader = QtGui.QImageReader(str(path))
            reader.setAutoTransform(True)  # respeta orientación EXIF
            reader.setScaledSize(QtCore.QSize(160, 160))
            img = reader.read()
            if img.isNull():
                raise ValueError("No image")
            pm = QtGui.QPixmap.fromImage(img)
            return QtGui.QIcon(pm)
        except Exception:
            return self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)

    def on_thumb_clicked(self, item: QtWidgets.QListWidgetItem):
        path = Path(item.data(QtCore.Qt.UserRole))
        for i, p in enumerate(self.files):
            if p == path:
                self.index = i
                break
        self.show_current()

    # ---------- Mostrar imagen ----------
    def show_current(self):
        if not self.files:
            self.image_label.clear()
            self.statusBar().showMessage("Sin imágenes cargadas.")
            return
        self.index = max(0, min(self.index, len(self.files) - 1))
        path = self.files[self.index]

        reader = QtGui.QImageReader(str(path))
        reader.setAutoTransform(True)
        img = reader.read()
        if img.isNull():
            self.statusBar().showMessage(f"No se pudo abrir: {path.name}")
            return

        # Aplicar rotación actual
        if self.rotation_deg % 360 != 0:
            transform = QtGui.QTransform()
            transform.rotate(self.rotation_deg)
            img = img.transformed(transform, QtCore.Qt.SmoothTransformation)

        pm = QtGui.QPixmap.fromImage(img)
        self._orig_pixmap = pm
        self.scale = 1.0
        self.update_pixmap()

        self.statusBar().showMessage(f"{path.name}  ({self.index+1}/{len(self.files)})  {img.width()}×{img.height()}px")
        # Seleccionar miniatura correspondiente
        self.thumb_list.setCurrentRow(self.index)
        self.thumb_list.scrollToItem(self.thumb_list.currentItem(), QtWidgets.QAbstractItemView.PositionAtCenter)

    def update_pixmap(self):
        if not hasattr(self, '_orig_pixmap'):
            return
        pm = self._orig_pixmap

        if self.fit_to_window:
            avail = self.scroll.viewport().size() - QtCore.QSize(24, 24)
            if not pm.isNull() and avail.width() > 0 and avail.height() > 0:
                pm = pm.scaled(avail, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        else:
            if self.scale != 1.0:
                new_size = self.scale * pm.size()
                pm = pm.scaled(new_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        self.image_label.setPixmap(pm)
        self.image_label.adjustSize()

    # ---------- Navegación ----------
    def wheelEvent(self, e: QtGui.QWheelEvent):
        if e.modifiers() & QtCore.Qt.ControlModifier:
            self.apply_zoom(1.15 if e.angleDelta().y() > 0 else 1/1.15)
        else:
            if e.angleDelta().y() > 0:
                self.prev_image()
            else:
                self.next_image()

    def prev_image(self):
        if not self.files:
            return
        self.index = (self.index - 1) % len(self.files)
        self.show_current()

    def next_image(self):
        if not self.files:
            return
        self.index = (self.index + 1) % len(self.files)
        self.show_current()

    # ---------- Zoom y ajuste ----------
    def apply_zoom(self, factor: float):
        self.fit_to_window = False
        self.act_fit.setChecked(False)
        self.scale *= factor
        self.scale = max(0.05, min(self.scale, 20.0))
        self.update_pixmap()

    def reset_zoom(self):
        self.fit_to_window = False
        self.act_fit.setChecked(False)
        self.scale = 1.0
        self.update_pixmap()

    def toggle_fit(self):
        self.fit_to_window = not self.fit_to_window
        self.act_fit.setChecked(self.fit_to_window)
        self.update_pixmap()

    # ---------- Rotación ----------
    def rotate(self, deg: int):
        self.rotation_deg = (self.rotation_deg + deg) % 360
        self.update_pixmap() if hasattr(self, '_orig_pixmap') else None

    # ---------- Pantalla completa & slideshow ----------
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def toggle_slideshow(self):
        if self.slideshow_timer.isActive():
            self.slideshow_timer.stop()
            self.act_slideshow.setChecked(False)
            self.statusBar().showMessage("Presentación detenida")
        else:
            # 3s por imagen
            self.slideshow_timer.start(3000)
            self.act_slideshow.setChecked(True)
            self.statusBar().showMessage("Presentación en curso… (Espacio para detener)")

    # ---------- Guardar / Eliminar ----------
    def save_as(self):
        if not self.files:
            return
        src = self.files[self.index]
        dest, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Guardar como", str(src.with_suffix(src.suffix)))
        if dest:
            QtCore.QFile.copy(str(src), dest)
            self.statusBar().showMessage(f"Guardado en: {dest}")

    def delete_current(self):
        if not self.files:
            return
        path = self.files[self.index]
        ret = QtWidgets.QMessageBox.question(self, "Eliminar",
                                             f"¿Mover a la papelera o eliminar permanentemente?",
                                             QtWidgets.QMessageBox.StandardButton.Cancel |
                                             QtWidgets.QMessageBox.StandardButton.Yes |
                                             QtWidgets.QMessageBox.StandardButton.No,
                                             QtWidgets.QMessageBox.StandardButton.Cancel)
        # Yes = papelera (gio), No = borrar permanente
        if ret == QtWidgets.QMessageBox.Yes:
            if self.move_to_trash(path):
                self.after_delete()
        elif ret == QtWidgets.QMessageBox.No:
            if path.exists():
                try:
                    path.unlink()
                    self.after_delete()
                except Exception as e:
                    QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def move_to_trash(self, path: Path) -> bool:
        # Usa 'gio trash' si está disponible
        try:
            import shutil
            if shutil.which('gio'):
                import subprocess
                res = subprocess.run(['gio', 'trash', str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res.returncode == 0:
                    return True
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", res.stderr.decode() or "No se pudo mover a la papelera")
            else:
                QtWidgets.QMessageBox.information(self, "Papelera no disponible",
                    "No se encontró 'gio'. Se puede instalar con 'sudo apt install libglib2.0-bin'.")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
        return False

    def after_delete(self):
        removed = self.files.pop(self.index)
        self.index = max(0, min(self.index, len(self.files)-1))
        self.populate_thumbs()
        self.show_current()
        self.statusBar().showMessage(f"Eliminado: {removed.name}")

    # ---------- Mensajes ----------
    def show_welcome(self):
        if not self.files:
            self.statusBar().showMessage("Consejo: Arrastra una carpeta o pulsa Ctrl+Shift+O para abrir.")

    # ---------- Eventos ----------
    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        if self.fit_to_window:
            self.update_pixmap()

    # ---------- Cerrar ----------
    def closeEvent(self, e: QtGui.QCloseEvent):
        # Guardar geometría
        settings = QtCore.QSettings('DockImageViewer', 'DockImageViewer')
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('windowState', self.saveState())
        super().closeEvent(e)

    def showEvent(self, e: QtGui.QShowEvent):
        super().showEvent(e)
        # Restaurar geometría
        settings = QtCore.QSettings('DockImageViewer', 'DockImageViewer')
        geo = settings.value('geometry')
        if geo:
            self.restoreGeometry(geo)
        st = settings.value('windowState')
        if st:
            self.restoreState(st)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName('DockImageViewer')
    app.setOrganizationName('DockImageViewer')

    start_path = None
    if len(sys.argv) > 1:
        start_path = Path(sys.argv[1]).expanduser().resolve()

    w = ImageViewer(start_path)
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
