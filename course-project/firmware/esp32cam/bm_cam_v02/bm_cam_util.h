/*
bm_cam_util.h: helpers for bm_cam-0.2 that use no ESP-IDF or Arduino API, so the same code is
compiled into the sketch and into the host test (course-project/firmware/esp32cam/tests/).

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: wrote these helpers and their host test.
Derived from: ITU-T T.81 (JPEG), Annex B marker and SOF layout (reimplemented, not copied).
*/
#ifndef BM_CAM_UTIL_H
#define BM_CAM_UTIL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Width and height from the first SOF (start-of-frame) marker of a JPEG.
   The driver labels every frame with the current frame size (esp_camera.c:396-398), even a frame
   that was read out before a frame-size switch, so the sketch reads the real size from the JPEG.
   Returns false if the buffer does not start with SOI or no SOF comes before SOS or the end. */
static inline bool bm_jpeg_size(const uint8_t *buf, size_t len, int *width, int *height) {
    if (buf == NULL || len < 4 || buf[0] != 0xFF || buf[1] != 0xD8) {
        return false;
    }
    size_t i = 2;
    while (i + 4 <= len) {
        if (buf[i] != 0xFF) {
            return false;                       /* every segment starts with a marker */
        }
        uint8_t marker = buf[i + 1];
        if (marker == 0xFF) {                   /* fill byte before a marker */
            i += 1;
            continue;
        }
        if (marker == 0x01 || (marker >= 0xD0 && marker <= 0xD7)) {
            i += 2;                             /* TEM and RSTn carry no length */
            continue;
        }
        if (marker == 0xD8 || marker == 0xD9 || marker == 0xDA) {
            return false;                       /* SOI again, EOI or SOS before any SOF */
        }
        size_t seglen = ((size_t)buf[i + 2] << 8) | buf[i + 3];
        if (seglen < 2 || i + 2 + seglen > len) {
            return false;
        }
        bool sof = marker >= 0xC0 && marker <= 0xCF && marker != 0xC4 && marker != 0xC8 &&
                   marker != 0xCC;               /* C4 = DHT, C8 = JPG, CC = DAC */
        if (sof) {
            if (seglen < 8) {                   /* length, precision, height, width, components */
                return false;
            }
            int h = ((int)buf[i + 5] << 8) | buf[i + 6];
            int w = ((int)buf[i + 7] << 8) | buf[i + 8];
            if (w <= 0 || h <= 0) {
                return false;
            }
            *width = w;
            *height = h;
            return true;
        }
        i += 2 + seglen;
    }
    return false;
}

/* Length of the first complete JPEG in buf (SOI through the first EOI after SOS), or 0 if there is
   none. On this board the driver sometimes leaves several frames in one buffer (it misses the end
   of a frame; seen 2026-10-25: 5 of 40 VGA buffers held 2-4 images separated by zero bytes), and it
   trims the buffer at the LAST EOI, so the sketch sends only the first image. In the entropy-coded
   data a 0xFF is followed by 0x00 (stuffing) or RSTn, never by 0xD9, so the first FF D9 ends it. */
static inline size_t bm_jpeg_first_image_len(const uint8_t *buf, size_t len) {
    if (buf == NULL || len < 4 || buf[0] != 0xFF || buf[1] != 0xD8) {
        return 0;
    }
    size_t i = 2;
    while (i + 4 <= len) {                      /* walk the header segments to SOS */
        if (buf[i] != 0xFF) {
            return 0;
        }
        uint8_t marker = buf[i + 1];
        if (marker == 0xFF) {
            i += 1;
            continue;
        }
        if (marker == 0x01 || (marker >= 0xD0 && marker <= 0xD7)) {
            i += 2;
            continue;
        }
        if (marker == 0xD8 || marker == 0xD9) {
            return 0;
        }
        size_t seglen = ((size_t)buf[i + 2] << 8) | buf[i + 3];
        if (seglen < 2 || i + 2 + seglen > len) {
            return 0;
        }
        i += 2 + seglen;
        if (marker == 0xDA) {                   /* SOS: entropy-coded data follows */
            for (size_t k = i; k + 1 < len; ++k) {
                if (buf[k] == 0xFF && buf[k + 1] == 0xD9) {
                    return k + 2;
                }
            }
            return 0;
        }
    }
    return 0;
}

/* Parses a whole string as a decimal integer in [lo, hi]. No sign, spaces or other characters. */
static inline bool bm_parse_int(const char *s, int lo, int hi, int *out) {
    if (s == NULL || *s == '\0') {
        return false;
    }
    long v = 0;
    for (const char *p = s; *p != '\0'; ++p) {
        if (*p < '0' || *p > '9') {
            return false;
        }
        v = v * 10 + (*p - '0');
        if (v > 1000000L) {
            return false;
        }
    }
    if (v < lo || v > hi) {
        return false;
    }
    *out = (int)v;
    return true;
}

/* True when every piece of a URL query ("a=1&b=2") is "key=value" with key one of
   allowed[0..n_allowed-1]. IDF's httpd_query_key_value finds a key only right after the start or
   a single '&', and looks for '=' past the next '&'; so a key with no '=' ("save&hmirror=1") or an
   empty piece ("a=1&&b=2", "&a=1") makes it miss keys and the request quietly does less. Both are
   refused here. A trailing '&' is harmless and allowed. On false, the offending key (empty for an
   empty piece) is copied into bad (cut to badlen - 1 characters). */
static inline bool bm_query_keys_allowed(const char *query, const char *const *allowed,
                                         size_t n_allowed, char *bad, size_t badlen) {
    const char *p = query;
    while (p != NULL && *p != '\0') {
        const char *end = strchr(p, '&');
        size_t piece = end != NULL ? (size_t)(end - p) : strlen(p);
        const char *eq = (const char *)memchr(p, '=', piece);
        size_t klen = eq != NULL ? (size_t)(eq - p) : piece;
        bool known = false;
        for (size_t k = 0; piece > 0 && eq != NULL && k < n_allowed; ++k) {
            if (strlen(allowed[k]) == klen && strncmp(allowed[k], p, klen) == 0) {
                known = true;
                break;
            }
        }
        if (!known) {
            if (bad != NULL && badlen > 0) {
                size_t c = klen < badlen - 1 ? klen : badlen - 1;
                memcpy(bad, p, c);
                bad[c] = '\0';
            }
            return false;
        }
        p = end != NULL ? end + 1 : NULL;
    }
    return true;
}

/* Frame timestamp (struct timeval fields) as microseconds since boot, the esp_timer clock. */
static inline int64_t bm_timeval_us(int64_t tv_sec, int64_t tv_usec) {
    return tv_sec * 1000000LL + tv_usec;
}

#endif /* BM_CAM_UTIL_H */
