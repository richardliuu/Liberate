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
        
        # Keyboard toggle
        self.mouth_open_count = 0
        self.mouth_open_timer = time.time()
        self.mouth_open_window = 2.0  
        self.keyboard_active = False
        
        # Calibration
        self.calibrated = False
        self.neutral_x = 0.5
        self.neutral_y = 0.5
        self.calibration_frames = 30
        self.calibration_count = 0
        
        # Face landmarks
        self.NOSE_TIP = 1
        self.UPPER_LIP = 13
        self.LOWER_LIP = 14
        self.LEFT_CHEEK = 123
        self.RIGHT_CHEEK = 352
        self.FOREHEAD = 10
        self.CHIN = 152
        self.LEFT_EYE_TOP = 159  
        self.RIGHT_EYE_TOP = 386
        self.LEFT_EYE_BOTTOM = 145
        self.RIGHT_EYE_BOTTOM = 374
        
        # Cheek inflation settings
        self.scroll_mode_active = False
        self.cheek_inflation_threshold = 0.04  # More reliable threshold
        self.scroll_speed = 30
        self.scroll_cooldown = 0.15
        self.neutral_cheek_distance = None
        self.cheek_inflation_frames = 0
        self.activation_threshold = 10  # Frames needed to activate
        
        # Debug info
        self.debug_info = {}
    
    def calibrate(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            nose_x = landmarks[self.NOSE_TIP].x
            nose_y = landmarks[self.NOSE_TIP].y
            
            self.calibration_count += 1
            
            # Visual feedback
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
            cv2.circle(frame, 
                      (int(nose_x * width), int(nose_y * height)), 
                      5, (0, 255, 0), -1)
            
            if self.calibration_count >= self.calibration_frames:
                self.neutral_x = nose_x
                self.neutral_y = nose_y
                
                # Calculate neutral cheek distance (using y-coordinate difference)
                left_cheek = landmarks[self.LEFT_CHEEK]
                right_cheek = landmarks[self.RIGHT_CHEEK]
                self.neutral_cheek_distance = abs(left_cheek.y - right_cheek.y)
                
                self.calibrated = True
                self.x_points.clear()
                self.y_points.clear()
                return True
        else:
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
    
    def detect_cheek_inflation(self, landmarks):
        """Improved cheek inflation detection using multiple landmarks"""
        if self.neutral_cheek_distance is None:
            return False
            
        # Calculate current cheek expansion
        current_distance = abs(landmarks[self.LEFT_CHEEK].y - landmarks[self.RIGHT_CHEEK].y)
        cheek_expansion = current_distance - self.neutral_cheek_distance
        
        # Additional check using mouth corners (more reliable)
        mouth_width = abs(landmarks[61].x - landmarks[291].x)  # Mouth corner indices
        face_width = abs(landmarks[234].x - landmarks[454].x)  # Ear to ear
        mouth_ratio = mouth_width / face_width
        
        # Combined detection - requires both cheek expansion and mouth compression
        return (cheek_expansion > self.cheek_inflation_threshold and 
                mouth_ratio < 0.25)  # Mouth gets narrower when puffing cheeks
    
    def detect_gaze_direction(self, landmarks):
        """More robust gaze detection using eye landmarks"""
        # Calculate eye openness ratios
        left_eye_h = abs(landmarks[self.LEFT_EYE_TOP].y - landmarks[self.LEFT_EYE_BOTTOM].y)
        right_eye_h = abs(landmarks[self.RIGHT_EYE_TOP].y - landmarks[self.RIGHT_EYE_BOTTOM].y)
        left_eye_w = abs(landmarks[33].x - landmarks[133].x)  # Left eye corners
        right_eye_w = abs(landmarks[362].x - landmarks[263].x) # Right eye corners
        
        left_ratio = left_eye_h / left_eye_w
        right_ratio = right_eye_h / right_eye_w
        avg_ratio = (left_ratio + right_ratio) / 2
        
        if avg_ratio < 0.2:   # Eyes more closed = looking down
            return "down"
        elif avg_ratio > 0.3: # Eyes more open = looking up
            return "up"
        return "neutral"
    
    def handle_scrolling(self, frame, landmarks):
        """Improved scrolling that doesn't disable mouse control"""
        current_time = time.time()
        cheek_inflated = self.detect_cheek_inflation(landmarks)
        
        if cheek_inflated:
            self.cheek_inflation_frames += 1
            
            # Only activate after consistent detection
            if self.cheek_inflation_frames >= self.activation_threshold:
                if not self.scroll_mode_active:
                    self.scroll_mode_active = True
                    cv2.putText(frame, "SCROLL MODE ACTIVATED", (20, 140),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
                
                # Perform scrolling based on gaze
                if current_time - self.last_click_time > self.scroll_cooldown:
                    gaze_dir = self.detect_gaze_direction(landmarks)
                    self.last_click_time = current_time
                    
                    if gaze_dir == "up":
                        pyautogui.scroll(self.scroll_speed)
                        return "up"
                    elif gaze_dir == "down":
                        pyautogui.scroll(-self.scroll_speed)
                        return "down"
        else:
            self.cheek_inflation_frames = 0
            if self.scroll_mode_active:
                cv2.putText(frame, "SCROLL MODE OFF", (20, 140),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
            self.scroll_mode_active = False
        
        return None
    
    def detect_mouth_open(self, landmarks):
        """Vertical mouth opening detection (for clicks)"""
        mouth_dist = abs(landmarks[self.UPPER_LIP].y - landmarks[self.LOWER_LIP].y)
        face_height = abs(landmarks[self.FOREHEAD].y - landmarks[self.CHIN].y)
        return (mouth_dist / face_height) > self.click_threshold
    
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
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Handle scrolling (runs alongside cursor tracking)
        scroll_action = self.handle_scrolling(frame, landmarks)
        
        # Always track cursor (scrolling doesn't disable it)
        nose_x = landmarks[self.NOSE_TIP].x
        nose_y = landmarks[self.NOSE_TIP].y
        
        # Calculate cursor position
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
            
            # Draw tracking visuals
            nose_pixel = (int(nose_x * width), int(nose_y * height))
            neutral_pixel = (int(self.neutral_x * width), int(self.neutral_y * height))
            
            cv2.circle(frame, nose_pixel, 5, (0, 255, 0), -1)
            cv2.circle(frame, neutral_pixel, 3, (0, 0, 255), -1)
            
            # Display status information
            status_y = 80
            mouth_status = "OPEN" if self.detect_mouth_open(landmarks) else "closed"
            mouth_color = (0, 255, 0) if mouth_status == "OPEN" else (255, 0, 0)
            cv2.putText(
                frame,
                f"Mouth: {mouth_status}",
                (20, status_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                mouth_color,
                2 if mouth_status == "OPEN" else 1
            )
            status_y += 30
            
            keyboard_status = "ACTIVE" if self.keyboard_active else "inactive"
            keyboard_color = (0, 255, 0) if self.keyboard_active else (255, 0, 0)
            cv2.putText(
                frame,
                f"Keyboard: {keyboard_status}",
                (20, status_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                keyboard_color,
                2 if self.keyboard_active else 1
            )
            status_y += 30
            
            # Display scroll status if active
            if self.scroll_mode_active:
                scroll_color = (0, 255, 255)
                cv2.putText(
                    frame,
                    "SCROLL MODE: ON",
                    (20, status_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    scroll_color,
                    2
                )
                status_y += 30
            
            # Visual feedback for scrolling action
            if scroll_action == "up":
                cv2.putText(
                    frame,
                    "SCROLLING UP",
                    (width//2 - 100, height - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )
            elif scroll_action == "down":
                cv2.putText(
                    frame,
                    "SCROLLING DOWN",
                    (width//2 - 100, height - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )
            
            return (int(smoothed_x), int(smoothed_y))
        
        return None
    
    def check_mouth_open(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return False
            
        landmarks = results.multi_face_landmarks[0].landmark
        current_time = time.time()
        
        if self.detect_mouth_open(landmarks):
            if current_time - self.last_click_time > self.click_cooldown:
                self.last_click_time = current_time
                self.mouth_open_count += 1
                
                if current_time - self.mouth_open_timer > self.mouth_open_window:
                    self.mouth_open_count = 1
                    self.mouth_open_timer = current_time
                
                if self.mouth_open_count >= 3:
                    self.keyboard_active = not self.keyboard_active
                    self.mouth_open_count = 0
                    return False 
                
                return True
        return False
    
    def release(self):
        """Clean up resources"""
        self.face_mesh.close()