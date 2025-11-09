# bt_bridge.py
import bluetooth
import os
import time
import glob
import struct
import traceback

# --- Bluetooth config (must match your Android app) ---
UUID = "00001101-0000-1000-8000-00805F9B34FB"
PORT = 1
SIGNAL_EXPECTED = "TAKE_PICTURE_SIGNAL"  # Kotlin sends "TAKE_PICTURE_SIGNAL\n"

# --- Capture/transfer config ---
IMAGE_DIR = "."                         # folder where capture_*.png are saved
GLOB_PATTERN = "capture_*.png"
LATEST_CANDIDATES = [                   # optional stable paths
    "/tmp/capture_latest.png",
    "/tmp/capture.png",
    "/tmp/capture.jpg",
]
FLAG = "/tmp/snap.flag"                 # file the capture script is watching
MIN_VALID_SIZE = 1024                   # bytes
NEW_IMAGE_TIMEOUT = 6.0                 # seconds to wait for a fresh image
READ_STABLE_DELAY = 0.15                # seconds to re-check file size before reading

def _find_latest_file():
    """Return path to the newest valid capture file (or None)."""
    candidates = []
    # include stable candidates first
    for p in LATEST_CANDIDATES:
        if os.path.exists(p):
            try:
                sz = os.path.getsize(p)
                if sz >= MIN_VALID_SIZE:
                    candidates.append((os.path.getmtime(p), p))
            except Exception:
                pass
    # then globbed captures
    try:
        for p in glob.glob(os.path.join(IMAGE_DIR, GLOB_PATTERN)):
            try:
                sz = os.path.getsize(p)
                if sz >= MIN_VALID_SIZE:
                    candidates.append((os.path.getmtime(p), p))
            except Exception:
                pass
    except Exception:
        pass

    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]

def _latest_mtime():
    p = _find_latest_file()
    try:
        return os.path.getmtime(p) if p and os.path.exists(p) else 0
    except Exception:
        return 0

def _read_file_bytes_stable(path):
    """Read file after ensuring size has stabilized."""
    try:
        s1 = os.path.getsize(path)
        time.sleep(READ_STABLE_DELAY)
        s2 = os.path.getsize(path)
        if s2 >= MIN_VALID_SIZE and s1 == s2:
            with open(path, "rb") as f:
                return f.read()
    except Exception as e:
        print(f"File read error ({path}): {e}")
    return None

def _trigger_new_capture_and_get_image():
    """Create the flag, wait for a strictly newer image, then read it."""
    before = _latest_mtime()
    # create trigger flag
    try:
        open(FLAG, "w").close()
        print(f"[BT] Created trigger flag {FLAG}")
    except Exception as e:
        print(f"[BT] Failed to create trigger flag: {e}")

    deadline = time.time() + NEW_IMAGE_TIMEOUT
    newest = None
    while time.time() < deadline:
        p = _find_latest_file()
        if p:
            try:
                mt = os.path.getmtime(p)
            except Exception:
                mt = 0
            if mt > before:
                newest = p
                break
        time.sleep(0.15)

    if not newest:
        print("[BT] No new image detected within timeout.")
        return None

    print(f"[BT] New image detected: {newest}")
    return _read_file_bytes_stable(newest)

def send_with_size_header(sock, payload: bytes, error_msg: str = None):
    """
    Protocol to match the Android client:
      - 4-byte big-endian unsigned int: payload size N
      - if N>0: N bytes of image; if N==0: optional ASCII error text
    """
    if payload and len(payload) > 0:
        header = struct.pack(">I", len(payload))
        sock.sendall(header)
        sock.sendall(payload)
    else:
        header = struct.pack(">I", 0)
        sock.sendall(header)
        if error_msg:
            try:
                sock.sendall(error_msg.encode("utf-8"))
            except Exception:
                pass

def run_server():
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_sock.bind(("", PORT))
    server_sock.listen(1)

    bluetooth.advertise_service(
        server_sock,
        "UrbanSightBTServer",
        service_id=UUID,
        service_classes=[UUID, bluetooth.SERIAL_PORT_CLASS],
        profiles=[bluetooth.SERIAL_PORT_PROFILE],
    )

    print(f"[BT] Waiting for connection on RFCOMM channel {PORT} with UUID {UUID}")

    while True:
        client_sock = None
        try:
            client_sock, client_info = server_sock.accept()
            print(f"[BT] Accepted connection from {client_info[0]}")

            data = client_sock.recv(1024) or b""
            txt = data.decode("utf-8", errors="ignore").strip()

            if txt.startswith(SIGNAL_EXPECTED) or txt == "" or txt == "\n":
                print("[BT] Trigger received.")
            else:
                print(f"[BT] Unexpected signal: {txt!r}. Proceeding anyway...")

            # Ask capture script for a FRESH photo, then send it
            image_bytes = _trigger_new_capture_and_get_image()

            if image_bytes and len(image_bytes) >= MIN_VALID_SIZE:
                send_with_size_header(client_sock, image_bytes)
                print(f"[BT] Sent image ({len(image_bytes)} bytes) with 4-byte header.")
            else:
                send_with_size_header(client_sock, b"", "ERROR: No image available.")
                print("[BT] Sent error (size=0).")

            client_sock.close()
            print("[BT] Client disconnected. Waiting for next connection...")

        except bluetooth.BluetoothError as e:
            print(f"[BT] Bluetooth Error: {e}. Waiting for new connection...")
            if client_sock:
                try: client_sock.close()
                except Exception: pass
            time.sleep(2)
        except Exception as e:
            print(f"[BT] General Error: {e}")
            traceback.print_exc()
            if client_sock:
                try: client_sock.close()
                except Exception: pass
            time.sleep(2)

if __name__ == "__main__":
    run_server()
