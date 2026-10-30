/*
AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the BeaconMind ESP32-CAM JPEG HTTP sketch (M1.T6).
AI-assisted: Grok 4.7 via Cursor, 2026-10-06: raised stills to UXGA and JPEG quality 10.
Derived from: none (esp_camera, WiFi, and WebServer used as libraries).
Pin numbers are the AI-Thinker values in the installed core file
camera_pins.h (esp32 3.3.12, CAMERA_MODEL_AI_THINKER, lines 161-180),
including LED_GPIO_NUM 4, which matches esp32cam-notes.md section 3.
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include "esp_timer.h"
#include "wifi_config.h"

#if !defined(BM_WIFI_SSID) && defined(WIFI_SSID)
#define BM_WIFI_SSID WIFI_SSID
#endif
#if !defined(BM_WIFI_PASS) && defined(WIFI_PASSWORD)
#define BM_WIFI_PASS WIFI_PASSWORD
#endif

#ifndef BM_VFLIP
#define BM_VFLIP 0
#endif
#ifndef BM_HMIRROR
#define BM_HMIRROR 0
#endif

// camera_pins.h CAMERA_MODEL_AI_THINKER
static const int kPwdn = 32;
static const int kReset = -1;
static const int kXclk = 0;
static const int kSiod = 26;
static const int kSioc = 27;
static const int kY9 = 35;
static const int kY8 = 34;
static const int kY7 = 39;
static const int kY6 = 36;
static const int kY5 = 21;
static const int kY4 = 19;
static const int kY3 = 18;
static const int kY2 = 5;
static const int kVsync = 25;
static const int kHref = 23;
static const int kPclk = 22;
static const int kFlashLed = 4;

static const char *kFw = "bm_cam-0.1";
// jpeg_quality is 0-63; lower is sharper (esp_camera.h). No tested value
// sharper than 10 is recorded in this tree. 0 is not used.
// fb_count is 1 because this sketch does not document that PSRAM can hold
// two UXGA JPEG buffers. QXGA and larger framesizes are not used.
#define BM_JPEG_QUALITY 10
#define BM_FB_COUNT 1
#define BM_STR_IMPL(x) #x
#define BM_STR(x) BM_STR_IMPL(x)
#pragma message("bm_cam frame_size=FRAMESIZE_UXGA width=1600 height=1200 jpeg_quality=" BM_STR(BM_JPEG_QUALITY) " fb_count=" BM_STR(BM_FB_COUNT))
static WebServer server(80);
static bool cameraOk = false;
static bool announced = false;
static uint32_t framesServed = 0;
static uint32_t lastRetryMs = 0;

static const char *const kFrameSizeNames[] = {
    "96X96", "QQVGA", "128X128", "QCIF",  "HQVGA", "240X240", "QVGA", "320X320",
    "CIF",   "HVGA",  "VGA",     "SVGA",  "XGA",   "HD",      "SXGA", "UXGA",
    "FHD",   "P_HD",  "P_3MP",   "QXGA",  "QHD",   "WQXGA",   "P_FHD", "QSXGA",
    "5MP"};
static_assert(sizeof(kFrameSizeNames) / sizeof(kFrameSizeNames[0]) == FRAMESIZE_INVALID,
              "kFrameSizeNames must match framesize_t");

const char *frameSizeName(framesize_t size) {
  if (size >= FRAMESIZE_INVALID) {
    return "INVALID";
  }
  return kFrameSizeNames[size];
}

void sendStatus() {
  int rssi = 0;
  if (WiFi.status() == WL_CONNECTED) {
    rssi = WiFi.RSSI();
  }
  const char *framesize = "NONE";
  int width = 0;
  int height = 0;
  int quality = 0;
  sensor_t *sensor = esp_camera_sensor_get();
  if (sensor != nullptr && sensor->status.framesize < FRAMESIZE_INVALID) {
    framesize_t size = sensor->status.framesize;
    framesize = frameSizeName(size);
    width = resolution[size].width;
    height = resolution[size].height;
    quality = sensor->status.quality;
  }
  char body[384];
  snprintf(
      body, sizeof(body),
      "{\"fw\": \"%s\", \"framesize\": \"%s\", \"width\": %d, \"height\": %d, "
      "\"quality\": %d, \"vflip\": %d, \"hmirror\": %d, \"rssi_dbm\": %d, "
      "\"uptime_ms\": %lu, \"free_heap\": %lu, \"psram\": %s, \"frames\": %lu}",
      kFw, framesize, width, height, quality, BM_VFLIP, BM_HMIRROR, rssi,
      (unsigned long)millis(), (unsigned long)ESP.getFreeHeap(),
      psramFound() ? "true" : "false", (unsigned long)framesServed);
  server.send(200, "application/json", body);
}

void handleCapture() {
  if (!cameraOk) {
    server.send(503, "text/plain", "camera failed\n");
    return;
  }
  camera_fb_t *discard = esp_camera_fb_get();
  if (discard != nullptr) {
    esp_camera_fb_return(discard);
  }
  camera_fb_t *fb = esp_camera_fb_get();
  if (fb == nullptr) {
    server.send(503, "text/plain", "camera failed\n");
    return;
  }
  int64_t captureUs = esp_timer_get_time();
  framesServed += 1;
  server.sendHeader("X-BM-Seq", String(framesServed));
  server.sendHeader("X-BM-Capture-Us", String((uint64_t)captureUs));
  server.sendHeader("X-BM-Uptime-Ms", String(millis()));
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void handleLed() {
  if (server.hasArg("on")) {
    String on = server.arg("on");
    if (on == "1") {
      digitalWrite(kFlashLed, HIGH);
    } else if (on == "0") {
      digitalWrite(kFlashLed, LOW);
    }
  }
  sendStatus();
}

bool startCamera() {
  camera_config_t config = {};
  config.pin_pwdn = kPwdn;
  config.pin_reset = kReset;
  config.pin_xclk = kXclk;
  config.pin_sccb_sda = kSiod;
  config.pin_sccb_scl = kSioc;
  config.pin_d7 = kY9;
  config.pin_d6 = kY8;
  config.pin_d5 = kY7;
  config.pin_d4 = kY6;
  config.pin_d3 = kY5;
  config.pin_d2 = kY4;
  config.pin_d1 = kY3;
  config.pin_d0 = kY2;
  config.pin_vsync = kVsync;
  config.pin_href = kHref;
  config.pin_pclk = kPclk;
  config.xclk_freq_hz = 20000000;
  config.ledc_timer = LEDC_TIMER_0;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_UXGA;
  config.jpeg_quality = BM_JPEG_QUALITY;
  config.fb_count = BM_FB_COUNT;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;
  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera probe failed");
    return false;
  }
  sensor_t *sensor = esp_camera_sensor_get();
  if (sensor != nullptr) {
    sensor->set_vflip(sensor, BM_VFLIP);
    sensor->set_hmirror(sensor, BM_HMIRROR);
  }
  return true;
}

void setup() {
  Serial.begin(115200);
  pinMode(kFlashLed, OUTPUT);
  digitalWrite(kFlashLed, LOW);
  cameraOk = startCamera();
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("bm-cam");
  WiFi.begin(BM_WIFI_SSID, BM_WIFI_PASS);
  lastRetryMs = millis();
  server.on("/capture", HTTP_GET, handleCapture);
  server.on("/status", HTTP_GET, sendStatus);
  server.on("/led", HTTP_GET, handleLed);
  server.begin();
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!announced) {
      Serial.printf("BM_CAM READY ip=%s rssi=%d fw=%s\n",
                    WiFi.localIP().toString().c_str(), WiFi.RSSI(), kFw);
      announced = true;
    }
  } else if (millis() - lastRetryMs >= 5000) {
    announced = false;
    Serial.println("BM_CAM WIFI_RETRY");
    WiFi.disconnect();
    WiFi.begin(BM_WIFI_SSID, BM_WIFI_PASS);
    lastRetryMs = millis();
  }
  server.handleClient();
}
