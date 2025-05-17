# Splitting everything into class-based files
# Reducing clutter 

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