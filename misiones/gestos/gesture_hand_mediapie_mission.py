import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import cv2
import numpy as np
import time
import threading
import math

from pysimverse import Drone

# ==========================================
# MEDIAPIPE
# ==========================================
# Se carga el modelo pre-entrenado. 'num_hands=1' optimiza el rendimiento al buscar solo una mano.
base_options = python.BaseOptions(model_asset_path='models/hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

# Definición manual del esqueleto para dibujar las líneas de la mano
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
    (13,17),(0,17),(17,18),(18,19),(19,20)
]

def draw_landmarks(image, detection_result):
    #Renderiza puntos (landmarks) y conexiones sobre el frame de video.
    out = np.copy(image)
    for hand_landmarks in detection_result.hand_landmarks:
        # Dibujo de líneas de conexión entre puntos clave
        for s, e in HAND_CONNECTIONS:
            if s < len(hand_landmarks) and e < len(hand_landmarks):
                # Conversión de coordenadas normalizadas (0-1) a píxeles reales de la imagen
                p1 = (int(hand_landmarks[s].x * image.shape[1]), int(hand_landmarks[s].y * image.shape[0]))
                p2 = (int(hand_landmarks[e].x * image.shape[1]), int(hand_landmarks[e].y * image.shape[0]))
                cv2.line(out, p1, p2, (0, 255, 0), 2)
        # Dibujo de los 21 puntos individuales
        for lm in hand_landmarks:
            cv2.circle(out, (int(lm.x * image.shape[1]), int(lm.y * image.shape[0])), 3, (255, 0, 0), -1)
    return out

#Lógica de clasificación de gestos basada en la anatomía de la mano. Utiliza distancias relativas a la muñeca para determinar si un dedo está extendido.
def detect_gesture(hand_landmarks):
    import math
    if not hand_landmarks:
        return "No hand"

    lm = hand_landmarks[0]
    wrist = lm[0]       # Punto 0: Muñeca
    pinky_base = lm[17] # Usamos el otro extremo de la mano para medir el pulgar

    def get_dist(p1, p2):
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    # REGLA INFALIBLE: Un dedo está "abierto" si su punta está más lejos de la muñeca
    # que su propia articulación media (PIP). Si está más cerca, está doblado.
    
    # Índices de articulaciones medias (PIP): 6, 10, 14, 18
    # Índices de puntas (TIP): 8, 12, 16, 20
    index_open  = get_dist(lm[8], wrist)  > get_dist(lm[6], wrist)
    middle_open = get_dist(lm[12], wrist) > get_dist(lm[10], wrist)
    ring_open   = get_dist(lm[16], wrist) > get_dist(lm[14], wrist)
    pinky_open  = get_dist(lm[20], wrist) > get_dist(lm[18], wrist)

    # REGLA DEL PULGAR: Si la punta (4) está más lejos del meñique (17) 
    # que su propia articulación (3), entonces está estirado hacia afuera.
    thumb_open = get_dist(lm[4], pinky_base) > get_dist(lm[3], pinky_base)

    # Agrupamos los estados
    four_fingers_closed = not (index_open or middle_open or ring_open or pinky_open)
    four_fingers_open   = index_open and middle_open and ring_open and pinky_open
    
    # Distancia para el OK
    dist_thumb_index = get_dist(lm[4], lm[8])

    # ── 1. Closed Fist (Puño cerrado: todo doblado) ───────────────────────
    if four_fingers_closed and not thumb_open:
        return "Closed Fist"

    # ── 2. Thumbs Up (Solo el pulgar abierto) ──────────────────────────────
    if four_fingers_closed and thumb_open:
        return "Thumbs Up"

    # ── 3. Peace Sign (V de victoria) ──────────────────────────────────────
    if index_open and middle_open and not ring_open and not pinky_open:
        return "Peace Sign"

    # ── 4. OK Sign (Puntas de índice y pulgar pegadas) ─────────────────────
    if dist_thumb_index < 0.06 and middle_open and ring_open and pinky_open:
        return "OK Sign"

    # ── 5. Open Hand (Todos los dedos estirados) ───────────────────────────
    if thumb_open and four_fingers_open:
        return "Open Hand"

    return "Unknown"
# ==========================================
# FASE 1 — CALIBRACIÓN (drone apagado)
# ==========================================
#Asegura que el usuario sepa hacer los gestos antes de encender el drone.
def calibracion(cap):
    gestures = ["Open Hand", "Closed Fist", "Peace Sign", "Thumbs Up", "OK Sign"]
    descriptions = {
        "Open Hand":   "MANO ABIERTA   -> Mover DERECHA",
        "Closed Fist": "PUNO CERRADO   -> Quieto",
        "Peace Sign":  "VICTORIA (V)   -> Mover IZQUIERDA",
        "Thumbs Up":   "PULGAR ARRIBA  -> (referencia)",
        "OK Sign":     "OK (circulo)   -> Aterrizar",
    }
    REQUIRED = 15 # Frames consecutivos necesarios para validar un gesto

    idx = 0
    frames_held = 0

    print("\n" + "="*55)
    print("  CALIBRACIÓN: muestra cada gesto hasta confirmar")
    print("  'S' = saltar gesto  |  'Q' = salir")
    print("="*55)

    while idx < len(gestures):
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 480))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_img)
        annotated = draw_landmarks(frame, result)

        gesture = detect_gesture(result.hand_landmarks)
        target  = gestures[idx]
        color   = (0, 255, 0) if gesture == target else (0, 0, 255)

        # Contador de progreso para el gesto actual
        if gesture == target:
            frames_held += 1
        else:
            frames_held = max(0, frames_held - 1)
        # Si se alcanza el umbral, se confirma el gesto y se pasa al siguiente
        if frames_held >= REQUIRED:
            cv2.rectangle(annotated, (0, 0), (640, 480), (0, 255, 0), 12)
            cv2.putText(annotated, "OK!", (260, 260),
                        cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 6)
            cv2.imshow("Calibracion", annotated)
            cv2.waitKey(700)
            print(f"  [{idx+1}/{len(gestures)}] {target} — CONFIRMADO")
            idx += 1
            frames_held = 0
            continue

        total = len(gestures)
        # Dibujo de interfaz de usuario (HUD) de calibración
        cv2.putText(annotated, f"[{idx+1}/{total}] Muestra:",
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(annotated, descriptions[target],
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
        cv2.putText(annotated, f"Detectado: {gesture}",
                    (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

        bar_w = int((frames_held / REQUIRED) * 300)
        cv2.rectangle(annotated, (10, 130), (310, 155), (80, 80, 80), -1)
        cv2.rectangle(annotated, (10, 130), (10 + bar_w, 155), color, -1)
        cv2.rectangle(annotated, (10, 130), (310, 155), (255, 255, 255), 2)
        cv2.putText(annotated, f"{int(frames_held / REQUIRED * 100)}%",
                    (320, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        cv2.putText(annotated, "'S' saltar  |  'Q' salir",
                    (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 1)

        cv2.imshow("Calibracion", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            print(f"  [{idx+1}/{total}] {target} — saltado")
            idx += 1
            frames_held = 0
        elif key in (ord('q'), 27):
            return False

    cv2.destroyWindow("Calibracion")
    print("\nCalibración completa. Conectando drone...\n")
    return True


# ==========================================
# ESTADO COMPARTIDO
# ==========================================
# Lock para evitar colisiones de datos entre el hilo de cámara y el de control del drone
gesture_lock = threading.Lock()
shared     = {"left_right": 0, "land": False, "gesture": "Closed Fist"}
stop_event = threading.Event()

SPEED             = 50
OK_CONFIRM_FRAMES = 20   # frames consecutivos para confirmar aterrizaje


# ==========================================
# HILO CÁMARA
# ==========================================
def camera_thread(cap):
    last_valid = "Closed Fist"
    timeout    = 0
    ok_counter = 0

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            stop_event.set()
            break

        frame    = cv2.resize(frame, (640, 480))
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = detector.detect(mp_img)
        annotated = draw_landmarks(frame, result)

        gesture = detect_gesture(result.hand_landmarks)

        # Contador dedicado para OK Sign
        if gesture == "OK Sign":
            ok_counter += 1
        else:
            ok_counter = 0

        if gesture not in ("No hand", "Unknown"):
            last_valid = gesture
            timeout    = 20
        else:
            timeout = max(0, timeout - 1)
            if timeout == 0:
                last_valid = "Closed Fist"

        # Traducción de Gestos -> Comandos RC
        lr   = 0
        land = False

        if last_valid == "Open Hand":
            lr = SPEED           # derecha
        elif last_valid == "Peace Sign":
            lr = -SPEED          # izquierda
        elif last_valid == "Closed Fist":
            lr = 0               # quieto
        
        if ok_counter >= OK_CONFIRM_FRAMES:
            land = True          # aterrizar solo tras 20 frames seguidos

        with gesture_lock:
            shared["left_right"] = lr
            shared["land"]       = land
            shared["gesture"]    = last_valid

        if land:
            stop_event.set()

        # Dibujo de HUD de control en tiempo real
        g_color   = (0, 255, 0) if lr > 0 else (255, 100, 0) if lr < 0 else (200, 200, 200)
        direction = ">>> DERECHA >>>" if lr > 0 else "<<< IZQUIERDA <<<" if lr < 0 else "[ QUIETO ]"
        ok_pct    = int(min(ok_counter / OK_CONFIRM_FRAMES, 1.0) * 100)

        cv2.putText(annotated, "PRUEBA: IZQUIERDA / DERECHA",
                    (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(annotated, f"Gesto: {last_valid}",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, g_color, 2)
        cv2.putText(annotated, direction,
                    (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.85, g_color, 2)
        cv2.putText(annotated, f"L/R enviado: {lr}",
                    (10, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 1)

        if ok_counter > 0:
            cv2.putText(annotated, f"OK confirm: {ok_pct}%  (manten para aterrizar)",
                        (10, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 1)

        cv2.putText(annotated,
                    "Open Hand=Derecha | Peace=Izquierda | OK (manten)=Aterrizar",
                    (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (150, 150, 150), 1)

        cv2.imshow("Control Drone", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            stop_event.set()

    cap.release()
    cv2.destroyAllWindows()


# ==========================================
# HILO DRONE — envío fijo cada 50 ms
# ==========================================
def drone_thread(drone):
    print("Hilo de control activo (50 ms)")
    while not stop_event.is_set():
        with gesture_lock:
            lr = shared["left_right"]
        drone.send_rc_control(lr, 0, 0, 0)
        time.sleep(0.05)

    # Freno antes de aterrizar
    drone.send_rc_control(0, 0, 0, 0)
    time.sleep(0.1)


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: no se puede abrir la cámara.")
        exit()

    # FASE 1: calibración (drone apagado)
    if not calibracion(cap):
        cap.release()
        cv2.destroyAllWindows()
        print("Abortado en calibración.")
        exit()

    # FASE 2: arrancar drone
    print("Conectando drone...")
    drone = Drone()
    drone.connect()
    print("Despegando — espera 3 s...")
    #drone.take_off()
    time.sleep(3)

    # Paso 3: Lanzamiento de hilos paralelos (Daemon=True para cierre automático)
    t_cam   = threading.Thread(target=camera_thread, args=(cap,),   daemon=True)
    t_drone = threading.Thread(target=drone_thread,  args=(drone,), daemon=True)

    t_cam.start()
    t_drone.start()

    # Espera a que los hilos terminen (cuando se presiona ESC o se detecta OK)
    t_cam.join()
    t_drone.join()

    print("Aterrizando...")
    try:
        drone.land()
    except Exception:
        pass
    time.sleep(2)
    print("Finalizado.")