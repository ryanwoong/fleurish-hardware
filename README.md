## Quick Start

### 1. Install Dependencies

```bash
cd processing
pip install -r requirements.txt
```

### 2. Download TACO Dataset

```bash
python download_taco.py
python download_taco_images.py  # ~15GB, takes 30-60 minutes
python download_taco.py         # Convert to YOLO format
```

### 3. Train Model

```bash
python train_taco.py
```

### 4. Detect Garbage

**Show all available garbage classes:**

```bash
python garbage_detector.py --show-classes
```

**Detect garbage in single image:**

```bash
python garbage_detector.py --image test.jpg
```

**Detect in multiple images:**

```bash
python garbage_detector.py --dir test_images/
```

**Use pretrained model (no training needed):**

```bash
python garbage_detector.py --model yolov8n.pt --image test.jpg
```

**Lower confidence for more detections:**

```bash
python garbage_detector.py --image test.jpg --conf 0.15
```
