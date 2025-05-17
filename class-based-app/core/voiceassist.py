# Splitting everything into class-based files
# Reducing clutter 
import customtkinter as ctk
import threading
import time
import speech_recognition as sr
import google.generativeai as genai
from typing import Callable

class VoiceAssistantCore:
    def __init__(self, api_key: str):
        self.recognizer = sr.Recognizer()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("models/gemini-1.5-flash")
        self.is_recording = False
        self.callbacks = {
            'on_status_change': None,
            'on_user_input': None,
            'on_ai_response': None,
            'on_error': None
        }

    def register_callback(self, event: str, callback: Callable):
        self.callbacks[event] = callback

    def start_recording(self):
        if not self._check_microphone():
            return False
        
        self.is_recording = True
        self._trigger_callback('on_status_change', "Listening...")
        threading.Thread(target=self._recording_loop, daemon=True).start()
        return True

    def stop_recording(self):
        self.is_recording = False
        self._trigger_callback('on_status_change', "Ready")

    def _recording_loop(self):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
                while self.is_recording:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    if self.is_recording:  # Check again in case stopped during listen
                        self._process_audio(audio)
        except Exception as e:
            self._trigger_callback('on_error', f"Recording error: {str(e)}")

    def _process_audio(self, audio):
        try:
            text = self.recognizer.recognize_google(audio)
            self._trigger_callback('on_user_input', text)
            self._get_ai_response(text)
        except Exception as e:
            self._trigger_callback('on_error', f"Processing error: {str(e)}")

    def _get_ai_response(self, text):
        try:
            response = self.model.generate_content(text)
            self._trigger_callback('on_ai_response', response.text)
        except Exception as e:
            self._trigger_callback('on_error', f"AI error: {str(e)}")

    def _check_microphone(self):
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                return True
        except Exception as e:
            self._trigger_callback('on_error', f"Microphone error: {str(e)}")
            return False

    def _trigger_callback(self, event: str, *args):
        if self.callbacks[event]:
            self.callbacks[event](*args)


# ========== TEXT-TO-SPEECH ============

class VoiceTypingAssistant:
    def __init__(self, parent_frame, api_key, keyboard_ref):
        self.parent = parent_frame
        self.keyboard = keyboard_ref  # Reference to your VirtualKeyboard
        self.api_key = api_key
        self.is_listening = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        self.frame = ctk.CTkFrame(self.parent)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        ctk.CTkLabel(
            self.frame, 
            text="Voice Typing Assistant", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 20))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.frame, 
            text="Ready", 
            text_color="gray"
        )
        self.status_label.pack(pady=5)
        
        # Toggle button
        self.toggle_btn = ctk.CTkButton(
            self.frame,
            text="Start Listening",
            command=self.toggle_listening,
            fg_color="#3B8ED0",
            hover_color="#1F6AA5"
        )
        self.toggle_btn.pack(pady=10)
        
        # Text display
        self.text_display = ctk.CTkTextbox(
            self.frame,
            height=150,
            wrap="word"
        )
        self.text_display.pack(fill="x", pady=10, padx=10)
        
        # Action buttons
        btn_frame = ctk.CTkFrame(self.frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.send_btn = ctk.CTkButton(
            btn_frame,
            text="Send to Keyboard",
            command=self.send_to_keyboard,
            state="disabled"
        )
        self.send_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="Clear",
            command=self.clear_text,
            fg_color="gray"
        )
        self.clear_btn.pack(side="right", padx=5)
        
    def toggle_listening(self):
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()
    
    def start_listening(self):
        self.is_listening = True
        self.toggle_btn.configure(text="Stop Listening", fg_color="#D0353B")
        self.status_label.configure(text="Listening...", text_color="#3B8ED0")
        self.text_display.delete("1.0", "end")
        
        # Start listening in a separate thread
        threading.Thread(target=self.listen_loop, daemon=True).start()
    
    def stop_listening(self):
        self.is_listening = False
        self.toggle_btn.configure(text="Start Listening", fg_color="#3B8ED0")
        self.status_label.configure(text="Ready", text_color="gray")
        
    def listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            
            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                    text = self.recognizer.recognize_google(audio)
                    
                    # Update UI with recognized text
                    self.text_display.insert("end", text + " ")
                    self.send_btn.configure(state="normal")
                    
                    # Optional: Process with Gemini for refinement
                    # self.process_with_gemini(text)
                    
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self.status_label.configure(text="Could not understand audio", text_color="orange")
                except Exception as e:
                    self.status_label.configure(text=f"Error: {str(e)}", text_color="red")
                    self.stop_listening()
    
    def process_with_gemini(self, text):
        """Optional: Use Gemini to refine or process the text"""
        try:
            prompt = f"Please correct any errors in this transcribed speech and format it properly:\n{text}"
            response = self.model.generate_content(prompt)
            
            # Update the text display with the refined text
            self.text_display.delete("1.0", "end")
            self.text_display.insert("end", response.text)
            
        except Exception as e:
            self.status_label.configure(text=f"Gemini error: {str(e)}", text_color="red")
    
    def send_to_keyboard(self):
        """Send the transcribed text to the virtual keyboard"""
        text = self.text_display.get("1.0", "end-1c")
        if text.strip():
            # Type the text using the virtual keyboard
            self.keyboard.type_text(text)
            self.status_label.configure(text="Text sent to keyboard!", text_color="green")
    
    def clear_text(self):
        self.text_display.delete("1.0", "end")
        self.send_btn.configure(state="disabled")