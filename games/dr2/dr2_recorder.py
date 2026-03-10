"""
Dirt Rally 2.0 - Telemetry Recorder
Listens for DR2 UDP packets (264 bytes) and stores to DuckDB.
No forwarder needed — DR2 sends UDP directly.

Usage:
  python3 games/dr2/dr2_recorder.py
"""

import socket
import os
import sys
import datetime
import json
import time
import duckdb

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from games.dr2.dr2_structs import parse_packet, DR2_PACKET_SIZE

# Configuration
UDP_IP = "0.0.0.0"
UDP_PORT = 20777
DB_PATH = "lakehouse/lakehouse_project/lakehouse.duckdb"
STAGE_REPORT_PATH = "dr2_stage_report.json"

# Schema definition (single source of truth)
SCHEMA_COLUMNS = {
    'session_id': 'VARCHAR',
    'date': 'TIMESTAMP',
    'stage_time': 'FLOAT',
    'stage_distance': 'FLOAT',
    'total_distance': 'FLOAT',
    'speed_kmh': 'FLOAT',
    'rpm': 'FLOAT',
    'gear': 'FLOAT',
    'throttle': 'FLOAT',
    'brake': 'FLOAT',
    'steer': 'FLOAT',
    'clutch': 'FLOAT',
    'handbrake': 'FLOAT',
    'g_force_lat': 'FLOAT',
    'g_force_lon': 'FLOAT',
    'pos_x': 'FLOAT',
    'pos_y': 'FLOAT',
    'pos_z': 'FLOAT',
    'susp_pos_fl': 'FLOAT',
    'susp_pos_fr': 'FLOAT',
    'susp_pos_rl': 'FLOAT',
    'susp_pos_rr': 'FLOAT',
    'susp_vel_fl': 'FLOAT',
    'susp_vel_fr': 'FLOAT',
    'susp_vel_rl': 'FLOAT',
    'susp_vel_rr': 'FLOAT',
    'wheel_speed_fl': 'FLOAT',
    'wheel_speed_fr': 'FLOAT',
    'wheel_speed_rl': 'FLOAT',
    'wheel_speed_rr': 'FLOAT',
    'slip_fl': 'FLOAT',
    'slip_fr': 'FLOAT',
    'slip_rl': 'FLOAT',
    'slip_rr': 'FLOAT',
    'brake_temp_fl': 'FLOAT',
    'brake_temp_fr': 'FLOAT',
    'brake_temp_rl': 'FLOAT',
    'brake_temp_rr': 'FLOAT',
    'air_temp': 'FLOAT',
    'turbo_pressure': 'FLOAT',
    'current_lap': 'FLOAT',
    'track_length': 'FLOAT',
    'sample_idx': 'UINTEGER',
}

def migrate_schema(con, table_name):
    """Auto-migrate: add missing columns to existing table"""
    try:
        existing = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        existing_cols = {row[1] for row in existing}
        added = 0
        for col, dtype in SCHEMA_COLUMNS.items():
            if col not in existing_cols:
                con.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {dtype}")
                added += 1
        if added:
            print(f"   📐 Schema migrated: {added} new columns added")
    except Exception:
        pass


def main():
    print("🏁 DR2 Telemetry Recorder v1.0")
    print(f"   Listening on UDP {UDP_PORT} | Direct from game")
    print(f"   Expected packet size: {DR2_PACKET_SIZE} bytes")
    print()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    con = duckdb.connect(DB_PATH)
    
    # Init DB
    table_name = 'gold_dr2_stages'
    col_defs = ', '.join(f'{col} {dtype}' for col, dtype in SCHEMA_COLUMNS.items())
    con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})")
    migrate_schema(con, table_name)
    
    # State
    buffer = []
    session_id = f"dr2_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    sample_idx = 0
    last_distance = 0.0
    stage_started = False
    max_speed = 0.0
    total_samples = 0
    
    # Stage report
    stage_report = {
        'game': 'Dirt Rally 2.0',
        'session_id': session_id,
        'start_time': datetime.datetime.now().isoformat(),
        'stages': [],
        'current_stage': {
            'max_speed_kmh': 0,
            'avg_speed_kmh': 0,
            'max_g_lat': 0,
            'max_g_lon': 0,
            'samples': 0,
            'speed_sum': 0,
            'gear_distribution': {},
            'handbrake_count': 0,
        }
    }
    
    print("⏳ Esperando datos de Dirt Rally 2.0...")
    print(f"   Config en Windows: C:\\Users\\diean\\OneDrive\\Documentos\\My Games\\DiRT Rally 2.0")
    print(f"   Verifica: <udp enabled=\"true\" extradata=\"3\" ip=\"TU_WSL_IP\" port=\"{UDP_PORT}\" />")
    print()
    
    try:
        while True:
            data, addr = sock.recvfrom(512)
            
            if len(data) < DR2_PACKET_SIZE:
                continue
            
            packet = parse_packet(data)
            if packet is None:
                continue
            
            # Detect stage start (distance > 0 and increasing)
            if packet['lap_distance'] > 0 and not stage_started:
                stage_started = True
                print(f"🚗 Stage started! Track length: {packet['track_length']:.0f}m")
                session_id = f"dr2_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                sample_idx = 0
                max_speed = 0
                stage_report['current_stage'] = {
                    'max_speed_kmh': 0, 'avg_speed_kmh': 0,
                    'max_g_lat': 0, 'max_g_lon': 0,
                    'samples': 0, 'speed_sum': 0,
                    'gear_distribution': {}, 'handbrake_count': 0,
                    'track_length': packet['track_length'],
                }
            
            # Detect stage end (distance reset or time stopped)
            if stage_started and packet['lap_distance'] < last_distance - 10:
                stage_time = packet['lap_time']
                cs = stage_report['current_stage']
                avg_spd = cs['speed_sum'] / max(cs['samples'], 1)
                
                m, s = divmod(stage_time, 60)
                print(f"🏁 Stage finished! Time: {int(m):02d}:{s:06.3f} | Top: {cs['max_speed_kmh']:.1f} km/h | Avg: {avg_spd:.1f} km/h")
                
                cs['avg_speed_kmh'] = round(avg_spd, 1)
                cs['stage_time'] = stage_time
                stage_report['stages'].append(cs.copy())
                
                # Save report
                with open(STAGE_REPORT_PATH, 'w') as f:
                    json.dump(stage_report, f, indent=2, default=str)
                
                # Flush buffer
                if buffer:
                    cols = list(SCHEMA_COLUMNS.keys())
                    placeholders = ', '.join(['?' for _ in cols])
                    col_names = ', '.join(cols)
                    con.executemany(
                        f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                        [tuple(row[c] for c in cols) for row in buffer]
                    )
                    print(f"   💾 Saved {len(buffer)} samples to DuckDB")
                    buffer.clear()
                
                stage_started = False
            
            last_distance = packet['lap_distance']
            
            if not stage_started:
                continue
            
            # Update stats
            sample_idx += 1
            cs = stage_report['current_stage']
            cs['samples'] += 1
            cs['speed_sum'] += packet['speed_kmh']
            cs['max_speed_kmh'] = max(cs['max_speed_kmh'], packet['speed_kmh'])
            cs['max_g_lat'] = max(cs['max_g_lat'], abs(packet['g_force_lat']))
            cs['max_g_lon'] = max(cs['max_g_lon'], abs(packet['g_force_lon']))
            
            gear = int(packet['gear_display'])
            gear_str = str(gear)
            cs['gear_distribution'][gear_str] = cs['gear_distribution'].get(gear_str, 0) + 1
            if packet['handbrake'] > 0.3:
                cs['handbrake_count'] += 1
            
            # Print periodic update
            if sample_idx % 300 == 0:
                progress = (packet['lap_distance'] / max(packet['track_length'], 1)) * 100
                print(f"   📍 {progress:.0f}% | {packet['speed_kmh']:.0f} km/h | G{gear} | G-lat: {packet['g_force_lat']:.2f}")
            
            # Build row
            row = {
                'session_id': session_id,
                'date': datetime.datetime.now(),
                'stage_time': packet['lap_time'],
                'stage_distance': packet['lap_distance'],
                'total_distance': packet['total_distance'],
                'speed_kmh': packet['speed_kmh'],
                'rpm': packet['rpm'],
                'gear': packet['gear_display'],
                'throttle': packet['throttle'],
                'brake': packet['brake'],
                'steer': packet['steer'],
                'clutch': packet['clutch'],
                'handbrake': packet['handbrake'],
                'g_force_lat': packet['g_force_lat'],
                'g_force_lon': packet['g_force_lon'],
                'pos_x': packet['pos_x'],
                'pos_y': packet['pos_y'],
                'pos_z': packet['pos_z'],
                'susp_pos_fl': packet['susp_pos_fl'],
                'susp_pos_fr': packet['susp_pos_fr'],
                'susp_pos_rl': packet['susp_pos_rl'],
                'susp_pos_rr': packet['susp_pos_rr'],
                'susp_vel_fl': packet['susp_vel_fl'],
                'susp_vel_fr': packet['susp_vel_fr'],
                'susp_vel_rl': packet['susp_vel_rl'],
                'susp_vel_rr': packet['susp_vel_rr'],
                'wheel_speed_fl': packet['wheel_speed_fl'],
                'wheel_speed_fr': packet['wheel_speed_fr'],
                'wheel_speed_rl': packet['wheel_speed_rl'],
                'wheel_speed_rr': packet['wheel_speed_rr'],
                'slip_fl': packet['slip_fl'],
                'slip_fr': packet['slip_fr'],
                'slip_rl': packet['slip_rl'],
                'slip_rr': packet['slip_rr'],
                'brake_temp_fl': packet['brake_temp_fl'],
                'brake_temp_fr': packet['brake_temp_fr'],
                'brake_temp_rl': packet['brake_temp_rl'],
                'brake_temp_rr': packet['brake_temp_rr'],
                'air_temp': packet['air_temp'],
                'turbo_pressure': packet['turbo_pressure'],
                'current_lap': packet['current_lap'],
                'track_length': packet['track_length'],
                'sample_idx': sample_idx,
            }
            
            buffer.append(row)
            
            # Batch insert every 500 samples
            if len(buffer) >= 500:
                cols = list(SCHEMA_COLUMNS.keys())
                placeholders = ', '.join(['?' for _ in cols])
                col_names = ', '.join(cols)
                con.executemany(
                    f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                    [tuple(row[c] for c in cols) for row in buffer]
                )
                total_samples += len(buffer)
                buffer.clear()
    
    except KeyboardInterrupt:
        # Flush remaining
        if buffer:
            cols = list(SCHEMA_COLUMNS.keys())
            placeholders = ', '.join(['?' for _ in cols])
            col_names = ', '.join(cols)
            con.executemany(
                f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                [tuple(row[c] for c in cols) for row in buffer]
            )
            total_samples += len(buffer)
        
        # Save final report
        with open(STAGE_REPORT_PATH, 'w') as f:
            json.dump(stage_report, f, indent=2, default=str)
        
        print(f"\n🛑 Recorder stopped. Total samples: {total_samples}")
        con.close()


if __name__ == '__main__':
    main()
