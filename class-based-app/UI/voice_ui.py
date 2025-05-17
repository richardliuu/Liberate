import customtkinter as ctk
from core.voiceassist import VoiceAssistantCore

class VoiceAssistantUI:
    def __init__(self, parent_frame, api_key: str):
        self.frame = parent_frame
        self.api_key = api_key
        self.assistant = VoiceAssistantCore(api_key)
        self._setup_ui()
        self._setup_callbacks()

    def cleanup(self):
    # Stop recording if active
        if hasattr(self.assistant, 'is_recording') and self.assistant.is_recording:
            self.assistant.stop_recording()
        
    # Close any resources in the assistant core
        if hasattr(self.assistant, 'cleanup'):
            self.assistant.cleanup()

    def _setup_ui(self):
        # Main chat display
        self.chat_display = ctk.CTkTextbox(
            self.frame,
            font=ctk.CTkFont(size=14),
            corner_radius=10
        )
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=10)

        # Control frame
        control_frame = ctk.CTkFrame(self.frame)
        control_frame.pack(fill="x", padx=10, pady=5)

        # Record button
        self.record_btn = ctk.CTkButton(
            control_frame,
            text="🎤 Start Listening",
            command=self._toggle_recording,
            width=200
        )
        self.record_btn.pack(side="left", padx=5)

        # Status indicator
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="Ready",
            width=100
        )
        self.status_label.pack(side="left", padx=5)

        # Processing indicator
        self.processing_indicator = ctk.CTkLabel(
            control_frame,
            text="",
            width=30
        )
        self.processing_indicator.pack(side="right", padx=5)

    def _setup_callbacks(self):
        self.assistant.register_callback('on_status_change', self._update_status)
        self.assistant.register_callback('on_user_input', self._display_user_message)
        self.assistant.register_callback('on_ai_response', self._display_ai_message)
        self.assistant.register_callback('on_error', self._display_error)

    def _toggle_recording(self):
        if self.assistant.is_recording:
            self.assistant.stop_recording()
            self.record_btn.configure(text="🎤 Start Listening")
        else:
            if self.assistant.start_recording():
                self.record_btn.configure(text="🔴 Stop Listening")

    def _update_status(self, message: str):
        self.status_label.configure(text=message)

    def _display_user_message(self, text: str):
        self._append_to_chat("You", text)

    def _display_ai_message(self, text: str):
        self._append_to_chat("Gemini", text)

    def _display_error(self, error: str):
        self._append_to_chat("Error", error)

    def _append_to_chat(self, sender: str, message: str):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\n{sender}: {message}\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")