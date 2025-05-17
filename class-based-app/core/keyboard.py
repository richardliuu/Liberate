import customtkinter as ctk
import pyautogui
import time
import threading
import win32gui
from pynput import keyboard
from ctypes import windll

# High DPI awareness
windll.shcore.SetProcessDpiAwareness(1)

class VirtualKeyboard(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Basic window configuration
        self.title("Virtual Keyboard")
        self.geometry("800x300")
        self.position_window()
        self.configure(fg_color="#333333")
        
        # Window behavior
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.95)
        
        # Keyboard state
        self.visible = False
        self.shift_active = False
        
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.create_keyboard_layout()
        self.withdraw()
        
        # Setup keyboard listener
        self.listener = None
        self.setup_keyboard_listener()
    
    def setup_keyboard_listener(self):
        """Setup keyboard listener to detect hotkey"""
        def on_press(key):
            try:
                if key == keyboard.Key.scroll_lock:
                    self.toggle()
            except AttributeError:
                pass
        
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()
    
    def position_window(self):
        """Position window at bottom center"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 800) // 2
        y = screen_height - 350
        self.geometry(f"800x300+{x}+{y}")
    
    def create_keyboard_layout(self):
        """Create keyboard interface"""
        main_frame = ctk.CTkFrame(self, fg_color="#333333")
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Keyboard layout
        self.keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Backspace'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'Enter'],
            ['Shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'Shift'],
            ['Ctrl', 'Alt', 'Space', 'Tab', '←', '→', '↑', '↓']
        ]
        
        # Create frames and buttons
        self.frames = []
        self.buttons = {}
        for row_idx, row in enumerate(self.keys):
            frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            frame.pack(expand=True, fill='both', padx=2, pady=2)
            self.frames.append(frame)
            
            for key in row:
                self.buttons[key] = self._create_key_button(row_idx, key)
        
        # Close button
        ctk.CTkButton(
            main_frame,
            text="Close Keyboard",
            fg_color="#D32F2F",
            command=self.hide
        ).pack(side='right', padx=10, pady=5)
    
    def _create_key_button(self, row_idx, key):
        """Create consistent key buttons"""
        if key == 'Space':
            width = 250
            fg_color = ("#3B8ED0", "#1F6AA5")
        elif key in ['Backspace', 'Enter', 'Shift']:
            width = 70
            fg_color = ("#555555", "#333333")
        elif key in ['←', '→', '↑', '↓']:
            width = 40
            fg_color = ("#555555", "#333333")
        else:
            width = 48
            fg_color = ("#444444", "#222222")
        
        button = ctk.CTkButton(
            self.frames[row_idx],
            text=key.upper() if key.isalpha() else key,
            width=width,
            height=40,
            fg_color=fg_color,
            text_color="white",
            corner_radius=6,
            command=lambda k=key: self.press_key(k)
        )
        button.pack(side='left', padx=2, pady=2)
        return button
    
    def press_key(self, key):
        """Handle key press with visual feedback"""
        btn = self.buttons[key]
        original_color = btn.cget("fg_color")
        btn.configure(fg_color="#aaddff", text_color="#000000")
        
        # Handle shift key
        if key == 'Shift':
            self.shift_active = not self.shift_active
            self._update_key_labels()
            btn.configure(fg_color=original_color, text_color="white")
            return
        
        # Send the key press
        self._send_keystroke(key)
        
        # Reset button appearance
        self.after(150, lambda: btn.configure(
            fg_color=original_color,
            text_color="white"
        ))
    
    def _update_key_labels(self):
        """Update key labels when shift state changes"""
        for key, btn in self.buttons.items():
            if key.isalpha():
                btn.configure(text=key.upper() if self.shift_active else key.lower())
    
    def _send_keystroke(self, key):
        """Send keystroke using pyautogui"""
        try:
            if key == 'Backspace':
                pyautogui.press('backspace')
            elif key == 'Enter':
                pyautogui.press('enter')
            elif key == 'Space':
                pyautogui.press('space')
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
            elif key.isalpha():
                if self.shift_active:
                    pyautogui.press(key.upper())
                else:
                    pyautogui.press(key.lower())
            else:
                pyautogui.press(key)
        except Exception as e:
            print(f"Key press error: {e}")
    
    def show(self):
        """Show the keyboard"""
        if not self.visible:
            self.deiconify()
            self.lift()
            self.visible = True
    
    def hide(self):
        """Hide the keyboard"""
        if self.visible:
            self.withdraw()
            self.visible = False
    
    def toggle(self):
        """Toggle keyboard visibility"""
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def __del__(self):
        """Clean up keyboard listener"""
        if self.listener:
            self.listener.stop()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = ctk.CTk()
    app.withdraw()
    
    keyboard = VirtualKeyboard()
    
    # Instructions
    print("Press Scroll Lock to toggle keyboard")
    
    app.mainloop()