
import mmap
import time
import struct

shm_name = "Local\\$pcars2$"

def main():
    print("--- AMS2 OFFSET HUNTER ---")
    print("Este script buscará automáticamente dónde están los datos.")
    print("INSTRUCCIONES: Entra a pista y mantén una velocidad constante (ej. 60 km/h).")
    
    try:
        shm = mmap.mmap(0, 16384, shm_name)
    except FileNotFoundError:
        print("❌ No se encontró la memoria. Abre el juego.")
        return

    while True:
        try:
            shm.seek(0)
            blob = shm.read(12000)
            
            # Buscamos floats razonables
            # Speed (m/s), RPM, etc.
            print("\rAnalizando...", end="")
            
            found = []
            # Escaneamos cada 4 bytes
            for i in range(0, 12000 - 4, 4):
                val_f = struct.unpack("f", blob[i:i+4])[0]
                val_i = struct.unpack("i", blob[i:i+4])[0]
                
                # Ejemplo de Speed (~20 m/s = 72 km/h)
                if 5.0 < val_f < 100.0:
                    # Podría ser speed
                    found.append((i, "float", val_f))
                
                # Ejemplo de RPM (> 1000)
                if 1000 < val_f < 15000:
                    found.append((i, "RPM?", val_f))

            # Filtramos los que más se repiten o tienen sentido
            # Si el usuario acelera, estos deberían cambiar.
            # Tomamos una muestra y comparamos
            time.sleep(1)
            shm.seek(0)
            blob2 = shm.read(12000)
            
            print("\n--- POSIBLES OFFSETS ENCONTRADOS ---")
            for offset, kind, val in found:
                val2_f = struct.unpack("f", blob2[offset:offset+4])[0]
                if abs(val2_f - val) > 0.01: # Si cambió, es dinámico (buena señal)
                    print(f"Offset {offset:5d}: {kind:6s} | Antes: {val:8.2f} | Ahora: {val2_f:8.2f} (CAMBIA ✅)")
            
            print("\nPresiona Ctrl+C para detener y pasarme los resultados.")
            time.sleep(2)
            
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
