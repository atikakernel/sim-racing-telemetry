#!/bin/bash

# Activar venv
source /home/diegokernel/proyectos/venv/bin/activate

# Limpieza agresiva de procesos previos
echo "🧹 Cleaning up old processes..."
pkill -f ams2_recorder.py
pkill -f app_ams2.py
sleep 1

cleanup() {
    echo "🛑 Stopping..."
    kill $REC_PID
    kill $APP_PID
    exit
}

trap cleanup SIGINT

echo "🏎️ Starting AMS2 Telemetry..."
echo "   Please set AMS2 System > UDP > Protocol: 'Project CARS 2', Frequency: 1"

python3 games/ams2/ams2_recorder.py &
REC_PID=$!

sleep 2

streamlit run apps/app_ams2.py &
APP_PID=$!

wait
