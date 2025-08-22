#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib
import os

class ImageViewer(Gtk.Window):
    def __init__(self):
        super().__init__(title="Visor de Imágenes GTK")
        self.set_default_size(1000, 700)

        # Caja principal vertical
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Área de imagen con scroll
        self.image = Gtk.Image()
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.image)
        vbox.pack_start(scrolled, True, True, 0)

        # Barra de herramientas estilo Dock
        dock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        dock.set_halign(Gtk.Align.CENTER)
        vbox.pack_end(dock, False, False, 10)

        # Botones de la barra
        buttons = [
            ("Abrir", Gtk.STOCK_OPEN, self.on_open),
            ("Anterior", Gtk.STOCK_GO_BACK, self.on_prev),
            ("Siguiente", Gtk.STOCK_GO_FORWARD, self.on_next),
            ("Zoom +", Gtk.STOCK_ZOOM_IN, self.on_zoom_in),
            ("Zoom -", Gtk.STOCK_ZOOM_OUT, self.on_zoom_out),
            ("Ajustar", Gtk.STOCK_ZOOM_FIT, self.on_fit),
            ("Pantalla completa", Gtk.STOCK_FULLSCREEN, self.on_fullscreen)
        ]

        for text, stock, callback in buttons:
            btn = Gtk.Button()
            img = Gtk.Image.new_from_stock(stock, Gtk.IconSize.DIALOG)
            btn.set_image(img)
            btn.set_tooltip_text(text)
            btn.connect("clicked", callback)
            dock.pack_start(btn, False, False, 0)

        # Estado de imágenes
        self.files = []
        self.index = -1
        self.scale = 1.0

    # --- Funciones principales ---
    def on_open(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Abrir imagen",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Imágenes")
        filter_img.add_mime_type("image/*")
        dialog.add_filter(filter_img)

        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            folder = os.path.dirname(path)
            self.files = [os.path.join(folder, f) for f in os.listdir(folder)
                          if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]
            self.index = self.files.index(path)
            self.show_image()
        dialog.destroy()

    def show_image(self):
        if 0 <= self.index < len(self.files):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.files[self.index])
            w = int(pixbuf.get_width() * self.scale)
            h = int(pixbuf.get_height() * self.scale)
            scaled = pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
            self.image.set_from_pixbuf(scaled)

    def on_prev(self, widget):
        if self.files:
            self.index = (self.index - 1) % len(self.files)
            self.show_image()

    def on_next(self, widget):
        if self.files:
            self.index = (self.index + 1) % len(self.files)
            self.show_image()

    def on_zoom_in(self, widget):
        self.scale *= 1.2
        self.show_image()

    def on_zoom_out(self, widget):
        self.scale /= 1.2
        self.show_image()

    def on_fit(self, widget):
        self.scale = 1.0
        self.show_image()

    def on_fullscreen(self, widget):
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

def main():
    win = ImageViewer()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
