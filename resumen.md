# Resumen del repositorio Pysimverse-DroneESP

## 1. Descripción general

Este repositorio es un proyecto educativo y experimental para controlar un dron en simulación con Pysimverse, usando visión por computadora y, en algunos casos, interacción física con un mando RC basado en ESP32. La idea central es aprender a pilotar un drone desde Python, usar cámaras para detectar objetos, líneas y gestos, y luego conectar estas ideas con un controlador real o semi-real basado en hardware.

El proyecto combina varios elementos:

- Simulación de vuelo con `pysimverse`
- Procesamiento de video con `OpenCV` y `cvzone`
- Detección y seguimiento con `MediaPipe`
- Control manual por teclado o RC
- Mando con ESP32 + joysticks + pantalla OLED
- Misiones y ejercicios para practicar vuelo y visión artificial

El repositorio tiene un enfoque didáctico: muchos archivos son ejemplos o misiones pequeñas que muestran cómo mover el drone, detectar figuras o reaccionar a gestos para pilotar en el simulador.

---

## 2. Estructura principal del proyecto

### 2.1 `README.md`

Es la documentación central del proyecto. Explica que el repositorio reúne varios escenarios de simulación para Pysimverse, incluyendo:

- plantillas base para aprender
- misiones en simulación
- control por comandos y teclado
- detección de gestos con la mano
- movimiento por gestos del cuerpo
- captura de imagenes
- control del drone con saltos
- requerimientos de librerías
- modelos de MediaPipe descargables

También menciona la inspiración del proyecto en un tutorial de FreeCodeCamp y en otros repositorios relacionados con drones RC, especialmente en torno a ESP32 y control con joysticks.

### 2.2 `requirements.txt`

Define las dependencias necesarias para ejecutar los scripts del proyecto. Incluye librerías clave como:

- `numpy`
- `matplotlib`
- `pandas`
- `opencv-python`
- `pysimverse`
- `pynput`
- `pyserial`
- `mediapipe`
- `cvzone`
- `pyautogui`

Esto confirma que el repositorio está orientado a visión artificial, control de drones, serial y automatización de input.

### 2.3 `templates/`

Carpeta con ejemplos reutilizables y básicos para entrenar/entender la API del dron. Aquí se encuentran scripts que sirven como base para empezar a programar con Pysimverse.

Ejemplos importantes:

- `first_flight.py`: ejemplo básico de despegue, movimientos, giro y aterrizaje.
- `keyboardcontroller.py`: control del dron con teclado usando `pynput`.
- `esp32_controller.py`: enlace entre un mando ESP32 y el simulador, leyendo canales RC por puerto serial.
- `dronevideostream.py`: captura y visualización del flujo de video del drone.
- `body_mediapipe.py`: ejemplo para reconocer poses corporales con MediaPipe.
- `drone_gesture_hand_mediapie.py`: ejemplo de control usando gestos de mano.
- `deteccion_de_saltos.py`: detector de saltos basado en pose/cadera.
- `colordeteccion.py`: detección de color en la imagen del dron.
- `rc_controller.py`: ejemplo de control remoto.

Estos scripts parecen funcionar como “bloques de construcción” que luego se reutilizan en misiones más complejas.

### 2.4 `misiones/`

Es la parte más relevante del repositorio: aquí se encuentran las misiones y escenarios prácticos. Está dividida por temáticas:

- `body/`
- `camara/`
- `control/`
- `garage/`
- `gestos/`

#### `misiones/body/`

Contiene misiones centradas en analiza de pose y movimiento corporal.

- `mision1_body.py`: usa `MediaPipe` con el modelo `pose_landmarker_lite.task` para detectar una persona y analizar la posición de las caderas. Tiene un detector de saltos basado en la velocidad vertical de la cadera y calcula si el usuario está en el aire o en tierra.
- El script dibuja el esqueleto del cuerpo, mide la velocidad del movimiento vertical y cuenta saltos.
- Se usa para integrar visión por pose con control del dron:
  - detectar salto
  - contar saltos
  - ajustar estado del drone
  - mostrar instrucciones visuales en pantalla

Es una misión muy orientada a interacción humano-drone usando el cuerpo como comando.

#### `misiones/camara/`

Contiene misiones relacionadas con captura y análisis de video.

- `mision2capturadeimagen.py`
- `mission2imagecapturecontrol.py`

Estas misiones probablemente capturan frames del drone y los muestran en ventanas OpenCV, con lógica para observar/capturar imágenes y usar la cámara del simulador como entrada de control o analítica.

#### `misiones/control/`

Aquí hay dos scripts muy importantes:

- `droneseguidordelinea.py`: un seguimiento de línea con PID. El drone:
  - captura un frame del simulador
  - detecta una línea en un color específico usando `cvzone.ColorFinder`
  - encuentra el centroide de la línea
  - calcula el error respecto al centro de la imagen
  - usa un controlador PID para corregir la rotación del drone
  - avanza hacia adelante si la línea está detectada
  - se detiene o evita perder la línea si no se detecta por más de cierto tiempo

Este es un ejemplo clásico de visión para navegación autónoma en un entorno que puede ser un camino o pista de color.

- `deteccionColorDrone.py`: otro script de visión, pero más simple. Detecta un color concreto del feed del dron, lo muestra como máscara y permite identificar el objeto o línea en la cámara del simulador.

La carpeta de control muestra claramente la combinación de:

- OpenCV para procesamiento visual
- control proporcional/integral/derivativo (PID)
- automatización compleja de navegación

#### `misiones/garage/`

Estas misiones son más de navegación/escenario tipo “garage” o movimiento básico.

- `mission1.py`
- `mission2garage.py`
- `mission3garage.py`

Estos scripts son ejemplos de recorrido del dron en un escenario: despegue, desplazamiento en distintas direcciones, giro y aterrizaje. Su objetivo es aprender a programar trayectorias simples en el simulador mediante comandos del API de `pysimverse`.

#### `misiones/gestos/`

Contiene la lógica más visual y avanzada del proyecto.

- `gesture_hand_mediapie_mission.py`: usa `MediaPipe HandLandmarker` para detectar la mano y clasificar gestos, por ejemplo:
  - `Open Hand`
  - `Closed Fist`
  - `Peace Sign`
  - `Thumbs Up`
  - `OK Sign`

A partir de esos gestos, el programa:

- calibra la detección del usuario
- enseña qué gesto corresponde a qué acción
- analiza la mano en tiempo real
- conecta cada gesto con un comando de control del drone
- puede iniciar/despegar, moverse, aterrizar o mantenerse en estado inmóvil

Esto convierte la mano del usuario en un interfaz natural para controlar el dron, algo muy apropiado en un proyecto de aprendizaje y prototipado.

---

## 3. Modelos de IA y visión

El proyecto incluye modelos descargables de MediaPipe en la carpeta `models/`:

- `hand_landmarker.task`
- `pose_landmarker_lite.task`

Estos archivos se usan para reconocer:

- gestos de la mano
- postura del cuerpo
- movimiento del torso y de las caderas
- detección de esqueletos para contar saltos o medir postura

Esto convierte el proyecto en una mezcla de visión computacional y automatización con drones.

---

## 4. Hardware ESP32 y mando RC

La carpeta `Platformio/` contiene firmware para un mando RC físico con joystick y pantalla OLED.

### `Platformio/platformio.ini`

Es la configuración del proyecto PlatformIO para compilar firmware para microcontrolador.

### `Platformio/src/tx_usb.cpp`

Este archivo es el corazón del diseño del mando. Implementa una aplicación con:

- dos joysticks analógicos
- lectura de ADC de 12 bits
- calibración de centros de sticks
- filtro EMA para suavizar datos
- mapeo de señales a un rango RC (1000 a 2000 µs)
- manejo de interruptores y anti-rebote
- salida serial para enviar los valores de los canales del transmisor
- pantalla OLED para mostrar los canales y estado de señales

Esto se usa para crear un mando RC con joysticks y visualizar los valores en tiempo real, y luego conectarlo con el software Python a través de `pyserial`.

La idea del proyecto es que el mando físico pueda controlar el drone virtual en Pysimverse, acercándolo a una experiencia realista de vuelo.

---

## 5. ¿Qué hace este repositorio en términos prácticos?

El proyecto permite hacer varias cosas:

1. Despegar, moverse, girar, subir, bajar y aterrizar un drone en simulación.
2. Controlarlo con comandos de teclado o con un mando real por serial.
3. Capturar y analizar frames de video del drone.
4. Detectar líneas de colores para hacer seguimiento de ruta.
5. Detectar gestos de mano para controlar movimiento.
6. Detectar pose humana para identificar saltos o comandos corporales.
7. Conectar un mando ESP32 con el simulador para simular una experiencia de vuelo realista.

En otras palabras, este repositorio es una colección de ejercicios de robótica, visión por computadora y control para drones.

---

## 6. Flujo típico de funcionamiento

Un flujo típico en el proyecto es:

1. crear o conectar el dron con `pysimverse`
2. activar `streamon()` para recibir video
3. capturar el frame actual
4. procesar la imagen con OpenCV o MediaPipe
5. detectar línea, gesto, pose o color
6. mapear esa detección a un comando del dron
7. enviar el comando por `send_rc_control()` o movimiento directo
8. repetir el ciclo en tiempo real
9. aterrizar o finalizar la misión

Esto es muy típico de sistemas de control reactivo con visión artificial.

---

## 7. Tecnologías involucradas

El repositorio usa una combinación bastante completa de tecnologías:

- `Python`: lógica principal del proyecto
- `Pysimverse`: simulador del drone
- `OpenCV`: lectura, visualización y procesamiento de imágenes
- `MediaPipe`: detección de pose y manos
- `NumPy`: análisis y cálculos numéricos
- `cvzone`: procesamiento visual más sencillo con máscaras y color detection
- `pyserial`: comunicación con dispositivos ESP32
- `pynput`: lectura de teclado
- `PlatformIO`: firmware para hardware ESP32
- `Arduino/C++`: firmware del mando RC en la carpeta `Platformio`

---

## 8. Objetivo del proyecto

El objetivo general parece ser didáctico e investigativo: aprender a pilotar un drone desde Python, integrar percepción visual y control de vuelo, y preparar una evolución hacia un dron físico basado en ESP32, joysticks y control RC real.

La documentación del README menciona explícitamente que además del simulador se está probando una forma dinámica de enseñanza para aprender a pilotear un dron y capturar imágenes con una ESP32, joysticks y pantalla OLED. La meta final es combinar simulación y implementación física en un drone ESP.

---

## 9. Conclusión

Este repositorio no es un único programa, sino un conjunto de prácticas y prototipos para trabajar con drones simulados y su control mediante visión artificial. Su valor principal está en la combinación de:

- simulación de vuelo
- programación en Python
- análisis visual con OpenCV y MediaPipe
- control emocional/automático del drone
- integración con hardware de mando RC

Es un proyecto muy bien alineado con un enfoque de aprendizaje práctico, prototipado y experimentación aplicada a robótica y drones.
