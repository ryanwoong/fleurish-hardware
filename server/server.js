const express = require("express");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const axios = require("axios");

const app = express();
const PORT = 3000;

// Create photos directory if it doesn't exist
const photosDir = path.join(__dirname, "photos");
if (!fs.existsSync(photosDir)) {
  fs.mkdirSync(photosDir);
}

// Create processed results directory if it doesn't exist
const processedDir = path.join(__dirname, "processed", "photo_results");
if (!fs.existsSync(processedDir)) {
  fs.mkdirSync(processedDir, { recursive: true });
}

// Configure multer for handling image uploads
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, photosDir);
  },
  filename: function (req, file, cb) {
    // Generate date/time timestamp for filename
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    const seconds = String(now.getSeconds()).padStart(2, "0");
    const timestamp = `${year}-${month}-${day}_${hours}-${minutes}-${seconds}`;
    cb(null, `photo_${timestamp}.jpg`);
  },
});

const upload = multer({
  storage: storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
});

// Serve static files (photos and HTML)
app.use("/photos", express.static(photosDir));
app.use(express.static(__dirname));

// Function to run YOLOv8 model on an image
async function runModelInference(imagePath, filename) {
  return new Promise((resolve, reject) => {
    const modelPath = path.join(__dirname, "..", "processing", "runs", "detect", "train8", "weights", "best.pt");
    const outputDir = processedDir;

    const pythonScript = `
import sys
from ultralytics import YOLO
import os

model_path = r'${modelPath.replace(/\\/g, "\\\\")}'
image_path = r'${imagePath.replace(/\\/g, "\\\\")}'
output_dir = r'${outputDir.replace(/\\/g, "\\\\")}'

model = YOLO(model_path)
results = model(image_path)

# Get the highest confidence detection
max_confidence = 0
if len(results) > 0 and results[0].boxes is not None:
    boxes = results[0].boxes
    if len(boxes) > 0:
        confidences = boxes.conf.cpu().numpy()
        max_confidence = float(confidences.max())

print(f"CONFIDENCE:{max_confidence}")

# Only save the annotated image if confidence > 0.4
if len(results) > 0 and max_confidence > 0.4:
    save_path = os.path.join(output_dir, '${filename}')
    results[0].save(save_path)
    print(f"SAVED:{save_path}")
`;

    const python = spawn("python", ["-c", pythonScript]);

    let output = "";
    let errorOutput = "";

    python.stdout.on("data", (data) => {
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      errorOutput += data.toString();
    });

    python.on("close", (code) => {
      if (code !== 0) {
        console.error(`Python script error: ${errorOutput}`);
        reject(new Error(`Model inference failed with code ${code}`));
        return;
      }

      // Parse the output for confidence
      const confidenceMatch = output.match(/CONFIDENCE:([\d.]+)/);
      const savedMatch = output.match(/SAVED:(.+)/);

      if (confidenceMatch) {
        const confidence = parseFloat(confidenceMatch[1]);
        const savedPath = savedMatch ? savedMatch[1].trim() : null;

        resolve({
          confidence,
          savedPath,
          passed: confidence > 0.4,
        });
      } else {
        reject(new Error("Could not parse model output"));
      }
    });
  });
}

// Endpoint to receive photos from ESP32
app.post("/upload", upload.single("image"), async (req, res) => {
  if (!req.file) {
    console.log("Upload failed: No file received");
    return res.status(400).json({ error: "No image file provided" });
  }

  console.log(`Photo received: ${req.file.filename} (${(req.file.size / 1024).toFixed(2)} KB)`);

  try {
    // Run model inference on the uploaded photo
    const imagePath = path.join(photosDir, req.file.filename);
    console.log(`Running model inference on ${req.file.filename}...`);

    const result = await runModelInference(imagePath, req.file.filename);

    console.log(`Confidence: ${(result.confidence * 100).toFixed(2)}%`);

    if (result.passed) {
      console.log("PASSED");
      console.log(`Result saved to: ${result.savedPath}`);

      // Create task on the backend server
      try {
        const taskResponse = await axios.post("http://localhost:5001/api/tasks/", {
          requestUserId: "000000000000000000000000",
        });
        console.log("Task created successfully:", taskResponse.data);
      } catch (taskError) {
        console.error("Error creating task:", taskError.message);
        // Continue with the rest of the flow even if task creation fails
      }

      // Delete the original photo from the photos folder
      fs.unlinkSync(imagePath);
      console.log(`Original photo deleted: ${req.file.filename}\n`);

      res.json({
        success: true,
        filename: req.file.filename,
        confidence: result.confidence,
        passed: true,
        message: "Photo processed successfully and passed threshold",
        resultPath: result.savedPath,
      });
    } else {
      console.log(`FAILED below threshold`);

      // Delete the original photo from photos folder
      fs.unlinkSync(imagePath);
      console.log(`Original photo deleted: ${req.file.filename}`);

      // Also delete the result image if it was saved
      const resultPath = path.join(processedDir, req.file.filename);
      if (fs.existsSync(resultPath)) {
        fs.unlinkSync(resultPath);
        console.log(`Result photo also deleted: ${resultPath}`);
      }
      console.log();

      res.json({
        success: true,
        filename: req.file.filename,
        confidence: result.confidence,
        passed: false,
        message: "Photo processed but did not meet confidence threshold",
      });
    }
  } catch (error) {
    console.error(`Error processing image: ${error.message}`);
    res.status(500).json({
      error: "Failed to process image",
      details: error.message,
    });
  }
});

app.listen(PORT, () => {
  const os = require("os");
  const networkInterfaces = os.networkInterfaces();
  const addresses = [];

  for (const name of Object.keys(networkInterfaces)) {
    for (const net of networkInterfaces[name]) {
      if (net.family === "IPv4" && !net.internal) {
        addresses.push(net.address);
      }
    }
  }

  console.log("========================================");
  console.log("ESP32-CAM Timelapse Server Running!");
  console.log("========================================");
  console.log(`Local:   http://localhost:${PORT}`);
  if (addresses.length > 0) {
    addresses.forEach((addr) => {
      console.log(`Network: http://${addr}:${PORT}`);
    });
  }
  console.log("========================================");
  console.log(`Photos will be saved to: ${photosDir}`);
  console.log("Waiting for ESP32 to send images...");
  console.log("========================================\n");
});
