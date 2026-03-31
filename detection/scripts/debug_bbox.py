#!/usr/bin/env python3

"""
debug_bbox.py
Debuggea la relación entre bbox y GPS calculado
"""

import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / 'src/drone_tracker_utils'))
from drone_tracker_utils import GeoCalculator

# Cargar datos
data_file = Path('/tmp/drone_map_data/map_data.json')

if not data_file.exists():
    print('❌ No hay datos')
    exit(1)

with open(data_file) as f:
    data = json.load(f)

drone = data['dron']
persons = data['persons']

geo_calc = GeoCalculator(fov_horizontal=50.5)

print('='*80)
print('🔍 DEBUG BBOX → GPS')
print('='*80)

print('\n🚁 DRON (de referencia):')
print(f'  Lat: {drone["latitude"]:.6f}')
print(f'  Lon: {drone["longitude"]:.6f}')
print(f'  Alt: {drone["altitude_rel"]:.2f}m')
print(f'  Yaw: {drone["yaw"]:.1f}°')
print(f'  Pitch: {drone["pitch"]:.1f}°')

print('\n📍 ANÁLISIS DE FOV:')
print(f'  FOV H: {geo_calc.fov_h:.1f}°')
print(f'  FOV V: {geo_calc.fov_v:.1f}°')

# Calcular corners esperados
corners = [
    (0, 0),           # Top-left
    (640, 0),         # Top-right
    (640, 512),       # Bottom-right
    (0, 512),         # Bottom-left
    (320, 256),       # Centro
]

print('\n  Corners del FOV (calculados):')
for px, py in corners:
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
        label = '(Center)' if px == 320 else ''
        print(f'    ({px:3d}, {py:3d}) → Dist: {loc.distance_m:7.1f}m {label}')
    else:
        print(f'    ({px:3d}, {py:3d}) → FALLO')

# Analizar personas
print('\n👤 PERSONAS DETECTADAS:')

for person_id, person in list(persons.items())[:5]:  # Primeras 5
    print(f'\n  ID {person_id}:')
    
    # No hay info de bbox en map_data.json
    # Pero podemos ver los datos calculados
    current = person.get('current')
    if current:
        print(f'    GPS calculado: ({current["latitude"]:.6f}, {current["longitude"]:.6f})')
        print(f'    Distancia: {current["distance_m"]:.1f}m')
        print(f'    Confianza: {current["confidence"]:.3f}')
        
        # Comparar con centro del FOV
        center_fov = geo_calc.pixel_to_gps(
            bbox_center_x=320,
            bbox_center_y=256,
            latitude_dron=drone['latitude'],
            longitude_dron=drone['longitude'],
            altitude_dron=drone['altitude_rel'],
            yaw=drone['yaw'],
            pitch=drone['pitch'],
            roll=drone['roll']
        )
        
        if center_fov:
            print(f'    Centro FOV: ({center_fov.latitude:.6f}, {center_fov.longitude:.6f})')
            print(f'    Distancia centro FOV: {center_fov.distance_m:.1f}m')
            
            # Haversine para distancia real
            def haversine(lat1, lon1, lat2, lon2):
                R = 6371000
                φ1 = math.radians(lat1)
                φ2 = math.radians(lat2)
                Δφ = math.radians(lat2 - lat1)
                Δλ = math.radians(lon2 - lon1)
                a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                return R * c
            
            real_dist = haversine(
                current['latitude'], current['longitude'],
                drone['latitude'], drone['longitude']
            )
            
            print(f'    Distancia real (Haversine): {real_dist:.1f}m')
            print(f'    Error: {abs(real_dist - current["distance_m"]):.1f}m')
            
            # ¿Está DENTRO del FOV esperado?
            if 0 <= current['distance_m'] <= 500:
                print(f'    ✅ Distancia dentro de rango esperado')
            else:
                print(f'    ⚠️ Distancia FUERA de rango (>500m con alt {drone["altitude_rel"]:.0f}m)')

print('\n' + '='*80)