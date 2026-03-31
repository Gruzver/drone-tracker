# Drone Tracker — Resumen del Proyecto

**Objetivo**: Mapeo en tiempo real de personas mediante cámara térmica en un dron, usando YOLO con transfer learning para detección, conversión pixel→GPS para georreferenciación, y visualización en dashboard web.

---

## Arquitectura General

```
[Video MP4 + SRT]
       │
       ▼
┌──────────────────────┐
│  video_publisher_node │  Publica frames e telemetría DroneState
└──────────┬───────────┘
           │
    /camera/thermal/image_raw
    /telemetry/drone/state
           │
           ▼
┌──────────────────────┐
│  yolo_detection_node  │  Detección + tracking con best.pt (YOLO transfer learning)
└──────────┬───────────┘
           │
    /detection/persons (PersonDetectionArray, coords en espacio 640×512)
    /vision/labeled_image_compressed
           │
           ▼
┌──────────────────────┐
│  georeferencing_node  │  Convierte píxel→GPS con GeoCalculator (FOV + altitud + ángulos)
└──────────┬───────────┘
           │
    /gps/persons_location (PersonLocationArray)
           │
           ▼
┌──────────────────────┐
│   map_server_node     │  Agrega datos, exporta JSON + JPEG a /tmp/drone_map_data/
└──────────┬───────────┘
           │
    /tmp/drone_map_data/map_data.json
    /tmp/drone_map_data/current_frame.jpg
           │
           ▼
┌──────────────────────┐
│    Flask Web App      │  Dashboard en http://localhost:5000
│    (web/app.py)       │  Video en vivo + mapa Leaflet.js interactivo
└──────────────────────┘
```

---

## Paquetes ROS2

| Paquete | Descripción |
|---------|-------------|
| `drone_bringup` | Launch package: arranca todo el pipeline con un comando, seleccion de video por argumento |
| `drone_tracker_msgs` | Mensajes custom: DroneState, PersonDetection, PersonDetectionArray, PersonLocation, PersonLocationArray |
| `video_publisher_node` | Lee video MP4 + SRT DJI, publica frames e telemetría |
| `yolo_detection_node` | Inferencia YOLO + tracking persistente (track IDs) |
| `georeferencing_node` | Georreferenciación pixel→GPS con sincronización temporal |
| `map_server_node` | Agrega, persiste y sirve datos al frontend |
| `drone_tracker_utils` | Utilidades compartidas: GeoCalculator, SRTParser, FOVVisualizer |

---

## Archivos Clave

| Archivo | Ruta | Notas |
|---------|------|-------|
| Modelo YOLO | `src/yolo_detection_node/models/best.pt` | 131MB, transfer learning térmico |
| Video de entrada | `/home/gr/Documents/drone-detection-project/data/raw/thermal_videos/DJI_*.MP4` | Grabación DJI térmica |
| Telemetría SRT | Mismo directorio, mismo nombre con `.SRT` | GPS, altitud, yaw/pitch/roll, focal |
| Salida de datos | `/tmp/drone_map_data/` | map_data.json, statistics.json, current_frame.jpg |
| Web server | `web/app.py` | Flask, puerto 5000 |
| Dashboard HTML | `web/templates/index.html` | Leaflet.js + dark UI |

---

## Mensajes ROS2 Custom

```
DroneState:
  timestamp, latitude, longitude
  altitude_rel, altitude_abs
  yaw, pitch, roll
  focal_len, dzoom_ratio

PersonDetection:
  track_id, confidence
  bbox_x1, bbox_y1, bbox_x2, bbox_y2  ← en espacio 640×512
  centroid_x, centroid_y
  timestamp

PersonLocation:
  track_id, latitude, longitude
  distance_m, confidence, status
  timestamp
```

---

## Pipeline de Georreferenciación (GeoCalculator)

1. Recibe centroide en píxeles (espacio 640×512)
2. Normaliza a rango [-0.5, 0.5]
3. Calcula ángulo subtendido según FOV horizontal/vertical de la cámara
4. Aplica rotaciones de yaw, pitch, roll del dron
5. Calcula desplazamiento horizontal en metros desde la posición del dron (trigonometría esférica)
6. Convierte offset en metros → delta lat/lon
7. Valida distancia resultante (rechaza si > 5000m)

---

## Dashboard Web

- **URL**: `http://localhost:5000`
- **Tecnologías**: Flask + Leaflet.js + OpenStreetMap
- **Mapa configurado para**: Lima, Perú (coordenadas por defecto en `web/config.py`)
- **Endpoints API**:
  - `GET /api/map_data` — Personas detectadas + posición dron (JSON)
  - `GET /api/statistics` — Métricas agregadas
  - `GET /api/current_frame` — Frame actual anotado (JPEG)
  - `GET /api/map_html` — Mapa Folium (HTML)
  - `GET /api/health` — Health check
- **Actualización**: cada 1 segundo vía polling
- **Marcadores**: verde = persona activa, gris = persona perdida; líneas drone→persona

---

## Herramientas de Debug

| Script | Función |
|--------|---------|
| `debug_bbox.py` | Valida conversión bbox→GPS, visualiza esquinas FOV |
| `debug_pixel_to_gps.py` | Debug paso a paso del cálculo GPS |
| `debug_timestamps.py` | Diagnóstico de sincronización temporal |
| `fov_visualizer_map.py` | Mapa Folium con cobertura FOV frame a frame |

---

## Estado Actual del Proyecto

### Implementado y funcional
- [x] Pipeline ROS2 completo end-to-end
- [x] Launch unificado `drone_bringup` con seleccion de video por argumento
- [x] Lectura de video termico DJI + parseo SRT (con soporte Windows \r\n)
- [x] Deteccion YOLO con tracking multi-objeto persistente
- [x] Georreferenciacion con correccion de orientacion del dron y tolerancia de sincronizacion temporal
- [x] Exportacion atomica de imagen (rename) y JSON periodico al dashboard
- [x] Dashboard web con video en vivo + mapa Leaflet interactivo
- [x] Historial de trayectorias por persona con deque de tamano fijo
- [x] Herramientas de diagnostico: FOV visualizer, debug bbox, debug timestamps
- [x] Revision de codigo completa: bugs corregidos, imports muertos eliminados, emojis removidos, docstrings agregados

### Bugs corregidos durante la revision de codigo
- `latitude_dron` / `longitude_dron` / `altitude_dron` renombrados a `latitude_drone` etc. en `GeoCalculator.pixel_to_gps` y todos los call sites actualizados
- `self.model.half()` en YOLO (metodo inexistente en ultralytics) eliminado
- `self.running` bool en `VisionViewer` sin sincronizacion reemplazado por `threading.Event`
- `start_server` en `FOVMapVisualizer`: `self.output_dir` dentro de clase `Handler` anidada apuntaba al Handler, no al visualizador — corregido con closure
- `sys.path.insert` a ruta inexistente en ambos `fov_visualizer.py` eliminado
- `self.lost_ids` set que crecia indefinidamente en `map_server` reemplazado por conteo dinamico
- `RcutilsLogger.info('%s', val)` → `f-string` en todos los nodos ROS2
- `frame_id = f'frame_{N}'` semanticamente incorrecto → constante `CAMERA_FRAME_ID`
- `split('\n\n')` en SRTParser falla con archivos Windows → `re.split(r'\r?\n\r?\n', ...)`
- Timer no se cancelaba al fin del video en `video_publisher` → `self.timer.cancel()`
- `self.cap.release()` en finally sin guard → `hasattr` check para evitar AttributeError

### Mejoras pendientes — priorizadas

#### Alta prioridad (afectan calidad del producto en uso real)

| # | Mejora | Nodo | Descripcion |
|---|--------|------|-------------|
| 1 | **Frame drop en YOLO** | `yolo_detection_node` | Si la inferencia supera 33ms, el subscriber acumula frames viejos. Descartar frames con timestamp mayor a N ms antes de procesar |
| 2 | ~~**Filtro de Kalman para GPS**~~ ✓ | `georeferencing_node` | Implementado: clase `KalmanTracker` ([lat,lon,vel_lat,vel_lon]), dt real por timestamps, limpieza automatica al perder track. Parametro `use_kalman` (default: true) |
| 3 | **Escritura atomica de JSON** | `map_server_node` | La imagen usa rename atomico pero los JSON se escriben directamente. Agregar escritura via archivo temporal + rename para ambos JSON |
| 4 | **Roll no se aplica en GeoCalculator** | `drone_tracker_utils` | El parametro `roll` llega a `pixel_to_gps` pero no se incorpora a la proyeccion. Con gimbal estabilizado el impacto es bajo pero existe |

#### Media prioridad (robustez y UX)

| # | Mejora | Componente | Descripcion |
|---|--------|-----------|-------------|
| 5 | **Servidor web en launch file** | `drone_bringup` | Agregar `ExecuteProcess` para lanzar `web/app.py` desde el launch, evitando la terminal manual |
| 6 | **WebSocket en dashboard** | `web/` | Reemplazar polling cada 1s por WebSocket para latencia < 100ms y eliminar peticiones cuando no hay cambios |
| 7 | **Revision del paquete web** | `web/` | Pendiente: revisar `app.py`, `map.js`, `dashboard.js`, `style.css` con el mismo criterio de calidad que los nodos ROS2 |

#### Menor prioridad (expansion de capacidades)

| # | Mejora | Descripcion |
|---|--------|-------------|
| 8 | **Soporte RTSP** | Reemplazar `video_publisher_node` con nodo que conecte a stream RTSP del dron en vuelo real |
| 9 | **Exportacion GeoJSON/KML** | Para abrir tracks en QGIS u otros SIG externos |
| 10 | **Calibracion automatica del FOV** | Derivar FOV desde `focal_len` y `dzoom_ratio` del SRT en lugar de la constante empirica 0.612 |
| 11 | **Tests unitarios** | Para `GeoCalculator` y `SRTParser` — cubrir casos limite de angulos y coordenadas |

---

## Cómo Ejecutar

### Opcion A — Launch unificado (recomendado)

```bash
# 1. Build
cd /home/gr/drone_ws
colcon build
source install/setup.bash

# 2. Lanzar todo el pipeline con el video por defecto
ros2 launch drone_bringup drone_tracker.launch.py

# 2b. Seleccionar video especifico
ros2 launch drone_bringup drone_tracker.launch.py \
    video_path:=/ruta/al/video.MP4

# 2c. El SRT se deduce automaticamente (.MP4 -> .SRT).
#     Si el nombre difiere, indicarlo explicitamente:
ros2 launch drone_bringup drone_tracker.launch.py \
    video_path:=/ruta/al/video.MP4 \
    srt_path:=/ruta/al/telemetria.SRT

# 2d. Ajustar parametros opcionales
ros2 launch drone_bringup drone_tracker.launch.py \
    video_path:=/ruta/al/video.MP4 \
    conf_threshold:=0.4 \
    keep_history:=true

# 3. Iniciar dashboard web (terminal separada)
cd web && python3 app.py

# 4. Abrir en navegador
# http://localhost:5000
```

### Argumentos del launch file

| Argumento | Default | Descripcion |
|-----------|---------|-------------|
| `video_path` | `DJI_20260210161918_0002_T.MP4` | Ruta al archivo MP4 termico |
| `srt_path` | *(deriva de video_path)* | Ruta al SRT; si se omite, se reemplaza la extension |
| `publish_rate` | `30` | Hz de publicacion de video |
| `conf_threshold` | `0.5` | Umbral de confianza YOLO (0.0-1.0) |
| `iou_threshold` | `0.45` | Umbral IoU para NMS |
| `use_half` | `false` | FP16 en GPU |
| `fov_horizontal` | `50.5` | FOV horizontal de la camara en grados |
| `max_distance` | `1000.0` | Distancia maxima GPS aceptable (metros) |
| `min_distance` | `10.0` | Distancia minima GPS aceptable (metros) |
| `keep_history` | `false` | Guardar historial de trayectorias |
| `output_dir` | `/tmp/drone_map_data` | Directorio de salida para JSON e imagen |

### Opcion B — Nodos individuales

```bash
ros2 run video_publisher_node video_publisher
ros2 run yolo_detection_node yolo_detector
ros2 run georeferencing_node georeferencer
ros2 run map_server_node map_server

# Visualizador de detecciones (opcional)
ros2 run yolo_detection_node view_vision
```

---

## Estado Actual del Proyecto

### Implementado y funcional
- [x] Pipeline ROS2 completo end-to-end
- [x] Launch unificado con seleccion de video por argumento (drone_bringup)
- [x] Lectura de video termico DJI + parseo SRT
- [x] Deteccion YOLO con tracking multi-objeto persistente
- [x] Georreferenciacion con correccion de orientacion del dron
- [x] Exportacion atomica de datos (sin corrupcion en lecturas concurrentes)
- [x] Dashboard web con video en vivo + mapa interactivo
- [x] Historial de trayectorias por persona (hasta 500 frames)
- [x] Herramientas de diagnostico y visualizacion

### Posibles áreas de mejora
- [ ] Soporte para camara en vivo (stream RTSP) — sustituye video_publisher_node
- [ ] Filtro de Kalman para suavizar trayectorias GPS, ya está
- [ ] WebSocket en lugar de polling para menor latencia en el dashboard
- [ ] Exportacion de datos en formato GeoJSON / KML
- [ ] Calibracion automatica del FOV desde metadatos DJI
- [ ] Tests unitarios para GeoCalculator y SRTParser

---

*Última actualización: 2026-03-30*
