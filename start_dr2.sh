#!/bin/bash

# Activar entorno virtual
source /home/diegokernel/proyectos/venv/bin/activate

# Función para matar procesos al salir
cleanup() {
    echo "🛑 Deteniendo DR2 Telemetry..."
    kill $RECORDER_PID
    kill $STREAMLIT_PID
    exit
}

trap cleanup SIGINT

echo "🏁 Iniciando Dirt Rally 2.0 Telemetry..."
echo ""
echo "📋 Config en Windows:"
echo "   C:\Users\diean\OneDrive\Documentos\My Games\DiRT Rally 2.0\hardwaresettings\hardware_settings_config.xml"
echo "   <udp enabled=\"true\" extradata=\"3\" ip=\"TU_WSL_IP\" port=\"20777\" delay=\"1\" />"
echo ""

# 1. Iniciar Recorder (en segundo plano)
echo "🎧 Iniciando DR2 Recorder..."
python3 games/dr2/dr2_recorder.py &
RECORDER_PID=$!

sleep 2

# 2. Iniciar Dashboard (Streamlit)
echo "📊 Iniciando Dashboard DR2..."
streamlit run apps/app_dr2.py &
STREAMLIT_PID=$!

echo ""
echo "✅ Todo listo. Presiona Ctrl+C para detener ambos."
wait
