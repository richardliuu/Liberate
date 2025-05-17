import cv2
import numpy as np
import pyautogui
import mediapipe as mp
import time
import tkinter as tk
# Might use CustomTkinter to style better
from collections import deque
import sys
import win32gui
import win32con
import win32process
import threading

# Just need to implement app functions right now 

def get_active_window_handle():
    """Get the currently active window handle for Windows"""
    try:
        return win32gui.GetForegroundWindow()
    except Exception as e:
        print(f"Error getting window handle: {e}")
        return None

def focus_window(handle):
    """Focus a specific window based on its handle on Windows"""
    try:
        if handle and win32gui.IsWindow(handle):
            if win32gui.IsIconic(handle):  # If minimized
                win32gui.ShowWindow(handle, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(handle)
            return True
    except Exception as e:
        print(f"Error focusing window: {e}")
        # Fallback to alt+tab if direct focus fails
        try:
            pyautogui.keyDown('alt')
            pyautogui.press('tab')
            pyautogui.keyUp('alt')
            return True
        except:
            pass
    return False


"""
The virtual keyboard will appear as a keyboard infront of a screen
Requires clicks to be used 
"""
class VirtualKeyboard:
    def __init__(self, parent=None):
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("Virtual Keyboard")
        self.window.attributes('-topmost', True)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)  
        
        # Making the keyboatd transparent so that users can see what is under it
        # The value can be adjusted (making could be a slider inside the settings of the app 
        # for more customizing 

        self.window.attributes('-alpha', 0.9)  
        
       
        screen_width, screen_height = pyautogui.size()

        # Keyboard sizes can be changed later to fit needs 
        keyboard_width = 800
        keyboard_height = 300

        # Positioning the keyboard a tad bit higher than the taskbar so it is still accessible
        self.window.geometry(f"{keyboard_width}x{keyboard_height}+{(screen_width-keyboard_width)//2}+{screen_height-keyboard_height-100}")
        
        self.create_keyboard_layout()
        self.window.withdraw()  
        self.visible = False
        
        # Store the active window when keyboard is shown
        self.active_window_before = None
    
    """
    Keyboard should be styled later (CustomTkinter)
    """
    def create_keyboard_layout(self):
        
        self.keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Backspace'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'Enter'],
            ['Shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'Shift'],
            ['Ctrl', 'Alt', 'Space', 'Tab', '←', '→', '↑', '↓']  # Added arrow keys and modifiers
        ]
        
        # Create frames for each row
        self.frames = []
        for i in range(len(self.keys)):
            frame = tk.Frame(self.window)
            frame.pack(expand=True, fill='both')
            self.frames.append(frame)
        
        # Create buttons for each key
        self.buttons = {}
        for row_idx, row in enumerate(self.keys):
            for key in row:
                if key == 'Space':
                    # Space bar is wider
                    button = tk.Button(self.frames[row_idx], text=key, 
                                     width=20, height=2, bg="#dddddd",
                                     command=lambda k=key: self.press_key(k))
                    button.pack(side='left', expand=True, fill='both', padx=2, pady=2)
                elif key in ['Backspace', 'Enter', 'Shift', 'Ctrl', 'Alt', 'Tab', '←', '→', '↑', '↓']:
                    # Special keys are wider and different color
                    button = tk.Button(self.frames[row_idx], text=key, 
                                     width=6, height=2, bg="#cccccc",
                                     command=lambda k=key: self.press_key(k))
                    button.pack(side='left', padx=2, pady=2)
                else:
                    # Regular keys
                    button = tk.Button(self.frames[row_idx], text=key, 
                                     width=4, height=2, bg="#ffffff",
                                     command=lambda k=key: self.press_key(k))
                    button.pack(side='left', padx=2, pady=2)
                
                self.buttons[key] = button
                
        # Add control buttons at the bottom
        control_frame = tk.Frame(self.window)
        control_frame.pack(fill='x', pady=5)
        
        # Add a close button
        close_button = tk.Button(control_frame, text="Close Keyboard", 
                               bg="#ff9999", command=self.hide)
        close_button.pack(side='right', padx=10)
        
        # Add sensitivity control
        sensitivity_frame = tk.Frame(control_frame)
        sensitivity_frame.pack(side='left', padx=10)
        tk.Label(sensitivity_frame, text="Sensitivity:").pack(side='left')

        # part of the tkinter setup, may be turned into a part of the app later 
        self.sensitivity_var = tk.DoubleVar(value=3.5)
        sensitivity_scale = tk.Scale(sensitivity_frame, from_=1.0, to=6.0, 
                                   orient='horizontal', resolution=0.5,
                                   variable=self.sensitivity_var)
        sensitivity_scale.pack(side='left')
    
    def press_key(self, key):
        """Handle key press events"""
        # Visual feedback by changing button appearance
        self.buttons[key].config(relief="sunken", bg="#aaddff")
        
        # Remember the keyboard window handle
        keyboard_handle = None
        try:
            keyboard_handle = win32gui.GetForegroundWindow()
        except:
            # Pass for now, might turn into error handling 
            pass
        
        # Use a separate thread to restore focus and send keystroke
        # This helps prevent UI blocking
        threading.Thread(target=self._execute_keystroke, args=(key, keyboard_handle)).start()
        
        # Reset button appearance after a delay
        self.window.after(100, lambda k=key: self.buttons[k].config(relief="raised", 
                                                                 bg="#ffffff" if k not in ['Backspace', 'Enter', 'Shift', 'Space', 
                                                                                          'Ctrl', 'Alt', 'Tab', '←', '→', '↑', '↓'] 
                                                                 else ("#cccccc" if k != 'Space' else "#dddddd")))
        
        # Keeping the window at the front of the screen
        self.window.after(150, lambda: self.window.attributes('-topmost', True))
    
    def _execute_keystroke(self, key, keyboard_handle):
        """Execute the actual keystroke in a separate thread"""
        try:
            # Try to restore focus to the application that was active before keyboard appeared
            if self.active_window_before:
                focus_window(self.active_window_before)
                time.sleep(0.05)  # Short delay to allow focus to change
            else:
                # If we don't have a stored handle, try alternative methods
                self.window.lower()
                time.sleep(0.05)
            
            # Send the keystroke
            if key == 'Backspace':
                pyautogui.press('backspace')
            elif key == 'Enter':
                pyautogui.press('enter')
            elif key == 'Shift':
                # Just press shift once (not hold)
                pyautogui.press('shift')
            elif key == 'Space':
                pyautogui.press('space')
            elif key == 'Ctrl':
                pyautogui.press('ctrl')
            elif key == 'Alt':
                pyautogui.press('alt')
            elif key == 'Tab':
                pyautogui.press('tab')
            elif key == '←':
                pyautogui.press('left')
            elif key == '→':
                pyautogui.press('right')
            elif key == '↑':
                pyautogui.press('up')
            elif key == '↓':
                pyautogui.press('down')
            else:
                pyautogui.press(key)
                
        except Exception as e:
            print(f"Error sending keystroke: {e}")
    
    def show(self):
        """Display the keyboard"""
        if not self.visible:
            # Store the currently active window before showing keyboard
            self.active_window_before = get_active_window_handle()
            
            # Make keyboard visible
            self.window.deiconify()
            self.visible = True
            
            # Make sure it's on top
            self.window.attributes('-topmost', True)
            self.window.update()
    
    def hide(self):
        """Hide the keyboard"""
        if self.visible:
            # Try to restore focus to the window that was active before
            if self.active_window_before:
                focus_window(self.active_window_before)
            
            self.window.withdraw()
            self.visible = False
    
    def toggle(self):
        """Toggle keyboard visibility"""
        if self.visible:
            self.hide()
        else:
            self.show()
            
# Update Window 
    def update(self):
        if self.window:
            self.window.update()
    
# Return sensitivity setting 
    def get_sensitivity(self):
        return self.sensitivity_var.get()
    
"""
The above features may be moved to a configuration section
"""

class FacialMouseController:
    def __init__(self):
        # Screen dimensions
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Smoothing Points
        # ====== These features could be included to a settings configuration ========
        # All adjustable 
        self.smoothing_factor = 10  
        self.x_points = deque(maxlen=self.smoothing_factor)
        self.y_points = deque(maxlen=self.smoothing_factor)
        self.base_sensitivity = 3.5
        self.sensitivity = self.base_sensitivity
        
        
        self.click_threshold = 0.05  
        self.last_click_time = 0
        self.click_cooldown = 0.5  # Minimum time between clicks (seconds)

                # This may need to be changed as I introduce more commands (mouth opens)
        # Might interfere

        
        # Might want to hide the OpenCV live camera to improve performance 
        self.paused = False
        cv2.namedWindow("Facial Mouse Control", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Facial Mouse Control", 640, 480)
        
        """
        Landmark features may be removed to improve performance
        They are here for now to indicate the functionality of the software 
        """
        self.show_nose_position = True
        self.show_mouth_status = True
        self.show_debug_info = True

        # Calibration - setting where the center point for the mouse is relative to the face (webcam)
        
        self.calibrated = False
        self.neutral_x = 0.5
        self.neutral_y = 0.5
        self.calibration_frames = 30
        self.calibration_count = 0
        self.calibration_data_x = []
        self.calibration_data_y = []
        
        # Virtual keyboard - root window invisible but needed for tk operations
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window
        self.root.attributes('-alpha', 0.0)  # Make fully transparent
        self.root.title("Facial Mouse Controller Base")
        self.keyboard = VirtualKeyboard(self.root)
        
        # Open mouth 3 times to toggle the keyboard 
        """
        Command Toggle 1 
        """
        self.mouth_open_count = 0
        self.mouth_open_sequence = []
        self.mouth_open_time_window = 2.0  # Time window for consecutive mouth opens (seconds)
        self.last_mouth_open_time = 0
        self.last_keyboard_toggle_time = 0
        self.keyboard_toggle_cooldown = 5  
        # Seconds between keyboard toggles
        
        # Showing that the keystroke has been clicked 
        self.showing_click_feedback = False
        self.click_feedback_start = 0
        self.click_feedback_duration = 0.3 
        
        """
        ====== IMPORTANT ====== 

        Frame/Performance Optimization 
        """
        self.frame_skip = 0 
        self.frame_counter = 0
        
        # Trackbars for these features
        # Might be put into the settings as well
        cv2.createTrackbar('Sensitivity', 'Facial Mouse Control', 35, 80, self.update_sensitivity)
        cv2.createTrackbar('Click Threshold', 'Facial Mouse Control', 5, 15, self.update_threshold)
        
    def update_sensitivity(self, value):
        """Callback for sensitivity trackbar"""
        self.sensitivity = value / 10.0
        
    def update_threshold(self, value):
        """Callback for threshold trackbar"""
        self.click_threshold = value / 100.0
        
    def start(self):
        # Opening the program to allow webcam features 
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: Could not open webcam.")
            return
            
        print("Facial Mouse Controller started!")
        print("Look straight at the camera for initial calibration")
        print("Controls:")
        print("- 'p' to pause/resume")
        print("- 'c' to recalibrate")
        print("- 'd' to toggle debug info")
        print("- 'k' to toggle keyboard")
        print("- 'q' to quit")
        print("\nFacial commands:")
        print("- Open mouth for click")
        print("- Open mouth 3 times in quick succession to toggle virtual keyboard")

        """
        Controls don't seem to work for now
        Manually close the app 
        """
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1)
            
             # ======= PERFORMANCE OPTIMIZATION =======
            # Skipping frames if needed 

            """
            Works by not processing the frames, reducing the amount of resources needed 
            """

            self.frame_counter += 1
            if self.frame_counter % (self.frame_skip + 1) != 0:
                # Still show the frame but don't process it
                self.display_status_on_frame(frame)
                cv2.imshow("Facial Mouse Control", frame)
                
                # Check for key presses
                key = cv2.waitKey(1) & 0xFF
                self.handle_key_press(key)
                
                # Update the Tkinter UI
                try:
                    self.root.update_idletasks()
                    self.root.update()
                except:
                    pass
                
                continue
            
            # Process frame for calibration or normal operation
            if not self.calibrated:
                self.calibrate_frame(frame)
            elif not self.paused:
                self.process_frame(frame)
        
            key = cv2.waitKey(1) & 0xFF
            self.handle_key_press(key)
            
            self.display_status_on_frame(frame)
            
            cv2.imshow("Facial Mouse Control", frame)
            
            # Update the Tkinter UI
            try:
                self.root.update_idletasks()
                self.root.update()
            except:
                pass
        
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        self.root.destroy()
    
    # Error handling for the keyboard commands like p for pause and such 
    def handle_key_press(self, key):
        """Handle keyboard input"""
        if key == ord('q'):
            cv2.destroyAllWindows()
            self.root.quit()
            sys.exit(0)
        elif key == ord('p'):
            self.paused = not self.paused
            status = "Paused" if self.paused else "Running"
            print(f"Application {status}")
        elif key == ord('c'):
            self.reset_calibration()
            print("Recalibrating: Look straight at the camera")
        elif key == ord('k'):
            # Manual keyboard toggle
            self.keyboard.toggle()
        elif key == ord('d'):
            # Toggle debug info
            self.show_debug_info = not self.show_debug_info
            print(f"Debug info {'shown' if self.show_debug_info else 'hidden'}")
    
    def display_status_on_frame(self, frame):
        """Display status information on the frame"""
        # Get frame dimensions
        frame_height, frame_width = frame.shape[:2]
        
        # Show calibration or running status
        if not self.calibrated:
            cv2.putText(frame, f"CALIBRATING... {self.calibration_count}/{self.calibration_frames}", 
                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            status_text = "PAUSED" if self.paused else "RUNNING"
            cv2.putText(frame, status_text, (10, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if self.paused else (0, 255, 0), 2)
        
        # Show keyboard status
        keyboard_status = "KEYBOARD: " + ("ON" if self.keyboard.visible else "OFF")
        cv2.putText(frame, keyboard_status, (frame_width - 200, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if self.keyboard.visible else (200, 100, 0), 2)
        
        # Show settings if debug info is enabled
        if self.show_debug_info:
            cv2.putText(frame, f"Sensitivity: {self.sensitivity:.1f}", (10, frame_height - 70), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
            cv2.putText(frame, f"Click threshold: {self.click_threshold:.2f}", (10, frame_height - 40), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
            cv2.putText(frame, "Controls: P=Pause C=Calibrate K=Keyboard D=Debug Q=Quit", 
                      (10, frame_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    def reset_calibration(self):
        """Reset calibration data to start fresh"""
        self.calibrated = False
        self.calibration_count = 0
        self.calibration_data_x = []
        self.calibration_data_y = []
        
    def calibrate_frame(self, frame):
        """Process a frame during calibration phase"""
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame with MediaPipe Face Mesh
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            
            # Get nose tip for calibration
            nose_x = landmarks[1].x
            nose_y = landmarks[1].y
            
            # Store calibration data
            self.calibration_data_x.append(nose_x)
            self.calibration_data_y.append(nose_y)
            self.calibration_count += 1
            
            # Mark nose position on frame
            frame_height, frame_width = frame.shape[:2]
            nose_screen_x = int(nose_x * frame_width)
            nose_screen_y = int(nose_y * frame_height)
            cv2.circle(frame, (nose_screen_x, nose_screen_y), 5, (0, 255, 255), -1)
            
            # Mark center target
            center_x = frame_width // 2
            center_y = frame_height // 2
            cv2.drawMarker(frame, (center_x, center_y), (0, 255, 255), 
                         markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)
            
            # Draw guidance rectangle for calibration
            rect_size = min(frame_width, frame_height) // 4
            cv2.rectangle(frame, 
                        (center_x - rect_size, center_y - rect_size),
                        (center_x + rect_size, center_y + rect_size),
                        (0, 255, 255), 1)
            
            # Once we have enough frames, complete calibration
            if self.calibration_count >= self.calibration_frames:
                # Calculate average neutral position (removing outliers)
                sorted_x = sorted(self.calibration_data_x)
                sorted_y = sorted(self.calibration_data_y)
                
                # Remove potential outliers (20% from each end)
                trim_size = int(self.calibration_frames * 0.2)
                trimmed_x = sorted_x[trim_size:-trim_size]
                trimmed_y = sorted_y[trim_size:-trim_size]
                
                self.neutral_x = sum(trimmed_x) / len(trimmed_x)
                self.neutral_y = sum(trimmed_y) / len(trimmed_y)
                
                self.calibrated = True
                print(f"Calibration complete! Neutral position set at ({self.neutral_x:.3f}, {self.neutral_y:.3f})")
                
                # Clear any queued positions
                self.x_points.clear()
                self.y_points.clear()
        
    def process_frame(self, frame):
        """Process a frame during normal operation"""
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_height, frame_width = frame.shape[:2]
        
        # Process the frame with MediaPipe Face Mesh
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            # No face detected
            if self.show_debug_info:
                cv2.putText(frame, "No face detected", (frame_width // 2 - 100, frame_height // 2), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            return
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        # Get nose tip (landmark 1)
        nose_x = landmarks[1].x
        nose_y = landmarks[1].y
        
        # Display nose position
        if self.show_nose_position:
            nose_screen_x = int(nose_x * frame_width)
            nose_screen_y = int(nose_y * frame_height)
            cv2.circle(frame, (nose_screen_x, nose_screen_y), 5, (0, 255, 0), -1)
        
        # Use keyboard sensitivity if available
        if self.keyboard.visible:
            try:
                self.sensitivity = self.keyboard.get_sensitivity()
            except:
                # Fallback if getting sensitivity fails
                pass
        
        # Map to screen coordinates with enhanced sensitivity
        # Center point calibration (use calibrated neutral position)
        offset_x = (nose_x - self.neutral_x) * self.sensitivity
        offset_y = (nose_y - self.neutral_y) * self.sensitivity
        
        # Calculate target position with exponential mapping for finer control
        target_x = self.screen_width * (0.5 + offset_x)
        target_y = self.screen_height * (0.5 + offset_y)
        
        # Add to smoothing queue
        self.x_points.append(target_x)
        self.y_points.append(target_y)
        
        # Enhanced smoothing with weighted average (recent positions have more influence)
        if len(self.x_points) > 3:  
            weights = np.linspace(0.5, 1.0, len(self.x_points))
            weights = weights / weights.sum()  
            
            smoothed_x = sum(x * w for x, w in zip(self.x_points, weights))
            smoothed_y = sum(y * w for y, w in zip(self.y_points, weights))
        else:
            # Simple average for the first few frames
            smoothed_x = sum(self.x_points) / len(self.x_points)
            smoothed_y = sum(self.y_points) / len(self.y_points)
        
        # Ensure coordinates are within screen bounds
        smoothed_x = max(0, min(smoothed_x, self.screen_width))
        smoothed_y = max(0, min(smoothed_y, self.screen_height))
        
        # Move cursor
        try:
            pyautogui.moveTo(int(smoothed_x), int(smoothed_y))
        except Exception as e:
            if self.show_debug_info:
                cv2.putText(frame, f"Mouse error: {str(e)}", (10, frame_height - 100), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        
        # Detect mouth open for click and keyboard toggle
        upper_lip = landmarks[13]
        lower_lip = landmarks[14]
        mouth_distance = abs(upper_lip.y - lower_lip.y)
        
        # Face height for relative measurement
        face_height = abs(landmarks[10].y - landmarks[152].y)
        relative_mouth_distance = mouth_distance / face_height
        
        # Current time for timing operations
        current_time = time.time()
        
        # Display mouth status
        mouth_open = relative_mouth_distance > self.click_threshold
        if self.show_mouth_status:
            mouth_status = "MOUTH: OPEN" if mouth_open else "MOUTH: CLOSED"
            cv2.putText(frame, mouth_status, (10, 60), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                      (0, 0, 255) if mouth_open else (255, 0, 0), 2)
            
            # Show mouth distance indicator
            indicator_x = 120
            indicator_y = 90
            indicator_width = 100
            indicator_height = 15
            """
            These landmarks, shapes may not be needed, are just indicators that the application is functioning as is 
            """
            # Background bar
            cv2.rectangle(frame, 
                        (indicator_x, indicator_y), 
                        (indicator_x + indicator_width, indicator_y + indicator_height),
                        (50, 50, 50), -1)
            
            # Fill bar based on mouth distance
            fill_width = int(min(1.0, relative_mouth_distance / (self.click_threshold * 1.5)) * indicator_width)
            cv2.rectangle(frame, 
                        (indicator_x, indicator_y),
                        (indicator_x + fill_width, indicator_y + indicator_height),
                        (0, 255, 0) if mouth_open else (0, 170, 255), -1)
            
            # Threshold line
            threshold_x = indicator_x + int(self.click_threshold / (self.click_threshold * 1.5) * indicator_width)
            cv2.line(frame, 
                   (threshold_x, indicator_y - 2), 
                   (threshold_x, indicator_y + indicator_height + 2),
                   (255, 255, 255), 1)
        
        # Mouth open detection and tracking
        if mouth_open:
            # If this is a new mouth opening (not continuous from previous frame)
            if (len(self.mouth_open_sequence) == 0 or 
                current_time - self.last_mouth_open_time > 0.5): 
                
                self.mouth_open_sequence.append(current_time)
                self.last_mouth_open_time = current_time
                
                # Remove any opens that are too old (outside the time window)
                while (len(self.mouth_open_sequence) > 0 and 
                       current_time - self.mouth_open_sequence[0] > self.mouth_open_time_window):
                    self.mouth_open_sequence.pop(0)
                
                # Display count of recent mouth opens
                cv2.putText(frame, f"MOUTH OPENS: {len(self.mouth_open_sequence)}/3", 
                          (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Check for 3 consecutive mouth opens in the time window
                if (len(self.mouth_open_sequence) >= 3 and 
                    current_time - self.last_keyboard_toggle_time > self.keyboard_toggle_cooldown):
                    self.keyboard.toggle()
                    self.last_keyboard_toggle_time = current_time
                    # Reset sequence after toggling
                    self.mouth_open_sequence = []
                    
                    # Visual feedback for keyboard toggle
                    keyboard_status = "KEYBOARD: " + ("HIDDEN" if not self.keyboard.visible else "VISIBLE")
                    cv2.putText(frame, keyboard_status, (frame_width - 300, 90), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Check for click (regular single mouth open)
            if (len(self.mouth_open_sequence) == 1 and 
                current_time - self.last_click_time > self.click_cooldown):
                try:
                    pyautogui.click()
                    self.last_click_time = current_time
                    self.showing_click_feedback = True
                    self.click_feedback_start = current_time
                    
                    cv2.putText(frame, "CLICK!", 
                              (nose_screen_x - 30, nose_screen_y - 20), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                except Exception as e:
                    if self.show_debug_info:
                        cv2.putText(frame, f"Click error: {str(e)}", (10, frame_height - 130), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
        
        # Show click feedback if active
        if self.showing_click_feedback:
            if current_time - self.click_feedback_start < self.click_feedback_duration:
                cv2.circle(frame, (int(nose_x * frame_width), int(nose_y * frame_height)), 
                         20, (0, 255, 255), 2)
            else:
                self.showing_click_feedback = False

if __name__ == "__main__":
    controller = FacialMouseController()
    controller.start()  