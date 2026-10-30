// bm_cam-0.2: one ESP32-CAM image for the Module 8 camera vision lab and the BeaconMind project.
//
// Joins Wi-Fi and serves a fresh JPEG photo over HTTP:
//   http://CAMERA_IP/capture             a new photo (boots at 640 x 480, the lab's size)
//   http://CAMERA_IP/capture?flash=1     the same, with the white flash LED on
//   http://CAMERA_IP/status              firmware, camera mode, Wi-Fi signal, counters (JSON)
//   http://CAMERA_IP/                    a preview page for checking aim, focus and orientation
//   http://CAMERA_IP/led?on=0|1          flash LED off/on (project freshness test and calibration cue)
//   http://CAMERA_IP/control?...         change the mode at runtime, not saved across a reboot:
//       framesize=qvga|vga|svga|xga|uxga   quality=10..63   vflip=0|1   hmirror=0|1
//       save=1               store the current vflip/hmirror in flash (kept across reboots)
//       clear_orientation=1  forget the stored vflip/hmirror (the build defaults apply at next boot)
//
// Board: AI Thinker ESP32-CAM (OV3660) on the ESP32-CAM-MB base board. Build and flash on the Spark
// with ../build.sh bm_cam_v02 and ../flash_app.sh bm_cam_v02 (an app-only write: this board boots
// only with the DOUT bootloader already at 0x1000, evidence/M1/M1.T6/dout-write.txt).
//
// Reused from: instructor Module 8 guide, esp32cam_camera.ino (EN.665.715 Camera Vision Source
//   Files, 2026; pristine copy assignments/assignment8/guide-original/firmware/esp32cam_camera/,
//   sha256 f8911650...); changes: see "Changes from the instructor sketch" below. The instructor
//   credits its OV3660 brightness/saturation values to Espressif's example.
// Copied from: course-project/firmware/esp32cam/bm_cam/bm_cam.ino (bm_cam-0.1) on 2026-10-25: the
//   /status field set, the X-BM-* headers, /led, the BM_CAM READY line, hostname bm-cam and the
//   BM_WIFI_* header names. Its disclosure: Grok 4.7 via Cursor, 2026-10-06, wrote that sketch.
// Derived from: espressif/esp32-camera@3fb41a9 driver/cam_hal.c:239-243 (fb->timestamp is set from
//   esp_timer when a frame's readout starts), :404-427 (CAMERA_GRAB_LATEST buffer handling) and
//   driver/esp_camera.c:396-398 (fb width/height are labels) (reimplemented, not copied).
// Derived from: espressif/arduino-esp32 3.3.12 libraries/ESP32/examples/Camera/CameraWebServer/
//   CameraWebServer.ino:44-58, 91-94 (start at UXGA, then set_framesize down) and app_httpd.cpp
//   cmd_handler "/control" (endpoint name and its setters) (reimplemented; different query format).
// AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: merged the two sketches and wrote the
//   frame-size switch, the timestamp freshness rule, the JPEG size check, /control with saved
//   orientation, the LED auto-off and the slow Wi-Fi supervisor, and the fixes from the review.
//
// Changes from the instructor sketch:
//   - Two 480,000 B frame buffers in PSRAM, enough for UXGA, so /control can select any 4:3 size up
//     to UXGA without a restart. BM_JPEG_BUFFER_BYTES alone sets that size (cam_hal.c:586-596); the
//     camera starts at UXGA and switches to VGA only to follow Espressif's example.
//   - /capture serves only a frame whose readout started after the request (or after the flash
//     LED came on) and whose JPEG is the current size; discarding one frame is not enough with two
//     buffers and CAMERA_GRAB_LATEST (cam_hal.c:404-427). Errors are 503 with a one-line body.
//   - CAMERA_VFLIP defaults to 0 and CAMERA_HMIRROR to 1 on this car's mount: frames are upright with
//     vflip 0 (evidence/M1/M1.T6/camera-quality.md:68-69) but mirrored without hmirror (printed-text
//     test, 2026-10-25). The instructor's defaults are vflip 1, hmirror 0.
//   - The SSID is never printed. Wi-Fi does not block setup(); camera failure still joins Wi-Fi.
//   - Wi-Fi scans every channel and joins the strongest node (the house mesh has six on channel 6).
//   - New endpoints /led and /control; more /status fields; X-BM-* headers on /capture.
//   - /capture sends only the first JPEG of a buffer: on this board the driver sometimes leaves 2-4
//     frames in one buffer (5 of 40 VGA buffers on 2026-10-25); /status counts them (merged_buffers).

#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>

#include <atomic>

#include "esp_camera.h"
#include "esp_http_server.h"
#include "esp_timer.h"

#include "bm_cam_util.h"
#include "wifi_config.h"   // git-ignored; copy wifi_config.h.example and fill it in on the Spark

// Copied from bm_cam-0.1: accept either spelling of the Wi-Fi macros.
#if !defined(WIFI_SSID) && defined(BM_WIFI_SSID)
#define WIFI_SSID BM_WIFI_SSID
#endif
#if !defined(WIFI_PASSWORD) && defined(BM_WIFI_PASS)
#define WIFI_PASSWORD BM_WIFI_PASS
#endif
#if !defined(WIFI_SSID) || !defined(WIFI_PASSWORD)
#error "wifi_config.h must define WIFI_SSID and WIFI_PASSWORD (or BM_WIFI_SSID and BM_WIFI_PASS)"
#endif

#define BM_FW "bm_cam-0.2"

// ===== Image orientation: build defaults; /control?hmirror=1&save=1 stores a correction =====
// A saved orientation wins over these at boot (also after a reflash, which keeps the NVS
// partition). Forget it with /control?clear_orientation=1 or the preview page's button.
#ifndef CAMERA_VFLIP
#define CAMERA_VFLIP 0     // 1 = flip vertically
#endif
#ifndef CAMERA_HMIRROR
// 1 = mirror left-right. The printed-text test on 2026-10-25 showed this mount needs it ("ABC 123"
// came out reversed with 0; assignments/assignment8/evidence/ball-test-2026-10-25/). Redo the test
// if the camera module is remounted.
#define CAMERA_HMIRROR 1
#endif

// ===== Camera mode =====
#define BM_BOOT_FRAMESIZE FRAMESIZE_VGA   // the lab's camera_node never calls /control
#define BM_BOOT_QUALITY 12                // 0-63, lower = better quality, bigger file
#define BM_MAX_FRAMESIZE FRAMESIZE_UXGA   // largest mode /control may select; also the init size
#define BM_MIN_QUALITY 10                 // sharpest value tested on this board (bm_cam-0.1)
#define BM_FB_COUNT 2
#define BM_JPEG_BUFFER_BYTES 480000       // per buffer; UXGA q10 frames measured up to 343,838 B
// Stop waiting for a fresh frame after this. The wait polls for a ready frame, so one call of
// esp_camera_fb_get blocks only when the driver drops a broken frame inside it (cam_hal.c:772-776).
#define BM_FRESH_TIMEOUT_US 1500000LL
#define BM_SETTLE_FRAMES 2                // frames dropped after a mode change
#define BM_FLASH_SETTLE_MS 150            // let auto exposure adjust to the flash LED

// ===== Housekeeping =====
#define BM_LED_AUTO_OFF_MS 30000          // /led?on=1 never stays on longer than this
#define BM_WIFI_FORCE_RETRY_MS 20000      // restart the connection only after 20 s down
#define BM_REPORT_MS 10000                // serial status line period

#define BM_STR_IMPL(x) #x
#define BM_STR(x) BM_STR_IMPL(x)
#pragma message("bm_cam-0.2 boot=FRAMESIZE_VGA quality=" BM_STR(BM_BOOT_QUALITY) " max=FRAMESIZE_UXGA fb_count=" BM_STR(BM_FB_COUNT) " jpeg_buffer=" BM_STR(BM_JPEG_BUFFER_BYTES) " vflip=" BM_STR(CAMERA_VFLIP) " hmirror=" BM_STR(CAMERA_HMIRROR))

// ===== AI Thinker ESP32-CAM pins (instructor sketch; equal to core 3.3.12 camera_pins.h
// CAMERA_MODEL_AI_THINKER, evidence/M1/M1.T6/camera-pins.txt) =====
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22
#define FLASH_LED_GPIO_NUM 4

// 4:3 sizes only: they all read the same sensor window (ov3660.c set_framesize, ratio_table), so
// the field of view stays the same. Sizes up to XGA are 2x2 binned and UXGA is not, so intrinsics
// must still be calibrated per size (plan M1.T7 pitfall); never scale camera.json K between sizes.
struct ModeName {
    const char *lower;
    const char *upper;
    framesize_t size;
};
static const ModeName kModes[] = {
    {"qvga", "QVGA", FRAMESIZE_QVGA}, {"vga", "VGA", FRAMESIZE_VGA},
    {"svga", "SVGA", FRAMESIZE_SVGA}, {"xga", "XGA", FRAMESIZE_XGA},
    {"uxga", "UXGA", FRAMESIZE_UXGA},
};
static const char *const kControlKeys[] = {"framesize", "quality", "vflip", "hmirror",
                                           "save", "clear_orientation", "t"};

static httpd_handle_t server = NULL;
static Preferences prefs;
static SemaphoreHandle_t led_lock = NULL;

static bool camera_ok = false;
static bool psram_ok = false;
static framesize_t max_framesize = FRAMESIZE_QVGA;
static const char *orientation_source = "build";   // build | saved | unsaved (changed at runtime)

// Written by the HTTP server task, read by loop() for the status line.
static std::atomic<uint32_t> frames_served{0};    // X-BM-Seq; "frames" and "photos_served"
static std::atomic<uint32_t> stale_discards{0};   // frames that started before the request
static std::atomic<uint32_t> size_discards{0};    // frames not of the current size (after a switch)
static std::atomic<uint32_t> fb_timeouts{0};      // esp_camera_fb_get returned NULL
static std::atomic<uint32_t> fresh_timeouts{0};   // no fresh frame before the deadline (a stall)
static std::atomic<uint32_t> merged_buffers{0};   // served buffers that held more than one JPEG
// LED state: changed only under led_lock; read without it for a quick check.
static std::atomic<bool> led_on{false};
static uint32_t led_on_since_ms = 0;
static bool flash_hold = false;                   // a flash photo is using the /led light now

static const char *mode_name(framesize_t size) {
    for (const ModeName &m : kModes) {
        if (m.size == size) {
            return m.upper;
        }
    }
    return "OTHER";
}

static bool mode_lookup(const char *name, framesize_t *size) {
    for (const ModeName &m : kModes) {
        if (strcasecmp(name, m.lower) == 0) {
            *size = m.size;
            return true;
        }
    }
    return false;
}

static void set_led(bool on) {
    xSemaphoreTake(led_lock, portMAX_DELAY);
    digitalWrite(FLASH_LED_GPIO_NUM, on ? HIGH : LOW);
    led_on = on;
    led_on_since_ms = millis();
    xSemaphoreGive(led_lock);
}

// Called from loop(). The clock is read under the lock, so led_on_since_ms is never later than
// now (reading it before the lock let a /led?on=1 in between wrap the difference and switch the
// LED off at once).
static bool led_auto_off() {
    bool switched = false;
    xSemaphoreTake(led_lock, portMAX_DELAY);
    const uint32_t now = millis();
    if (led_on && !flash_hold && now - led_on_since_ms >= BM_LED_AUTO_OFF_MS) {
        digitalWrite(FLASH_LED_GPIO_NUM, LOW);
        led_on = false;
        switched = true;
    }
    xSemaphoreGive(led_lock);
    return switched;
}

// For /capture?flash=1. If /led already has the LED on, hold it on for this photo only (the
// auto-off waits; its timer is not restarted, so repeated flash photos cannot keep it on);
// otherwise light it for this photo. Returns true if this call lit it.
static bool flash_begin() {
    bool lit = false;
    xSemaphoreTake(led_lock, portMAX_DELAY);
    if (led_on) {
        flash_hold = true;
    } else {
        digitalWrite(FLASH_LED_GPIO_NUM, HIGH);
        lit = true;
    }
    xSemaphoreGive(led_lock);
    return lit;
}

static void flash_end(bool lit) {
    xSemaphoreTake(led_lock, portMAX_DELAY);
    if (lit && !led_on) {
        digitalWrite(FLASH_LED_GPIO_NUM, LOW);
    }
    flash_hold = false;
    xSemaphoreGive(led_lock);
}

// Returns a frame whose readout started at or after not_before_us and whose JPEG has the current
// size, or NULL after about BM_FRESH_TIMEOUT_US. With two buffers and CAMERA_GRAB_LATEST one frame
// is always queued and the next one is already being read out, so "drop one, take the next" can
// still serve a frame that started before the request (cam_hal.c:404-427); the driver's start
// timestamp decides instead. It waits for a ready frame before calling esp_camera_fb_get, which
// would otherwise block for up to 4 s past the deadline (esp_camera.c:387, 394).
static camera_fb_t *take_fresh_frame(int64_t not_before_us, int *width, int *height) {
    const int64_t deadline = esp_timer_get_time() + BM_FRESH_TIMEOUT_US;
    while (esp_timer_get_time() < deadline) {
        if (!esp_camera_available_frames()) {
            vTaskDelay(pdMS_TO_TICKS(5));
            continue;
        }
        sensor_t *s = esp_camera_sensor_get();
        const int want_w = resolution[s->status.framesize].width;
        const int want_h = resolution[s->status.framesize].height;
        camera_fb_t *fb = esp_camera_fb_get();
        if (fb == NULL) {
            fb_timeouts++;
            continue;
        }
        const int64_t started_us = bm_timeval_us(fb->timestamp.tv_sec, fb->timestamp.tv_usec);
        int w = 0;
        int h = 0;
        if (started_us < not_before_us) {
            stale_discards++;
        } else if (!bm_jpeg_size(fb->buf, fb->len, &w, &h) || w != want_w || h != want_h) {
            size_discards++;
        } else {
            *width = w;
            *height = h;
            return fb;
        }
        esp_camera_fb_return(fb);
    }
    fresh_timeouts++;
    return NULL;
}

// After a mode change, drop the first frames of the new mode (auto exposure, half-switched frames).
static bool settle_after_change() {
    const int64_t changed_us = esp_timer_get_time();
    for (int i = 0; i < BM_SETTLE_FRAMES; ++i) {
        int w = 0;
        int h = 0;
        camera_fb_t *fb = take_fresh_frame(changed_us, &w, &h);
        if (fb == NULL) {
            return false;
        }
        esp_camera_fb_return(fb);
    }
    return true;
}

static void load_orientation(int *vflip, int *hmirror) {
    *vflip = CAMERA_VFLIP;
    *hmirror = CAMERA_HMIRROR;
    if (prefs.isKey("vflip") && prefs.isKey("hmirror")) {
        *vflip = prefs.getUChar("vflip", CAMERA_VFLIP) ? 1 : 0;
        *hmirror = prefs.getUChar("hmirror", CAMERA_HMIRROR) ? 1 : 0;
        orientation_source = "saved";
    }
}

static bool start_camera() {
    camera_config_t config = {};
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.jpeg_quality = BM_BOOT_QUALITY;

    psram_ok = psramFound();
    if (psram_ok) {
        // jpeg_buffer_size sets the buffer size (cam_hal.c:586-596), not frame_size; starting at
        // the largest mode only follows Espressif's example. set_framesize below picks the boot size.
        config.frame_size = BM_MAX_FRAMESIZE;
        config.fb_count = BM_FB_COUNT;
        config.fb_location = CAMERA_FB_IN_PSRAM;
        config.jpeg_buffer_size = BM_JPEG_BUFFER_BYTES;
        max_framesize = BM_MAX_FRAMESIZE;
    } else {
        Serial.println("No PSRAM found: check the board setting (AI Thinker ESP32-CAM). QVGA only.");
        config.frame_size = FRAMESIZE_QVGA;
        config.fb_count = 1;
        config.fb_location = CAMERA_FB_IN_DRAM;
        max_framesize = FRAMESIZE_QVGA;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x. Check the ribbon cable.\n", err);
        Serial.println("BM_CAM CAMERA_FAILED");
        return false;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (s == NULL) {
        Serial.println("Camera init failed: no sensor. Check the ribbon cable.");
        Serial.println("BM_CAM CAMERA_FAILED");
        return false;
    }
    if (s->id.PID == OV3660_PID) {
        // Recommended starting settings for the OV3660 (from Espressif's example)
        s->set_brightness(s, 1);
        s->set_saturation(s, -2);
    }
    int vflip = 0;
    int hmirror = 0;
    load_orientation(&vflip, &hmirror);
    s->set_vflip(s, vflip);
    s->set_hmirror(s, hmirror);

    const framesize_t boot = psram_ok ? BM_BOOT_FRAMESIZE : FRAMESIZE_QVGA;
    if (s->set_framesize(s, boot) != 0) {
        Serial.println("Camera init failed: could not set the boot frame size.");
        Serial.println("BM_CAM CAMERA_FAILED");
        return false;
    }
    if (!settle_after_change()) {
        Serial.println("Camera init failed: no frame after setting the boot frame size.");
        Serial.println("BM_CAM CAMERA_FAILED");
        return false;
    }

    const int w = resolution[boot].width;
    const int h = resolution[boot].height;
    if (s->id.PID == OV3660_PID) {
        Serial.printf("Camera ready: OV3660, %d x %d JPEG.\n", w, h);
    } else {
        Serial.printf("Camera ready: sensor ID 0x%x, %d x %d JPEG.\n", s->id.PID, w, h);
    }
    Serial.printf("BM_CAM CAMERA ok sensor=0x%x mode=%s q=%d max=%s vflip=%d hmirror=%d (%s)\n",
                  s->id.PID, mode_name(boot), BM_BOOT_QUALITY, mode_name(max_framesize), vflip,
                  hmirror, orientation_source);
    if (strcmp(orientation_source, "saved") == 0 &&
        (vflip != CAMERA_VFLIP || hmirror != CAMERA_HMIRROR)) {
        Serial.printf("BM_CAM ORIENTATION saved vflip=%d hmirror=%d overrides build CAMERA_VFLIP=%d "
                      "CAMERA_HMIRROR=%d (forget it: /control?clear_orientation=1)\n",
                      vflip, hmirror, CAMERA_VFLIP, CAMERA_HMIRROR);
    }
    return true;
}

// ===== HTTP =====

static esp_err_t send_text_status(httpd_req_t *req, const char *status, const char *body) {
    httpd_resp_set_status(req, status);
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_sendstr(req, body);
}

// JSON with bm_cam-0.1's fields (plan M1.T6 step 8) plus the instructor's sensor_id/photos_served
// and the new counters. Returns the snprintf length; the caller checks it against the buffer.
static int status_json(char *out, size_t cap) {
    sensor_t *s = camera_ok ? esp_camera_sensor_get() : NULL;
    const char *framesize = "NONE";
    int width = 0;
    int height = 0;
    int quality = 0;
    int vflip = 0;
    int hmirror = 0;
    unsigned sensor_id = 0;
    if (s != NULL && s->status.framesize < FRAMESIZE_INVALID) {
        framesize = mode_name(s->status.framesize);
        width = resolution[s->status.framesize].width;
        height = resolution[s->status.framesize].height;
        quality = s->status.quality;
        vflip = s->status.vflip;
        hmirror = s->status.hmirror;
        sensor_id = s->id.PID;
    }
    const int rssi = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
    return snprintf(
        out, cap,
        "{\"fw\": \"%s\", \"camera_ok\": %s, \"sensor_id\": \"0x%x\", \"framesize\": \"%s\", "
        "\"width\": %d, \"height\": %d, \"quality\": %d, \"vflip\": %d, \"hmirror\": %d, "
        "\"orientation\": \"%s\", \"max_framesize\": \"%s\", \"rssi_dbm\": %d, \"uptime_ms\": %lu, "
        "\"free_heap\": %lu, \"psram\": %s, \"frames\": %lu, \"photos_served\": %lu, "
        "\"stale_discards\": %lu, \"size_discards\": %lu, \"fb_timeouts\": %lu, "
        "\"fresh_timeouts\": %lu, \"merged_buffers\": %lu, \"led\": %d}",
        BM_FW, camera_ok ? "true" : "false", sensor_id, framesize, width, height, quality, vflip,
        hmirror, orientation_source, mode_name(max_framesize), rssi, (unsigned long)millis(),
        (unsigned long)ESP.getFreeHeap(), psram_ok ? "true" : "false",
        (unsigned long)frames_served.load(), (unsigned long)frames_served.load(),
        (unsigned long)stale_discards.load(), (unsigned long)size_discards.load(),
        (unsigned long)fb_timeouts.load(), (unsigned long)fresh_timeouts.load(),
        (unsigned long)merged_buffers.load(), led_on.load() ? 1 : 0);
}

static esp_err_t send_status(httpd_req_t *req) {
    char json[640];
    const int n = status_json(json, sizeof(json));
    if (n < 0 || (size_t)n >= sizeof(json)) {
        return send_text_status(req, "500 Internal Server Error", "status too long\n");
    }
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, json, n);
}

static esp_err_t capture_handler(httpd_req_t *req) {
    const int64_t request_us = esp_timer_get_time();
    if (!camera_ok) {
        return send_text_status(req, "503 Service Unavailable", "camera failed\n");
    }
    bool flash = false;
    char query[64];
    char value[8];
    if (httpd_req_get_url_query_str(req, query, sizeof(query)) == ESP_OK &&
        httpd_query_key_value(query, "flash", value, sizeof(value)) == ESP_OK) {
        flash = atoi(value) == 1;
    }
    int64_t not_before_us = request_us;
    bool lit_here = false;   // an LED already on from /led stays on
    if (flash) {
        lit_here = flash_begin();
        if (lit_here) {
            delay(BM_FLASH_SETTLE_MS);   // let the auto exposure adjust to the light
            not_before_us = esp_timer_get_time();
        }
    }
    int width = 0;
    int height = 0;
    camera_fb_t *fb = take_fresh_frame(not_before_us, &width, &height);
    const int64_t obtained_us = esp_timer_get_time();
    flash_end(lit_here);
    if (fb == NULL) {
        Serial.println("Photo failed.");
        return send_text_status(req, "503 Service Unavailable", "camera failed\n");
    }

    const uint32_t seq_no = frames_served.fetch_add(1) + 1;
    // Header values must stay valid until httpd_resp_send returns.
    char seq[12];
    char capture_us[24];
    char frame_us[24];
    char uptime_ms[12];
    char w_text[8];
    char h_text[8];
    snprintf(seq, sizeof(seq), "%lu", (unsigned long)seq_no);
    snprintf(capture_us, sizeof(capture_us), "%lld", (long long)obtained_us);
    snprintf(frame_us, sizeof(frame_us), "%lld",
             (long long)bm_timeval_us(fb->timestamp.tv_sec, fb->timestamp.tv_usec));
    snprintf(uptime_ms, sizeof(uptime_ms), "%lu", (unsigned long)millis());
    snprintf(w_text, sizeof(w_text), "%d", width);
    snprintf(h_text, sizeof(h_text), "%d", height);

    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "X-BM-Seq", seq);
    httpd_resp_set_hdr(req, "X-BM-Capture-Us", capture_us);   // esp_timer when the frame was obtained
    httpd_resp_set_hdr(req, "X-BM-Frame-Us", frame_us);       // esp_timer when its readout started
    httpd_resp_set_hdr(req, "X-BM-Uptime-Ms", uptime_ms);
    httpd_resp_set_hdr(req, "X-BM-Width", w_text);
    httpd_resp_set_hdr(req, "X-BM-Height", h_text);
    // The driver can leave several frames in one buffer (it misses a frame's end) and trims at the
    // last EOI; send only the first image, the one that started at X-BM-Frame-Us.
    size_t send_len = bm_jpeg_first_image_len(fb->buf, fb->len);
    if (send_len == 0) {
        send_len = fb->len;
    } else if (send_len < fb->len) {
        merged_buffers++;
    }
    esp_err_t result = httpd_resp_send(req, (const char *)fb->buf, send_len);
    esp_camera_fb_return(fb);
    return result;
}

static esp_err_t status_handler(httpd_req_t *req) {
    return send_status(req);
}

// One query value: 1 = present, 0 = absent, -1 = present but longer than the buffer (IDF returns
// ESP_ERR_HTTPD_RESULT_TRUNC without copying, httpd_parse.c), which must not look like "absent".
static int query_value(const char *query, const char *key, char *value, size_t size) {
    const esp_err_t r = httpd_query_key_value(query, key, value, size);
    if (r == ESP_OK) {
        return 1;
    }
    return r == ESP_ERR_HTTPD_RESULT_TRUNC ? -1 : 0;
}

static esp_err_t led_handler(httpd_req_t *req) {
    char query[32];
    char value[4];
    const esp_err_t got = httpd_req_get_url_query_str(req, query, sizeof(query));
    if (got == ESP_ERR_HTTPD_RESULT_TRUNC) {
        return send_text_status(req, "400 Bad Request", "query too long\n");
    }
    static const char *const kLedKeys[] = {"on", "t"};
    char bad[16];
    if (got == ESP_OK && !bm_query_keys_allowed(query, kLedKeys, 2, bad, sizeof(bad))) {
        return send_text_status(req, "400 Bad Request", "use /led?on=0 or /led?on=1\n");
    }
    if (got == ESP_OK) {
        const int on = query_value(query, "on", value, sizeof(value));
        if (on == 1 && strcmp(value, "1") == 0) {
            set_led(true);
        } else if (on == 1 && strcmp(value, "0") == 0) {
            set_led(false);
        } else if (on != 0) {
            return send_text_status(req, "400 Bad Request", "on must be 0 or 1\n");
        }
    }
    return send_status(req);
}

static esp_err_t control_handler(httpd_req_t *req) {
    if (!camera_ok) {
        return send_text_status(req, "503 Service Unavailable", "camera failed\n");
    }
    char query[128] = "";
    const esp_err_t got = httpd_req_get_url_query_str(req, query, sizeof(query));
    if (got == ESP_ERR_HTTPD_RESULT_TRUNC) {
        return send_text_status(req, "400 Bad Request", "query too long\n");
    }
    char bad[24];
    if (got == ESP_OK && !bm_query_keys_allowed(query, kControlKeys,
                                                sizeof(kControlKeys) / sizeof(kControlKeys[0]),
                                                bad, sizeof(bad))) {
        char body[64];
        snprintf(body, sizeof(body), "unknown key or key without a value: %s\n", bad);
        return send_text_status(req, "400 Bad Request", body);
    }

    // Check every value first, then apply them together.
    char value[16];
    bool has_size = false, has_quality = false, has_vflip = false, has_hmirror = false;
    bool save = false, clear = false;
    framesize_t size = FRAMESIZE_VGA;
    int quality = 0, vflip = 0, hmirror = 0, flag = 0;
    if (got == ESP_OK) {
        int found = query_value(query, "framesize", value, sizeof(value));
        if (found != 0) {
            if (found < 0 || !mode_lookup(value, &size) || size > max_framesize) {
                return send_text_status(req, "400 Bad Request",
                                        "framesize: qvga, vga, svga, xga or uxga (up to max_framesize)\n");
            }
            has_size = true;
        }
        found = query_value(query, "quality", value, sizeof(value));
        if (found != 0) {
            if (found < 0 || !bm_parse_int(value, BM_MIN_QUALITY, 63, &quality)) {
                return send_text_status(req, "400 Bad Request", "quality: 10 to 63\n");
            }
            has_quality = true;
        }
        found = query_value(query, "vflip", value, sizeof(value));
        if (found != 0) {
            if (found < 0 || !bm_parse_int(value, 0, 1, &vflip)) {
                return send_text_status(req, "400 Bad Request", "vflip: 0 or 1\n");
            }
            has_vflip = true;
        }
        found = query_value(query, "hmirror", value, sizeof(value));
        if (found != 0) {
            if (found < 0 || !bm_parse_int(value, 0, 1, &hmirror)) {
                return send_text_status(req, "400 Bad Request", "hmirror: 0 or 1\n");
            }
            has_hmirror = true;
        }
        found = query_value(query, "save", value, sizeof(value));
        if (found != 0) {
            if (found < 0 || !bm_parse_int(value, 1, 1, &flag)) {
                return send_text_status(req, "400 Bad Request", "save: 1\n");
            }
            save = true;
        }
        found = query_value(query, "clear_orientation", value, sizeof(value));
        if (found != 0) {
            if (found < 0 || !bm_parse_int(value, 1, 1, &flag)) {
                return send_text_status(req, "400 Bad Request", "clear_orientation: 1\n");
            }
            clear = true;
        }
    }
    if (save && clear) {
        return send_text_status(req, "400 Bad Request", "save and clear_orientation together\n");
    }

    sensor_t *s = esp_camera_sensor_get();
    const framesize_t old_size = s->status.framesize;
    const int old_quality = s->status.quality;
    const int old_vflip = s->status.vflip;
    const int old_hmirror = s->status.hmirror;
    const char *failed = NULL;
    if (has_vflip && s->set_vflip(s, vflip) != 0) {
        failed = "vflip";
    }
    if (failed == NULL && has_hmirror && s->set_hmirror(s, hmirror) != 0) {
        failed = "hmirror";
    }
    if (failed == NULL && has_quality && s->set_quality(s, quality) != 0) {
        failed = "quality";
    }
    if (failed == NULL && has_size && s->set_framesize(s, size) != 0) {
        failed = "framesize";
    }
    if (failed != NULL) {
        // A failed setter can leave driver status and sensor registers disagreeing (ov3660.c
        // set_framesize restores only status.framesize on failure), so put the previous mode back.
        // set_framesize goes last: it rewrites the window, size, timing and flip registers.
        int restore = s->set_vflip(s, old_vflip);
        restore |= s->set_hmirror(s, old_hmirror);
        restore |= s->set_quality(s, old_quality);
        restore |= s->set_framesize(s, old_size);
        const bool frames = restore == 0 && settle_after_change();
        const char *outcome = restore != 0 ? "NOT restored" : (frames ? "restored" : "restored, no frame");
        if (restore != 0) {
            orientation_source = "unsaved";
        }
        Serial.printf("BM_CAM CONTROL_FAILED %s previous mode %s\n", failed, outcome);
        char body[112];
        snprintf(body, sizeof(body), "sensor write failed: %s; previous mode %s (size_discards %lu)\n",
                 failed, outcome, (unsigned long)size_discards.load());
        return send_text_status(req, "500 Internal Server Error", body);
    }
    if (has_vflip || has_hmirror) {
        orientation_source = "unsaved";   // before the settle, so a 503 below still reports it
    }
    if ((has_vflip || has_hmirror || has_quality || has_size) && !settle_after_change()) {
        return send_text_status(req, "503 Service Unavailable", "no frame after the change\n");
    }
    if (save) {
        const uint8_t vf = s->status.vflip ? 1 : 0;
        const uint8_t hm = s->status.hmirror ? 1 : 0;
        if (prefs.putUChar("vflip", vf) != 1 || prefs.putUChar("hmirror", hm) != 1) {
            return send_text_status(req, "500 Internal Server Error", "could not save orientation\n");
        }
        orientation_source = "saved";
        Serial.printf("BM_CAM ORIENTATION saved vflip=%u hmirror=%u\n", vf, hm);
    }
    if (clear) {
        prefs.remove("vflip");
        prefs.remove("hmirror");
        // The next boot uses the build values; say "build" only if the image already matches them.
        const bool as_built = s->status.vflip == CAMERA_VFLIP && s->status.hmirror == CAMERA_HMIRROR;
        orientation_source = as_built ? "build" : "unsaved";
        Serial.println("BM_CAM ORIENTATION cleared (build defaults at next boot)");
    }
    if (has_size || has_quality) {
        Serial.printf("BM_CAM MODE %s q=%d\n", mode_name(s->status.framesize), s->status.quality);
    }
    return send_status(req);
}

// Instructor preview page, plus orientation buttons for the printed-text test and the status JSON.
static esp_err_t index_handler(httpd_req_t *req) {
    static const char page[] =
        "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width'>"
        "<title>ESP32-CAM</title></head><body style='font-family:sans-serif'>"
        "<h2>ESP32-CAM preview</h2>"
        "<p><button onclick=\"img.src='/capture?t='+Date.now()\">New photo</button> "
        "<button onclick=\"img.src='/capture?flash=1&t='+Date.now()\">New photo with flash</button></p>"
        "<img id='img' src='/capture' style='max-width:100%'>"
        "<p>Orientation: <button onclick=\"ctl('hmirror=1')\">Mirror on</button> "
        "<button onclick=\"ctl('hmirror=0')\">Mirror off</button> "
        "<button onclick=\"ctl('vflip=1')\">Flip on</button> "
        "<button onclick=\"ctl('vflip=0')\">Flip off</button> "
        "<button onclick=\"ctl('save=1')\">Save orientation</button> "
        "<button onclick=\"ctl('clear_orientation=1')\">Forget saved orientation</button></p>"
        "<p id='warn' style='color:#b00'></p>"
        "<pre id='st' style='white-space:pre-wrap'></pre>"
        "<script>"
        "function show(t){st.textContent=t;warn.textContent=t.indexOf('\"orientation\": \"unsaved\"')>=0?"
        "'Orientation differs from what the next boot will use. Save orientation keeps this one.':''}"
        "function refresh(){fetch('/status').then(r=>r.text()).then(show)}"
        "function ctl(q){fetch('/control?'+q).then(r=>r.text().then(t=>{if(r.ok){show(t)}else{"
        "refresh();setTimeout(()=>{warn.textContent='Error: '+t},300)}"
        "img.src='/capture?t='+Date.now()}))}"
        "refresh()"
        "</script></body></html>";
    httpd_resp_set_type(req, "text/html");
    return httpd_resp_sendstr(req, page);
}

static void start_server() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.stack_size = 8192;         // handlers keep a 640 B JSON buffer and header strings
    config.max_resp_headers = 16;     // /capture sets 10
    config.lru_purge_enable = true;   // reuse sockets that a Wi-Fi stall left half open
    if (httpd_start(&server, &config) != ESP_OK) {
        Serial.println("HTTP server failed to start.");
        return;
    }
    httpd_uri_t index_uri = {"/", HTTP_GET, index_handler, NULL};
    httpd_uri_t capture_uri = {"/capture", HTTP_GET, capture_handler, NULL};
    httpd_uri_t status_uri = {"/status", HTTP_GET, status_handler, NULL};
    httpd_uri_t led_uri = {"/led", HTTP_GET, led_handler, NULL};
    httpd_uri_t control_uri = {"/control", HTTP_GET, control_handler, NULL};
    httpd_register_uri_handler(server, &index_uri);
    httpd_register_uri_handler(server, &capture_uri);
    httpd_register_uri_handler(server, &status_uri);
    httpd_register_uri_handler(server, &led_uri);
    httpd_register_uri_handler(server, &control_uri);
}

// ===== Wi-Fi and serial =====

// Every 10 s, two lines: the project's exact "BM_CAM READY ip=... rssi=... fw=..." (plan M1.T6
// step 8) and the instructor sketch's exact "Photo URL: ..." line (guide Step 9.3). They repeat
// because an RTS pulse does not reset this board, so a line printed only at boot is usually missed
// (course-project/CONTEXT.md, entries "2026-10-06 — M1.T6 upload retry" and "M1.T6 after RST").
// A third line gives the mode, so a serial watcher sees a reboot back to VGA.
static void report() {
    if (camera_ok) {
        sensor_t *s = esp_camera_sensor_get();
        Serial.printf("BM_CAM MODE %s q=%d\n", mode_name(s->status.framesize), s->status.quality);
    }
    if (WiFi.status() == WL_CONNECTED) {
        const String ip = WiFi.localIP().toString();
        const int rssi = WiFi.RSSI();
        Serial.printf("BM_CAM READY ip=%s rssi=%d fw=%s\n", ip.c_str(), rssi, BM_FW);
        Serial.printf("Photo URL: http://%s/capture | Wi-Fi %d dBm | %lu photos served\n",
                      ip.c_str(), rssi, (unsigned long)frames_served.load());
    } else {
        Serial.printf("BM_CAM WIFI_DOWN | %lu photos served\n", (unsigned long)frames_served.load());
    }
}

// The core already reconnects after most disconnect reasons (STA.cpp:66-91, 139-173). After 20 s
// down this also restarts the connection, then every 20 s while it stays down; a restart can abort
// a join that is in progress, which costs one join (a few seconds).
static void wifi_supervise(uint32_t now) {
    static bool was_up = false;
    static uint32_t down_since = 0;
    static uint32_t last_retry = 0;
    const bool up = WiFi.status() == WL_CONNECTED;
    if (up) {
        if (!was_up) {
            Serial.printf("Connected. Photo URL: http://%s/capture\n",
                          WiFi.localIP().toString().c_str());
            report();
        }
        was_up = true;
        return;
    }
    if (was_up) {
        Serial.println("BM_CAM WIFI_LOST");
        was_up = false;
        down_since = now;
        last_retry = now;
    }
    if (now - down_since >= BM_WIFI_FORCE_RETRY_MS && now - last_retry >= BM_WIFI_FORCE_RETRY_MS) {
        last_retry = now;
        Serial.println("BM_CAM WIFI_RETRY");
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println();
    Serial.println("ESP32-CAM photo server starting. fw=" BM_FW);
    pinMode(FLASH_LED_GPIO_NUM, OUTPUT);
    digitalWrite(FLASH_LED_GPIO_NUM, LOW);
    led_lock = xSemaphoreCreateMutex();
    prefs.begin("bm_cam", false);

    // A camera failure no longer stops here: Wi-Fi and /status still come up, and /capture says 503.
    camera_ok = start_camera();

    WiFi.persistent(false);                         // do not rewrite the credentials to flash
    WiFi.setHostname("bm-cam");
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);                           // answer photo requests quickly
    WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);      // see every mesh node ...
    WiFi.setSortMethod(WIFI_CONNECT_AP_BY_SIGNAL);  // ... and join the strongest
    Serial.println("Connecting to Wi-Fi (network name not printed).");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    start_server();
}

void loop() {
    static uint32_t last_report = 0;
    const uint32_t now = millis();
    if (led_auto_off()) {
        Serial.println("BM_CAM LED_AUTO_OFF");
    }
    wifi_supervise(now);
    if (now - last_report >= BM_REPORT_MS) {
        last_report = now;
        report();
    }
    delay(100);
}
