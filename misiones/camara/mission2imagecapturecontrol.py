from pysimverse import Drone
import time
import cv2
from pynput import keyboard
import os
from datetime import datetime

# Gestión de archivos: Creación de la carpeta local para almacenamiento de telemetría visual 
capture_dir = "capturas_drone"
if not os.path.exists(capture_dir):
    os.makedirs(capture_dir)
    print(f"Directorio '{capture_dir}' creado")

# Inicializar el drone
drone = Drone()
drone.connect()
time.sleep(1)   # Estabilización de la conexión
drone.streamon() # Activación del buffer de video UDP
drone.take_off()

# Variables de control de velocidad
left_right = 0
forward_backward = 0
up_down = 0
yaw = 0

# Estructura para gestión de concurrencia de eventos de teclado
keys_pressed = set()

# Parámetros de sensibilidad y límites de velocidad
SPEED_INCREMENT = 50
ROTATION_SPEED = 5  # Velocidad más baja para rotación
MAX_SPEED = 100

def on_press(key):
    """Capturar teclas presionadas"""
    try:
        keys_pressed.add(key.char)
    except AttributeError:
        # Para teclas especiales (flechas, etc)
        keys_pressed.add(key)

def on_release(key):
    """Capturar teclas liberadas"""
    try:
        keys_pressed.discard(key.char)
    except AttributeError:
        keys_pressed.discard(key)

def update_speeds():
    """Actualizar velocidades basadas en teclas presionadas"""
    global left_right, forward_backward, up_down, yaw
    
    # Resetear velocidades
    left_right = 0
    forward_backward = 0
    up_down = 0
    yaw = 0
    
    # Movimiento adelante/atrás (W/S)
    if 'w' in keys_pressed:
        forward_backward = SPEED_INCREMENT
    elif 's' in keys_pressed:
        forward_backward = -SPEED_INCREMENT
    
    # Movimiento izquierda/derecha (A/D)
    if 'a' in keys_pressed:
        left_right = -SPEED_INCREMENT
    elif 'd' in keys_pressed:
        left_right = SPEED_INCREMENT
    
    # Movimiento arriba/abajo (Flecha Arriba/Abajo)
    if keyboard.Key.up in keys_pressed:
        up_down = SPEED_INCREMENT
    elif keyboard.Key.down in keys_pressed:
        up_down = -SPEED_INCREMENT
    
    # Rotación (Q/E)
    if 'q' in keys_pressed:
        yaw = -ROTATION_SPEED
    elif 'e' in keys_pressed:
        yaw = ROTATION_SPEED

def capture_screenshot(frame):
    """Serialización de la matriz de imagen a formato JPG con marca de tiempo precisa"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = os.path.join(capture_dir, f"captura_{timestamp}.jpg")
    cv2.imwrite(filename, frame)
    print(f"Captura guardada: {filename}")
    return filename

# Ejecución del hilo secundario para el monitoreo del teclado sin bloquear el ciclo principa
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

try:
    print("=" * 50)
    print("Control de Drone con Transmisión de Video")
    print("=" * 50)
    # Bloque de instrucciones de control en consola
    print("W/S - Adelante/Atrás")
    print("A/D - Izquierda/Derecha")
    print("Flecha Arriba/Abajo - Subir/Bajar")
    print("Q/E - Girar Izquierda/Derecha")
    print("Z - Capturar imagen")
    print("ESC - Aterrizar y salir")
    print("=" * 50)
    
    running = True
    while running:
        # Recuperación del último frame disponible en el stream
        frame, is_success = drone.get_frame()
        
        if is_success:
            # Actualizar velocidades según teclas presionadas
            update_speeds()
            
            # Enviar comandos de control al drone
            drone.send_rc_control(left_right, forward_backward, up_down, yaw)
            
            # Mostrar información en el frame
            info_text = f"Vel: L/R={left_right} F/B={forward_backward} U/D={up_down} YAW={yaw}"
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Mostrar el frame
            cv2.imshow("Transmisión de Drone", frame)
            
            # Capturar imagen si se presiona Z
            if 'z' in keys_pressed:
                capture_screenshot(frame)
                keys_pressed.discard('z')  # Evitar capturas múltiples por una pulsación
                time.sleep(0.3)  # Pequeño retardo para evitar múltiples capturas
            
            # Presionar ESC para salir
            if keyboard.Key.esc in keys_pressed:
                print("Aterrizando...")
                running = False
        
        # Retardo para mantener control fluido
        time.sleep(0.05)
        
        # Salida con tecla ESC del teclado (alternativa) - Presiona ESC en la ventana de OpenCV
        if cv2.waitKey(1) & 0xFF == 27:  # ESC en OpenCV
            print("Aterrizando...")
            running = False
            
except KeyboardInterrupt:
    print("Interrupción por teclado")
finally:
    # Protocolo de seguridad: Cierre de hilos y aterrizaje forzoso
    print("Cerrando sesión...")
    listener.stop()  # Detener el listener de teclado primero
    time.sleep(0.1)
    drone.land()
    time.sleep(2)
    drone.streamoff()
    cv2.destroyAllWindows()  # Cerrar todas las ventanas de OpenCV
    print("Drone aterrizó correctamente")
    print(f"Capturas guardadas en: {os.path.abspath(capture_dir)}")

from pysimverse import Drone
import time
import cv2
from pynput import keyboard
import os
from datetime import datetime

# Gestión de archivos: Creación de la carpeta local para almacenamiento de telemetría visual 
capture_dir = "capturas_drone"
if not os.path.exists(capture_dir):
    os.makedirs(capture_dir)
    print(f"Directorio '{capture_dir}' creado")

# Inicializar el drone
drone = Drone()
drone.connect()
time.sleep(1)   # Estabilización de la conexión
drone.streamon() # Activación del buffer de video UDP
drone.take_off()

# Variables de control de velocidad
left_right = 0
forward_backward = 0
up_down = 0
yaw = 0

# Estructura para gestión de concurrencia de eventos de teclado
keys_pressed = set()

# Parámetros de sensibilidad y límites de velocidad
SPEED_INCREMENT = 50
ROTATION_SPEED = 5  # Velocidad más baja para rotación
MAX_SPEED = 100

def on_press(key):
    """Capturar teclas presionadas"""
    try:
        keys_pressed.add(key.char)
    except AttributeError:
        # Para teclas especiales (flechas, etc)
        keys_pressed.add(key)

def on_release(key):
    """Capturar teclas liberadas"""
    try:
        keys_pressed.discard(key.char)
    except AttributeError:
        keys_pressed.discard(key)

def update_speeds():
    """Actualizar velocidades basadas en teclas presionadas"""
    global left_right, forward_backward, up_down, yaw
    
    # Resetear velocidades
    left_right = 0
    forward_backward = 0
    up_down = 0
    yaw = 0
    
    # Movimiento adelante/atrás (W/S)
    if 'w' in keys_pressed:
        forward_backward = SPEED_INCREMENT
    elif 's' in keys_pressed:
        forward_backward = -SPEED_INCREMENT
    
    # Movimiento izquierda/derecha (A/D)
    if 'a' in keys_pressed:
        left_right = -SPEED_INCREMENT
    elif 'd' in keys_pressed:
        left_right = SPEED_INCREMENT
    
    # Movimiento arriba/abajo (Flecha Arriba/Abajo)
    if keyboard.Key.up in keys_pressed:
        up_down = SPEED_INCREMENT
    elif keyboard.Key.down in keys_pressed:
        up_down = -SPEED_INCREMENT
    
    # Rotación (Q/E)
    if 'q' in keys_pressed:
        yaw = -ROTATION_SPEED
    elif 'e' in keys_pressed:
        yaw = ROTATION_SPEED

def capture_screenshot(frame):
    """Serialización de la matriz de imagen a formato JPG con marca de tiempo precisa"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = os.path.join(capture_dir, f"captura_{timestamp}.jpg")
    cv2.imwrite(filename, frame)
    print(f"Captura guardada: {filename}")
    return filename

# Ejecución del hilo secundario para el monitoreo del teclado sin bloquear el ciclo principa
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

try:
    print("=" * 50)
    print("Control de Drone con Transmisión de Video")
    print("=" * 50)
    # Bloque de instrucciones de control en consola
    print("W/S - Adelante/Atrás")
    print("A/D - Izquierda/Derecha")
    print("Flecha Arriba/Abajo - Subir/Bajar")
    print("Q/E - Girar Izquierda/Derecha")
    print("Z - Capturar imagen")
    print("ESC - Aterrizar y salir")
    print("=" * 50)
    
    running = True
    while running:
        # Recuperación del último frame disponible en el stream
        frame, is_success = drone.get_frame()
        
        if is_success:
            # Actualizar velocidades según teclas presionadas
            update_speeds()
            
            # Enviar comandos de control al drone
            drone.send_rc_control(left_right, forward_backward, up_down, yaw)
            
            # Mostrar información en el frame
            info_text = f"Vel: L/R={left_right} F/B={forward_backward} U/D={up_down} YAW={yaw}"
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Mostrar el frame
            cv2.imshow("Transmisión de Drone", frame)
            
            # Capturar imagen si se presiona Z
            if 'z' in keys_pressed:
                capture_screenshot(frame)
                keys_pressed.discard('z')  # Evitar capturas múltiples por una pulsación
                time.sleep(0.3)  # Pequeño retardo para evitar múltiples capturas
            
            # Presionar ESC para salir
            if keyboard.Key.esc in keys_pressed:
                print("Aterrizando...")
                running = False
        
        # Retardo para mantener control fluido
        time.sleep(0.05)
        
        # Salida con tecla ESC del teclado (alternativa) - Presiona ESC en la ventana de OpenCV
        if cv2.waitKey(1) & 0xFF == 27:  # ESC en OpenCV
            print("Aterrizando...")
            running = False
            
except KeyboardInterrupt:
    print("Interrupción por teclado")
finally:
    # Protocolo de seguridad: Cierre de hilos y aterrizaje forzoso
    print("Cerrando sesión...")
    listener.stop()  # Detener el listener de teclado primero
    time.sleep(0.1)
    drone.land()
    time.sleep(2)
    drone.streamoff()
    cv2.destroyAllWindows()  # Cerrar todas las ventanas de OpenCV
    print("Drone aterrizó correctamente")
    print(f"Capturas guardadas en: {os.path.abspath(capture_dir)}")
