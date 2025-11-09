# bt_bridge.py
import bluetooth
import os
import time
import glob
import struct
import traceback
import pwd

# --- Bluetooth config (must match Android app) ---
UUID = "00001101-0000-1000-8000-00805F9B34FB"
SERVICE_NAME = "UrbanSightBTServer"
SIGNAL_EXPECTED = "TAKE_PICTURE_SIGNAL"   # Kotlin sends "TAKE_PICTURE_SIGNAL\n"

# --- Capture/transfer config ---
IMAGE_DIR = "."                           # folder where capture_*.png are saved
GLOB_PATTERN = "capture_*.png"
LATEST_CANDIDATES = [
    "/tmp/capture_latest.png",
    "/tmp/capture.png",
    "/tmp/capture.jpg",
]
FLAG = "/tmp/snap.flag"                   # file the capture script is watching
MIN_VALID_SIZE = 1024                     # bytes
NEW_IMAGE_TIMEOUT = 6.0                   # seconds to wait for a fresh image
READ_STABLE_DELAY = 0.15                  # seconds to re-check file size before reading

# --- Single-instance lock ---
LOCKFILE = "/tmp/urbansight_bt.lock"

def _acquire_lock():
    if os.path.exists(LOCKFILE):
        raise RuntimeError("Another bt_bridge.py is already running.")
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))

def _release_lock():
    try:
        os.remove(LOCKFILE)
    except Exception:
        pass

# --- Helpers ---
def _find_latest_file():
    """Return path to the newest valid capture file (or None)."""
    candidates = []
    for p in LATEST_CANDIDATES:
        if os.path.exists(p):
            try:
                sz = os.path.getsize(p)
                if sz >= MIN_VALID_SIZE:
                    candidates.append((os.path.getmtime(p), p))
            except Exception:
                pass
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
    """Create the flag (owned by the capture user), wait for a newer image, then read it."""
    before = _latest_mtime()

    # Create flag
    try:
        open(FLAG, "w").close()
        # Make sure the capture script can delete the flag:
        flag_owner = os.environ.get("SUDO_USER") or os.environ.get("USER") or "pi"
        try:
            entry = pwd.getpwnam(flag_owner)
            os.chown(FLAG, entry.pw_uid, entry.pw_gid)
        except Exception as e:
            print(f"[BT] chown FLAG to {flag_owner} failed (non-fatal): {e}")
        print(f"[BT] Created trigger flag {FLAG}")
    except Exception as e:
        print(f"[BT] Failed to create trigger flag: {e}")

    # Wait for a strictly newer image
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
        print("sending header")
        sock.sendall(header)
        print("sending image body")
        sock.sendall(payload)
        print("send complete")
    else:
        header = struct.pack(">I", 0)
        print("sending header error!!")
        sock.sendall(header)
        if error_msg:
            try:
                sock.sendall(error_msg.encode("utf-8"))
            except Exception:
                pass

# --- Server ---
def run_server():
    _acquire_lock()
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    try:
        # Use a free RFCOMM channel (avoid "address already in use")
        server_sock.bind(("", bluetooth.PORT_ANY))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]
        print(f"[BT] Listening on RFCOMM channel {port}")

        bluetooth.advertise_service(
            server_sock,
            SERVICE_NAME,
            service_id=UUID,
            service_classes=[UUID, bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE],
        )
        print(f"[BT] Advertised UUID {UUID} as '{SERVICE_NAME}'")

        while True:
            client_sock = None
            try:
                client_sock, client_info = server_sock.accept()
                client_sock.settimeout(60)
                print("[BT] Client connected; waiting for trigger...")
                print(f"[BT] Accepted connection from {client_info[0]}")

                data = client_sock.recv(1024) or b""
                txt = data.decode("utf-8", errors="ignore").strip()
                if txt.startswith(SIGNAL_EXPECTED) or txt == "" or txt == "\n":
                    print("[BT] Trigger received.")
                else:
                    print(f"[BT] Unexpected signal: {txt!r}. Proceeding anyway...")

                image_bytes = _trigger_new_capture_and_get_image()

                if image_bytes and len(image_bytes) >= MIN_VALID_SIZE:
                    send_with_size_header(client_sock, image_bytes)
                    print(f"[BT] Sent image ({len(image_bytes)} bytes) with 4-byte header.")
                else:
                    send_with_size_header(client_sock, b"", "ERROR: No image available.")
                    print("[BT] Sent error (size=0).")

            except bluetooth.BluetoothError as e:
                print(f"[BT] Bluetooth Error (per-conn): {e}")
            except Exception as e:
                print(f"[BT] General Error (per-conn): {e}")
                traceback.print_exc()
            finally:
                if client_sock:
                    try:
                        client_sock.close()
                    except Exception:
                        pass
                print("[BT] Client disconnected. Waiting for next connection...")

    except KeyboardInterrupt:
        print("\n[BT] Shutting down on Ctrl+C.")
    except Exception as e:
        print(f"[BT] Fatal server error: {e}")
        traceback.print_exc()
    finally:
        try:
            server_sock.close()
        except Exception:
            pass
        _release_lock()
        print("[BT] Server socket closed.")

if __name__ == "__main__":
    run_server()
