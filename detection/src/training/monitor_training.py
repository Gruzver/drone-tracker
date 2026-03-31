import time
import pandas as pd
from pathlib import Path
import os

print("="*70)
print("MONITOR EN TIEMPO REAL - FASE 1")
print("="*70)
print("Monitoreando metrics cada 10 segundos...")
print("Presiona Ctrl+C para salir\n")

results_csv = Path('runs/person_detection/phase1_v2_improved/results.csv')

last_epoch = 0

try:
    while True:
        if results_csv.exists():
            try:
                df = pd.read_csv(results_csv)
                
                if len(df) > last_epoch:
                    # Mostrar últimas 3 epochs
                    print("\n" + "="*70)
                    print(f"ÚLTIMA ACTUALIZACIÓN: {time.strftime('%H:%M:%S')}")
                    print("="*70)
                    
                    latest = df.tail(3)
                    
                    for idx, row in latest.iterrows():
                        epoch = idx + 1
                        print(f"\n📊 EPOCH {epoch}:")
                        print(f"  Box Loss: {row[' box_loss']:.4f}")
                        print(f"  Cls Loss: {row[' cls_loss']:.4f}")
                        print(f"  DFL Loss: {row[' dfl_loss']:.4f}")
                        print(f"  mAP50: {row[' metrics/mAP50(B)']:.4f} {'↑' if idx > 0 and row[' metrics/mAP50(B)'] > latest.iloc[idx-1][' metrics/mAP50(B)'] else '↓' if idx > 0 else ''}")
                        print(f"  mAP50-95: {row[' metrics/mAP50-95(B)']:.4f}")
                        print(f"  Precision: {row[' metrics/precision(B)']:.4f}")
                        print(f"  Recall: {row[' metrics/recall(B)']:.4f}")
                    
                    # Mejor hasta ahora
                    best_idx = df[' metrics/mAP50(B)'].idxmax()
                    best_map = df.loc[best_idx, ' metrics/mAP50(B)']
                    print(f"\n🏆 Mejor mAP50 hasta ahora: {best_map:.4f} (Epoch {best_idx + 1})")
                    
                    # Tendencia
                    if len(df) > 5:
                        recent_trend = df[' metrics/mAP50(B)'].tail(5)
                        if recent_trend.iloc[-1] > recent_trend.iloc[0]:
                            print("📈 Tendencia: MEJORANDO")
                        elif recent_trend.iloc[-1] < recent_trend.iloc[0]:
                            print("📉 Tendencia: EMPEORANDO")
                        else:
                            print("➡️  Tendencia: ESTABLE")
                    
                    last_epoch = len(df)
            
            except Exception as e:
                print(f"⚠️ Error leyendo archivo: {e}")
        else:
            print("Esperando a que inicie el entrenamiento...")
        
        time.sleep(10)  # Actualizar cada 10 segundos

except KeyboardInterrupt:
    print("\n\n✋ Monitor detenido")