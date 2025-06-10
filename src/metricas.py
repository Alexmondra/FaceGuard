import matplotlib.pyplot as plt
import pandas as pd

# Ruta del archivo log
log_file = "../models/metricas_con_camaras_seguimiento.log"

data = pd.read_csv(
    log_file,
    sep=r'\s+',  # Maneja múltiples espacios como separador
    skiprows=4,  # Salta las primeras 4 líneas de encabezado
    engine="python",
    on_bad_lines="skip",  # Ignora líneas con problemas
)

print("Columnas detectadas automáticamente:")
print(data.columns)

num_columns = len(data.columns)
expected_columns = [
    "time", "AM/PM", "UID", "TGID", "TID", "%usr", "%system", "%guest", "%wait", "%CPU", "CPU", "Command"
]
data.columns = expected_columns[:num_columns]

print("Datos cargados:")
print(data.head())

for col in ["%CPU", "%usr", "%system", "%wait"]:
    if col in data.columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

# Análisis de métricas
total_cpu_usage = data["%CPU"].sum()
average_cpu_usage = data["%CPU"].mean()
max_cpu_usage = data["%CPU"].max()

print("\n--- Análisis de uso de CPU ---")
print(f"Uso total del CPU (%): {total_cpu_usage:.2f}")
print(f"Uso promedio del CPU (%): {average_cpu_usage:.2f}")
print(f"Uso máximo del CPU (%): {max_cpu_usage:.2f}")

# Graficar uso de CPU por TID
plt.figure(figsize=(12, 6))
for tid, group in data.groupby("TID"):
    plt.plot(group["time"], group["%CPU"], label=f"TID: {tid}")

plt.xlabel("Tiempo")
plt.ylabel("Uso de CPU (%)")
plt.title("Uso de CPU por TID")
plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
plt.tight_layout()
plt.grid()
plt.show()

# Graficar uso cpu
plt.figure(figsize=(10, 5))
plt.bar(["Total CPU"], [total_cpu_usage], color="orange", alpha=0.7)
plt.ylabel("Uso de CPU (%)")
plt.title("Uso Total del CPU")
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.show()
