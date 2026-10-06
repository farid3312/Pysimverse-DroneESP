from __future__ import annotations  # Permite usar anotaciones con tipos modernos de Python y evita problemas con versiones más antiguas.
import re                           # Importa el módulo re para trabajar con expresiones regulares y reconocer el formato de los datos del mando.
import time                         # Importa time para medir tiempos y hacer pausas entre ciclos del bucle de control.
import serial                       # Importa la librería PySerial para leer datos desde el puerto serie conectado a la ESP32.
from pysimverse import Drone        # Importa la clase Drone del simulador pysimverse para controlar el dron virtual.


SERIAL_PORT = "COM3"                # Define el puerto COM donde está conectada la ESP32 o el receptor RC.
BAUD_RATE = 115200                  # Define la velocidad de transmisión serial para comunicarse correctamente con el dispositivo.
CONTROL_INTERVAL = 0.01             # Revisa el mando cada 10 milisegundos para reducir la latencia de respuesta.
COMMAND_INTERVAL = 0.02             # Envía comandos al simulador cada 20 milisegundos, igual que la ESP32, evitando saturarlo.
SERIAL_TIMEOUT = 0.01               # Evita que una lectura del puerto serie bloquee el control durante mucho tiempo.
FAILSAFE_TIMEOUT = 0.50             # Si pasan 500 ms sin recibir paquetes válidos, se activa un modo de seguridad y se apaga el control.
THROTTLE_ARM_THRESHOLD = 1100       # El throttle debe estar muy bajo para permitir armar. Si está alto, el dron no se activa.
ARM_CHANNEL_INDEX = 4               # El canal 5 del ESP32 funciona como botón de armado/encendido del dron.
ARM_ACTIVE_VALUE = 1500             # El valor mínimo para considerar que el botón de armado está pulsado.
YAW_RESPONSE = 0.10                 # Reduce la velocidad máxima de giro para que el yaw responda de forma más suave.


RC_LINE_PATTERN = re.compile(
    r"^RC:\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)"
)
# Crea una expresión regular para detectar líneas del tipo: RC: 1234 5678 900 1200 1000 2000.
# Cada grupo captura un canal del mando RC: roll, pitch, throttle, yaw, arm-button y aux.

_serial_buffer = bytearray()
# Conserva una línea incompleta entre lecturas sin bloquear esperando a que termine.


def rc_to_simulator(value: int) -> int:
    """Convert a 1000..2000 RC channel to pysimverse's -100..100 range."""
    # Convierte un valor del canal RC de 1000 a 2000 en un valor comprendido entre -100 y 100 para pysimverse.

    value = max(1000, min(2000, value))
    # Ajusta el valor para que nunca salga del rango permitido por el receptor RC.

    return int((value - 1500) * 100 / 500)
    # Calcula la posición del stick alrededor del centro (1500), con un rango de ±100.
    # Ejemplo: 1500 -> 0, 2000 -> 100, 1000 -> -100.


def read_rc_channels(serial_port: serial.Serial) -> list[int] | None:
    # Lee una línea del puerto serie y devuelve los 6 canales RC si la línea tiene el formato esperado.
    # En este proyecto, los canales son: roll, pitch, throttle, yaw, arm-switch, aux.
    
    bytes_waiting = serial_port.in_waiting                       # Consulta cuántos bytes ya llegaron sin bloquear el hilo de control.
    if bytes_waiting == 0:
        # Si todavía no llegó información, el bucle puede continuar inmediatamente.
        return None

    _serial_buffer.extend(serial_port.read(bytes_waiting))      # Lee de una vez todos los bytes disponibles para evitar acumular paquetes antiguos
    lines = _serial_buffer.split(b"\n")                         # Separa los paquetes completos usando el salto de línea enviado por la ESP32.
    _serial_buffer.clear()
    _serial_buffer.extend(lines.pop())                          # Conserva únicamente la última línea incompleta para terminarla en la siguiente lectura.
    latest_values = None                                        # Guarda el último paquete válido del bloque leído; los anteriores ya están atrasados.
    
    for raw_line in lines:
        # Recorre todos los paquetes completos recibidos desde la última iteración.

        line = raw_line.decode("ascii", errors="ignore").strip() # Convierte cada paquete a texto y elimina espacios o retornos de carro.
        match = RC_LINE_PATTERN.match(line)
        # Comprueba si el paquete tiene los seis canales esperados.

        if match is not None:
            # Solo se conserva un paquete que tenga el formato RC correcto.
            latest_values = [int(value) for value in match.groups()]
            # Convierte los canales del paquete válido a números enteros.

    return latest_values
    # Devuelve el estado más reciente y descarta estados viejos para minimizar la latencia.


def main() -> None:
    # Función principal del programa, donde se inicializa la conexión y se controla el dron.

    serial_port = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=SERIAL_TIMEOUT,
    )
    # Abre el puerto serie con la velocidad y el timeout especificados.

    drone = Drone()                                 # Crea una instancia del dron del simulador.
    drone.connect()                                 # Conecta el programa con el simulador del dron.
    last_packet_time = time.monotonic()             # Guarda el instante en que se recibió el último paquete válido del mando RC
    is_armed = False                                # Indica si el dron ya fue armado de forma segura.
    last_command_time = 0.0                         # Guarda cuándo se envió el último comando para limitar la frecuencia hacia pysimverse

    try:
        # Inicia un bloque protegido con try para manejar Ctrl+C (cancelar el vuelo y conexion con pysimverse) y limpieza final.

        print(f"Esperando datos del control en {SERIAL_PORT}...")
        # Muestra un mensaje en consola indicando en qué puerto está escuchando.

        print("Throttle bajo + botón de armado para activar el dron.")
        # Explica la secuencia de arranque segura tipo Betaflight.

        while True:
            # Bucle infinito que mantiene el control del dron activo hasta que se interrumpa.

            channels = read_rc_channels(serial_port)
            # Llama a la función que intenta leer los canales del mando RC.

            if channels is not None:
                # Si se recibió una línea válida con datos del RC, se procesa.

                roll = rc_to_simulator(channels[0])                     # Convierte el canal roll del mando en un valor para el simulador.
                pitch = -rc_to_simulator(channels[1])                   # Invierte el pitch para que subir la palanca avance y bajarla retroceda.
                throttle = rc_to_simulator(channels[2])                 # Convierte el canal throttle del mando en un valor para el simulador.
                yaw = int(rc_to_simulator(channels[3]) * YAW_RESPONSE)  # Reduce la respuesta del giro sin cambiar la sensibilidad de los demás canales.
                arm_button = channels[ARM_CHANNEL_INDEX]                # El canal 5 del ESP32 se usa como botón de armado. Si supera el umbral, se activa el arranque.
                throttle_low = channels[2] <= THROTTLE_ARM_THRESHOLD    # El throttle debe estar bajo para poder armar; si está alto, el dron no puede iniciar.
                
                if not is_armed:
                    # Mientras no esté armado, no se permiten movimientos de vuelo ni despegue.

                    if throttle_low and arm_button >= ARM_ACTIVE_VALUE:
                        # Condición segura de armado: throttle bajo + botón pulsado.
                        is_armed = True
                        drone.take_off(1)
                        # Activa el vuelo solo después de confirmar throttle bajo y botón de armado.
                        print("Drone armado. Ahora puedes subir el throttle gradualmente.")
                        drone.send_rc_control(0, 0, 0, 0)
                        # Pone el dron en estado neutral al armar para evitar movimientos accidentales.

                    else:
                        # Si no se cumplen las condiciones, se mantiene inmóvil y bloqueado.
                        drone.send_rc_control(0, 0, 0, 0)
                        last_packet_time = time.monotonic()
                        time.sleep(CONTROL_INTERVAL)
                        continue

                if is_armed and arm_button < ARM_ACTIVE_VALUE:
                    # Si el botón vuelve a la posición apagada, se desarma y aterriza el dron.
                    drone.send_rc_control(0, 0, 0, 0)
                    drone.land()
                    is_armed = False
                    last_packet_time = time.monotonic()
                    time.sleep(CONTROL_INTERVAL)
                    continue

                # Si el dron ya está armado, entonces se acepta el comando normal.
                # El throttle solo se puede subir gradualmente con el resto de canales activos, como en Betaflight.
                now = time.monotonic()
                # Obtiene el tiempo actual para controlar la frecuencia de envío al simulador.

                if now - last_command_time >= COMMAND_INTERVAL:
                    # Envía como máximo 50 comandos por segundo para evitar saturar pysimverse.
                    drone.send_rc_control(roll, pitch, throttle, yaw)
                    # Envía al dron la combinación más reciente de valores RC.
                    last_command_time = now
                    # Guarda el instante de este envío.

                last_packet_time = time.monotonic()
                # Actualiza la hora del último paquete válido para el sistema de seguridad.

            elif time.monotonic() - last_packet_time > FAILSAFE_TIMEOUT:
                # Si no hay paquetes válidos y se supera el tiempo de seguridad, se para el dron.

                drone.send_rc_control(0, 0, 0, 0)                       # Envía todos los canales en 0 para evitar que el dron siga moviéndose.
                is_armed = False                                        # Se desarma automáticamente si se pierde el enlace.
                

            time.sleep(CONTROL_INTERVAL)                                # Espera 50 ms antes de repetir el ciclo de lectura y control.
            
    except KeyboardInterrupt:                                           # Si el usuario presiona Ctrl+C, entra aquí y ejecuta una secuencia de aterrizaje.
        print("\nAterrizando...")                                       # Muestra un mensaje de que el dron va a aterrizar.
        

    finally:
        # Este bloque siempre se ejecuta, tanto si hubo Ctrl+C como si hubo otro error.

        drone.send_rc_control(0, 0, 0, 0)                              # Pone todos los canales del mando a cero antes de aterrizar.
        drone.land()                                                   # Ordena al dron que aterrice.
        serial_port.close()                                            # Cierra el puerto serie para liberar el recurso.
        time.sleep(2)                                                  # Espera 2 segundos para permitir que el aterrizaje termine correctamente.
        print("Control finalizado.")                                   # Muestra un mensaje final de que el programa terminó.
        
if __name__ == "__main__":                                             # Verifica que este archivo se esté ejecutando como programa principal y no importado como módulo.
    main()                                                             # Llama a la función principal para arrancar el control del dron.
    
