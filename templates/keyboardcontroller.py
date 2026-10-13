from pysimverse import Drone
import time
from pynput import keyboard

# Inicializar el drone
drone = Drone()
drone.connect()
drone.take_off()

# Variables de control de movimiento (Ejes: Roll, Pitch, Throttle, Yaw)
# Se inicializan en 0 para asegurar que el drone esté estable al inicio
left_right = 0          # Roll: Movimiento lateral
forward_backward = 0    # Pitch: Movimiento adelante/atrás
up_down = 0             # Throttle: Altitud
yaw = 0                 # Yaw: Rotación sobre el eje vertical

# Estructura de datos 'set' para gestionar múltiples teclas presionadas simultáneamente
# Esto permite movimientos diagonales (ej. presionar 'W' y 'D' al mismo tiempo)
keys_pressed = set()

# Velocidad de incremento
SPEED_INCREMENT = 50
ROTATION_SPEED =  4 # Velocidad más baja para rotación
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
    
    # Presionar ESC para aterrizar y salir
    try:
        if key == keyboard.Key.esc:
            return False  # Detener el listener
    except AttributeError:
        pass

def update_speeds():
    """Actualizar velocidades basadas en teclas presionadas"""
    global left_right, forward_backward, up_down, yaw
    
    # Reset temporal de velocidades para evitar que el drone mantenga inercia sin teclas
    left_right = 0
    forward_backward = 0
    up_down = 0
    yaw = 0
    
    # Movimiento adelante/atrás (W/S) (Pitch)
    if 'w' in keys_pressed:
        forward_backward = SPEED_INCREMENT
    elif 's' in keys_pressed:
        forward_backward = -SPEED_INCREMENT
    
    # Movimiento izquierda/derecha (A/D)(desplazamiento lateral)
    if 'a' in keys_pressed:
        left_right = -SPEED_INCREMENT
    elif 'd' in keys_pressed:
        left_right = SPEED_INCREMENT
    
    # Movimiento arriba/abajo (Flecha Arriba/Abajo)(cambio de altitud)
    if keyboard.Key.up in keys_pressed:
        up_down = SPEED_INCREMENT
    elif keyboard.Key.down in keys_pressed:
        up_down = -SPEED_INCREMENT
    
    # Rotación (Q/E) (rotacion horizontal)
    if 'q' in keys_pressed:
        yaw = -ROTATION_SPEED
    elif 'e' in keys_pressed:
        yaw = ROTATION_SPEED

# Configuración del listener de teclado como un hilo independiente (No bloqueante)
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

try:
    print("Control de Drone por Teclado")
    print("W/S - Adelante/Atrás")
    print("A/D - Izquierda/Derecha")
    print("Flecha Arriba/Abajo - Subir/Bajar")
    print("Q/E - Girar Izquierda/Derecha")
    print("ESC - Aterrizar y salir")
    print("-" * 40)
    
    while True:
        update_speeds()
        # Envío de comandos al simulador
        drone.send_rc_control(left_right, forward_backward, up_down, yaw)
        time.sleep(0.05)  # 50ms entre actualizaciones
        
        if keyboard.Key.esc in keys_pressed:
            print("Aterrizando...")
            break
            
except KeyboardInterrupt:
    print("Interrupción por teclado")
finally:
    # Bloque de seguridad: garantiza que el drone aterrice y se detenga el listener
    drone.land()
    time.sleep(2)
    listener.stop()
    print("Drone aterrizó correctamente")


