/**
 * dashboard.js
 * Lógica del dashboard - actualización en tiempo real
 */

class Dashboard {
    constructor() {
        this.updateInterval = 500; // ms
        this.frameUpdateInterval = 100; // ms
        this.lastUpdate = 0;
        this.lastFrameUpdate = 0;
        this.frameCount = 0;
        this.fps = 0;
        this.latency = 0;
        this.isConnected = false;
        this.lastValidFrame = null; // ✅ Guardar último frame válido
        this.isLoadingFrame = false;
        
        this.init();
    }

    init() {
        console.log('🎛️ Dashboard initialized');
        
        // Elementos DOM
        this.elements = {
            statusIndicator: document.getElementById('status-indicator'),
            statusDot: document.querySelector('.status-dot'),
            statusText: document.querySelector('.status-text'),
            videoFrame: document.getElementById('video-frame'),
            videoOverlay: document.getElementById('video-overlay'),
            videoContainer: document.querySelector('.video-container'),
            
            statFrame: document.getElementById('stat-frame'),
            statActive: document.getElementById('stat-active'),
            statUnique: document.getElementById('stat-unique'),
            statGps: document.getElementById('stat-gps'),
            statAlt: document.getElementById('stat-alt'),
            statYaw: document.getElementById('stat-yaw'),
            statPitch: document.getElementById('stat-pitch'),
            statLatency: document.getElementById('stat-latency'),
            statFps: document.getElementById('stat-fps'),
            statStatus: document.getElementById('stat-status'),
            statUpdated: document.getElementById('stat-updated'),
            
            progressFill: document.getElementById('progress-fill'),
            frameInfo: document.getElementById('frame-info'),
            mapInfo: document.getElementById('map-info'),
            
            personsTable: document.getElementById('persons-tbody'),
            btnRefresh: document.getElementById('btn-refresh'),
            btnDownload: document.getElementById('btn-download'),
            btnFullscreen: document.getElementById('btn-fullscreen'),
        };

        // Event listeners
        this.elements.btnRefresh.addEventListener('click', () => this.refreshData());
        this.elements.btnDownload.addEventListener('click', () => this.downloadData());
        this.elements.btnFullscreen.addEventListener('click', () => this.toggleFullscreen());

        // Setup video con preload
        this.setupVideoPreload();

        // Iniciar actualización
        this.startUpdating();
    }

    setupVideoPreload() {
        /**
         * ✅ Precargar siguiente frame mientras se muestra el actual
         */
        const img = this.elements.videoFrame;
        
        img.style.transition = 'opacity 0.1s ease-in-out'; // Fade suave
        img.style.opacity = '1';
    }

    startUpdating() {
        // Actualizar datos principales cada 500ms
        setInterval(() => this.updateDashboard(), this.updateInterval);
        
        // Actualizar frame cada 100ms (SIN esperar a que cargue)
        setInterval(() => this.updateFrame(), this.frameUpdateInterval);
        
        // Calcular FPS cada segundo
        setInterval(() => this.calculateFPS(), 1000);
    }

    async updateDashboard() {
        try {
            const startTime = performance.now();

            // Obtener datos
            const [mapData, stats] = await Promise.all([
                this.fetchAPI('/api/map_data'),
                this.fetchAPI('/api/statistics')
            ]);

            this.latency = Math.round(performance.now() - startTime);

            if (mapData && stats) {
                this.updateStats(mapData, stats);
                this.updateTable(mapData);
                this.setConnected(true);
            } else {
                this.setConnected(false);
            }
        } catch (error) {
            console.error('❌ Error updating dashboard:', error);
            this.setConnected(false);
        }
    }

    async updateFrame() {
        /**
         * ✅ MEJORADO: Retry logic + mejor timing
         */
        try {
            if (this.isLoadingFrame) {
                return;
            }

            this.isLoadingFrame = true;
            const timestamp = new Date().getTime();
            const url = `/api/current_frame?t=${timestamp}`;
            
            const tempImg = new Image();
            
            // ✅ Timeout más generoso (150ms)
            const timeoutHandle = setTimeout(() => {
                this.isLoadingFrame = false;
                console.warn('⏱️ Frame timeout');
            }, 150);
            
            tempImg.onload = () => {
                clearTimeout(timeoutHandle);
                
                // ✅ Fade suave entre frames
                const img = this.elements.videoFrame;
                img.style.opacity = '0.5';
                
                setTimeout(() => {
                    img.src = tempImg.src;
                    img.style.opacity = '1';
                    this.lastValidFrame = tempImg.src;
                    this.elements.videoOverlay.classList.add('hidden');
                    this.frameCount++;
                    this.isLoadingFrame = false;
                }, 30);
            };
            
            tempImg.onerror = () => {
                clearTimeout(timeoutHandle);
                console.warn('⚠️ Frame load failed');
                this.isLoadingFrame = false;
            };
            
            tempImg.src = url;
        } catch (error) {
            console.error('❌ Error updating frame:', error);
            this.isLoadingFrame = false;
        }
    }

    updateStats(mapData, stats) {
        const drone = mapData.dron || {};
        const persons = mapData.persons || {};
        const frame = mapData.frame_number || 0;

        // Frame progress
        const totalFrames = stats.total_frames || frame;
        const progress = totalFrames > 0 ? (frame / totalFrames) * 100 : 0;
        
        this.elements.statFrame.textContent = `${frame}/${totalFrames}`;
        this.elements.progressFill.style.width = `${progress}%`;
        this.elements.frameInfo.textContent = `Frame ${frame} (${progress.toFixed(1)}%)`;

        // Persons
        const activePeople = Object.values(persons).filter(p => p.status === 'active').length;
        this.elements.statActive.textContent = activePeople;
        this.elements.statUnique.textContent = `${Object.keys(persons).length} únicas`;

        // GPS
        const lat = drone.latitude?.toFixed(6) || '--';
        const lon = drone.longitude?.toFixed(6) || '--';
        const alt = drone.altitude_abs?.toFixed(2) || '--';
        
        this.elements.statGps.textContent = `${lat}, ${lon}`;
        this.elements.statAlt.textContent = `Alt: ${alt} m`;

        // Angles
        const yaw = drone.yaw?.toFixed(1) || '--';
        const pitch = drone.pitch?.toFixed(1) || '--';
        const roll = drone.roll?.toFixed(1) || '--';
        
        this.elements.statYaw.textContent = `Yaw: ${yaw}°`;
        this.elements.statPitch.textContent = `Pitch: ${pitch}° | Roll: ${roll}°`;

        // Latency & FPS
        this.elements.statLatency.textContent = `${this.latency}ms`;
        this.elements.statFps.textContent = `FPS: ${this.fps}`;

        // Status
        this.elements.statStatus.textContent = 'Conectado';
        this.elements.statUpdated.textContent = `Última: ${new Date().toLocaleTimeString()}`;
    }

    updateTable(mapData) {
        const persons = mapData.persons || {};
        const tbody = this.elements.personsTable;

        if (Object.keys(persons).length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No hay personas detectadas</td></tr>';
            return;
        }

        tbody.innerHTML = Object.entries(persons)
            .sort((a, b) => b[1].detections_count - a[1].detections_count)
            .map(([id, person]) => {
                const current = person.current || {};
                const status = person.status || 'unknown';
                const badge = status === 'active' 
                    ? `<span class="status-badge active">${status}</span>`
                    : `<span class="status-badge lost">${status}</span>`;

                const gps = current.latitude 
                    ? `${current.latitude.toFixed(6)}, ${current.longitude.toFixed(6)}`
                    : '--';

                return `
                    <tr>
                        <td><strong>${id}</strong></td>
                        <td>${badge}</td>
                        <td>${current.distance_m?.toFixed(1) || '--'} m</td>
                        <td>${((current.confidence || 0) * 100).toFixed(1)}%</td>
                        <td>${person.detections_count || 0}</td>
                        <td style="font-size: 11px; word-break: break-all;">${gps}</td>
                        <td style="font-size: 10px; color: #707070;">
                            ${current.distance_m > 200 ? '⚠️ Lejos' : '✅ OK'}
                        </td>
                    </tr>
                `;
            })
            .join('');
    }

    calculateFPS() {
        this.fps = Math.round(this.frameCount / (this.frameUpdateInterval / 1000) / 10);
        this.frameCount = 0;
    }

    setConnected(connected) {
        this.isConnected = connected;
        
        if (connected) {
            this.elements.statusDot.classList.remove('disconnected');
            this.elements.statusDot.classList.add('connected');
            this.elements.statusText.textContent = 'Conectado';
            this.elements.statStatus.textContent = 'Conectado';
        } else {
            this.elements.statusDot.classList.remove('connected');
            this.elements.statusDot.classList.add('disconnected');
            this.elements.statusText.textContent = 'Desconectado';
            this.elements.statStatus.textContent = 'Offline';
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

    refreshData() {
        console.log('🔄 Actualizando datos...');
        this.updateDashboard();
        this.elements.btnRefresh.style.animation = 'spin 1s linear';
        setTimeout(() => {
            this.elements.btnRefresh.style.animation = '';
        }, 1000);
    }

    downloadData() {
        fetch('/api/map_data')
            .then(response => response.json())
            .then(data => {
                const json = JSON.stringify(data, null, 2);
                const blob = new Blob([json], { type: 'application/json' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `map_data_${new Date().getTime()}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
                console.log('📥 JSON descargado');
            });
    }

    toggleFullscreen() {
        const elem = document.documentElement;
        if (!document.fullscreenElement) {
            elem.requestFullscreen().catch(err => {
                console.error('Error requesting fullscreen:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }
}

// Inicializar cuando DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});