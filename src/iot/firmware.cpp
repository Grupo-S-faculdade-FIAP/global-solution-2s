/*
 * GS2 — ESP32 IoT Sensor Node (DHT22)
 *
 * Lê temperatura e umidade via DHT22 e envia para a API GS2.
 * Endpoint destino: POST /iot/readings na Lambda GS2 (ou local via make demo).
 *
 * Simulação: https://wokwi.com — usar placa ESP32 + sensor DHT22.
 *
 * CREDENCIAIS: defina as macros abaixo antes de compilar.
 * NÃO faça commit com credenciais reais.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "DHT.h"
#include "time.h"

/* ── Configuração — altere antes de compilar ─────────────────────────────── */
#ifndef WIFI_SSID
  #define WIFI_SSID     "Wokwi-GUEST"   // Simulador Wokwi
#endif
#ifndef WIFI_PASSWORD
  #define WIFI_PASSWORD ""
#endif

// Endpoint da API GS2 (Lambda + API Gateway)
// Produção: https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/iot/readings
// Local (make demo):  http://<IP>:8000/iot/readings
#ifndef GS2_API_ENDPOINT
  #define GS2_API_ENDPOINT "https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/iot/readings"
#endif

#ifndef DEVICE_ID
  #define DEVICE_ID "esp32_01"
#endif

#ifndef CIDADE
  #define CIDADE "São Paulo"
#endif
/* ─────────────────────────────────────────────────────────────────────────── */

#define LED_VERMELHO 15
#define DHTPIN       4
#define DHTTYPE      DHT22

const char* ntpServer       = "pool.ntp.org";
const long  gmtOffset_sec   = -10800;  // Brasília UTC-3
const int   daylightOffset_sec = 0;

DHT dht(DHTPIN, DHTTYPE);


void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Conectando ao Wi-Fi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWi-Fi conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    Serial.println("NTP sincronizado.");
  } else {
    Serial.println("\nFalha Wi-Fi — operando offline.");
  }

  pinMode(LED_VERMELHO, OUTPUT);
  dht.begin();
  Serial.println("\nDigite o nome da cidade para iniciar leitura.");
}


String isoTimestamp() {
  struct tm t;
  if (!getLocalTime(&t)) return "1970-01-01T00:00:00";
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", &t);
  return String(buf);
}


bool enviarLeitura(float temperatura, float umidade, const String& cidade) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[SKIP] Wi-Fi desconectado.");
    return false;
  }

  HTTPClient http;
  http.begin(GS2_API_ENDPOINT);
  http.addHeader("Content-Type", "application/json");

  DynamicJsonDocument doc(256);
  doc["device_id"]   = DEVICE_ID;
  doc["timestamp"]   = isoTimestamp();
  doc["cidade"]      = cidade;
  doc["temperatura"] = temperatura;
  doc["umidade"]     = umidade;

  String body;
  serializeJson(doc, body);

  int code = http.POST(body);

  if (code > 0) {
    Serial.printf("[OK] HTTP %d — %s\n", code, http.getString().c_str());
    digitalWrite(LED_VERMELHO, code == 201 ? HIGH : LOW);
    delay(200);
    digitalWrite(LED_VERMELHO, LOW);
  } else {
    Serial.printf("[ERR] POST falhou: %d\n", code);
  }

  http.end();
  return (code == 200 || code == 201);
}


void loop() {
  if (!Serial.available()) return;

  String cidade = Serial.readStringUntil('\n');
  cidade.trim();

  if (cidade.length() == 0) {
    Serial.println("Cidade inválida. Tente novamente.");
    return;
  }

  float umidade     = dht.readHumidity();
  float temperatura = dht.readTemperature();

  if (isnan(umidade) || isnan(temperatura)) {
    Serial.println("[ERR] Falha na leitura do DHT22.");
    return;
  }

  Serial.printf("\n--- Leitura ---\n"
                "Device  : %s\n"
                "Cidade  : %s\n"
                "Temp    : %.1f °C\n"
                "Umidade : %.1f %%\n"
                "Horário : %s\n"
                "Endpoint: %s\n",
                DEVICE_ID, cidade.c_str(),
                temperatura, umidade,
                isoTimestamp().c_str(),
                GS2_API_ENDPOINT);

  enviarLeitura(temperatura, umidade, cidade);

  Serial.println("\nDigite o nome da cidade para nova leitura.");
}
