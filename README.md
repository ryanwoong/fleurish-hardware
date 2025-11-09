# fleurish Hardware

An intelligent litter detection system combining ESP32-CAM hardware with YOLOv8 machine learning for automated waste monitoring. The system captures images, processes them through a trained object detection model, and manages detected litter via a backend API.

## Related Repositories

- [Frontend](https://github.com/fion-lei/fleurish)
- [Backend](https://github.com/fion-lei/fleurish-backend)

## System Overview

This project consists of three main components:

1. **ESP32-CAM Module** - Captures periodic images and uploads them to the server
2. **Node.js Server** - Receives images, runs ML inference, and manages results
3. **Processing/Training** - YOLOv8 model training and litter detection

## Architecture

```
ESP32-CAM (hardware)
    ↓ (uploads images every 10s)
Node.js Server (port 3000)
    ↓ (runs YOLOv8 inference)
YOLOv8 Model (trained on TACO dataset)
    ↓ (if confidence > 0.4)
fleurish Backend API (port 5001) + Processed Images
```

---

## 📁 Project Structure

```
fleurish-hardware/
├── esp32/                    # ESP32-CAM firmware
│   ├── hackathon.ino        # Main Arduino sketch
│   ├── camera_pins.h        # Camera pin definitions
│   └── config.h             # WiFi and server configuration
│
├── server/                   # Node.js image processing server
│   ├── server.js            # Main server application
│   ├── package.json         # Node dependencies
│   ├── requirements.txt     # Python ML dependencies
│   ├── photos/              # Temporary upload directory
│   └── processed/
│       └── photo_results/   # Litter detections (confidence > 0.4)
│
└── processing/              # ML model training
    ├── Litter_Detection_YoloV8.ipynb
    ├── dataset/             # TACO dataset
    └── runs/detect/train8/  # Trained model weights
```

---

## 🖥️ Server Component

### What the Server Does

The Node.js server (`server/server.js`) acts as the central processing hub:

1. **Receives Images** - Accepts POST requests from ESP32-CAM at `/upload` endpoint
2. **Timestamps Files** - Automatically names images with date/time (e.g., `photo_2025-11-09_14-30-45.jpg`)
3. **Runs ML Inference** - Executes YOLOv8 model on each uploaded image using Python
4. **Filters Results** - Only saves images with litter confidence > 40%
5. **Creates Tasks** - Notifies backend API (port 5001) when litter is detected
6. **Manages Storage** - Automatically deletes low-confidence images to save space

### Server Directories

- **`server/photos/`** - Temporary storage for uploaded images (deleted after processing)
- **`server/processed/photo_results/`** - Permanent storage for images with detected litter (confidence > 0.4)

Only images where the model detects litter with high confidence are kept in `processed/photo_results/` with bounding boxes drawn around detected objects.

### Server Installation

```bash
cd server

# Install Node.js dependencies
npm install

# Install Python ML dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
cd server
node server.js
```

The server will start on port 3000 and display:

- Local URL: `http://localhost:3000`
- Network URLs for ESP32 to connect to
- Paths where photos will be saved

---

## 📷 ESP32-CAM Component

### Setup

1. Create `config.h` from template:

```cpp
// config.h
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "http://YOUR_SERVER_IP:3000/upload";
```

2. Upload `hackathon.ino` to ESP32-CAM using Arduino IDE
3. The camera will capture and upload images every 10 seconds

---

## Processing Component

The litter detection model training is based on [AaronVincent6411/Litter-Detection](https://github.com/AaronVincent6411/Litter-Detection).

### Training the Model

#### 1. Install Dependencies

```bash
cd processing
pip install -r requirements.txt
```

#### 2. Download TACO Dataset

```bash
python download_taco.py
python download_taco_images.py  # ~15GB, takes 30-60 minutes
python download_taco.py         # Convert to YOLO format
```

#### 3. Train Model

```bash
python train_taco.py
```

The trained model will be saved to `processing/runs/detect/train8/weights/best.pt`

### Using the Garbage Detector (Standalone)

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
