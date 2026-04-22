import threading
import time
import webbrowser

import uvicorn

from app.main import app


URL = "http://127.0.0.1:8000"


def open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def main():
    print(f"starting chirp on {URL}")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
