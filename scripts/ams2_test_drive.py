
import mmap
import time
import ctypes
from windows_ams2_shm import SharedMemoryV2

# Config
shm_name = "Local\\$-cre-sm-p-cars-2-$"
shm_size = ctypes.sizeof(SharedMemoryV2)

def main():
    print("--- AMS2 ACTIVITY MONITOR ---")
    print(f"Buscando: {shm_name}")
    print("INSTRUCCIONES:")
    print("1. Deja este script corriendo.")
    print("2. Entra al juego y DA UNA VUELTA (o muévete un poco).")
    print("3. Vuelve aquí y presiona Ctrl+C para ver el resumen.")
    print("-" * 30)

    shm = None
    while not shm:
        try:
            shm = mmap.mmap(0, shm_size, shm_name)
            print("✅ Conectado a la memoria. Esperando datos...")
        except FileNotFoundError:
            time.sleep(1)

    max_speed = 0
    max_rpm = 0
    packets_seen = 0
    states_seen = set()

    try:
        while True:
            shm.seek(0)
            data = shm.read(shm_size)
            sm = SharedMemoryV2.from_buffer_copy(data)
            
            states_seen.add(sm.mGameState)
            
            if sm.mSpeed > 0:
                packets_seen += 1
                speed_kmh = sm.mSpeed * 3.6
                if speed_kmh > max_speed: max_speed = speed_kmh
                if sm.mRpm > max_rpm: max_rpm = sm.mRpm
            
            if packets_seen > 0 and packets_seen % 100 == 0:
                print(f"\rCapturando... Speed actual: {sm.mSpeed*3.6:.1f} kmh", end="")
            
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n\n--- RESUMEN DE LA SESIÓN ---")
        print(f"Estados del juego detectados: {list(states_seen)}")
        print(f"Paquetes con movimiento (>0 km/h): {packets_seen}")
        print(f"Velocidad Máxima alcanzada: {max_speed:.1f} km/h")
        print(f"RPM Máximo alcanzado: {max_rpm:.1f}")
        
        if packets_seen > 0:
            print("\n✅ ¡SÍ ESTÁ LLEGANDO INFORMACIÓN!")
            print("Ahora puedes cerrar esto y correr 'forward_ams2.py'.")
        else:
            print("\n❌ NO SE DETECTÓ MOVIMIENTO.")
            print("Asegúrate de que en Opciones > Sistema > Shared Memory diga 'Project CARS 2'.")
    finally:
        if shm: shm.close()

if __name__ == "__main__":
    main()
