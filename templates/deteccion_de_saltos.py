<<<<<<< HEAD
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np
from collections import deque
from typing import Tuple

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
# DETECTOR DE SALTOS - VERTICAL VELOCITY METHOD
# ===============================

class VerticalVelocityJumpDetector:
    """
    Detector de saltos basado en VERTICAL VELOCITY OF HIP CENTER
    
    Algoritmo:
    1. Smooth: Hip center Y se suaviza con media móvil de 9 frames
    2. Velocity: velocity = prev_smoothed_y - smoothed_y 
       (positivo = hacia arriba, negativo = hacia abajo)
    3. Takeoff: Cuando NO está en aire, si velocity > TAKEOFF_VELOCITY → marcar en aire
    4. Landing: Cuando está en aire, si velocity < LANDING_VELOCITY → aterrizaje
    5. Debounce: Mínimo 12 frames entre dos saltos contados
    """
    
    def __init__(self, smooth_len=9, takeoff_velocity=0.019, 
                 landing_velocity=-0.015, debounce_frames=9):
        """
        Args:
            smooth_len: Ventana de suavizado (9 = más responsivo, detecta mejor)
            takeoff_velocity: Velocidad mínima para detectar despegue (0.019 por defecto - sensible)
            landing_velocity: Velocidad máxima para detectar aterrizaje (-0.015 por defecto)
            debounce_frames: Frames mínimos entre dos saltos contados (9 por defecto)
        """
        self.smooth_len = smooth_len
        self.takeoff_velocity = takeoff_velocity
        self.landing_velocity = landing_velocity
        self.debounce_frames = debounce_frames
        
        # Historial de alturas de caderas (sin suavizar)
        self.hip_y_history = deque(maxlen=smooth_len)
        
        # Historial de alturas suavizadas
        self.smoothed_y_history = deque(maxlen=2)  # Solo necesitamos 2 valores
        
        # Estado del salto
        self.in_air = False
        self.jump_count = 0
        self.frames_since_last_jump = 0
        
        # Para visualización
        self.last_velocity = 0.0
        self.current_state = "TIERRA"
        
    def check_landmarks_validity(self, landmarks) -> bool:
        """
        Verifica que los landmarks sean válidos y confiables
        - Ambas caderas deben ser visibles (visibility > 0.5)
        - La persona no debe estar demasiado cerca (tamaño del cuerpo adecuado)
        
        Returns:
            True si los landmarks son válidos, False si no
        """
        if not landmarks or len(landmarks) < 29:
            return False
        
        left_hip = landmarks[KEYPOINTS['left_hip']]
        right_hip = landmarks[KEYPOINTS['right_hip']]
        
        # Verificar visibilidad de ambas caderas
        if left_hip.visibility < 0.5 or right_hip.visibility < 0.5:
            return False
        
        # Detectar si está demasiado cerca (caderas muy separadas horizontalmente)
        # Si la distancia entre caderas > 0.35 (35% del frame), está muy cerca
        hip_distance = abs(right_hip.x - left_hip.x)
        if hip_distance > 0.40:
            return False
        
        # Detectar si está demasiado lejos (caderas muy cercanas)
        if hip_distance < 0.05:
            return False
        
        return True
    
    def get_hip_center_y(self, landmarks) -> float:
        """Obtiene posición Y promedio de caderas (normalizado 0-1)"""
        if not landmarks:
            return 0.0
        left_hip = landmarks[KEYPOINTS['left_hip']]
        right_hip = landmarks[KEYPOINTS['right_hip']]
        return (left_hip.y + right_hip.y) / 2.0
    
    def smooth_hip_y(self, current_y: float) -> float:
        """
        Suaviza la posición Y de caderas usando media móvil
        
        Args:
            current_y: Valor actual Y de caderas
            
        Returns:
            Valor suavizado (promedio de smooth_len últimos frames)
        """
        self.hip_y_history.append(current_y)
        
        # Calcular promedio de los frames disponibles
        smoothed = np.mean(list(self.hip_y_history))
        return smoothed
    
    def compute_velocity(self, smoothed_y: float) -> float:
        """
        Calcula velocidad vertical
        velocity = prev_smoothed_y - smoothed_y
        - Positivo = hacia arriba (DESPEGUE)
        - Negativo = hacia abajo (ATERRIZAJE)
        
        Args:
            smoothed_y: Valor suavizado actual
            
        Returns:
            Velocidad vertical
        """
        if len(self.smoothed_y_history) < 1:
            self.smoothed_y_history.append(smoothed_y)
            return 0.0
        
        prev_smoothed_y = self.smoothed_y_history[0]
        velocity = prev_smoothed_y - smoothed_y  # Negativo en Y = hacia arriba en pantalla
        
        self.smoothed_y_history.append(smoothed_y)
        
        return velocity
    
    def detect_jump(self, landmarks) -> Tuple[bool, str]:
        """
        Detecta saltos usando velocidad vertical de caderas
        
        Lógica:
        - TAKEOFF: velocity > TAKEOFF_VELOCITY → persona despega
        - LANDING: En aire + velocity < LANDING_VELOCITY → aterrizaje
        - Debounce: Esperar N frames antes de contar otro salto
        
        Returns:
            (jump_detected, message)
        """
        jump_detected = False
        
        if not landmarks:
            return False, "No se detectó persona"
        
        # VALIDACIÓN: Verificar que los landmarks sean confiables
        if not self.check_landmarks_validity(landmarks):
            self.frames_since_last_jump += 1
            return False, "⚠ Acércate o retrocede (distancia incorrecta)"
        
        # 1. Obtener Y actual de caderas
        current_y = self.get_hip_center_y(landmarks)
        
        # 2. Suavizar
        smoothed_y = self.smooth_hip_y(current_y)
        
        # 3. Calcular velocidad
        velocity = self.compute_velocity(smoothed_y)
        self.last_velocity = velocity
        
        # Incrementar contador de debounce
        self.frames_since_last_jump += 1
        
        # 4. DETECCIÓN DE DESPEGUE (takeoff)
        if not self.in_air and velocity > self.takeoff_velocity:
            self.in_air = True
            self.current_state = "AIRE ↑"
        
        # 5. DETECCIÓN DE ATERRIZAJE (landing) con debounce
        elif self.in_air and velocity < self.landing_velocity:
            self.in_air = False
            
            # Contar salto solo si ha pasado debounce
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
        
        # Construir mensaje mejorado
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
        # Dibujar conexiones
        for connection in BODY_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            if start_idx < len(pose_landmarks) and end_idx < len(pose_landmarks):
                start = pose_landmarks[start_idx]
                end = pose_landmarks[end_idx]
                
                start_pos = (int(start.x * image.shape[1]), int(start.y * image.shape[0]))
                end_pos = (int(end.x * image.shape[1]), int(end.y * image.shape[0]))
                cv2.line(annotated_image, start_pos, end_pos, (0, 255, 0), 2)
        
        # Dibujar puntos
        for landmark in pose_landmarks:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(annotated_image, (x, y), 4, (255, 0, 0), -1)
    
    return annotated_image

def draw_text_on_image(image, texts, position=(20, 50), font_scale=0.9, color=(0, 255, 0)):
    """Dibuja texto con fondo semi-transparente para mejor legibilidad"""
    output_image = np.copy(image)
    y_offset = position[1]
    
    for text in texts:
        # Dividir por líneas si hay saltos de línea
        lines = text.split('\n')
        
        for line in lines:
            # Determinar color según contenido
            if "🎯" in line or "SALTO" in line or "SALTANDO" in line:
                text_color = (0, 0, 255)  # Rojo para saltos
                bg_color = (0, 0, 150)    # Fondo rojo oscuro
            elif "AIRE" in line:
                text_color = (0, 255, 255)  # Cyan para aire
                bg_color = (100, 100, 0)    # Fondo oscuro
            else:
                text_color = (0, 255, 0)   # Verde para información normal
                bg_color = (0, 100, 0)     # Fondo verde oscuro
            
            # Obtener tamaño del texto
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            text_width = text_size[0]
            text_height = text_size[1]
            
            # Crear rectángulo de fondo
            margin = 10
            cv2.rectangle(output_image, 
                         (position[0] - margin, y_offset - text_height - margin),
                         (position[0] + text_width + margin, y_offset + margin),
                         bg_color, -1)
            
            # Dibujar texto
            cv2.putText(output_image, line, (position[0], y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2)
            y_offset += 40
    
    return output_image

def draw_calibration_info(image, smooth_len, takeoff_vel, landing_vel, debounce):
    """Dibuja información de calibración en la parte inferior"""
    output = np.copy(image)
    
    # Fondo oscuro en la parte inferior
    cv2.rectangle(output, (0, output.shape[0] - 50), 
                 (output.shape[1], output.shape[0]), (30, 30, 30), -1)
    
    # Información de calibración
    info_text = (
        f"SMOOTH={smooth_len} | "
        f"TAKEOFF={takeoff_vel:.3f} | "
        f"LANDING={landing_vel:.3f} | "
        f"DEBOUNCE={debounce}"
    )
    
    cv2.putText(output, info_text, (20, output.shape[0] - 15), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    return output


# ===============================
# FUNCIÓN PRINCIPAL
# ===============================

def process_video(video_source=0, 
                  smooth_len=9,
                  takeoff_velocity=0.019,
                  landing_velocity=-0.015,
                  debounce_frames=9):
    """
    Procesa video en tiempo real detectando saltos con método de VERTICAL VELOCITY
    
    Args:
        video_source: 0 para cámara web, o ruta a archivo de video
        smooth_len: Ventana de suavizado (9 por defecto - más responsivo)
        takeoff_velocity: Umbral de velocidad para despegue (0.019 por defecto - más sensible)
        landing_velocity: Umbral de velocidad para aterrizaje (-0.015 por defecto)
        debounce_frames: Frames mínimos entre dos saltos (9 por defecto - menos espera)
    """
    cap = cv2.VideoCapture(video_source)
    jump_detector = VerticalVelocityJumpDetector(
        smooth_len=smooth_len,
        takeoff_velocity=takeoff_velocity,
        landing_velocity=landing_velocity,
        debounce_frames=debounce_frames
    )
    
    print(f"\n{'='*80}")
    print(f"DETECTOR DE SALTOS - VERTICAL VELOCITY METHOD")
    print(f"{'='*80}")
    print(f"Configuración:")
    print(f"  SMOOTH_LEN:        {smooth_len}")
    print(f"  TAKEOFF_VELOCITY:  {takeoff_velocity}")
    print(f"  LANDING_VELOCITY:  {landing_velocity}")
    print(f"  DEBOUNCE_FRAMES:   {debounce_frames}")
    print(f"\nDistancia óptima de la cámara:")
    print(f"  - Mantente a una distancia moderada de la cámara")
    print(f"  - No demasiado cerca (evita llenar el frame)")
    print(f"  - No demasiado lejos (asegúrate de que te vea bien)")
    print(f"{'='*80}")
    print("Presiona 'q' o ESC para salir\n")
    
    frame_count = 0
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        frame_count += 1
        
        # Convertir BGR a RGB para MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Detectar pose
        detection_result = detector.detect(image_mp)
        
        # Dibujar landmarks
        annotated_frame = draw_landmarks_on_image(frame, detection_result)
        
        # Detectar saltos
        messages = []
        
        if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
            landmarks = detection_result.pose_landmarks[0]
            jump_detected, message = jump_detector.detect_jump(landmarks)
            
            # Mostrar mensaje apropiado
            if jump_detected:
                messages.append(f"🎯 ¡¡SALTO #{jump_detector.jump_count}!!")
                print(f"\n{'='*50}")
                print(f"✓✓✓ SALTO #{jump_detector.jump_count} DETECTADO EN FRAME {frame_count} ✓✓✓")
                print(f"{'='*50}\n")
            else:
                messages.append(message)
        else:
            messages.append("⚠ No se detectó persona")
        
        # Dibujar información
        annotated_frame = draw_text_on_image(annotated_frame, messages)
        annotated_frame = draw_calibration_info(
            annotated_frame, smooth_len, takeoff_velocity, landing_velocity, debounce_frames
        )
        
        # Mostrar
        cv2.imshow("Jump Detection - Vertical Velocity Method", annotated_frame)
        
        # Permitir salir con 'q' o ESC (27)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n{'='*80}")
    print(f"Sesión finalizada.")
    print(f"Saltos detectados: {jump_detector.jump_count}")
    print(f"{'='*80}\n")


# ===============================
# EJEMPLOS DE USO Y CONFIGURACIÓN
# ===============================

if __name__ == "__main__":
    """
    EJEMPLOS DE CONFIGURACIÓN:
    
    1. CONFIGURACIÓN POR DEFECTO (recomendado - MÁS SENSIBLE):
       process_video(video_source=0)
       smooth_len=9, takeoff_velocity=0.019, landing_velocity=-0.015, debounce=9
       ✓ Detecta mejor los saltos
       ✓ Más responsivo
    
    2. MÁS SENSIBLE (detecta incluso saltos débiles):
       process_video(
           video_source=0,
           smooth_len=7,               # Menos suavizado
           takeoff_velocity=0.015,     # Velocidad mínima menor
           landing_velocity=-0.012,    # Menos exigente
           debounce_frames=6           # Menos espera entre saltos
       )
    
    3. MÁS ESTRICTO (rechaza saltos débiles):
       process_video(
           video_source=0,
           smooth_len=11,              # Más suavizado
           takeoff_velocity=0.023,     # Velocidad mínima más alta
           landing_velocity=-0.018,    # Más exigente
           debounce_frames=12          # Más espera entre saltos
       )
    
    4. CON ARCHIVO DE VIDEO:
       process_video(
           video_source="path/to/video.mp4",
           smooth_len=9,
           takeoff_velocity=0.019,
           landing_velocity=-0.015,
           debounce_frames=9
       )
    
    PARÁMETROS SINTONIZABLES:
    - smooth_len: 5-15 (más pequeño = más responsivo, más ruido)
    - takeoff_velocity: 0.012-0.030 (más bajo = más sensible)
    - landing_velocity: -0.020 a -0.010 (menos negativo = más sensible)
    - debounce_frames: 6-15 (más bajo = menos espera entre saltos)
    
    CONTROLES:
    - Presiona 'q' o ESC para salir
    - La ventana se cierra automáticamente si no hay entrada de video
    
    RECOMENDACIONES:
    - Si detectas falsos positivos: Aumenta takeoff_velocity a 0.021
    - Si no detecta suficientemente: Reduce takeoff_velocity a 0.017
    - Si ves saltos fantasma: Aumenta smooth_len a 10
    """
    
    # Ejecutar con configuración por defecto (más sensible)
    process_video(video_source=0)



=======
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np
from collections import deque
from typing import Tuple

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
# DETECTOR DE SALTOS - VERTICAL VELOCITY METHOD
# ===============================

class VerticalVelocityJumpDetector:
    """
    Detector de saltos basado en VERTICAL VELOCITY OF HIP CENTER
    
    Algoritmo:
    1. Smooth: Hip center Y se suaviza con media móvil de 9 frames
    2. Velocity: velocity = prev_smoothed_y - smoothed_y 
       (positivo = hacia arriba, negativo = hacia abajo)
    3. Takeoff: Cuando NO está en aire, si velocity > TAKEOFF_VELOCITY → marcar en aire
    4. Landing: Cuando está en aire, si velocity < LANDING_VELOCITY → aterrizaje
    5. Debounce: Mínimo 12 frames entre dos saltos contados
    """
    
    def __init__(self, smooth_len=9, takeoff_velocity=0.019, 
                 landing_velocity=-0.015, debounce_frames=9):
        """
        Args:
            smooth_len: Ventana de suavizado (9 = más responsivo, detecta mejor)
            takeoff_velocity: Velocidad mínima para detectar despegue (0.019 por defecto - sensible)
            landing_velocity: Velocidad máxima para detectar aterrizaje (-0.015 por defecto)
            debounce_frames: Frames mínimos entre dos saltos contados (9 por defecto)
        """
        self.smooth_len = smooth_len
        self.takeoff_velocity = takeoff_velocity
        self.landing_velocity = landing_velocity
        self.debounce_frames = debounce_frames
        
        # Historial de alturas de caderas (sin suavizar)
        self.hip_y_history = deque(maxlen=smooth_len)
        
        # Historial de alturas suavizadas
        self.smoothed_y_history = deque(maxlen=2)  # Solo necesitamos 2 valores
        
        # Estado del salto
        self.in_air = False
        self.jump_count = 0
        self.frames_since_last_jump = 0
        
        # Para visualización
        self.last_velocity = 0.0
        self.current_state = "TIERRA"
        
    def check_landmarks_validity(self, landmarks) -> bool:
        """
        Verifica que los landmarks sean válidos y confiables
        - Ambas caderas deben ser visibles (visibility > 0.5)
        - La persona no debe estar demasiado cerca (tamaño del cuerpo adecuado)
        
        Returns:
            True si los landmarks son válidos, False si no
        """
        if not landmarks or len(landmarks) < 29:
            return False
        
        left_hip = landmarks[KEYPOINTS['left_hip']]
        right_hip = landmarks[KEYPOINTS['right_hip']]
        
        # Verificar visibilidad de ambas caderas
        if left_hip.visibility < 0.5 or right_hip.visibility < 0.5:
            return False
        
        # Detectar si está demasiado cerca (caderas muy separadas horizontalmente)
        # Si la distancia entre caderas > 0.35 (35% del frame), está muy cerca
        hip_distance = abs(right_hip.x - left_hip.x)
        if hip_distance > 0.40:
            return False
        
        # Detectar si está demasiado lejos (caderas muy cercanas)
        if hip_distance < 0.05:
            return False
        
        return True
    
    def get_hip_center_y(self, landmarks) -> float:
        """Obtiene posición Y promedio de caderas (normalizado 0-1)"""
        if not landmarks:
            return 0.0
        left_hip = landmarks[KEYPOINTS['left_hip']]
        right_hip = landmarks[KEYPOINTS['right_hip']]
        return (left_hip.y + right_hip.y) / 2.0
    
    def smooth_hip_y(self, current_y: float) -> float:
        """
        Suaviza la posición Y de caderas usando media móvil
        
        Args:
            current_y: Valor actual Y de caderas
            
        Returns:
            Valor suavizado (promedio de smooth_len últimos frames)
        """
        self.hip_y_history.append(current_y)
        
        # Calcular promedio de los frames disponibles
        smoothed = np.mean(list(self.hip_y_history))
        return smoothed
    
    def compute_velocity(self, smoothed_y: float) -> float:
        """
        Calcula velocidad vertical
        velocity = prev_smoothed_y - smoothed_y
        - Positivo = hacia arriba (DESPEGUE)
        - Negativo = hacia abajo (ATERRIZAJE)
        
        Args:
            smoothed_y: Valor suavizado actual
            
        Returns:
            Velocidad vertical
        """
        if len(self.smoothed_y_history) < 1:
            self.smoothed_y_history.append(smoothed_y)
            return 0.0
        
        prev_smoothed_y = self.smoothed_y_history[0]
        velocity = prev_smoothed_y - smoothed_y  # Negativo en Y = hacia arriba en pantalla
        
        self.smoothed_y_history.append(smoothed_y)
        
        return velocity
    
    def detect_jump(self, landmarks) -> Tuple[bool, str]:
        """
        Detecta saltos usando velocidad vertical de caderas
        
        Lógica:
        - TAKEOFF: velocity > TAKEOFF_VELOCITY → persona despega
        - LANDING: En aire + velocity < LANDING_VELOCITY → aterrizaje
        - Debounce: Esperar N frames antes de contar otro salto
        
        Returns:
            (jump_detected, message)
        """
        jump_detected = False
        
        if not landmarks:
            return False, "No se detectó persona"
        
        # VALIDACIÓN: Verificar que los landmarks sean confiables
        if not self.check_landmarks_validity(landmarks):
            self.frames_since_last_jump += 1
            return False, "⚠ Acércate o retrocede (distancia incorrecta)"
        
        # 1. Obtener Y actual de caderas
        current_y = self.get_hip_center_y(landmarks)
        
        # 2. Suavizar
        smoothed_y = self.smooth_hip_y(current_y)
        
        # 3. Calcular velocidad
        velocity = self.compute_velocity(smoothed_y)
        self.last_velocity = velocity
        
        # Incrementar contador de debounce
        self.frames_since_last_jump += 1
        
        # 4. DETECCIÓN DE DESPEGUE (takeoff)
        if not self.in_air and velocity > self.takeoff_velocity:
            self.in_air = True
            self.current_state = "AIRE ↑"
        
        # 5. DETECCIÓN DE ATERRIZAJE (landing) con debounce
        elif self.in_air and velocity < self.landing_velocity:
            self.in_air = False
            
            # Contar salto solo si ha pasado debounce
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
        
        # Construir mensaje mejorado
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
        # Dibujar conexiones
        for connection in BODY_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            if start_idx < len(pose_landmarks) and end_idx < len(pose_landmarks):
                start = pose_landmarks[start_idx]
                end = pose_landmarks[end_idx]
                
                start_pos = (int(start.x * image.shape[1]), int(start.y * image.shape[0]))
                end_pos = (int(end.x * image.shape[1]), int(end.y * image.shape[0]))
                cv2.line(annotated_image, start_pos, end_pos, (0, 255, 0), 2)
        
        # Dibujar puntos
        for landmark in pose_landmarks:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(annotated_image, (x, y), 4, (255, 0, 0), -1)
    
    return annotated_image

def draw_text_on_image(image, texts, position=(20, 50), font_scale=0.9, color=(0, 255, 0)):
    """Dibuja texto con fondo semi-transparente para mejor legibilidad"""
    output_image = np.copy(image)
    y_offset = position[1]
    
    for text in texts:
        # Dividir por líneas si hay saltos de línea
        lines = text.split('\n')
        
        for line in lines:
            # Determinar color según contenido
            if "🎯" in line or "SALTO" in line or "SALTANDO" in line:
                text_color = (0, 0, 255)  # Rojo para saltos
                bg_color = (0, 0, 150)    # Fondo rojo oscuro
            elif "AIRE" in line:
                text_color = (0, 255, 255)  # Cyan para aire
                bg_color = (100, 100, 0)    # Fondo oscuro
            else:
                text_color = (0, 255, 0)   # Verde para información normal
                bg_color = (0, 100, 0)     # Fondo verde oscuro
            
            # Obtener tamaño del texto
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            text_width = text_size[0]
            text_height = text_size[1]
            
            # Crear rectángulo de fondo
            margin = 10
            cv2.rectangle(output_image, 
                         (position[0] - margin, y_offset - text_height - margin),
                         (position[0] + text_width + margin, y_offset + margin),
                         bg_color, -1)
            
            # Dibujar texto
            cv2.putText(output_image, line, (position[0], y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2)
            y_offset += 40
    
    return output_image

def draw_calibration_info(image, smooth_len, takeoff_vel, landing_vel, debounce):
    """Dibuja información de calibración en la parte inferior"""
    output = np.copy(image)
    
    # Fondo oscuro en la parte inferior
    cv2.rectangle(output, (0, output.shape[0] - 50), 
                 (output.shape[1], output.shape[0]), (30, 30, 30), -1)
    
    # Información de calibración
    info_text = (
        f"SMOOTH={smooth_len} | "
        f"TAKEOFF={takeoff_vel:.3f} | "
        f"LANDING={landing_vel:.3f} | "
        f"DEBOUNCE={debounce}"
    )
    
    cv2.putText(output, info_text, (20, output.shape[0] - 15), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    return output


# ===============================
# FUNCIÓN PRINCIPAL
# ===============================

def process_video(video_source=0, 
                  smooth_len=9,
                  takeoff_velocity=0.019,
                  landing_velocity=-0.015,
                  debounce_frames=9):
    """
    Procesa video en tiempo real detectando saltos con método de VERTICAL VELOCITY
    
    Args:
        video_source: 0 para cámara web, o ruta a archivo de video
        smooth_len: Ventana de suavizado (9 por defecto - más responsivo)
        takeoff_velocity: Umbral de velocidad para despegue (0.019 por defecto - más sensible)
        landing_velocity: Umbral de velocidad para aterrizaje (-0.015 por defecto)
        debounce_frames: Frames mínimos entre dos saltos (9 por defecto - menos espera)
    """
    cap = cv2.VideoCapture(video_source)
    jump_detector = VerticalVelocityJumpDetector(
        smooth_len=smooth_len,
        takeoff_velocity=takeoff_velocity,
        landing_velocity=landing_velocity,
        debounce_frames=debounce_frames
    )
    
    print(f"\n{'='*80}")
    print(f"DETECTOR DE SALTOS - VERTICAL VELOCITY METHOD")
    print(f"{'='*80}")
    print(f"Configuración:")
    print(f"  SMOOTH_LEN:        {smooth_len}")
    print(f"  TAKEOFF_VELOCITY:  {takeoff_velocity}")
    print(f"  LANDING_VELOCITY:  {landing_velocity}")
    print(f"  DEBOUNCE_FRAMES:   {debounce_frames}")
    print(f"\nDistancia óptima de la cámara:")
    print(f"  - Mantente a una distancia moderada de la cámara")
    print(f"  - No demasiado cerca (evita llenar el frame)")
    print(f"  - No demasiado lejos (asegúrate de que te vea bien)")
    print(f"{'='*80}")
    print("Presiona 'q' o ESC para salir\n")
    
    frame_count = 0
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        frame_count += 1
        
        # Convertir BGR a RGB para MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Detectar pose
        detection_result = detector.detect(image_mp)
        
        # Dibujar landmarks
        annotated_frame = draw_landmarks_on_image(frame, detection_result)
        
        # Detectar saltos
        messages = []
        
        if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
            landmarks = detection_result.pose_landmarks[0]
            jump_detected, message = jump_detector.detect_jump(landmarks)
            
            # Mostrar mensaje apropiado
            if jump_detected:
                messages.append(f"🎯 ¡¡SALTO #{jump_detector.jump_count}!!")
                print(f"\n{'='*50}")
                print(f"✓✓✓ SALTO #{jump_detector.jump_count} DETECTADO EN FRAME {frame_count} ✓✓✓")
                print(f"{'='*50}\n")
            else:
                messages.append(message)
        else:
            messages.append("⚠ No se detectó persona")
        
        # Dibujar información
        annotated_frame = draw_text_on_image(annotated_frame, messages)
        annotated_frame = draw_calibration_info(
            annotated_frame, smooth_len, takeoff_velocity, landing_velocity, debounce_frames
        )
        
        # Mostrar
        cv2.imshow("Jump Detection - Vertical Velocity Method", annotated_frame)
        
        # Permitir salir con 'q' o ESC (27)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n{'='*80}")
    print(f"Sesión finalizada.")
    print(f"Saltos detectados: {jump_detector.jump_count}")
    print(f"{'='*80}\n")


# ===============================
# EJEMPLOS DE USO Y CONFIGURACIÓN
# ===============================

if __name__ == "__main__":
    """
    EJEMPLOS DE CONFIGURACIÓN:
    
    1. CONFIGURACIÓN POR DEFECTO (recomendado - MÁS SENSIBLE):
       process_video(video_source=0)
       smooth_len=9, takeoff_velocity=0.019, landing_velocity=-0.015, debounce=9
       ✓ Detecta mejor los saltos
       ✓ Más responsivo
    
    2. MÁS SENSIBLE (detecta incluso saltos débiles):
       process_video(
           video_source=0,
           smooth_len=7,               # Menos suavizado
           takeoff_velocity=0.015,     # Velocidad mínima menor
           landing_velocity=-0.012,    # Menos exigente
           debounce_frames=6           # Menos espera entre saltos
       )
    
    3. MÁS ESTRICTO (rechaza saltos débiles):
       process_video(
           video_source=0,
           smooth_len=11,              # Más suavizado
           takeoff_velocity=0.023,     # Velocidad mínima más alta
           landing_velocity=-0.018,    # Más exigente
           debounce_frames=12          # Más espera entre saltos
       )
    
    4. CON ARCHIVO DE VIDEO:
       process_video(
           video_source="path/to/video.mp4",
           smooth_len=9,
           takeoff_velocity=0.019,
           landing_velocity=-0.015,
           debounce_frames=9
       )
    
    PARÁMETROS SINTONIZABLES:
    - smooth_len: 5-15 (más pequeño = más responsivo, más ruido)
    - takeoff_velocity: 0.012-0.030 (más bajo = más sensible)
    - landing_velocity: -0.020 a -0.010 (menos negativo = más sensible)
    - debounce_frames: 6-15 (más bajo = menos espera entre saltos)
    
    CONTROLES:
    - Presiona 'q' o ESC para salir
    - La ventana se cierra automáticamente si no hay entrada de video
    
    RECOMENDACIONES:
    - Si detectas falsos positivos: Aumenta takeoff_velocity a 0.021
    - Si no detecta suficientemente: Reduce takeoff_velocity a 0.017
    - Si ves saltos fantasma: Aumenta smooth_len a 10
    """
    
    # Ejecutar con configuración por defecto (más sensible)
    process_video(video_source=0)



>>>>>>> bd5b9b8bcdd753e4d51a89fff8d1e311fcdab9c0
