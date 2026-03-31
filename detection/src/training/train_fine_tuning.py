from ultralytics import YOLO
import torch
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*60)
print("FASE 2: FINE-TUNING (CON DATOS AUMENTADOS)")
print("="*60)
print(f"GPU: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Device: {torch.cuda.get_device_name(0)}\n")

# Cargar el MEJOR modelo de Fase 1
print("Cargando modelo de Fase 1...")
model = YOLO('models/trained/phase1_v2_improved_best.pt')

print("\n" + "="*60)
print("FASE 2: FINE-TUNING (DESCONGELAR TODO)")
print("="*60)
print("(Refinamiento con todo el modelo)")
print("="*60 + "\n")

results2 = model.train(
    data=os.path.join(PROJECT_ROOT, 'configs/data.yaml'),
    epochs=50,              # ← AUMENTADO (antes 50)
    imgsz=640,
    batch=8,
    device=0,
    patience=25,             # ← AUMENTADO (antes 10, para más paciencia)
    save=True,
    save_period=5,
    
    # Fine-tuning - DESCONGELAR TODO
    freeze=0,
    
    # ===== OPTIMIZACIÓN MEJORADA =====
    optimizer='SGD',
    lr0=0.00005,             # ← MÁS BAJO que antes (0.0001 → 0.00005)
    lrf=0.00001,             # ← MÁS BAJO que antes (0.001 → 0.00001)
    momentum=0.937,
    weight_decay=0.0001,     # ← REDUCIDO (evita regularización excesiva)
    
    # ===== REGULARIZACIÓN =====
    dropout=0.1,             # ← AGREGADO (antes 0.0, previene overfitting)
    
    # ===== AUGMENTATION (MÁS AGRESIVA) =====
    hsv_h=0.02,              # ← AUMENTADO (0.015 → 0.02)
    hsv_s=0.8,               # ← AUMENTADO (0.7 → 0.8)
    hsv_v=0.5,               # ← AUMENTADO (0.4 → 0.5)
    degrees=15,              # ← AUMENTADO (10 → 15)
    translate=0.15,          # ← AUMENTADO (0.1 → 0.15)
    scale=0.6,               # ← AUMENTADO (0.5 → 0.6)
    flipud=0.5,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.1,               # ← AGREGADO (mejora robustez)
    
    # ===== OPTIMIZACIONES ADICIONALES =====
    cos_lr=True,             # ← AGREGADO (cosine learning rate schedule)
    warmup_epochs=5,         # ← AGREGADO (warmup para mejor convergencia)
    warmup_momentum=0.8,
    warmup_bias_lr=0.1,
    
    # ===== VALIDACIÓN =====
    val=True,                # Validar en cada epoch
    plots=True,              # Generar gráficas
    
    # Logging
    project=os.path.join(PROJECT_ROOT, 'runs/person_detection'),
    name='phase2_finetuned_final',
    verbose=True,
)

print("\n" + "="*60)
print("ENTRENAMIENTO COMPLETADO")
print("="*60)
print(f"Mejor modelo: runs/person_detection/phase2_finetuned_final/weights/best.pt")
print("="*60 + "\n")

# ===== RESUMEN DE CAMBIOS =====
print("CAMBIOS REALIZADOS:")
print("-"*60)
print("✓ Modelo base: phase1_v2_improved (mejor que phase1_frozen_backbone)")
print("✓ Epochs: 50 → 100 (más tiempo de entrenamiento)")
print("✓ Patience: 10 → 25 (más tolerancia antes de parar)")
print("✓ Learning rate: 0.0001 → 0.00005 (más refinado)")
print("✓ Dropout: 0.0 → 0.1 (previene overfitting)")
print("✓ Augmentation: más agresiva (hsv, rotation, etc.)")
print("✓ Mixup: desactivado → 0.1 (mejora robustez)")
print("✓ Cosine LR: desactivado → True (mejor convergencia)")
print("✓ Warmup: desactivado → 5 epochs (arranque suave)")
print("-"*60 + "\n")