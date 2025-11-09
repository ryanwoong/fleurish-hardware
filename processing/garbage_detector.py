from ultralytics import YOLO
import cv2
from pathlib import Path
import argparse


class GarbageDetector:
    def __init__(self, model_path='runs/garbage_detection/taco_model/weights/best.pt', confidence_threshold=0.25):
        """
        Initialize the garbage detector with YOLOv8
        
        Args:
            model_path: Path to YOLOv8 model weights (default: trained TACO model)
            confidence_threshold: Minimum confidence for detections (0-1)
        """
        # Check if custom trained model exists, otherwise use pretrained
        if not Path(model_path).exists():
            print(f"Warning: Trained model not found at {model_path}")
            print("Using pretrained yolov8n.pt model instead")
            print("To use trained model, run: python train_taco.py")
            model_path = 'yolov8n.pt'
        
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        
        # Print model info
        print(f"Loaded model: {model_path}")
        print(f"Number of classes: {len(self.model.names)}")
        
    def detect_garbage(self, image_path, save_results=True, output_dir='results'):
        """
        Detect garbage in a single image
        
        Args:
            image_path: Path to the input image
            save_results: Whether to save annotated results
            output_dir: Directory to save results
            
        Returns:
            Detection results
        """
        # Run inference
        results = self.model(image_path, conf=self.confidence_threshold)
        
        # Save results if requested
        if save_results:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save annotated image
            for result in results:
                annotated = result.plot()
                output_file = output_path / f"detected_{Path(image_path).name}"
                cv2.imwrite(str(output_file), annotated)
                print(f"Saved result to: {output_file}")
        
        return results
    
    def detect_batch(self, image_dir, save_results=True, output_dir='results'):
        """
        Detect garbage in multiple images from a directory
        
        Args:
            image_dir: Directory containing images
            save_results: Whether to save annotated results
            output_dir: Directory to save results
            
        Returns:
            List of detection results
        """
        image_path = Path(image_dir)
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
        
        # Find all images in directory
        image_files = []
        for ext in image_extensions:
            image_files.extend(image_path.glob(f'*{ext}'))
            image_files.extend(image_path.glob(f'*{ext.upper()}'))
        
        if not image_files:
            print(f"No images found in {image_dir}")
            return []
        
        print(f"Found {len(image_files)} images")
        
        # Process each image
        all_results = []
        detection_summary = {}
        
        for img_file in image_files:
            print(f"\nProcessing: {img_file.name}")
            results = self.detect_garbage(str(img_file), save_results, output_dir)
            all_results.append(results)
            
            # Print detection summary
            for result in results:
                boxes = result.boxes
                if len(boxes) > 0:
                    print(f"  Detected {len(boxes)} objects")
                    for box in boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        class_name = self.model.names[cls]
                        print(f"    - {class_name}: {conf:.2%}")
                        
                        # Update summary
                        if class_name not in detection_summary:
                            detection_summary[class_name] = 0
                        detection_summary[class_name] += 1
                else:
                    print("  No objects detected")
        
        # Print overall summary
        if detection_summary:
            print("\n" + "=" * 60)
            print("Detection Summary Across All Images:")
            print("=" * 60)
            for class_name, count in sorted(detection_summary.items(), key=lambda x: x[1], reverse=True):
                print(f"{class_name:30s}: {count:3d} detections")
            print("=" * 60)
        
        return all_results
    
    def get_classes(self):
        """Get list of all classes the model can detect"""
        return self.model.names


def main():
    parser = argparse.ArgumentParser(description='Detect garbage in images using YOLOv8')
    parser.add_argument('--image', type=str, help='Path to a single image')
    parser.add_argument('--dir', type=str, help='Path to directory containing images')
    parser.add_argument('--model', type=str, default='runs/garbage_detection/taco_model/weights/best.pt', 
                       help='Path to YOLOv8 model (default: trained TACO model)')
    parser.add_argument('--conf', type=float, default=0.25, 
                       help='Confidence threshold (default: 0.25)')
    parser.add_argument('--output', type=str, default='results', 
                       help='Output directory for results (default: results)')
    parser.add_argument('--show-classes', action='store_true',
                       help='Show all available classes and exit')
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = GarbageDetector(model_path=args.model, confidence_threshold=args.conf)
    
    # Show classes if requested
    if args.show_classes:
        print("\n" + "=" * 60)
        print("Available Garbage Classes:")
        print("=" * 60)
        for idx, name in detector.model.names.items():
            print(f"{idx:3d}: {name}")
        print("=" * 60)
        print(f"\nTotal: {len(detector.model.names)} classes")
        return
    
    # Process images
    if args.image:
        print(f"Processing single image: {args.image}")
        detector.detect_garbage(args.image, save_results=True, output_dir=args.output)
    elif args.dir:
        print(f"Processing images from directory: {args.dir}")
        detector.detect_batch(args.dir, save_results=True, output_dir=args.output)
    else:
        print("Please specify either --image or --dir")
        parser.print_help()


if __name__ == "__main__":
    main()
