import os
import json
import shutil
from pathlib import Path
from tqdm import tqdm
import requests
import zipfile


def download_file(url, destination):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(destination, 'wb') as file, tqdm(
        desc=destination.name,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024*1024):
            size = file.write(data)
            progress_bar.update(size)


def download_taco(output_dir='taco_dataset'):
    print("=" * 70)
    print("Downloading TACO Dataset")
    print("=" * 70)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print("Downloading from TACO repository...")
    
    # Download annotations and images
    annotations_url = "https://github.com/pedropro/TACO/archive/refs/heads/master.zip"
    zip_file = output_path / "taco.zip"
    
    print(f"\nDownloading TACO repository...")
    download_file(annotations_url, zip_file)
    
    print("\nExtracting...")
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(output_path)
    
    zip_file.unlink()
    
    print("\nTACO dataset downloaded!")
    return output_path / "TACO-master"


def convert_coco_to_yolo(coco_annotation, img_width, img_height):
    """Convert COCO bbox format to YOLO format"""
    # COCO format: [x, y, width, height] (top-left corner)
    # YOLO format: [x_center, y_center, width, height] (normalized)
    
    x, y, w, h = coco_annotation
    
    # Convert to center coordinates
    x_center = (x + w / 2) / img_width
    y_center = (y + h / 2) / img_height
    
    # Normalize width and height
    width = w / img_width
    height = h / img_height
    
    return [x_center, y_center, width, height]


def prepare_taco_yolo(taco_path, output_dir='taco_yolo'):
    """
    Convert TACO dataset to YOLO format
    """
    print("\n" + "=" * 70)
    print("Preparing TACO Dataset in YOLO Format")
    print("=" * 70)
    
    output_path = Path(output_dir)
    
    # Create directory structure
    (output_path / 'images' / 'train').mkdir(parents=True, exist_ok=True)
    (output_path / 'images' / 'val').mkdir(parents=True, exist_ok=True)
    (output_path / 'labels' / 'train').mkdir(parents=True, exist_ok=True)
    (output_path / 'labels' / 'val').mkdir(parents=True, exist_ok=True)
    
    # Load COCO annotations
    taco_path = Path(taco_path)
    annotations_file = taco_path / "data" / "annotations.json"
    
    if not annotations_file.exists():
        print(f"Error: Annotations file not found at {annotations_file}")
        return False
    
    print(f"Loading annotations from {annotations_file}")
    with open(annotations_file, 'r') as f:
        coco_data = json.load(f)
    
    # Create category mapping
    categories = {cat['id']: cat['name'] for cat in coco_data['categories']}
    category_to_id = {cat['id']: idx for idx, cat in enumerate(coco_data['categories'])}
    
    print(f"\nFound {len(categories)} categories")
    print(f"Total images: {len(coco_data['images'])}")
    print(f"Total annotations: {len(coco_data['annotations'])}")
    
    # Create image_id to annotations mapping
    img_to_anns = {}
    for ann in coco_data['annotations']:
        img_id = ann['image_id']
        if img_id not in img_to_anns:
            img_to_anns[img_id] = []
        img_to_anns[img_id].append(ann)
    
    # Split into train/val (80/20)
    images = coco_data['images']
    split_idx = int(len(images) * 0.8)
    
    train_images = images[:split_idx]
    val_images = images[split_idx:]
    
    print(f"\nSplit: {len(train_images)} training, {len(val_images)} validation")
    
    # Process images
    def process_split(image_list, split_name):
        processed = 0
        skipped = 0
        
        print(f"\nProcessing {split_name} set...")
        for img_data in tqdm(image_list):
            img_id = img_data['id']
            img_filename = img_data['file_name']
            img_width = img_data['width']
            img_height = img_data['height']
            
            # Source image path
            src_img = taco_path / "data" / img_filename
            
            if not src_img.exists():
                skipped += 1
                continue
            
            # Copy image
            dest_img = output_path / 'images' / split_name / Path(img_filename).name
            shutil.copy2(src_img, dest_img)
            
            # Create label file
            if img_id in img_to_anns:
                label_lines = []
                for ann in img_to_anns[img_id]:
                    category_id = category_to_id[ann['category_id']]
                    bbox = ann['bbox']
                    
                    # Convert to YOLO format
                    yolo_bbox = convert_coco_to_yolo(bbox, img_width, img_height)
                    
                    # Create label line
                    label_line = f"{category_id} {' '.join(map(str, yolo_bbox))}\n"
                    label_lines.append(label_line)
                
                # Write label file
                label_file = output_path / 'labels' / split_name / f"{Path(img_filename).stem}.txt"
                label_file.write_text(''.join(label_lines))
                
                processed += 1
        
        print(f"{split_name}: {processed} images processed, {skipped} skipped (not found)")
        return processed, skipped
    
    train_processed, train_skipped = process_split(train_images, 'train')
    val_processed, val_skipped = process_split(val_images, 'val')
    
    if train_processed == 0:
        print("\nNo images were processed!")
        return False
    
    # Create data.yaml
    class_names = [categories[cat_id] for cat_id in sorted(category_to_id.keys())]
    
    yaml_content = f"""# TACO Dataset Configuration
path: {output_path.absolute()}
train: images/train
val: images/val

# Classes
nc: {len(class_names)}
names: {class_names}
"""
    
    yaml_file = output_path / 'data.yaml'
    yaml_file.write_text(yaml_content)
    
    print(f"\nConfiguration file created: {yaml_file}")
    print(f"Dataset location: {output_path.absolute()}")
    print(f"Total processed: {train_processed + val_processed} images")
    
    return True


def main():
    print("=" * 70)
    print("TACO Dataset Preparation")
    print("=" * 70)
    
    # Download TACO repository
    try:
        taco_path = download_taco('taco_dataset')
    except Exception as e:
        print(f"\nError downloading TACO: {e}")
        return
    
    # Prepare for YOLO
    success = prepare_taco_yolo(taco_path, 'taco_yolo')
    
    if success:
        print("\n" + "=" * 70)
        print("TACO dataset ready for training")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("Please download TACO images separately")
        print("=" * 70)


if __name__ == "__main__":
    main()
