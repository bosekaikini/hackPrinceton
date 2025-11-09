import pyrealsense2 as rs
import numpy as np
import cv2
import bluetooth
import os
import time
import struct
import sys

# --- Bluetooth Configuration (MUST match Android App) ---
UUID = "00001101-0000-1000-8000-00805F9B34FB"
PORT = 1
SIGNAL_EXPECTED = "TAKE_PICTURE_SIGNAL\n" # Signal from phone to trigger action
ADAPTER = "hci0" # Force adapter name

# --- Data Transfer Protocol ---
HEADER_FORMAT = '!I' # Network byte order, Unsigned Int (4 bytes)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# --- RealSense Setup ---
# These variables will hold the pipeline and configuration objects globally
rs_pipeline = None
rs_config = None


def setup_realsense_pipeline():
    """Initializes and starts the RealSense pipeline."""
    global rs_pipeline, rs_config
    if rs_pipeline is None:
        rs_pipeline = rs.pipeline()
        rs_config = rs.config()
        # Using 640x400 as per your original code
        rs_config.enable_stream(rs.stream.color, 640, 400, rs.format.bgr8, 30)
        rs_pipeline.start(rs_config)
        print("RealSense pipeline started successfully.")
    # Allow a few frames to pass for auto-exposure stabilization
    time.sleep(1)


def take_picture_and_encode_jpeg():
    """
    Captures a frame using the active RealSense pipeline and encodes it to JPEG bytes.
    """
    if rs_pipeline is None:
        print("CAMERA ERROR: RealSense pipeline not initialized.")
        return None
       
    print("-> Waiting for RealSense frame...")
    try:
        # Wait for a fresh set of frames
        frames = rs_pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
       
        if not color_frame:
            print("CAMERA ERROR: No color frame captured.")
            return None
           
        # Convert frame to numpy array
        color_image = np.asanyarray(color_frame.get_data())
       
        # Encode the numpy array into JPEG format bytes
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90] # 90% quality
        success, encoded_image = cv2.imencode('.jpg', color_image, encode_param)
       
        if not success:
            print("ENCODING ERROR: Failed to encode image to JPEG.")
            return None

        # Convert the numpy array of bytes to a standard Python byte object
        image_bytes = encoded_image.tobytes()
       
        print(f"-> Photo captured and encoded. Size: {len(image_bytes)} bytes")
        return image_bytes

    except Exception as e:
        print(f"CAPTURE/ENCODING ERROR: {e}")
        return None


def run_server():
    global rs_pipeline
    server_sock = None
    client_sock = None
   
    try:
        # Initialize the camera setup once
        setup_realsense_pipeline()

        # 1. Socket Setup
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind((ADAPTER, PORT))
        server_sock.listen(1)

        bluetooth.advertise_service(server_sock, "UrbanSightBTServer",
                                   service_id=UUID,
                                   service_classes=[UUID, bluetooth.SERIAL_PORT_CLASS],
                                   profiles=[bluetooth.SERIAL_PORT_PROFILE])

        print(f"\nBluetooth Server Active. Waiting for connection on RFCOMM channel {PORT}.")

        while True:
            try:
                # 2. Wait for connection and Signal
                client_sock, client_info = server_sock.accept()
                print(f"\nAccepted connection from {client_info[0]}")
               
                # Receive signal from phone
                data = client_sock.recv(1024).decode('utf-8')
               
                if not data or not data.strip() == SIGNAL_EXPECTED.strip():
                    print(f"Received unexpected signal: {data.strip()}")
                    client_sock.close()
                    continue
                   
                print("Received picture signal. Starting capture and transfer...")
               
                # 3. Capture Image In-Memory
                image_bytes = take_picture_and_encode_jpeg()
               
                # 4. Protocol for Sending Image
                if image_bytes and len(image_bytes) > 0:
                    image_size = len(image_bytes)
                    print(f"Sending image header: {image_size} bytes.")
                   
                    # a) Send the image size (HEADER)
                    size_header = struct.pack(HEADER_FORMAT, image_size)
                    client_sock.sendall(size_header)
                   
                    # b) Send the raw image data (BODY)
                    client_sock.sendall(image_bytes)
                   
                    print("Image sent successfully.")
                else:
                    # Send a zero size header to signal failure
                    client_sock.sendall(struct.pack(HEADER_FORMAT, 0))
                    print("Sent zero-size header indicating failure to client.")
                   
                # 5. Close the client socket
                client_sock.close()
                client_sock = None
                print("Connection closed. Waiting for the next connection...")

            except bluetooth.BluetoothError as e:
                print(f"RUNTIME BLUETOOTH ERROR: {e}. Releasing socket and waiting.")
                if client_sock: client_sock.close()
                client_sock = None
                time.sleep(5)
                continue
            except Exception as e:
                print(f"RUNTIME GENERAL ERROR: {e}")
                if client_sock: client_sock.close()
                client_sock = None
                time.sleep(5)
                continue

    except Exception as e:
        print(f"\nFATAL SETUP ERROR: {e}")
        if rs_pipeline:
            rs_pipeline.stop()
        if server_sock: server_sock.close()
        sys.exit(1)

if __name__ == "__main__":
    run_server()
