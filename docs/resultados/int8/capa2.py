exec(open("capa.py").read().split("n = len(nombres)")[0])
for i in range(4):
    print(f"PRUEBA solo capa {i} en float ({nombres[i][-45:]}):", sin([nombres[i]]))
print("PRUEBA capas 2 y 3 en float:", sin(nombres[2:4]))
