#!/usr/bin/env python3

"""
fov_visualizer_map.py
Visualiza el FOV de la cámara en un mapa real (Folium)
Permite navegar por frames del SRT
"""

import math
import folium
from folium import plugins
from pathlib import Path
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time

# Agregar path para imports
sys.path.insert(0, str(Path(__file__).parent / 'src/drone_tracker_utils'))

from drone_tracker_utils import SRTParser, GeoCalculator


class FOVMapVisualizer:
    def __init__(self, srt_path):
        self.parser = SRTParser(srt_path)
        self.frames = self.parser.parse()
        self.current_frame_idx = 0
        
        self.geo_calc = GeoCalculator(fov_horizontal=50.5)
        
        print(f'✅ Cargados {len(self.frames)} frames del SRT')
        
        # Directorio de salida
        self.output_dir = Path('/tmp/fov_maps')
        self.output_dir.mkdir(exist_ok=True)
        
        # Inicializar
        self.update_map()
        self.start_server()
    
    def get_current_frame(self):
        """Obtiene el frame actual"""
        return self.frames[self.current_frame_idx]
    
    def update_map(self):
        """Crea el mapa con el frame actual"""
        frame_data = self.get_current_frame()
        
        lat_dron = frame_data.latitude
        lon_dron = frame_data.longitude
        alt_dron = frame_data.altitude_rel
        yaw = frame_data.yaw
        pitch = frame_data.pitch
        roll = frame_data.roll
        
        # Crear mapa centrado en dron
        m = folium.Map(
            location=[lat_dron, lon_dron],
            zoom_start=17,
            tiles='OpenStreetMap'
        )
        
        # Marcador del dron
        folium.Marker(
            location=[lat_dron, lon_dron],
            popup=folium.Popup(f"""
            <b>🚁 DRON</b><br>
            Frame: {self.current_frame_idx + 1}/{len(self.frames)}<br>
            Lat: {lat_dron:.6f}<br>
            Lon: {lon_dron:.6f}<br>
            Alt: {alt_dron:.1f}m<br>
            Yaw: {yaw:.1f}°<br>
            Pitch: {pitch:.1f}°<br>
            Roll: {roll:.1f}°
            """, max_width=300),
            icon=folium.Icon(color='red', icon='helicopter', prefix='fa'),
            tooltip='Dron'
        ).add_to(m)
        
        # Calcular corners del FOV
        fov_corners_gps = self.calculate_fov_corners(
            lat_dron, lon_dron, alt_dron, yaw, pitch, roll
        )
        
        # Dibujar FOV como polígono
        if len(fov_corners_gps) == 4:
            fov_polygon = folium.Polygon(
                locations=fov_corners_gps,
                color='cyan',
                fill=True,
                fillColor='cyan',
                fillOpacity=0.2,
                weight=3,
                popup=f"FOV - Pitch: {pitch:.1f}°, Yaw: {yaw:.1f}°"
            )
            fov_polygon.add_to(m)
            
            # Dibujar corners (marcadores)
            corner_names = ['Top-Left (0,0)', 'Top-Right (640,0)', 'Bottom-Right (640,512)', 'Bottom-Left (0,512)']
            for i, (corner_lat, corner_lon) in enumerate(fov_corners_gps):
                folium.CircleMarker(
                    location=[corner_lat, corner_lon],
                    radius=6,
                    popup=f"{corner_names[i]}",
                    color='orange',
                    fill=True,
                    fillColor='orange',
                    fillOpacity=0.8,
                    weight=2,
                    tooltip=f'Corner {i}'
                ).add_to(m)
            
            # Dibujar líneas desde dron a corners
            for corner_lat, corner_lon in fov_corners_gps:
                folium.PolyLine(
                    locations=[[lat_dron, lon_dron], [corner_lat, corner_lon]],
                    color='orange',
                    weight=1,
                    opacity=0.5,
                    dash_array='5, 5'
                ).add_to(m)
        
        # Dibujar círculo de rango
        folium.Circle(
            location=[lat_dron, lon_dron],
            radius=500,  # 500 metros
            color='green',
            fill=False,
            weight=1,
            opacity=0.3,
            popup='Rango 500m'
        ).add_to(m)
        
        # Información en la esquina
        info_text = f"""
        <div style="font-family: monospace; background-color: white; padding: 10px; border-radius: 5px;">
            <b>Frame:</b> {self.current_frame_idx + 1}/{len(self.frames)}<br>
            <b>Lat:</b> {lat_dron:.6f}<br>
            <b>Lon:</b> {lon_dron:.6f}<br>
            <b>Alt:</b> {alt_dron:.1f}m<br>
            <b>Yaw:</b> {yaw:.1f}°<br>
            <b>Pitch:</b> {pitch:.1f}°<br>
            <b>Roll:</b> {roll:.1f}°<br>
            <b>FOV H:</b> {self.geo_calc.fov_h:.1f}°<br>
            <b>FOV V:</b> {self.geo_calc.fov_v:.1f}°<br>
            <br>
            <b>Controles:</b><br>
            Abre: http://localhost:8000<br>
            N: Next | P: Prev | Q: Quit
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(info_text))
        
        # Guardar mapa
        map_file = self.output_dir / 'fov_map.html'
        m.save(str(map_file))
        print(f'✅ Mapa guardado: {map_file}')
    
    def calculate_fov_corners(self, lat_dron, lon_dron, alt_dron, yaw, pitch, roll):
        """
        Calcula los 4 corners del FOV en GPS
        """
        corners_pixels = [
            (0, 0),           # Top-left
            (640, 0),         # Top-right
            (640, 512),       # Bottom-right
            (0, 512),         # Bottom-left
        ]
        
        corners_gps = []
        
        for px, py in corners_pixels:
            location = self.geo_calc.pixel_to_gps(
                bbox_center_x=px,
                bbox_center_y=py,
                latitude_dron=lat_dron,
                longitude_dron=lon_dron,
                altitude_dron=alt_dron,
                yaw=yaw,
                pitch=pitch,
                roll=roll
            )
            
            if location:
                corners_gps.append([location.latitude, location.longitude])
                print(f'  Corner ({px}, {py}): ({location.latitude:.6f}, {location.longitude:.6f}) - {location.distance_m:.1f}m')
            else:
                print(f'  ❌ Corner ({px}, {py}): FALLO en cálculo GPS')
                corners_gps.append([lat_dron, lon_dron])
        
        return corners_gps
    
    def start_server(self):
        """Inicia servidor HTTP"""
        output_dir = self.output_dir  # ✅ Guardar en variable local
        
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(output_dir), **kwargs)
            
            def log_message(self, format, *args):
                pass  # Silenciar logs
        
        server = HTTPServer(('localhost', 8000), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        
        print(f'✅ Server HTTP en http://localhost:8000')
        
    def interactive_loop(self):
        """Loop interactivo"""
        # Abrir navegador
        webbrowser.open('http://localhost:8000/fov_map.html')
        
        print("""
╔════════════════════════════════════════════════════════════════╗
║           FOV MAP VISUALIZER - MODO INTERACTIVO               ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Abre http://localhost:8000/fov_map.html en tu navegador      ║
║                                                                ║
║  Controles:                                                    ║
║    N - Siguiente frame                                        ║
║    P - Frame anterior                                         ║
║    J - Ir a frame específico                                  ║
║    Q - Salir                                                  ║
║    H - Ayuda                                                  ║
║                                                                ║
║  Busca anomalías en el FOV:                                   ║
║    • ¿El polígono cyan es un rectángulo?                      ║
║    • ¿Los corners (naranja) son lógicos?                      ║
║    • ¿Se mueve correctamente con Yaw/Pitch?                   ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """)
        
        while True:
            key = input('\n> ').strip().lower()
            
            if key == 'q':
                print('Saliendo...')
                break
            elif key == 'n':
                self.current_frame_idx = min(self.current_frame_idx + 1, len(self.frames) - 1)
                print(f'Frame {self.current_frame_idx + 1}/{len(self.frames)}')
                self.update_map()
            elif key == 'p':
                self.current_frame_idx = max(self.current_frame_idx - 1, 0)
                print(f'Frame {self.current_frame_idx + 1}/{len(self.frames)}')
                self.update_map()
            elif key == 'j':
                try:
                    idx = int(input(f'Ir a frame (1-{len(self.frames)}): ')) - 1
                    self.current_frame_idx = max(0, min(idx, len(self.frames) - 1))
                    print(f'Frame {self.current_frame_idx + 1}/{len(self.frames)}')
                    self.update_map()
                except:
                    print('❌ Input inválido')
            elif key == 'h':
                self.print_help()
            else:
                print('Comando no reconocido. Escribe H para ayuda.')
    
    def print_help(self):
        """Imprime ayuda detallada"""
        help_text = """
╔════════════════════════════════════════════════════════════════╗
║                         AYUDA COMPLETA                        ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  COMANDOS:                                                     ║
║    N - Siguiente frame                                        ║
║    P - Frame anterior                                         ║
║    J - Ir a frame específico (ingresa número)                 ║
║    Q - Salir del programa                                     ║
║    H - Mostrar esta ayuda                                     ║
║                                                                ║
║  INTERPRETACIÓN DEL MAPA:                                     ║
║                                                                ║
║    🚁 Punto rojo:                                             ║
║       Posición del dron en el mapa real                       ║
║                                                                ║
║    🟦 Polígono cyan:                                          ║
║       Área que "ve" la cámara del dron (FOV)                  ║
║       Si está bien, debería ser un RECTÁNGULO                ║
║                                                                ║
║    🟠 Puntos naranja:                                         ║
║       Las 4 esquinas del FOV:                                 ║
║       • Top-Left (0, 0) - arriba a la izquierda             ║
║       • Top-Right (640, 0) - arriba a la derecha            ║
║       • Bottom-Right (640, 512) - abajo a la derecha        ║
║       • Bottom-Left (0, 512) - abajo a la izquierda         ║
║                                                                ║
║    ---- Líneas punteadas naranja:                             ║
║       Líneas desde dron a cada corner (referencia)            ║
║                                                                ║
║  QUÉ BUSCAR PARA DEBUGGEAR:                                   ║
║                                                                ║
║    ✅ CORRECTO:                                               ║
║       • FOV es un rectángulo lógico                           ║
║       • Corners forman un polígono válido                     ║
║       • Se mueve suavemente al cambiar frames                 ║
║       • Tamaño FOV cambia lógicamente con Pitch              ║
║                                                                ║
║    ❌ PROBLEMA:                                               ║
║       • Polígono está "roto" o desordenado                    ║
║       • Corners están muy lejos del dron                      ║
║       • FOV apunta en dirección incorrecta                    ║
║       • Puntos "saltan" entre frames                          ║
║       • Corners están del otro lado del dron (invertido)     ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
        """
        print(help_text)


def main():
    # Path del SRT
    srt_path = Path.home() / '/home/gr/Documents/drone-detection-project/data/raw/thermal_videos/DJI_20260212192435_0001_T.SRT'
    
    if not srt_path.exists():
        print('❌ SRT no encontrado en ruta por defecto')
        print('Ingresa la ruta del archivo SRT:')
        srt_path = input('Path: ').strip()
        srt_path = Path(srt_path)
    
    if not srt_path.exists():
        print(f'❌ Archivo no encontrado: {srt_path}')
        return
    
    try:
        visualizer = FOVMapVisualizer(str(srt_path))
        visualizer.interactive_loop()
    except KeyboardInterrupt:
        print('\n\nSaliendo...')


if __name__ == '__main__':
    main()