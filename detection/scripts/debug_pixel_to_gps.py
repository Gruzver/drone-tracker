#!/usr/bin/env python3

"""
Debuggea el cálculo pixel_to_gps
"""

import sys
from pathlib import Path
import json
import math

sys.path.insert(0, str(Path(__file__).parent / 'src/drone_tracker_utils'))
from drone_tracker_utils import GeoCalculator

# Datos
data_file = Path('/tmp/drone_map_data/map_data.json')

with open(data_file) as f:
    data = json.load(f)

drone = data['dron']

geo_calc = GeoCalculator(fov_horizontal=50.5)

print('='*80)
print('🔍 ANÁLISIS DETALLADO: pixel_to_gps')
print('='*80)

print('\n📐 PARÁMETROS DEL CÁLCULO:')
print(f'  Frame size: 640x512 (width x height)')
print(f'  FOV H: {geo_calc.fov_h:.1f}°')
print(f'  FOV V: {geo_calc.fov_v:.1f}°')
print(f'  Dron alt: {drone["altitude_rel"]:.2f}m')
print(f'  Pitch: {drone["pitch"]:.1f}°')
print(f'  Yaw: {drone["yaw"]:.1f}°')

# Calcular manualmente para entender

print('\n📍 PASO A PASO (ejemplo con centro de imagen):')
px, py = 320, 256  # Centro

print(f'\n1️⃣ Pixel: ({px}, {py})')

# Normalizar
x_norm = (px / 640) - 0.5
y_norm = (py / 512) - 0.5
print(f'2️⃣ Normalizado: ({x_norm:.3f}, {y_norm:.3f})')

# Convertir a ángulos
theta_h = x_norm * math.radians(geo_calc.fov_h)
theta_v = y_norm * math.radians(geo_calc.fov_v)
print(f'3️⃣ Ángulos: theta_h={math.degrees(theta_h):.1f}°, theta_v={math.degrees(theta_v):.1f}°')

# Sumar pitch
pitch_rad = math.radians(drone['pitch'])
angle_vertical_total = pitch_rad + theta_v
print(f'4️⃣ Ángulo vertical total: {math.degrees(angle_vertical_total):.1f}°')

# Distancia
tan_angle = math.tan(angle_vertical_total)
if abs(tan_angle) < 0.001:
    print(f'5️⃣ ❌ ERROR: tan({math.degrees(angle_vertical_total):.1f}°) = {tan_angle:.6f} (casi cero!)')
    print(f'   Esto produce distancia infinita o muy grande')
else:
    distance = drone['altitude_rel'] / abs(tan_angle)
    print(f'5️⃣ Distancia horizontal: {distance:.1f}m')

# Ahora probar con otros píxeles clave
print('\n\n📊 PRUEBAS EN DIFERENTES PÍXELES:')

test_pixels = [
    (320, 256, 'Centro'),
    (0, 256, 'Izquierda centro'),
    (640, 256, 'Derecha centro'),
    (320, 0, 'Arriba centro'),
    (320, 512, 'Abajo centro'),
    (0, 0, 'Arriba-izquierda'),
    (640, 512, 'Abajo-derecha'),
]

for px, py, label in test_pixels:
    loc = geo_calc.pixel_to_gps(
        bbox_center_x=px,
        bbox_center_y=py,
        latitude_dron=drone['latitude'],
        longitude_dron=drone['longitude'],
        altitude_dron=drone['altitude_rel'],
        yaw=drone['yaw'],
        pitch=drone['pitch'],
        roll=drone['roll']
    )
    
    if loc:
        print(f'{label:20} ({px:3d}, {py:3d}): {loc.distance_m:7.1f}m')
    else:
        print(f'{label:20} ({px:3d}, {py:3d}): ❌ FAILED')

# Verificar normalización
print('\n\n🔍 VERIFICAR NORMALIZACIÓN:')
print(f'  x_norm para x=0: {(0/640)-0.5:.3f} → debería ser -0.5')
print(f'  x_norm para x=640: {(640/640)-0.5:.3f} → debería ser +0.5')
print(f'  y_norm para y=0: {(0/512)-0.5:.3f} → debería ser -0.5')
print(f'  y_norm para y=512: {(512/512)-0.5:.3f} → debería ser +0.5')

print('\n' + '='*80)