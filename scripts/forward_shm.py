
import mmap
import time
import socket
import json
import ctypes
import os
from windows_acc_shm import SPageFilePhysics, SPageFileGraphics, SPageFileStatic

# Config
WSL_PORT = 9002  # Custom port for our JSON Physics Feed

def detect_wsl_ip():
    """Auto-detect WSL IP address"""
    import subprocess
    try:
        result = subprocess.run(
            ["wsl", "hostname", "-I"],
            capture_output=True, text=True, timeout=5
        )
        ip = result.stdout.strip().split()[0]
        if ip:
            print(f"🔍 Auto-detected WSL IP: {ip}")
            return ip
    except Exception:
        pass
    fallback = "172.23.190.180"
    print(f"⚠️ Could not auto-detect WSL IP, using fallback: {fallback}")
    return fallback

WSL_IP = detect_wsl_ip()

TRACK_MAP = {
    "monza_2020": "Monza",
    "monza": "Monza",
    "spa_2019": "Spa",
    "spa": "Spa",
    "nurburgring_2020": "Nurburgring",
    "nurburgring": "Nurburgring",
    "silverstone_2020": "Silverstone",
    "silverstone": "Silverstone",
    "paul_ricard_2020": "Paul Ricard",
    "paul_ricard": "Paul Ricard",
    "misano_2020": "Misano",
    "misano": "Misano",
    "zandvoort_2020": "Zandvoort",
    "zandvoort": "Zandvoort",
    "brands_hatch_2020": "Brands Hatch",
    "brands_hatch": "Brands Hatch",
    "hungaroring_2020": "Hungaroring",
    "hungaroring": "Hungaroring",
    "barcelona_2020": "Barcelona",
    "barcelona": "Barcelona",
    "imola_2020": "Imola",
    "imola": "Imola",
    "mount_panorama_2019": "Bathurst",
    "mount_panorama": "Bathurst",
    "suzuka_2019": "Suzuka",
    "suzuka": "Suzuka",
    "kyalami_2019": "Kyalami",
    "kyalami": "Kyalami",
    "laguna_seca_2019": "Laguna Seca",
    "laguna_seca": "Laguna Seca",
    "zolder_2020": "Zolder",
    "zolder": "Zolder",
    "donington_2019": "Donington",
    "donington": "Donington",
    "snetterton_2019": "Snetterton",
    "snetterton": "Snetterton",
    "oulton_park_2019": "Oulton Park",
    "oulton_park": "Oulton Park",
    "valencia_2021": "Valencia",
    "valencia": "Valencia"
}

def normalize_track(track_raw):
    """Cleans ACC track names (e.g. monza_2020 -> Monza)"""
    try:
        raw = track_raw.decode('utf-8', errors='ignore').strip()
    except:
        raw = str(track_raw)
    return TRACK_MAP.get(raw, raw.replace("_2019", "").replace("_2020", "").replace("_", " ").title())

def main():
    print(f"ACC Shared Memory Forwarder (Physics -> UDP {WSL_PORT})")
    print("Waiting for ACC...")

    # Open Shared Memory
    while True:
        try:
            shm_phys = mmap.mmap(0, ctypes.sizeof(SPageFilePhysics), "Local\\acpmf_physics")
            shm_graph = mmap.mmap(0, ctypes.sizeof(SPageFileGraphics), "Local\\acpmf_graphics")
            shm_stat = mmap.mmap(0, ctypes.sizeof(SPageFileStatic), "Local\\acpmf_static")
            print("Connected to ACC Shared Memory!")
            break
        except FileNotFoundError:
            time.sleep(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    last_print = 0

    while True:
        try:
            # Read Physics
            shm_phys.seek(0)
            phys_data = shm_phys.read(ctypes.sizeof(SPageFilePhysics))
            phys = SPageFilePhysics.from_buffer_copy(phys_data)

            # Read Graphics
            shm_graph.seek(0)
            graph_data = shm_graph.read(ctypes.sizeof(SPageFileGraphics))
            graph = SPageFileGraphics.from_buffer_copy(graph_data)

            # Read Static (Less frequent, but we'll peek)
            shm_stat.seek(0)
            stat_data = shm_stat.read(ctypes.sizeof(SPageFileStatic))
            stat = SPageFileStatic.from_buffer_copy(stat_data)

            # Data Packet
            data = {
                "timestamp": time.time(),
                "packetId": phys.packetId,
                "track": normalize_track(stat.track),
                "car": stat.carModel,
                "rpms": phys.rpms,
                "speedKmh": phys.speedKmh,
                "gear": phys.gear - 1,  # 0=R, 1=N, 2=1st...
                "throttle": phys.gas,
                "brake": phys.brake,
                "fuel_rem": phys.fuel,
                "steerAngle": phys.steerAngle,
                # G-Forces (real values from physics)
                "g_force": list(phys.accG),  # [x=lateral, y=vertical, z=longitudinal]
                # Tyres
                "tyre_press": list(phys.wheelsPressure),
                "tyre_temp": list(phys.tyreCoreTemperature),
                "tyre_temp_omi": {
                    "i": list(phys.tyreTempI),
                    "m": list(phys.tyreTempM),
                    "o": list(phys.tyreTempO)
                },
                "brake_temp": list(phys.brakeTemp),
                "brake_press": list(phys.brakePressure),
                "pad_life": list(phys.padLife),
                "tyre_wear": list(phys.tyreWear),
                "ride_height": list(phys.rideHeight),  # [Front, Rear]
                "suspension_travel": list(phys.suspensionTravel),
                # Wheel slip (traction analysis)
                "wheel_slip": list(phys.wheelSlip),  # [FL, FR, RL, RR]
                # TC/ABS as float (intensity) + bool for compatibility
                "tc_value": phys.tc,
                "abs_value": phys.abs,
                "tc_active": int(phys.tc > 0),
                "abs_active": int(phys.abs > 0),
                # Brake bias
                "brake_bias": phys.brakeBias,
                # Car damage (5 zones)
                "car_damage": list(phys.carDamage),
                # Ambient conditions
                "air_temp": phys.airTemp,
                "road_temp": phys.roadTemp,
                "water_temp": phys.waterTemp,
                # Graphics - Timing
                "status": graph.status,
                "session": graph.session,
                "completedLaps": graph.completedLaps,
                "iCurrentTime": graph.iCurrentTime,
                "iLastTime": graph.iLastTime,
                "iBestTime": graph.iBestTime,
                "iDeltaLapTime": graph.iDeltaLapTime,
                "isInPitLane": graph.isInPitLane,
                "isValidLap": graph.isValidLap,
                # Electronics settings (level chosen, not activation)
                "tc_setting": graph.TC,
                "tc_cut_setting": graph.TCCut,
                "abs_setting": graph.ABS,
                "engine_map": graph.EngineMap,
                # Fuel strategy
                "fuel_per_lap": graph.fuelXLap,
                # Wind conditions
                "wind_speed": graph.windSpeed,
                "wind_direction": graph.windDirection,
                # Distance
                "distance_traveled": graph.distanceTraveled,
                # Sectors & Position
                "sector": graph.currentSectorIndex,       # 0, 1, 2
                "last_sector_time": graph.lastSectorTime,  # ms
                "split_time": graph.iSplit,                 # ms
                "track_position": graph.normalizedCarPosition,  # 0.0-1.0
            }

            # Send UDP
            msg = json.dumps(data).encode('utf-8')
            sock.sendto(msg, (WSL_IP, WSL_PORT))

            if time.time() - last_print > 1.0:
                print(f"Sending... Speed: {phys.speedKmh:.1f} km/h | FPS: TBD")
                last_print = time.time()

            time.sleep(0.02)  # 50 Hz
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    # Allow user to pass IP as arg
    import sys
    if len(sys.argv) > 1:
        WSL_IP = sys.argv[1]
    main()
