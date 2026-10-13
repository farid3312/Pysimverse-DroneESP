from pysimverse import Drone
import cv2
import cvzone
from cvzone.ColorModule import ColorFinder
import numpy as np
import time

# =====================================================
# PARÁMETROS DE CONFIGURACIÓN DEL SEGUIDOR DE LÍNEA
# =====================================================

# Parámetros PID para control de rotación (YAW) - OPTIMIZADOS
KP_YAW = 0.035     # Ganancia proporcional - respuesta suave pero efectiva
KI_YAW = 0.001     # Ganancia integral - muy pequeña
KD_YAW = 0.020     # Ganancia derivativa - suavizante

# Velocidad máxima de rotación en grados/segundo
MAX_YAW_SPEED = 20

# Velocidad hacia adelante (muy lenta para mejor seguimiento)
FORWARD_SPEED = 10

# Zona muerta: ignorar rotaciones si el error es menor que esto (en píxeles)
DEADZONE = 20

# Área mínima de contorno para considerar que es una línea válida
MIN_AREA = 500

# Factor de suavizado para filtro de media móvil (0.0 a 1.0)
# Valores más bajos = más suavizado
SMOOTHING_FACTOR = 0.3

# Tiempo máximo sin detectar la línea (en segundos) antes de terminar
MAX_TIME_WITHOUT_LINE = 3

# =====================================================
# CLASE DE CONTROLADOR PID
# =====================================================

class PIDController:
    """
    Controlador PID simple para seguimiento suave.
    """
    def __init__(self, kp, ki, kd, max_output, deadzone=0, smoothing=0.3):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output
        self.deadzone = deadzone
        self.smoothing = smoothing
        
        self.prev_error = 0
        self.integral = 0
        self.prev_output = 0
        self.last_time = time.time()
    
    def update(self, error):
        """
        Calcula la salida PID basada en el error.
        
        Args:
            error: Error actual (diferencia desde el centro)
        
        Returns:
            output: Valor de control limitado a max_output
        """
        # Aplicar zona muerta
        if abs(error) < self.deadzone:
            error = 0
        
        # Calcular tiempo transcurrido
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Evitar división por cero
        if dt == 0:
            dt = 0.001
        if dt > 0.1:  # Evitar picos si hay retraso
            dt = 0.05
        
        # Término proporcional
        p_term = self.kp * error
        
        # Término integral (acumulación de errores)
        self.integral += error * dt
        # Limitar integral para evitar windup
        self.integral = np.clip(self.integral, -50, 50)
        i_term = self.ki * self.integral
        
        # Término derivativo (tasa de cambio del error)
        d_term = self.kd * (error - self.prev_error) / dt
        
        # Salida total
        output = p_term + i_term + d_term
        
        # Limitar salida
        output = np.clip(output, -self.max_output, self.max_output)
        
        # Aplicar suavizado con filtro de media móvil
        output = (self.smoothing * output) + ((1 - self.smoothing) * self.prev_output)
        
        # Guardar valores para próxima iteración
        self.prev_error = error
        self.prev_output = output
        
        return output
    
    def reset(self):
        """Reinicia el controlador PID."""
        self.prev_error = 0
        self.integral = 0
        self.prev_output = 0
        self.last_time = time.time()

# =====================================================
# FUNCIONES DE PROCESAMIENTO
# =====================================================

def detectar_linea(mask):
    """
    Detecta la línea en la máscara y retorna su centroide.
    
    Args:
        mask: Imagen binaria (máscara) de la línea detectada
    
    Returns:
        centroid_x: Coordenada X del centroide (-1 si no se detecta)
        area: Área del contorno detectado
    """
    # Encontrar contornos en la máscara
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        return -1, 0
    
    # Encontrar el contorno con mayor área
    largest_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_contour)
    
    # Verificar si el área es suficientemente grande
    if area < MIN_AREA:
        return -1, area
    
    # Calcular el momento del contorno
    M = cv2.moments(largest_contour)
    
    if M["m00"] == 0:
        return -1, area
    
    # Calcular el centroide
    centroid_x = int(M["m10"] / M["m00"])
    
    return centroid_x, area


def dibujar_info(frame, centroid_x, error, yaw_speed, area, forward_speed):
    """
    Dibuja información de depuración en el frame.
    """
    height, width = frame.shape[:2]
    center_x = width // 2
    
    # Dibujar línea vertical central (referencia)
    cv2.line(frame, (center_x, 0), (center_x, height), (0, 255, 0), 2)
    
    # Dibujar centroide detectado
    if centroid_x != -1:
        cv2.line(frame, (centroid_x, 0), (centroid_x, height), (0, 0, 255), 2)
        cv2.circle(frame, (centroid_x, height // 2), 10, (255, 0, 0), -1)
    
    # Añadir texto con información
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_color = (0, 255, 0)
    
    if centroid_x != -1:
        cv2.putText(frame, f"Error: {error} px", (10, 30), font, 0.7, text_color, 2)
        cv2.putText(frame, f"Yaw Speed: {yaw_speed:.1f} deg/s", (10, 60), font, 0.7, text_color, 2)
        cv2.putText(frame, f"Forward: {forward_speed}", (10, 90), font, 0.7, text_color, 2)
        cv2.putText(frame, f"Area: {area}", (10, 120), font, 0.7, text_color, 2)
    else:
        cv2.putText(frame, "LINEA NO DETECTADA", (10, 30), font, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, "Buscando linea...", (10, 60), font, 0.7, (0, 0, 255), 2)
    
    return frame


# =====================================================
# INICIALIZACIÓN DEL DRON
# =====================================================

drone = Drone()
drone.connect()
time.sleep(1)

drone.streamon()
drone.take_off(30)

# Instancia del detector de color
myColorFinder = ColorFinder(trackBar=False)

# Valores HSV para detectar la línea ROJA
hsvVals = {'hmin': 0, 'smin': 95, 'vmin': 0, 'hmax': 179, 'smax': 255, 'vmax': 255}

# Crear controlador PID para la rotación con zona muerta y suavizado
pid_yaw = PIDController(KP_YAW, KI_YAW, KD_YAW, MAX_YAW_SPEED, DEADZONE, SMOOTHING_FACTOR)

# Descomenta la siguiente línea si quieres ajustar los valores en tiempo real
# hsvVals = {'hmin': 0, 'smin': 95, 'vmin': 0, 'hmax': 179, 'smax': 255, 'vmax': 255}

print("=" * 60)
print("SEGUIDOR DE LÍNEA CON CONTROL PID - DRON")
print("=" * 60)
print(f"KP: {KP_YAW}, KI: {KI_YAW}, KD: {KD_YAW}")
print(f"Velocidad máxima de rotación: {MAX_YAW_SPEED} deg/s")
print(f"Velocidad hacia adelante: {FORWARD_SPEED}")
print(f"Zona muerta (deadzone): {DEADZONE} píxeles")
print(f"Factor de suavizado: {SMOOTHING_FACTOR}")
print(f"Área mínima de línea: {MIN_AREA} píxeles")
print("Presiona 'q' o 'ESC' para salir")
print("=" * 60)

# =====================================================
# BUCLE PRINCIPAL
# =====================================================

time_last_line_detected = time.time()  # Rastrear tiempo sin detección de línea

while True:
    try:
        # Captura del frame actual del drone
        frame, is_success = drone.get_frame()
        
        if not is_success:
            print("No se pudo capturar frame del drone")
            continue
        
        height, width = frame.shape[:2]
        
        # Detectar el color de la línea
        imgColor, mask = myColorFinder.update(frame, hsvVals)
        
        # Detectar la línea en la máscara
        centroid_x, area = detectar_linea(mask)
        
        # Variables por defecto
        yaw_speed = 0
        error = 0
        forward_speed = 0
        
        # Si se detecta la línea, calcular velocidad de rotación con PID
        if centroid_x != -1:
            # Actualizar tiempo de última detección
            time_last_line_detected = time.time()
            
            # Centro de la imagen
            center_x = width // 2
            
            # Error (distancia desde el centro)
            error = centroid_x - center_x
            
            # Calcular velocidad de rotación usando PID
            yaw_speed = pid_yaw.update(error)
            
            # Controlar velocidad de avance según el error
            # Si el error es grande, reducir velocidad de avance
            error_magnitude = abs(error)
            if error_magnitude < 50:  # Muy centrado
                forward_speed = FORWARD_SPEED
            elif error_magnitude < 100:  # Un poco descentrado
                forward_speed = max(FORWARD_SPEED // 2, 5)
            else:  # Muy descentrado, ralentizar
                forward_speed = max(FORWARD_SPEED // 3, 3)
            
            # Enviar comando de movimiento al dron usando RC control
            # send_rc_control(left_right, forward_backward, up_down, yaw)
            drone.send_rc_control(0, int(forward_speed), 0, int(yaw_speed))
        else:
            # Verificar si ha pasado demasiado tiempo sin detectar la línea
            time_elapsed = time.time() - time_last_line_detected
            
            if time_elapsed > MAX_TIME_WITHOUT_LINE:
                print(f"\n⚠️  LÍNEA PERDIDA POR {time_elapsed:.1f}s - TERMINANDO MISIÓN")
                drone.send_rc_control(0, 0, 0, 0)
                break
            
            # Si no se detecta línea, detener movimiento pero seguir intentando
            drone.send_rc_control(0, 0, 0, 0)
            pid_yaw.reset()  # Reiniciar PID cuando se pierda la línea
            forward_speed = 0
        
        # Dibujar información de depuración
        time_since_detection = time.time() - time_last_line_detected
        frame_debug = dibujar_info(frame.copy(), centroid_x, error, yaw_speed, area, forward_speed)
        
        # Mostrar tiempo sin detectar línea si es relevante
        if centroid_x == -1 and time_since_detection > 0.5:
            cv2.putText(frame_debug, f"Buscando linea: {time_since_detection:.1f}s", 
                       (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            if time_since_detection > MAX_TIME_WITHOUT_LINE - 1:
                cv2.putText(frame_debug, f"ADVERTENCIA: Terminando en {MAX_TIME_WITHOUT_LINE - time_since_detection:.1f}s", 
                           (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Apilar la imagen original, máscara de color y la procesada
        imgStack = cvzone.stackImages([frame_debug, imgColor, mask], 3, 0.5)
        
        # Mostrar el resultado
        cv2.imshow("Seguidor de Linea - Drone Feed", imgStack)
        
        # Romper el bucle si se presiona 'q' o 'ESC'
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            print("\nSaliendo de la misión...")
            break

    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        break

# =====================================================
# FINALIZACIÓN
# =====================================================

print("Deteniendo movimiento del dron...")
drone.send_rc_control(0, 0, 0, 0)
time.sleep(0.5)

print("Aterrizando el drone...")
drone.land()
time.sleep(2)

# Liberar recursos
drone.streamon_off()
drone.disconnect()
cv2.destroyAllWindows()
print("Misión finalizada")
