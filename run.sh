#!/bin/bash

# Otorgar permisos de ejecución al propio script
chmod +x "$0"

# Verificar si python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "Instalando python3..."
    apt update && apt install -y python3
fi

# Verificar si gi está instalado
if ! command -v python3-gi &> /dev/null; then
    echo "Instalando python3-gi..."
    apt install -y python3-gi 
fi

# Verificar si ffmpeg está instalado
if ! command -v gir1.2-gtk-3.0 &> /dev/null; then
    echo "Instalando gir1.2-gtk-3.0..."
    apt install -y gir1.2-gtk-3.0
fi

# Verificar si PyGObject está instalado
python3 -c "import gi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Instalando PyGObject..."
    pip3 install PyGObject
fi

# Ejecutar el programa principal
exec python3 "$(dirname "$0")/main.py"

