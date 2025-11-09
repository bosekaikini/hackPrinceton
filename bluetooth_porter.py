import bluetooth
import os
import time
import glob
import struct  # <-- added

# --- Configuration (unchanged where possible) ---
UUID = "00001101-0000-1000-8000-00805F9B34FB"
PORT = 1

SIGNAL_EXPECTED = "TAKE_PICTURE_SIGNAL"  # Kotlin sends "TAKE_PICTURE_SIGNAL\n"

IMAGE_DIR = "."                  # set to the folder where your top script writes images
GLOB_PATTERN = "capture_*.png"

LATEST_CANDIDATES = [
    "/tmp/capture.jpg",
    "/tmp/capture.png",
    "/tmp/capture_latest.png",
]

MIN_VALID_SIZE = 1024
MAX_WAIT_FOR_FILE = 5.0


def _find_latest_file():
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


def take_picture():
    deadline = time.time() + MAX_WAIT_FOR_FILE
    while time.time() < deadline:
        chosen = _find_latest_file()
        if chosen is None:
            time.sleep(0.2)
            continue
        try:
            s1 = os.path.getsize(chosen)
            time.sleep(0.15)
            s2 = os.path.getsize(chosen)
            if s2 >= MIN_VALID_SIZE and s1 == s2:
                with open(chosen, "rb") as f:
                    data = f.read()
                if len(data) >= MIN_VALID_SIZE:
                    print(f"-> Using latest image: {chosen} ({len(data)} bytes)")
                    return data
        except Exception as e:
            print(f"File read error: {e}")
            time.sleep(0.2)
    print("-> No valid image found to send.")
    return None


def send_with_size_header(sock, payload: bytes, error_msg: str = None):
    """
    Protocol to match your Kotlin client:
      - First send a 4-byte big-endian integer: payload size (N)
      - If N > 0: send exactly N bytes (the image)
      - If N == 0: optionally send ASCII error text
    """
    if payload and len(payload) > 0:
        header = struct.pack(">I", len(payload))  # big-endian uint32
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

    print(f"Waiting for connection on RFCOMM channel {PORT} with UUID: {UUID}")

    while True:
        client_sock = None
        try:
            client_sock, client_info = server_sock.accept()
            print(f"Accepted connection from {client_info[0]}")

            # Treat ANY data (even just Enter/newline) as a trigger
            data = client_sock.recv(1024) or b""
            txt = data.decode("utf-8", errors="ignore").strip()

            if txt.startswith(SIGNAL_EXPECTED) or txt == "" or txt == "\n":
                print("Trigger received. Grabbing latest image from disk...")
            else:
                print(f"Unexpected signal: {txt!r}. Proceeding anyway...")

            image_bytes = take_picture()

            if image_bytes and len(image_bytes) > 0:
                send_with_size_header(client_sock, image_bytes)
                print(f"Sent image ({len(image_bytes)} bytes) with 4-byte size header.")
            else:
                send_with_size_header(client_sock, b"", "ERROR: No image available.")
                print("Sent error (size=0 + message).")

            client_sock.close()
            print("Connection closed. Waiting for the next connection...")

        except bluetooth.BluetoothError as e:
            print(f"Bluetooth Error: {e}. Waiting for a new connection...")
            if client_sock:
                try: client_sock.close()
                except Exception: pass
            time.sleep(2)
            continue
        except Exception as e:
            print(f"General Error: {e}")
            if client_sock:
                try: client_sock.close()
                except Exception: pass
            time.sleep(2)
            continue


if __name__ == "__main__":
    run_server()
