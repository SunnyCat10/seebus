#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include <Adafruit_NeoPixel.h>

#include "secrets.h"

// ------------------------------------------------------
// API CONFIGURATION
// ------------------------------------------------------
static const char* API_URL = "https://api.bolognese.dev/api/readings";
static const char* STATION_ID = "3";

// Server telemetry interval (milliseconds)
const unsigned long SEND_INTERVAL_MS = 10000; 
unsigned long lastSendTime = 0;

// ------------------------------------------------------
// ULTRASONIC & NEOPIXEL CONFIGURATION
// ------------------------------------------------------
#define SOUND_SPEED 0.034
const float ALPHA = 0.1; // EMA smoothing factor
const unsigned long PULSE_TIMEOUT = 30000;

#define NEOPIXEL_PIN 15
#define NUM_LEDS     4

Adafruit_NeoPixel strip(NUM_LEDS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

const int sensorNumber = 2;
const float HEIGHT_THRESHOLD = 50.0; // cm

struct UltrasonicSensor {
  int trigPin;
  int echoPin;
  float groundDistance;
  
  // State variables
  float emaDistance;
  bool isPersonUnder;
};

UltrasonicSensor sensors[sensorNumber] = {
  {12, 13, 95.0, -1.0, false}, // Sensor 0 (S1)
  {27, 14, 95.0, -1.0, false}  // Sensor 1 (S2)
};

int currentPeopleCount = 0;

// ------------------------------------------------------
// WI-FI & TIME HELPER FUNCTIONS
// ------------------------------------------------------
void connectToWifi() {
    Serial.print("Connecting to Wi-Fi");

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWi-Fi connected.");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

void syncTime() {
    configTime(0, 0, "pool.ntp.org", "time.google.com");

    Serial.print("Synchronizing time");
    time_t now;

    do {
        delay(500);
        Serial.print(".");
        time(&now);
    } while (now < 1700000000);

    Serial.println("\nTime synchronized.");
}

String getUtcTimestamp() {
    time_t now;
    time(&now);

    struct tm timeInfo;
    gmtime_r(&now, &timeInfo);

    char buffer[32];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);

    return String(buffer);
}

// ------------------------------------------------------
// HTTP POST FUNCTION
// ------------------------------------------------------
bool sendReading(float occupancy) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Wi-Fi disconnected. Reconnecting...");
        connectToWifi();
    }

    WiFiClientSecure client;
    client.setInsecure(); // Disable TLS verification for PoC

    HTTPClient http;

    if (!http.begin(client, API_URL)) {
        Serial.println("Could not initialize HTTP connection.");
        return false;
    }

    http.addHeader("Content-Type", "application/json");
    http.addHeader("Authorization", String("Bearer ") + SEEBUS_SENSOR_TOKEN);

    String timestamp = getUtcTimestamp();

    String body = "{"
        "\"stationId\":\"" + String(STATION_ID) + "\","
        "\"occupancy\":" + String(occupancy, 3) + ","
        "\"measuredAt\":\"" + timestamp + "\""
        "}";

    Serial.println("\n--- Sending Reading ---");
    Serial.println(body);

    int statusCode = http.POST(body);
    String response = http.getString();

    Serial.print("HTTP status: ");
    Serial.println(statusCode);
    Serial.println("Response: " + response);

    http.end();

    return statusCode == 201;
}

// ------------------------------------------------------
// NEOPIXEL HELPER
// ------------------------------------------------------
void updateNeoPixels(int visualCount) {
    strip.clear();

    if (visualCount == 0) {
        // 1 Green LED
        strip.setPixelColor(0, strip.Color(0, 255, 0));
    } 
    else if (visualCount == 50) {
        // 2 Orange LEDs
        strip.setPixelColor(0, strip.Color(255, 165, 0));
        strip.setPixelColor(1, strip.Color(255, 165, 0));
    } 
    else if (visualCount >= 100) {
        // 4 Red LEDs (All LEDs)
        for (int i = 0; i < NUM_LEDS; i++) {
            strip.setPixelColor(i, strip.Color(255, 0, 0));
        }
    }

    strip.show();
}

// ------------------------------------------------------
// ARDUINO SETUP & LOOP
// ------------------------------------------------------
void setup() {
    Serial.begin(115200);
    delay(1000);

    // Initialize NeoPixels
    strip.begin();
    strip.show();
    strip.setBrightness(50);

    // Initialize Ultrasonic pins
    for (int i = 0; i < sensorNumber; i++) {
        pinMode(sensors[i].trigPin, OUTPUT);
        pinMode(sensors[i].echoPin, INPUT);
    }

    // Connect Network & Sync Clock
    connectToWifi();
    syncTime();
}

void loop() {
    int activeSensorsThisCycle = 0;

    // 1. Read Sensors
    for (int i = 0; i < sensorNumber; i++) {
        digitalWrite(sensors[i].trigPin, LOW);
        delayMicroseconds(2);
        
        digitalWrite(sensors[i].trigPin, HIGH);
        delayMicroseconds(10);
        digitalWrite(sensors[i].trigPin, LOW);
        
        long duration = pulseIn(sensors[i].echoPin, HIGH, PULSE_TIMEOUT);
        
        if (duration > 0) {
            float rawDistance = duration * SOUND_SPEED / 2.0;
            
            if (sensors[i].emaDistance < 0) {
                sensors[i].emaDistance = rawDistance;
            } else {
                sensors[i].emaDistance = (ALPHA * rawDistance) + ((1.0 - ALPHA) * sensors[i].emaDistance);
            }
            
            float triggerDistance = sensors[i].groundDistance - HEIGHT_THRESHOLD;
            bool heightConditionMet = (sensors[i].emaDistance < triggerDistance) && (sensors[i].emaDistance > 0);
            
            if (heightConditionMet) {
                sensors[i].isPersonUnder = true;
            } else {
                if (sensors[i].emaDistance > (triggerDistance + 10.0)) {
                    sensors[i].isPersonUnder = false;
                }
            }
        }
        
        if (sensors[i].isPersonUnder) {
            activeSensorsThisCycle++;
        }
    }
    
    currentPeopleCount = activeSensorsThisCycle;
    int visualCount = currentPeopleCount * 50; // Visual scale: 0, 50, or 100

    // 2. Update NeoPixels
    updateNeoPixels(visualCount);
    
    // 3. Output Plotter Telemetry
    Serial.print("S1_EMA:"); Serial.print(sensors[0].emaDistance); Serial.print(",");
    Serial.print("S1_Trigger:"); Serial.print(sensors[0].groundDistance - HEIGHT_THRESHOLD); Serial.print(",");
    Serial.print("S2_EMA:"); Serial.print(sensors[1].emaDistance); Serial.print(",");
    Serial.print("S2_Trigger:"); Serial.print(sensors[1].groundDistance - HEIGHT_THRESHOLD); Serial.print(",");
    Serial.print("S1_Active:"); Serial.print(sensors[0].isPersonUnder ? 100 : 0); Serial.print(",");
    Serial.print("S2_Active:"); Serial.print(sensors[1].isPersonUnder ? 100 : 0); Serial.print(",");
    Serial.print("PeopleCount_Visual:"); Serial.println(visualCount); 

    // 4. Send Occupancy to Server Every 10 Seconds
    if (millis() - lastSendTime >= SEND_INTERVAL_MS) {
        lastSendTime = millis();
        float occupancy = (float)visualCount / 100.0f; // Calculate occupancy (0.00, 0.50, 1.00)
        sendReading(occupancy);
    }

    delay(100); 
}