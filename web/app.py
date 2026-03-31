#!/usr/bin/env python3

import os
import json
import cv2
import base64
import folium
from flask import Flask, render_template, jsonify, send_file
from pathlib import Path
from datetime import datetime
import io
import logging
import time

from config import (
    DATA_DIR, TEMPLATE_DIR, STATIC_DIR, PORT, HOST,
    MAP_CENTER_LAT, MAP_CENTER_LON, MAP_ZOOM_START,
    COLOR_DRONE, COLOR_ACTIVE, COLOR_LOST,
    MARKER_SIZE_ACTIVE, MARKER_SIZE_LOST
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)

class DataManager:
    """Gestor de datos - lee archivos JSON"""
    
    @staticmethod
    def load_map_data():
        """Carga map_data.json"""
        try:
            map_file = DATA_DIR / 'map_data.json'
            if not map_file.exists():
                return None
            
            with open(map_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'Error loading map_data: {e}')
            return None
    
    @staticmethod
    def load_statistics():
        """Carga statistics.json"""
        try:
            stats_file = DATA_DIR / 'statistics.json'
            if not stats_file.exists():
                return None
            
            with open(stats_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f'Error loading statistics: {e}')
            return None
    
    @staticmethod
    def load_current_frame():
        """Carga current_frame.jpg"""
        try:
            frame_file = DATA_DIR / 'current_frame.jpg'
            if not frame_file.exists():
                return None
            
            with open(frame_file, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f'Error loading frame: {e}')
            return None


class MapBuilder:
    """Constructor de mapas Folium"""
    
    @staticmethod
    def build_map(map_data):
        """Construye mapa Folium con datos GPS"""
        
        if not map_data:
            return None
        
        try:
            # Crear mapa base
            drone = map_data.get('dron', {})
            center_lat = drone.get('latitude', MAP_CENTER_LAT)
            center_lon = drone.get('longitude', MAP_CENTER_LON)
            
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=MAP_ZOOM_START,
                tiles='OpenStreetMap',
                control_scale=True
            )
            
            # Marcador del dron
            drone_popup = f"""
            <b>🚁 DRON</b><br>
            Lat: {center_lat:.6f}<br>
            Lon: {center_lon:.6f}<br>
            Alt: {drone.get('altitude_abs', 0):.1f}m<br>
            Yaw: {drone.get('yaw', 0):.1f}°<br>
            Pitch: {drone.get('pitch', 0):.1f}°<br>
            Roll: {drone.get('roll', 0):.1f}°
            """
            
            folium.Marker(
                location=[center_lat, center_lon],
                popup=folium.Popup(drone_popup, max_width=250),
                icon=folium.Icon(color='red', icon='helicopter', prefix='fa'),
                tooltip='Posición del Dron'
            ).add_to(m)
            
            # Marcadores de personas
            persons = map_data.get('persons', {})
            
            for person_id, person in persons.items():
                current = person.get('current')
                if not current:
                    continue
                
                status = person.get('status', 'unknown')
                lat = current.get('latitude')
                lon = current.get('longitude')
                distance = current.get('distance_m', 0)
                confidence = current.get('confidence', 0)
                detections = person.get('detections_count', 0)
                
                # Seleccionar color por estado
                if status == 'active':
                    color = COLOR_ACTIVE
                    icon = 'person'
                    size = MARKER_SIZE_ACTIVE
                else:
                    color = COLOR_LOST
                    icon = 'person-slash'
                    size = MARKER_SIZE_LOST
                
                # Popup
                person_popup = f"""
                <b>👤 Persona ID: {person_id}</b><br>
                Estado: {status.upper()}<br>
                Lat: {lat:.6f}<br>
                Lon: {lon:.6f}<br>
                Distancia: {distance:.1f}m<br>
                Confianza: {confidence*100:.1f}%<br>
                Detecciones: {detections}
                """
                
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=size,
                    popup=folium.Popup(person_popup, max_width=250),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=2,
                    tooltip=f'ID: {person_id} ({status})'
                ).add_to(m)
                
                # Dibujar línea desde dron a persona
                if status == 'active':
                    folium.PolyLine(
                        locations=[[center_lat, center_lon], [lat, lon]],
                        color=color,
                        weight=1,
                        opacity=0.5,
                        dash_array='5, 5'
                    ).add_to(m)
            
            return m
        
        except Exception as e:
            logger.error(f'Error building map: {e}')
            return None


# ========================
# RUTAS API
# ========================

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/map_data')
def api_map_data():
    """Retorna datos del mapa (JSON)"""
    data = DataManager.load_map_data()
    
    if not data:
        return jsonify({
            'error': 'No map data available',
            'timestamp': datetime.now().isoformat()
        }), 404
    
    return jsonify(data)


@app.route('/api/statistics')
def api_statistics():
    """Retorna estadísticas (JSON)"""
    stats = DataManager.load_statistics()
    
    if not stats:
        return jsonify({
            'error': 'No statistics available',
            'timestamp': datetime.now().isoformat()
        }), 404
    
    return jsonify(stats)


@app.route('/api/current_frame')
def api_current_frame():
    """Retorna frame actual (JPEG) - con mejor handling"""
    try:
        frame_file = DATA_DIR / 'current_frame.jpg'
        
        # Verificar que existe
        if not frame_file.exists():
            return '', 404
        
        # ✅ Leer archivo con reintentos (por si está en escritura)
        max_retries = 3
        frame_data = None
        
        for attempt in range(max_retries):
            try:
                with open(frame_file, 'rb') as f:
                    frame_data = f.read()
                
                # Validar que no esté vacío
                if len(frame_data) > 1000:  # Mínimo 1KB
                    break
                
                frame_data = None  # Reset si es muy pequeño
                time.sleep(0.01)  # Esperar 10ms
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.01)
                continue
        
        if frame_data is None or len(frame_data) == 0:
            return '', 500
        
        # ✅ Servir con headers correctos
        response = send_file(
            io.BytesIO(frame_data),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name='current_frame.jpg'
        )
        
        # Headers: NO cachear, siempre fresco
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    
    except Exception as e:
        logger.error(f'❌ Error serving frame: {e}')
        return '', 500


@app.route('/api/map_html')
def api_map_html():
    """Retorna mapa Folium como HTML"""
    map_data = DataManager.load_map_data()
    
    if not map_data:
        return jsonify({'error': 'No map data'}), 404
    
    m = MapBuilder.build_map(map_data)
    
    if not m:
        return jsonify({'error': 'Failed to build map'}), 500
    
    # Convertir a HTML
    map_html = m._repr_html_()
    
    return map_html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/api/health')
def api_health():
    """Health check"""
    map_data = DataManager.load_map_data()
    
    return jsonify({
        'status': 'ok' if map_data else 'no_data',
        'timestamp': datetime.now().isoformat(),
        'data_dir': str(DATA_DIR),
        'data_available': map_data is not None
    })


# ========================
# ERROR HANDLERS
# ========================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500


# ========================
# MAIN
# ========================

if __name__ == '__main__':
    logger.info(f'🚀 Flask Server iniciado')
    logger.info(f'📁 Data dir: {DATA_DIR}')
    logger.info(f'📍 URL: http://localhost:{PORT}')
    logger.info(f'🌐 Abre http://localhost:{PORT} en tu navegador')
    
    app.run(host=HOST, port=PORT, debug=True)