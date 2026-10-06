from __future__ import annotations
import os
import re
import time
import cv2
import serial
import pyautogui
from pysimverse import Drone

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================
SERIAL_PORT = "COM3"
BAUD_RATE = 115200
CONTROL_INTERVAL = 0.01      # Intervalo de revisión del mando (10 ms)
COMMAND_INTERVAL = 0.02      # Intervalo de envío al simulador (20 ms / 50 Hz)
SERIAL_TIMEOUT = 0.01
FAILSAFE_TIMEOUT = 0.50

THROTTLE_ARM_THRESHOLD = 1100
ARM_CHANNEL_INDEX = 4        # Canal Aux 1 (Interruptor izquierdo: Armado)
PHOTO_CHANNEL_INDEX = 5      # Canal Aux 2 (Interruptor derecho: Captura/Tecla Z)
ARM_ACTIVE_VALUE = 1500
PHOTO_ACTIVE_VALUE = 1500
YAW_RESPONSE = 0.05

RC_LINE_PATTERN = re.compile(
    r"^RC:\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)"
)

_serial_buffer = bytearray()


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================
def rc_to_simulator(value: int) -> int:
    """Convierte un canal RC de 1000..2000 al rango -100..100 de pysimverse."""
    value = max(1000, min(2000, value))
    return int((value - 1500) * 100 / 500)


def read_rc_channels(serial_port: serial.Serial) -> list[int] | None:
    """Lee y parsea la última línea válida enviada por la ESP32 por puerto serie."""
    bytes_waiting = serial_port.in_waiting
    if bytes_waiting == 0:
        return None

    _serial_buffer.extend(serial_port.read(bytes_waiting))
    lines = _serial_buffer.split(b"\n")
    _serial_buffer.clear()
    _serial_buffer.extend(lines.pop())

    latest_values = None
    for raw_line in lines:
        line = raw_line.decode("ascii", errors="ignore").strip()
        match = RC_LINE_PATTERN.match(line)
        if match is not None:
            latest_values = [int(val) for val in match.groups()]

    return latest_values


# ============================================================================
# PROGRAMA PRINCIPAL
# ============================================================================
def main() -> None:
    # Gestión de archivos: Creación de la carpeta local para capturas
    capture_dir = "capturas_drone"
    if not os.path.exists(capture_dir):
        os.makedirs(capture_dir)
        print(f"Directorio '{capture_dir}' creado")

    serial_port = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=SERIAL_TIMEOUT,
    )

    drone = Drone()
    drone.connect()
    
    # Inicialización del streaming de video
    time.sleep(1)
    drone.streamon()

    last_packet_time = time.monotonic()
    is_armed = False
    last_command_time = 0.0
    last_photo_button_state = False  # Detección de flanco
    photo_text_timer = 0.0           # Temporizador para mostrar el mensaje en pantalla

    try:
        print(f"Esperando datos del control en {SERIAL_PORT}...")
        print("Throttle bajo + botón de armado para activar el dron.")
        print("Usa el switch derecho para accionar 'Z' y tomar fotos durante el vuelo.")

        while True:
            # 1. ACTUALIZACIÓN DEL STREAM DE VIDEO Y OVERLAY HUD
            frame, is_success = drone.get_frame()
            if is_success and frame is not None:
                display_frame = frame.copy()
                
                # Muestra el texto en pantalla durante 1.5 segundos tras tomar una foto
                if time.monotonic() - photo_text_timer < 1.5:
                    cv2.putText(
                        display_frame,
                        "FOTO TOMADA (TECLA Z)",
                        (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 255, 0),  # Verde BGR
                        3,
                        cv2.LINE_AA,
                    )

                cv2.imshow("Drone Feed", display_frame)
                cv2.waitKey(1)

            # 2. LECTURA Y PROCESAMIENTO DEL CONTROL
            channels = read_rc_channels(serial_port)

            if channels is not None:
                roll = rc_to_simulator(channels[0])
                pitch = -rc_to_simulator(channels[1])
                throttle = rc_to_simulator(channels[2])
                yaw = int(rc_to_simulator(channels[3]) * YAW_RESPONSE)
                
                arm_button = channels[ARM_CHANNEL_INDEX]
                photo_button = channels[PHOTO_CHANNEL_INDEX]
                throttle_low = channels[2] <= THROTTLE_ARM_THRESHOLD

                # LÓGICA DE SIMULACIÓN DE TECLA 'Z' Y TOMA DE FOTO (SIN ATERRIZAR)
                photo_button_active = photo_button >= PHOTO_ACTIVE_VALUE
                if photo_button_active and not last_photo_button_state:
                    print("[MISIÓN] Pulsador AUX activado: Enviando tecla 'Z'...")

                    # 1. Emular la pulsación de la tecla 'z'
                    pyautogui.press('z')

                    # 2. Guardar captura en la carpeta "capturas_drone"
                    if is_success and frame is not None:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"foto_mision_{timestamp}.png"
                        filepath = os.path.join(capture_dir, filename)
                        cv2.imwrite(filepath, frame)
                        print(f"[CÁMARA] Foto guardada localmente en: {filepath}")

                    # 3. Activar temporizador de notificación visual
                    photo_text_timer = time.monotonic()

                last_photo_button_state = photo_button_active

                # Lógica de Armado
                if not is_armed:
                    if throttle_low and arm_button >= ARM_ACTIVE_VALUE:
                        is_armed = True
                        drone.take_off(1)
                        print("Drone armado. Control de vuelo activo.")
                        drone.send_rc_control(0, 0, 0, 0)
                    else:
                        drone.send_rc_control(0, 0, 0, 0)
                        last_packet_time = time.monotonic()
                        time.sleep(CONTROL_INTERVAL)
                        continue

                # Lógica de Desarmado manual
                if is_armed and arm_button < ARM_ACTIVE_VALUE:
                    drone.send_rc_control(0, 0, 0, 0)
                    drone.land()
                    is_armed = False
                    last_packet_time = time.monotonic()
                    time.sleep(CONTROL_INTERVAL)
                    continue

                # Envío de mandos de vuelo continuos
                now = time.monotonic()
                if now - last_command_time >= COMMAND_INTERVAL:
                    drone.send_rc_control(roll, pitch, throttle, yaw)
                    last_command_time = now

                last_packet_time = time.monotonic()

            elif time.monotonic() - last_packet_time > FAILSAFE_TIMEOUT:
                # Sistema Failsafe
                drone.send_rc_control(0, 0, 0, 0)
                is_armed = False

            time.sleep(CONTROL_INTERVAL)

    except KeyboardInterrupt:
        print("\nAterrizando por interrupción...")

    finally:
        drone.send_rc_control(0, 0, 0, 0)
        drone.land()
        serial_port.close()
        cv2.destroyAllWindows()
        time.sleep(2)
        print("Control finalizado.")


if __name__ == "__main__":
    main()
