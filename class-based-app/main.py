import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import os 
import cv2
from dotenv import load_dotenv
import pyautogui
import time
from PIL import Image, ImageTk
import numpy as np
import threading


# Import your components
from core.facialtracker import FacialTracker
from UI.voice_ui import VoiceAssistantUI
from collections import deque

# Load environment variables
load_dotenv()

class FacialMouseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Facial Mouse Controller & Voice Assistant")
        self.geometry("1200x800")
        
        # Initialize components
        self.tracker = FacialTracker()
        
        # Track app state
        self.tracking_active = False
        self.calibrating = False
        self.cam_active = False
        
        # Setup UI
        self.setup_ui()
        self.setup_webcam()
        
    def setup_ui(self):
        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add tabs
        self.tab_home = self.tabview.add("Facial Control")
        self.tab_voice = self.tabview.add("Voice Assistant")
        self.tab_settings = self.tabview.add("Settings")
        
        # Setup each tab
        self.setup_home_tab()
        self.setup_voice_tab()
        self.setup_settings_tab()
        
        # Set default tab
        self.tabview.set("Facial Control")

    def setup_home_tab(self):
        """Setup facial mouse control tab"""
        # Main split frame for webcam and controls
        main_frame = ctk.CTkFrame(self.tab_home)
        main_frame.pack(fill="both", expand=True)
        
        # Webcam frame (left side)
        self.webcam_frame = ctk.CTkFrame(main_frame)
        self.webcam_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Webcam preview label
        self.cam_label = ctk.CTkLabel(self.webcam_frame, text="Camera Feed", height=480)
        self.cam_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Controls frame (right side)
        controls_frame = ctk.CTkFrame(main_frame)
        controls_frame.pack(side="right", fill="y", padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(
            controls_frame, 
            text="Facial Mouse Controls", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 30))
        
        # Start/Stop tracking button
        self.btn_tracking = ctk.CTkButton(
            controls_frame,
            text="Start Tracking",
            command=self.toggle_tracking,
            fg_color="#3B8ED0",
            hover_color="#1F6AA5",
            width=200,
            height=40
        )
        self.btn_tracking.pack(pady=10)
        
        # Calibration button
        self.btn_calibrate = ctk.CTkButton(
            controls_frame,
            text="Calibrate",
            command=self.start_calibration,
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            width=200,
            height=40
        )
        self.btn_calibrate.pack(pady=10)
        
        # Sensitivity control
        sens_frame = ctk.CTkFrame(controls_frame)
        sens_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            sens_frame, 
            text="Sensitivity", 
            font=ctk.CTkFont(size=14)
        ).pack(pady=5)
        
        self.sensitivity = ctk.CTkSlider(
            sens_frame,
            from_=1,
            to=10,
            number_of_steps=18,
            command=self.update_sensitivity
        )
        self.sensitivity.set(3.5)
        self.sensitivity.pack(pady=5, fill="x", padx=20)
        
        # Sensitivity value label
        self.sensitivity_label = ctk.CTkLabel(sens_frame, text="3.5")
        self.sensitivity_label.pack(pady=5)
        
        # Status frame
        status_frame = ctk.CTkFrame(controls_frame)
        status_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            status_frame, 
            text="Status", 
            font=ctk.CTkFont(size=14)
        ).pack(pady=5)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Ready to start tracking",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=5)
        
        # Debug info
        debug_frame = ctk.CTkFrame(controls_frame)
        debug_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            debug_frame, 
            text="Debug Info", 
            font=ctk.CTkFont(size=14)
        ).pack(pady=5)
        
        self.debug_label = ctk.CTkLabel(
            debug_frame,
            text="No data available",
            font=("Courier", 10),
            justify="left"
        )
        self.debug_label.pack(pady=5)
        
        # Instructions
        instr_frame = ctk.CTkFrame(controls_frame)
        instr_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(
            instr_frame, 
            text="Instructions", 
            font=ctk.CTkFont(size=14)
        ).pack(pady=5)
        
        instructions = (
            "• Open mouth once → Left click\n"
            "• Open mouth 3 times → Toggle keyboard\n"
            "• Move head to control cursor"
        )
        
        ctk.CTkLabel(
            instr_frame,
            text=instructions,
            font=ctk.CTkFont(size=12),
            justify="left"
        ).pack(pady=5)

    def setup_voice_tab(self):
        """Setup voice assistant tab"""
        voice_frame = ctk.CTkFrame(self.tab_voice)
        voice_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Initialize the voice assistant UI component
        try:
            self.voice_ui = VoiceAssistantUI(
                parent_frame=voice_frame,
                api_key=os.getenv("GEMINI_API_KEY")
            )
        except Exception as e:
            error_label = ctk.CTkLabel(
                voice_frame,
                text=f"Error initializing voice assistant: {str(e)}",
                text_color="red"
            )
            error_label.pack(pady=20)
            
            help_label = ctk.CTkLabel(
                voice_frame,
                text="Make sure you have set the GEMINI_API_KEY in your .env file",
                text_color="yellow"
            )
            help_label.pack(pady=10)

    def setup_settings_tab(self):
        """Setup settings tab"""
        settings_frame = ctk.CTkFrame(self.tab_settings)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create a scrollable frame for settings
        scrollable_frame = ctk.CTkScrollableFrame(settings_frame)
        scrollable_frame.pack(fill="both", expand=True)
        
        # Appearance settings
        appearance_section = self.create_settings_section(
            scrollable_frame, 
            "Appearance Settings"
        )
        
        # Appearance mode 
        appearance_frame = ctk.CTkFrame(appearance_section)
        appearance_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(appearance_frame, text="Appearance Mode:").pack(side="left", padx=10)
        self.appearance_mode = ctk.CTkOptionMenu(
            appearance_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode
        )
        self.appearance_mode.pack(side="left")
        self.appearance_mode.set("Dark")
        
        # Color theme
        theme_frame = ctk.CTkFrame(appearance_section)
        theme_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(theme_frame, text="Color Theme:").pack(side="left", padx=10)
        self.color_theme = ctk.CTkOptionMenu(
            theme_frame,
            values=["Blue", "Green", "Dark-Blue"],
            command=self.change_color_theme
        )
        self.color_theme.pack(side="left")
        self.color_theme.set("Blue")
        
        # Tracking settings
        tracking_section = self.create_settings_section(
            scrollable_frame, 
            "Tracking Settings"
        )
        
        # Click threshold
        click_frame = ctk.CTkFrame(tracking_section)
        click_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(click_frame, text="Click Threshold:").pack(anchor="w", padx=10, pady=5)
        self.click_threshold = ctk.CTkSlider(
            click_frame,
            from_=0.01,
            to=0.15,
            number_of_steps=14
        )
        self.click_threshold.set(0.05)
        self.click_threshold.pack(fill="x", padx=20, pady=5)
        
        self.click_threshold_label = ctk.CTkLabel(click_frame, text="0.05")
        self.click_threshold_label.pack(anchor="center", pady=5)
        
        # Click cooldown
        cooldown_frame = ctk.CTkFrame(tracking_section)
        cooldown_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(cooldown_frame, text="Click Cooldown (seconds):").pack(anchor="w", padx=10, pady=5)
        self.click_cooldown = ctk.CTkSlider(
            cooldown_frame,
            from_=0.1,
            to=2.0,
            number_of_steps=19
        )
        self.click_cooldown.set(0.5)
        self.click_cooldown.pack(fill="x", padx=20, pady=5)
        
        self.click_cooldown_label = ctk.CTkLabel(cooldown_frame, text="0.5")
        self.click_cooldown_label.pack(anchor="center", pady=5)
        
        # Smoothing factor
        smoothing_frame = ctk.CTkFrame(tracking_section)
        smoothing_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(smoothing_frame, text="Smoothing Factor:").pack(anchor="w", padx=10, pady=5)
        self.smoothing = ctk.CTkSlider(
            smoothing_frame,
            from_=1,
            to=20,
            number_of_steps=19
        )
        self.smoothing.set(10)
        self.smoothing.pack(fill="x", padx=20, pady=5)
        
        self.smoothing_label = ctk.CTkLabel(smoothing_frame, text="10")
        self.smoothing_label.pack(anchor="center", pady=5)
        
        # Connect sliders to update functions
        self.click_threshold.configure(command=self.update_click_threshold)
        self.click_cooldown.configure(command=self.update_click_cooldown)
        self.smoothing.configure(command=self.update_smoothing)
        
        # About section
        about_section = self.create_settings_section(
            scrollable_frame, 
            "About"
        )
        
        about_text = (
            "Facial Mouse Controller & Voice Assistant\n\n"
            "Version 1.0.0\n\n"
            "This application allows you to control your mouse cursor using facial movements\n"
            "and interact with a voice assistant.\n\n"
            "© 2023 - All rights reserved"
        )
        
        ctk.CTkLabel(
            about_section,
            text=about_text,
            justify="left",
            wraplength=400
        ).pack(pady=10, padx=10)

    def create_settings_section(self, parent, title):
        """Create a collapsible settings section"""
        section_frame = ctk.CTkFrame(parent)
        section_frame.pack(fill="x", pady=10, padx=5)
        
        # Header with title
        header = ctk.CTkFrame(section_frame, fg_color=("gray85", "gray25"))
        header.pack(fill="x")
        
        ctk.CTkLabel(
            header, 
            text=title, 
            font=ctk.CTkFont(weight="bold", size=14)
        ).pack(anchor="w", padx=10, pady=8)
        
        # Content frame
        content_frame = ctk.CTkFrame(section_frame)
        content_frame.pack(fill="x", pady=5, padx=5)
        
        return content_frame

    def setup_webcam(self):
        """Initialize webcam capture"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Could not open webcam")
                
            self.cam_active = True
            self.update_camera_preview()
        except Exception as e:
            self.show_error(f"Error initializing webcam: {str(e)}")
    
    def update_camera_preview(self):
        """Update the camera preview in the UI"""
        if self.cam_active and hasattr(self, 'cap'):
            ret, frame = self.cap.read()
            
            if ret:
                # Flip the frame horizontally for a mirror effect
                # This is how the cusor moves in the same direction as you in real life 
                frame = cv2.flip(frame, 1)
                
                # Process the frame if tracking is active
                if self.tracking_active:
                    if self.calibrating:
                        # Handle calibration
                        if self.tracker.calibrate(frame):
                            self.calibrating = False
                            self.status_label.configure(text="Calibration complete!")
                    else:
                        cursor_pos = self.tracker.track_face(frame)
                        
                        if cursor_pos:
                            screen_width, screen_height = pyautogui.size()
                            
                            # Add safety margins to avoid triggering PyAutoGUI's fail-safe
                            safe_margin = 15
                            safe_x = max(safe_margin, min(cursor_pos[0], screen_width - safe_margin))
                            safe_y = max(safe_margin, min(cursor_pos[1], screen_height - safe_margin))
                            
                            # Move the cursor to the safe position
                            pyautogui.moveTo(safe_x, safe_y)
                            
                            # Check for click events
                            if self.tracker.check_mouth_open(frame):
                                pyautogui.click()
                                self.status_label.configure(text="Click detected!")
                            
                            # Update debug info
                            if hasattr(self.tracker, 'debug_info'):
                                debug_text = "\n".join([
                                    f"{k}: {v}" for k, v in self.tracker.debug_info.items()
                                ])
                                self.debug_label.configure(text=debug_text)
                
                # Convert the frame to a format suitable for CTk
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                photo = ImageTk.PhotoImage(image=img)
                
                # Update the camera label
                self.cam_label.configure(image=photo)
                self.cam_label.image = photo
        
        # Schedule next update
        self.after(10, self.update_camera_preview)
    
    def toggle_tracking(self):
        if self.tracking_active:
            self.tracking_active = False
            self.btn_tracking.configure(text="Start Tracking")
            self.status_label.configure(text="Tracking stopped")
        else:
            if not self.tracker.calibrated:
                # Will automatically calibrate if not calibrated 
                self.start_calibration()
            
            self.tracking_active = True
            self.btn_tracking.configure(text="Stop Tracking")
            self.status_label.configure(text="Tracking active")
    
    def start_calibration(self):
        self.calibrating = True
        self.tracker.calibrated = False
        self.tracker.calibration_count = 0
        self.tracking_active = True
        self.btn_tracking.configure(text="Stop Tracking")
        self.status_label.configure(text="Calibrating... Look straight at the camera")
    
    def update_sensitivity(self, value):
        self.tracker.sensitivity = float(value)
        self.sensitivity_label.configure(text=f"{value:.1f}")
    
    def update_click_threshold(self, value):
        self.tracker.click_threshold = float(value)
        self.click_threshold_label.configure(text=f"{value:.2f}")
    
    def update_click_cooldown(self, value):
        self.tracker.click_cooldown = float(value)
        self.click_cooldown_label.configure(text=f"{value:.1f}")
    
    def update_smoothing(self, value):
        value = int(value)
        self.tracker.smoothing_factor = value
        self.tracker.x_points = deque(self.tracker.x_points, maxlen=value)
        self.tracker.y_points = deque(self.tracker.y_points, maxlen=value)
        self.smoothing_label.configure(text=str(value))
    
    def change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode.lower())
    
    def change_color_theme(self, new_theme):
        ctk.set_default_color_theme(new_theme.lower())
    
    def show_error(self, message):
        self.status_label.configure(text=message, text_color="red")
        print(f"ERROR: {message}")
    
    def on_closing(self):
        # Clean up resources before closing the app to reduce lag 
        self.cam_active = False
        if hasattr(self, 'cap'):
            self.cap.release()
        
        if hasattr(self, 'tracker'):
            self.tracker.release()
            
        if hasattr(self, 'voice_ui'):
            self.voice_ui.cleanup()
            
        self.destroy()


if __name__ == "__main__":
    # Configure appearance
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Create and run app
    app = FacialMouseApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()