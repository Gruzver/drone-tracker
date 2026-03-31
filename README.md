# Drone Tracker

<div align="center">

**Real-time person detection and GPS geolocation from thermal drone video**

[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue?logo=ros&logoColor=white)](https://docs.ros.org/en/humble/)
[![Python 3.10](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-FF6B35?logo=pytorch&logoColor=white)](https://github.com/ultralytics/ultralytics)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## Overview

Drone Tracker is a ROS2-based pipeline that processes thermal drone video to detect, track, and geolocate people in real time. Each detected person is assigned a persistent tracking ID and a GPS coordinate derived from the drone's telemetry (altitude, orientation, FOV), then displayed on an interactive web map.

The system was developed for search-and-rescue and surveillance use cases using DJI thermal cameras. The YOLO detection model was trained via transfer learning on a custom thermal dataset of ~5,000 images.

---

## Pipeline Architecture

```
[MP4 Video + SRT Telemetry]
          │
          ▼
┌─────────────────────┐
│  video_publisher    │  Publishes frames → /camera/thermal/image_raw
│                     │  Publishes telemetry → /telemetry/drone/state
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  yolo_detection     │  YOLOv8 inference + persistent multi-object tracking
│                     │  → /detection/persons (PersonDetectionArray)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  georeferencing     │  Pixel → GPS via FOV projection + Kalman filter
│                     │  → /gps/persons_location (PersonLocationArray)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  map_server         │  Aggregates data, exports JSON + JPEG
│                     │  → /tmp/drone_map_data/
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Flask Web App      │  Dashboard: live video + Leaflet.js map
│  localhost:5000     │  Polling every 1s, person trajectories
└─────────────────────┘
```

---

## Features

- **Thermal person detection** — YOLOv8x fine-tuned on ~5,000 thermal frames from DJI drones
- **Persistent tracking** — Multi-object tracking with stable IDs across frames
- **GPS geolocation** — Pixel-to-GPS conversion using drone altitude, yaw/pitch/roll, and camera FOV
- **Kalman filter** — Trajectory smoothing on GPS coordinates to reduce jitter
- **Interactive map** — Real-time Leaflet.js dashboard showing person markers, trajectories, and drone FOV
- **DJI SRT parsing** — Automatic parsing of DJI `.SRT` telemetry files (GPS, altitude, gimbal angles, focal length)
- **One-command launch** — Single `ros2 launch` command starts the full pipeline

---

## ROS2 Packages

| Package | Description |
|---------|-------------|
| [`drone_bringup`](src/drone_bringup/) | Launch package — starts the full pipeline with one command |
| [`drone_tracker_msgs`](src/drone_tracker_msgs/) | Custom message types: `DroneState`, `PersonDetection`, `PersonLocation` and their arrays |
| [`video_publisher_node`](src/video_publisher_node/) | Reads MP4 + SRT, publishes frames and telemetry |
| [`yolo_detection_node`](src/yolo_detection_node/) | YOLOv8 inference with persistent tracking |
| [`georeferencing_node`](src/georeferencing_node/) | Pixel → GPS georeferencing with Kalman smoothing |
| [`map_server_node`](src/map_server_node/) | Data aggregation and JSON/image export for the web dashboard |
| [`drone_tracker_utils`](src/drone_tracker_utils/) | Shared utilities: `GeoCalculator`, `SRTParser`, `FOVVisualizer` |

---

## Detection Model

The YOLO model is trained separately in the [`detection/`](detection/) directory using a custom pipeline:

- **Base model**: YOLOv8x (pretrained on COCO)
- **Dataset**: ~4,900 thermal images (3,437 train / 736 val / 737 test)
- **Classes**: `person` (1 class)
- **Training**: 2-phase transfer learning — frozen backbone → full fine-tuning
- **Export**: ONNX FP16 for deployment

See [`detection/README.md`](detection/README.md) for the full training pipeline.

---

## Requirements

- ROS2 Humble
- Python 3.10+
- CUDA-capable GPU (recommended for real-time inference)

```bash
pip install ultralytics opencv-python flask folium numpy
```

Or install all dependencies:
```bash
pip install -r detection/requirements.txt
pip install -r web/requirements.txt
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/drone-tracker.git
cd drone-tracker

# Install ROS2 dependencies
rosdep install --from-paths src --ignore-src -r -y

# Build
colcon build
source install/setup.bash
```

---

## Usage

### Launch the full pipeline

```bash
# Default video
ros2 launch drone_bringup drone_tracker.launch.py

# Specify video and SRT
ros2 launch drone_bringup drone_tracker.launch.py \
    video_path:=/path/to/video.MP4

# All options
ros2 launch drone_bringup drone_tracker.launch.py \
    video_path:=/path/to/video.MP4 \
    conf_threshold:=0.4 \
    use_kalman:=true \
    keep_history:=true
```

### Launch parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `video_path` | *(configured in launch file)* | Path to thermal MP4 |
| `srt_path` | *(derived from video_path)* | Path to SRT telemetry; auto-derived if omitted |
| `publish_rate` | `30` | Video publish rate in Hz |
| `conf_threshold` | `0.5` | YOLO confidence threshold |
| `iou_threshold` | `0.45` | IoU threshold for NMS |
| `fov_horizontal` | `50.5` | Camera horizontal FOV in degrees |
| `use_kalman` | `true` | Enable Kalman filter for GPS smoothing |
| `max_distance` | `1000.0` | Maximum accepted GPS distance in meters |
| `keep_history` | `false` | Store full trajectory history |
| `output_dir` | `/tmp/drone_map_data` | Output directory for JSON and image exports |

### Open the dashboard

```bash
# In a separate terminal
cd web && python3 app.py

# Open in browser
http://localhost:5000
```

### Run nodes individually

```bash
ros2 run video_publisher_node video_publisher
ros2 run yolo_detection_node yolo_detector
ros2 run georeferencing_node georeferencer
ros2 run map_server_node map_server

# Optional: live detection viewer
ros2 run yolo_detection_node view_vision
```

---

## Debug Tools

Utility scripts in [`scripts/`](scripts/) for development and troubleshooting:

| Script | Purpose |
|--------|---------|
| `debug_bbox.py` | Validate bounding box → GPS conversion, visualize FOV corners |
| `debug_pixel_to_gps.py` | Step-by-step GPS calculation debug |
| `debug_timestamps.py` | ROS2 node for telemetry/detection timestamp sync diagnostics |
| `fov_visualizer_map.py` | Frame-by-frame FOV coverage on a Folium map |

```bash
python3 scripts/debug_bbox.py
python3 scripts/fov_visualizer_map.py
```

---

## Custom ROS2 Messages

```
DroneState
  timestamp, latitude, longitude
  altitude_rel, altitude_abs
  yaw, pitch, roll
  focal_len, dzoom_ratio

PersonDetection
  track_id, confidence
  bbox_x1, bbox_y1, bbox_x2, bbox_y2   # in 640×512 inference space
  centroid_x, centroid_y, timestamp

PersonLocation
  track_id, latitude, longitude
  distance_m, confidence, status, timestamp
```

---

## Project Structure

```
drone_ws/
├── src/                          # ROS2 packages
│   ├── drone_bringup/            # Launch package
│   ├── drone_tracker_msgs/       # Custom messages
│   ├── drone_tracker_utils/      # Shared utilities
│   ├── video_publisher_node/     # Video + telemetry publisher
│   ├── yolo_detection_node/      # YOLOv8 inference + tracking
│   ├── georeferencing_node/      # Pixel → GPS conversion
│   └── map_server_node/          # Data aggregation + export
├── detection/                    # Model training pipeline (YOLOv8)
├── web/                          # Flask web dashboard
├── scripts/                      # Debug and utility tools
└── docs/                         # Extended notes and project state
```

---

## Georeferencing Algorithm

1. Receive detection centroid in pixel space (640×512)
2. Normalize to `[-0.5, 0.5]` range
3. Compute subtended angle using horizontal/vertical FOV
4. Apply drone orientation corrections (yaw, pitch — roll reserved)
5. Calculate horizontal displacement in meters using trigonometry
6. Convert meter offset → lat/lon delta
7. Apply Kalman filter for temporal smoothing
8. Reject results with distance > `max_distance` meters

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  Built with ROS2 Humble · YOLOv8 · Python 3.10
</div>
