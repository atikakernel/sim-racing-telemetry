# 🏎️ Sim Racing Telemetry Platform

Real-time telemetry capture, analytics lakehouse, and AI-powered race engineering for sim racing.

Built with **Python**, **dbt**, **DuckDB**, and **Streamlit** — running on **WSL2** with UDP telemetry forwarded from Windows.

---

## 🎮 Supported Sims

| Sim | Telemetry Source | Status |
|-----|-----------------|--------|
| **Assetto Corsa Competizione** | Shared Memory → UDP | ✅ Full pipeline |
| **Automobilista 2** | Shared Memory → UDP | ✅ Full pipeline |
| **DiRT Rally 2.0** | Native UDP | ✅ Full pipeline |

---

## 🏗️ Architecture

```
Windows (Gaming PC)                    WSL2 (Data Platform)
┌─────────────────────┐               ┌──────────────────────────────┐
│  Racing Sim (ACC)   │  UDP/SHM      │  Recorder (Python)           │
│  Racing Sim (AMS2)  │──────────────▶│    ↓                         │
│  Racing Sim (DR2)   │  Forwarder    │  DuckDB Lakehouse (dbt)      │
└─────────────────────┘  (PowerShell) │    ↓                         │
                                      │  Streamlit Dashboard         │
                                      │    ↓                         │
                                      │  AI Race Engineer (Gemini)   │
                                      └──────────────────────────────┘
```

---

## 📁 Project Structure

```
├── apps/                  # Streamlit dashboards
│   ├── app_acc.py         # ACC telemetry dashboard
│   ├── app_ams2.py        # AMS2 telemetry dashboard
│   └── app_dr2.py         # DR2 telemetry dashboard
├── games/                 # Game-specific recorders & data structs
│   ├── ams2/              # AMS2 recorder + shared memory structs
│   └── dr2/               # DR2 recorder + UDP packet structs
├── scripts/               # Utilities & forwarders
│   ├── acc_forwarder.ps1  # Windows → WSL UDP forwarder (ACC)
│   ├── acc_recorder_v2.py # ACC telemetry recorder
│   ├── forward_ams2.py    # AMS2 shared memory forwarder
│   └── ...                # Debug tools & helpers
├── lakehouse/             # Data lakehouse
│   └── lakehouse_project/ # dbt project (models, seeds, macros)
├── assets/                # Audio & image assets
├── start_engineer.sh      # Launch ACC pipeline (recorder + dashboard)
├── start_ams2.sh          # Launch AMS2 pipeline
└── start_dr2.sh           # Launch DR2 pipeline
```

---

## 🚀 Quick Start

```bash
# 1. On Windows: Start the UDP forwarder
.\scripts\acc_forwarder.ps1

# 2. On WSL: Launch the full pipeline
./start_engineer.sh
```

This starts the telemetry recorder and Streamlit dashboard. Open `http://localhost:8501` for the live dashboard.

---

## 🔧 Tech Stack

- **Python 3** — Telemetry capture, data processing
- **dbt + DuckDB** — Analytics lakehouse (bronze → silver → gold)
- **Streamlit** — Real-time dashboards
- **Google Gemini** — AI race engineer feedback
- **PowerShell** — Windows shared memory → UDP forwarding

---

## 📄 License

Personal project. All rights reserved.
