# Pysimverse-codigos

Aqui se encontraran algunos codigos de los diferentes escenarios que existen para el simulador de Pysimverse, contando con el apartado de las plantillas (templates) y con las misiones que van desde moverse por comandos, con el teclado, tomar capturas de pantalla, verificacion de gestos de las manos,movimiento por gestos de la mano y por ultimo mover el drone con saltos, ademas de esto se incluyen los requerimientos que contiene las librerias necesarias para hacer uso de los codigos(requiremets.txt), a parte de ello se debe descargar el modelo de mediapipe para el reconocimiento de gestos desde el siguiente link:
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task.
como el modelo de mediapipe para el reconocimiento de poses:
https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
para realizar este proyecto se baso en la ayuda del canal de youtobe freecodecamp.org en su video Learn Drone Programming with Python – Tutorial, del siguiente link:
https://www.youtube.com/watch?v=k-yDYgc8AmU&t=5305s

Además de estos apartados se essta probando de poco en poco una manera dinamica de enseñanza para aprender a pilotear un drone y la captura de imagenes de este con una esp32, Joysticks y una pantalla OLED, esto se hace con el fin de lograr trabajar mediante simulacion y la implementacion fisica de los drones.
especial mencion al github : https://github.com/nikhiltelase/mini-esp-now-rc-drone/tree/main el cuál diseña un control de drones con joysticks y una esp32, principal proyecto para hacer la conexion con pysimverse y el control del drone que luego se implementara de manera fisica en la construccion de un drone ESP.
