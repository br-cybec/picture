#!/bin/bash
# run.sh - Script de ejecución para el visor de imágenes GTK

# Nombre del archivo principal
APP="dock_image_viewer.py"

# Dependencias requeridas
DEPS=("python3-gi" "gir1.2-gtk-3.0" "python3-pil")

check_and_install() {
    MISSING=0
    for dep in "${DEPS[@]}"; do
        dpkg -s "$dep" &> /dev/null
        if [ $? -ne 0 ]; then
            echo "❌ Falta dependencia: $dep"
            MISSING=1
        else
            echo "✅ $dep ya está instalado"
        fi
    done

    if [ $MISSING -eq 1 ]; then
        echo "⚙️ Instalando dependencias..."
        sudo apt-get update
        sudo apt-get install -y "${DEPS[@]}"
    else
        echo "🔹 Todas las dependencias están instaladas."
    fi
}

# Verificar dependencias
check_and_install

# Ejecutar la app
echo "🚀 Ejecutando $APP..."
python3 "$APP" "$@"
