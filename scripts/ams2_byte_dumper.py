
import mmap
import time
import struct

shm_name = "Local\\$pcars2$"

def main():
    print("--- AMS2 BYTE DUMPER ---")
    try:
        shm = mmap.mmap(0, 16384, shm_name)
    except FileNotFoundError:
        print("❌ Memoria no encontrada.")
        return

    print("Analizando zona 6800-8000...")
    while True:
        try:
            shm.seek(0)
            data = shm.read(12000)
            
            # Dump zone
            start = 6800
            end = 8000
            print("\n" + "="*50)
            # Imprimimos de 16 en 16 bytes para ver los arrays de 4 floats (4x4=16)
            for i in range(start, end, 16):
                vals = []
                for j in range(4):
                    vals.append(struct.unpack_from("f", data, i + j*4)[0])
                
                # Solo imprimimos si hay algo que parezca un dato (no todo ceros)
                if any(abs(v) > 0.1 for v in vals):
                    print(f"Offset {i:4d} | {vals[0]:8.2f} {vals[1]:8.2f} {vals[2]:8.2f} {vals[3]:8.2f}")
            
            time.sleep(2)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
