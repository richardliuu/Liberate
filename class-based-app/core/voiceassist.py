# Splitting everything into class-based files
# Reducing clutter 
import customtkinter as ctk
import threading
import time
import speech_recognition as sr
import google.generativeai as genai
from typing import Callable
from queue import Queue
import pyautogui
import os 
import webbrowser
import logging 

logger = logging.getLogger(__name__)

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
    def __init__(self, parent_frame, api_key, keyboard_ref=None):
        self.parent = parent_frame
        self.keyboard = keyboard_ref
        self.api_key = api_key
        self.mode = "docs"  # Default mode ("docs" or "python")
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        # Audio and text queues
        self.audio_queue = Queue()
        self.text_queue = Queue()
        self.is_listening = False
        
        # UI Setup
        self.setup_ui()
        
        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self.process_audio_queue,
            daemon=True
        )
        self.processing_thread.start()
        
        logger.info("Voice typing assistant initialized")

    def setup_ui(self):
        """Create the voice typing interface with mode switching"""
        self.frame = ctk.CTkFrame(self.parent)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title that updates with mode
        self.title_label = ctk.CTkLabel(
            self.frame,
            text="Voice to Google Docs",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.pack(pady=(5, 15))
        
        # Mode switch button
        self.mode_btn = ctk.CTkButton(
            self.frame,
            text="Switch to Python Mode",
            command=self.toggle_mode,
            fg_color="#4CAF50",  # Green for Python mode
            hover_color="#2E7D32",
            width=200
        )
        self.mode_btn.pack(pady=(0, 10))
        
        # Status frame
        status_frame = ctk.CTkFrame(self.frame)
        status_frame.pack(fill="x", pady=5)
        
        self.status_light = ctk.CTkLabel(
            status_frame,
            text="●",
            text_color="red",
            font=ctk.CTkFont(size=24)
        )
        self.status_light.pack(side="left", padx=10)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Ready",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(side="left")
        
        # Button frame
        btn_frame = ctk.CTkFrame(self.frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="Start Listening",
            command=self.start_listening,
            fg_color="#3B8ED0"
        )
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="Stop & Send to Docs",
            command=self.stop_and_process,
            fg_color="#D0353B",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="Clear",
            command=self.clear_text,
            fg_color="gray"
        )
        self.clear_btn.pack(side="right", padx=5)
        
        # Text display
        self.text_display = ctk.CTkTextbox(
            self.frame,
            height=200,
            wrap="word",
            font=ctk.CTkFont(size=14)
        )
        self.text_display.pack(fill="both", expand=True, pady=10)
        
        # Debug console
        self.debug_console = ctk.CTkTextbox(
            self.frame,
            height=100,
            wrap="word",
            font=ctk.CTkFont(size=10)
        )
        self.debug_console.pack(fill="x", pady=(0, 10))
        self.debug_console.insert("end", "Console output...\n")
        
        # Update UI based on initial mode
        self.update_mode_ui()

    def toggle_mode(self):
        """Switch between docs and python modes"""
        self.mode = "python" if self.mode == "docs" else "docs"
        self.update_mode_ui()
        self.log_to_ui(f"Switched to {self.mode} mode")

    def update_mode_ui(self):
        """Update UI elements based on current mode"""
        if self.mode == "docs":
            self.title_label.configure(text="Voice to Google Docs")
            self.mode_btn.configure(
                text="Switch to Python Mode",
                fg_color="#4CAF50",  # Green
                hover_color="#2E7D32"
            )
            self.stop_btn.configure(text="Stop & Send to Docs")
        else:
            self.title_label.configure(text="Voice to Python Code")
            self.mode_btn.configure(
                text="Switch to Docs Mode",
                fg_color="#2196F3",  # Blue
                hover_color="#1565C0"
            )
            self.stop_btn.configure(text="Stop & Generate Code")

    def log_to_ui(self, message):
        """Helper to log messages to both console and UI"""
        logger.info(message)
        self.debug_console.insert("end", f"{message}\n")
        self.debug_console.see("end")

    def start_listening(self):
        """Start recording speech"""
        try:
            if not self.is_listening:
                self.is_listening = True
                self.start_btn.configure(state="disabled")
                self.stop_btn.configure(state="normal")
                self.status_light.configure(text_color="green")
                self.status_label.configure(text="Listening...")
                self.text_display.delete("1.0", "end")
                self.log_to_ui("Listening started...")

                # Start listening in background
                threading.Thread(
                    target=self.capture_audio,
                    daemon=True
                ).start()
        except Exception as e:
            self.log_to_ui(f"Start listening error: {str(e)}")

    def stop_and_process(self):
        """Stop recording and process based on current mode"""
        try:
            self.is_listening = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_light.configure(text_color="red")
            self.status_label.configure(text="Processing...")
            
            raw_text = self.text_display.get("1.0", "end-1c").replace("Listening...\n", "")
            
            if raw_text.strip():
                if self.mode == "docs":
                    corrected_text = self.fix_grammar_with_gemini(raw_text)
                    self.text_display.insert("end", f"\nCorrected Text:\n{corrected_text}\n")
                    self.open_and_type_in_docs(corrected_text)
                    self.status_label.configure(text="Done! Text sent to Google Docs.")
                else:
                    generated_code = self.generate_python_code(raw_text)
                    self.text_display.insert("end", f"\nGenerated Code:\n{generated_code}\n")
                    self.status_label.configure(text="Python code generated!")
            else:
                self.status_label.configure(text="No text detected.")
        except Exception as e:
            self.log_to_ui(f"Processing error: {str(e)}")

    def capture_audio(self):
        """Capture audio from microphone"""
        try:
            with self.microphone as source:
                self.log_to_ui("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while self.is_listening:
                    try:
                        self.log_to_ui("Listening... (timeout 1s)")
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                        self.audio_queue.put(audio)
                        self.log_to_ui("Audio captured and queued")
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        self.log_to_ui(f"Audio capture error: {str(e)}")
                        self.text_queue.put(f"Error: {str(e)}")
                        self.stop_and_process()
        except Exception as e:
            self.log_to_ui(f"Microphone error: {str(e)}")

    def process_audio_queue(self):
        """Convert audio to text"""
        while True:
            if not self.audio_queue.empty():
                audio = self.audio_queue.get()
                try:
                    self.log_to_ui("Processing audio...")
                    text = self.recognizer.recognize_google(audio)
                    self.text_queue.put(text)
                    self.log_to_ui(f"Recognized text: {text[:50]}...")  # Log first 50 chars
                except sr.UnknownValueError:
                    self.text_queue.put("(Could not understand audio)")
                    self.log_to_ui("Audio not understood")
                except Exception as e:
                    self.text_queue.put(f"(Error: {str(e)})")
                    self.log_to_ui(f"Recognition error: {str(e)}")

            # Update UI with new text
            self.update_text_display()
            time.sleep(0.1)

    def update_text_display(self):
        """Show transcribed text in UI"""
        while not self.text_queue.empty():
            text = self.text_queue.get()
            self.text_display.insert("end", f"{text}\n")
            self.text_display.see("end")

    def fix_grammar_with_gemini(self, text):
        """Use Gemini to correct grammar for Docs mode"""
        try:
            self.log_to_ui("Sending text to Gemini for grammar correction...")
            prompt = f"You are a transcriptor who writes down what is said. Correct the grammar and improve this text (keep the original meaning):\n{text}"
            response = self.model.generate_content(prompt)
            self.log_to_ui("Received response from Gemini")
            return response.text
        except Exception as e:
            self.log_to_ui(f"Gemini error: {str(e)}")
            return f"Error: {str(e)}"

    def generate_python_code(self, text):
        """Use Gemini to generate Python code"""
        try:
            self.log_to_ui("Sending text to Gemini for code generation...")
            prompt = f"""Convert this natural language description into clean, functional Python code:
            
            Description: {text}
            
            Requirements:
            - Only output the code itself with minimal comments
            - Include all necessary imports
            - Use Python 3.10+ syntax
            - Ensure the code is properly indented
            - Add type hints where appropriate
            
            Python Code:"""
            
            response = self.model.generate_content(prompt)
            self.log_to_ui("Received code from Gemini")
            return response.text
        except Exception as e:
            self.log_to_ui(f"Code generation error: {str(e)}")
            return f"Error generating code: {str(e)}"

    def open_and_type_in_docs(self, text):
        """Open Google Docs and type the text (Docs mode only)"""
        try:
            self.log_to_ui("Opening Google Docs...")
            
            # Direct URL to create new blank document
            docs_url = "https://docs.google.com/document/create"
            
            # Try different methods to ensure it opens
            try:
                # Method 1: Try default browser
                webbrowser.open(docs_url)
                self.log_to_ui("Opened via webbrowser.open")
            except:
                # Method 2: Try platform-specific
                if os.name == 'nt':  # Windows
                    os.startfile(docs_url)
                elif os.name == 'posix':  # Linux/Mac
                    subprocess.run(['xdg-open', docs_url])
                self.log_to_ui("Opened via system command")

            # Wait for browser to open
            time.sleep(3)
            
            # Additional wait if needed (check for browser focus)
            for _ in range(5):
                if "Google Docs" in pyautogui.getActiveWindowTitle():
                    break
                time.sleep(1)
            
            self.log_to_ui(f"Browser active window: {pyautogui.getActiveWindowTitle()}")
            
            # Type the text with failsafe
            self.log_to_ui("Starting to type...")
            pyautogui.click()  # Ensure focus
            time.sleep(0.5)
            
            # Type in chunks to avoid issues
            chunk_size = 200
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i+chunk_size]
                pyautogui.write(chunk, interval=0.02)
                time.sleep(0.1)
            
            self.log_to_ui("Typing complete")
        except Exception as e:
            self.log_to_ui(f"Google Docs error: {str(e)}")

    def clear_text(self):
        """Clear the text display"""
        self.text_display.delete("1.0", "end")
        self.log_to_ui("Text display cleared")