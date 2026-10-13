<<<<<<< HEAD
from pysimverse import Drone
import time

drone = Drone()
drone.connect()
drone.take_off()

drone.rotate(45)
time.sleep(1)
drone.set_speed(150)
drone.move_forward(370)

drone.land()
=======
from pysimverse import Drone
import time

drone = Drone()
drone.connect()
drone.take_off()

drone.rotate(45)
time.sleep(1)
drone.set_speed(150)
drone.move_forward(370)

drone.land()
>>>>>>> bd5b9b8bcdd753e4d51a89fff8d1e311fcdab9c0
time.sleep(3)