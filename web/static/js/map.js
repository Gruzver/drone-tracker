/**
 * map.js
 * Lógica del mapa Leaflet - SIN recarga completa
 */

class MapManager {
    constructor() {
        this.mapContainer = document.getElementById('map-container');
        this.mapInfo = document.getElementById('map-info');
        this.updateInterval = 1000; // ms (actualizar cada 1 segundo)
        
        this.map = null;
        this.markers = {}; // Almacenar markers
        this.droneMarker = null;
        this.polylines = {}; // Almacenar líneas
        this.lastMapData = null;
        
        this.init();
    }

    init() {
        console.log('🗺️ Map Manager initialized with Leaflet');
        this.initMap();
        this.startUpdating();
    }

    initMap() {
        /**
         * ✅ Crear mapa UNA SOLA VEZ
         */
        // Coordenadas iniciales (Lima, Perú)
        const center = [-12.066849, -77.079978];
        
        this.map = L.map(this.mapContainer).setView(center, 16);
        
        // Tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
            opacity: 0.8
        }).addTo(this.map);
        
        // Controles
        L.control.scale().addTo(this.map);
        L.control.zoom().addTo(this.map);
        
        console.log('✅ Mapa Leaflet creado');
    }

    startUpdating() {
        // Actualizar datos cada segundo (NO recarga HTML)
        setInterval(() => this.updateMapData(), this.updateInterval);
    }

    async updateMapData() {
        try {
            const mapData = await this.fetchAPI('/api/map_data');
            
            if (!mapData) {
                this.mapInfo.textContent = '⚠️ Sin datos';
                return;
            }

            this.lastMapData = mapData;
            
            // ✅ Actualizar mapa SIN recargarlo
            this.updateDroneMarker(mapData);
            this.updatePersonMarkers(mapData);
            this.updateLines(mapData);
            
            const timestamp = new Date().toLocaleTimeString();
            this.mapInfo.textContent = `✅ ${timestamp}`;
            
        } catch (error) {
            console.error('❌ Error updating map data:', error);
            this.mapInfo.textContent = '❌ Error';
        }
    }

    updateDroneMarker(mapData) {
        const drone = mapData.dron || {};
        const lat = drone.latitude;
        const lon = drone.longitude;
        
        if (!lat || !lon) return;
        
        const position = [lat, lon];
        
        if (!this.droneMarker) {
            // Crear marcador del dron
            this.droneMarker = L.circleMarker(position, {
                radius: 12,
                fillColor: '#ff3333',
                color: '#ff0000',
                weight: 3,
                opacity: 1,
                fillOpacity: 0.8
            }).addTo(this.map);
            
            this.droneMarker.bindPopup(`
                <b>🚁 DRON</b><br>
                Lat: ${lat.toFixed(6)}<br>
                Lon: ${lon.toFixed(6)}<br>
                Alt: ${drone.altitude_abs?.toFixed(1) || '--'}m<br>
                Yaw: ${drone.yaw?.toFixed(1) || '--'}°
            `);
        } else {
            // ✅ Actualizar posición (SIN recrear)
            this.droneMarker.setLatLng(position);
        }
    }

    updatePersonMarkers(mapData) {
        const persons = mapData.persons || {};
        const currentIds = new Set();
        
        // Actualizar/crear markers de personas
        for (const [id, person] of Object.entries(persons)) {
            currentIds.add(id);
            const current = person.current;
            
            if (!current) continue;
            
            const lat = current.latitude;
            const lon = current.longitude;
            const status = person.status;
            const confidence = current.confidence;
            const distance = current.distance_m;
            
            const position = [lat, lon];
            const color = status === 'active' ? '#00cc00' : '#808080';
            const radius = status === 'active' ? 8 : 6;
            
            if (!this.markers[id]) {
                // ✅ Crear nuevo marker
                this.markers[id] = L.circleMarker(position, {
                    radius: radius,
                    fillColor: color,
                    color: color,
                    weight: 2,
                    opacity: 0.8,
                    fillOpacity: 0.7
                }).addTo(this.map);
            } else {
                // ✅ Actualizar existente
                this.markers[id].setLatLng(position);
                this.markers[id].setStyle({
                    fillColor: color,
                    color: color,
                    radius: radius
                });
            }
            
            // Actualizar popup
            const popupText = `
                <b>👤 ID: ${id}</b><br>
                Estado: <b>${status.toUpperCase()}</b><br>
                Distancia: ${distance.toFixed(1)}m<br>
                Confianza: ${(confidence * 100).toFixed(1)}%<br>
                Detecciones: ${person.detections_count}
            `;
            
            this.markers[id].bindPopup(popupText);
        }
        
        // ✅ Eliminar markers que desaparecieron
        for (const id of Object.keys(this.markers)) {
            if (!currentIds.has(id)) {
                this.map.removeLayer(this.markers[id]);
                delete this.markers[id];
            }
        }
    }

    updateLines(mapData) {
        const drone = mapData.dron || {};
        const dronePos = [drone.latitude, drone.longitude];
        const persons = mapData.persons || {};
        const currentIds = new Set();
        
        // Crear/actualizar líneas hacia personas activas
        for (const [id, person] of Object.entries(persons)) {
            if (person.status !== 'active') continue;
            
            const current = person.current;
            if (!current) continue;
            
            currentIds.add(id);
            const personPos = [current.latitude, current.longitude];
            
            if (!this.polylines[id]) {
                // ✅ Crear línea nueva
                this.polylines[id] = L.polyline([dronePos, personPos], {
                    color: '#0088ff',
                    weight: 2,
                    opacity: 0.5,
                    dashArray: '5, 5'
                }).addTo(this.map);
            } else {
                // ✅ Actualizar línea
                this.polylines[id].setLatLngs([dronePos, personPos]);
            }
        }
        
        // ✅ Eliminar líneas de personas perdidas
        for (const id of Object.keys(this.polylines)) {
            if (!currentIds.has(id)) {
                this.map.removeLayer(this.polylines[id]);
                delete this.polylines[id];
            }
        }
    }

    async fetchAPI(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) return null;
            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            return null;
        }
    }
}

// Inicializar cuando DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    // Pequeño delay para asegurar que el contenedor exista
    setTimeout(() => {
        window.mapManager = new MapManager();
    }, 100);
});