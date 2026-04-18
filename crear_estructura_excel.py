# crear_estructura_excel.py
# Script para crear un archivo Excel de ejemplo
import pandas as pd
from datetime import datetime, timedelta
import random

# Generar datos de ejemplo para el mes actual
fecha_inicio = datetime.now().replace(day=1)
dias = (datetime.now() - fecha_inicio).days + 1

datos = []
for i in range(dias):
    fecha = fecha_inicio + timedelta(days=i)
    ventas = random.randint(25000000, 45000000)
    tickets = random.randint(300, 500)
    visitas = random.randint(800, 1500)
    articulos_por_ticket = random.uniform(2.5, 4.5)
    
    datos.append({
        'fecha': fecha.strftime('%Y-%m-%d'),
        'ventas': ventas,
        'tickets': tickets,
        'visitas': visitas,
        'articulos_ticket': round(articulos_por_ticket, 1)
    })

df = pd.DataFrame(datos)
df.to_excel('ventas_ejemplo.xlsx', index=False)
print("✅ Archivo 'ventas_ejemplo.xlsx' creado exitosamente")