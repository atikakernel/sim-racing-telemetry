
import mmap
import time

# Lista de todos los nombres sospechosos
nombres = [
    "$-cre-sm-p-cars-2-$",
    "Local\\$-cre-sm-p-cars-2-$",
    "pCARS2API",
    "Local\\pCARS2API",
    "ProjectCARS2SharedMemory",
    "Local\\ProjectCARS2SharedMemory",
    "$pcars2$",
    "Local\\$pcars2$",
    "$PCSC$",
    "Local\\$PCSC$"
]

print("--- SNIFFER DE SHARED MEMORY ---")
print("Este script buscará cuál de estas memorias tiene DATOS de verdad.")
print("Por favor, entra a pista y acelera mientras esto corre.\n")

shms = []
for n in nombres:
    try:
        # Intentamos abrir 4KB de cada una
        s = mmap.mmap(0, 4096, n)
        shms.append((n, s))
        print(f"✅ Memoria encontrada: {n}")
    except FileNotFoundError:
        pass

if not shms:
    print("\n❌ No se encontró ninguna memoria. ¿Seguro que el juego está abierto?")
else:
    print("\n🧐 Escaneando por datos cambiantes (10 segundos)...")
    for _ in range(20):
        found_data = False
        for nombre, shm in shms:
            shm.seek(0)
            data = shm.read(20)
            # Si hay algo que no sea cero
            if any(b != 0 for b in data):
                print(f"\r🔥 ¡DATOS DETECTADOS EN: {nombre}! -> {data[:10].hex(' ')}", end="")
                found_data = True
        
        if not found_data:
            print("\r💤 Todos los canales siguen en cero...", end="")
        
        time.sleep(0.5)

for n, s in shms: s.close()
print("\n\nEscaneo terminado.")
