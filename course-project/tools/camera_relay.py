#!/usr/bin/env python3
"""TCP relay on the Spark host: Docker bridge gateway 172.17.0.1:18080 -> the ESP32-CAM on the Spark's access point.

Why (CONTEXT.md 2026-11-02): a container cannot open a connection into the access point's subnet (the camera answers
"connection refused" to a container while the Spark itself reaches it), most likely because NetworkManager's shared
mode rejects forwarded connections. A host process is not forwarded, so a relay needs no firewall change and no sudo.
It listens only on the Docker bridge, not on the Wi-Fi. Containers then use http://172.17.0.1:18080/... .

Usage (Spark host): python3 course-project/tools/camera_relay.py <camera ip> [listen_host] [listen_port] [target_port]
The approach follows the Module 9 relay in the private course repo (discussions/module9/tools/camera_relay.py); this
file is a separate implementation for the project.

AI-assisted: Claude Opus 5.5 via Claude Code, 2026-11-10: wrote this relay.
"""
import asyncio
import sys

async def pipe(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


def handler(target, target_port):
    async def handle(client_r, client_w):
        try:
            cam_r, cam_w = await asyncio.wait_for(asyncio.open_connection(target, target_port), timeout=5)
        except Exception as exc:  # report and drop this connection only
            print("relay: cannot reach %s:%d (%s)" % (target, target_port, type(exc).__name__), flush=True)
            client_w.close()
            return
        await asyncio.gather(pipe(client_r, cam_w), pipe(cam_r, client_w))
    return handle


async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "10.42.0.89"
    host = sys.argv[2] if len(sys.argv) > 2 else "172.17.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 18080
    target_port = int(sys.argv[4]) if len(sys.argv) > 4 else 80
    server = await asyncio.start_server(handler(target, target_port), host, port)
    print("relay %s:%d -> %s:%d" % (host, port, target, target_port), flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
