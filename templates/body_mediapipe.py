<<<<<<< HEAD
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np

# Configuración del modelo Pose Landmarker utilizando la nueva API de MediaPipe Tasks
# Requiere que el archivo 'pose_landmarker.task' esté en la carpeta 'models'
base_options = python.BaseOptions(model_asset_path='models/pose_landmarker_lite.task')
options = vision.PoseLandmarkerOptions(base_options=base_options)
detector = vision.PoseLandmarker.create_from_options(options)

# Mapa de conexiones para el esqueleto del cuerpo (33 landmarks en total)
# Define qué puntos se deben unir para representar cabeza, brazos, torso y piernas
BODY_CONNECTIONS = [
    # Cabeza
    (0, 1), (1, 2), (2, 3), (3, 7),         # Lado derecho de la cara
    (0, 4), (4, 5), (5, 6), (6, 8),         # Lado izquierdo de la cara
    (9, 10),                                 # Mandíbula
    
    # Torso
    (11, 12),                                # Hombros
    (11, 13), (13, 15),                     # Brazo derecho
    (12, 14), (14, 16),                     # Brazo izquierdo
    
    # Cadera y piernas
    (23, 24),                                # Caderas
    (11, 23), (12, 24),                     # Conexión hombro-cadera
    (23, 25), (25, 27),                     # Pierna derecha
    (24, 26), (26, 28),                     # Pierna izquierda
    
    # Pies
    (27, 29), (29, 31),                     # Pie derecho
    (28, 30), (30, 32),                     # Pie izquierdo
]

def draw_landmarks_on_image(image, detection_result):
    """Proyecta los puntos detectados y sus conexiones sobre el frame original"""
    annotated_image = np.copy(image)
    
    for pose_landmarks in detection_result.pose_landmarks:
        # Dibujo de las líneas (conexiones) del esqueleto corporal
        for connection in BODY_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            if start_idx < len(pose_landmarks) and end_idx < len(pose_landmarks):
                start = pose_landmarks[start_idx]
                end = pose_landmarks[end_idx]
                
                # Conversión de coordenadas normalizadas (0.0 - 1.0) a píxeles de la imagen
                start_pos = (int(start.x * image.shape[1]), int(start.y * image.shape[0]))
                end_pos = (int(end.x * image.shape[1]), int(end.y * image.shape[0]))
                cv2.line(annotated_image, start_pos, end_pos, (0, 255, 0), 2)
        
        # Dibujo de los nodos (puntos clave) del cuerpo
        for landmark in pose_landmarks:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(annotated_image, (x, y), 4, (255, 0, 0), -1)
            
    return annotated_image

def detect_body_gesture(pose_landmarks):
    """Lógica heurística: detecta posturas corporales basadas en posiciones de articulaciones"""
    if not pose_landmarks:
        return "No body detected"
    
    landmarks = pose_landmarks[0]
    
    # Puntos de referencia principales
    nose = landmarks[0]
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]
    left_elbow = landmarks[13]
    right_elbow = landmarks[14]
    left_wrist = landmarks[15]
    right_wrist = landmarks[16]
    left_hip = landmarks[23]
    right_hip = landmarks[24]
    left_knee = landmarks[25]
    right_knee = landmarks[26]
    left_ankle = landmarks[27]
    right_ankle = landmarks[28]
    
    # Detección Brazos Levantados: Ambas muñecas por encima de los hombros
    if left_wrist.y < left_shoulder.y and right_wrist.y < right_shoulder.y:
        return "Arms Raised"
    
    # Detección Brazos Extendidos: Muñecas lejos horizontalmente de los hombros
    shoulder_width = abs(right_shoulder.x - left_shoulder.x)
    if (abs(left_wrist.x - left_shoulder.x) > shoulder_width * 0.5 and 
        abs(right_wrist.x - right_shoulder.x) > shoulder_width * 0.5 and
        left_wrist.y < left_shoulder.y + 0.1 and right_wrist.y < right_shoulder.y + 0.1):
        return "Arms Extended"
    
    # Detección De Pie: Tobillos visibles y por debajo de caderas
    if left_ankle.y > left_hip.y and right_ankle.y > right_hip.y:
        if left_ankle.visibility > 0.5 and right_ankle.visibility > 0.5:
            return "Standing"
    
    # Detección Sentado: Rodillas por encima de caderas
    if left_knee.y < left_hip.y and right_knee.y < right_hip.y:
        if left_knee.visibility > 0.5 and right_knee.visibility > 0.5:
            return "Sitting"
    
    # Detección Brazo Derecho Levantado
    if right_wrist.y < right_shoulder.y - 0.15:
        return "Right Arm Raised"
    
    # Detección Brazo Izquierdo Levantado
    if left_wrist.y < left_shoulder.y - 0.15:
        return "Left Arm Raised"
    
    # Detección Postura Inclinada: Nariz adelante del torso
    torso_x = (left_shoulder.x + right_shoulder.x) / 2
    if nose.x > torso_x + 0.1:
        return "Leaning Forward"
    
    # Detección Postura Normal
    return "Normal Posture"

try:
    print("Inicializando cámara...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: No se puede acceder a la cámara")
        exit()

    # Ajuste de resolución y tasa de refresco    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Configurar ventana para permitir redimensionamiento
    window_name = "Body Detection - Camara PC"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 960)
    
    print("=" * 50)
    print("Detección de Posturas Corporales - Cámara PC")
    print("=" * 50)
    print("Presiona Q o ESC en la ventana de video para salir")
    print("=" * 50)
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: No se puede leer frame de la cámara")
            break
            
        # MediaPipe requiere formato RGB, OpenCV captura en BGR
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Ejecución de la inferencia del modelo de pose
        detection_result = detector.detect(mp_image)
        
        # Generación de la imagen con la superposición gráfica
        annotated_image = draw_landmarks_on_image(frame, detection_result)
        
        gesture = "No body detected"
        if detection_result.pose_landmarks:
            gesture = detect_body_gesture(detection_result.pose_landmarks)
            
        # Visualización de etiquetas de texto en el frame
        cv2.putText(annotated_image, f"Posture: {gesture}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated_image, f"Bodies detected: {len(detection_result.pose_landmarks)}", 
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(annotated_image, "Press Q or ESC to exit", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
        cv2.imshow(window_name, annotated_image)
        
        # Log en consola cada 30 frames para monitoreo
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}: {gesture} - Bodies: {len(detection_result.pose_landmarks)}")
            
        # Control de salida unificado
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            print("Saliendo...")
            break

except Exception as e:
    print(f"Error crítico: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Liberación de recursos de hardware y cierre de ventanas
    print("Cerrando sesión...")
    try:
        cap.release()
    except NameError:
        pass
    cv2.destroyAllWindows()
    print("Programa finalizado")
=======
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np

# Configuración del modelo Pose Landmarker utilizando la nueva API de MediaPipe Tasks
# Requiere que el archivo 'pose_landmarker.task' esté en la carpeta 'models'
base_options = python.BaseOptions(model_asset_path='models/pose_landmarker_lite.task')
options = vision.PoseLandmarkerOptions(base_options=base_options)
detector = vision.PoseLandmarker.create_from_options(options)

# Mapa de conexiones para el esqueleto del cuerpo (33 landmarks en total)
# Define qué puntos se deben unir para representar cabeza, brazos, torso y piernas
BODY_CONNECTIONS = [
    # Cabeza
    (0, 1), (1, 2), (2, 3), (3, 7),         # Lado derecho de la cara
    (0, 4), (4, 5), (5, 6), (6, 8),         # Lado izquierdo de la cara
    (9, 10),                                 # Mandíbula
    
    # Torso
    (11, 12),                                # Hombros
    (11, 13), (13, 15),                     # Brazo derecho
    (12, 14), (14, 16),                     # Brazo izquierdo
    
    # Cadera y piernas
    (23, 24),                                # Caderas
    (11, 23), (12, 24),                     # Conexión hombro-cadera
    (23, 25), (25, 27),                     # Pierna derecha
    (24, 26), (26, 28),                     # Pierna izquierda
    
    # Pies
    (27, 29), (29, 31),                     # Pie derecho
    (28, 30), (30, 32),                     # Pie izquierdo
]

def draw_landmarks_on_image(image, detection_result):
    """Proyecta los puntos detectados y sus conexiones sobre el frame original"""
    annotated_image = np.copy(image)
    
    for pose_landmarks in detection_result.pose_landmarks:
        # Dibujo de las líneas (conexiones) del esqueleto corporal
        for connection in BODY_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            if start_idx < len(pose_landmarks) and end_idx < len(pose_landmarks):
                start = pose_landmarks[start_idx]
                end = pose_landmarks[end_idx]
                
                # Conversión de coordenadas normalizadas (0.0 - 1.0) a píxeles de la imagen
                start_pos = (int(start.x * image.shape[1]), int(start.y * image.shape[0]))
                end_pos = (int(end.x * image.shape[1]), int(end.y * image.shape[0]))
                cv2.line(annotated_image, start_pos, end_pos, (0, 255, 0), 2)
        
        # Dibujo de los nodos (puntos clave) del cuerpo
        for landmark in pose_landmarks:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(annotated_image, (x, y), 4, (255, 0, 0), -1)
            
    return annotated_image

def detect_body_gesture(pose_landmarks):
    """Lógica heurística: detecta posturas corporales basadas en posiciones de articulaciones"""
    if not pose_landmarks:
        return "No body detected"
    
    landmarks = pose_landmarks[0]
    
    # Puntos de referencia principales
    nose = landmarks[0]
    left_shoulder = landmarks[11]
    right_shoulder = landmarks[12]
    left_elbow = landmarks[13]
    right_elbow = landmarks[14]
    left_wrist = landmarks[15]
    right_wrist = landmarks[16]
    left_hip = landmarks[23]
    right_hip = landmarks[24]
    left_knee = landmarks[25]
    right_knee = landmarks[26]
    left_ankle = landmarks[27]
    right_ankle = landmarks[28]
    
    # Detección Brazos Levantados: Ambas muñecas por encima de los hombros
    if left_wrist.y < left_shoulder.y and right_wrist.y < right_shoulder.y:
        return "Arms Raised"
    
    # Detección Brazos Extendidos: Muñecas lejos horizontalmente de los hombros
    shoulder_width = abs(right_shoulder.x - left_shoulder.x)
    if (abs(left_wrist.x - left_shoulder.x) > shoulder_width * 0.5 and 
        abs(right_wrist.x - right_shoulder.x) > shoulder_width * 0.5 and
        left_wrist.y < left_shoulder.y + 0.1 and right_wrist.y < right_shoulder.y + 0.1):
        return "Arms Extended"
    
    # Detección De Pie: Tobillos visibles y por debajo de caderas
    if left_ankle.y > left_hip.y and right_ankle.y > right_hip.y:
        if left_ankle.visibility > 0.5 and right_ankle.visibility > 0.5:
            return "Standing"
    
    # Detección Sentado: Rodillas por encima de caderas
    if left_knee.y < left_hip.y and right_knee.y < right_hip.y:
        if left_knee.visibility > 0.5 and right_knee.visibility > 0.5:
            return "Sitting"
    
    # Detección Brazo Derecho Levantado
    if right_wrist.y < right_shoulder.y - 0.15:
        return "Right Arm Raised"
    
    # Detección Brazo Izquierdo Levantado
    if left_wrist.y < left_shoulder.y - 0.15:
        return "Left Arm Raised"
    
    # Detección Postura Inclinada: Nariz adelante del torso
    torso_x = (left_shoulder.x + right_shoulder.x) / 2
    if nose.x > torso_x + 0.1:
        return "Leaning Forward"
    
    # Detección Postura Normal
    return "Normal Posture"

try:
    print("Inicializando cámara...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: No se puede acceder a la cámara")
        exit()

    # Ajuste de resolución y tasa de refresco    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Configurar ventana para permitir redimensionamiento
    window_name = "Body Detection - Camara PC"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 960)
    
    print("=" * 50)
    print("Detección de Posturas Corporales - Cámara PC")
    print("=" * 50)
    print("Presiona Q o ESC en la ventana de video para salir")
    print("=" * 50)
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: No se puede leer frame de la cámara")
            break
            
        # MediaPipe requiere formato RGB, OpenCV captura en BGR
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Ejecución de la inferencia del modelo de pose
        detection_result = detector.detect(mp_image)
        
        # Generación de la imagen con la superposición gráfica
        annotated_image = draw_landmarks_on_image(frame, detection_result)
        
        gesture = "No body detected"
        if detection_result.pose_landmarks:
            gesture = detect_body_gesture(detection_result.pose_landmarks)
            
        # Visualización de etiquetas de texto en el frame
        cv2.putText(annotated_image, f"Posture: {gesture}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated_image, f"Bodies detected: {len(detection_result.pose_landmarks)}", 
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(annotated_image, "Press Q or ESC to exit", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
        cv2.imshow(window_name, annotated_image)
        
        # Log en consola cada 30 frames para monitoreo
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}: {gesture} - Bodies: {len(detection_result.pose_landmarks)}")
            
        # Control de salida unificado
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            print("Saliendo...")
            break

except Exception as e:
    print(f"Error crítico: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Liberación de recursos de hardware y cierre de ventanas
    print("Cerrando sesión...")
    try:
        cap.release()
    except NameError:
        pass
    cv2.destroyAllWindows()
    print("Programa finalizado")
>>>>>>> bd5b9b8bcdd753e4d51a89fff8d1e311fcdab9c0
