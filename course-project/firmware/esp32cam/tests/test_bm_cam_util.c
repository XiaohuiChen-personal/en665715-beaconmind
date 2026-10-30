/*
Host test for bm_cam_v02/bm_cam_util.h: the JPEG size reader on real ESP32-CAM frames and on
crafted buffers, and the query helpers. Run by run_host_tests.sh (Mac or Spark host, plain cc).

Usage: test_bm_cam_util <jpeg> <width> <height> [<jpeg> <width> <height> ...]

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-10-25: wrote this test.
*/
#include <stdio.h>
#include <stdlib.h>

#include "../bm_cam_v02/bm_cam_util.h"

static int failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            failures++;                                                    \
        }                                                                  \
    } while (0)

static unsigned char *read_file(const char *path, size_t *len) {
    FILE *f = fopen(path, "rb");
    if (f == NULL) {
        return NULL;
    }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    unsigned char *buf = (unsigned char *)malloc((size_t)n);
    if (buf != NULL && fread(buf, 1, (size_t)n, f) != (size_t)n) {
        free(buf);
        buf = NULL;
    }
    fclose(f);
    *len = (size_t)n;
    return buf;
}

static void test_real_frames(int argc, char **argv) {
    for (int i = 1; i + 2 < argc; i += 3) {
        size_t len = 0;
        unsigned char *buf = read_file(argv[i], &len);
        CHECK(buf != NULL);
        if (buf == NULL) {
            continue;
        }
        int w = 0, h = 0;
        bool ok = bm_jpeg_size(buf, len, &w, &h);
        int want_w = atoi(argv[i + 1]);
        int want_h = atoi(argv[i + 2]);
        printf("%s: ok=%d %dx%d (want %dx%d)\n", argv[i], ok, w, h, want_w, want_h);
        CHECK(ok && w == want_w && h == want_h);
        /* A single real JPEG is one complete image. */
        CHECK(bm_jpeg_first_image_len(buf, len) == len);
        /* Two copies with zero padding between them, as the driver delivered on 2026-10-25: the first
           image ends where the first copy ends. A truncated buffer has no complete image. */
        unsigned char *two = (unsigned char *)malloc(2 * len + 1024);
        if (two != NULL) {
            memcpy(two, buf, len);
            memset(two + len, 0, 1024);
            memcpy(two + len + 1024, buf, len);
            CHECK(bm_jpeg_first_image_len(two, 2 * len + 1024) == len);
            CHECK(bm_jpeg_first_image_len(two, len - 1) == 0);
            free(two);
        }
        /* Every truncation of the header region must fail cleanly or give the same answer. */
        for (size_t cut = 0; cut < 700 && cut < len; ++cut) {
            int tw = 0, th = 0;
            bool tok = bm_jpeg_size(buf, cut, &tw, &th);
            CHECK(!tok || (tw == want_w && th == want_h));
        }
        free(buf);
    }
}

static void test_crafted(void) {
    int w = -1, h = -1;
    /* SOI, APP0 (len 4), SOF0 for 640 x 480. */
    const uint8_t good[] = {0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x04, 0x00, 0x00, 0xFF, 0xC0, 0x00, 0x11,
                            0x08, 0x01, 0xE0, 0x02, 0x80, 0x03, 0x01, 0x22, 0x00, 0x02, 0x11, 0x01,
                            0x03, 0x11, 0x01};
    CHECK(bm_jpeg_size(good, sizeof(good), &w, &h) && w == 640 && h == 480);
    /* DHT (C4) before SOF0 must be skipped, not read as a frame header. */
    const uint8_t dht_first[] = {0xFF, 0xD8, 0xFF, 0xC4, 0x00, 0x04, 0x12, 0x34, 0xFF, 0xC0, 0x00,
                                 0x08, 0x08, 0x04, 0xB0, 0x06, 0x40, 0x01};
    CHECK(bm_jpeg_size(dht_first, sizeof(dht_first), &w, &h) && w == 1600 && h == 1200);
    /* Fill bytes before a marker are allowed. */
    const uint8_t fill[] = {0xFF, 0xD8, 0xFF, 0xFF, 0xC0, 0x00, 0x08, 0x08, 0x02, 0x58, 0x03, 0x20,
                            0x01};
    CHECK(bm_jpeg_size(fill, sizeof(fill), &w, &h) && w == 800 && h == 600);
    /* Not a JPEG, SOS before SOF, a length running past the end, a zero size. */
    const uint8_t not_jpeg[] = {0x89, 0x50, 0x4E, 0x47};
    CHECK(!bm_jpeg_size(not_jpeg, sizeof(not_jpeg), &w, &h));
    const uint8_t sos_first[] = {0xFF, 0xD8, 0xFF, 0xDA, 0x00, 0x08, 0, 0, 0, 0, 0, 0};
    CHECK(!bm_jpeg_size(sos_first, sizeof(sos_first), &w, &h));
    const uint8_t overrun[] = {0xFF, 0xD8, 0xFF, 0xE0, 0x10, 0x00, 0x00, 0x00};
    CHECK(!bm_jpeg_size(overrun, sizeof(overrun), &w, &h));
    const uint8_t zero[] = {0xFF, 0xD8, 0xFF, 0xC0, 0x00, 0x08, 0x08, 0x00, 0x00, 0x02, 0x80, 0x01};
    CHECK(!bm_jpeg_size(zero, sizeof(zero), &w, &h));
    const uint8_t short_sof[] = {0xFF, 0xD8, 0xFF, 0xC0, 0x00, 0x05, 0x08, 0x01, 0xE0};
    CHECK(!bm_jpeg_size(short_sof, sizeof(short_sof), &w, &h));
    CHECK(!bm_jpeg_size(NULL, 10, &w, &h));

    /* First-image length on crafted data: stuffed FF 00 and RST markers inside the scan are not the end. */
    const uint8_t scan[] = {0xFF, 0xD8, 0xFF, 0xDA, 0x00, 0x02, 0x12, 0xFF, 0x00, 0x34, 0xFF, 0xD3,
                            0x56, 0xFF, 0xD9, 0x00, 0x00, 0xFF, 0xD8, 0xFF, 0xD9};
    CHECK(bm_jpeg_first_image_len(scan, sizeof(scan)) == 15);
    const uint8_t no_end[] = {0xFF, 0xD8, 0xFF, 0xDA, 0x00, 0x02, 0x12, 0x34};
    CHECK(bm_jpeg_first_image_len(no_end, sizeof(no_end)) == 0);
    CHECK(bm_jpeg_first_image_len(not_jpeg, sizeof(not_jpeg)) == 0);
    CHECK(bm_jpeg_first_image_len(NULL, 10) == 0);
}

static void test_query(void) {
    static const char *const keys[] = {"framesize", "quality", "vflip", "hmirror", "save",
                                       "clear_orientation", "t"};
    const size_t n = sizeof(keys) / sizeof(keys[0]);
    char bad[24];
    CHECK(bm_query_keys_allowed("framesize=uxga&quality=10", keys, n, bad, sizeof(bad)));
    CHECK(bm_query_keys_allowed("hmirror=1&save=1&t=1761426000000", keys, n, bad, sizeof(bad)));
    CHECK(bm_query_keys_allowed("", keys, n, bad, sizeof(bad)));
    /* Empty pieces are refused: IDF's parser would miss the key after "&&" or a leading "&". */
    CHECK(!bm_query_keys_allowed("vflip=0&&hmirror=1", keys, n, bad, sizeof(bad)) &&
          strcmp(bad, "") == 0);
    CHECK(!bm_query_keys_allowed("hmirror=1&&save=1", keys, n, bad, sizeof(bad)));
    CHECK(!bm_query_keys_allowed("&hmirror=1", keys, n, bad, sizeof(bad)));
    CHECK(!bm_query_keys_allowed("t=1&&vflip=1", keys, n, bad, sizeof(bad)));
    /* A trailing '&' is harmless (IDF still finds every key) and stays allowed. */
    CHECK(bm_query_keys_allowed("hmirror=1&", keys, n, bad, sizeof(bad)));
    CHECK(!bm_query_keys_allowed("framesize=vga&frame=1", keys, n, bad, sizeof(bad)) &&
          strcmp(bad, "frame") == 0);
    CHECK(!bm_query_keys_allowed("qualityx=10", keys, n, bad, sizeof(bad)) &&
          strcmp(bad, "qualityx") == 0);
    CHECK(!bm_query_keys_allowed("flash", keys, n, bad, sizeof(bad)) && strcmp(bad, "flash") == 0);
    /* A known key without '=' is refused too (IDF would read past the '&'). */
    CHECK(!bm_query_keys_allowed("hmirror=1&save", keys, n, bad, sizeof(bad)) &&
          strcmp(bad, "save") == 0);
    CHECK(!bm_query_keys_allowed("save&hmirror=1", keys, n, bad, sizeof(bad)) &&
          strcmp(bad, "save") == 0);
    CHECK(!bm_query_keys_allowed("t&vflip=1", keys, n, bad, sizeof(bad)) && strcmp(bad, "t") == 0);
    /* An empty value is a key with '=' and passes here; the value check then refuses it. */
    CHECK(bm_query_keys_allowed("quality=", keys, n, bad, sizeof(bad)));
    /* A piece that is only "=value" has an empty key and is refused. */
    CHECK(!bm_query_keys_allowed("=1", keys, n, bad, sizeof(bad)) && strcmp(bad, "") == 0);
    char tiny[4];
    CHECK(!bm_query_keys_allowed("abcdefgh=1", keys, n, tiny, sizeof(tiny)) &&
          strcmp(tiny, "abc") == 0);

    int v = -1;
    CHECK(bm_parse_int("10", 10, 63, &v) && v == 10);
    CHECK(bm_parse_int("63", 10, 63, &v) && v == 63);
    CHECK(!bm_parse_int("9", 10, 63, &v));
    CHECK(!bm_parse_int("64", 10, 63, &v));
    CHECK(!bm_parse_int("", 0, 1, &v));
    CHECK(!bm_parse_int("1x", 0, 1, &v));
    CHECK(!bm_parse_int("-1", 0, 1, &v));
    CHECK(!bm_parse_int(" 1", 0, 1, &v));
    CHECK(!bm_parse_int("99999999999", 0, 100, &v));
    CHECK(bm_timeval_us(3, 250000) == 3250000LL);
}

int main(int argc, char **argv) {
    test_crafted();
    test_query();
    test_real_frames(argc, argv);
    if (failures == 0) {
        printf("OK: all bm_cam_util checks passed\n");
        return 0;
    }
    printf("FAILED: %d check(s)\n", failures);
    return 1;
}
