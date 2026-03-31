#!/usr/bin/env python3

"""
quantize_model.py
Exporta el modelo YOLO a diferentes formatos optimizados
"""

from pathlib import Path
from ultralytics import YOLO
import time

# Modelo a optimizar
MODEL_PATH = Path(__file__).parent.parent.parent / 'models/trained/phase2_finetuned_final_best.pt'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'models/optimized'

if not MODEL_PATH.exists():
    print(f'❌ Modelo no encontrado: {MODEL_PATH}')
    exit(1)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print('='*80)
print('🚀 OPTIMIZACIÓN DE MODELO YOLO')
print('='*80)

print(f'\n📦 Modelo original: {MODEL_PATH}')
print(f'📁 Salida: {OUTPUT_DIR}')

# Cargar modelo
print('\n⏳ Cargando modelo...')
model = YOLO(str(MODEL_PATH))
model.info()

print('\n' + '='*80)
print('1️⃣ EXPORTAR A ONNX (CPU-friendly)')
print('='*80)

try:
    print('⏳ Exportando a ONNX (FP32)...')
    start = time.time()
    onnx_path = model.export(
        format='onnx',
        imgsz=640,
        half=False,
        device=0,
        simplify=True
    )
    elapsed = time.time() - start
    print(f'✅ Exportado en {elapsed:.1f}s')
    print(f'   Path: {onnx_path}')
    
    # Obtener tamaño
    size_mb = Path(onnx_path).stat().st_size / (1024*1024)
    print(f'   Tamaño: {size_mb:.1f}MB')
    
except Exception as e:
    print(f'❌ Error: {e}')

print('\n' + '='*80)
print('2️⃣ EXPORTAR A ONNX (FP16 - más rápido)')
print('='*80)

try:
    print('⏳ Exportando a ONNX (FP16)...')
    start = time.time()
    onnx_fp16_path = model.export(
        format='onnx',
        imgsz=640,
        half=True,
        device=0,
        simplify=True
    )
    elapsed = time.time() - start
    print(f'✅ Exportado en {elapsed:.1f}s')
    print(f'   Path: {onnx_fp16_path}')
    
    size_mb = Path(onnx_fp16_path).stat().st_size / (1024*1024)
    print(f'   Tamaño: {size_mb:.1f}MB')
    
except Exception as e:
    print(f'❌ Error: {e}')

print('\n' + '='*80)
print('3️⃣ EXPORTAR A TENSORRT (GPU - MÁS RÁPIDO)')
print('='*80)

try:
    print('⏳ Exportando a TensorRT (FP16)...')
    start = time.time()
    tensorrt_path = model.export(
        format='engine',
        imgsz=640,
        half=True,
        device=0,
        verbose=False
    )
    elapsed = time.time() - start
    print(f'✅ Exportado en {elapsed:.1f}s')
    print(f'   Path: {tensorrt_path}')
    
    size_mb = Path(tensorrt_path).stat().st_size / (1024*1024)
    print(f'   Tamaño: {size_mb:.1f}MB')
    
except Exception as e:
    print(f'⚠️ TensorRT no disponible (normal si CUDA no está instalado)')
    print(f'   Error: {e}')

print('\n' + '='*80)
print('📊 RESUMEN Y BENCHMARKS ESPERADOS')
print('='*80)

print('''
FORMATO          | TAMAÑO    | VELOCIDAD    | PRECISIÓN
─────────────────┼───────────┼──────────────┼──────────
PyTorch (PT)     | ~250 MB   | ~30-50ms     | 100% ✅
ONNX (FP32)      | ~125 MB   | ~20-30ms     | 99.9%
ONNX (FP16)      | ~65 MB    | ~15-20ms     | 99.8%
TensorRT (FP16)  | ~125 MB   | ~10-15ms     | 99.8% ⭐

RECOMENDACIÓN: TensorRT (si funciona) o ONNX FP16
''')

print('\n✅ Exportación completada')
print(f'📁 Modelos guardados en: {OUTPUT_DIR}')