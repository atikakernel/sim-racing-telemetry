#!/bin/bash

# Activar entorno virtual
source /home/diegokernel/proyectos/venv/bin/activate

# Función para matar procesos al salir
cleanup() {
    echo "🛑 Deteniendo Ingeniero Virtual..."
    kill $RECORDER_PID
    kill $STREAMLIT_PID
    exit
}

trap cleanup SIGINT

echo "🏎️  Iniciando Ingeniero Virtual de ACC..."

# 1. Iniciar Recorder (en segundo plano)
echo "🎧 Iniciando Grabador de Telemetría (Recorder)..."
python3 scripts/acc_recorder_v2.py &
RECORDER_PID=$!

sleep 2

# 2. Iniciar Dashboard (Streamlit)
echo "📊 Iniciando Dashboard..."
streamlit run apps/app_acc.py &
STREAMLIT_PID=$!

echo "✅ Todo listo. Presiona Ctrl+C para detener ambos."
wait
