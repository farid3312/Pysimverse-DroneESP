import cv2
import cvzone
from cvzone.ColorModule import ColorFinder

# Instancia de la clase ColorFinder con trackBar activado
myColorFinder = ColorFinder(trackBar=False)

# Inicializar la captura de video (ajusta el índice si no lee tu cámara)
cap = cv2.VideoCapture(0)

# Configurar las dimensiones de la cámara a 640x480
cap.set(3, 640)
cap.set(4, 480)

# Valores HSV para detectar el color azul claro
hsvVals = {'hmin': 89, 'smin': 50, 'vmin': 108, 'hmax': 147, 'smax': 157, 'vmax': 155}

# Bucle principal para procesamiento en tiempo real
while True:
    success, img = cap.read()
    if not success:
        print("No se pudo acceder a la cámara.")
        break

    # Detectar el color configurado
    imgOrange, mask = myColorFinder.update(img, hsvVals)

    # Apilar la imagen original, la máscara de color y la binaria
    imgStack = cvzone.stackImages([img, imgOrange, mask], 3, 0.5)
  # Mostrar el resultado apilado
    cv2.imshow("Image Stack", imgStack)

    # Romper el bucle si se presiona la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar recursos al salir
cap.release()
cv2.destroyAllWindows()