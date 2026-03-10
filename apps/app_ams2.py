import streamlit as st
import pandas as pd
import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import time
import requests
import re
import json
import asyncio
import concurrent.futures
import datetime
from google import genai

DB_PATH = "/home/diegokernel/proyectos/lakehouse/lakehouse_project/lakehouse.duckdb"
STINT_REPORT_PATH = "/home/diegokernel/proyectos/stint_report_ams2.json"
GEMINI_MODEL = "gemini-1.5-pro-latest"

st.set_page_config(page_title="🏎️ AMS2 AI Crew", layout="wide")

# Gemini Setup
GEMINI_AVAILABLE = False
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        gemini_client = genai.Client(api_key=api_key)
        GEMINI_AVAILABLE = True
except: pass

def get_con():
    if not os.path.exists(DB_PATH):
        return None
    try:
        return duckdb.connect(DB_PATH, read_only=True)
    except:
        return None

# --- AI AGENTS ---
def consultar_ollama(prompt, rol):
    try:
        payload = {
            "model": "llama3.2:3b", 
            "prompt": f"Eres un {rol} experto en simulación de carreras. Analiza estos datos de AMS2 y da 1 consejo breve.\nDATOS: {prompt}", 
            "stream": False, "options": {"temperature": 0.3}
        }
        res = requests.post("http://localhost:11434/api/generate", json=payload, timeout=15)
        # Limpieza básica de tags si el modelo los genera
        resp = res.json().get('response', '')
        return re.sub(r'<think>.*?</think>', '', resp, flags=re.DOTALL).strip()
    except: return "No disponible (Ollama)."

def ejecutar_crew(report):
    roles = {
        "Tyre Engineer": f"Temps C: {json.dumps(report['tyres']['avg_temp_c'])}",
        "Brake Engineer": f"Max Temps: {json.dumps(report['brakes']['max_temp_c'])}",
        "Driving Coach": f"Coasting: {report['summary'].get('coasting_pct', 0)}%"
    }
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(consultar_ollama, p, r): r for r, p in roles.items()}
        for f in concurrent.futures.as_completed(futures):
            results[futures[f]] = f.result()
    return results

async def generar_tts(texto):
    try:
        import edge_tts
        path = os.path.join(os.getcwd(), "radio_ams2.mp3")
        communicate = edge_tts.Communicate(texto, "es-ES-AlvaroNeural")
        await communicate.save(path)
        return path
    except: return None

def main():
    st.title("🏎️ Automobilista 2 Pro Dashboard")
    
    t1, t2 = st.tabs(["🧠 AI Crew & Stint", "📊 Telemetría Histórica"])

    with t1:
        st.header("🏁 Análisis de Stint (Pit Wall)")
        if os.path.exists(STINT_REPORT_PATH):
            with open(STINT_REPORT_PATH, 'r') as f:
                report = json.load(f)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("🛞 Neumáticos")
                t = report['tyres']['avg_temp_c']
                st.metric("FL", f"{t['fl']}°C")
                st.metric("FR", f"{t['fr']}°C")
            with c2:
                st.subheader("🔥 Frenos")
                b = report['brakes']['max_temp_c']
                st.metric("FL Max", f"{b['fl']}°C")
                st.metric("FR Max", f"{b['fr']}°C")
            with c3:
                st.subheader("⛽ Consumo & Handling")
                st.metric("Fuel Usado", f"{report['fuel']['total_used']} L")
                st.metric("Coasting", f"{report['summary']['coasting_pct']}%")

            if st.button("🎙️ Consultar al Equipo de Ingeniería (IA)"):
                with st.status("🛠️ Conectando con el Pit Wall...") as status:
                    crew_feedback = ejecutar_crew(report)
                    st.write("✅ Informes recibidos.")
                    
                    if GEMINI_AVAILABLE:
                        prompt = f"Actúa como Crew Chief. Sintetiza estos informes de tus ingenieros para el piloto de AMS2. Sé breve y técnico.\n"
                        for r, f in crew_feedback.items(): prompt += f"- {r}: {f}\n"
                        
                        response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt).text
                        st.markdown(response)
                        
                        # TTS
                        clean_text = response.replace("*", "").replace("#", "")
                        audio_path = asyncio.run(generar_tts(f"Atención piloto. {clean_text}"))
                        if audio_path: st.audio(audio_path, autoplay=True)
                    else:
                        st.warning("Gemini no disponible. Aquí los informes de los ingenieros:")
                        for r, f in crew_feedback.items(): st.write(f"**{r}**: {f}")
                    status.update(label="Análisis completado", state="complete")
        else:
            st.info("Esperando reporte de stint... (Entra a boxes en el simulador)")

    with t2:
        con = get_con()
        if not con:
            st.info("🕒 Esperando conexión a la base de datos...")
            time.sleep(2)
            st.rerun()
            return

        try:
            sessions = con.execute("SELECT session_id, MIN(timestamp) as t, COUNT(*) as c FROM gold_ams2_laps GROUP BY 1 ORDER BY 2 DESC").df()
        except:
            st.warning("No se ha encontrado la tabla de telemetría aún.")
            return

        if sessions.empty:
            st.write("No hay datos históricos grabados.")
        else:
            sid = st.selectbox("Selecciona Sesión", sessions['session_id'])
            df = con.execute(f"SELECT * FROM gold_ams2_laps WHERE session_id = '{sid}' ORDER BY timestamp").df()
            
            if df.empty:
                st.warning("La sesión seleccionada no tiene datos.")
            else:
                # Synthetic distance
                if df['odometer_km'].nunique() > 1:
                    df['dist_m'] = (df['odometer_km'] - df['odometer_km'].iloc[0]) * 1000
                else:
                    df['dt'] = pd.to_datetime(df['timestamp']).diff().dt.total_seconds().fillna(0)
                    df['dist_m'] = (df['speed_kmh'] / 3.6 * df['dt']).cumsum()

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)
                fig.add_trace(go.Scatter(x=df['dist_m'], y=df['speed_kmh'], name="Velocidad (km/h)", line=dict(color='#00ff88')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df['dist_m'], y=df['throttle']*100, name="Gas %", line=dict(color='#00ff88')), row=2, col=1)
                fig.add_trace(go.Scatter(x=df['dist_m'], y=df['brake']*100, name="Freno %", line=dict(color='#ff4444')), row=2, col=1)
                
                fig.update_layout(height=600, template="plotly_dark", showlegend=True)
                st.plotly_chart(fig, width="stretch")

if __name__ == "__main__":
    main()
