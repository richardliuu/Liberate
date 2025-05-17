import speech_recognition as sr
import google.generativeai as genai
import webbrowser
import pyautogui
import time
import threading
import logging
import os
import subprocess
from queue import Queue
import customtkinter as ctk
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='speech_to_docs.log',
    filemode='w'
)
logger = logging.getLogger('SpeechToDocs')

# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SpeechToDocsApp:
    def __init__(self):
        # Initialize the main window
        self.root = ctk.CTk()
        self.root.title("Speech to Google Docs")
        self.root.geometry("600x500")
        
        # Load API key with validation
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.gemini_api_key:
            raise ValueError("Missing GEMINI_API_KEY in .env file")
            
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel("models/gemini-1.5-flash")
            logger.info("Gemini API configured successfully")
        except Exception as e:
            logger.error(f"Gemini setup failed: {str(e)}")
            raise

        # Speech recognition
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            logger.info(f"Available microphones: {sr.Microphone.list_microphone_names()}")
        except Exception as e:
            logger.error(f"Audio setup failed: {str(e)}")
            raise

        self.is_listening = False
        self.audio_queue = Queue()
        self.text_queue = Queue()

        # UI Setup
        self.setup_ui()

        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self.process_audio_queue,
            daemon=True
        )
        self.processing_thread.start()
        logger.info("Processing thread started")

    def setup_ui(self):
        """Create the application interface"""
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Debug console
        self.debug_console = ctk.CTkTextbox(
            self.main_frame,
            height=100,
            wrap="word",
            font=ctk.CTkFont(size=10)
        )
        self.debug_console.pack(fill="x", pady=(0, 10))
        self.debug_console.insert("end", "Debug console ready...\n")

        # Title and controls
        ctk.CTkLabel(
            self.main_frame,
            text="Speech to Google Docs",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(5, 15))

        self.status_frame = ctk.CTkFrame(self.main_frame)
        self.status_frame.pack(fill="x", pady=5)

        self.status_light = ctk.CTkLabel(
            self.status_frame,
            text="●",
            text_color="red",
            font=ctk.CTkFont(size=24)
        )
        self.status_light.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(side="left")

        self.btn_frame = ctk.CTkFrame(self.main_frame)
        self.btn_frame.pack(fill="x", pady=10)

        self.start_btn = ctk.CTkButton(
            self.btn_frame,
            text="Start Listening",
            command=self.start_listening,
            fg_color="#3B8ED0"
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ctk.CTkButton(
            self.btn_frame,
            text="Stop & Send to Docs",
            command=self.stop_and_process,
            fg_color="#D0353B",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        self.text_display = ctk.CTkTextbox(
            self.main_frame,
            height=200,
            wrap="word",
            font=ctk.CTkFont(size=14)
        )
        self.text_display.pack(fill="both", expand=True, pady=10)

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
        """Stop recording and send to Gemini & Google Docs"""
        try:
            self.is_listening = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_light.configure(text_color="red")
            self.status_label.configure(text="Processing...")
            self.log_to_ui("Processing started...")

            raw_text = self.text_display.get("1.0", "end-1c").replace("Listening...\n", "")
            
            if raw_text.strip():
                self.log_to_ui(f"Raw text captured: {raw_text[:50]}...")  # Log first 50 chars
                
                corrected_text = self.fix_grammar_with_gemini(raw_text)
                self.text_display.insert("end", f"\nCorrected Text:\n{corrected_text}\n")
                self.log_to_ui("Text corrected by Gemini")
                
                self.open_and_type_in_docs(corrected_text)
                self.status_label.configure(text="Done! Text sent to Google Docs.")
                self.log_to_ui("Text sent to Google Docs")
            else:
                self.status_label.configure(text="No text detected.")
                self.log_to_ui("No text detected")
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
        """Use Gemini to correct grammar"""
        try:
            self.log_to_ui("Sending text to Gemini...")
            prompt = f"Correct the grammar and improve this text (keep the original meaning):\n{text}"
            response = self.model.generate_content(prompt)
            self.log_to_ui("Received response from Gemini")
            return response.text
        except Exception as e:
            self.log_to_ui(f"Gemini error: {str(e)}")
            return f"Error: {str(e)}"

    def open_and_type_in_docs(self, text):
        """Improved Google Docs opening and typing"""
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

    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = SpeechToDocsApp()
    app.run()