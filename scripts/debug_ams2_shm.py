
import mmap
import time

def check_shm(name):
    try:
        # Intento con y sin prefijo Local\\
        names_to_try = [name, f"Local\\{name}"]
        for n in names_to_try:
            try:
                shm = mmap.mmap(0, 1024, n)
                print(f"✅ Encontrado: {n}")
                data = shm.read(12)
                print(f"   Primeros 12 bytes (hex): {data.hex(' ')}")
                shm.close()
                return True
            except FileNotFoundError:
                continue
    except Exception as e:
        print(f"❌ Error probando {name}: {e}")
    return False

print("--- DIAGNÓSTICO DE SHARED MEMORY V2 ---")
print("Buscando memorias de Project CARS / AMS2...")

names_to_try = [
    "$-cre-sm-p-cars-2-$", 
    "Local\\$-cre-sm-p-cars-2-$",
    "pCARS2API",
    "Local\\pCARS2API",
    "$pcars2$",
    "Local\\$pcars2$",
    "$PCSC$",
    "Local\\$PCSC$"
]

found_names = []
for name in names_to_try:
    try:
        shm = mmap.mmap(0, 4096, name)
        print(f"✅ Encontrado: {name}")
        found_names.append(name)
        shm.close()
    except FileNotFoundError:
        continue

if not found_names:
    print("\n❌ NO SE ENCONTRÓ NINGUNA MEMORIA.")
else:
    print("\n🧐 Monitoreando cambios (muévete en el juego o entra a pista)...")
    shms = [mmap.mmap(0, 4096, n) for n in found_names]
    
    for _ in range(10):
        for i, shm in enumerate(shms):
            shm.seek(0)
            data = shm.read(16)
            print(f"[{found_names[i]}] Bytes: {data.hex(' ')}")
        time.sleep(1)
    
    for shm in shms: shm.close()
