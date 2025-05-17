import customtkinter as ctk
import tkinter as tk
import pyautogui
import time
import threading
import win32gui

def get_active_window_handle():
    """Get the handle of the currently active window"""
    try:
        return win32gui.GetForegroundWindow()
    except:
        return None

def focus_window(handle):
    """Set focus to a window by its handle"""
    try:
        if handle and win32gui.IsWindow(handle):
            win32gui.SetForegroundWindow(handle)
            return True
    except:
        pass
    return False

class VirtualKeyboard(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__()
        screen_width = self.winfo_screenwidth()
        self.window = ctk.CTkToplevel(parent) if parent else ctk.CTk()
        self.window.title("Virtual Keyboard")
        self.window.attributes('-topmost', True)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        keyboard_width = 800
        keyboard_height = 250
        x = (screen_width - keyboard_width) // 2
        y = screen_height - keyboard_height - 50  # 50px above taskbar

        self.geometry(f"{keyboard_width}x{keyboard_height}+{x}+{y}")
        
        # Making the keyboard semi-transparent
        self.window.attributes('-alpha', 0.9)
        
        # Get screen dimensions
        screen_width, screen_height = pyautogui.size()

        # Keyboard dimensions
        keyboard_width = 800
        keyboard_height = 300

        # Position the keyboard near the bottom of the screen
        self.window.geometry(f"{keyboard_width}x{keyboard_height}+{(screen_width-keyboard_width)//2}+{screen_height-keyboard_height-100}")
        
        self.create_keyboard_layout()
        self.window.withdraw()
        self.visible = False
        
        # Store the active window when keyboard is shown
        self.active_window_before = None
    
    def create_keyboard_layout(self):
        # Modern dark themed keyboard layout
        self.keys = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Backspace'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'Enter'],
            ['Shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'Shift'],
            ['Ctrl', 'Alt', 'Space', 'Tab', '←', '→', '↑', '↓']
        ]
        
        # Create frames for each row with consistent styling
        self.frames = []
        for i in range(len(self.keys)):
            frame = ctk.CTkFrame(self.window, fg_color="transparent")
            frame.pack(expand=True, fill='both')
            self.frames.append(frame)
        
        # Create buttons for each key with CustomTkinter styling
        self.buttons = {}
        for row_idx, row in enumerate(self.keys):
            for key in row:
                if key == 'Space':
                    # Space bar is wider
                    button = ctk.CTkButton(
                        self.frames[row_idx], 
                        text=key,
                        width=250,
                        height=40, 
                        fg_color=("#3B8ED0", "#1F6AA5"),  # Blue theme matching main app
                        text_color=("white", "white"),
                        corner_radius=8,
                        command=lambda k=key: self.press_key(k)
                    )
                elif key in ['Backspace', 'Enter', 'Shift', 'Ctrl', 'Alt', 'Tab', '←', '→', '↑', '↓']:
                    # Special keys
                    button = ctk.CTkButton(
                        self.frames[row_idx], 
                        text=key,
                        width=70,
                        height=40, 
                        fg_color=("#555555", "#333333"),  # Darker for special keys
                        text_color=("white", "white"),
                        corner_radius=8,
                        command=lambda k=key: self.press_key(k)
                    )
                else:
                    # Regular keys
                    button = ctk.CTkButton(
                        self.frames[row_idx], 
                        text=key,
                        width=48,
                        height=40, 
                        fg_color=("#444444", "#222222"),  # Dark gray for regular keys
                        text_color=("white", "white"),
                        corner_radius=8,
                        command=lambda k=key: self.press_key(k)
                    )
                
                button.pack(side='left', padx=2, pady=2)
                self.buttons[key] = button
                
        # Add control buttons at the bottom
        control_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        control_frame.pack(fill='x', pady=5)
        
        # Add a close button
        close_button = ctk.CTkButton(
            control_frame, 
            text="Close Keyboard", 
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            text_color="white",
            corner_radius=8,
            command=self.hide
        )
        close_button.pack(side='right', padx=10)
        
        # Add transparency control
        transparency_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        transparency_frame.pack(side='left', padx=10)
        
        ctk.CTkLabel(
            transparency_frame, 
            text="Transparency:"
        ).pack(side='left', padx=(0, 5))

        self.transparency_var = ctk.DoubleVar(value=0.9)
        transparency_slider = ctk.CTkSlider(
            transparency_frame, 
            from_=0.2, 
            to=1.0,
            width=120,
            variable=self.transparency_var,
            command=self.update_transparency
        )
        transparency_slider.pack(side='left')
    
    def update_transparency(self, value):
        """Update keyboard transparency"""
        self.window.attributes('-alpha', value)
    
    def press_key(self, key):
        """Handle key press events"""
        # Visual feedback by changing button appearance
        original_color = self.buttons[key].cget("fg_color")
        hover_color = self.buttons[key].cget("hover_color")
        self.buttons[key].configure(fg_color="#aaddff", text_color="#000000")
        
        # Remember the keyboard window handle
        keyboard_handle = None
        try:
            keyboard_handle = win32gui.GetForegroundWindow()
        except:
            pass
        
        # Use a separate thread to restore focus and send keystroke
        threading.Thread(target=self._execute_keystroke, args=(key, keyboard_handle)).start()
        
        # Reset button appearance after a delay
        self.window.after(100, lambda k=key: self.buttons[k].configure(fg_color=original_color, text_color="white"))
        
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
        if self.visible:
            # Try to restore focus to the window that was active before
            if self.active_window_before:
                focus_window(self.active_window_before)
            
            self.window.withdraw()
            self.visible = False
    
    def toggle(self):
        if self.visible:
            self.hide()
        else:
            self.show()