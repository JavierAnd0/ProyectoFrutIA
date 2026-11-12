// FruitAI — prueba del sensor de ambiente (DHT22/DHT11) en el ESP32.
//
// Lee temperatura y humedad cada INTERVALO_MS y las publica en
// fruitai/ambiente con el mismo formato que el simulador:
//   {"temperatura": 24.5, "humedad": 60.0}
// El servicio de la Raspberry las guarda en SQLite y Home Assistant las muestra
// en "Temperatura frutero" y "Humedad frutero".
//
// Probado en ESP32-C6. Sirve igual en ESP32 clásico o S3 cambiando la placa
// al compilar (y el pin si hace falta).
//
// Credenciales: copiar secrets.h.example a secrets.h y completarlo (no va a git).

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include "secrets.h"

// ---------- Configuración ----------
#define PIN_DHT 2              // pin de datos del sensor (GPIO2)
#define TIPO_DHT DHT22         // DHT22 o DHT11
const unsigned long INTERVALO_MS = 30000;  // cada 30 s

const char* T_AMBIENTE = "fruitai/ambiente";
const char* T_ESTADO   = "fruitai/esp32/estado";  // online / offline (LWT)
// ------------------------------------

DHT dht(PIN_DHT, TIPO_DHT);
WiFiClient red;
PubSubClient mqtt(red);
unsigned long ultimaLectura = 0;
unsigned long ultimoIntentoMqtt = 0;

void conectarWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("Conectando a Wi-Fi \"%s\"", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_CLAVE);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWi-Fi OK, IP %s, señal %d dBm\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
  } else {
    Serial.println("\nNo conectó al Wi-Fi (¿red de 2,4 GHz? ¿clave?). Reintento luego.");
  }
}

bool conectarMqtt() {
  Serial.printf("Conectando a MQTT %s:%d como %s... ", MQTT_HOST, MQTT_PUERTO, MQTT_USUARIO);
  // LWT: si el ESP32 se desconecta sin avisar, el broker publica "offline".
  bool ok = mqtt.connect("fruitai-esp32", MQTT_USUARIO, MQTT_CLAVE,
                         T_ESTADO, 1, true, "offline");
  if (ok) {
    Serial.println("OK");
    mqtt.publish(T_ESTADO, "online", true);
  } else {
    // -2: no llega al broker (IP/red); 4 o 5: usuario o clave incorrectos
    Serial.printf("falló (estado %d)\n", mqtt.state());
  }
  return ok;
}

void leerYPublicar() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println("Error leyendo el DHT (¿cableado? ¿pin? ¿DHT11 vs DHT22?)");
    return;
  }
  char payload[64];
  snprintf(payload, sizeof(payload), "{\"temperatura\": %.1f, \"humedad\": %.1f}", t, h);
  bool ok = mqtt.publish(T_AMBIENTE, payload, true);
  Serial.printf("%s %s %s\n", ok ? "→" : "✗ no se envió", T_AMBIENTE, payload);
}

void setup() {
  Serial.begin(115200);
  delay(1500);  // tiempo para abrir el monitor serie
  Serial.println("\n== FruitAI ESP32: sensor de ambiente ==");
  dht.begin();
  mqtt.setServer(MQTT_HOST, MQTT_PUERTO);
  conectarWifi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    conectarWifi();
    return;
  }
  if (!mqtt.connected()) {
    // reintento cada 5 s sin bloquear
    if (millis() - ultimoIntentoMqtt > 5000) {
      ultimoIntentoMqtt = millis();
      if (conectarMqtt()) ultimaLectura = 0;  // publicar enseguida al reconectar
    }
    return;
  }
  mqtt.loop();
  if (ultimaLectura == 0 || millis() - ultimaLectura >= INTERVALO_MS) {
    ultimaLectura = millis();
    leerYPublicar();
  }
}
