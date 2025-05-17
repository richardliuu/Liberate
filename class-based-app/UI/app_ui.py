import customtkinter as ctk
from core.facialtracker import FacialTracker
from core.voiceassist import VoiceAssistantCore
from UI.voice_ui import VoiceAssistantUI

class FacialMouseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Facial Mouse Controller & Voice Assistant")
        self.geometry("900x700")
        
        # Create tab view
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True)
        
        # Create the tabs on top 
        # Might want to make their size bigger so that it is easier to click on, especially when using the facial controlelr 
        self.tab_home = self.tabview.add("Facial Control")
        self.tab_voice = self.tabview.add("Voice Assistant")
        self.tab_settings = self.tabview.add("Settings")
        
        # Initialize controllers
        self.facial_controller = FacialTracker(self)
        self.voice_assistant = VoiceAssistantCore(self)
        
        # Setup UI components
        self.setup_facial_control_tab()
        self.setup_voice_assistant_tab()
        self.setup_settings_tab()

    def setup_facial_control_tab(self):
        # Need to add facial control UI components here
        pass
        
    def setup_voice_assistant_tab(self):
        # Need to add voice assistant UI components here
        pass
        
    def setup_settings_tab(self):
        # Need to add settings UI components 
        pass