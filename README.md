# Pet Feeder Desktop App

A modern PyQt5 desktop application to control your Viam-powered pet feeder robot with **real-time cat/dog detection** using YOLOv8.

## 🚀 Features

- **🤖 Manual & Scheduled Feeding**: Instant feeding and customizable schedules
- **📹 Live Camera Feed**: Real-time video with 2 FPS refresh rate
- **🐱🐶 AI-Powered Detection**: YOLOv8-based cat and dog detection with bounding boxes
- **⚡ Performance Optimized**: Smart detection intervals and efficient processing
- **🎨 Modern UI**: Clean, responsive interface with performance monitoring
- **💾 Persistent Schedule**: Automatic saving and loading of feeding schedules
- **📊 Real-time Metrics**: Live FPS counter and detection status

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- Viam robot with camera and motor components
- Your Viam API credentials

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ZACHARY2215/pet-feeder.git
   cd pet-feeder
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your Viam credentials:**
   Edit `pet-feeder.py` and update these variables:
   ```python
   ROBOT_API_KEY = "your_api_key"
   ROBOT_API_KEY_ID = "your_api_key_id"
   ROBOT_ADDRESS = "your_robot_address"
   STEPPER_NAME = "your_motor_name"
   CAMERA_NAME = "your_camera_name"
   ```

## 🎯 Usage

1. **Run the app:**
   ```bash
   python pet-feeder.py
   ```

2. **Connect to your robot** by clicking "Connect to Robot"

3. **Manage feeding schedule:**
   - Add/remove feeding times (HH:MM format)
   - Schedule is automatically saved to `schedule.json`

4. **Use manual feeding:**
   - Click "Feed Now" for instant feeding

5. **Enable AI detection:**
   - Toggle "Enable Cat/Dog Detection" to see bounding boxes
   - Detection runs every 3rd frame for optimal performance

6. **Monitor performance:**
   - View real-time FPS counter
   - See detection status in the UI

## 🔧 Technical Details

### Performance Optimizations
- **2 FPS Camera**: Double the refresh rate (500ms intervals)
- **Smart Detection**: Only runs every 3rd frame to save CPU
- **Efficient Processing**: Optimized image conversion pipeline
- **Memory Management**: Automatic cleanup of large files

### AI Detection Features
- **Model**: YOLOv8n (nano) - 6MB, optimized for speed
- **Dataset**: COCO (80 classes including cats and dogs)
- **Accuracy**: High precision for pet detection
- **Real-time**: Bounding boxes with confidence scores

### File Structure
```
pet-feeder/
├── pet-feeder.py          # Main application
├── requirements.txt       # Python dependencies
├── schedule.json         # Feeding schedule (auto-generated)
├── README.md             # This file
└── .gitignore           # Excludes large files
```

## 📋 Dependencies

- **PyQt5**: Desktop GUI framework
- **qasync**: Async support for PyQt5
- **viam-sdk**: Viam robot control
- **ultralytics**: YOLOv8 object detection
- **torch**: PyTorch for AI models
- **opencv-python**: Computer vision
- **numpy**: Numerical computing

## 🎨 UI Features

- **Modern Design**: Clean, professional interface
- **Performance Monitoring**: Real-time FPS and status
- **Responsive Layout**: Adapts to different screen sizes
- **Color-coded Detection**: Blue for dogs, red for cats
- **Black Schedule Text**: Improved readability

## 🔍 Troubleshooting

- **Connection Issues**: Check your Viam credentials and robot status
- **Detection Not Working**: Ensure the toggle is enabled and camera is connected
- **Performance Issues**: The app automatically optimizes detection frequency
- **Model Download**: YOLOv8n model downloads automatically on first run

## 📝 Notes

- The YOLO model (`yolov8n.pt`) downloads automatically (~6MB)
- Schedule is saved in `schedule.json` and persists between sessions
- Detection can be toggled on/off to balance performance vs features
- The app handles connection drops gracefully and reconnects automatically

## 📄 License

MIT License - Feel free to use and modify for your projects!

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests. 
