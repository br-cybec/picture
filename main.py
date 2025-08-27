#!/usr/bin/env python3
import gi  # type: ignore
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk  # type: ignore
import os

class ImageViewer(Gtk.Window):
    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        uris = data.get_uris()
        image_files = []
        for uri in uris:
            if uri.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                filename, _ = GLib.filename_from_uri(uri)
                if filename:
                    image_files.append(filename)
        if image_files:
            folder = os.path.dirname(image_files[0])
            self.files = [os.path.join(folder, f) for f in os.listdir(folder)
                          if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))]
            self.index = self.files.index(image_files[0])
            self.show_image()
        drag_context.finish(True, False, time)
    def __init__(self):
        super().__init__(title="Visor de Imágenes Stellar PictureGTK")
        # Establecer icono de la ventana principal (después de inicializar la ventana)
        icon_app_path = os.path.join(os.path.dirname(__file__), "icons", "icon.png")
        if os.path.exists(icon_app_path):
            self.set_icon_from_file(icon_app_path)
        # Leer configuración guardada
        self.config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        tema = "oscuro"
        win_w, win_h = 1000, 700
        if os.path.exists(self.config_path):
            import configparser
            config = configparser.ConfigParser()
            config.read(self.config_path)
            tema = config.get("Apariencia", "tema", fallback="oscuro")
            win_w = config.getint("Ventana", "ancho", fallback=1000)
            win_h = config.getint("Ventana", "alto", fallback=700)
        self.set_default_size(win_w, win_h)
        # ...existing code...
        # Contenedor principal
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(self.vbox)

        # Área de imagen con scroll
        self.image = Gtk.Image()
        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.image)
        self.vbox.pack_start(scrolled, True, True, 0)

        # Barra de herramientas estilo Dock
        dock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        dock.set_halign(Gtk.Align.CENTER)
        dock.set_name("dockbar")
        self.vbox.pack_end(dock, False, False, 8)

        # Botones de la barra
        buttons = [
            ("Abrir", "abrir.png", self.on_open),
            ("Anterior", "anterior.png", self.on_prev),
            ("Siguiente", "siguiente.png", self.on_next),
            ("Zoom +", "aumentar.png", self.on_zoom_in),
            ("Zoom -", "disminuir.png", self.on_zoom_out),
            ("Ajustar", "ajustar.png", self.on_fit),
            ("Pantalla completa", "completa.png", self.on_fullscreen),
            ("Detalles", "detalles.png", self.on_details),
            ("Compartir", "compartir.png", self.on_share),
            ("Menú", "menu.png", self.on_menu)
        ]
        for text, icon_file, callback in buttons:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            icon_path = os.path.join(os.path.dirname(__file__), "icons", icon_file)
            if os.path.exists(icon_path):
                img = Gtk.Image.new_from_file(icon_path)
            else:
                img = Gtk.Image()  # Icono vacío si no existe
            btn.set_image(img)
            btn.set_tooltip_text(text)
            btn.connect("clicked", callback)
            dock.pack_start(btn, False, False, 0)

        # Estado de imágenes
        self.files = []
        self.index = -1
        self.scale = 1.0

        # Habilitar arrastrar y soltar archivos de imagen
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        targets = Gtk.TargetList.new([])
        targets.add_uri_targets(0)
        self.drag_dest_set_target_list(targets)
        self.connect("drag-data-received", self.on_drag_data_received)

        # Leer tema guardado
        self.config_path = os.path.join(os.path.dirname(__file__), "config.ini")
        tema = "oscuro"
        if os.path.exists(self.config_path):
            import configparser
            config = configparser.ConfigParser()
            config.read(self.config_path)
            tema = config.get("Apariencia", "tema", fallback="oscuro")
            self.set_theme(tema)

            # Cargar CSS externo para el dock y temas
            style_provider = Gtk.CssProvider()
            css_path = os.path.join(os.path.dirname(__file__), "style.css")
            with open(css_path, "rb") as f:
                style_provider.load_from_data(f.read())
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def on_details(self, widget):
        # Muestra detalles de la imagen actual
        if 0 <= self.index < len(self.files):
            path = self.files[self.index]
            info = os.stat(path)
            details = f"Nombre: {os.path.basename(path)}\n"
            details += f"Ruta: {path}\n"
            details += f"Tamaño: {info.st_size} bytes\n"
            details += f"Modificado: {GLib.DateTime.new_from_unix_local(info.st_mtime).format('%Y-%m-%d %H:%M:%S')}\n"
            dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.INFO,
                                      buttons=Gtk.ButtonsType.OK, text=details)
            dialog.run()
            dialog.destroy()
        else:
            dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.WARNING,
                                      buttons=Gtk.ButtonsType.OK, text="No hay imagen seleccionada.")
            dialog.run()
            dialog.destroy()
    def is_fullscreen(self):
        # Verifica si la ventana está en modo pantalla completa
        return bool(self.get_window() and self.get_window().get_state() & Gdk.WindowState.FULLSCREEN)

    def on_share(self, widget):
        # Compartir la imagen actual por email (abre cliente de correo con archivo adjunto)
        if 0 <= self.index < len(self.files):
            path = self.files[self.index]
            import subprocess
            # Intenta abrir el cliente de correo predeterminado con el archivo adjunto
            subprocess.Popen(["xdg-email", "--attach", path])
        else:
            dialog = Gtk.MessageDialog(parent=self, flags=0, type=Gtk.MessageType.WARNING,
                                      buttons=Gtk.ButtonsType.OK, message_format="No hay imagen seleccionada para compartir.")
            dialog.run()
            dialog.destroy()

    def on_menu(self, widget):
        # Muestra un menú simple con opciones
        menu = Gtk.Menu()
        item_tema = Gtk.MenuItem(label="Tema")
        submenu_tema = Gtk.Menu()
        item_tema_claro = Gtk.MenuItem(label="Claro")
        item_tema_oscuro = Gtk.MenuItem(label="Oscuro")
        item_salir = Gtk.MenuItem(label="Salir")
        item_about = Gtk.MenuItem(label="Acerca de")
        icon_about_path = os.path.join(os.path.dirname(__file__), "icons", "about.png")

        def set_theme_claro(_):
            self.set_theme("claro")
        def set_theme_oscuro(_):
            self.set_theme("oscuro")

        def show_about(_):
            about_dialog = Gtk.Dialog(title="Acerca de", parent=self, flags=0)
            about_dialog.set_default_size(400, 240)
            about_dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
            box = about_dialog.get_content_area()
            grid = Gtk.Grid()
            grid.set_row_spacing(10)
            grid.set_column_spacing(10)
            grid.set_border_width(16)
            # Imagen
            if os.path.exists(icon_about_path):
                img = Gtk.Image.new_from_file(icon_about_path)
                img.set_pixel_size(50)
                grid.attach(img, 0, 0, 1, 1)
            # Descripción
            label = Gtk.Label()
            label.set_markup(
                "<b>Stellar Picture GTK</b>\n\n"
                "Visor de Imágenes ligera y moderna para visualizar imágenes en Linux.\n"
                "Permite navegar, hacer zoom, ver detalles, cambiar tema y compartir imágenes.\n"
                "Desarrollado por B&amp;R.Comp y diseñado con IA."
            )
            label.set_justify(Gtk.Justification.CENTER)
            label.set_line_wrap(True)
            label.set_max_width_chars(40)
            label.set_size_request(320, 80)
            grid.attach(label, 0, 1, 1, 1)
            box.add(grid)
            box.show_all()
            about_dialog.run()
            about_dialog.destroy()

        item_tema_claro.connect("activate", set_theme_claro)
        item_tema_oscuro.connect("activate", set_theme_oscuro)
        item_about.connect("activate", show_about)
        submenu_tema.append(item_tema_claro)
        submenu_tema.append(item_tema_oscuro)
        submenu_tema.show_all()
        item_tema.set_submenu(submenu_tema)

        item_salir.connect("activate", lambda w: self.close())
        menu.append(item_tema)
        menu.append(item_about)
        menu.append(item_salir)
        menu.show_all()
        menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())
        menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())
    def set_theme(self, modo):
        # Guardar el tema y tamaño de ventana en config.ini
        import configparser
        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path)
        config["Apariencia"] = {"tema": modo}
        w, h = self.get_size()
        config["Ventana"] = {"ancho": str(w), "alto": str(h)}
        with open(self.config_path, "w") as f:
            config.write(f)

        # Cambia el nombre del contenedor principal para el CSS
        if modo == "claro":
            self.vbox.set_name("visor-claro")
        elif modo == "oscuro":
            self.vbox.set_name("visor-oscuro")

        # Recargar el CSS para aplicar el cambio visual
        style_provider = Gtk.CssProvider()
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        with open(css_path, "rb") as f:
            style_provider.load_from_data(f.read())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_configure_event(self, widget, event):
        # Guardar tamaño de ventana al redimensionar
        import configparser
        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path)
        tema = config.get("Apariencia", "tema", fallback="oscuro")
        w, h = self.get_size()
        config["Apariencia"] = {"tema": tema}
        config["Ventana"] = {"ancho": str(w), "alto": str(h)}
        with open(self.config_path, "w") as f:
            config.write(f)
        return False

    # No inicializar estado aquí, ya está en __init__

    # --- Funciones principales ---
    def on_open(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Abrir imagen",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Imágenes")
        filter_img.add_mime_type("image/png")
        filter_img.add_mime_type("image/jpeg")
        filter_img.add_mime_type("image/bmp")
        filter_img.add_mime_type("image/gif")
        dialog.add_filter(filter_img)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
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
            # Obtener tamaño del área de scroll
            alloc = self.image.get_allocation()
            area_w = alloc.width if alloc.width > 0 else self.get_allocated_width()
            area_h = alloc.height if alloc.height > 0 else self.get_allocated_height()
            # Escalar la imagen para ajustarse al área manteniendo proporción
            img_w, img_h = pixbuf.get_width(), pixbuf.get_height()
            scale = min(area_w / img_w, area_h / img_h, 1.0)
            w = int(img_w * scale)
            h = int(img_h * scale)
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
    win.connect("configure-event", win.on_configure_event)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
