<<<<<<< HEAD
from pysimverse import Drone
import time

# Inicialización y despegue inmediato
drone = Drone()
drone.connect()
drone.take_off()

# Configuración de canales RC (Rango típico -100 a 100)
left_right = 0        # Roll
forward_backward = 50 # Pitch (Avance constante)
up_down = 0           # Throttle
yaw = 0               # Yaw

# Bucle infinito de transmisión de datos
#solo avanzará hacia adelante.
while True:
    # Envío continuo de la señal de control
    drone.send_rc_control(left_right, forward_backward, up_down, yaw)
    
    # Delay mínimo para estabilidad del hilo y evitar saturación de CPU
    time.sleep(0.05)
=======
from pysimverse import Drone
import time

# Inicialización y despegue inmediato
drone = Drone()
drone.connect()
drone.take_off()

# Configuración de canales RC (Rango típico -100 a 100)
left_right = 0        # Roll
forward_backward = 50 # Pitch (Avance constante)
up_down = 0           # Throttle
yaw = 0               # Yaw

# Bucle infinito de transmisión de datos
#solo avanzará hacia adelante.
while True:
    # Envío continuo de la señal de control
    drone.send_rc_control(left_right, forward_backward, up_down, yaw)
    
    # Delay mínimo para estabilidad del hilo y evitar saturación de CPU
    time.sleep(0.05)
>>>>>>> bd5b9b8bcdd753e4d51a89fff8d1e311fcdab9c0
