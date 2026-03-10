
import socket
import json
import duckdb
import os
import datetime
import numpy as np

# Configuration
UDP_IP = "0.0.0.0" 
UDP_PORT = 9002
DB_PATH = "lakehouse/lakehouse_project/lakehouse.duckdb"
STINT_REPORT_PATH = "stint_report.json"

# Full schema definition (single source of truth)
SCHEMA_COLUMNS = {
    'filename': 'VARCHAR', 'driver': 'VARCHAR', 'vehicle': 'VARCHAR',
    'track': 'VARCHAR', 'session': 'VARCHAR', 'date': 'TIMESTAMP',
    'rpms': 'FLOAT', 'speedkmh': 'FLOAT', 'gear': 'FLOAT',
    'throttle': 'FLOAT', 'brake': 'FLOAT', 'steerangle': 'FLOAT',
    'g_lat': 'FLOAT', 'g_lon': 'FLOAT', 'g_vert': 'FLOAT',
    'time': 'FLOAT', 'tc': 'FLOAT', 'abs': 'FLOAT',
    'tc_value': 'FLOAT', 'abs_value': 'FLOAT', 'brake_bias': 'FLOAT',
    'packet_idx': 'UINTEGER', 'lap': 'UINTEGER',
    'sector': 'UINTEGER', 'track_position': 'FLOAT',
    'tyre_press_lf': 'FLOAT', 'tyre_press_rf': 'FLOAT',
    'tyre_press_lr': 'FLOAT', 'tyre_press_rr': 'FLOAT',
    'tyre_tair_lf': 'FLOAT', 'tyre_tair_rf': 'FLOAT',
    'tyre_tair_lr': 'FLOAT', 'tyre_tair_rr': 'FLOAT',
    'brake_temp_lf': 'FLOAT', 'brake_temp_rf': 'FLOAT',
    'brake_temp_lr': 'FLOAT', 'brake_temp_rr': 'FLOAT',
    'fuel_rem': 'FLOAT', 'tc_active': 'FLOAT', 'abs_active': 'FLOAT',
    'is_in_pit_lane': 'FLOAT',
    # Phase 3: New KPIs
    'wheel_slip_fl': 'FLOAT', 'wheel_slip_fr': 'FLOAT',
    'wheel_slip_rl': 'FLOAT', 'wheel_slip_rr': 'FLOAT',
    'car_damage_front': 'FLOAT', 'car_damage_rear': 'FLOAT',
    'car_damage_left': 'FLOAT', 'car_damage_right': 'FLOAT',
    'car_damage_centre': 'FLOAT',
    'air_temp': 'FLOAT', 'road_temp': 'FLOAT', 'water_temp': 'FLOAT',
    'tc_setting': 'FLOAT', 'tc_cut_setting': 'FLOAT',
    'abs_setting': 'FLOAT', 'engine_map': 'FLOAT',
    'best_lap_time': 'FLOAT', 'delta_lap_time': 'FLOAT',
    'fuel_per_lap': 'FLOAT',
    'wind_speed': 'FLOAT', 'wind_direction': 'FLOAT',
    'distance_traveled': 'FLOAT',
}

def migrate_schema(con):
    """Auto-migrate: add missing columns to existing table"""
    try:
        existing = con.execute("PRAGMA table_info('gold_acc_laps')").fetchall()
        existing_cols = {row[1] for row in existing}
        added = 0
        for col, dtype in SCHEMA_COLUMNS.items():
            if col not in existing_cols:
                con.execute(f"ALTER TABLE gold_acc_laps ADD COLUMN {col} {dtype}")
                added += 1
        if added:
            print(f"   📐 Schema migrated: {added} new columns added")
    except Exception:
        pass  # Table doesn't exist yet, CREATE TABLE will handle it

def main():
    print(f"🧠 ACC Data Engineer (Recorder) v3.0")
    print(f"   Listening on {UDP_PORT} | 35 KPIs | Auto-Migrate")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    con = duckdb.connect(DB_PATH)
    
    # Init DB Table with full schema
    col_defs = ', '.join(f'{col} {dtype}' for col, dtype in SCHEMA_COLUMNS.items())
    con.execute(f"CREATE TABLE IF NOT EXISTS gold_acc_laps ({col_defs})")
    
    # Auto-migrate existing tables
    migrate_schema(con)
    
    buffer = []
    
    # Stint Analysis State
    current_stint = {
        'laps': [],
        'pressures': [],
        'brake_temps': [],
        'fuel': [],
        'wear': [],
        'tc_activations': 0,
        'abs_activations': 0,
        'samples': 0,
        # Phase 5: Expert Metrics
        'omi_temps': {'i': [], 'm': [], 'o': []},
        'ride_heights': [],
        'coasting_samples': 0,
        'brake_pressures': [],
        'suspension_travel': []
    }
    
    was_in_pit = True # Assume start in pit
    start_time = datetime.datetime.now()
    session_id = f"udp_session_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    last_completed_laps = -1
    track_name = "Unknown"
    car_name = "Unknown"
    
    print("Waiting for data...")
    
    try:
        while True:
            data, addr = sock.recvfrom(65535)
            try:
                packet = json.loads(data.decode('utf-8'))
                
                # Extract metadata (Update always to support session changes)
                if packet.get('track'):
                    if packet['track'] != track_name:
                        track_name = packet['track']
                        print(f"📍 Track Detected: {track_name}")
                
                if packet.get('car'):
                    if packet['car'] != car_name:
                        car_name = packet['car']
                        print(f"🏎️ Car Detected: {car_name}")
                
                # Extract fields
                g_force = packet.get('g_force', [0.0, 0.0, 0.0])
                fuel = packet.get('fuel_rem', 0.0)
                brake_temp = packet.get('brake_temp', [0.0, 0.0, 0.0, 0.0])
                tc_value = packet.get('tc_value', 0.0)
                abs_value = packet.get('abs_value', 0.0)
                tc_active = packet.get('tc_active', 0)
                abs_active = packet.get('abs_active', 0)
                brake_bias = packet.get('brake_bias', 0.0)
                in_pit = packet.get('isInPitLane', 0)
                completed_laps = packet.get('completedLaps', 0)
                is_valid_lap = packet.get('isValidLap', 1)
                sector = packet.get('sector', 0)
                track_position = packet.get('track_position', 0.0)
                wheel_slip = packet.get('wheel_slip', [0.0, 0.0, 0.0, 0.0])
                car_damage = packet.get('car_damage', [0.0, 0.0, 0.0, 0.0, 0.0])
                
                # --- Lap Tracking ---
                if last_completed_laps == -1: # Sync
                    last_completed_laps = completed_laps

                if completed_laps > last_completed_laps:
                    lap_time_ms = packet.get('iLastTime', 0)
                    lap_time_s = lap_time_ms / 1000.0
                    if lap_time_s > 10: 
                        m, s = divmod(lap_time_s, 60)
                        status = "✅" if is_valid_lap else "❌"
                        print(f"🏁 Lap {completed_laps} Finished: {int(m):02d}:{s:06.3f} {status}")
                        
                        current_stint['laps'].append({
                            "lap": completed_laps,
                            "time": lap_time_s,
                            "isValid": bool(is_valid_lap)
                        })
                    last_completed_laps = completed_laps

                # DB Insert Row
                row = {
                    'filename': session_id,
                    'driver': os.environ.get('USER', 'Driver'),
                    'vehicle': car_name,
                    'track': track_name,
                    'session': 'PRACTICE',
                    'date': datetime.datetime.fromtimestamp(packet['timestamp']),
                    'rpms': packet['rpms'],
                    'speedkmh': packet['speedKmh'],
                    'gear': packet['gear'],
                    'throttle': packet['throttle'],
                    'brake': packet['brake'],
                    'steerangle': packet['steerAngle'],
                    'g_lat': g_force[0],
                    'g_lon': g_force[2],
                    'g_vert': g_force[1],
                    'time': packet['iCurrentTime'] / 1000.0,
                    'tc': tc_value,
                    'abs': abs_value,
                    'tc_value': tc_value,
                    'abs_value': abs_value,
                    'brake_bias': brake_bias,
                    'packet_idx': packet['packetId'],
                    'lap': completed_laps,
                    'sector': sector,
                    'track_position': track_position,
                    'tyre_press_lf': packet['tyre_press'][0],
                    'tyre_press_rf': packet['tyre_press'][1],
                    'tyre_press_lr': packet['tyre_press'][2],
                    'tyre_press_rr': packet['tyre_press'][3],
                    'tyre_tair_lf': packet['tyre_temp'][0],
                    'tyre_tair_rf': packet['tyre_temp'][1],
                    'tyre_tair_lr': packet['tyre_temp'][2],
                    'tyre_tair_rr': packet['tyre_temp'][3],
                    'brake_temp_lf': brake_temp[0],
                    'brake_temp_rf': brake_temp[1],
                    'brake_temp_lr': brake_temp[2],
                    'brake_temp_rr': brake_temp[3],
                    'fuel_rem': fuel,
                    'tc_active': tc_active,
                    'abs_active': abs_active,
                    'is_in_pit_lane': in_pit,
                    # Phase 3: New KPIs
                    'wheel_slip_fl': wheel_slip[0],
                    'wheel_slip_fr': wheel_slip[1],
                    'wheel_slip_rl': wheel_slip[2],
                    'wheel_slip_rr': wheel_slip[3],
                    'car_damage_front': car_damage[0],
                    'car_damage_rear': car_damage[1],
                    'car_damage_left': car_damage[2],
                    'car_damage_right': car_damage[3],
                    'car_damage_centre': car_damage[4],
                    'air_temp': packet.get('air_temp', 0.0),
                    'road_temp': packet.get('road_temp', 0.0),
                    'water_temp': packet.get('water_temp', 0.0),
                    'tc_setting': packet.get('tc_setting', 0),
                    'tc_cut_setting': packet.get('tc_cut_setting', 0),
                    'abs_setting': packet.get('abs_setting', 0),
                    'engine_map': packet.get('engine_map', 0),
                    'best_lap_time': packet.get('iBestTime', 0) / 1000.0,
                    'delta_lap_time': packet.get('iDeltaLapTime', 0) / 1000.0,
                    'fuel_per_lap': packet.get('fuel_per_lap', 0.0),
                    'wind_speed': packet.get('wind_speed', 0.0),
                    'wind_direction': packet.get('wind_direction', 0.0),
                    'distance_traveled': packet.get('distance_traveled', 0.0),
                }
                
                buffer.append(row)
                
                # --- Stint Logic ---
                if not in_pit:
                    was_in_pit = False
                    current_stint['samples'] += 1
                    current_stint['pressures'].append(packet['tyre_press'])
                    current_stint['brake_temps'].append(brake_temp)
                    current_stint['fuel'].append(fuel)
                    current_stint['wear'] = packet.get('tyre_wear', [0,0,0,0]) 
                    
                    omi = packet.get('tyre_temp_omi', {})
                    if omi:
                        current_stint['omi_temps']['i'].append(omi['i'])
                        current_stint['omi_temps']['m'].append(omi['m'])
                        current_stint['omi_temps']['o'].append(omi['o'])
                    
                    current_stint['ride_heights'].append(packet.get('ride_height', [0, 0]))
                    current_stint['brake_pressures'].append(packet.get('brake_press', [0,0,0,0]))
                    current_stint['suspension_travel'].append(packet.get('suspension_travel', [0,0,0,0]))
                    
                    # Coasting: Using 5% threshold as per expert advice
                    if packet['throttle'] < 0.05 and packet['brake'] < 0.05 and packet['speedKmh'] > 20:
                        current_stint['coasting_samples'] += 1
                    
                    if tc_active: current_stint['tc_activations'] += 1
                    if abs_active: current_stint['abs_activations'] += 1
                    
                    if current_stint['samples'] % 500 == 0:
                         print(f"📊 Stint Progress: {current_stint['samples']} samples | Lap {completed_laps}")

                elif in_pit and not was_in_pit:
                    # just entered pits -> End of Stint
                    was_in_pit = True
                    print(f"🛑 Pit Entry detected! Stint analysis triggered.")
                    if current_stint['samples'] > 500: 
                        analyze_stint(current_stint, track_name, car_name)
                        # Reset
                        current_stint = {
                            'laps': [], 'pressures': [], 'brake_temps': [], 
                            'fuel': [], 'wear': [], 'tc_activations': 0, 
                            'abs_activations': 0, 'samples': 0,
                            'omi_temps': {'i': [], 'm': [], 'o': []},
                            'ride_heights': [], 'coasting_samples': 0,
                            'brake_pressures': [], 'suspension_travel': []
                        }
                    else:
                        print("⚠️ Stint too short, skipping report.")
                
                # Batch Insert to DB
                if len(buffer) >= 50:
                    keys = row.keys()
                    values_list = [[r[k] for k in keys] for r in buffer]
                    placeholders = ', '.join(['?'] * len(keys))
                    query = f"INSERT INTO gold_acc_laps ({', '.join(keys)}) VALUES ({placeholders})"
                    con.executemany(query, values_list)
                    buffer = []
                    
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"Error processing: {e}")
                
    except KeyboardInterrupt:
        con.close()

def analyze_stint(data, track, car):
    """Calculates averages and saves JSON report"""
    try:
        if data['samples'] < 10 or len(data['ride_heights']) == 0:
            print("⚠️ Insufficient data for analysis (Empty Stint).")
            return

        # Averages
        pressures = np.array(data['pressures']) if len(data['pressures']) > 0 else np.zeros((1, 4))
        brake_temps = np.array(data['brake_temps']) if len(data['brake_temps']) > 0 else np.zeros((1, 4))
        
        avg_press = np.mean(pressures, axis=0) # [lf, rf, lr, rr]
        avg_brake = np.mean(brake_temps, axis=0)
        max_brake = np.max(brake_temps, axis=0)
        
        fuel_used = data['fuel'][0] - data['fuel'][-1] if len(data['fuel']) > 0 else 0
        
        # Phase 5: Advanced KPI Calculations
        # OMI Delta (Inside - Outside)
        if len(data['omi_temps']['i']) > 0:
            omi_i = np.mean(data['omi_temps']['i'], axis=0)
            omi_o = np.mean(data['omi_temps']['o'], axis=0)
            omi_delta = omi_i - omi_o # [lf, rf, lr, rr]
        else:
            omi_delta = [0, 0, 0, 0]
        
        # Rake (Rear RH - Front RH)
        rhs = np.array(data['ride_heights'])
        if len(rhs) > 0 and rhs.shape[1] >= 2:
            avg_rhs = np.mean(rhs, axis=0)
            rake = avg_rhs[1] - avg_rhs[0] # Rear - Front
        else:
            rake = 0.0
        
        # Coasting %
        coasting_pct = (data['coasting_samples'] / data['samples']) * 100 if data['samples'] > 0 else 0
        
        # Suspension Stats
        susp_travel = np.array(data.get('suspension_travel', []))
        avg_susp = np.mean(susp_travel, axis=0) if len(susp_travel) > 0 else [0,0,0,0]
        
        # --- Phase 7: Pace & Consistency ---
        valid_laps = [l['time'] for l in data['laps'] if l['isValid']]
        
        if len(valid_laps) > 0:
            best_lap = min(valid_laps)
            # Consistency (Std Dev of last 5 valid laps)
            recent_laps = valid_laps[-5:]
            consistency = np.std(recent_laps) if len(recent_laps) > 1 else 0.0
            avg_pace = np.mean(recent_laps)
        else:
            best_lap = 0.0
            consistency = 0.0
            avg_pace = 0.0

        # Calculate Theoretical Best (Optimal Sectors) - Placeholder logic as sectors aren't fully tracked yet
        # For now we use Best Lap as reference
        
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "track": track,
            "car": car,
            "laps": data['laps'],
            "summary": {
                "lap_count": len(data['laps']),
                "best_lap": best_lap,
                "avg_pace": round(avg_pace, 3),
                "consistency": round(consistency, 3),
                "coasting_pct": round(coasting_pct, 1),
                "rake_avg_mm": round(rake, 2),
                "avg_susp_travel": [round(x, 2) for x in avg_susp]
            },
            "tyres": {
                "avg_pressure_psi": {
                    "fl": round(avg_press[0], 2), "fr": round(avg_press[1], 2),
                    "rl": round(avg_press[2], 2), "rr": round(avg_press[3], 2)
                },
                "wear": {
                    "fl": round(data['wear'][0], 2), "fr": round(data['wear'][1], 2),
                    "rl": round(data['wear'][2], 2), "rr": round(data['wear'][3], 2)
                },
                "omi_delta": {
                    "fl": round(omi_delta[0], 1), "fr": round(omi_delta[1], 1),
                    "rl": round(omi_delta[2], 1), "rr": round(omi_delta[3], 1)
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
                "total_used": round(fuel_used, 2)
            },
            "electronics": {
                "abs_triggers": data['abs_activations'],
                "tc_triggers": data['tc_activations']
            }
        }
        
        with open(STINT_REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=4)
            
        print(f"✅ Report saved to {STINT_REPORT_PATH}")
        print(f"   Avg Pressures: {report['tyres']['avg_pressure_psi']}")
        
    except Exception as e:
        print(f"❌ Error analyzing stint: {e}")

if __name__ == "__main__":
    main()
