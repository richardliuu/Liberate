import cv2
import numpy as np
import pyautogui
import mediapipe as mp
import time
from collections import deque

class FacialTracker:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Screen dimensions
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Smoothing settings
        self.smoothing_factor = 10
        self.x_points = deque(maxlen=self.smoothing_factor)
        self.y_points = deque(maxlen=self.smoothing_factor)
        
        # Tracking settings
        self.sensitivity = 3.5
        self.click_threshold = 0.05
        self.last_click_time = 0
        self.click_cooldown = 0.5  
        
        # Triple click for keyboard
        self.mouth_open_count = 0
        self.mouth_open_timer = time.time()
        self.mouth_open_window = 2.0  
        self.keyboard_active = False
        
        # Calibration variables
        self.calibrated = False
        self.neutral_x = 0.5
        self.neutral_y = 0.5
        self.calibration_frames = 30
        self.calibration_count = 0
        
        # Face landmarks for tracking
        self.NOSE_TIP = 1
        self.UPPER_LIP = 13
        self.LOWER_LIP = 14
        self.FOREHEAD = 10
        self.CHIN = 152
        
        # Debug info
        self.debug_info = {}
    
    def calibrate(self, frame):
        """
        Calibrate function to determine the general centerpoint of the webcam for the facial mouse controller
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            nose_x = landmarks[self.NOSE_TIP].x
            nose_y = landmarks[self.NOSE_TIP].y
            
            # Accumulate calibration frames
            self.calibration_count += 1
            
            # Draw visual feedback
            height, width, _ = frame.shape
            cv2.putText(
                frame,
                f"Calibrating: {self.calibration_count}/{self.calibration_frames}",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # Mark nose position
            nose_x_pixel = int(nose_x * width)
            nose_y_pixel = int(nose_y * height)
            cv2.circle(frame, (nose_x_pixel, nose_y_pixel), 5, (0, 255, 0), -1)
            
            # When enough frames collected, finalize calibration
            if self.calibration_count >= self.calibration_frames:
                self.neutral_x = nose_x
                self.neutral_y = nose_y
                self.calibrated = True
                self.x_points.clear()
                self.y_points.clear()
                return True
        else:
            # If face not detected during calibration
            cv2.putText(
                frame,
                "No face detected! Please look at the camera",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            
        return False
    
    def track_face(self, frame):
        if not self.calibrated:
            return None
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        height, width, _ = frame.shape
        
        if not results.multi_face_landmarks:
            cv2.putText(
                frame,
                "Face not detected",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
            return None
            
        # Get landmarks
        landmarks = results.multi_face_landmarks[0].landmark
        nose_x = landmarks[self.NOSE_TIP].x
        nose_y = landmarks[self.NOSE_TIP].y
        
        # Calculate cursor position based on head movement
        offset_x = (nose_x - self.neutral_x) * self.sensitivity
        offset_y = (nose_y - self.neutral_y) * self.sensitivity
        
        # Map to screen coordinates
        target_x = self.screen_width * (0.5 + offset_x)
        target_y = self.screen_height * (0.5 + offset_y)
        
        # Apply smoothing
        self.x_points.append(target_x)
        self.y_points.append(target_y)
        
        if len(self.x_points) > 0 and len(self.y_points) > 0:
            smoothed_x = sum(self.x_points) / len(self.x_points)
            smoothed_y = sum(self.y_points) / len(self.y_points)
            
            # Draw tracking info on frame
            nose_x_pixel = int(nose_x * width)
            nose_y_pixel = int(nose_y * height)
            
            # Draw face tracking indicators
            cv2.circle(frame, (nose_x_pixel, nose_y_pixel), 5, (0, 255, 0), -1)
            
            neutral_x_pixel = int(self.neutral_x * width)
            neutral_y_pixel = int(self.neutral_y * height)
            cv2.circle(frame, (neutral_x_pixel, neutral_y_pixel), 3, (0, 0, 255), -1)
            
            # Draw mouth state
            mouth_open = self.detect_mouth_open(landmarks)
            if mouth_open:
                cv2.putText(
                    frame,
                    "Mouth: OPEN",
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )
            else:
                cv2.putText(
                    frame,
                    "Mouth: closed",
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    1
                )
                
            # Draw keyboard status
            keyboard_status = "ACTIVE" if self.keyboard_active else "inactive"
            keyboard_color = (0, 255, 0) if self.keyboard_active else (255, 0, 0)
            thickness = 2 if self.keyboard_active else 1
            
            cv2.putText(
                frame,
                f"Keyboard: {keyboard_status}",
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                keyboard_color,
                thickness
            )
            
            # Update debug info
            self.debug_info = {
                "nose_position": (nose_x, nose_y),
                "neutral_position": (self.neutral_x, self.neutral_y),
                "offset": (offset_x, offset_y),
                "cursor": (int(smoothed_x), int(smoothed_y)),
                "mouth_open": mouth_open,
                "mouth_count": self.mouth_open_count,
                "keyboard_active": self.keyboard_active
            }
            
            return (int(smoothed_x), int(smoothed_y))
            
        return None
    
    def detect_mouth_open(self, landmarks):
        """Detect if mouth is open based on lip distance"""
        upper_lip = landmarks[self.UPPER_LIP]
        lower_lip = landmarks[self.LOWER_LIP]
        
        # Calculate vertical distance between lips
        mouth_distance = abs(upper_lip.y - lower_lip.y)
        
        # Calculate face height for normalization
        face_height = abs(landmarks[self.FOREHEAD].y - landmarks[self.CHIN].y)
        
        # Normalized mouth openness
        mouth_ratio = mouth_distance / face_height
        
        return mouth_ratio > self.click_threshold
    
    def check_mouth_open(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return False
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Check if mouth is open
        mouth_open = self.detect_mouth_open(landmarks)
        
        # Handle mouth open/close state changes for click detection
        current_time = time.time()
        
        if mouth_open:
            # Registers a new mouth open only after mouth was closed
            if current_time - self.last_click_time > self.click_cooldown:
                self.last_click_time = current_time
                
                # Track multiple mouth opens for keyboard toggle
                self.mouth_open_count += 1
                if current_time - self.mouth_open_timer > self.mouth_open_window:
                    # Reset counter if too much time passed
                    # This vaule could be changed to 
                    self.mouth_open_count = 1
                    self.mouth_open_timer = current_time
                """
                Keyboard component has yet to be implemented.
                Look back to the big file draft that contains it 
                """
                # Check for triple click to toggle keyboard
                if self.mouth_open_count >= 3:
                    self.keyboard_active = not self.keyboard_active
                    self.mouth_open_count = 0
                    print(f"Keyboard {'activated' if self.keyboard_active else 'deactivated'}")
                    return False 
                
                return True
                
        return False
    
    def release(self):
        """Clean up resources"""
        self.face_mesh.close()