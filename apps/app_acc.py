#!/usr/bin/env python3
"""
🏎️ ACC Telemetry Dashboard v3 - Pro Racing Analysis
=====================================================
Dashboard profesional con análisis avanzado para convertirte en el mejor piloto.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb
import subprocess
import os
import json
import glob
import requests
import re
import time
import datetime
import concurrent.futures
import asyncio
from google import genai
try:
    from scipy.signal import find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="🏎️ ACC Pro Racing",
    layout="wide",
    page_icon="🏁",
    initial_sidebar_state="expanded"
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../lakehouse/lakehouse_project/lakehouse.duckdb")
MODELO_IA = "deepseek-r1:14b"
GEMINI_MODEL = "gemini-3-pro-preview"
LIVE_DATA_FILE = "../data/live_data.json"

# --- SAFETY LIMITS (solo datos críticos de seguridad) ---
ACC_CAR_SAFETY = {
    # GT4 - Motor central/trasero
    'audi_r8_gt4': 52, 'ktm_xbow_gt4': 52, 'mclaren_570s_gt4': 52,
    'porsche_718_gt4': 52, 'alpine_a110_gt4': 52,
    # GT4 - Motor delantero (más tolerantes)
    'bmw_m4_gt4': 48, 'chevrolet_camaro_gt4': 48, 'ginetta_g55_gt4': 48,
    'maserati_mc_gt4': 48, 'mercedes_amg_gt4': 48,
    # GT3 - Motor central/trasero
    'audi_r8_lms': 52, 'audi_r8_lms_evo': 52, 'audi_r8_lms_evo_ii': 52,
    'ferrari_488_gt3': 52, 'ferrari_488_gt3_evo': 52, 'ferrari_296_gt3': 52,
    'honda_nsx_gt3': 52, 'honda_nsx_gt3_evo': 52,
    'lamborghini_huracan_gt3': 52, 'lamborghini_huracan_gt3_evo': 52, 'lamborghini_huracan_gt3_evo2': 52,
    'mclaren_720s_gt3': 52, 'mclaren_720s_gt3_evo': 52,
    # GT3 - Motor delantero
    'bmw_m4_gt3': 48, 'bmw_m6_gt3': 48, 'mercedes_amg_gt3': 48, 'mercedes_amg_gt3_evo': 48,
    'nissan_gt_r_gt3': 48, 'bentley_continental_gt3': 48, 'lexus_rc_f_gt3': 48,
    'aston_martin_v8_gt3': 48, 'aston_martin_v12_gt3': 48, 'jaguar_g3': 48,
    # GT3 - Motor trasero (Porsche = más restrictivo)
    'porsche_991_gt3_r': 54, 'porsche_991ii_gt3_r': 54, 'porsche_992_gt3_r': 54,
}

def get_car_context(car_name):
    """Genera contexto de seguridad del coche"""
    min_bias = ACC_CAR_SAFETY.get(car_name, 50)  # default conservador
    return min_bias

def get_safety_block(car_name, track_name):
    """Bloque de seguridad + contexto para que Gemini use su conocimiento"""
    min_bias = get_car_context(car_name)
    car_display = car_name.replace('_', ' ').title()
    track_display = track_name.replace('_', ' ').title()
    
    return f"""[COCHE Y PISTA]
Coche: {car_display} | Pista: {track_display}
IMPORTANTE: Usa tu conocimiento sobre este coche específico (posición del motor, tracción, 
distribución de peso, comportamiento dinámico) y sobre esta pista (tipo, curvas clave, 
zonas de frenada, sectores rápidos/lentos). Adapta tus recomendaciones a las características 
REALES del coche y la pista.

[REGLAS DE SEGURIDAD - OBLIGATORIAS]
- Brake Bias: NUNCA menor a {min_bias}% para este coche
- Piloto INTERMEDIO (no alien). Cambios GRADUALES:
  * Brake Bias: máx ±2% por sesión
  * Presiones: máx ±1.0 PSI por sesión
  * Camber: máx ±0.5\u00B0 por sesión
  * ARB/Alerón: máx ±2 clicks por sesión
- Si un parámetro ya está en su LÍMITE (ej: alerón en 0), NO bajarlo más"""

# Gemini client
GEMINI_AVAILABLE = False
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    # Fallback to Streamlit secrets
    if not api_key:
        try:
            # Debug: Print secrets (Masked)
            # st.write("Secrets keys available:", list(st.secrets.keys()))
            api_key = st.secrets["general"]["GEMINI_API_KEY"] # TOML structure
        except KeyError:
            try:
                 api_key = st.secrets["GEMINI_API_KEY"] # Flat structure fallback
            except:
                pass
            
    if not api_key:
        print("⚠️ GEMINI_API_KEY not found in environment variables or secrets.")
        GEMINI_AVAILABLE = False
    else:
        gemini_client = genai.Client(api_key=api_key)
        GEMINI_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Error initializing Gemini: {e}")
    GEMINI_AVAILABLE = False

# --- ESTILOS ---
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%); }
    div.stButton > button { width: 100%; border-radius: 8px; font-weight: bold; }
    .best-lap { color: #00ff88; font-weight: bold; }
    .slow-lap { color: #ff4444; }
</style>
""", unsafe_allow_html=True)

# --- DATA LAYER ---
SETUPS_PATH = "/mnt/c/Users/diean/OneDrive/Documentos/Assetto Corsa Competizione/Setups"

def get_db_connection():
    return duckdb.connect(DB_PATH, read_only=True)

def load_live_data():
    """Lee el estado en vivo desde el JSON generado por acc_recorder_v2.py"""
    try:
        if not os.path.exists(LIVE_DATA_FILE):
            return None
        with open(LIVE_DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def get_available_setups(car, track):
    """Lista todos los setups disponibles para un coche/pista"""
    try:
        setup_dir = os.path.join(SETUPS_PATH, car, track)
        json_files = glob.glob(os.path.join(setup_dir, "*.json"))
        if not json_files:
            return []
        # Ordenar por fecha de modificación (más reciente primero)
        return sorted(json_files, key=os.path.getmtime, reverse=True)
    except:
        return []

def load_acc_setup(car, track, setup_file=None):
    """Lee el setup JSON de ACC. Si se pasa setup_file, lee ese; si no, el más reciente."""
    try:
        if setup_file:
            target = setup_file
        else:
            setup_dir = os.path.join(SETUPS_PATH, car, track)
            json_files = glob.glob(os.path.join(setup_dir, "*.json"))
            if not json_files:
                return None
            target = max(json_files, key=os.path.getmtime)
        
        with open(target, 'r') as f:
            setup = json.load(f)
        return setup
    except:
        return None

def get_current_setup():
    """Lee el setup 'current.json' que es el que el usuario tiene activo en el coche."""
    try:
        current_path = "/mnt/c/Users/diean/OneDrive/Documentos/Assetto Corsa Competizione/Config/current.json"
        if os.path.exists(current_path):
            with open(current_path, 'r', encoding='utf-16') as f: # ACC usa UTF-16 a veces para configs
                return json.load(f)
        else:
            # Intentar UTF-8 si falla o path alternativo
             with open(current_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        return None

async def generar_audio_tts(texto):
    """Genera audio MP3 usando edge-tts"""
    try:
        import edge_tts
        OUTPUT_FILE = "mensaje_ingeniero.mp3"
        communicate = edge_tts.Communicate(texto, "es-ES-AlvaroNeural") # Voz masculina natural
        await communicate.save(OUTPUT_FILE)
        return OUTPUT_FILE
    except Exception as e:
        return None
        # Convertir a valores legibles
        basic = setup.get('basicSetup', {})
        advanced = setup.get('advancedSetup', {})
        tyres = basic.get('tyres', {})
        alignment = basic.get('alignment', {})
        mech = advanced.get('mechanicalBalance', {})
        aero = advanced.get('aeroBalance', {})
        electronics = basic.get('electronics', {})
        strategy = basic.get('strategy', {})
        dampers = advanced.get('dampers', {})
        
        # Presiones: ACC usa índice, convertir a PSI real (base ~20.3 + idx * 0.1)
        pressures_raw = tyres.get('tyrePressure', [0,0,0,0])
        pressures_psi = [round(20.3 + p * 0.1, 1) for p in pressures_raw]
        
        # Camber: usar staticCamber si existe, sino convertir índice
        static_camber = alignment.get('staticCamber', [0,0,0,0])
        camber_values = [round(c, 1) for c in static_camber]
        
        parsed = {
            'setup_name': os.path.basename(target),
            'car': setup.get('carName', car),
            # Presiones
            'pressure_lf': pressures_psi[0],
            'pressure_rf': pressures_psi[1],
            'pressure_lr': pressures_psi[2],
            'pressure_rr': pressures_psi[3],
            # Camber
            'camber_lf': camber_values[0],
            'camber_rf': camber_values[1], 
            'camber_lr': camber_values[2],
            'camber_rr': camber_values[3],
            # Aero
            'rear_wing': aero.get('rearWing', 'N/A'),
            'splitter': aero.get('splitter', 'N/A'),
            'ride_height': aero.get('rideHeight', [0,0,0,0]),
            'brake_duct_front': aero.get('brakeDuct', [0,0])[0] if len(aero.get('brakeDuct', [])) > 0 else 'N/A',
            'brake_duct_rear': aero.get('brakeDuct', [0,0])[1] if len(aero.get('brakeDuct', [])) > 1 else 'N/A',
            # Mecánica - convertir índices ACC a valores reales
            # Brake Bias: ACC guarda índice, bias_real = 57.0 - (index * 0.2)
            # Brake Torque: ACC guarda índice, torque_real = 80 + index
            'arb_front': mech.get('aRBFront', 'N/A'),
            'arb_rear': mech.get('aRBRear', 'N/A'),
            'brake_bias': round(57.0 - mech.get('brakeBias', 0) * 0.2, 1),
            'brake_bias_raw': mech.get('brakeBias', 0),
            'brake_torque': 80 + mech.get('brakeTorque', 0),
            # Electrónica
            'tc1': electronics.get('tC1', 'N/A'),
            'tc2': electronics.get('tC2', 'N/A'),
            'abs': electronics.get('abs', 'N/A'),
            'ecu_map': electronics.get('eCUMap', 'N/A'),
            # Estrategia
            'fuel': strategy.get('fuel', 'N/A'),
            'fuel_per_lap': strategy.get('fuelPerLap', 'N/A'),
            # Dampers
            'bump_slow': dampers.get('bumpSlow', []),
            'rebound_slow': dampers.get('reboundSlow', []),
        }
        return parsed
    except Exception as e:
        return None

def format_setup_for_prompt(setup):
    """Formatea el setup para inyectar en el prompt de la IA"""
    if not setup:
        return "⚠️ No se encontró archivo de setup para esta combinación coche/pista."
    
    return f"""
SETUP ACTUAL DEL COCHE (archivo: {setup['setup_name']}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEUMÁTICOS (Presiones en frío PSI):
  - Delantera Izq: {setup['pressure_lf']} PSI
  - Delantera Der: {setup['pressure_rf']} PSI
  - Trasera Izq: {setup['pressure_lr']} PSI  
  - Trasera Der: {setup['pressure_rr']} PSI

ALINEACIÓN (Camber):
  - Delantero: {setup['camber_lf']}\u00B0 / {setup['camber_rf']}\u00B0
  - Trasero: {setup['camber_lr']}\u00B0 / {setup['camber_rr']}\u00B0

AERODINÁMICA:
  - Alerón Trasero (Rear Wing): {setup['rear_wing']}
  - Splitter: {setup['splitter']}
  - Brake Duct: Frontal {setup['brake_duct_front']} / Trasero {setup['brake_duct_rear']}

AGARRE MECÁNICO:
  - ARB Frontal: {setup['arb_front']}
  - ARB Trasero: {setup['arb_rear']}
  - Brake Bias: {setup['brake_bias']}%
  - Brake Torque: {setup['brake_torque']}

ELECTRÓNICA:
  - TC1: {setup['tc1']} | TC2: {setup['tc2']} | ABS: {setup['abs']} | ECU Map: {setup['ecu_map']}

COMBUSTIBLE:
  - Litros: {setup['fuel']}L | Consumo/vuelta: {setup['fuel_per_lap']}L
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

def get_sessions():
    try:
        conn = get_db_connection()
        df = conn.execute("""
            SELECT source_file, source_path, track, car, session_date, samples, ingested_at
            FROM bronze_acc_sessions ORDER BY ingested_at DESC
        """).df()
        conn.close()
        return df
    except:
        return pd.DataFrame()

def get_all_sessions_for_trends():
    """Obtiene todas las sesiones para análisis de tendencias"""
    try:
        conn = get_db_connection()
        df = conn.execute("""
            SELECT s.*, 
                   MAX(t.speed_kmh) as top_speed,
                   AVG(t.speed_kmh) as avg_speed,
                   AVG(CASE WHEN t.throttle_pct > 99 THEN 1.0 ELSE 0.0 END) * 100 as full_throttle_pct
            FROM bronze_acc_sessions s
            LEFT JOIN stg_acc_telemetry t ON s.source_file = t.source_file
            GROUP BY s.source_file, s.source_path, s.track, s.car, s.session_date, s.samples, s.ingested_at
            ORDER BY s.ingested_at
        """).df()
        conn.close()
        return df
    except:
        return pd.DataFrame()






@st.cache_resource
def get_db_connection():
    try:
        # Connect in READ_ONLY mode to avoid locking the writer
        conn = duckdb.connect(DB_PATH, read_only=True)
        return conn
    except Exception as e:
        st.error(f"Error connecting to DB: {e}")
        return None



def calculate_session_stats(df):
    if df.empty:
        return {}
    return {
        'samples': len(df),
        'top_speed_kmh': round(df['speed_kmh'].max(), 1) if 'speed_kmh' in df.columns else 0,
        'avg_speed_kmh': round(df['speed_kmh'].mean(), 1) if 'speed_kmh' in df.columns else 0,
        'full_throttle_pct': round((df['throttle_pct'] > 99).mean() * 100, 1) if 'throttle_pct' in df.columns else 0,
        'braking_pct': round((df['brake_pct'] > 5).mean() * 100, 1) if 'brake_pct' in df.columns else 0,
        'max_g_lateral': round(df['g_lateral'].abs().max(), 2) if 'g_lateral' in df.columns else 0,
        'max_g_longitudinal': round(df['g_longitudinal'].abs().max(), 2) if 'g_longitudinal' in df.columns else 0,
        'avg_tyre_temp_front': round((df['tyre_temp_lf'].mean() + df['tyre_temp_rf'].mean()) / 2, 1) if 'tyre_temp_lf' in df.columns else 0,
        'avg_tyre_temp_rear': round((df['tyre_temp_lr'].mean() + df['tyre_temp_rr'].mean()) / 2, 1) if 'tyre_temp_lr' in df.columns else 0,
    }

def analyze_braking_zones(df, laps):
    """Detecta zonas de frenado y genera feedback de pilotaje por vuelta"""
    if df.empty or not laps or 'brake_pct' not in df.columns:
        return []
    
    zones = []
    for lap in laps:
        lap_df = df.iloc[lap['start']:lap['end']].copy()
        if lap_df.empty:
            continue
        
        # Detectar eventos de frenado (brake > 10% por al menos 20 samples = 0.2s)
        braking = lap_df['brake_pct'] > 10
        brake_groups = (braking != braking.shift()).cumsum()
        
        lap_zones = []
        for group_id in brake_groups[braking].unique():
            mask = brake_groups == group_id
            group_data = lap_df[mask]
            if len(group_data) >= 20:  # Al menos 0.2 segundos
                entry_speed = group_data['speed_kmh'].iloc[0]
                exit_speed = group_data['speed_kmh'].iloc[-1]
                duration_ms = len(group_data) * 10  # 100Hz
                max_brake = group_data['brake_pct'].max()
                avg_brake = group_data['brake_pct'].mean()
                speed_lost = entry_speed - exit_speed
                
                lap_zones.append({
                    'entry_speed': round(entry_speed, 0),
                    'exit_speed': round(exit_speed, 0),
                    'speed_lost': round(speed_lost, 0),
                    'duration_ms': duration_ms,
                    'max_brake': round(max_brake, 0),
                    'avg_brake': round(avg_brake, 0),
                })
        
        zones.append({
            'lap': lap['lap'],
            'num_braking_events': len(lap_zones),
            'zones': lap_zones,
            'heaviest_brake': max(lap_zones, key=lambda z: z['speed_lost']) if lap_zones else None,
            'longest_brake': max(lap_zones, key=lambda z: z['duration_ms']) if lap_zones else None,
        })
    
    return zones

def analyze_driving_patterns(df, laps):
    """Analiza patrones de conducción para coaching"""
    if df.empty or not laps:
        return {}
    
    patterns = {'laps': []}
    
    for lap in laps:
        lap_df = df.iloc[lap['start']:lap['end']]
        if lap_df.empty:
            continue
        
        n = len(lap_df)
        throttle = lap_df['throttle_pct']
        brake = lap_df['brake_pct']
        
        # Coasting: ni acelerador (>5%) ni freno (>5%)
        coasting = ((throttle < 5) & (brake < 5)).sum() / n * 100
        
        # Overlap: freno y acelerador simultáneo
        overlap = ((throttle > 10) & (brake > 10)).sum() / n * 100
        
        # Trail braking: freno suave (<30%) con dirección (steer > 5\u00B0)
        trail = 0
        if 'steer_angle' in lap_df.columns:
            trail = ((brake > 5) & (brake < 40) & (lap_df['steer_angle'].abs() > 5)).sum() / n * 100
        
        # Smoothness: std de throttle (menor = más suave)
        throttle_smoothness = round(throttle.diff().abs().mean(), 2)
        
        # Tiempo en full throttle
        full_throttle = (throttle > 99).sum() / n * 100
        
        # Velocidad mínima en la vuelta
        min_speed = lap_df['speed_kmh'].min()
        
        patterns['laps'].append({
            'lap': lap['lap'],
            'coasting_pct': round(coasting, 1),
            'overlap_pct': round(overlap, 1),
            'trail_braking_pct': round(trail, 1),
            'throttle_smoothness': throttle_smoothness,
            'full_throttle_pct': round(full_throttle, 1),
            'min_speed': round(min_speed, 1),
        })
    
    # Promedios
    if patterns['laps']:
        patterns['avg_coasting'] = round(np.mean([l['coasting_pct'] for l in patterns['laps']]), 1)
        patterns['avg_overlap'] = round(np.mean([l['overlap_pct'] for l in patterns['laps']]), 1)
        patterns['avg_trail'] = round(np.mean([l['trail_braking_pct'] for l in patterns['laps']]), 1)
        patterns['avg_smoothness'] = round(np.mean([l['throttle_smoothness'] for l in patterns['laps']]), 2)
        patterns['consistency'] = round(np.std([l['full_throttle_pct'] for l in patterns['laps']]), 1)
    
    return patterns

def get_session_progress(current_file, sessions_df, all_silver_func):
    """Compara la sesión actual vs sesiones anteriores de la misma pista/coche"""
    if sessions_df.empty or len(sessions_df) < 2:
        return None
    
    current_row = sessions_df[sessions_df['source_file'] == current_file]
    if current_row.empty:
        return None
    
    car = current_row.iloc[0]['car']
    track = current_row.iloc[0]['track']
    
    # Filtrar sesiones del mismo coche/pista
    same_combo = sessions_df[(sessions_df['car'] == car) & (sessions_df['track'] == track)]
    if len(same_combo) < 2:
        return None
    
    # Ordenar por fecha
    same_combo = same_combo.sort_values('ingested_at')
    current_idx = same_combo[same_combo['source_file'] == current_file].index
    if len(current_idx) == 0:
        return None
    
    progress = {'sessions': []}
    for _, sess in same_combo.iterrows():
        try:
            s_df = all_silver_func(sess['source_file'])
            s_stats = calculate_session_stats(s_df)
            s_stats['source_file'] = sess['source_file']
            s_stats['session_date'] = sess['session_date']
            progress['sessions'].append(s_stats)
        except:
            continue
    
    if len(progress['sessions']) >= 2:
        first = progress['sessions'][0]
        last = progress['sessions'][-1]
        progress['delta'] = {
            'top_speed': round(last.get('top_speed_kmh', 0) - first.get('top_speed_kmh', 0), 1),
            'avg_speed': round(last.get('avg_speed_kmh', 0) - first.get('avg_speed_kmh', 0), 1),
            'throttle': round(last.get('full_throttle_pct', 0) - first.get('full_throttle_pct', 0), 1),
            'braking': round(last.get('braking_pct', 0) - first.get('braking_pct', 0), 1),
            'tyre_temp_f': round(last.get('avg_tyre_temp_front', 0) - first.get('avg_tyre_temp_front', 0), 1),
            'tyre_temp_r': round(last.get('avg_tyre_temp_rear', 0) - first.get('avg_tyre_temp_rear', 0), 1),
        }
        progress['num_sessions'] = len(progress['sessions'])
    
    return progress

def format_driving_analysis(braking_zones, patterns, progress):
    """Formatea el análisis de conducción para el prompt del Director"""
    lines = []
    
    # Análisis de frenado
    if braking_zones:
        best_lap = min(braking_zones, key=lambda z: z['num_braking_events']) if braking_zones else None
        lines.append("[ANÁLISIS DE PILOTAJE]")
        
        for bz in braking_zones[:5]:  # Max 5 vueltas para no saturar
            if bz['heaviest_brake']:
                hb = bz['heaviest_brake']
                lines.append(f"Vuelta {bz['lap']}: {bz['num_braking_events']} frenadas | "
                           f"Frenada más fuerte: {hb['entry_speed']}→{hb['exit_speed']} km/h "
                           f"({hb['speed_lost']} km/h perdidos, {hb['duration_ms']}ms, {hb['max_brake']}% presión)")
            if bz['longest_brake']:
                lb = bz['longest_brake']
                lines.append(f"  Frenada más larga: {lb['duration_ms']}ms desde {lb['entry_speed']} km/h")
    
    # Patrones de conducción
    if patterns and patterns.get('laps'):
        lines.append(f"\n[PATRONES DE CONDUCCIÓN]")
        lines.append(f"- Coasting (sin pedal): {patterns.get('avg_coasting', 0)}% → Ideal <5%. Más = tiempo perdido.")
        lines.append(f"- Overlap (freno+gas): {patterns.get('avg_overlap', 0)}% → Ideal <2%. Más = desgaste de frenos.")
        lines.append(f"- Trail Braking: {patterns.get('avg_trail', 0)}% → Ideal 8-15%. Poco = entradas lentas.")
        lines.append(f"- Suavidad del throttle: {patterns.get('avg_smoothness', 0)} → Menos = más suave.")
        lines.append(f"- Consistencia entre vueltas: σ={patterns.get('consistency', 0)}% → Menos = más consistente.")
        
        # Análisis por vuelta
        for lp in patterns['laps'][:5]:
            issues = []
            if lp['coasting_pct'] > 8: issues.append(f"coasting alto ({lp['coasting_pct']}%)")
            if lp['overlap_pct'] > 3: issues.append(f"overlap ({lp['overlap_pct']}%)")
            if lp['trail_braking_pct'] < 3: issues.append(f"poco trail braking ({lp['trail_braking_pct']}%)")
            if issues:
                lines.append(f"  → Vuelta {lp['lap']}: {', '.join(issues)}")
    
    # Progreso entre sesiones
    if progress and progress.get('delta'):
        d = progress['delta']
        lines.append(f"\n[PROGRESO ENTRE {progress['num_sessions']} SESIONES]")
        
        def arrow(val):
            return f"↑{val}" if val > 0 else f"↓{abs(val)}" if val < 0 else "="
        
        lines.append(f"- Top Speed: {arrow(d['top_speed'])} km/h")
        lines.append(f"- Vel. Promedio: {arrow(d['avg_speed'])} km/h")
        lines.append(f"- Full Throttle: {arrow(d['throttle'])}%")
        lines.append(f"- Tiempo frenando: {arrow(d['braking'])}%")
        lines.append(f"- Temp neumáticos F/R: {arrow(d['tyre_temp_f'])}\u00B0C / {arrow(d['tyre_temp_r'])}\u00B0C")
    
    return '\n'.join(lines)

def detect_laps_from_data(df, samples_per_lap=None):
    """Detecta vueltas usando lap_beacon, o patrones en la velocidad"""
    if df.empty:
        return []
    
    # Si hay lap_beacon, usarlo
    if 'lap_beacon' in df.columns and df['lap_beacon'].sum() > 0:
        laps = []
        lap_starts = df[df['lap_beacon'] > 0].index.tolist()
        for i, start in enumerate(lap_starts):
            end = lap_starts[i+1] if i+1 < len(lap_starts) else len(df)
            if end - start > 500:
                laps.append({'lap': i+1, 'start': start, 'end': end})
        return laps
    
    # Sin beacon: detectar vueltas buscando el punto más lento repetido
    if 'speed_kmh' not in df.columns or len(df) < 5000:
        return []
    
    speed = df['speed_kmh'].values
    n = len(speed)
    
    # Suavizar bastante para eliminar ruido (500 samples ≈ 5 seg)
    window = min(500, n // 20)
    speed_smooth = pd.Series(speed).rolling(window, center=True, min_periods=1).mean().values
    
    # MÉTODO: Buscar los VALLES de velocidad (punto más lento de cada vuelta)
    # Cada vuelta tiene UN punto donde se pasa por la curva más lenta del circuito
    # Esto ocurre exactamente 1 vez por vuelta (a diferencia de las rectas que pueden ser 2+)
    
    # Mínimo 100 segundos entre vueltas (= 6000 samples a 60Hz)
    # Ningún circuito GT tiene vueltas menores a 1:40
    min_distance = 6000  
    
    # Invertir velocidad para buscar valles como picos
    speed_inverted = -speed_smooth
    
    if SCIPY_AVAILABLE:
        try:
            # Buscar los puntos más lentos separados por al mínimo ~100 seg
            valleys, props = find_peaks(speed_inverted, 
                                        distance=min_distance,
                                        prominence=15)
        except Exception:
            valleys = np.array([])
    else:
        # Detección manual de valles
        valleys = []
        search_start = 0
        while search_start < n - 5000:
            search_end = min(search_start + 15000, n)
            chunk = speed_smooth[search_start:search_end]
            if len(chunk) > 0:
                valley_idx = search_start + np.argmin(chunk)
                if speed_smooth[valley_idx] < np.percentile(speed_smooth, 30):
                    valleys.append(valley_idx)
                    search_start = valley_idx + min_distance
                else:
                    search_start += min_distance
            else:
                break
        valleys = np.array(valleys)
    
    if len(valleys) < 2:
        return []
    
    # Filtrar valles que están muy cerca (sub-harmonics)
    # Quedarnos solo con los más profundos si hay duplicados cercanos
    filtered_valleys = [valleys[0]]
    for v in valleys[1:]:
        if v - filtered_valleys[-1] >= min_distance:
            filtered_valleys.append(v)
        else:
            # Si este valle es más profundo, reemplazar
            if speed_smooth[v] < speed_smooth[filtered_valleys[-1]]:
                filtered_valleys[-1] = v
    valleys = np.array(filtered_valleys)
    
    if len(valleys) < 2:
        return []
    
    # La vuelta va del punto medio ENTRE valles consecutivos
    # (así cada vuelta incluye su frenada + curva lenta + aceleración)
    midpoints = []
    for i in range(len(valleys) - 1):
        mid = (valleys[i] + valleys[i + 1]) // 2
        midpoints.append(mid)
    
    # Agregar inicio y final
    all_points = [0] + midpoints + [n]
    
    laps = []
    for i in range(len(all_points) - 1):
        start = all_points[i]
        end = all_points[i + 1]
        if end - start > 5000:  # Al menos ~50 seg de datos
            laps.append({'lap': i + 1, 'start': start, 'end': end})
    
    return laps

def calculate_lap_time_ms(df, lap):
    """Calcula el tiempo real de una vuelta usando time_ms"""
    lap_df = df.iloc[lap['start']:lap['end']]
    if lap_df.empty or 'time_ms' not in lap_df.columns:
        return None
    return lap_df['time_ms'].iloc[-1] - lap_df['time_ms'].iloc[0]

def format_lap_time(ms):
    """Convierte milliseconds a formato M:SS.mmm"""
    if ms is None or ms <= 0:
        return "N/A"
    mins = int(ms // 60000)
    secs = (ms % 60000) / 1000
    return f"{mins}:{secs:06.3f}"



# --- VISUALIZACIONES ---
def plot_speed_comparison(df, laps, best_lap_idx):
    """Compara mejor vuelta vs todas las demás"""
    fig = go.Figure()
    
    best_lap = laps[best_lap_idx]
    best_data = df.iloc[best_lap['start']:best_lap['end']]['speed_kmh'].reset_index(drop=True)
    
    # Dibujar todas las vueltas en gris
    for i, lap in enumerate(laps):
        if i != best_lap_idx:
            lap_data = df.iloc[lap['start']:lap['end']]['speed_kmh'].reset_index(drop=True)
            fig.add_trace(go.Scatter(
                y=lap_data, mode='lines', name=f"Vuelta {lap['lap']}",
                line=dict(color='rgba(150,150,150,0.3)', width=1),
                showlegend=False
            ))
    
    # Mejor vuelta en verde brillante
    fig.add_trace(go.Scatter(
        y=best_data, mode='lines', name=f"🏆 Mejor (V{best_lap['lap']})",
        line=dict(color='#00ff88', width=3)
    ))
    
    fig.update_layout(
        title="📈 Velocidad: Mejor Vuelta vs Todas",
        yaxis_title="km/h",
        template="plotly_dark",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig

def plot_inputs_comparison(df, laps, best_lap_idx):
    """Compara inputs de mejor vuelta vs promedio"""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        subplot_titles=("Throttle", "Brake"), vertical_spacing=0.1)
    
    best_lap = laps[best_lap_idx]
    best_throttle = df.iloc[best_lap['start']:best_lap['end']]['throttle_pct'].reset_index(drop=True)
    best_brake = df.iloc[best_lap['start']:best_lap['end']]['brake_pct'].reset_index(drop=True)
    
    # Calcular promedio de todas las vueltas
    all_throttle = []
    all_brake = []
    min_len = min(lap['end'] - lap['start'] for lap in laps)
    
    for lap in laps:
        all_throttle.append(df.iloc[lap['start']:lap['start']+min_len]['throttle_pct'].values)
        all_brake.append(df.iloc[lap['start']:lap['start']+min_len]['brake_pct'].values)
    
    avg_throttle = np.mean(all_throttle, axis=0)
    avg_brake = np.mean(all_brake, axis=0)
    
    # Promedio en gris
    fig.add_trace(go.Scatter(y=avg_throttle, mode='lines', name='Promedio',
                             line=dict(color='gray', width=2, dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(y=avg_brake, mode='lines', name='Promedio',
                             line=dict(color='gray', width=2, dash='dash'), showlegend=False), row=2, col=1)
    
    # Mejor vuelta
    fig.add_trace(go.Scatter(y=best_throttle[:min_len], mode='lines', name='Mejor Vuelta',
                             line=dict(color='#00ff88', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(y=best_brake[:min_len], mode='lines', name='Mejor Vuelta',
                             line=dict(color='#ff4444', width=2), showlegend=False), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=400,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_yaxes(range=[0, 105])
    return fig

def plot_gforces(df):
    if 'g_lateral' not in df.columns:
        return None
    sample = df.iloc[::5].copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sample['g_lateral'], y=sample['g_longitudinal'], mode='markers',
        marker=dict(size=3, color=sample['speed_kmh'], colorscale='Turbo',
                   showscale=True, colorbar=dict(title="km/h"))
    ))
    theta = np.linspace(0, 2*np.pi, 100)
    for g in [1, 2]:
        fig.add_trace(go.Scatter(x=g*np.cos(theta), y=g*np.sin(theta),
                                mode='lines', line=dict(dash='dash', color='gray'), showlegend=False))
    fig.update_layout(title="🎯 G-Force Map", template="plotly_dark", height=350,
                      xaxis=dict(scaleanchor="y", range=[-2.5, 2.5]), yaxis=dict(range=[-2.5, 2.5]))
    return fig

def plot_trends(sessions_df):
    """Gráfico de evolución de rendimiento"""
    if sessions_df.empty or len(sessions_df) < 2:
        return None
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=("Top Speed (km/h)", "Full Throttle %"))
    
    x = list(range(len(sessions_df)))
    labels = [f"{row['track'][:3]}\n{row['session_date'][-8:]}" for _, row in sessions_df.iterrows()]
    
    fig.add_trace(go.Scatter(x=x, y=sessions_df['top_speed'], mode='lines+markers',
                             name='Top Speed', line=dict(color='#ff4b4b', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=sessions_df['full_throttle_pct'], mode='lines+markers',
                             name='Full Throttle', line=dict(color='#00ff88', width=2)), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=400, showlegend=False)
    fig.update_xaxes(tickvals=x, ticktext=labels)
    return fig

def plot_tyre_balance(df):
    """Mapa de calor de temperaturas de neumáticos"""
    temps = {
        'LF': df['tyre_temp_lf'].mean() if 'tyre_temp_lf' in df.columns else 0,
        'RF': df['tyre_temp_rf'].mean() if 'tyre_temp_rf' in df.columns else 0,
        'LR': df['tyre_temp_lr'].mean() if 'tyre_temp_lr' in df.columns else 0,
        'RR': df['tyre_temp_rr'].mean() if 'tyre_temp_rr' in df.columns else 0,
    }
    
    z = [[temps['LF'], temps['RF']], [temps['LR'], temps['RR']]]
    
    fig = go.Figure(data=go.Heatmap(
        z=z, x=['Izquierda', 'Derecha'], y=['Delantero', 'Trasero'],
        colorscale='RdYlGn_r', text=[[f"{temps['LF']:.1f}\u00B0C", f"{temps['RF']:.1f}\u00B0C"],
                                      [f"{temps['LR']:.1f}\u00B0C", f"{temps['RR']:.1f}\u00B0C"]],
        texttemplate="%{text}", textfont={"size": 16}
    ))
    fig.update_layout(title="🌡️ Balance de Temperaturas", template="plotly_dark", height=300)
    return fig

# --- AGENTES IA ---
def consultar_ia(prompt, timeout=90):
    try:
        payload = {"model": MODELO_IA, "prompt": prompt, "stream": False, "options": {"temperature": 0.6}}
        res = requests.post("http://localhost:11434/api/generate", json=payload, timeout=timeout)
        texto = res.json().get('response', '')
        return re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL).strip() or "..."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def consultar_gemini(prompt, timeout=120):
    """Consulta a Gemini Pro para análisis avanzado"""
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        return response.text or "..."
    except Exception as e:
        return f"⚠️ Error Gemini: {str(e)}"

# --- AI CREW (PHASE 6) ---
def consultar_ollama_especialista(prompt, rol):
    """Consulta a Ollama usando el modelo especialista rápido (Llama 3.2 3B)"""
    try:
        # Usamos el modelo rápido sugerido por el usuario
        payload = {
            "model": "llama3.2:3b", 
            "prompt": f"Eres un {rol} experto en ACC. Analiza estos datos y da 2 consejos técnicos breves.\nDATOS: {prompt}", 
            "stream": False, 
            "options": {"temperature": 0.3}
        }
        res = requests.post("http://localhost:11434/api/generate", json=payload, timeout=30)
        texto = res.json().get('response', '...')
        # Limpiar etiquetas <think> si el modelo las genera
        return re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL).strip()
    except Exception as e:
        return f"⚠️ Error en {rol}: {str(e)}"

def ejecutar_crew_ia(report):
    """Ejecuta los 4 especialistas en paralelo usando ThreadPoolExecutor"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        prompts = {
            "Tyre Engineer": f"PSI Hot: {json.dumps(report['tyres']['avg_pressure_psi'])}, OMI Deltas: {json.dumps(report['tyres'].get('omi_delta', {}))}",
            "Aero & Brake Engineer": f"Brake Max Temp: {json.dumps(report['brakes']['max_temp_c'])}, Rake Avg: {report['summary'].get('rake_avg_mm', 0)}mm",
            "Driving Coach": f"Coasting: {report['summary'].get('coasting_pct', 0)}%, ABS: {report['electronics']['abs_triggers']}, TC: {report['electronics']['tc_triggers']}",
            "Suspension Specialist": f"Suspension Travel Avg: {json.dumps(report['summary'].get('avg_susp_travel', [0,0,0,0]))}"
        }
        
        future_to_role = {executor.submit(consultar_ollama_especialista, p, r): r for r, p in prompts.items()}
        
        results = {}
        for future in concurrent.futures.as_completed(future_to_role):
            role = future_to_role[future]
            try:
                results[role] = future.result()
            except Exception:
                results[role] = "Error en el análisis del especialista."
    return results

def agente_conductor(stats, track, laps_data):
    prompt = f"""[INSTRUCCIÓN] RESPONDE SOLO EN ESPAÑOL. Máximo 5 frases específicas.
    [ROL] Ingeniero de Conducción experto GT. Eres MUY exigente.
    [PISTA] {track.upper()}
    [DATOS TELEMETRÍA] 
    - Top Speed: {stats.get('top_speed_kmh')} km/h
    - Velocidad Promedio: {stats.get('avg_speed_kmh')} km/h  
    - Full Throttle: {stats.get('full_throttle_pct')}%
    - Tiempo Frenando: {stats.get('braking_pct')}%
    - G-Lateral Máx: {stats.get('max_g_lateral')}G
    
    [TAREA] Da 3 consejos TÉCNICOS ESPECÍFICOS para mejorar tiempos. Menciona curvas conocidas de la pista si es posible."""
    return consultar_ia(prompt)

def agente_neumaticos(stats):
    prompt = f"""[INSTRUCCIÓN] RESPONDE SOLO EN ESPAÑOL. Máximo 5 frases.
    [ROL] Ingeniero de Neumáticos GT3/GT4.
    [DATOS]
    - Temp Delanteras: {stats.get('avg_tyre_temp_front')}\u00B0C
    - Temp Traseras: {stats.get('avg_tyre_temp_rear')}\u00B0C
    - Diferencia F/R: {round(stats.get('avg_tyre_temp_rear', 0) - stats.get('avg_tyre_temp_front', 0), 1)}\u00B0C
    - G-Lateral: {stats.get('max_g_lateral')}G
    
    [TAREA] Analiza balance térmico. Recomienda ajustes específicos de presión (en PSI) y camber."""
    return consultar_ia(prompt)

def agente_estratega(stats, track):
    prompt = f"""[INSTRUCCIÓN] RESPONDE SOLO EN ESPAÑOL. Máximo 5 frases.
    [ROL] Jefa de Estrategia de Carreras GT.
    [PISTA] {track.upper()}
    [DATOS]
    - Velocidad Promedio: {stats.get('avg_speed_kmh')} km/h
    - Full Throttle: {stats.get('full_throttle_pct')}%
    - Degradación estimada por las temperaturas
    
    [TAREA] Dame una estrategia de carrera: gestión de neumáticos, cuándo atacar, cuándo conservar."""
    return consultar_ia(prompt)

def agente_setup(stats, track):
    prompt = f"""[INSTRUCCIÓN] RESPONDE SOLO EN ESPAÑOL. Máximo 5 frases.
    [ROL] Ingeniero de Setup GT3/GT4.
    [PISTA] {track.upper()}
    [DATOS]
    - G-Lateral Máx: {stats.get('max_g_lateral')}G
    - G-Longitudinal Máx: {stats.get('max_g_longitudinal')}G
    - Balance térmico F/R: {round(stats.get('avg_tyre_temp_rear', 0) - stats.get('avg_tyre_temp_front', 0), 1)}\u00B0C
    
    [TAREA] Recomienda ajustes de setup: alerón, ARB, brake bias. Valores específicos."""
    return consultar_ia(prompt)

def agente_coach(stats, track, best_vs_avg):
    prompt = f"""[INSTRUCCIÓN] RESPONDE SOLO EN ESPAÑOL. Máximo 5 frases.
    [ROL] Coach de Pilotos GT. MOTIVADOR pero EXIGENTE.
    [PISTA] {track.upper()}
    [ANÁLISIS]
    - Diferencia mejor vuelta vs promedio: {best_vs_avg.get('speed_diff', 0)} km/h
    - Consistencia: {'Buena' if best_vs_avg.get('consistency', 0) < 5 else 'Mejorable'}
    
    [TAREA] Identifica en qué sectores puedo mejorar más. Sé específico con curvas de {track}."""
    return consultar_ia(prompt)

def agente_analista(stats, sessions_count):
    prompt = f"""[INSTRUCCIÓN] RESPONDE SOLO EN ESPAÑOL. Máximo 5 frases.
    [ROL] Analista de Datos de Rendimiento.
    [DATOS]
    - Sesiones analizadas: {sessions_count}
    - Top Speed actual: {stats.get('top_speed_kmh')} km/h
    - Full Throttle: {stats.get('full_throttle_pct')}%
    
    [TAREA] Analiza tendencias de rendimiento. ¿Estoy mejorando? ¿Qué área necesita más trabajo?"""
    return consultar_ia(prompt)

# --- CROSS-SESSION ANALYSIS ---
def get_all_sessions_summary():
    """Get summary stats for all sessions in the DB"""
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        df = conn.execute("""
            SELECT 
                filename,
                track,
                vehicle,
                MIN(date) as session_start,
                COUNT(*) as samples,
                MAX(speedkmh) as top_speed,
                AVG(speedkmh) as avg_speed,
                AVG(CASE WHEN throttle > 0.99 THEN 1.0 ELSE 0.0 END) * 100 as full_throttle_pct,
                AVG(CASE WHEN brake > 0.05 THEN 1.0 ELSE 0.0 END) * 100 as braking_pct,
                MAX(lap) as max_lap,
                AVG(fuel_rem) as avg_fuel,
                MAX(ABS(g_lat)) as max_g_lat,
                MAX(ABS(g_lon)) as max_g_lon
            FROM gold_acc_laps
            WHERE track IS NOT NULL AND track != 'Unknown' AND track != 'TBD'
            GROUP BY filename, track, vehicle
            HAVING samples > 500
            ORDER BY session_start DESC
        """).df()
        return df
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return pd.DataFrame()

def get_session_laps(filename):
    """Get lap-by-lap data for a specific session"""
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        df = conn.execute(f"""
            SELECT 
                lap,
                MAX(speedkmh) as top_speed,
                AVG(speedkmh) as avg_speed,
                COUNT(*) as samples,
                AVG(CASE WHEN throttle > 0.99 THEN 1.0 ELSE 0.0 END) * 100 as full_throttle_pct,
                MAX(ABS(g_lat)) as max_g_lat,
                MAX(ABS(g_lon)) as max_g_lon,
                AVG(fuel_rem) as fuel_avg,
                AVG(brake_bias) as brake_bias_avg,
                AVG(tc_value) as tc_avg,
                AVG(abs_value) as abs_avg
            FROM gold_acc_laps
            WHERE filename = '{filename}' AND lap > 0
            GROUP BY lap
            ORDER BY lap
        """).df()
        return df
    except:
        return pd.DataFrame()

def get_session_telemetry(filename, lap=None):
    """Get full telemetry for a session or specific lap"""
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        where = f"filename = '{filename}'"
        if lap is not None:
            where += f" AND lap = {lap}"
        df = conn.execute(f"""
            SELECT * FROM gold_acc_laps
            WHERE {where}
            ORDER BY packet_idx
        """).df()
        return df
    except:
        return pd.DataFrame()

def render_progress_tab():
    """Render the cross-session progress analysis tab"""
    st.header("📈 Progreso Intersesión")
    st.markdown("Análisis de tu evolución a través de todas las sesiones guardadas en DuckDB.")
    
    sessions = get_all_sessions_summary()
    
    if sessions.empty:
        st.warning("No hay sesiones suficientes en la base de datos. Necesitas sesiones con >500 samples y pista detectada.")
        return
    
    # --- Filtros ---
    tracks = sessions['track'].unique().tolist()
    selected_track = st.selectbox("🏁 Circuito", ["Todos"] + tracks)
    
    if selected_track != "Todos":
        sessions = sessions[sessions['track'] == selected_track]
    
    st.caption(f"📊 {len(sessions)} sesiones | {sessions['samples'].sum():,.0f} data points totales")
    
    # --- KPI Overview ---
    st.subheader("🏆 Resumen Global")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Sesiones", len(sessions))
    k2.metric("Top Speed", f"{sessions['top_speed'].max():.1f} km/h")
    k3.metric("Vel. Prom Mejor", f"{sessions['avg_speed'].max():.1f} km/h")
    k4.metric("G-Lat Máx", f"{sessions['max_g_lat'].max():.2f} G")
    k5.metric("G-Lon Máx", f"{sessions['max_g_lon'].max():.2f} G")
    
    # --- Evolución de velocidad y rendimiento ---
    st.subheader("📈 Evolución por Sesión")
    
    sessions_sorted = sessions.sort_values('session_start')
    session_labels = [f"S{i+1}" for i in range(len(sessions_sorted))]
    
    # Speed evolution
    fig_evo = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Velocidad Máxima (km/h)", "% Full Throttle", "% Frenando", "G-Lat Máximo"),
        vertical_spacing=0.12, horizontal_spacing=0.1
    )
    
    fig_evo.add_trace(go.Scatter(
        x=session_labels, y=sessions_sorted['top_speed'],
        mode='lines+markers', name='Top Speed',
        line=dict(color='#00ff88', width=2), marker=dict(size=8)
    ), row=1, col=1)
    
    fig_evo.add_trace(go.Scatter(
        x=session_labels, y=sessions_sorted['full_throttle_pct'],
        mode='lines+markers', name='Full Throttle %',
        line=dict(color='#ffaa00', width=2), marker=dict(size=8)
    ), row=1, col=2)
    
    fig_evo.add_trace(go.Scatter(
        x=session_labels, y=sessions_sorted['braking_pct'],
        mode='lines+markers', name='Braking %',
        line=dict(color='#ff4444', width=2), marker=dict(size=8)
    ), row=2, col=1)
    
    fig_evo.add_trace(go.Scatter(
        x=session_labels, y=sessions_sorted['max_g_lat'],
        mode='lines+markers', name='G-Lat Max',
        line=dict(color='#00ccff', width=2), marker=dict(size=8)
    ), row=2, col=2)
    
    fig_evo.update_layout(
        height=500, template="plotly_dark", showlegend=False,
        title_text=f"Evolución de Rendimiento ({selected_track})"
    )
    st.plotly_chart(fig_evo, use_container_width=True, key="progress_evolution")
    
    # --- Tabla de sesiones ---
    st.subheader("📋 Historial de Sesiones")
    
    display_df = sessions_sorted[['track', 'vehicle', 'session_start', 'samples', 'top_speed', 'avg_speed', 'full_throttle_pct', 'max_g_lat']].copy()
    display_df.columns = ['Pista', 'Coche', 'Fecha', 'Samples', 'V.Max', 'V.Prom', 'Throttle%', 'G-Lat']
    display_df['Fecha'] = pd.to_datetime(display_df['Fecha']).dt.strftime('%d/%m %H:%M')
    display_df['V.Max'] = display_df['V.Max'].round(1)
    display_df['V.Prom'] = display_df['V.Prom'].round(1)
    display_df['Throttle%'] = display_df['Throttle%'].round(1)
    display_df['G-Lat'] = display_df['G-Lat'].round(2)
    st.dataframe(display_df, use_container_width=True)
    
    # --- Comparar 2 sesiones ---
    st.subheader("🔍 Comparar Sesiones")
    
    session_opts = [f"{r['track']} | {r['vehicle']} | {pd.to_datetime(r['session_start']).strftime('%d/%m %H:%M')} ({r['samples']:,.0f} pts)"
                    for _, r in sessions_sorted.iterrows()]
    
    if len(session_opts) >= 2:
        col_a, col_b = st.columns(2)
        with col_a:
            idx_a = st.selectbox("Sesión A", range(len(session_opts)), format_func=lambda x: session_opts[x], key="sess_a")
        with col_b:
            idx_b = st.selectbox("Sesión B", range(len(session_opts)), index=min(1, len(session_opts)-1), format_func=lambda x: session_opts[x], key="sess_b")
        
        if st.button("⚡ Comparar", key="btn_compare"):
            sess_a = sessions_sorted.iloc[idx_a]
            sess_b = sessions_sorted.iloc[idx_b]
            
            with st.spinner("Cargando telemetría de ambas sesiones..."):
                laps_a = get_session_laps(sess_a['filename'])
                laps_b = get_session_laps(sess_b['filename'])
            
            if not laps_a.empty and not laps_b.empty:
                # Side-by-side metrics
                st.markdown("#### Comparación")
                m1, m2, m3, m4 = st.columns(4)
                
                m1.metric("V.Max A→B", 
                          f"{sess_b['top_speed']:.1f}",
                          f"{sess_b['top_speed'] - sess_a['top_speed']:+.1f} km/h")
                m2.metric("V.Prom A→B",
                          f"{sess_b['avg_speed']:.1f}",
                          f"{sess_b['avg_speed'] - sess_a['avg_speed']:+.1f} km/h")
                m3.metric("Throttle A→B",
                          f"{sess_b['full_throttle_pct']:.1f}%",
                          f"{sess_b['full_throttle_pct'] - sess_a['full_throttle_pct']:+.1f}%")
                m4.metric("G-Lat A→B",
                          f"{sess_b['max_g_lat']:.2f}",
                          f"{sess_b['max_g_lat'] - sess_a['max_g_lat']:+.2f} G")
                
                # Lap speed overlay
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Scatter(
                    x=laps_a['lap'], y=laps_a['avg_speed'],
                    mode='lines+markers', name=f"Sesión A ({pd.to_datetime(sess_a['session_start']).strftime('%d/%m')})",
                    line=dict(color='#ff6b6b', width=2)
                ))
                fig_comp.add_trace(go.Scatter(
                    x=laps_b['lap'], y=laps_b['avg_speed'],
                    mode='lines+markers', name=f"Sesión B ({pd.to_datetime(sess_b['session_start']).strftime('%d/%m')})",
                    line=dict(color='#4ecdc4', width=2)
                ))
                fig_comp.update_layout(
                    title="Velocidad Promedio por Vuelta",
                    xaxis_title="Vuelta", yaxis_title="Vel. Prom (km/h)",
                    template="plotly_dark", height=400
                )
                st.plotly_chart(fig_comp, use_container_width=True, key="lap_comparison")
            else:
                st.warning("No hay suficientes datos de vueltas para comparar.")
    else:
        st.info("Necesitas al menos 2 sesiones para comparar.")

# --- UI PRINCIPAL ---
def main():
    st.title("🏎️ ACC Pro Racing Dashboard")
    st.caption("Tu equipo de carreras virtual con IA")
    
    with st.sidebar:
        st.image("https://toucan.simracing.club/static/img/games/acc.png", width=100)
        st.title("Menú")
        st.caption("Tu equipo de carreras virtual con IA")

    tab_stint, tab_progress = st.tabs(["🧠 Sesión Actual (Stint)", "📈 Progreso (Todas las Sesiones)"])

    with tab_stint:
        st.header("🧠 Ingeniero Virtual (Fase Stint)")
        st.markdown("Análisis automático de tus tandas de vueltas (Stints) importado desde WSL.")
        
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../stint_report.json")
        
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r') as f:
                    report = json.load(f)
                
                dt = datetime.datetime.fromisoformat(report['timestamp'])
                st.info(f"📊 Último Reporte: {dt.strftime('%H:%M:%S')} (Hace {(datetime.datetime.now() - dt).seconds // 60} min)")
                
                # --- FASE 1: SÍNTOMAS (Dashboard) ---
                c1, c2, c3 = st.columns(3)
                
                # Neumáticos
                # Metadata & Track
                st.info(f"📍 **Circuito:** {report.get('track', 'Unknown')} | 🏎️ **Vehículo:** {report.get('car', 'Unknown')}")
                
                c1, c2, c3 = st.columns(3)
                
                # Neumáticos
                with c1:
                    st.subheader("🛞 Neumáticos (PSI Caliente)")
                    press = report['tyre_press' if 'tyre_press' in report else 'tyres']['avg_pressure_psi']
                    wear = report['tyre_wear' if 'tyre_wear' in report else 'tyres']['wear']
                    
                    col_fl, col_fr = st.columns(2)
                    col_fl.metric("FL", f"{press['fl']} psi", f"{wear['fl']:.1f} mm wear", delta_color="inverse")
                    col_fr.metric("FR", f"{press['fr']} psi", f"{wear['fr']:.1f} mm wear", delta_color="inverse")
                    
                    col_rl, col_rr = st.columns(2)
                    col_rl.metric("RL", f"{press['rl']} psi", f"{wear['rl']:.1f} mm wear", delta_color="inverse")
                    col_rr.metric("RR", f"{press['rr']} psi", f"{wear['rr']:.1f} mm wear", delta_color="inverse")
                    
                    # OMI Delta (Expert)
                    if 'omi_delta' in report['tyres']:
                        st.write("**Delta OMI (I-O)**")
                        omi = report['tyres']['omi_delta']
                        st.text(f"FL: {omi['fl']}\u00B0 | FR: {omi['fr']}\u00B0")
                        st.text(f"RL: {omi['rl']}\u00B0 | RR: {omi['rr']}\u00B0")
                
                # Frenos & Aero
                with c2:
                    st.subheader("🔥 Frenos & Aero")
                    brake_avg = report['brakes']['avg_temp_c']
                    brake_max = report['brakes']['max_temp_c']
                    
                    st.write("**Temp Máxima Frenos**")
                    st.text(f"FL: {brake_max['fl']}\u00B0 | FR: {brake_max['fr']}\u00B0")
                    st.text(f"RL: {brake_max['rl']}\u00B0 | RR: {brake_max['rr']}\u00B0")
                    
                    rake = report['summary'].get('rake_avg_mm', 0)
                    st.metric("Rake Promedio", f"{rake} mm")
                
                # Electrónica & Driving
                with c3:
                    st.subheader("⚡ Electrónica & Handling")
                    st.metric("ABS Activations", report['electronics']['abs_triggers'])
                    st.metric("TC Activations", report['electronics']['tc_triggers'])
                    
                    coasting = report['summary'].get('coasting_pct', 0)
                    st.metric("Coasting (Tiempo Muerto)", f"{coasting}%")
                    st.metric("Fuel Usado", f"{report['fuel']['total_used']} L")

                # --- Tabla de Vueltas ---
                if 'laps' in report and report['laps']:
                    st.divider()
                    st.subheader("🏁 Tiempos por Vuelta")
                    lap_data = []
                    for l in report['laps']:
                        m, s = divmod(l['time'], 60)
                        lap_data.append({
                            "Vuelta": l['lap'],
                            "Tiempo": f"{int(m):02d}:{s:06.3f}",
                            "Válida": "✅" if l['isValid'] else "❌"
                        })
                    st.table(lap_data)

                # --- FASE 7: LAP TIMING BAR ---
                st.divider()
                st.subheader("⏱️ Ritmo de Carrera")
                
                # Extraer métricas de ritmo
                best_lap = report['summary'].get('best_lap', 0)
                avg_pace = report['summary'].get('avg_pace', 0)
                consistency = report['summary'].get('consistency', 0)
                lap_count = report['summary'].get('lap_count', 0)
                
                # Visual Bar
                k1, k2, k3, k4 = st.columns(4)
                
                def fmt_lap(sec):
                    if sec == 0: return "--:--"
                    m, s = divmod(sec, 60)
                    return f"{int(m)}:{s:06.3f}"

                k1.metric("Vueltas", lap_count)
                k2.metric("Mejor Vuelta", fmt_lap(best_lap), delta="Récord" if best_lap > 0 else None, delta_color="normal")
                k3.metric("Ritmo Promedio", fmt_lap(avg_pace))
                
                consist_label = "✅ Reloj Suizo" if consistency < 0.3 else "⚠️ Errático"
                k4.metric("Consistencia (StdDev)", f"{consistency:.2f}s", delta=consist_label, delta_color="inverse")

                # --- FASE 2: DIRECTOR (Prompt Gen) ---
                st.divider()
                st.subheader("🤖 Diagnóstico IA (El Director)")
                
                prompt = f"""
Actúa como un Crew Chief e Ingeniero de Pista experto en Assetto Corsa Competizione (GT3).
Analiza este Stint Report y genera un diagnóstico profesional.

CONTEXTO:
- Circuito: {report.get('track', 'Unknown')}
- Vehículo: {report.get('car', 'Unknown')}

DATOS DEL STINT:
- Presiones Avg (Hot): {json.dumps(press)}
- Delta OMI (Inside-Outside): {json.dumps(report['tyres'].get('omi_delta', {}))}
- Brakes (Temp Max): {json.dumps(brake_max)}
- Aero (Rake Avg): {report['summary'].get('rake_avg_mm', 0)} mm
- Driving: Coasting={report['summary'].get('coasting_pct', 0)}%, ABS={report['electronics']['abs_triggers']}, TC={report['electronics']['tc_triggers']}
- Laps: {json.dumps(report.get('laps', []))}

[NUEVA SECCIÓN DE DATOS PARA LA IA - RITMO]
- Mejor Vuelta: {fmt_lap(best_lap)}
- Ritmo Promedio (Avg Pace): {fmt_lap(avg_pace)}
- Consistencia (StdDev): {consistency:.2f}s ({consist_label})
- Total Vueltas: {lap_count}

REGLAS DE ORO DEL EQUIPO (KPIs Críticos):
1. NEUMÁTICOS: El target es 26.0 - 27.0 PSI. Si OMI Delta > 15\u00B0C, sugerir reducir Camber.
2. FRENOS: Target 400\u00B0C - 650\u00B0C. Si > 700\u00B0C, sugerir abrir Brake Ducts (+1). Si < 350\u00B0C, cerrar (-1).
3. MANEJO: Coasting debe ser mínimo. Si > 5%, el piloto está dudando en curvas. Si TC se activa mucho en salidas, sugerir bajar TC o suavizar aceleración.
4. RAKE: Si el coche es inestable en frenada, revisar variación del Rake.
5. RITMO: Si la consistencia es mala (> 0.5s), dile al piloto que deje de buscar "vueltas mágicas" y busque ritmo. Si es buena pero lenta, culpa al Setup.

TU RESPUESTA:
- Dame 3 ajustes de SETUP específicos y 2 consejos de CONDUCCIÓN.
- Analiza brevemente el RITMO (Pace) al final.
- Usa un tono de Ingeniero de Carreras (directo, técnico, motivador).
- Formato: Markdown limpio.
"""
                
                if st.button("🧠 Generar Diagnóstico con AI Crew (Ollama + Gemini)"):
                    if GEMINI_AVAILABLE:
                        with st.status("🛠️ Consultando al Equipo de Ingeniería...", expanded=True) as status:
                            st.write("🤖 Especialistas analizando telemetría (Ollama)...")
                            crew_feedback = ejecutar_crew_ia(report)
                            st.write("✅ Informes de especialistas recibidos.")
                            
                            st.write("👑 El Director (Gemini) está sintetizando la estrategia final...")
                            
                            # Cargar Setup Actual
                            current_setup = get_current_setup()
                            setup_context = ""
                            if current_setup:
                                basic = current_setup.get('basicSetup', {})
                                adv = current_setup.get('advancedSetup', {})
                                setup_context = f"\n\nSETUP ACTUAL DEL PILOTO (Referencia):\n- Tyres PSI: {basic.get('tyres', {}).get('tyrePressure', 'Unknown')}\n- Aero: Rear Wing={basic.get('aerodynamics', {}).get('rearWing', 'Unknown')}\n- Brake Bias: {basic.get('electronics', {}).get('brakeBias', 'Unknown')}"
                                st.info(f"🔧 Setup detectado: Alerón {basic.get('aerodynamics', {}).get('rearWing', 'Unknown')} | Bias {basic.get('electronics', {}).get('brakeBias', 'Unknown')}")

                            prompt_final = prompt + setup_context + "\n\nINFORMES DE TUS ESPECIALISTAS (Usa esto como base):\n"
                            for role, feedback in crew_feedback.items():
                                prompt_final += f"### {role}\n{feedback}\n\n"
                            
                            response = consultar_gemini(prompt_final)
                            
                            # Generar Audio TTS
                            st.write("🎙️ Ingeniero generando mensaje de radio...")
                            
                            # Extraer resumen inteligente para audio (Busca secciones clave)
                            audio_text = "Aquí tu ingeniero. "
                            if "AJUSTES DE SETUP" in response:
                                parts = response.split("AJUSTES DE SETUP")[1].split("CONSEJOS DE CONDUCCIÓN")[0]
                                audio_text += "He encontrado ajustes críticos en el setup. " + parts[:400] # Limitar caracteres
                            else:
                                audio_text += response[:300]
                            
                            audio_text += ". Revisa el monitor para el detalle completo. Cambio."
                            
                            # Limpiar caracteres raros para el TTS
                            audio_text = audio_text.replace("*", "").replace("#", "").replace("-", "")
                            
                            audio_file = asyncio.run(generar_audio_tts(audio_text))
                            
                            status.update(label="✅ Diagnóstico Completado", state="complete", expanded=False)
                            st.markdown(response)
                            
                            if audio_file:
                                st.audio(audio_file, format='audio/mp3', autoplay=True)
                            
                            with st.expander("📄 Ver informes técnicos de los especialistas"):
                                for role, feedback in crew_feedback.items():
                                    st.write(f"**{role}:**")
                                    st.write(feedback)
                    else:
                        st.error("⚠️ Gemini no disponible. Falta la API Key.")
                        st.info("Configura tu API Key en la terminal: `export GEMINI_API_KEY='tu_clave'`")
                        st.code(prompt, language='text')

            except Exception as e:
                st.error(f"Error leyendo reporte: {e}")
        else:
            st.info("ℹ️ No se encontró reporte de Stint. Ejecuta `acc_recorder_v2.py` en WSL y completa un stint (entra a pits).") 

    with tab_progress:
        render_progress_tab()

if __name__ == "__main__":
    main()


