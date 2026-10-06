"""Start the server and open the sites in the browser. Used by start.bat.

    python -m app.run
"""
import os
import sys
import threading
import time
import urllib.request
import webbrowser

import uvicorn

HOST, PORT = "127.0.0.1", int(os.environ.get("CRUNCH_PORT", "8000"))
URL = f"http://{HOST}:{PORT}"
OPEN_BROWSER = not os.environ.get("CRUNCH_NO_BROWSER")


def _running() -> bool:
    try:
        urllib.request.urlopen(URL + "/api/health", timeout=1)
        return True
    except OSError:
        return False


def _open_when_ready() -> None:
    for _ in range(80):
        if _running():
            webbrowser.open(URL + "/")
            webbrowser.open(URL + "/admin/")
            return
        time.sleep(0.5)


if __name__ == "__main__":
    if _running():
        print("\n  Crunch is already running (another window started it). Opening it in your browser.\n", flush=True)
        if OPEN_BROWSER:
            webbrowser.open(URL + "/admin/")
        sys.exit(0)
    print(f"\n  Buyer site:   {URL}/\n  Seller site:  {URL}/seller/\n  Admin site:   {URL}/admin/\n", flush=True)
    print("  Keep this window open while you use the sites. Close it to stop the server.\n", flush=True)
    if OPEN_BROWSER:
        threading.Thread(target=_open_when_ready, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="warning")
