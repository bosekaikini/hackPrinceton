import os
from ultralytics import YOLO

GCS_BUCKET_NAME = os.environ.get('AIP_MODEL_DIR', '').split('gs://')[-1].split('/')[0]
GCS_INPUT_ROOT = f"/gcs/{GCS_BUCKET_NAME}"
DATA_CONFIG_PATH = os.path.join(GCS_INPUT_ROOT, 'master_data/config.yaml')

print(f"--- Starting Training Job ---")
print(f"GCS Bucket Name (Inferred): {GCS_BUCKET_NAME}")
print(f"Data Config Path (In Container): {DATA_CONFIG_PATH}")


def main():
    """
    Main function to load the model, set up training, and start the job.
    """
    try:
        # Load the pre-trained YOLOv8L model for a strong start
        # 'l' stands for large, offering a good balance of speed and accuracy.
        model = YOLO('yolov8l.pt')

        # --- Training Configuration ---
        # data: Path to your dataset config (master_data/data.yaml) which points 
        #       to the train/test/valid folders inside the GCS bucket.
        # epochs: 50 epochs for a good initial training duration.
        # imgsz: Standard image size for YOLOv8.
        # batch: -1 tells the system to auto-determine the largest batch size 
        #        that fits on the T4 GPU's memory.
        # workers: Uses all available CPU cores for faster data loading.
        # project/name: Define the output folder structure where weights and results go
        
        model.train(
            data=DATA_CONFIG_PATH,
            epochs=50,
            imgsz=640,
            batch=-1, 
            workers=os.cpu_count(),
            project='output_yolov8_urban_issues',
            name='run_t4_50epochs'
        )

        print("\n--- Training Completed Successfully ---")

    except Exception as e:
        print(f"\n--- Training Failed ---")
        print(f"An error occurred: {e}")
        # Re-raise the exception to signal Vertex AI that the job failed
        raise e

if __name__ == '__main__':
    # This reminder is just for the user in case they use a custom image.
    print("Ensure 'ultralytics' is installed if you use a custom container.")
    main()