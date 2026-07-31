"""Standalone test bridge: WinPTY + frozen --cli, serves a config-comparison page."""
import sys, os, json, asyncio, threading, http.server, socketserver, functools
sys.path.insert(0, r"C:\Scripts\LoneWolf_ActionAssistant_SAA")
import winpty
from websockets.asyncio.server import serve
from runtime_paths import PATHS

EXE = r"C:\Scripts\LoneWolf_ActionAssistant_SAA\dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant.exe"
HTTP_PORT, WS_PORT = 8899, 8900

def command():
    return [EXE, "--cli", "--save-dir", str(PATHS.saves), "--data-dir", str(PATHS.resource_data),
            "--state-data-dir", str(PATHS.user_data), "--books-dir", str(PATHS.books_lw)]

async def session(ws):
    loop = asyncio.get_running_loop()
    env = dict(os.environ); env.pop("LONEWOLF_SAA_CHEAT_URL", None); env.pop("LONEWOLF_SAA_CHEAT_TOKEN", None)
    p = winpty.PtyProcess.spawn(command(), dimensions=(30,100), cwd=str(PATHS.user_root), env=env, backend=winpty.Backend.WinPTY)
    q = asyncio.Queue(); stop = threading.Event()
    def rd():
        while not stop.is_set():
            try: d = p.read(4096)
            except Exception: break
            if d: asyncio.run_coroutine_threadsafe(q.put(d), loop)
            elif not p.isalive(): break
        asyncio.run_coroutine_threadsafe(q.put(None), loop)
    threading.Thread(target=rd, daemon=True).start()
    async def out():
        while True:
            d = await q.get()
            if d is None: break
            try: await ws.send(d)
            except Exception: break
    async def inp():
        try:
            async for m in ws:
                t = m if isinstance(m,str) else m.decode("utf-8","replace")
                if t.startswith("\x00"):
                    try:
                        o=json.loads(t[1:])
                        if o.get("type")=="resize": p.setwinsize(max(1,int(o["rows"])),max(1,int(o["cols"])))
                    except Exception: pass
                else: p.write("\r\n" if t=="\r" else t)
        except Exception: pass
    ot=asyncio.create_task(out()); it=asyncio.create_task(inp())
    await asyncio.wait([ot,it], return_when=asyncio.FIRST_COMPLETED)
    stop.set(); ot.cancel(); it.cancel()
    try: p.terminate(force=True)
    except Exception: pass

def http_thread():
    d = os.path.dirname(os.path.abspath(__file__))
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=d)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", HTTP_PORT), h) as s:
        print(f"HTTP  http://127.0.0.1:{HTTP_PORT}/termcheck.html", flush=True); s.serve_forever()

async def main():
    threading.Thread(target=http_thread, daemon=True).start()
    print(f"WS    ws://127.0.0.1:{WS_PORT}", flush=True)
    print("Open the HTTP URL above in Edge/Chrome. Ctrl+C here to stop.", flush=True)
    async with serve(session, "127.0.0.1", WS_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("stopped")
