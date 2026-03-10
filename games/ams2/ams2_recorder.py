"""
Automobilista 2 Telemetry Recorder + AI Crew Engine
Listens on UDP 5607 for JSON packets from Windows forwarder.
"""

import socket
import duckdb
import os
import sys
import datetime
import time
import json

UDP_IP = "0.0.0.0"
UDP_PORT = 5607 # Port for SHM JSON
DB_PATH = "/home/diegokernel/proyectos/lakehouse/lakehouse_project/lakehouse.duckdb"

SCHEMA_COLUMNS = {
    'session_id': 'VARCHAR',
    'timestamp': 'TIMESTAMP',
    'speed_kmh': 'FLOAT',
    'rpm': 'UINTEGER',
    'gear': 'INTEGER',
    'throttle': 'FLOAT',
    'brake': 'FLOAT',
    'steering': 'FLOAT',
    'fuel': 'FLOAT',
    'odometer_km': 'FLOAT',
    'tyre_temp_lf': 'FLOAT', 'tyre_temp_rf': 'FLOAT',
    'tyre_temp_lr': 'FLOAT', 'tyre_temp_rr': 'FLOAT',
    'brake_temp_lf': 'FLOAT', 'brake_temp_rf': 'FLOAT',
    'brake_temp_lr': 'FLOAT', 'brake_temp_rr': 'FLOAT',
    'is_in_pit': 'BOOLEAN',
    'game_state': 'UINTEGER'
}

STINT_REPORT_PATH = "/home/diegokernel/proyectos/stint_report_ams2.json"

def migrate_schema(con, table_name):
    try:
        existing = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        existing_cols = {row[1] for row in existing}
        for col, dtype in SCHEMA_COLUMNS.items():
            if col not in existing_cols:
                con.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {dtype}")
                print(f"📐 Added column {col}")
    except Exception as e:
        print(f"⚠️ Schema migration warning: {e}")

def analyze_stint(data):
    """Calcula promedios y guarda reporte JSON para la IA"""
    import numpy as np
    try:
        if data['samples'] < 50: # Reducido para testing
            print("⚠️ Stint demasiado corto para análisis.")
            return
        
        avg_press = np.mean(data['tyre_temps'], axis=0) if data['tyre_temps'] else [0,0,0,0]
        avg_brake = np.mean(data['brake_temps'], axis=0) if data['brake_temps'] else [0,0,0,0]
        max_brake = np.max(data['brake_temps'], axis=0) if data['brake_temps'] else [0,0,0,0]
        
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "track": "Unknown (AMS2)",
            "car": "Unknown (AMS2)",
            "summary": {
                "samples": data['samples'],
                "coasting_pct": round((data['coasting_samples'] / data['samples']) * 100, 1) if data['samples'] > 0 else 0
            },
            "tyres": {
                "avg_temp_c": {
                    "fl": round(avg_press[0], 1), "fr": round(avg_press[1], 1),
                    "rl": round(avg_press[2], 1), "rr": round(avg_press[3], 1)
                }
            },
            "brakes": {
                "avg_temp_c": {
                    "fl": round(avg_brake[0], 1), "fr": round(avg_brake[1], 1),
                    "rl": round(avg_brake[2], 1), "rr": round(avg_brake[3], 1)
                },
                "max_temp_c": {
                    "fl": round(max_brake[0], 1), "fr": round(max_brake[1], 1),
                    "rl": round(max_brake[2], 1), "rr": round(max_brake[3], 1)
                }
            },
            "fuel": {
                "total_used": round(data['fuel'][0] - data['fuel'][-1], 2) if len(data['fuel']) > 1 else 0
            }
        }
        
        with open(STINT_REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=4)
        print(f"✅ Stint Report guardado en {STINT_REPORT_PATH}")
    except Exception as e:
        print(f"❌ Error analizando stint: {e}")

def get_db_con():
    """Intenta conectar a la DB con reintentos si está bloqueada"""
    for _ in range(5):
        try:
            return duckdb.connect(DB_PATH)
        except Exception:
            time.sleep(1)
    return duckdb.connect(DB_PATH) # Último intento sin catch para ver error real

def main():
    print("🏎️ AMS2 Telemetry Recorder + AI Crew Engine")
    print(f"   Listening on UDP {UDP_PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    table_name = 'gold_ams2_laps'
    
    # Init DB
    con = get_db_con()
    con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (session_id VARCHAR)")
    migrate_schema(con, table_name)
    con.close()
    
    session_id = f"ams2_prod_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    buffer = []
    
    # Stint State
    stint_data = {
        'samples': 0, 'tyre_temps': [], 'brake_temps': [], 
        'fuel': [], 'coasting_samples': 0
    }
    was_in_pit = True
    
    print("⏳ Waiting for data...")
    
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            try:
                packet = json.loads(data.decode('utf-8'))
            except: continue
            
            in_pit = packet.get('is_in_pit', False)
            game_state = packet.get('game_state', 0)
            
            # Recolectar datos si estamos en pista (State 2 = In Race)
            if not in_pit and game_state == 2:
                was_in_pit = False
                stint_data['samples'] += 1
                stint_data['tyre_temps'].append(packet.get('tyre_temp', [0,0,0,0]))
                stint_data['brake_temps'].append(packet.get('brake_temp', [0,0,0,0]))
                stint_data['fuel'].append(packet.get('fuel', 0.0))
                
                throttle = packet.get('throttle', 0.0)
                brake = packet.get('brake', 0.0)
                speed = packet.get('speed_kmh', 0.0)
                if throttle < 0.05 and brake < 0.05 and speed > 30:
                    stint_data['coasting_samples'] += 1
            
            # Detectar entrada a pits -> Fin de Stint
            elif in_pit and not was_in_pit:
                was_in_pit = True
                print("🛑 Pit Entry! Generando reporte de stint...")
                analyze_stint(stint_data)
                stint_data = {'samples': 0, 'tyre_temps': [], 'brake_temps': [], 'fuel': [], 'coasting_samples': 0}

            # Preparar fila para DB
            tyre_temp = packet.get('tyre_temp', [0,0,0,0])
            brake_temp = packet.get('brake_temp', [0,0,0,0])
            
            row = {
                'session_id': session_id,
                'timestamp': datetime.datetime.now(),
                'speed_kmh': packet.get('speed_kmh', 0.0),
                'rpm': int(packet.get('rpm', 0)),
                'gear': packet.get('gear', 0),
                'throttle': packet.get('throttle', 0.0),
                'brake': packet.get('brake', 0.0),
                'steering': packet.get('steering', 0.0),
                'fuel': packet.get('fuel', 0.0),
                'odometer_km': packet.get('odometer_km', 0.0),
                'tyre_temp_lf': tyre_temp[0] if len(tyre_temp) > 0 else 0,
                'tyre_temp_rf': tyre_temp[1] if len(tyre_temp) > 1 else 0,
                'tyre_temp_lr': tyre_temp[2] if len(tyre_temp) > 2 else 0,
                'tyre_temp_rr': tyre_temp[3] if len(tyre_temp) > 3 else 0,
                'brake_temp_lf': brake_temp[0] if len(brake_temp) > 0 else 0,
                'brake_temp_rf': brake_temp[1] if len(brake_temp) > 1 else 0,
                'brake_temp_lr': brake_temp[2] if len(brake_temp) > 2 else 0,
                'brake_temp_rr': brake_temp[3] if len(brake_temp) > 3 else 0,
                'is_in_pit': in_pit,
                'game_state': game_state
            }
            
            buffer.append(row)
            
            if len(buffer) >= 100:
                con = get_db_con()
                keys = row.keys()
                vals = [tuple(r[k] for k in keys) for r in buffer]
                placeholders = ', '.join(['?' for _ in keys])
                con.executemany(f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})", vals)
                con.close()
                buffer.clear()
                
    except KeyboardInterrupt:
        if buffer:
            con = get_db_con()
            keys = row.keys()
            vals = [tuple(r[k] for k in keys) for r in buffer]
            placeholders = ', '.join(['?' for _ in keys])
            con.executemany(f"INSERT INTO {table_name} ({', '.join(keys)}) VALUES ({placeholders})", vals)
            con.close()

if __name__ == '__main__':
    main()
