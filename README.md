# Smart Robotic Arm Color Sorting System

> **Automated color-based object sorting using Computer Vision, Inverse Kinematics, IoT, and a real-time Web Dashboard**

**Lebanese International University — School of Engineering**
**CENG495 Senior Project — Spring 2025–2026**

**Team:** Hussam Zahraman · Mosaab Zein · Oday Kassar
**Supervisor:** Dr. Bilal Daass

---

## Table of Contents

- [Project Overview](#project-overview)
- [System Demo](#system-demo)
- [Features](#features)
- [Hardware Components](#hardware-components)
- [Software Stack](#software-stack)
- [System Architecture](#system-architecture)
- [Inverse Kinematics](#inverse-kinematics)
- [Installation and Setup](#installation-and-setup)
- [How to Run](#how-to-run)
- [File Structure](#file-structure)
- [Results](#results)
- [Future Work](#future-work)
- [License](#license)

---

## Project Overview

This project presents a complete low-cost intelligent system for automatic color-based object sorting using a 6-DOF robotic arm. The system integrates computer vision, embedded Inverse Kinematics, wireless WiFi communication, a real-time web dashboard, and a MySQL database — all at a total hardware cost of approximately **$128**.

The system detects the color and real-world position of colored blocks placed in a calibrated workspace zone using a USB webcam and the OpenCV library. It then computes the required servo joint angles using an embedded Inverse Kinematics solver on the ESP8266 microcontroller, moves the arm to pick up the block, and places it into the correct sorting box.

```
[ PHOTO HERE — Overview of the complete system on the workbench ]
```

---

## System Demo

```
[ PHOTO HERE — GIF or screenshot of the arm sorting a red block ]
```

```
[ PHOTO HERE — Screenshot of the web dashboard showing live statistics ]
```

---

## Features

- **Real-time color detection** — Red, Blue, and Green using HSV thresholding and perspective transform
- **Dynamic position detection** — converts pixel coordinates to real-world centimeters
- **Inverse Kinematics** — computes Base, Shoulder, Elbow 1, and Elbow 2 joint angles from any target position
- **Wireless control** — ESP8266 receives commands over local WiFi via HTTP POST
- **Real-time web dashboard** — live statistics, servo gamepad, arm status
- **Admin analytics dashboard** — daily, weekly, hourly, color comparison, and accuracy charts powered by Chart.js
- **MySQL database** — persistent storage of all sorting events
- **Anti-duplicate detection** — position-based tracking prevents counting the same block twice
- **Smooth servo movement** — 2 PWM step interpolation per 10ms for fluid motion

---

## Hardware Components

| Component | Model | Quantity | Cost |
|---|---|---|---|
| 6-DOF Robotic Arm | ROT3U Aluminum | 1 | $90 |
| Servo Motors | MG996R 11kg.cm | 6 | included |
| Microcontroller | ESP8266 NodeMCU | 1 | $5 |
| PWM Driver | PCA9685 16-ch I2C | 1 | $5 |
| Webcam | USB 720p | 1 | $10 |
| Power Supply | 6V / 5A | 1 | $10 |
| Base + Boxes | Wooden board | 1 set | $8 |
| **Total** | | | **~$128** |

```
[ PHOTO HERE — All hardware components laid out ]
```

### Wiring

| PCA9685 Pin | ESP8266 Pin | Function |
|---|---|---|
| SDA | D2 (GPIO4) | I2C data |
| SCL | D1 (GPIO5) | I2C clock |
| VCC | 3.3V | Logic power |
| V+ | External 6V | Servo power |

### Servo Channel Mapping

| Channel | Joint | Direction | Home PWM |
|---|---|---|---|
| ch0 | Base | Horizontal rotation | 370 |
| ch1 | Shoulder | Vertical (reversed) | 360 |
| ch2 | Elbow 1 | Vertical | 200 |
| ch4 | Gripper | Open / Close | 320 |
| ch5 | Elbow 2 | Vertical | 200 |

```
[ PHOTO HERE — Wiring diagram of ESP8266 to PCA9685 to servos ]
```

---

## Software Stack

### Laptop Side (Python)

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Main language |
| OpenCV | 4.8+ | Camera capture and image processing |
| NumPy | 1.24+ | Array operations |
| Flask | 2.3+ | Web server and REST API |
| Flask-SocketIO | 5.3+ | WebSocket real-time updates |
| mysql-connector-python | 8.1+ | MySQL database connection |
| Requests | 2.31+ | HTTP client for ESP8266 |

### Frontend

| Tool | Purpose |
|---|---|
| HTML / CSS / JavaScript | Dashboard UI |
| Socket.IO JS Client | Real-time WebSocket connection |
| Chart.js | Admin analytics charts |

### ESP8266 Firmware (C++)

| Library | Purpose |
|---|---|
| Arduino IDE + ESP8266 core | Development environment |
| Adafruit PCA9685 | PWM servo control over I2C |
| ArduinoJson | JSON parsing from HTTP requests |
| ESP8266WiFi + ESP8266WebServer | WiFi and HTTP server |

### Database

| Tool | Purpose |
|---|---|
| MySQL via XAMPP | Local database server |
| phpMyAdmin | Visual database management |

---

## System Architecture

The system follows a four-layer architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER                          │
│   USB Webcam → OpenCV detect.py → Flask /detect             │
│   (perspective transform · HSV · contour · pixel→cm)        │
└─────────────────────────────┬───────────────────────────────┘
                              │ HTTP POST
┌─────────────────────────────▼───────────────────────────────┐
│                 PROCESSING & COMMUNICATION LAYER             │
│   Flask Server ──WiFi──► ESP8266 ──I2C──► PCA9685 ──► Arm  │
│                ◄── POST /done ──────────────────────────────│
└───────────────┬─────────────────────────────────────────────┘
                │ WebSocket · REST
┌───────────────▼─────────────────────────────────────────────┐
│                   PRESENTATION LAYER                         │
│   Web Dashboard (Live Stats · Gamepad)                       │
│   Admin Dashboard (Charts · Accuracy · History)             │
└───────────────┬─────────────────────────────────────────────┘
                │ SQL queries
┌───────────────▼─────────────────────────────────────────────┐
│                      DATA LAYER                              │
│   MySQL sorting_db → sorting_events table                    │
│   id · color · x · y · timestamp · success                  │
└─────────────────────────────────────────────────────────────┘
```

```
[ PHOTO HERE — System architecture diagram ]
```

---

## Inverse Kinematics

The IK solver is embedded in the ESP8266 firmware. Given the target position (x, y) in centimeters:

**Step 1 — Base angle:**
```
Θ₀ = atan2(y, x) + 10°
```

**Step 2 — Distances:**
```
r   = √(x² + y²)
z   = −L1
D   = √(r² + z²)
L34 = L3 + L4 = 24 cm
```

**Step 3 — Elbow angle:**
```
Θ_elbow = acos((D² − L2² − L34²) / (2 · L2 · L34))
```

**Step 4 — Shoulder angle:**
```
α  = atan2(−z, r)
β  = atan2(L34 · sin(Θ_elbow), L2 + L34 · cos(Θ_elbow))
Θ₁ = α − β
```

**Step 5 — Elbow distribution:**
```
Θ₂ = Θ₃ = Θ_elbow / 2
```

### Link Lengths

| Link | From | To | Length |
|---|---|---|---|
| L1 | Base | Shoulder | 9.5 cm |
| L2 | Shoulder | Elbow 1 | 10.5 cm |
| L3 | Elbow 1 | Elbow 2 | 9.5 cm |
| L4 | Elbow 2 | Gripper | 14.5 cm |
| L34 | Combined | Elbow 1 → Gripper | 24.0 cm |

```
[ PHOTO HERE — IK geometry diagram showing all angles and link lengths ]
```

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/robotic-arm-sorting.git
cd robotic-arm-sorting
```

### 2. Install Python Dependencies

```bash
pip install flask flask-socketio requests opencv-python numpy mysql-connector-python
```

### 3. Setup XAMPP

- Download and install XAMPP from [apachefriends.org](https://apachefriends.org)
- Start **Apache** and **MySQL** from the XAMPP Control Panel
- The database and table will be created automatically when you run `app.py`

### 4. Configure the ESP8266 Firmware

Open `esp_firmware/esp_final.ino` in Arduino IDE and update:

```cpp
const char* ssid     = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
```

Also update the Flask server IP in the firmware to match your laptop's local IP address.

Add the ESP8266 board to Arduino IDE:
- Go to **File → Preferences**
- Add this URL to Additional Board Manager URLs:
```
http://arduino.esp8266.com/stable/package_esp8266com_index.json
```
- Install **ESP8266 by ESP8266 Community** from Board Manager

Install required Arduino libraries via Library Manager:
- Adafruit PWM Servo Driver Library
- ArduinoJson

Upload the firmware to the ESP8266 using:
- Board: **NodeMCU 1.0 (ESP-12E Module)**
- Upload Speed: **115200**

### 5. Camera Calibration

Run the calibration script and click the four corners of the workspace zone:

```bash
python calibrate.py
```

Copy the printed `ZONE_POINTS` coordinates into `detect.py`.

---

## How to Run

### Step 1 — Start XAMPP

Open XAMPP Control Panel and start Apache and MySQL.

### Step 2 — Start Flask Server

```bash
python app.py
```

You should see:
```
Database ready!
Running on http://0.0.0.0:5000
```

### Step 3 — Start Camera Detection

```bash
python detect.py
```

You should see:
```
Camera running — press Q to quit | press R to reset counted blocks
```

### Step 4 — Open the Dashboard

Open your browser and go to:
- **Main Dashboard:** `http://127.0.0.1:5000`
- **Admin Analytics:** `http://127.0.0.1:5000/admin`

### Step 5 — Place Blocks

Place colored blocks inside the marked workspace zone. The system will:
1. Detect the color and position
2. Send coordinates to the ESP8266
3. Move the arm to pick up the block
4. Sort it into the correct box
5. Update the dashboard in real time

**Keyboard shortcuts in the detection window:**
- `Q` — quit
- `R` — reset the counted blocks list

---

## File Structure

```
robotic-arm-sorting/
│
├── app.py                  # Flask web server — all routes and API
├── detect.py               # Camera capture and color detection
│
├── templates/
│   ├── index.html          # Main web dashboard
│   └── admin.html          # Admin analytics dashboard
│
├── esp_firmware/
│   └── esp_final.ino       # ESP8266 firmware — IK solver + servo control
│
└── README.md
```

---

## Results

The system was tested over 30 consecutive sorting trials under stable indoor lighting:

| Metric | Result |
|---|---|
| Total trials | 30 blocks |
| Successfully sorted | 28 blocks |
| Success rate | 93.3% |
| Color detection accuracy | 95% |
| Average cycle time | 8–10 seconds |
| Total hardware cost | ~$128 |

```
[ PHOTO HERE — Results table or chart ]
```

```
[ PHOTO HERE — Arm sorting a block during live testing ]
```

---

## Future Work

- **Conveyor belt** — automatic block feeding without manual placement
- **More colors** — extend HSV thresholds beyond Red, Blue, and Green
- **Cloud deployment** — host the dashboard online for remote access
- **Machine learning** — replace HSV thresholding with a trained CNN model
- **ESP32-CAM** — remove the laptop dependency with onboard image processing
- **Wrist IK** — add wrist angle control for more precise gripping

---

## License

This project was developed as a senior project at the Lebanese International University and is shared for educational purposes.

---

*Lebanese International University — CENG495 — Spring 2025–2026*
*Hussam Zahraman · Mosaab Zein · Oday Kassar*
