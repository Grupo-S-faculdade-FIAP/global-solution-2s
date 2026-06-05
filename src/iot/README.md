# IoT — ESP32 + DHT22

Módulo de coleta de dados de campo (temperatura e umidade) com envio direto à API GS2.

## Hardware

| Componente | Pino ESP32 |
|------------|-----------|
| DHT22 DATA | GPIO 4 |
| LED vermelho | GPIO 15 |

## Simulação (Wokwi)

1. Acesse [wokwi.com](https://wokwi.com) → New Project → ESP32
2. Adicione sensor DHT22 no GPIO 4
3. Cole o conteúdo de `firmware.cpp`

## Configuração

As credenciais e o endpoint são configurados por macros antes de compilar:

```cpp
// Wi-Fi
#define WIFI_SSID     "sua-rede"
#define WIFI_PASSWORD "sua-senha"

// Endpoint GS2
#define GS2_API_ENDPOINT "https://qqnjq8qsmh.execute-api.us-east-1.amazonaws.com/iot/readings"

// Demo local (make demo)
// #define GS2_API_ENDPOINT "http://192.168.x.x:8000/iot/readings"
```

Nunca faça commit dessas macros com credenciais reais — use builds locais.

## Fluxo de dados

```
ESP32 (DHT22) → POST /iot/readings → FastAPI GS2 → DynamoDB iot_readings
                                                  ↓ (mock)
                                              data/demo/iot_readings.json
```

## Formato da requisição

```json
{
  "device_id": "esp32_01",
  "cidade": "São Paulo",
  "temperatura": 24.5,
  "umidade": 68.0
}
```

## Resposta

```json
{
  "stored": true,
  "reading_id": "iot_abc123",
  "timestamp": "2026-06-05T15:00:00Z",
  "storage": "dynamodb"
}
```

## Dependências Arduino

- `ArduinoJson`
- `DHT sensor library` (Adafruit)
- `WiFi` (built-in ESP32)
- `HTTPClient` (built-in ESP32)
