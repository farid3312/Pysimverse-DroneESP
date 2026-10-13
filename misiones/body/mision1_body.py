import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np
from collections import deque
from typing import Tuple
from pysimverse import Drone
import time
import threading

# ===============================
# CONFIGURACIÓN DE MEDIAPIPE
# ===============================
base_options = python.BaseOptions(model_asset_path='models/pose_landmarker_lite.task')
options = vision.PoseLandmarkerOptions(base_options=base_options)
detector = vision.PoseLandmarker.create_from_options(options)

# Puntos clave del esqueleto
KEYPOINTS = {
    'left_hip': 23,
    'right_hip': 24,
}

# Conexiones para visualización
BODY_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (23, 24), (11, 23), (12, 24), (23, 25), (25, 27),
    (24, 26), (26, 28), (27, 29), (29, 31), (28, 30), (30, 32),
]

# ===============================
# DETECTOR DE SALTOS
# ===============================

class VerticalVelocityJumpDetector:
    """Detector de saltos basado en VERTICAL VELOCITY OF HIP CENTER"""
    
    def __init__(self, smooth_len=9, takeoff_velocity=0.019, 
                 landing_velocity=-0.015, debounce_frames=9):
        self.smooth_len = smooth_len
        self.takeoff_velocity = takeoff_velocity
        self.landing_velocity = landing_velocity
        self.debounce_frames = debounce_frames
        
        self.hip_y_history = deque(maxlen=smooth_len)
        self.smoothed_y_history = deque(maxlen=2)
        
        self.in_air = False
        self.jump_count = 0
        self.frames_since_last_jump = 0
        
        self.last_velocity = 0.0
        self.current_state = "TIERRA"
        
    def check_landmarks_validity(self, landmarks) -> bool:
        """Verifica que los landmarks sean válidos y confiables"""
        if not landmarks or len(landmarks) < 29:
            return False
        
        left_hip = landmarks[KEYPOINTS['left_hip']]
        right_hip = landmarks[KEYPOINTS['right_hip']]
        
        if left_hip.visibility < 0.5 or right_hip.visibility < 0.5:
            return False
        
        hip_distance = abs(right_hip.x - left_hip.x)
        if hip_distance > 0.40 or hip_distance < 0.05:
            return False
        
        return True
    
    def get_hip_center_y(self, landmarks) -> float:
        """Obtiene posición Y promedio de caderas"""
        if not landmarks:
            return 0.0
        left_hip = landmarks[KEYPOINTS['left_hip']]
        right_hip = landmarks[KEYPOINTS['right_hip']]
        return (left_hip.y + right_hip.y) / 2.0
    
    def smooth_hip_y(self, current_y: float) -> float:
        """Suaviza la posición Y de caderas usando media móvil"""
        self.hip_y_history.append(current_y)
        smoothed = np.mean(list(self.hip_y_history))
        return smoothed
    
    def compute_velocity(self, smoothed_y: float) -> float:
        """Calcula velocidad vertical"""
        if len(self.smoothed_y_history) < 1:
            self.smoothed_y_history.append(smoothed_y)
            return 0.0
        
        prev_smoothed_y = self.smoothed_y_history[0]
        velocity = prev_smoothed_y - smoothed_y
        
        self.smoothed_y_history.append(smoothed_y)
        return velocity
    
    def detect_jump(self, landmarks) -> Tuple[bool, str]:
        """Detecta saltos usando velocidad vertical de caderas"""
        jump_detected = False
        
        if not landmarks:
            return False, "No se detectó persona"
        
        if not self.check_landmarks_validity(landmarks):
            self.frames_since_last_jump += 1
            return False, "⚠ Acércate o retrocede (distancia incorrecta)"
        
        current_y = self.get_hip_center_y(landmarks)
        smoothed_y = self.smooth_hip_y(current_y)
        velocity = self.compute_velocity(smoothed_y)
        self.last_velocity = velocity
        
        self.frames_since_last_jump += 1
        
        if not self.in_air and velocity > self.takeoff_velocity:
            self.in_air = True
            self.current_state = "AIRE ↑"
        
        elif self.in_air and velocity < self.landing_velocity:
            self.in_air = False
            
            if self.frames_since_last_jump >= self.debounce_frames:
                self.jump_count += 1
                self.frames_since_last_jump = 0
                jump_detected = True
                self.current_state = f"✓ SALTO CONTADO #{self.jump_count}"
            else:
                self.current_state = "TIERRA (debounce...)"
        else:
            if self.in_air:
                self.current_state = "SALTANDO ↑"
            else:
                self.current_state = "EN TIERRA"
        
        if jump_detected:
            message = f"🎯 ¡¡SALTO #{self.jump_count}!!"
        else:
            message = (
                f"{self.current_state} | Vel: {velocity:+.4f}\n"
                f"Total: {self.jump_count}"
            )
        
        return jump_detected, message


# ===============================
# FUNCIONES DE VISUALIZACIÓN
# ===============================

def draw_landmarks_on_image(image, detection_result):
    """Dibuja los landmarks y conexiones sobre la imagen"""
    annotated_image = np.copy(image)
    
    for pose_landmarks in detection_result.pose_landmarks:
        for connection in BODY_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            if start_idx < len(pose_landmarks) and end_idx < len(pose_landmarks):
                start = pose_landmarks[start_idx]
                end = pose_landmarks[end_idx]
                
                start_pos = (int(start.x * image.shape[1]), int(start.y * image.shape[0]))
                end_pos = (int(end.x * image.shape[1]), int(end.y * image.shape[0]))
                cv2.line(annotated_image, start_pos, end_pos, (0, 255, 0), 2)
        
        for landmark in pose_landmarks:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(annotated_image, (x, y), 4, (255, 0, 0), -1)
    
    return annotated_image

def draw_text_on_image(image, texts, position=(20, 50), font_scale=0.9, color=(0, 255, 0)):
    """Dibuja texto con fondo semi-transparente"""
    output_image = np.copy(image)
    y_offset = position[1]
    
    for text in texts:
        lines = text.split('\n')
        
        for line in lines:
            if "🎯" in line or "SALTO" in line or "SALTANDO" in line:
                text_color = (0, 0, 255)
                bg_color = (0, 0, 150)
            elif "AIRE" in line:
                text_color = (0, 255, 255)
                bg_color = (100, 100, 0)
            else:
                text_color = (0, 255, 0)
                bg_color = (0, 100, 0)
            
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            text_width = text_size[0]
            text_height = text_size[1]
            
            margin = 10
            cv2.rectangle(output_image, 
                         (position[0] - margin, y_offset - text_height - margin),
                         (position[0] + text_width + margin, y_offset + margin),
                         bg_color, -1)
            
            cv2.putText(output_image, line, (position[0], y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2)
            y_offset += 40
    
    return output_image

def draw_drone_status(image, drone_height, jump_detected):
    """Dibuja estado del drone en la esquina superior derecha"""
    output = np.copy(image)
    
    # Fondo oscuro
    cv2.rectangle(output, (output.shape[1] - 300, 0), 
                 (output.shape[1], 100), (30, 30, 30), -1)
    
    # Estado del drone
    status_color = (0, 0, 255) if jump_detected else (0, 255, 0)
    status_text = "DRONE SUBIENDO ↑" if jump_detected else "DRONE ESTABLE"
    
    cv2.putText(output, status_text, (output.shape[1] - 290, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    cv2.putText(output, f"Altura: {drone_height}", (output.shape[1] - 290, 70), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    
    return output


# ===============================
# FUNCIÓN PRINCIPAL
# ===============================

def mission_jump_and_fly(video_source=0, 
                        smooth_len=9,
                        takeoff_velocity=0.019,
                        landing_velocity=-0.015,
                        debounce_frames=9,
                        drone_up_speed=50,
                        drone_jump_boost_speed=85,
                        drone_down_speed=-15,
                        descent_delay=0.75):
    """
    Misión: Detectar saltos y controlar el drone
    
    Args:
        video_source: 0 para cámara web, o ruta a archivo de video
        smooth_len: Ventana de suavizado
        takeoff_velocity: Umbral de velocidad para despegue
        landing_velocity: Umbral de velocidad para aterrizaje
        debounce_frames: Frames mínimos entre dos saltos
        drone_up_speed: Velocidad normal de ascenso del drone (50 por defecto)
        drone_jump_boost_speed: Velocidad de ascenso al detectar salto (85 por defecto)
        drone_down_speed: Velocidad de descenso del drone (-5 por defecto, descenso lento)
        descent_delay: Tiempo en segundos después del salto antes de descender (1.5s por defecto)
    """
    
    print(f"\n{'='*80}")
    print(f"MISIÓN: CONTROL DE DRONE CON DETECCIÓN DE SALTOS")
    print(f"{'='*80}")
    
    # ===============================
    # INICIALIZACIÓN DE CÁMARA Y DETECTOR (PRIMERO)
    # ===============================
    print("Abriendo cámara...")
    cap = cv2.VideoCapture(video_source)
    
    if not cap.isOpened():
        print("✗ No se pudo abrir la cámara")
        return
    
    print("✓ Cámara abierta")
    
    jump_detector = VerticalVelocityJumpDetector(
        smooth_len=smooth_len,
        takeoff_velocity=takeoff_velocity,
        landing_velocity=landing_velocity,
        debounce_frames=debounce_frames
    )
    print("✓ Detector de saltos inicializado")
    
    print(f"\nConfiguraciones:")
    print(f"  SMOOTH_LEN:        {smooth_len}")
    print(f"  TAKEOFF_VELOCITY:  {takeoff_velocity}")
    print(f"  LANDING_VELOCITY:  {landing_velocity}")
    print(f"  DEBOUNCE_FRAMES:   {debounce_frames}")
    print(f"  DRONE_UP_SPEED:    {drone_up_speed}")
    print(f"  DRONE_JUMP_BOOST:  {drone_jump_boost_speed}")
    print(f"  DRONE_DOWN_SPEED:  {drone_down_speed} (lento)")
    print(f"  DESCENT_DELAY:     {descent_delay}s (tiempo antes de descender)")
    
    # ===============================
    # INICIALIZACIÓN DEL DRONE (DESPUÉS)
    # ===============================
    print(f"\n{'='*80}")
    print("Inicializando drone...")
    
    try:
        drone = Drone()
        drone.connect()
        print("✓ Drone conectado")
        
        drone.take_off()
        print("✓ Drone despegó")
        time.sleep(2)
    except Exception as e:
        print(f"✗ Error al conectar el drone: {e}")
        print("Continuando solo con detección de saltos...")
        drone = None
    
    print(f"{'='*80}")
    print("Presiona 'q' o ESC para salir\n")
    
    frame_count = 0
    last_jump_time = 0
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
            
            frame_count += 1
            current_time = time.time()
            
            # Convertir BGR a RGB para MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detectar pose
            detection_result = detector.detect(image_mp)
            
            # Dibujar landmarks
            annotated_frame = draw_landmarks_on_image(frame, detection_result)
            
            # Detectar saltos
            messages = []
            jump_detected = False
            
            if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
                landmarks = detection_result.pose_landmarks[0]
                jump_detected, message = jump_detector.detect_jump(landmarks)
                
                if jump_detected:
                    messages.append(f"🎯 ¡¡SALTO #{jump_detector.jump_count}!!")
                    print(f"\n{'='*50}")
                    print(f"✓✓✓ SALTO #{jump_detector.jump_count} DETECTADO EN FRAME {frame_count} ✓✓✓")
                    print(f"{'='*50}")
                    
                    # Enviar comando al drone para subir
                    if drone:
                        try:
                            # Parámetros: left_right, forward_backward, up_down, yaw
                            drone.send_rc_control(0, 0, drone_jump_boost_speed, 0)
                            print(f"Drone subiendo a velocidad BOOST {drone_jump_boost_speed}...\n")
                            last_jump_time = current_time
                        except Exception as e:
                            print(f"Error al controlar drone: {e}\n")
                else:
                    messages.append(message)
            else:
                messages.append("⚠ No se detectó persona")
            
            # Si no hay salto, el drone desciende lentamente o se estabiliza
            if not jump_detected and drone:
                try:
                    if current_time - last_jump_time > descent_delay:  # Esperar más tiempo antes de descender
                        drone.send_rc_control(0, 0, drone_down_speed, 0)
                except Exception as e:
                    print(f"Error al controlar drone: {e}")
            
            # Dibujar información en pantalla
            annotated_frame = draw_text_on_image(annotated_frame, messages)
            annotated_frame = draw_drone_status(
                annotated_frame, 
                "Controlada", 
                jump_detected
            )
            
            # Mostrar
            cv2.imshow("Jump Detection & Drone Control", annotated_frame)
            
            # Permitir salir
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
        
    except KeyboardInterrupt:
        print("\n\nMisión interrumpida por usuario")
    
    finally:
        # ===============================
        # LIMPIEZA Y ATERRIZAJE
        # ===============================
        print(f"\n{'='*80}")
        print("Finalizando misión...")
        
        cap.release()
        cv2.destroyAllWindows()
        
        if drone:
            try:
                print("Aterrizando drone...")
                drone.land()
                time.sleep(2)
                drone.disconnect()
                print("✓ Drone aterrizó y se desconectó")
            except Exception as e:
                print(f"Error al aterrizar: {e}")
        
        print(f"\nEstadísticas:")
        print(f"  Frames procesados: {frame_count}")
        print(f"  Saltos detectados: {jump_detector.jump_count}")
        print(f"{'='*80}\n")


# ===============================
# PUNTO DE ENTRADA
# ===============================

if __name__ == "__main__":
    """
    Ejecuta la misión de control de drone con detección de saltos
    
    EJEMPLOS DE CONFIGURACIÓN:
    
    1. CONFIGURACIÓN POR DEFECTO:
       mission_jump_and_fly(video_source=0)
    
    2. CON VELOCIDADES DE DRONE PERSONALIZADAS:
       mission_jump_and_fly(
           video_source=0,
           drone_up_speed=50,          # Subida normal
           drone_jump_boost_speed=90,  # Subida con boost al detectar salto
           drone_down_speed=-30        # Baja más rápido
       )
    
    3. CON ARCHIVO DE VIDEO:
       mission_jump_and_fly(
           video_source="path/to/video.mp4",
           drone_jump_boost_speed=85
       )
    
    4. MÁS SENSIBLE A LOS SALTOS Y CON BOOST MÁXIMO:
       mission_jump_and_fly(
           video_source=0,
           smooth_len=7,
           takeoff_velocity=0.015,
           landing_velocity=-0.012,
           debounce_frames=6,
           drone_up_speed=50,
           drone_jump_boost_speed=100  # Boost máximo
       )
    """
    
    # Ejecutar misión con configuración por defecto
    mission_jump_and_fly(video_source=0)
