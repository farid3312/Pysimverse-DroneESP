<<<<<<< HEAD
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np

# Configuración del modelo Hand Landmarker utilizando la nueva API de MediaPipe Tasks
# Requiere que el archivo 'hand_landmarker.task' esté en el mismo directorio
base_options = python.BaseOptions(model_asset_path='models/hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
detector = vision.HandLandmarker.create_from_options(options)

# Mapa de conexiones manual para el esqueleto de la mano (21 landmarks en total)
# Define qué puntos se deben unir para representar pulgar, dedos y palma

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # Pulgar
    (0, 5), (5, 6), (6, 7), (7, 8),         # Índice
    (5, 9), (9, 10), (10, 11), (11, 12),    # Medio
    (9, 13), (13, 14), (14, 15), (15, 16),  # Anular
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Meñique y base
]

def draw_landmarks_on_image(image, detection_result):
    """Proyecta los puntos detectados y sus conexiones sobre el frame original"""
    annotated_image = np.copy(image)
    
    for hand_landmarks in detection_result.hand_landmarks:
        # Dibujo de las líneas (conexiones) del esqueleto
        for connection in HAND_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            if start_idx < len(hand_landmarks) and end_idx < len(hand_landmarks):
                start = hand_landmarks[start_idx]
                end = hand_landmarks[end_idx]
                
                # Conversión de coordenadas normalizadas (0.0 - 1.0) a píxeles de la imagen
                start_pos = (int(start.x * image.shape[1]), int(start.y * image.shape[0]))
                end_pos = (int(end.x * image.shape[1]), int(end.y * image.shape[0]))
                cv2.line(annotated_image, start_pos, end_pos, (0, 255, 0), 2)
        
        # Dibujo de los nodos (puntos clave) de la mano
        for landmark in hand_landmarks:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(annotated_image, (x, y), 3, (255, 0, 0), -1)
            
    return annotated_image

def detect_hand_gesture(hand_landmarks):
    """Lógica heurística: compara la altura (eje Y) de las puntas contra la palma"""
    if not hand_landmarks:
        return "No hand detected"
    # Referencia de los puntos clave (Tips)
    landmarks = hand_landmarks[0]
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    middle_tip = landmarks[12]
    ring_tip = landmarks[16]
    pinky_tip = landmarks[20]
    palm = landmarks[0] # Base de la muñeca
    
    # Detección Thumbs Up: Pulgar arriba de la palma, índice abajo
    if thumb_tip.y < palm.y and index_tip.y > palm.y:
        return "Thumbs Up"
    # Detección Peace: Índice y medio arriba, anular y meñique abajo
    if (index_tip.y < palm.y and middle_tip.y < palm.y and 
        ring_tip.y > palm.y and pinky_tip.y > palm.y):
        return "Peace Sign"
    # Detección OK: Proximidad mínima entre punta de pulgar e índice
    if (abs(thumb_tip.x - index_tip.x) < 0.05 and 
        abs(thumb_tip.y - index_tip.y) < 0.05):
        return "OK Sign"
    # Detección Fist: Todas las puntas por debajo del nivel de la palma
    if (index_tip.y > palm.y and middle_tip.y > palm.y and 
        ring_tip.y > palm.y and pinky_tip.y > palm.y):
        return "Closed Fist"
    # Detección Open Hand: Todas las puntas por encima de la palma
    if (thumb_tip.y < palm.y and index_tip.y < palm.y and 
        middle_tip.y < palm.y and ring_tip.y < palm.y and pinky_tip.y < palm.y):
        return "Open Hand"
        
    return "Unknown Gesture"

try:
    print("Inicializando cámara...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: No se puede acceder a la cámara")
        exit()

    # Ajuste de resolución y tasa de refresco    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("=" * 50)
    print("Detección de Gestos de Mano - Cámara PC")
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
        # Ejecución de la inferencia del modelo
        detection_result = detector.detect(mp_image)
        
        # Generación de la imagen con la superposición gráfica
        annotated_image = draw_landmarks_on_image(frame, detection_result)
        
        gesture = "No hand detected"
        if detection_result.hand_landmarks:
            gesture = detect_hand_gesture(detection_result.hand_landmarks)
            
        # Visualización de etiquetas de texto en el frame
        cv2.putText(annotated_image, f"Gesture: {gesture}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated_image, f"Hands detected: {len(detection_result.hand_landmarks)}", 
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(annotated_image, "Press Q or ESC to exit", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
        cv2.imshow("Hand Detection - Camara PC", annotated_image)
        
        # Log en consola cada 30 frames para monitoreo
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}: {gesture} - Hands: {len(detection_result.hand_landmarks)}")
            
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
=======
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np

# Configuración del modelo Hand Landmarker utilizando la nueva API de MediaPipe Tasks
# Requiere que el archivo 'hand_landmarker.task' esté en el mismo directorio
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
detector = vision.HandLandmarker.create_from_options(options)

# Mapa de conexiones manual para el esqueleto de la mano (21 landmarks en total)
# Define qué puntos se deben unir para representar pulgar, dedos y palma

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # Pulgar
    (0, 5), (5, 6), (6, 7), (7, 8),         # Índice
    (5, 9), (9, 10), (10, 11), (11, 12),    # Medio
    (9, 13), (13, 14), (14, 15), (15, 16),  # Anular
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Meñique y base
]

def draw_landmarks_on_image(image, detection_result):
    """Proyecta los puntos detectados y sus conexiones sobre el frame original"""
    annotated_image = np.copy(image)
    
    for hand_landmarks in detection_result.hand_landmarks:
        # Dibujo de las líneas (conexiones) del esqueleto
        for connection in HAND_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            if start_idx < len(hand_landmarks) and end_idx < len(hand_landmarks):
                start = hand_landmarks[start_idx]
                end = hand_landmarks[end_idx]
                
                # Conversión de coordenadas normalizadas (0.0 - 1.0) a píxeles de la imagen
                start_pos = (int(start.x * image.shape[1]), int(start.y * image.shape[0]))
                end_pos = (int(end.x * image.shape[1]), int(end.y * image.shape[0]))
                cv2.line(annotated_image, start_pos, end_pos, (0, 255, 0), 2)
        
        # Dibujo de los nodos (puntos clave) de la mano
        for landmark in hand_landmarks:
            x = int(landmark.x * image.shape[1])
            y = int(landmark.y * image.shape[0])
            cv2.circle(annotated_image, (x, y), 3, (255, 0, 0), -1)
            
    return annotated_image

def detect_hand_gesture(hand_landmarks):
    """Lógica heurística: compara la altura (eje Y) de las puntas contra la palma"""
    if not hand_landmarks:
        return "No hand detected"
    # Referencia de los puntos clave (Tips)
    landmarks = hand_landmarks[0]
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    middle_tip = landmarks[12]
    ring_tip = landmarks[16]
    pinky_tip = landmarks[20]
    palm = landmarks[0] # Base de la muñeca
    
    # Detección Thumbs Up: Pulgar arriba de la palma, índice abajo
    if thumb_tip.y < palm.y and index_tip.y > palm.y:
        return "Thumbs Up"
    # Detección Peace: Índice y medio arriba, anular y meñique abajo
    if (index_tip.y < palm.y and middle_tip.y < palm.y and 
        ring_tip.y > palm.y and pinky_tip.y > palm.y):
        return "Peace Sign"
    # Detección OK: Proximidad mínima entre punta de pulgar e índice
    if (abs(thumb_tip.x - index_tip.x) < 0.05 and 
        abs(thumb_tip.y - index_tip.y) < 0.05):
        return "OK Sign"
    # Detección Fist: Todas las puntas por debajo del nivel de la palma
    if (index_tip.y > palm.y and middle_tip.y > palm.y and 
        ring_tip.y > palm.y and pinky_tip.y > palm.y):
        return "Closed Fist"
    # Detección Open Hand: Todas las puntas por encima de la palma
    if (thumb_tip.y < palm.y and index_tip.y < palm.y and 
        middle_tip.y < palm.y and ring_tip.y < palm.y and pinky_tip.y < palm.y):
        return "Open Hand"
        
    return "Unknown Gesture"

try:
    print("Inicializando cámara...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: No se puede acceder a la cámara")
        exit()

    # Ajuste de resolución y tasa de refresco    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("=" * 50)
    print("Detección de Gestos de Mano - Cámara PC")
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
        # Ejecución de la inferencia del modelo
        detection_result = detector.detect(mp_image)
        
        # Generación de la imagen con la superposición gráfica
        annotated_image = draw_landmarks_on_image(frame, detection_result)
        
        gesture = "No hand detected"
        if detection_result.hand_landmarks:
            gesture = detect_hand_gesture(detection_result.hand_landmarks)
            
        # Visualización de etiquetas de texto en el frame
        cv2.putText(annotated_image, f"Gesture: {gesture}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(annotated_image, f"Hands detected: {len(detection_result.hand_landmarks)}", 
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(annotated_image, "Press Q or ESC to exit", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
        cv2.imshow("Hand Detection - Camara PC", annotated_image)
        
        # Log en consola cada 30 frames para monitoreo
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Frame {frame_count}: {gesture} - Hands: {len(detection_result.hand_landmarks)}")
            
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
>>>>>>> bd5b9b8bcdd753e4d51a89fff8d1e311fcdab9c0
    print("Programa finalizado")