#!/usr/bin/env python3
"""Read one serial port for a fixed time and exit.

Creates the port with serial.Serial(), sets DTR and RTS false before open()
(pyserial 3.5 applies those states during open; on an ESP32 base board they
drive IO0 and EN), optionally pulses RTS for a reset, then prints each
received line with a host timestamp.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the M1 serial reader.
Derived from: none.
"""
import argparse
import datetime
import sys
import time

import serial


def build_parser():
    parser = argparse.ArgumentParser(description="Read a serial port for a fixed number of seconds.")
    parser.add_argument("port")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--esp32-reset", action="store_true")
    parser.add_argument("--out", default="")
    return parser


def open_port(port, baud):
    """Open with DTR and RTS held false so open() does not strap the ESP32."""
    if baud == 1200:
        raise ValueError("refusing 1200 baud")
    link = serial.Serial()
    link.port = port
    link.baudrate = baud
    link.timeout = 0.2
    link.dtr = False
    link.rts = False
    link.open()
    return link


def format_line(raw):
    text = raw.decode("utf-8", errors="replace").rstrip("\r")
    stamp = datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
    return "{0} {1}".format(stamp, text)


def read_for(link, seconds, write):
    """Print every complete line received until seconds have elapsed."""
    deadline = time.monotonic() + seconds
    pending = b""
    while time.monotonic() < deadline:
        chunk = link.read(4096)
        if not chunk:
            continue
        pending += chunk
        while b"\n" in pending:
            raw, pending = pending.split(b"\n", 1)
            write(format_line(raw))
    if pending:
        write(format_line(pending))


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        link = open_port(args.port, args.baud)
    except (OSError, serial.SerialException, ValueError) as exc:
        print("serial_read: {0}".format(exc), file=sys.stderr)
        return 1
    out_file = None
    try:
        if args.esp32_reset:
            link.rts = True
            time.sleep(0.1)
            link.rts = False
        if args.out:
            out_file = open(args.out, "w", encoding="utf-8")

        def write(line):
            print(line, flush=True)
            if out_file is not None:
                out_file.write(line + "\n")
                out_file.flush()

        read_for(link, args.seconds, write)
    finally:
        if out_file is not None:
            out_file.close()
        link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
