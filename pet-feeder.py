import sys
import os
import json
import asyncio
from datetime import datetime
from typing import List
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QTimeEdit, QLineEdit, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt, QTime, QTimer
from PyQt5.QtGui import QPixmap, QImage

from qasync import QEventLoop, asyncSlot

from viam.robot.client import RobotClient
from viam.components.board import Board
from viam.components.motor import Motor
from viam.components.camera import Camera

import torch
from ultralytics import YOLO
import cv2
import numpy as np

# --- Viam Credentials and Component Names ---
ROBOT_API_KEY = "az50dxbw0ddyuzl8ulb7osjxiavaexiy"
ROBOT_API_KEY_ID = "42efaa5a-fa77-4bc1-8bc3-91cf494d1584"
ROBOT_ADDRESS = "petfeeder-main.o8s889lyi5.viam.cloud"
STEPPER_NAME = "stepper"
BOARD_NAME = "pi"
CAMERA_NAME = "petcam"

# --- Default Schedule (HH:MM 24h format) ---
DEFAULT_SCHEDULE = ["06:00", "12:00", "16:02"]
SCHEDULE_FILE = "schedule.json"

class PetFeederApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Viam Pet Feeder Controller")
        self.setGeometry(200, 200, 520, 670)
        self.robot = None
        self.stepper = None
        self.camera = None
        self.schedule: List[str] = self.load_schedule()
        self.last_feed_time = None
        self.detect_enabled = False
        self.yolo_model = YOLO('yolov8n.pt')
        self.frame_count = 0
        self.detection_interval = 3  # Run detection every 3 frames
        self.last_detection_time = 0
        self.detection_cooldown = 0.5  # Minimum time between detections
        self.init_ui()
        self.loop = asyncio.get_event_loop()
        self.connected = False
        
        # Schedule timer - check every 30 seconds
        self.schedule_timer = QTimer()
        self.schedule_timer.timeout.connect(self.check_schedule)
        self.schedule_timer.start(30000)  # 30 seconds

        # Camera timer - refresh every 500ms for better performance
        self.camera_timer = QTimer()
        self.camera_timer.timeout.connect(self.refresh_camera_auto)
        self.camera_timer.start(500)  # 500ms = 2 FPS

    def load_schedule(self):
        if os.path.exists(SCHEDULE_FILE):
            try:
                with open(SCHEDULE_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"[SCHEDULE] Failed to load schedule: {e}")
        return DEFAULT_SCHEDULE.copy()

    def save_schedule(self):
        try:
            with open(SCHEDULE_FILE, "w") as f:
                json.dump(self.schedule, f)
        except Exception as e:
            print(f"[SCHEDULE] Failed to save schedule: {e}")

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 15px; background: #f7f7fa; }
            QPushButton { background: #3a7afe; color: white; border-radius: 8px; padding: 8px 18px; font-weight: 500; }
            QPushButton:disabled { background: #b0b0b0; }
            QListWidget { background: #fff; border-radius: 8px; border: 1px solid #e0e0e0; color: black; }
            QLabel { color: #222; }
        """)
        # Status
        self.status_label = QLabel("Status: Not connected")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #3a7afe;")
        layout.addWidget(self.status_label)
        # Connect button
        self.connect_btn = QPushButton("Connect to Robot")
        self.connect_btn.clicked.connect(self.on_connect)
        layout.addWidget(self.connect_btn)
        # Schedule
        sch_title = QLabel("Feeding Schedule (HH:MM):")
        sch_title.setStyleSheet("margin-top: 10px; font-weight: 500;")
        layout.addWidget(sch_title)
        self.schedule_list = QListWidget()
        self.schedule_list.addItems(self.schedule)
        self.schedule_list.setFixedHeight(100)
        layout.addWidget(self.schedule_list)
        sch_btns = QHBoxLayout()
        self.add_time_btn = QPushButton("Add Time")
        self.add_time_btn.clicked.connect(self.add_time)
        sch_btns.addWidget(self.add_time_btn)
        self.remove_time_btn = QPushButton("Remove Selected")
        self.remove_time_btn.clicked.connect(self.remove_time)
        sch_btns.addWidget(self.remove_time_btn)
        layout.addLayout(sch_btns)
        # Manual Feed
        self.feed_btn = QPushButton("Feed Now")
        self.feed_btn.clicked.connect(self.on_feed)
        self.feed_btn.setEnabled(False)
        layout.addWidget(self.feed_btn)
        # Camera
        cam_title = QLabel("Live Camera:")
        cam_title.setStyleSheet("margin-top: 10px; font-weight: 500;")
        layout.addWidget(cam_title)
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(400, 300)
        self.camera_label.setStyleSheet("background: #222; border-radius: 10px;")
        layout.addWidget(self.camera_label, alignment=Qt.AlignCenter)
        # Performance info
        self.perf_label = QLabel("Performance: 0 FPS | Detection: Off")
        self.perf_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(self.perf_label)
        # Toggle Object Detection
        self.detect_btn = QPushButton("Enable Cat/Dog Detection")
        self.detect_btn.setCheckable(True)
        self.detect_btn.setChecked(False)
        self.detect_btn.clicked.connect(self.toggle_detection)
        self.detect_btn.setEnabled(False)
        layout.addWidget(self.detect_btn)
        self.setLayout(layout)

    def toggle_detection(self):
        self.detect_enabled = self.detect_btn.isChecked()
        if self.detect_enabled:
            self.detect_btn.setText("Disable Cat/Dog Detection")
            self.perf_label.setText("Performance: 0 FPS | Detection: On")
        else:
            self.detect_btn.setText("Enable Cat/Dog Detection")
            self.perf_label.setText("Performance: 0 FPS | Detection: Off")

    @asyncSlot()
    async def on_connect(self):
        self.status_label.setText("Status: Connecting...")
        self.connect_btn.setEnabled(False)
        try:
            opts = RobotClient.Options.with_api_key(
                api_key=ROBOT_API_KEY,
                api_key_id=ROBOT_API_KEY_ID
            )
            self.robot = await RobotClient.at_address(ROBOT_ADDRESS, opts)
            print("Available components:", self.robot.resource_names)
            self.stepper = Motor.from_robot(self.robot, STEPPER_NAME)
            self.camera = Camera.from_robot(self.robot, CAMERA_NAME)
            self.connected = True
            self.status_label.setText("Status: Connected!")
            self.feed_btn.setEnabled(True)
            self.detect_btn.setEnabled(True)
        except Exception as e:
            self.status_label.setText(f"Status: Connection failed")
            QMessageBox.critical(self, "Connection Error", str(e))
            self.connect_btn.setEnabled(True)

    def add_time(self):
        time, ok = QInputDialog.getText(self, "Add Feeding Time", "Enter time (HH:MM):")
        if ok and time:
            try:
                datetime.strptime(time, "%H:%M")
                if time not in self.schedule:
                    self.schedule.append(time)
                    self.schedule.sort()
                    self.schedule_list.clear()
                    self.schedule_list.addItems(self.schedule)
                    self.save_schedule()
            except ValueError:
                QMessageBox.warning(self, "Invalid Time", "Please enter time in HH:MM format.")

    def remove_time(self):
        selected = self.schedule_list.currentRow()
        if selected >= 0:
            self.schedule.pop(selected)
            self.schedule_list.takeItem(selected)
            self.save_schedule()

    def check_schedule(self):
        """Check if it's time to feed based on the schedule"""
        if not self.connected or not self.stepper:
            return
            
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Check if current time matches any schedule time
        if current_time in self.schedule:
            # Prevent multiple feeds at the same time
            if self.last_feed_time != current_time:
                self.last_feed_time = current_time
                print(f"[SCHEDULE] Time to feed! Current time: {current_time}")
                # Trigger feeding asynchronously
                asyncio.create_task(self.scheduled_feed())

    @asyncSlot()
    async def scheduled_feed(self):
        """Perform a scheduled feed"""
        if not self.connected or not self.stepper:
            return
            
        self.status_label.setText("Status: Scheduled feeding...")
        try:
            print("[SCHEDULE] Scheduled feeding started")
            await self.stepper.go_for(rpm=500, revolutions=-3)
            await self.stepper.stop()
            self.status_label.setText("Status: Scheduled feed complete!")
            print("[SCHEDULE] Scheduled feeding complete")
        except Exception as e:
            print(f"[SCHEDULE] Scheduled feed error: {e}")
            self.status_label.setText("Status: Scheduled feed failed!")

    @asyncSlot()
    async def on_feed(self):
        if not self.connected or not self.stepper:
            QMessageBox.warning(self, "Not Connected", "Connect to the robot first.")
            return
        self.feed_btn.setEnabled(False)
        self.status_label.setText("Status: Feeding...")
        try:
            print("[DEBUG] Feeding started")
            await self.stepper.go_for(rpm=500, revolutions=-3)
            await self.stepper.stop()
            self.status_label.setText("Status: Feed complete!")
            print("[DEBUG] Feeding complete")
        except Exception as e:
            print(f"[DEBUG] Feed error: {e}")
            QMessageBox.critical(self, "Feed Error", str(e))
            self.status_label.setText("Status: Feed failed!")
        finally:
            print("[DEBUG] Re-enabling feed button")
            self.feed_btn.setEnabled(True)

    def refresh_camera_auto(self):
        if self.connected and self.camera:
            asyncio.create_task(self._refresh_camera(auto=True))

    async def _refresh_camera(self, auto=False):
        if not self.connected or not self.camera:
            return
        try:
            start_time = time.time()
            viam_img = await self.camera.get_image(mime_type="image/jpeg")
            if hasattr(viam_img, 'data'):
                img_bytes = viam_img.data
            else:
                img_bytes = viam_img
            np_img = np.frombuffer(img_bytes, np.uint8)
            cv_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            
            # Smart detection: only run detection periodically and when enabled
            should_detect = (self.detect_enabled and 
                           self.frame_count % self.detection_interval == 0 and
                           time.time() - self.last_detection_time > self.detection_cooldown)
            
            if should_detect:
                self.last_detection_time = time.time()
                try:
                    results = self.yolo_model(cv_img, verbose=False)  # Disable verbose output
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                conf = box.conf[0].cpu().numpy()
                                cls = int(box.cls[0].cpu().numpy())
                                label = self.yolo_model.names[cls]
                                if label in ["cat", "dog"]:
                                    color = (58, 122, 254) if label == "dog" else (255, 99, 71)
                                    cv2.rectangle(cv_img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                                    cv2.putText(cv_img, f"{label} {conf:.2f}", (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                except Exception as e:
                    print(f"Detection error: {e}")
            
            # Optimize image conversion
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            pixmap = pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_label.setPixmap(pixmap)
            
            # Update performance metrics
            frame_time = time.time() - start_time
            fps = 1.0 / frame_time if frame_time > 0 else 0
            self.frame_count += 1
            
            # Update performance label every 10 frames
            if self.frame_count % 10 == 0:
                detect_status = "On" if self.detect_enabled else "Off"
                self.perf_label.setText(f"Performance: {fps:.1f} FPS | Detection: {detect_status}")
            
            if not auto:
                self.status_label.setText("Status: Camera updated!")
        except Exception as e:
            if not auto:
                QMessageBox.critical(self, "Camera Error", str(e))
                self.status_label.setText("Status: Camera failed!")


def main():
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = PetFeederApp()
    window.show()
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()