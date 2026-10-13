<<<<<<< HEAD
from pysimverse import Drone
import time

drone = Drone()
drone.connect()
drone.take_off()

drone.set_speed(200)
drone.move_forward(320)
drone.move_left(220)

drone.move_right(470)
drone.move_down(80)
drone.move_backward(140)

drone.land()
=======
from pysimverse import Drone
import time

drone = Drone()
drone.connect()
drone.take_off()

drone.set_speed(200)
drone.move_forward(320)
drone.move_left(220)

drone.move_right(470)
drone.move_down(80)
drone.move_backward(140)

drone.land()
>>>>>>> bd5b9b8bcdd753e4d51a89fff8d1e311fcdab9c0
time.sleep(1)