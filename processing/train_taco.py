from ultralytics import YOLO
from pathlib import Path
import argparse


def train_model(
    data_yaml='taco_yolo/data.yaml',
    model='yolov8n.pt',  # Nano model for 4GB VRAM
    epochs=150,
    imgsz=416,  # Smaller image size for less VRAM
    batch=8,  # Small batch for 4GB VRAM
    device='0',
    workers=8  # More workers for data loading
):
    """
    Train YOLOv8 on combined garbage dataset
    
    Args:
        data_yaml: Path to data configuration file
        model: Base model (yolov8n/s/m/l/x)
        epochs: Number of training epochs
        imgsz: Image size
        batch: Batch size (increase with more RAM)
        device: Device ('0' for GPU, 'cpu' for CPU)
        workers: Number of data loading workers
    """
    
    if not Path(data_yaml).exists():
        print(f"Error: {data_yaml} not found!")
        print("Please run 'python download_taco.py' first to prepare the dataset")
        return
    
    print("=" * 70)
    print("Training YOLOv8 on TACO Garbage Dataset")
    print("=" * 70)
    print(f"Model: {model}")
    print(f"Epochs: {epochs}")
    print(f"Image size: {imgsz}")
    print(f"Batch size: {batch}")
    print(f"Workers: {workers}")
    print(f"Device: {device}")
    print("=" * 70)
    
    # Load model
    yolo_model = YOLO(model)
    
    results = yolo_model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        patience=30,
        save=True,
        project='runs/garbage_detection',
        name='taco_model',
        pretrained=True,
        optimizer='AdamW',
        verbose=True,
        seed=42,
        deterministic=False,
        single_cls=False,
        rect=True,
        cos_lr=True,
        close_mosaic=15,
        resume=False,
        amp=True,
        fraction=1.0,
        profile=False,
        overlap_mask=True,
        mask_ratio=4,
        dropout=0.0,
        val=True,
        plots=True,
        
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=5.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,
        mosaic=0.5,
        mixup=0.0,
        copy_paste=0.0,
        
        cache=False,
        multi_scale=False,
    )
    
    print("\n" + "=" * 70)
    print("Training Complete!")
    print("=" * 70)
    print(f"Best model: runs/garbage_detection/taco_model/weights/best.pt")
    print(f"Last model: runs/garbage_detection/taco_model/weights/last.pt")
    print("=" * 70)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Train YOLOv8 on TACO garbage dataset')
    parser.add_argument('--data', type=str, default='taco_yolo/data.yaml',
                       help='Path to data.yaml')
    parser.add_argument('--model', type=str, default='yolov8n.pt',
                       choices=['yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt', 'yolov8l.pt', 'yolov8x.pt'],
                       help='Model size')
    parser.add_argument('--epochs', type=int, default=150,
                       help='Training epochs')
    parser.add_argument('--imgsz', type=int, default=416,
                       help='Image size (416 for 4GB VRAM, 640 for 8GB+)')
    parser.add_argument('--batch', type=int, default=8,
                       help='Batch size (8 for 4GB VRAM, 16 for 6GB, 32 for 8GB+)')
    parser.add_argument('--device', type=str, default='0',
                       help='Device (0 for GPU, cpu for CPU)')
    parser.add_argument('--workers', type=int, default=8,
                       help='Data loading workers')
    parser.add_argument('--cache', action='store_true',
                       help='Cache images in RAM (much faster!)')
    
    args = parser.parse_args()
    
    train_model(
        data_yaml=args.data,
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers
    )


if __name__ == "__main__":
    main()
