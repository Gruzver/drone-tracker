"""
inference_video_with_tracking.py
Detección + Tracking en video con métricas detalladas
"""

from ultralytics import YOLO
import cv2
from pathlib import Path
import torch
import time
import numpy as np
from collections import defaultdict

class PersonTracker:
    def __init__(self):
        self.model = YOLO('models/trained/phase2_finetuned_final_best.pt')
        self.conf_threshold = 0.5
        self.iou_threshold = 0.45
        
    def process_video(self, video_path, output_path=None):
        """Procesa video con detección y tracking"""
        
        # Validar video
        if not Path(video_path).exists():
            print(f"Video no encontrado: {video_path}")
            return None
        
        # Abrir video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error al abrir video")
            return None
        
        # Obtener propiedades
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps
        
        print("="*70)
        print("DETECCIÓN + TRACKING DE PERSONAS")
        print("="*70)
        print(f"\n Video: {Path(video_path).name}")
        print(f"Resolución: {width}x{height}")
        print(f"FPS: {fps:.2f}")
        print(f"Total frames: {total_frames}")
        print(f"Duración: {duration:.1f}s\n")
        
        # Preparar guardado si se especifica
        out = None
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            print(f"Guardando en: {output_path}\n")
        
        # Inicializar métricas
        metrics = {
            'frame_count': 0,
            'total_persons': 0,
            'max_persons': 0,
            'frames_with_persons': 0,
            'frames_without_persons': 0,
            'inference_times': [],
            'persons_per_frame': [],
            'track_ids': set(),
            'detections': defaultdict(list),
        }
        
        print("Procesando video...")
        print("-"*70)
        
        # Procesar frames
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            metrics['frame_count'] += 1
            
            # Inferencia con tracking
            frame_start = time.time()
            results = self.model.track(
                frame, 
                conf=self.conf_threshold, 
                iou=self.iou_threshold,
                persist=True,  # Mantener IDs de track
                verbose=False
            )
            inference_time = time.time() - frame_start
            metrics['inference_times'].append(inference_time)
            
            # Procesar detecciones
            annotated_frame = results[0].plot()
            detections = results[0].boxes
            num_persons = len(detections)
            
            metrics['total_persons'] += num_persons
            metrics['persons_per_frame'].append(num_persons)
            
            if num_persons > 0:
                metrics['frames_with_persons'] += 1
                metrics['max_persons'] = max(metrics['max_persons'], num_persons)
                
                # Recopilar IDs de track
                if results[0].boxes.id is not None:
                    track_ids = results[0].boxes.id.int().cpu().numpy()
                    metrics['track_ids'].update(track_ids)
                    
                    # Guardar detecciones
                    for tid, detection in zip(track_ids, detections):
                        x1, y1, x2, y2 = detection.xyxy[0].cpu().numpy()
                        conf = detection.conf.item()
                        metrics['detections'][int(tid)].append({
                            'frame': metrics['frame_count'],
                            'confidence': conf,
                            'bbox': [x1, y1, x2, y2]
                        })
            else:
                metrics['frames_without_persons'] += 1
            
            # Agregar información en el frame
            info_text = f"Frame: {metrics['frame_count']}/{total_frames} | Personas: {num_persons} | IDs: {len(metrics['track_ids'])}"
            cv2.putText(annotated_frame, info_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Agregar tiempo de inferencia
            time_text = f"Inf: {inference_time*1000:.1f}ms"
            cv2.putText(annotated_frame, time_text, (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            # Guardar frame
            if out:
                out.write(annotated_frame)
            
            # Progreso
            if metrics['frame_count'] % 100 == 0:
                avg_inf = np.mean(metrics['inference_times'][-100:]) * 1000
                print(f"  Frame {metrics['frame_count']}/{total_frames} | Inf promedio: {avg_inf:.2f}ms")
        
        # Liberar recursos
        cap.release()
        if out:
            out.release()
        
        total_time = time.time() - start_time
        metrics['total_time'] = total_time
        
        return metrics
    
    def print_metrics(self, metrics):
        """Imprime métricas detalladas"""
        
        if not metrics:
            return
        
        print("\n" + "="*70)
        print(" MÉTRICAS DE PROCESAMIENTO")
        print("="*70)
        
        # Información del video
        print("\n INFORMACIÓN DEL VIDEO:")
        print(f"  Total frames procesados: {metrics['frame_count']}")
        print(f"  Tiempo de procesamiento: {metrics['total_time']:.2f}s")
        print(f"  Velocidad de procesamiento: {metrics['frame_count']/metrics['total_time']:.1f} FPS")
        
        # Detecciones
        print("\n DETECCIONES:")
        print(f"  Total de personas detectadas: {metrics['total_persons']}")
        print(f"  Personas por frame (promedio): {np.mean(metrics['persons_per_frame']):.2f}")
        print(f"  Máximo de personas en un frame: {metrics['max_persons']}")
        print(f"  Frames con personas: {metrics['frames_with_persons']}")
        print(f"  Frames sin personas: {metrics['frames_without_persons']}")
        
        # Tracking
        print("\n TRACKING:")
        print(f"  IDs únicos rastreados: {len(metrics['track_ids'])}")
        print(f"  IDs: {sorted(list(metrics['track_ids']))}")
        
        # Inferencia
        print("\n⚡ INFERENCIA:")
        inf_times = metrics['inference_times']
        print(f"  Tiempo promedio por frame: {np.mean(inf_times)*1000:.2f}ms")
        print(f"  Tiempo mínimo: {np.min(inf_times)*1000:.2f}ms")
        print(f"  Tiempo máximo: {np.max(inf_times)*1000:.2f}ms")
        print(f"  Desv. estándar: {np.std(inf_times)*1000:.2f}ms")
        
        # Análisis por ID de tracking
        if metrics['detections']:
            print("\n ANÁLISIS POR ID DE TRACKING:")
            for track_id in sorted(metrics['detections'].keys()):
                detections = metrics['detections'][track_id]
                frames = [d['frame'] for d in detections]
                confs = [d['confidence'] for d in detections]
                
                print(f"\n  ID {track_id}:")
                print(f"    Frames detectado: {len(detections)}")
                print(f"    Primer frame: {min(frames)}")
                print(f"    Último frame: {max(frames)}")
                print(f"    Duración: {max(frames) - min(frames)} frames")
                print(f"    Confianza promedio: {np.mean(confs):.2%}")
                print(f"    Confianza mínima: {np.min(confs):.2%}")
                print(f"    Confianza máxima: {np.max(confs):.2%}")
        
        print("\n" + "="*70 + "\n")

# EJECUCIÓN
if __name__ == '__main__':
    # Crear tracker
    tracker = PersonTracker()
    
    # Video a procesar
    video_path = 'data/raw/thermal_videos/DJI_20260212190618_0001_T.MP4'
    output_path = 'inference_output/video_con_tracking.mp4'
    
    # Procesar
    metrics = tracker.process_video(video_path, output_path)
    
    # Mostrar métricas
    if metrics:
        tracker.print_metrics(metrics)
        
        print(f" Video guardado: {output_path}")
    else:
        print(" Error al procesar video")