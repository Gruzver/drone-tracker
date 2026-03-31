# Detección y Tracking de Personas en Videos de Drones

Pipeline completo para detectar y rastrear personas en videos térmicos de drones usando YOLOv8 con transfer learning y fine-tuning.

## Estructura del Proyecto

```
detection/
├── configs/
│   ├── classes.yaml              # Definición de clases
│   ├── data.yaml                 # Config del dataset (YOLO)
│   └── extraction_config.json    # Config de extracción de frames
│
├── data/
│   ├── raw/                      # Videos originales (RGB + thermal)
│   ├── processed/                # Frames extraídos
│   ├── labeled/                  # Imágenes con etiquetas YOLO
│   ├── dataset/                  # Dataset split (train/val/test)
│   ├── telemetry/                # Datos SRT de los drones
│   └── logs/                     # Logs de extracción
│
├── models/
│   ├── pretrained/               # Pesos base (yolov8x.pt, yolov8n.pt)
│   ├── trained/                  # Modelos entrenados
│   └── optimized/                # Modelos exportados (ONNX, TensorRT)
│
└── src/
    ├── data/                     # Pipeline de datos
    ├── training/                 # Scripts de entrenamiento
    ├── inference/                # Inferencia en video
    └── utils/                    # Utilidades (exportación)
```

## Modelos

| Modelo | Ruta | Uso |
|--------|------|-----|
| YOLOv8x pretrained | `models/pretrained/yolov8x.pt` | Base para training |
| Phase 1 best | `models/trained/phase1_v2_improved_best.pt` | Input para phase 2 |
| Phase 2 final | `models/trained/phase2_finetuned_final_best.pt` | Inferencia (usar este) |
| ONNX FP16 | `models/optimized/best_fp16.onnx` | Despliegue optimizado |

## Dataset

- **Raw videos**: `data/raw/thermal_videos/` — 20 videos DJI térmicos (~8.7 GB)
- **Imágenes etiquetadas**: `data/labeled/` — formato YOLO (298 MB)
- **Dataset split**: `data/dataset/` — 4,910 imágenes (3437 train / 736 val / 737 test)
- **Clase entrenada**: `person` (1 clase)
- **Config YOLO**: `configs/data.yaml`

---

## Pipeline Completo

### 1. Instalación

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Extracción de frames

Extrae frames de los videos crudos usando la configuración en `configs/extraction_config.json`:

```bash
python src/data/extract_frames.py --config configs/extraction_config.json
# Output: data/processed/thermal_frames/
```

Para un video individual:
```bash
python src/data/extract_frames.py data/raw/thermal_videos/VIDEO.MP4 \
    --output-dir data/processed/thermal_frames/lote1 \
    --frame-step 30 \
    --prefix THERMAL_Lote1 \
    --video-type thermal
```

### 3. Aumentación de datos

Genera 2 versiones aumentadas por imagen original (flip, rotación, ruido, brillo/contraste):

```bash
python src/data/augment_dataset.py
# Input:  data/labeled/
# Output: data/dataset/images/augmented_temp/
```

### 4. Distribución del dataset

Divide en train (70%) / val (15%) / test (15%):

```bash
python src/data/distribute_dataset.py
# Input:  data/dataset/images/augmented_temp/
# Output: data/dataset/{images,labels}/{train,val,test}/
```

### 5. Entrenamiento

El script implementa fine-tuning de 2 fases sobre YOLOv8x:
- **Phase 1** (ya completada): backbone congelado, entrena el head
- **Phase 2** (este script): descongelado total, refinamiento con LR muy bajo

Para re-entrenar phase 2 desde el mejor modelo de phase 1:

```bash
# Ajustar hiperparámetros si es necesario (epochs, lr, etc.)
python src/training/train_fine_tuning.py
# Output: runs/person_detection/phase2_finetuned_final/weights/best.pt
```

Monitorear el entrenamiento en tiempo real (en otra terminal):
```bash
python src/training/monitor_training.py
```

### 6. Inferencia + Tracking

Procesa un video con detección de personas y tracking por ID:

```bash
python src/inference/inference_tracking.py
# Output: inference_output/video_con_tracking.mp4
```

Para cambiar el video de entrada, editar las líneas al final de `inference_tracking.py`:
```python
video_path = 'data/raw/thermal_videos/TU_VIDEO.MP4'
output_path = 'inference_output/resultado.mp4'
```

### 7. Exportación del modelo

Exporta el modelo entrenado a ONNX o TensorRT para despliegue:

```bash
python src/utils/quantize_model.py
# Output: models/optimized/
# Genera: ONNX FP32, ONNX FP16, TensorRT FP16 (si CUDA disponible)
```

---

## Notas de Entrenamiento

Los resultados de training se guardan en `runs/person_detection/` con la siguiente estructura:
```
runs/person_detection/<nombre_run>/
├── weights/
│   ├── best.pt    # Mejor checkpoint (usar este)
│   └── last.pt    # Último checkpoint
├── results.csv    # Métricas por época
└── results.png    # Curvas de entrenamiento
```

Después de confirmar que el modelo es satisfactorio, mover `best.pt` a `models/trained/`.

## Autor

gruzver

## Licencia

MIT License
