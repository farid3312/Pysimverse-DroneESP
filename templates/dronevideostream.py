from pysimverse import Drone
import time
import cv2

# Inicialización de la interfaz del dron
drone = Drone()
drone.connect()
#agregar el time para que la transmision funcione bien
time.sleep(1)
# Habilita la recepción de paquetes de video vía UDP
drone.streamon()
drone.take_off()


#con el while tomara las fotos
#recordando que necesitmaos instalar opencv para esta parte.
# entonces en la terminal colocarle pip install opencv
#imshow para mostrar en la terminal
#se da un retardo 
while True:
    # Captura del frame actual (imagen) y el bit de estado (éxito/fallo)
    frame, is_success = drone.get_frame()
    # Renderizado de la matriz de píxeles en una ventana externa
    cv2.imshow("Drone feed", frame)
    # Delay de 1ms necesario para procesar los eventos de la interfaz de usuario de OpenCV
    cv2.waitKey(1)
