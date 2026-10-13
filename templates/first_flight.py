from  pysimverse import Drone
import time

drone = Drone()
drone.connect()

#  funcion para activar el despegue (1m o 1.5m)
drone.take_off()

### movimientos :

#funcion para descender el drone, en este caso a 30cm del suelo
drone.move_down(20)
time.sleep(2)
#ahora que suba a 30cm
drone.move_up(30)
time.sleep(2)
# ahora para moverse a la izquierda y a la derecha
drone.move_left(30)
time.sleep(2)
#derecha
drone.move_right(30)
time.sleep(2)
#hacia adelante
drone.move_forward(20)
time.sleep(2)
#hacia atrás
drone.move_backward(30)
time.sleep(2)
#funcion para rotar el drone
drone.rotate(30)
time.sleep(2)
#para cambiarle la velocidad cm/s (defecto en 20)
drone.set_speed(50)
drone.move_forward(100)

# funcion para aterrizar controlado el drone
drone.land()
time.sleep(2)
