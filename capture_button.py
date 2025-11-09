# capture_button.py
import os
import sys
import time
import glob
import select

import numpy as np
import cv2
import pyrealsense2 as rs

# -------- Settings --------
IMAGE_DIR = "."                 # Where to save images
NAME_PATTERN = "capture_{}.png" # File name pattern
FLAG = "/tmp/snap.flag"         # BT script drops this file to trigger a capture
WARMUP_FRAMES = 10              # Let auto-exposure settle
# --------------------------

def next_index():
    """Pick the next capture_N index based on existing files."""
    nums = []
    for p in glob.glob(os.path.join(IMAGE_DIR, "capture_*.png")):
        try:
            n = int(os.path.splitext(os.path.basename(p))[0].split("_")[1])
            nums.append(n)
        except Exception:
            pass
    return (max(nums) + 1) if nums else 0

def init_rs():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)
    for _ in range(WARMUP_FRAMES):
        pipeline.wait_for_frames()
    return pipeline

def snap_and_save(pipeline, idx):
    frames = pipeline.wait_for_frames()
    color_frame = frames.get_color_frame()
    if not color_frame:
        print("No frame captured, try again.")
        return None

    img = np.asanyarray(color_frame.get_data())
    fname = os.path.join(IMAGE_DIR, NAME_PATTERN.format(idx))
    cv2.imwrite(fname, img)
    try:
        cv2.imwrite("/tmp/capture_latest.png", img)  # handy stable path
    except Exception:
        pass
    print(f"{os.path.basename(fname)} saved on Raspberry Pi!")
    return fname

def main():
    pipeline = None
    try:
        pipeline = init_rs()
        img_counter = next_index()

        print("Press ENTER to capture an image,")
        print(f"or trigger via {FLAG} (set by bt_bridge.py). Ctrl+C to quit.")

        while True:
            # 1) Flag trigger from Bluetooth script
            if os.path.exists(FLAG):
                try:
                    os.remove(FLAG)   # IMPORTANT: delete the flag so we don't loop
                except Exception:
                    pass
                if snap_and_save(pipeline, img_counter):
                    img_counter += 1
                continue

            # 2) Non-blocking stdin check for keyboard ENTER
            r, _, _ = select.select([sys.stdin], [], [], 0.1)
            if r:
                _ = sys.stdin.readline()  # consume line
                if snap_and_save(pipeline, img_counter):
                    img_counter += 1
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        try:
            if pipeline is not None:
                pipeline.stop()
        except Exception:
            pass

if __name__ == "__main__":
    main()
