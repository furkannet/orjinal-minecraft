#!/usr/bin/env python3
"""Orijinal Minecraft çok oyunculu sunucusu (WebSocket rölesi).

Kullanım:  pip install websockets  &&  python3 server.py [port]
Varsayılan port: 8765.

Odalar:
  sky     -> Skyblock (tek blok). Tohum sabittir.
  normal  -> Normal dünya. Tohumu ilk giren oyuncu belirler.

Sunucu yalnızca blok değişikliklerini (mods) ve oyuncu konumlarını tutar;
arazi her istemcide aynı tohumdan üretilir.
"""
import asyncio
import json
import os
import sys

import websockets

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8765))
CHUNK_Y = 150
SKY_SEED = 424242
ROOMS = ("sky", "normal")

rooms = {r: {"seed": SKY_SEED if r == "sky" else None, "mods": {}, "players": {}, "clients": set(),
             "slots": {}, "byname": {}} for r in ROOMS}  # slots: ada no -> isim (yalnızca sky odası)
SKY_SLOTS = 16  # Skyblock'ta en fazla 16 ayrı ada (4x4 ızgara)
next_id = 1


async def send(ws, msg):
    await ws.send(json.dumps(msg))


async def broadcast(room, msg, skip=None):
    data = json.dumps(msg)
    for c in list(room["clients"]):
        if c is not skip:
            try:
                await c.send(data)
            except websockets.ConnectionClosed:
                pass


def valid_block(x, y, z, bid):
    return all(isinstance(v, int) for v in (x, y, z, bid)) and abs(x) < 10**6 and abs(z) < 10**6 \
        and 0 <= y < CHUNK_Y and 0 <= bid < 256


async def handler(ws):
    global next_id
    room = None
    pid = None
    try:
        async for raw in ws:
            try:
                m = json.loads(raw)
            except (ValueError, TypeError):
                continue
            t = m.get("t")

            if t == "hello" and room is None:
                name = str(m.get("name", "Oyuncu"))[:16]
                rname = m.get("room") if m.get("room") in ROOMS else "normal"
                room = rooms[rname]
                if room["seed"] is None:
                    seed = m.get("seed")
                    room["seed"] = seed if isinstance(seed, int) else 123456
                pid = next_id
                next_id += 1
                slot = -1
                if rname == "sky":
                    if name in room["byname"]:
                        slot = room["byname"][name]
                    else:
                        free = [i for i in range(SKY_SLOTS) if i not in room["slots"]]
                        if free:
                            slot = free[0]
                            room["slots"][slot] = name
                            room["byname"][name] = slot
                            await broadcast(room, {"t": "slot", "i": slot, "name": name}, skip=ws)
                mods = []
                for key, bid in room["mods"].items():
                    x, y, z = key.split(",")
                    mods += [int(x), int(y), int(z), bid]
                room["clients"].add(ws)
                room["players"][pid] = {"id": pid, "name": name, "x": 8.5, "y": 0, "z": 8.5, "yaw": 0, "pitch": 0}
                await send(ws, {"t": "welcome", "id": pid, "room": rname, "seed": room["seed"], "mods": mods,
                          "slot": slot, "slots": {str(i): n for i, n in room["slots"].items()},
                          "players": [p for p in room["players"].values() if p["id"] != pid]})
                await broadcast(room, {"t": "join", **room["players"][pid]}, skip=ws)

            elif room is None:
                continue

            elif t == "p":
                p = room["players"].get(pid)
                if p:
                    for k in ("x", "y", "z", "yaw", "pitch"):
                        if isinstance(m.get(k), (int, float)):
                            p[k] = m[k]
                    await broadcast(room, {"t": "p", "id": pid, "x": p["x"], "y": p["y"], "z": p["z"],
                                           "yaw": p["yaw"], "pitch": p["pitch"]}, skip=ws)

            elif t == "reset" and room is not None and room is rooms["sky"]:
                # Skyblock adasını sıfırla: blok değişikliklerini temizle, herkese bildir (ada istemcide yeniden kurulur)
                room["mods"].clear()
                await broadcast(room, {"t": "reset"})

            elif t == "bs":
                flat = m.get("l") or []
                out = []
                for i in range(0, len(flat) - 3, 4):
                    x, y, z, bid = flat[i:i + 4]
                    if valid_block(x, y, z, bid):
                        room["mods"][f"{x},{y},{z}"] = bid
                        out += [x, y, z, bid]
                if out:
                    await broadcast(room, {"t": "bs", "l": out}, skip=ws)
    except websockets.ConnectionClosed:
        pass
    finally:
        if room is not None:
            room["clients"].discard(ws)
            room["players"].pop(pid, None)
            await broadcast(room, {"t": "leave", "id": pid})


async def main():
    print(f"Orijinal Minecraft sunucusu: ws://0.0.0.0:{PORT}  (odalar: {', '.join(ROOMS)})", flush=True)
    async with websockets.serve(handler, "0.0.0.0", PORT, max_size=2**22):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
