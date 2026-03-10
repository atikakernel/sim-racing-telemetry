"""
Dirt Rally 2.0 - Telemetry Dashboard
Two tabs: Stage Analysis + Cross-Stage Progress

Usage:
  streamlit run apps/app_dr2.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb
import json
import os
import numpy as np

# Config
DB_PATH = "lakehouse/lakehouse_project/lakehouse.duckdb"
STAGE_REPORT_PATH = "dr2_stage_report.json"

st.set_page_config(page_title="🏁 DR2 Telemetry", layout="wide", page_icon="🏁")

# --- DB Connection ---
@st.cache_resource
def get_db_connection():
    try:
        return duckdb.connect(DB_PATH, read_only=True)
    except:
        return None

# --- Data Functions ---
def load_stage_report():
    try:
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../{STAGE_REPORT_PATH}")
        if os.path.exists(report_path):
            with open(report_path, 'r') as f:
                return json.load(f)
    except:
        pass
    return None

def get_all_stages():
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        return conn.execute("""
            SELECT 
                session_id,
                MIN(date) as session_start,
                COUNT(*) as samples,
                MAX(speed_kmh) as top_speed,
                AVG(speed_kmh) as avg_speed,
                MAX(stage_distance) as stage_length,
                MAX(ABS(g_force_lat)) as max_g_lat,
                MAX(ABS(g_force_lon)) as max_g_lon,
                AVG(CASE WHEN throttle > 0.95 THEN 1.0 ELSE 0.0 END) * 100 as full_throttle_pct,
                AVG(CASE WHEN brake > 0.05 THEN 1.0 ELSE 0.0 END) * 100 as braking_pct,
                AVG(CASE WHEN handbrake > 0.3 THEN 1.0 ELSE 0.0 END) * 100 as handbrake_pct,
                MAX(stage_time) as stage_time
            FROM gold_dr2_stages
            GROUP BY session_id
            HAVING samples > 100
            ORDER BY session_start DESC
        """).df()
    except:
        return pd.DataFrame()

def get_stage_telemetry(session_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        return conn.execute(f"""
            SELECT * FROM gold_dr2_stages
            WHERE session_id = '{session_id}'
            ORDER BY sample_idx
        """).df()
    except:
        return pd.DataFrame()

# --- Visualization Helpers ---
def plot_speed_trace(df, title="Speed Trace"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['stage_distance'], y=df['speed_kmh'],
        mode='lines', name='Speed',
        line=dict(color='#00ff88', width=1.5),
        fill='tozeroy', fillcolor='rgba(0,255,136,0.1)'
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Distancia (m)", yaxis_title="Velocidad (km/h)",
        template="plotly_dark", height=300,
        margin=dict(l=50, r=20, t=40, b=40)
    )
    return fig

def plot_inputs(df):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=("Throttle / Brake", "Steering", "Clutch / Handbrake"),
                        vertical_spacing=0.08)
    
    dist = df['stage_distance']
    
    fig.add_trace(go.Scatter(x=dist, y=df['throttle'], name='Throttle',
                             line=dict(color='#00ff88', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=dist, y=df['brake'], name='Brake',
                             line=dict(color='#ff4444', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=dist, y=df['steer'], name='Steering',
                             line=dict(color='#ffaa00', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=dist, y=df['clutch'], name='Clutch',
                             line=dict(color='#00ccff', width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=dist, y=df['handbrake'], name='Handbrake',
                             line=dict(color='#ff66ff', width=1)), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=500, showlegend=True,
                      margin=dict(l=50, r=20, t=40, b=40))
    fig.update_xaxes(title_text="Distancia (m)", row=3, col=1)
    return fig

def plot_gg_diagram(df):
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=df['g_force_lat'], y=df['g_force_lon'],
        mode='markers', marker=dict(
            size=2, color=df['speed_kmh'],
            colorscale='Turbo', showscale=True,
            colorbar=dict(title="km/h")
        ),
        name='G-G'
    ))
    fig.update_layout(
        title="Diagrama G-G (color = velocidad)",
        xaxis_title="G Lateral", yaxis_title="G Longitudinal",
        template="plotly_dark", height=400,
        xaxis=dict(scaleanchor="y", scaleratio=1),
        margin=dict(l=50, r=20, t=40, b=40)
    )
    return fig

def plot_track_map(df):
    fig = go.Figure()
    fig.add_trace(go.Scattergl(
        x=df['pos_x'], y=df['pos_z'],
        mode='markers', marker=dict(
            size=2, color=df['speed_kmh'],
            colorscale='Turbo', showscale=True,
            colorbar=dict(title="km/h")
        ),
        name='Track'
    ))
    fig.update_layout(
        title="Track Map (color = velocidad)",
        xaxis_title="X", yaxis_title="Z",
        template="plotly_dark", height=400,
        xaxis=dict(scaleanchor="y", scaleratio=1),
        margin=dict(l=50, r=20, t=40, b=40)
    )
    return fig

# --- Tab: Stage Analysis ---
def render_stage_tab():
    st.header("🏁 Análisis de Etapa")
    
    report = load_stage_report()
    
    if report is None:
        st.info("ℹ️ No hay reporte de etapa. Ejecuta `dr2_recorder.py` y completa una etapa en DR2.")
        return
    
    cs = report.get('current_stage', {})
    stages = report.get('stages', [])
    
    if not stages and cs.get('samples', 0) == 0:
        st.warning("El recorder está corriendo pero aún no hay datos suficientes.")
        return
    
    # Show last completed stage if available, else current
    if stages:
        last_stage = stages[-1]
        st.success(f"🏁 Última etapa completada | {last_stage.get('track_length', 0):.0f}m")
    else:
        last_stage = cs
        st.info("📍 Etapa en progreso...")
    
    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    
    stage_time = last_stage.get('stage_time', 0)
    if stage_time > 0:
        m, s = divmod(stage_time, 60)
        k1.metric("Tiempo", f"{int(m):02d}:{s:06.3f}")
    else:
        k1.metric("Tiempo", "En curso...")
    
    k2.metric("V. Máxima", f"{last_stage.get('max_speed_kmh', 0):.1f} km/h")
    k3.metric("V. Promedio", f"{last_stage.get('avg_speed_kmh', 0):.1f} km/h")
    k4.metric("G-Lat Máx", f"{last_stage.get('max_g_lat', 0):.2f} G")
    k5.metric("G-Lon Máx", f"{last_stage.get('max_g_lon', 0):.2f} G")
    
    # Gear distribution
    gear_dist = last_stage.get('gear_distribution', {})
    if gear_dist:
        st.subheader("⚙️ Distribución de Marchas")
        total = sum(gear_dist.values())
        gear_cols = st.columns(min(len(gear_dist), 8))
        for i, (gear, count) in enumerate(sorted(gear_dist.items(), key=lambda x: int(x[0]))):
            pct = (count / total) * 100
            label = "R" if gear == "10" else ("N" if gear == "0" else f"G{gear}")
            gear_cols[i % len(gear_cols)].metric(label, f"{pct:.1f}%")
    
    # Handbrake usage
    hb = last_stage.get('handbrake_count', 0)
    samples = last_stage.get('samples', 1)
    st.metric("🅿️ Freno de mano", f"{hb} activaciones ({(hb/samples)*100:.1f}% del tiempo)")
    
    # Load telemetry for detailed plots
    st.divider()
    st.subheader("📊 Telemetría Detallada")
    
    # Get the latest session from DB
    all_stages = get_all_stages()
    if not all_stages.empty:
        latest_session = all_stages.iloc[0]['session_id']
        
        if st.button("📈 Cargar Telemetría Detallada", key="load_telem"):
            with st.spinner("Cargando..."):
                df = get_stage_telemetry(latest_session)
            
            if not df.empty:
                # Speed trace
                st.plotly_chart(plot_speed_trace(df), use_container_width=True, key="speed_trace")
                
                # Inputs
                st.plotly_chart(plot_inputs(df), use_container_width=True, key="inputs_trace")
                
                # G-G and Track map side by side
                col_gg, col_map = st.columns(2)
                with col_gg:
                    st.plotly_chart(plot_gg_diagram(df), use_container_width=True, key="gg_diag")
                with col_map:
                    st.plotly_chart(plot_track_map(df), use_container_width=True, key="track_map")
            else:
                st.warning("No hay telemetría detallada para esta sesión.")
    
    # Stage history
    if stages:
        st.divider()
        st.subheader("📋 Etapas Completadas")
        stage_data = []
        for i, s in enumerate(stages):
            t = s.get('stage_time', 0)
            m, sec = divmod(t, 60)
            stage_data.append({
                "Etapa": i + 1,
                "Tiempo": f"{int(m):02d}:{sec:06.3f}",
                "V.Max": f"{s.get('max_speed_kmh', 0):.1f}",
                "V.Avg": f"{s.get('avg_speed_kmh', 0):.1f}",
                "G-Lat": f"{s.get('max_g_lat', 0):.2f}",
                "Largo": f"{s.get('track_length', 0):.0f}m",
            })
        st.table(stage_data)


# --- Tab: Progress Analysis ---
def render_progress_tab():
    st.header("📈 Progreso de Rally")
    st.markdown("Evolución a través de todas tus etapas grabadas.")
    
    stages = get_all_stages()
    
    if stages.empty:
        st.warning("No hay etapas suficientes en la base de datos.")
        return
    
    st.caption(f"📊 {len(stages)} etapas | {stages['samples'].sum():,.0f} data points")
    
    # Global KPIs
    st.subheader("🏆 Mejores Marcas")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Etapas", len(stages))
    k2.metric("Top Speed", f"{stages['top_speed'].max():.1f} km/h")
    k3.metric("Mejor V.Avg", f"{stages['avg_speed'].max():.1f} km/h")
    k4.metric("G-Lat Máx", f"{stages['max_g_lat'].max():.2f} G")
    k5.metric("Handbrake Máx", f"{stages['handbrake_pct'].max():.1f}%")
    
    # Evolution charts
    st.subheader("📈 Evolución por Etapa")
    
    stages_sorted = stages.sort_values('session_start')
    labels = [f"E{i+1}" for i in range(len(stages_sorted))]
    
    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=("Top Speed (km/h)", "Vel. Promedio (km/h)", 
                                       "% Full Throttle", "% Handbrake"),
                        vertical_spacing=0.12, horizontal_spacing=0.1)
    
    fig.add_trace(go.Scatter(x=labels, y=stages_sorted['top_speed'],
                             mode='lines+markers', line=dict(color='#00ff88', width=2),
                             marker=dict(size=8)), row=1, col=1)
    fig.add_trace(go.Scatter(x=labels, y=stages_sorted['avg_speed'],
                             mode='lines+markers', line=dict(color='#ffaa00', width=2),
                             marker=dict(size=8)), row=1, col=2)
    fig.add_trace(go.Scatter(x=labels, y=stages_sorted['full_throttle_pct'],
                             mode='lines+markers', line=dict(color='#ff4444', width=2),
                             marker=dict(size=8)), row=2, col=1)
    fig.add_trace(go.Scatter(x=labels, y=stages_sorted['handbrake_pct'],
                             mode='lines+markers', line=dict(color='#ff66ff', width=2),
                             marker=dict(size=8)), row=2, col=2)
    
    fig.update_layout(height=500, template="plotly_dark", showlegend=False,
                      title_text="Evolución de Rendimiento")
    st.plotly_chart(fig, use_container_width=True, key="evo_chart")
    
    # Session table
    st.subheader("📋 Historial de Etapas")
    display = stages_sorted[['session_start', 'samples', 'top_speed', 'avg_speed', 
                              'full_throttle_pct', 'handbrake_pct', 'max_g_lat', 'stage_length']].copy()
    display.columns = ['Fecha', 'Samples', 'V.Max', 'V.Avg', 'Throttle%', 'Handbrake%', 'G-Lat', 'Largo(m)']
    display['Fecha'] = pd.to_datetime(display['Fecha']).dt.strftime('%d/%m %H:%M')
    for col in ['V.Max', 'V.Avg', 'Throttle%', 'Handbrake%']:
        display[col] = display[col].round(1)
    display['G-Lat'] = display['G-Lat'].round(2)
    display['Largo(m)'] = display['Largo(m)'].round(0)
    st.dataframe(display, use_container_width=True)
    
    # Compare 2 stages
    if len(stages_sorted) >= 2:
        st.subheader("🔍 Comparar Etapas")
        
        opts = [f"E{i+1} | {pd.to_datetime(r['session_start']).strftime('%d/%m %H:%M')} | {r['top_speed']:.0f} km/h ({r['samples']:,.0f} pts)"
                for i, (_, r) in enumerate(stages_sorted.iterrows())]
        
        ca, cb = st.columns(2)
        with ca:
            idx_a = st.selectbox("Etapa A", range(len(opts)), format_func=lambda x: opts[x], key="dr2_a")
        with cb:
            idx_b = st.selectbox("Etapa B", range(len(opts)), index=min(1, len(opts)-1), format_func=lambda x: opts[x], key="dr2_b")
        
        if st.button("⚡ Comparar", key="dr2_compare"):
            sa = stages_sorted.iloc[idx_a]
            sb = stages_sorted.iloc[idx_b]
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("V.Max A→B", f"{sb['top_speed']:.1f}", f"{sb['top_speed']-sa['top_speed']:+.1f}")
            m2.metric("V.Avg A→B", f"{sb['avg_speed']:.1f}", f"{sb['avg_speed']-sa['avg_speed']:+.1f}")
            m3.metric("Throttle A→B", f"{sb['full_throttle_pct']:.1f}%", f"{sb['full_throttle_pct']-sa['full_throttle_pct']:+.1f}%")
            m4.metric("G-Lat A→B", f"{sb['max_g_lat']:.2f}", f"{sb['max_g_lat']-sa['max_g_lat']:+.2f}")
            
            # Overlay speed traces
            with st.spinner("Cargando telemetría..."):
                df_a = get_stage_telemetry(sa['session_id'])
                df_b = get_stage_telemetry(sb['session_id'])
            
            if not df_a.empty and not df_b.empty:
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Scatter(
                    x=df_a['stage_distance'], y=df_a['speed_kmh'],
                    mode='lines', name='Etapa A', line=dict(color='#ff6b6b', width=1.5)))
                fig_comp.add_trace(go.Scatter(
                    x=df_b['stage_distance'], y=df_b['speed_kmh'],
                    mode='lines', name='Etapa B', line=dict(color='#4ecdc4', width=1.5)))
                fig_comp.update_layout(
                    title="Comparación Speed Trace",
                    xaxis_title="Distancia (m)", yaxis_title="km/h",
                    template="plotly_dark", height=400)
                st.plotly_chart(fig_comp, use_container_width=True, key="dr2_speed_comp")


# --- Main ---
def main():
    st.title("🏁 Dirt Rally 2.0 - Telemetry Dashboard")
    st.caption("Análisis de rally con datos UDP en tiempo real")
    
    with st.sidebar:
        st.title("🏔️ DR2 Telemetry")
        st.caption("Recorder → DuckDB → Dashboard")
        st.divider()
        st.markdown("""
        **Flujo:**
        1. Edita `hardware_settings_config.xml`
        2. Ejecuta `start_dr2.sh`
        3. Juega una etapa
        4. Analiza aquí
        """)
    
    tab_stage, tab_progress = st.tabs(["🏁 Etapa Actual", "📈 Progreso"])
    
    with tab_stage:
        render_stage_tab()
    
    with tab_progress:
        render_progress_tab()


if __name__ == "__main__":
    main()
