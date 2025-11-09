#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>

// ===================
// WiFi Configuration
// ===================
// IMPORTANT: Create config.h file with your credentials!
// See config.example.h for template
#include "config.h"

#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// ===========================
// Configuration
// ===========================
const unsigned long CAPTURE_INTERVAL = 10000; // 10 seconds (change this for different intervals)
unsigned long lastCaptureTime = 0;
int pictureNumber = 0;

void setup() {
  Serial.begin(115200);
  Serial.println();
  Serial.println("Starting ESP32-CAM Timelapse (WiFi Upload Mode)...");

  // Connect to WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected!");
  Serial.print("ESP32-CAM IP address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Server URL: ");
  Serial.println(serverUrl);

  // Camera configuration
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA; // High resolution
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 5; // 0-63, lower means higher quality
  config.fb_count = 1;
  
  // Adjust settings based on PSRAM availability
  if(psramFound()){
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }

  Serial.println("Camera initialized successfully!");
  Serial.printf("Capturing photos every %lu seconds and uploading to server\n", CAPTURE_INTERVAL/1000);
  Serial.println("Starting timelapse...");
}

void captureAndUploadPhoto() {
  // Take picture
  camera_fb_t * fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  Serial.printf("Photo captured: %d bytes\n", fb->len);
  
  // Upload to server
  if(WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    http.begin(serverUrl);
    
    // Generate timestamp-based filename
    String timestamp = String(millis());
    String filename = "photo_" + timestamp + ".jpg";
    
    // Create multipart form data
    String boundary = "----ESP32Boundary";
    String contentType = "multipart/form-data; boundary=" + boundary;
    http.addHeader("Content-Type", contentType);
    
    // Build the multipart form data body
    String bodyStart = "--" + boundary + "\r\n";
    bodyStart += "Content-Disposition: form-data; name=\"image\"; filename=\"" + filename + "\"\r\n";
    bodyStart += "Content-Type: image/jpeg\r\n\r\n";
    
    String bodyEnd = "\r\n--" + boundary + "--\r\n";
    
    // Calculate total length
    int totalLen = bodyStart.length() + fb->len + bodyEnd.length();
    
    // Prepare the complete payload
    uint8_t *payload = (uint8_t*)malloc(totalLen);
    if(!payload) {
      Serial.println("Failed to allocate memory for upload");
      esp_camera_fb_return(fb);
      return;
    }
    
    // Copy parts into payload
    memcpy(payload, bodyStart.c_str(), bodyStart.length());
    memcpy(payload + bodyStart.length(), fb->buf, fb->len);
    memcpy(payload + bodyStart.length() + fb->len, bodyEnd.c_str(), bodyEnd.length());
    
    // Send POST request
    Serial.print("Uploading to server... ");
    int httpResponseCode = http.POST(payload, totalLen);
    
    if(httpResponseCode > 0) {
      Serial.printf("Success! Server response: %d\n", httpResponseCode);
      String response = http.getString();
      Serial.println(response);
      pictureNumber++;
    } else {
      Serial.printf("Error: %s\n", http.errorToString(httpResponseCode).c_str());
      Serial.println("Make sure the server is running and the IP address is correct!");
    }
    
    free(payload);
    http.end();
  } else {
    Serial.println("WiFi Disconnected! Cannot upload photo.");
  }
  
  // Return the frame buffer back to the driver for reuse
  esp_camera_fb_return(fb);
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check if it's time to take a photo
  if (currentTime - lastCaptureTime >= CAPTURE_INTERVAL) {
    captureAndUploadPhoto();
    lastCaptureTime = currentTime;
  }
  
  delay(100);
}
