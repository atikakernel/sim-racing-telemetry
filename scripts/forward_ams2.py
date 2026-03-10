
import mmap
import time
import socket
import json
import ctypes
import os
from windows_ams2_shm import SharedMemoryV2

# Config
WSL_PORT = 5607  # Different port for SHM JSON feed to avoid conflict with UDP 5606

def detect_wsl_ip():
    import subprocess
    try:
        result = subprocess.run(["wsl", "hostname", "-I"], capture_output=True, text=True, timeout=5)
        ip = result.stdout.strip().split()[0]
        if ip: return ip
    except: pass
    return "172.23.190.180"

WSL_IP = detect_wsl_ip()

def main():
    print(f"AMS2 Shared Memory Forwarder (SHM -> UDP {WSL_PORT})")
    print("Waiting for AMS2...")

    # Descubierto por el sniffer: Local\$pcars2$
    shm_name = "Local\\$pcars2$"
    
    while True:
        try:
            # Forzamos mapear 16KB para que quepan todos los offsets de PCars2
            shm = mmap.mmap(0, 16384, shm_name)
            print(f"Connected to {shm_name} (16KB Buffer)!")
            break
        except FileNotFoundError:
            time.sleep(1)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_print = 0

    while True:
        try:
            shm.seek(0)
            data_raw = shm.read(12000)
            
            # Offsets corregidos y estimados:
            # 6844: Fuel (float)
            # 6848: Speed (float)
            # 6852: RPM (float)
            # 6856: MaxRPM (float)
            # 6860: Steering (float)
            # 6876: Gear (int)
            # 6884: Odometer (float)
            # 7052: Tyre Tread Temp (4 floats)
            # 7164: Brake Temp (4 floats)
            # 7116: Tyre Wear (4 floats)
            # 8: GameState (uint)
            # 12: SessionState (uint)
            
            import struct
            speed_ms = struct.unpack_from("f", data_raw, 6848)[0]
            rpm = struct.unpack_from("f", data_raw, 6852)[0]
            max_rpm = struct.unpack_from("f", data_raw, 6856)[0]
            steering = struct.unpack_from("f", data_raw, 6860)[0]
            gear_raw = struct.unpack_from("i", data_raw, 6876)[0]
            fuel = struct.unpack_from("f", data_raw, 6844)[0]
            throttle = struct.unpack_from("f", data_raw, 6840)[0]
            brake = struct.unpack_from("f", data_raw, 6836)[0]
            odometer = struct.unpack_from("f", data_raw, 6884)[0]
            
            # Temps (Arrays de 4 floats)
            tyre_temps = list(struct.unpack_from("ffff", data_raw, 7052))
            brake_temps = list(struct.unpack_from("ffff", data_raw, 7164))
            tyre_wear = list(struct.unpack_from("ffff", data_raw, 7116))
            
            # States
            game_state = struct.unpack_from("I", data_raw, 8)[0]
            session_state = struct.unpack_from("I", data_raw, 12)[0]
            
            # Pit Status (Mapeamos mCarFlags a offset 6833? No, probamos con bit de mGameState o similar)
            # Por ahora simplificamos: si la velocidad es < 5 y estamos en una zona de pit (esto lo detectará el recorder)
            # Pero enviamos el raw de mCarFlags si lo encontramos. 
            # Según dumper, hay un byte interesante cerca de 6833.
            car_flags = data_raw[6833] if len(data_raw) > 6833 else 0
            is_in_pit = bool(car_flags & 1)

            # Normalización de marchas
            gear = gear_raw
            if gear == 15: gear = -1
            
            # Map to common JSON format (mantenemos compatibilidad con tu dashboard)
            packet = {
                "timestamp": time.time(),
                "game_state": game_state,
                "session_state": session_state,
                "speed_kmh": speed_ms * 3.6,
                "rpm": rpm,
                "max_rpm": max_rpm,
                "gear": gear,
                "throttle": min(1.0, max(0.0, throttle)) if throttle < 1.1 else 0,
                "brake": min(1.0, max(0.0, brake)) if brake < 1.1 else 0,
                "clutch": 0,
                "steering": steering,
                "g_force_lat": 0,
                "g_force_lon": 0,
                "fuel": fuel,
                "odometer_km": odometer,
                "tyre_temp": tyre_temps,
                "brake_temp": brake_temps,
                "tyre_wear": tyre_wear,
                "is_in_pit": is_in_pit
            }

            msg = json.dumps(packet).encode('utf-8')
            sock.sendto(msg, (WSL_IP, WSL_PORT))

            if time.time() - last_print > 1.0:
                print(f"Relaying... RPM: {int(rpm)} | Gear: {gear} | Pit: {is_in_pit} | State: {game_state}")
                last_print = time.time()

            time.sleep(0.01) # 100 Hz
            
        except KeyboardInterrupt: break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
