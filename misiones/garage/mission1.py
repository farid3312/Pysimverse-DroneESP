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
time.sleep(3)