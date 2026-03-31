import os
from pathlib import Path

# Rutas
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = Path('/tmp/drone_map_data')
TEMPLATE_DIR = PROJECT_ROOT / 'web' / 'templates'
STATIC_DIR = PROJECT_ROOT / 'web' / 'static'

# Flask
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000

# Cache
CACHE_TIMEOUT = 1  # segundos

# Mapa Folium
MAP_CENTER_LAT = -12.066849
MAP_CENTER_LON = -77.079978
MAP_ZOOM_START = 16

# Colores
COLOR_DRONE = 'red'
COLOR_ACTIVE = 'green'
COLOR_LOST = 'gray'

# Temas
MARKER_SIZE_ACTIVE = 8
MARKER_SIZE_LOST = 6