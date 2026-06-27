/*
 * MotoTrack - ESP32 + GPS NEO-6M
 * Bibliothèques Arduino : TinyGPSPlus et ArduinoJson.
 * Branchement : GPS TX -> ESP32 GPIO 16, GPS RX -> ESP32 GPIO 17.
 */
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <TinyGPSPlus.h>

const char* WIFI_SSID = "NOM_DU_WIFI";
const char* WIFI_PASSWORD = "MOT_DE_PASSE_WIFI";

// Test local : remplacer l'IP par celle du PC qui exécute Django.
// Adresse de production Render.
const char* API_URL = "https://mototrack-nian.onrender.com/api/gps/positions/";
// Production Render :
// const char* API_URL = "https://mototrack.onrender.com/api/gps/positions/";

const char* API_KEY = "esp32-moto-2026-secret";
const int MOTO_ID = 1;  // Identifiant affiché dans l'administration Django.
const unsigned long SEND_INTERVAL = 15000;

TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
unsigned long lastSend = 0;

void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connexion Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnecté. IP ESP32 : " + WiFi.localIP().toString());
}

void sendPosition(double latitude, double longitude) {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();

  Serial.println("\n--- Envoi MotoTrack ---");
  Serial.println("URL : " + String(API_URL));
  Serial.println("IP ESP32 : " + WiFi.localIP().toString());
  Serial.printf("Signal Wi-Fi : %d dBm\n", WiFi.RSSI());

  WiFiClientSecure client;
  // Suffisant pour les tests academiques HTTPS.
  client.setInsecure();
  HTTPClient http;
  http.setConnectTimeout(70000);
  http.setTimeout(70000);
  if (!http.begin(client, API_URL)) {
    Serial.println("Erreur : impossible d'initialiser la connexion HTTP.");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  StaticJsonDocument<256> document;
  document["moto_id"] = MOTO_ID;
  document["latitude"] = latitude;
  document["longitude"] = longitude;

  // Le NEO-6M fournit une date/heure UTC si le signal satellite est valide.
  if (gps.date.isValid() && gps.time.isValid()) {
    char dateBuffer[11];
    char timeBuffer[9];
    snprintf(dateBuffer, sizeof(dateBuffer), "%04d-%02d-%02d", gps.date.year(), gps.date.month(), gps.date.day());
    snprintf(timeBuffer, sizeof(timeBuffer), "%02d:%02d:%02d", gps.time.hour(), gps.time.minute(), gps.time.second());
    document["date"] = dateBuffer;
    document["heure"] = timeBuffer;
  }

  String payload;
  serializeJson(document, payload);
  Serial.println("Donnees : " + payload);
  int statusCode = http.POST(payload);
  Serial.printf("Code HTTP : %d\n", statusCode);
  if (statusCode > 0) {
    Serial.println("Reponse : " + http.getString());
  } else {
    Serial.println("Erreur reseau : " + http.errorToString(statusCode));
    Serial.println("Verifier : IP du PC, serveur 0.0.0.0, meme Wi-Fi et pare-feu.");
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);
  connectWiFi();
}

void loop() {
  while (gpsSerial.available()) gps.encode(gpsSerial.read());

  if (gps.location.isUpdated() && gps.location.isValid() &&
      millis() - lastSend >= SEND_INTERVAL) {
    lastSend = millis();
    sendPosition(gps.location.lat(), gps.location.lng());
  }

  if (millis() > 10000 && gps.charsProcessed() < 10) {
    Serial.println("Aucune donnée GPS : vérifier le câblage et sortir à l'extérieur.");
    delay(3000);
  }
}
