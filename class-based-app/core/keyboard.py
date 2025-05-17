import customtkinter as ctk
import tkinter as tk
import pyautogui
import time
import threading
import win32gui
import win32con
import win32api

def get_active_window_handle():
    try:
        return win32gui.GetForegroundWindow()
    except:
        return None

def focus_window(handle):
    try:
        if handle and win32gui.IsWindow(handle):
            # Use AttachThreadInput for more reliable focus management
            foreground_thread = win32api.GetWindowThreadProcessId(win32gui.GetForegroundWindow())[0]
            my_thread = win32api.GetCurrentThreadId()
            
            # Attach threads to ensure focus switch works properly
            win32api.AttachThreadInput(my_thread, foreground_thread, True)
            win32gui.SetForegroundWindow(handle)
            win32api.AttachThreadInput(my_thread, foreground_thread, False)
            return True
    except Exception as e:
        print(f"Failed to focus window: {e}")
    return False

class VirtualKeyboard:
    def __init__(self, parent=None):
        if parent is None:
            raise ValueError("VirtualKeyboard requires a parent window")
        
        self.target_window = None
            
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Virtual Keyboard")
        
        # Set window style to be less intrusive
        self.window.attributes('-topmost', True)
        self.window.overrideredirect(False)
        
        # Make it a tool window (doesn't appear in taskbar)
        try:
            hwnd = self.window.winfo_id()
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                                 win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | 
                                 win32con.WS_EX_TOOLWINDOW)
        except Exception as e:
            print(f"Error setting window style: {e}")
        
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.visible = False
        self.window.withdraw()

        # Get screen dimensions
        screen_width, screen_height = pyautogui.size()
        
        # Keyboard dimensions
        keyboard_width = 800
        keyboard_height = 300
        
        # Position the keyboard just above the taskbar
        taskbar_height = self.get_taskbar_height()
        y_position = screen_height - keyboard_height - taskbar_height
        
        self.window.geometry(f"{keyboard_width}x{keyboard_height}+{(screen_width-keyboard_width)//2}+{y_position}")
        
        # Making the keyboard semi-transparent but still clickable
        self.window.attributes('-alpha', 0.9)
        
        self.create_keyboard_layout()
        self.window.withdraw()
        self.visible = False
        
        # Store the active window when keyboard is shown
        self.active_window_before = None
    
    def get_taskbar_height(self):
        try:
            taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
            rect = win32gui.GetWindowRect(taskbar)
            screen_height = win32gui.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # Taskbar could be on bottom, top, left or right
            if rect[1] > 0:  
                return rect[3] - rect[1]
            else:  # Taskbar at bottom (most common)
                return screen_height - rect[3]
        except:
            # Default fallback if we can't detect taskbar
            return 40
    
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
        
        # Add a reminder label for the target window
        self.target_label = ctk.CTkLabel(
            control_frame,
            text="No target window selected",
            text_color="gray"
        )
        self.target_label.pack(side='left', padx=10)
    
    def update_transparency(self, value):
        self.window.attributes('-alpha', value)
    
    def press_key(self, key):
        # Visual feedback
        original_color = self.buttons[key].cget("fg_color")
        self.buttons[key].configure(fg_color="#aaddff", text_color="#000000")
            
        # Make sure we have a valid target window
        if not self.target_window:
            self.target_window = self.active_window_before
        
        if not self.target_window:
            print("No target window available")
            return
            
        # Execute keystroke in separate thread
        threading.Thread(target=self._execute_keystroke, args=(key,)).start()
            
        # Reset button appearance
        self.window.after(100, lambda k=key: self.buttons[k].configure(
            fg_color=original_color, 
            text_color="white"
        ))
        
    def _execute_keystroke(self, key):
        try:
            # Use reliable method to store keyboard window handle before refocusing
            keyboard_hwnd = self.window.winfo_id()
            
            # Critical: Bring target window to foreground
            if self.target_window:
                # Set focus to target window
                if focus_window(self.target_window):
                    time.sleep(0.05)  # Short pause to let focus change take effect
                    
                    # Map special keys to PyAutoGUI keys
                    key_map = {
                        '←': 'left',
                        '→': 'right',
                        '↑': 'up',
                        '↓': 'down',
                        'Space': 'space'
                    }
                    
                    # Use mapped key if available
                    send_key = key_map.get(key, key)
                    
                    # Special handling for modifier keys
                    if key == 'Shift':
                        pyautogui.press('shift')
                    elif key == 'Ctrl':
                        pyautogui.press('ctrl')
                    elif key == 'Alt':
                        pyautogui.press('alt')
                    else:
                        # Send the actual key press
                        pyautogui.press(send_key)
                    
                    # Give time for the key action to register
                    time.sleep(0.05)
                else:
                    print(f"Failed to focus target window for key: {key}")
            else:
                print("No target window to send keystrokes to")
                
        except Exception as e:
            print(f"Error sending keystroke: {e}")
        
    def show(self):
        if not self.visible:
            # Store the currently active window before showing keyboard
            self.active_window_before = get_active_window_handle()
            self.target_window = self.active_window_before
            
            try:
                window_title = win32gui.GetWindowText(self.target_window)
                self.target_label.configure(text=f"Target: {window_title[:20]}{'...' if len(window_title) > 20 else ''}")
            except:
                self.target_label.configure(text="Unknown target window")
            
            # Make keyboard visible
            self.window.deiconify()
            self.visible = True
            
            # Configure to stay on top but not interfere
            self.window.attributes('-topmost', True)
            try:
                hwnd = self.window.winfo_id()
                # Use SWP_NOACTIVATE to prevent taking focus
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | 
                                    win32con.SWP_NOACTIVATE)
            except Exception as e:
                print(f"Error configuring window: {e}")
    
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