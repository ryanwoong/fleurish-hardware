const express = require("express");
const multer = require("multer");
const fs = require("fs");
const path = require("path");

const app = express();
const PORT = 3000;

// Create photos directory if it doesn't exist
const photosDir = path.join(__dirname, "photos");
if (!fs.existsSync(photosDir)) {
  fs.mkdirSync(photosDir);
}

// Configure multer for handling image uploads
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, photosDir);
  },
  filename: function (req, file, cb) {
    // Get the highest photo number and increment
    const files = fs
      .readdirSync(photosDir)
      .filter((f) => f.startsWith("photo_") && f.endsWith(".jpg"))
      .map((f) => parseInt(f.match(/photo_(\d+)\.jpg/)?.[1] || 0))
      .filter((n) => !isNaN(n));

    const nextNumber = files.length > 0 ? Math.max(...files) + 1 : 0;
    cb(null, `photo_${nextNumber}.jpg`);
  },
});

const upload = multer({
  storage: storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
});

// Serve static files (photos and HTML)
app.use("/photos", express.static(photosDir));
app.use(express.static(__dirname));

// Endpoint to receive photos from ESP32
app.post("/upload", upload.single("image"), (req, res) => {
  if (!req.file) {
    console.log("Upload failed: No file received");
    return res.status(400).json({ error: "No image file provided" });
  }

  console.log(`Photo received: ${req.file.filename} (${(req.file.size / 1024).toFixed(2)} KB)`);
  res.json({
    success: true,
    filename: req.file.filename,
    message: "Photo uploaded successfully",
  });
});

// Endpoint to get list of all photos
app.get("/api/photos", (req, res) => {
  try {
    const files = fs
      .readdirSync(photosDir)
      .filter((f) => f.endsWith(".jpg"))
      .map((f) => {
        const stats = fs.statSync(path.join(photosDir, f));
        return {
          name: f,
          size: stats.size,
          created: stats.birthtime,
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

    res.json({ photos: files });
  } catch (error) {
    res.status(500).json({ error: "Failed to list photos" });
  }
});

// Gallery page with live stream
app.get("/", (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>ESP32-CAM Timelapse Gallery</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
          background: #f5f5f5;
          padding: 20px;
        }
        .header {
          background: white;
          padding: 20px;
          border-radius: 8px;
          margin-bottom: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #333; margin-bottom: 10px; }
        .stats {
          display: flex;
          gap: 20px;
          margin-top: 15px;
          flex-wrap: wrap;
        }
        .stat {
          background: #007bff;
          color: white;
          padding: 10px 15px;
          border-radius: 4px;
          font-size: 14px;
        }
        .controls {
          background: white;
          padding: 15px;
          border-radius: 8px;
          margin-bottom: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .btn {
          display: inline-block;
          padding: 10px 20px;
          background: #007bff;
          color: white;
          text-decoration: none;
          border-radius: 4px;
          border: none;
          cursor: pointer;
          font-size: 14px;
        }
        .btn:hover { background: #0056b3; }
        .btn.secondary { background: #6c757d; }
        .btn.secondary:hover { background: #545b62; }
        .gallery {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
        }
        .photo-card {
          background: white;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          transition: transform 0.2s;
        }
        .photo-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .photo-card img {
          width: 100%;
          height: 250px;
          object-fit: cover;
          cursor: pointer;
        }
        .photo-info {
          padding: 15px;
        }
        .photo-name {
          font-weight: 600;
          color: #333;
          margin-bottom: 5px;
        }
        .photo-details {
          font-size: 12px;
          color: #666;
        }
        .modal {
          display: none;
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0,0,0,0.9);
          z-index: 1000;
          justify-content: center;
          align-items: center;
        }
        .modal.active { display: flex; }
        .modal img {
          max-width: 90%;
          max-height: 90%;
          object-fit: contain;
        }
        .modal-close {
          position: absolute;
          top: 20px;
          right: 40px;
          color: white;
          font-size: 40px;
          cursor: pointer;
        }
        .loading {
          text-align: center;
          padding: 40px;
          color: #666;
        }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>🎥 ESP32-CAM Timelapse Gallery</h1>
        <div class="stats">
          <div class="stat">📷 Photos: <span id="photoCount">0</span></div>
          <div class="stat">💾 Total Size: <span id="totalSize">0 MB</span></div>
          <div class="stat">🟢 Server Running</div>
        </div>
      </div>

      <div class="controls">
        <button class="btn" onclick="loadPhotos()">🔄 Refresh Photos</button>
        <button class="btn secondary" onclick="viewLatest()">👁️ View Latest Photo</button>
        <label style="margin-left: 15px; font-size: 14px;">
          <input type="checkbox" id="autoRefresh" onchange="toggleAutoRefresh()">
          Auto-refresh photos every 10s
        </label>
      </div>

      <div class="gallery" id="gallery">
        <div class="loading">Loading photos...</div>
      </div>

      <div class="modal" id="modal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImg" src="">
      </div>

      <script>
        let autoRefreshInterval = null;

        async function loadPhotos() {
          try {
            const response = await fetch('/api/photos');
            const data = await response.json();
            const gallery = document.getElementById('gallery');
            
            if (data.photos.length === 0) {
              gallery.innerHTML = '<div class="loading">No photos yet. Waiting for ESP32 to send images...</div>';
              document.getElementById('photoCount').textContent = '0';
              document.getElementById('totalSize').textContent = '0 MB';
              return;
            }

            const totalSize = data.photos.reduce((sum, p) => sum + p.size, 0);
            document.getElementById('photoCount').textContent = data.photos.length;
            document.getElementById('totalSize').textContent = (totalSize / (1024 * 1024)).toFixed(2);

            gallery.innerHTML = data.photos.map(photo => \`
              <div class="photo-card">
                <img src="/photos/\${photo.name}" alt="\${photo.name}" onclick="openModal('/photos/\${photo.name}')">
                <div class="photo-info">
                  <div class="photo-name">\${photo.name}</div>
                  <div class="photo-details">
                    \${(photo.size / 1024).toFixed(2)} KB<br>
                    \${new Date(photo.created).toLocaleString()}
                  </div>
                </div>
              </div>
            \`).join('');
          } catch (error) {
            console.error('Failed to load photos:', error);
            document.getElementById('gallery').innerHTML = '<div class="loading">Error loading photos</div>';
          }
        }

        function openModal(src) {
          document.getElementById('modalImg').src = src;
          document.getElementById('modal').classList.add('active');
        }

        function closeModal() {
          document.getElementById('modal').classList.remove('active');
        }

        function viewLatest() {
          const images = document.querySelectorAll('.photo-card img');
          if (images.length > 0) {
            const lastImage = images[images.length - 1];
            openModal(lastImage.src);
          }
        }

        function toggleAutoRefresh() {
          const checkbox = document.getElementById('autoRefresh');
          if (checkbox.checked) {
            autoRefreshInterval = setInterval(loadPhotos, 10000);
            console.log('Auto-refresh enabled');
          } else {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
            console.log('Auto-refresh disabled');
          }
        }

        // Load photos on page load
        loadPhotos();

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') closeModal();
          if (e.key === 'r' || e.key === 'R') loadPhotos();
        });
      </script>
    </body>
    </html>
  `);
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
