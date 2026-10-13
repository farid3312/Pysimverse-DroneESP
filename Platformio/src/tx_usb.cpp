// ============================================================================
// 1. LIBRERÍAS
// ============================================================================

#include <Arduino.h>
#include <math.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ============================================================================
// 2. DEFINICIONES Y CONSTANTES
// ============================================================================
// Configuración de la pantalla OLED (SSD1306 128x64 por I2C)
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

// Asignación de Pines
const int JOY1_X_PIN = 34; // Acelerador / Throttle (Stick izquierdo vertical)
const int JOY1_Y_PIN = 35; //  Guiñada / Yaw (Stick izquierdo horizontal)
const int JOY2_X_PIN = 33; // Eje X físico del joystick derecho
const int JOY2_Y_PIN = 32; // Eje Y físico del joystick derecho
const int SWITCH_PIN = 25;  // Interruptor/Pulsador auxiliar 1
const int SWITCH2_PIN = 26; // Interruptor/Pulsador auxiliar 2

// Rangos de Señal y Estándar de Radiocontrol (RC)
const int ANALOG_MIN = 0;       // Lectura mínima del ADC (12 bits: 0)
const int ANALOG_MAX = 4095;    // Lectura máxima del ADC (12 bits: 4095)
const int RC_MIN = 1000;        // Ancho de pulso RC mínimo (µs)
const int RC_MAX = 2000;        // Ancho de pulso RC máximo (µs)
const int RC_CENTER = 1500;     // Centro neutro de señal RC (µs)
const int RC_HALF_SPAN = 500;   // Desviación máxima desde el centro (1500 ± 500)

// Tiempos y Parámetros de Procesamiento
const uint32_t SEND_INTERVAL_MS = 20;   // Frecuencia de envío de datos (50 Hz / 20 ms)
const float FILTER_ALPHA = 0.15f;       // Factor de suavizado del filtro EMA (0.0 a 1.0)
const float DEADZONE_FRACTION = 0.05f;  // Zona muerta central (5%)
const int SWITCH_DEBOUNCE_MS = 120;     // Tiempo de anti-rebote para interruptores (ms)

// ============================================================================
// 3. ESTRUCTURAS Y CLASES
// ============================================================================

/**
 * Filtro de Promedio Móvil Exponencial (EMA) para suavizar la lectura analógica.
*/

class EmaFilter {
public:
  explicit EmaFilter(float alpha = FILTER_ALPHA)
      : alpha(alpha), initialized(false), value(0.0f) {}
   /**
   * Actualiza el filtro con una nueva lectura.
   * sample Valor analógico sin filtrar.
   * Valor filtrado acumulado.
   */
  float update(float sample) {
    if (!initialized) {
      value = sample;
      initialized = true;
    } else {
      value = alpha * sample + (1.0f - alpha) * value;
    }
    return value;
  }

private:
  float alpha;
  bool initialized;
  float value;
};
/**
 * Estructura para almacenar las lecturas de centro calibradas en el arranque.
*/

struct StickCenters {
  float yaw;
  float roll;
  float pitch;
};

// ============================================================================
// 4. INSTANCIAS Y VARIABLES GLOBALES
// ============================================================================
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
// Centros calibrados predeterminados al punto medio teórico
static StickCenters centers = {
  ANALOG_MIN + ((ANALOG_MAX - ANALOG_MIN) * 0.5f),
  ANALOG_MIN + ((ANALOG_MAX - ANALOG_MIN) * 0.5f),
  ANALOG_MIN + ((ANALOG_MAX - ANALOG_MIN) * 0.5f)
};
// ============================================================================
// 5. FUNCIONES AUXILIARES DE LECTURA Y PROCESAMIENTO
// ============================================================================

/**
 *  Obtiene el promedio de varias muestras para determinar el centro físico del stick.
*/
static float measureStickCenter(int pin, size_t samples = 32) {
  uint32_t total = 0;
  for (size_t i = 0; i < samples; ++i) {
    total += analogRead(pin);
    delay(2);
  }
  return constrain(
      static_cast<float>(total) / static_cast<float>(samples),
      static_cast<float>(ANALOG_MIN),
      static_cast<float>(ANALOG_MAX));
}
/**
 * Lee el ADC, limita el rango y aplica el filtro EMA.
*/
static float readFiltered(int pin, EmaFilter &filter) {
  int raw = constrain(analogRead(pin), ANALOG_MIN, ANALOG_MAX);
  return filter.update(static_cast<float>(raw));
}
/**
 *  Mapea un eje centrado (Yaw, Roll, Pitch) al rango RC (1000-2000 ms)
 *  considerando el centro real, invirtiendo el sentido si aplica y añadiendo zona muerta.
 */
static int mapCenteredAxis(float rawSample, float center, bool invert = false) {
  float offset = rawSample - center;
  float span = (offset >= 0.0f)
                   ? static_cast<float>(ANALOG_MAX) - center
                   : center - static_cast<float>(ANALOG_MIN);
  span = max(span, 1.0f);

  // Normalización entre -1.0 y +1.0
  float centered = constrain(offset / span, -1.0f, 1.0f);
  if (invert) {
    centered = -centered;
  }

  // Aplicación de la zona muerta central
  if (fabsf(centered) < DEADZONE_FRACTION) {
    centered = 0.0f;
  } else {
    float sign = centered < 0.0f ? -1.0f : 1.0f;
    float magnitude = (fabsf(centered) - DEADZONE_FRACTION) /
                      (1.0f - DEADZONE_FRACTION);
    centered = sign * constrain(magnitude, 0.0f, 1.0f);
  }

// Conversión final al rango de pulso RC (1000 a 2000 µs)
  return constrain(
      RC_CENTER + static_cast<int>(centered * RC_HALF_SPAN),
      RC_MIN,
      RC_MAX);
}

/**
 * Mapea la palanca de acelerador (Throttle) de 0-4095 a 1000-2000 ms.
 */
static int mapThrottleAxis(float rawSample) {
  float normalized = (rawSample - ANALOG_MIN) /
                     static_cast<float>(ANALOG_MAX - ANALOG_MIN);
  normalized = constrain(normalized, 0.0f, 1.0f);
  return constrain(
      RC_MIN + static_cast<int>(normalized * (RC_MAX - RC_MIN)),
      RC_MIN,
      RC_MAX);
}

/**
 * Lee el estado de los conmutadores digitales aplicando anti-rebote (debounce) y alternado (toggle).
 */
static int readSwitchChannel(int pin) {
  static int channelValues[2] = {RC_MIN, RC_MIN};
  static bool lastPressed[2] = {false, false};
  static uint32_t lastToggleMs[2] = {0, 0};
  static const int pins[2] = {SWITCH_PIN, SWITCH2_PIN};

  int index = pin == SWITCH2_PIN ? 1 : 0;
  bool pressed = digitalRead(pins[index]) == LOW;
  uint32_t now = millis();

  // Detección de flanco de bajada (transición no presionado -> presionado) con debounce
  if (pressed && !lastPressed[index] &&
      now - lastToggleMs[index] > static_cast<uint32_t>(SWITCH_DEBOUNCE_MS)) {
    channelValues[index] = channelValues[index] == RC_MIN ? RC_MAX : RC_MIN;
    lastToggleMs[index] = now;
  }

  lastPressed[index] = pressed;
  return channelValues[index];
}
// Dibuja en la pantalla OLED los valores actuales de los 6 canales del transmisor.

static void renderOled(const int channels[6]) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(F("USB RC Monitor"));
  display.setCursor(0, 12);
  display.print(F("R:"));
  display.print(channels[0]);
  display.print(F(" P:"));
  display.println(channels[1]);
  display.setCursor(0, 24);
  display.print(F("T:"));
  display.print(channels[2]);
  display.print(F(" Y:"));
  display.println(channels[3]);
  display.setCursor(0, 36);
  display.print(F("A1:"));
  display.print(channels[4]);
  display.print(F(" A2:"));
  display.println(channels[5]);
  display.display();
}

// ============================================================================
// 6. CONFIGURACIÓN INICIAL (SETUP)
// ============================================================================
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);   // Inicializa bus I2C (SDA = GPIO21, SCL = GPIO22)

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("OLED no encontrada"));
  }

  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(SWITCH2_PIN, INPUT_PULLUP);
  analogReadResolution(12); // Configura ADC a 12 bits (0-4095)

  // Muestreo inicial para registrar los centros físicos neutros
  centers.yaw = measureStickCenter(JOY1_Y_PIN);
  centers.roll = measureStickCenter(JOY2_Y_PIN);
  centers.pitch = measureStickCenter(JOY2_X_PIN);

  Serial.println(F("USB RC ready"));
}

// ============================================================================
// 7. BUCLE PRINCIPAL (LOOP)
// ============================================================================

void loop() {
  static uint32_t lastSendMs = 0;
  static uint32_t lastOledMs = 0;

  // Filtros estáticos para conservar el historial de cada eje entre ciclos
  static EmaFilter yawFilter;
  static EmaFilter throttleFilter;
  static EmaFilter rollFilter;
  static EmaFilter pitchFilter;

  uint32_t now = millis();
  // Mantiene la cadencia de procesamiento a 50 Hz (cada 20 ms)
  if (now - lastSendMs < SEND_INTERVAL_MS) {
    return;
  }
  lastSendMs = now;

  // 1. Muestreo filtrado de las entradas analógicas
  float yawSample = readFiltered(JOY1_Y_PIN, yawFilter);
  float throttleSample = readFiltered(JOY1_X_PIN, throttleFilter);
  float rollSample = readFiltered(JOY2_X_PIN, rollFilter);
  float pitchSample = readFiltered(JOY2_Y_PIN, pitchFilter);

  // 2. Procesamiento y mapeo a canales de radiocontrol
  int channels[6];
  channels[0] = mapCenteredAxis(pitchSample, centers.roll, false);
  channels[1] = mapCenteredAxis(rollSample, centers.pitch, true);
  channels[2] = mapThrottleAxis(throttleSample);
  channels[3] = mapCenteredAxis(yawSample, centers.yaw, false);
  channels[4] = readSwitchChannel(SWITCH_PIN);
  channels[5] = readSwitchChannel(SWITCH2_PIN);

  // 3. Envío de la trama de canales por el puerto serie
  Serial.print(F("RC:"));
  for (uint8_t i = 0; i < 6; ++i) {
    Serial.print(' ');
    Serial.print(channels[i]);
  }
  Serial.println();
  // 4. Refresco de pantalla OLED cada 100 ms (10 Hz)
  if (now - lastOledMs >= 100) {
    renderOled(channels);
    lastOledMs = now;
  }
}
