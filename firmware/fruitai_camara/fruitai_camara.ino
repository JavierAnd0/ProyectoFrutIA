// FruitAI — firmware principal del ESP32-S3 con cámara.
//
//   cámara OV2640 → modelo TinyML (Edge Impulse) → confirmación anti-duplicados
//   → botón ENTRADA / SALIDA → MQTT fruitai/movimiento → servicio (Pi) → SQLite → HA
//
// Es el mismo ciclo que simulador/esp32_virtual.py y publica exactamente los
// mismos mensajes (ver "Contrato MQTT" en el README). La lógica de
// confirmación está en confirmacion.h, traducida de simulador/confirmacion.py y
// probada en el PC con ./scripts/probar_firmware.sh.
//
// Antes de compilar (detalle en firmware/fruitai_camara/README.md):
//  1. Edge Impulse → Deployment → Arduino library → instalar el .zip en el IDE
//     (Sketch → Include Library → Add .ZIP Library).
//  2. Cambiar MODELO_H abajo por el nombre del .h de esa librería.
//  3. Copiar secrets.h.example a secrets.h y completarlo (no va a git).
//  4. Placa: "ESP32S3 Dev Module" (o "XIAO_ESP32S3"), PSRAM: "OPI PSRAM".

// ====================== Configuración ======================
#include <fruitai_inferencing.h>   // MODELO_H: <nombre-proyecto-EI>_inferencing.h

// Placa: descomentar UNA.
#define PLACA_FREENOVE_S3    // Freenove ESP32-S3 WROOM CAM / ESP32-S3-EYE (mismo pinout)
// #define PLACA_XIAO_S3     // Seeed XIAO ESP32S3 Sense

#define UMBRAL           0.75f  // confianza mínima (igual que --umbral del ESP32 virtual)
#define FRAMES_CONFIRMAR 5      // fotogramas seguidos para confirmar (~1 s a 5 inf/s)
#define FRAMES_RETIRO    5      // fotogramas de "fondo" para dar la fruta por retirada
#define PERIODO_INF_MS   200    // una inferencia cada 200 ms = 5 inf/s como máximo

#define USAR_PIR     1          // 0 = siempre activo (sin sensor de presencia)
#define PRESENCIA_MS 15000      // la cámara sigue activa 15 s después del último movimiento

#define PUBLICAR_FOTO 0         // 1 = manda fotos a Home Assistant (para verla en el panel).
                                // El reconocimiento sigue siendo en el ESP32; la foto es solo para mirar.
#define PERIODO_FOTO_MS 500    // 2 fotos/s (~20 KB/s por Wi-Fi)

#define USAR_DHT     0          // 1 = este mismo ESP32 publica temperatura y humedad
#define TIPO_DHT     DHT22
#define INTERVALO_DHT_MS 30000
// ===========================================================

#if defined(PLACA_FREENOVE_S3)
  // Cámara
  #define PWDN_GPIO_NUM  -1
  #define RESET_GPIO_NUM -1
  #define XCLK_GPIO_NUM  15
  #define SIOD_GPIO_NUM   4
  #define SIOC_GPIO_NUM   5
  #define Y9_GPIO_NUM    16
  #define Y8_GPIO_NUM    17
  #define Y7_GPIO_NUM    18
  #define Y6_GPIO_NUM    12
  #define Y5_GPIO_NUM    10
  #define Y4_GPIO_NUM     8
  #define Y3_GPIO_NUM     9
  #define Y2_GPIO_NUM    11
  #define VSYNC_GPIO_NUM  6
  #define HREF_GPIO_NUM   7
  #define PCLK_GPIO_NUM  13
  // Botones (a GND), PIR, DHT y LED externo (con resistencia de 220 Ω)
  #define PIN_BTN_ENTRADA 14
  #define PIN_BTN_SALIDA  21
  #define PIN_PIR          1
  #define PIN_DHT         47
  #define PIN_LED          2   // LED azul de la placa
  #define LED_ACTIVO_BAJO  0
#elif defined(PLACA_XIAO_S3)
  #define PWDN_GPIO_NUM  -1
  #define RESET_GPIO_NUM -1
  #define XCLK_GPIO_NUM  10
  #define SIOD_GPIO_NUM  40
  #define SIOC_GPIO_NUM  39
  #define Y9_GPIO_NUM    48
  #define Y8_GPIO_NUM    11
  #define Y7_GPIO_NUM    12
  #define Y6_GPIO_NUM    14
  #define Y5_GPIO_NUM    16
  #define Y4_GPIO_NUM    18
  #define Y3_GPIO_NUM    17
  #define Y2_GPIO_NUM    15
  #define VSYNC_GPIO_NUM 38
  #define HREF_GPIO_NUM  47
  #define PCLK_GPIO_NUM  13
  #define PIN_BTN_ENTRADA 1    // D0
  #define PIN_BTN_SALIDA  2    // D1
  #define PIN_PIR         3    // D2
  #define PIN_DHT         4    // D3
  #define PIN_LED        21    // LED de usuario (naranja)
  #define LED_ACTIVO_BAJO 1
#else
  #error "Elige una placa: PLACA_FREENOVE_S3 o PLACA_XIAO_S3"
#endif

#include <WiFi.h>
#include <PubSubClient.h>
#include "esp_camera.h"
#include "img_converters.h"
#include "edge-impulse-sdk/dsp/image/image.hpp"
#include "confirmacion.h"
#include "secrets.h"
#if USAR_DHT
  #include <DHT.h>
  DHT dht(PIN_DHT, TIPO_DHT);
  unsigned long ultimoDht = 0;
#endif

#if !defined(EI_CLASSIFIER_SENSOR) || EI_CLASSIFIER_SENSOR != EI_CLASSIFIER_SENSOR_CAMERA
  #error "El modelo de Edge Impulse no es de imagen"
#endif

const char* T_MOVIMIENTO = "fruitai/movimiento";
const char* T_AMBIENTE   = "fruitai/ambiente";
const char* T_ESTADO     = "fruitai/esp32/estado";   // online / offline (LWT)
const char* T_AVISO      = "fruitai/aviso";          // rechazos del servicio
const char* T_DETECCION  = "fruitai/esp32/deteccion"; // qué ve/confirma (sensor "Fruta detectada" en HA)
const char* T_BOTON      = "fruitai/esp32/boton";     // botones + / − del panel de HA: entrada / salida
const char* T_FOTO       = "fruitai/esp32/foto";      // JPEG para la cámara del panel (opcional)

// La cámara entrega QVGA; el modelo usa el cuadrado central reescalado
// (EI_CLASSIFIER_INPUT_WIDTH x HEIGHT, normalmente 96x96), igual que el
// recorte_central() del ESP32 virtual.
#define CAM_ANCHO 320
#define CAM_ALTO  240
static uint8_t* imagen = nullptr;   // RGB888 en PSRAM

WiFiClient red;
PubSubClient mqtt(red);
Confirmador conf(UMBRAL, FRAMES_CONFIRMAR, FRAMES_RETIRO);

// ---------- cola de movimientos pendientes ----------
// PubSubClient publica con QoS 0. Para no perder un movimiento si el Wi-Fi o el
// broker caen justo al pulsar, se guarda aquí y se envía al reconectar. Con
// evento_id el servicio ignora un repetido, así que reenviar es seguro.
#define COLA_MAX 8
static char cola[COLA_MAX][160];
static int colaInicio = 0, colaN = 0;
static uint32_t idArranque = 0, contadorEventos = 0;

// ---------- utilidades ----------
void led(bool encendido) { digitalWrite(PIN_LED, (encendido ^ LED_ACTIVO_BAJO) ? HIGH : LOW); }

void parpadear(int veces, int ms) {
  for (int i = 0; i < veces; i++) { led(true); delay(ms); led(false); delay(ms); }
}

struct Boton {
  uint8_t pin;
  bool anterior = true;            // INPUT_PULLUP: suelto = HIGH
  unsigned long cambio = 0;
  bool estable = true;
  explicit Boton(uint8_t p) : pin(p) {}
  bool pulsado() {                 // true una sola vez por pulsación (antirrebote 50 ms)
    bool lectura = digitalRead(pin);
    if (lectura != anterior) { cambio = millis(); anterior = lectura; }
    if (millis() - cambio > 50 && lectura != estable) {
      estable = lectura;
      return estable == LOW;
    }
    return false;
  }
};
Boton btnEntrada(PIN_BTN_ENTRADA), btnSalida(PIN_BTN_SALIDA);

// Pulsación pendiente que llegó desde Home Assistant (se procesa en loop(), igual que un botón).
static const char* botonRemoto = nullptr;
// Última predicción, para informarla a HA.
static const char* ultimaEtiqueta = "fondo";
static float ultimaConfianza = 0.0f;

// ---------- cámara ----------
bool iniciarCamara() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM; c.pin_d1 = Y3_GPIO_NUM; c.pin_d2 = Y4_GPIO_NUM; c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM; c.pin_d5 = Y7_GPIO_NUM; c.pin_d6 = Y8_GPIO_NUM; c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM; c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM; c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_QVGA;
  c.jpeg_quality = 12;
  c.fb_count = 1;
  c.fb_location = CAMERA_FB_IN_PSRAM;
  c.grab_mode = CAMERA_GRAB_LATEST;   // siempre el fotograma más reciente

  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("Error iniciando la cámara: 0x%x (¿placa correcta? ¿cable plano?)\n", err);
    return false;
  }
#if defined(PLACA_FREENOVE_S3)
  sensor_t* s = esp_camera_sensor_get();
  s->set_vflip(s, 1);                 // en esta placa la imagen sale invertida
#endif
  return true;
}

// Edge Impulse pide los píxeles como floats 0xRRGGBB. fmt2rgb888 deja BGR.
static int leerPixeles(size_t desde, size_t n, float* salida) {
  size_t i = desde * 3;
  for (size_t k = 0; k < n; k++, i += 3)
    salida[k] = (imagen[i + 2] << 16) + (imagen[i + 1] << 8) + imagen[i];
  return 0;
}

// Captura y clasifica un fotograma. Devuelve false si falló la cámara.
bool clasificar(const char** etiqueta, float* confianza, uint32_t* ms) {
  unsigned long t0 = millis();
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) return false;
#if PUBLICAR_FOTO
  // La cámara ya entrega JPEG: se manda tal cual, sin copiarlo, por partes.
  static unsigned long ultimaFoto = 0;
  if (mqtt.connected() && millis() - ultimaFoto >= PERIODO_FOTO_MS) {
    ultimaFoto = millis();
    if (mqtt.beginPublish(T_FOTO, fb->len, false)) {
      mqtt.write(fb->buf, fb->len);
      mqtt.endPublish();
    }
  }
#endif
  bool ok = fmt2rgb888(fb->buf, fb->len, PIXFORMAT_JPEG, imagen);
  esp_camera_fb_return(fb);
  if (!ok) return false;
  // Recorta el cuadrado central y lo reescala al tamaño del modelo.
  ei::image::processing::crop_and_interpolate_rgb888(
      imagen, CAM_ANCHO, CAM_ALTO, imagen, EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT);

  ei::signal_t senal;
  senal.total_length = EI_CLASSIFIER_INPUT_WIDTH * EI_CLASSIFIER_INPUT_HEIGHT;
  senal.get_data = &leerPixeles;
  ei_impulse_result_t r = {};
  if (run_classifier(&senal, &r, false) != EI_IMPULSE_OK) return false;

  size_t mejor = 0;
  for (size_t i = 1; i < EI_CLASSIFIER_LABEL_COUNT; i++)
    if (r.classification[i].value > r.classification[mejor].value) mejor = i;
  *etiqueta = r.classification[mejor].label;
  *confianza = r.classification[mejor].value;
  *ms = millis() - t0;
  return true;
}

// ---------- red ----------
void conectarWifi() {
  static unsigned long ultimoIntento = 0;
  if (WiFi.status() == WL_CONNECTED || millis() - ultimoIntento < 10000) return;
  ultimoIntento = millis();
  Serial.printf("Conectando a Wi-Fi \"%s\"...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_CLAVE);   // no bloquea: el loop sigue clasificando
}

void alRecibir(char* topico, byte* payload, unsigned int largo) {
  if (strcmp(topico, T_BOTON) == 0) {
    if (largo == 7 && memcmp(payload, "entrada", 7) == 0) botonRemoto = "entrada";
    else if (largo == 6 && memcmp(payload, "salida", 6) == 0) botonRemoto = "salida";
    return;
  }
  if (strcmp(topico, T_AVISO) != 0) return;
  Serial.printf("Aviso del servicio: %.*s\n", (int)largo, (const char*)payload);
  parpadear(3, 80);   // p. ej. "salida de banano con stock 0"
}

void conectarMqtt() {
  static unsigned long ultimoIntento = 0;
  if (mqtt.connected() || WiFi.status() != WL_CONNECTED || millis() - ultimoIntento < 5000) return;
  ultimoIntento = millis();
  Serial.printf("Wi-Fi OK (%s, %d dBm). MQTT %s:%d como %s... ", WiFi.localIP().toString().c_str(),
                WiFi.RSSI(), MQTT_HOST, MQTT_PUERTO, MQTT_USUARIO);
  if (mqtt.connect("fruitai-camara", MQTT_USUARIO, MQTT_CLAVE, T_ESTADO, 1, true, "offline")) {
    Serial.println("OK");
    mqtt.publish(T_ESTADO, "online", true);
    mqtt.subscribe(T_AVISO, 1);
    mqtt.subscribe(T_BOTON, 1);
  } else {
    // -2: no llega al broker (IP/red); 4 o 5: usuario o clave incorrectos
    Serial.printf("falló (estado %d)\n", mqtt.state());
  }
}

void encolarMovimiento(const Movimiento& m) {
  if (colaN == COLA_MAX) {   // llena: se descarta el más viejo
    Serial.println("Cola llena: se pierde el movimiento más antiguo");
    colaInicio = (colaInicio + 1) % COLA_MAX;
    colaN--;
  }
  char* p = cola[(colaInicio + colaN) % COLA_MAX];
  snprintf(p, sizeof(cola[0]),
           "{\"fruta\": \"%s\", \"tipo\": \"%s\", \"cantidad\": 1, \"confianza\": %.2f, "
           "\"evento_id\": \"cam-%08lx-%lu\"}",
           m.fruta, m.tipo, m.confianza, (unsigned long)idArranque, (unsigned long)++contadorEventos);
  colaN++;
}

void enviarPendientes() {
  while (colaN > 0 && mqtt.connected()) {
    const char* p = cola[colaInicio];
    if (!mqtt.publish(T_MOVIMIENTO, p)) break;   // se reintenta en la próxima vuelta
    Serial.printf("→ %s %s\n", T_MOVIMIENTO, p);
    colaInicio = (colaInicio + 1) % COLA_MAX;
    colaN--;
  }
}

#if USAR_DHT
void publicarAmbiente() {
  if (!mqtt.connected() || (ultimoDht && millis() - ultimoDht < INTERVALO_DHT_MS)) return;
  ultimoDht = millis();
  float h = dht.readHumidity(), t = dht.readTemperature();
  if (isnan(h) || isnan(t)) { Serial.println("Error leyendo el DHT"); return; }
  char p[64];
  snprintf(p, sizeof(p), "{\"temperatura\": %.1f, \"humedad\": %.1f}", t, h);
  mqtt.publish(T_AMBIENTE, p, true);
  Serial.printf("→ %s %s\n", T_AMBIENTE, p);
}
#endif

// ---------- programa ----------
void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n== FruitAI ESP32-S3: cámara + TinyML ==");
  pinMode(PIN_LED, OUTPUT);
  led(false);
  pinMode(PIN_BTN_ENTRADA, INPUT_PULLUP);
  pinMode(PIN_BTN_SALIDA, INPUT_PULLUP);
#if USAR_PIR
  pinMode(PIN_PIR, INPUT);
#endif
#if USAR_DHT
  dht.begin();
#endif
  idArranque = esp_random();   // evento_id distinto en cada arranque

  imagen = (uint8_t*)ps_malloc(CAM_ANCHO * CAM_ALTO * 3);
  if (!imagen || !iniciarCamara()) {
    Serial.println(imagen ? "Sin cámara: detenido." : "Sin PSRAM (activa \"OPI PSRAM\" en Herramientas): detenido.");
    while (true) parpadear(1, 500);   // LED lento = error de hardware
  }
  Serial.printf("Modelo: %dx%d, %d clases:", EI_CLASSIFIER_INPUT_WIDTH, EI_CLASSIFIER_INPUT_HEIGHT,
                EI_CLASSIFIER_LABEL_COUNT);
  for (size_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) Serial.printf(" %s", ei_classifier_inferencing_categories[i]);
  Serial.printf("\nUmbral %.2f, %d fotogramas para confirmar\n", UMBRAL, FRAMES_CONFIRMAR);

  mqtt.setServer(MQTT_HOST, MQTT_PUERTO);
  mqtt.setCallback(alRecibir);
  mqtt.setKeepAlive(15);
  conectarWifi();
}

void loop() {
  conectarWifi();
  conectarMqtt();
  mqtt.loop();
  enviarPendientes();
#if USAR_DHT
  publicarAmbiente();
#endif

  // Botones: se leen en cada vuelta para no perder una pulsación corta. Los botones
  // + / − del panel de Home Assistant llegan por MQTT y siguen el mismo camino.
  const char* tipo = btnEntrada.pulsado() ? "entrada" : (btnSalida.pulsado() ? "salida" : nullptr);
  const bool desdeHA = !tipo && botonRemoto;
  if (desdeHA) tipo = botonRemoto;
  botonRemoto = nullptr;
  if (tipo) {
    Movimiento m = conf.boton(tipo);
    Serial.printf("%s%s\n", conf.mensaje, desdeHA ? "  [desde Home Assistant]" : "");
    if (m.valido) {
      encolarMovimiento(m);
      enviarPendientes();
      if (colaN) Serial.printf("Sin conexión: %d movimiento(s) en cola\n", colaN);
    } else {
      parpadear(2, 60);   // pulsación ignorada
      if (desdeHA && mqtt.connected()) mqtt.publish(T_AVISO, conf.mensaje);   // que el celular sepa por qué
    }
  }

  // Sensor de presencia: solo ACTIVA la detección (plan: "sensor de presencia
  // para activar la detección"). Sin movimiento la cámara descansa y el estado
  // se congela; NO cuenta como retiro, porque un PIR deja de ver una fruta
  // quieta y eso permitiría registrarla dos veces. El retiro lo decide la
  // cámara al ver "fondo".
  static unsigned long ultimaPresencia = 0;
#if USAR_PIR
  if (digitalRead(PIN_PIR) == HIGH) ultimaPresencia = millis();
  const bool activa = ultimaPresencia && millis() - ultimaPresencia < PRESENCIA_MS;
#else
  const bool activa = true;
#endif

  static bool activaAntes = false;
  if (activa != activaAntes) {
    Serial.println(activa ? "Presencia: cámara activa" : "Sin presencia: cámara en reposo");
    activaAntes = activa;
  }

  static unsigned long ultimaInf = 0;
  if (activa && millis() - ultimaInf >= PERIODO_INF_MS) {
    ultimaInf = millis();
    const char* etiqueta;
    float confianza;
    uint32_t ms;
    if (!clasificar(&etiqueta, &confianza, &ms)) {
      Serial.println("Fallo al capturar/clasificar");
      return;
    }
    Estado antes = conf.estado;
    ultimaEtiqueta = etiqueta;
    ultimaConfianza = confianza;
    conf.procesar(etiqueta, confianza, true);
    if (conf.estado != antes) Serial.println(conf.mensaje);

    static unsigned long ultimoLog = 0;   // una línea por segundo (latencia para el documento)
    if (millis() - ultimoLog >= 1000) {
      ultimoLog = millis();
      Serial.printf("ve: %s %.0f%% (%lu ms) | %s%s%s\n", etiqueta, confianza * 100, (unsigned long)ms,
                    nombreEstado(conf.estado), conf.fruta[0] ? " - " : "", conf.fruta);
    }
  }

  // Estado para Home Assistant ("Fruta detectada"): al cambiar y cada 2 s.
  static Estado estadoPublicado = (Estado)-1;
  static unsigned long ultimaDeteccion = 0;
  if (mqtt.connected() && (conf.estado != estadoPublicado || millis() - ultimaDeteccion >= 2000)) {
    char p[200];
    snprintf(p, sizeof(p),
             "{\"estado\": \"%s\", \"fruta\": \"%s\", \"confianza\": %.2f, \"ve\": \"%s\", \"ve_confianza\": %.2f}",
             nombreEstado(conf.estado), conf.fruta[0] ? conf.fruta : "ninguna", conf.confianza,
             ultimaEtiqueta, ultimaConfianza);
    if (mqtt.publish(T_DETECCION, p, true)) {
      estadoPublicado = conf.estado;
      ultimaDeteccion = millis();
    }
  }

  // LED: apagado = esperando, fijo = confirmada (pulsa un botón),
  // parpadeo lento = registrada (retira la fruta).
  if (conf.estado == CONFIRMADA) led(true);
  else if (conf.estado == REGISTRADA) led((millis() / 400) % 2);
  else led(false);
}
