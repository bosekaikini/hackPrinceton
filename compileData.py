import os
import shutil
from typing import List


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_SEARCH_DIR = SCRIPT_DIR  

MASTER_DIR_NAME = 'master_data'
MASTER_DIR = os.path.join(BASE_SEARCH_DIR, MASTER_DIR_NAME) 

SPLITS = ['train', 'test', 'valid']
CONTENT_DIRS = ['images', 'labels'] 
CLASS_ID_MAP = {
    'DeadAnimalsPollution': 0,
    'DamagedConcreteStructures': 1,
    'FallenTrees': 2,
    'Garbage': 3,
    'Graffiti': 4,
    'IllegalParking': 5,
    'PotholesAndRoadCracks': 6,
    'DamagedRoadSigns': 7,
    'DamagedElectricPoles': 8,
}
TARGET_FOLDER_NAMES = list(CLASS_ID_MAP.keys())


def ensure_master_structure():
    """Ensures the final target directories (train/images, valid/labels, etc.) exist."""
    os.makedirs(MASTER_DIR, exist_ok=True) 
    print(f"Ensuring master directory structure exists at: {MASTER_DIR}")
    for split in SPLITS:
        for content in CONTENT_DIRS:
            os.makedirs(os.path.join(MASTER_DIR, split, content), exist_ok=True)
    print("Master structure ready.")


def find_data_folders_recursively(root_dir: str) -> List[str]:
    """
    Finds the base directory that immediately contains the 'train', 'test', and 'valid' folders,
    specifically checking for the Category/Category nesting pattern.
    """
    found_bases = []
    
    for entry in os.listdir(root_dir):
        entry_path = os.path.join(root_dir, entry)
        
        if entry == MASTER_DIR_NAME or not os.path.isdir(entry_path):
            continue
        
        nested_folder_path = os.path.join(entry_path, entry)

        if os.path.isdir(nested_folder_path):
            if os.path.isdir(os.path.join(nested_folder_path, SPLITS[0])):
                found_bases.append(nested_folder_path)
                print(f"   --> Found nested structure for: {entry}")
                continue
        
        if os.path.isdir(os.path.join(entry_path, SPLITS[0])):
            found_bases.append(entry_path)
            print(f"   --> Found direct structure for: {entry}")

    return list(set(found_bases))


def merge_datasets(category_base_paths: List[str]):
    
    total_files_moved = 0
    
    if not category_base_paths:
        print("No category data folders containing 'train', 'test', and 'valid' were found.")
        return

    for category_base_path in category_base_paths:
        display_name = os.path.basename(category_base_path)

        parent_name = os.path.basename(os.path.dirname(category_base_path))
        if parent_name == display_name:
            display_name = parent_name
        
        print(f"Processing data found at: '{display_name}' ({category_base_path})")
        
        for split in SPLITS:
            source_split_dir = os.path.join(category_base_path, split)
            destination_split_dir = os.path.join(MASTER_DIR, split)

            if not os.path.isdir(source_split_dir):
                continue

            for content_dir in CONTENT_DIRS:
                source_content_dir = os.path.join(source_split_dir, content_dir)
                target_dir = os.path.join(destination_split_dir, content_dir)
                
                if os.path.isdir(source_content_dir):
                    
                    for filename in os.listdir(source_content_dir):
                        source_file = os.path.join(source_content_dir, filename)
                        
                        if os.path.isfile(source_file):
                            destination_file = os.path.join(target_dir, filename)
                            
                            try:
                                shutil.move(source_file, destination_file)
                                total_files_moved += 1
                                
                            except FileExistsError:
                                pass
                            except Exception as e:
                                print(f"      Failed to move {source_file}: {e}")

        print(f"Finished consolidating data from '{display_name}'.")
        
    print("\n--- Data Consolidation Complete ---")
    print(f"Total files moved: {total_files_moved}")


if __name__ == "__main__":
    ensure_master_structure()
    category_paths = find_data_folders_recursively(BASE_SEARCH_DIR)
    merge_datasets(category_paths)
    
    print("\nYour dataset files have been successfully merged into the 'master_data' folder.")