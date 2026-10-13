<<<<<<< HEAD
from pysimverse import Drone
import time

drone = Drone()
drone.connect()
drone.take_off()

drone.set_speed(150)
drone.move_forward(70)
drone.move_left(220)

drone.move_forward(150)
drone.move_right(220)

drone.move_forward(100)
drone.move_right(270)

drone.land()
time.sleep(1)
=======
from pysimverse import Drone
import time

drone = Drone()
drone.connect()
drone.take_off()

drone.set_speed(150)
drone.move_forward(70)
drone.move_left(220)

drone.move_forward(150)
drone.move_right(220)

drone.move_forward(100)
drone.move_right(270)

drone.land()
time.sleep(1)
>>>>>>> bd5b9b8bcdd753e4d51a89fff8d1e311fcdab9c0
