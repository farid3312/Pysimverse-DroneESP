from pysimverse import Drone
import cv2
import cvzone
from cvzone.ColorModule import ColorFinder
import time

# Inicialización de la interfaz del dron
drone = Drone()
drone.connect()
# Agregar delay para que la transmisión funcione bien
time.sleep(1)

# Habilita la recepción de paquetes de video vía UDP
drone.streamon()
drone.take_off(50)

# Instancia de la clase ColorFinder con trackBar activado
myColorFinder = ColorFinder(trackBar=False)

# Valores HSV para detectar el color naranja
hsvVals = {'hmin': 0, 'smin': 94, 'vmin': 112, 'hmax': 179, 'smax': 202, 'vmax': 235}

print("Iniciando detección de color en el feed del drone...")
print("Presiona 'q' o 'ESC' para salir")

# Bucle principal para procesamiento en tiempo real
while True:
    try:
        # Captura del frame actual del drone
        frame, is_success = drone.get_frame()
        
        if not is_success:
            print("No se pudo capturar frame del drone")
            continue

        # Detectar el color configurado
        imgColor, mask = myColorFinder.update(frame, hsvVals)

        # Apilar la imagen original, la máscara de color y la binaria
        imgStack = cvzone.stackImages([frame, imgColor, mask], 3, 0.5)
        
        # Mostrar el resultado apilado
        cv2.imshow("Deteccion de Color - Drone Feed", imgStack)

        # Romper el bucle si se presiona 'q' o 'ESC'
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            print("Saliendo de la misión...")
            break

    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        break

# Aterrizaje del drone
print("Aterrizando el drone...")
drone.land()
time.sleep(2)

# Liberar recursos al salir
drone.streamon_off()
drone.disconnect()
cv2.destroyAllWindows()
print("Misión finalizada")
