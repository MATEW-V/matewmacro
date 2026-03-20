import tkinter as tk
import os
import subprocess
import time
import cv2
import numpy as np
import mss
import keyboard
import threading
from threading import Thread
from datetime import datetime
import sys

# ============ LETTER MACRO CONFIG ============
TEMPLATE_FOLDER = r"c:\Users\Matthew V\Desktop\MATEWMACRO\letter_templates"
SLOT1_LOCATION = {'left': 860, 'top': 200, 'width': 50, 'height': 100}

# Verify folder exists
print("=" * 50)
print("PATH DEBUG INFORMATION")
print("=" * 50)
print(f"Templates folder: {TEMPLATE_FOLDER}")
print(f"Folder exists? {os.path.exists(TEMPLATE_FOLDER)}")

if os.path.exists(TEMPLATE_FOLDER):
    print(f"Files found: {os.listdir(TEMPLATE_FOLDER)}")
else:
    print(f"❌ ERROR: Templates folder not found!")
    print(f"Please check the path: {TEMPLATE_FOLDER}")
    input("Press Enter to exit...")
    sys.exit(1)
print("=" * 50)

class LetterMacro:
    def __init__(self, parent, status_callback=None):
        self.enabled = False
        self.running = False
        self.region = SLOT1_LOCATION
        self.templates = []
        self.debug = True
        self.status_callback = status_callback
        self.parent = parent
        
        self.DETECTION_THRESHOLD = 0.85
        self.MIN_BRIGHTNESS = 10
        self.FAST_POLL = 0.05
        self.KEY_DELAY = 0.10
        self.thread = None
        
        self.load_templates()
        
    def log(self, message):
        if self.debug:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            if self.status_callback:
                self.status_callback(message)
        
    def load_templates(self):
        self.log("Loading templates...")
        self.templates = []
        loaded = 0
        
        for f in os.listdir(TEMPLATE_FOLDER):
            if not f.lower().endswith('.png'):
                continue
                
            letter = f[1].upper() if f.startswith('p') else f[0].upper()
            path = os.path.join(TEMPLATE_FOLDER, f)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            
            if img is not None:
                self.templates.append((letter, img))
                loaded += 1
                self.log(f"Loaded: {f} -> {letter}")
                
        self.log(f"Loaded {loaded} templates")
        return loaded > 0
        
    def detect_in_region(self, img):
        try:
            if img.shape[2] == 4:
                gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
            if np.mean(gray) < self.MIN_BRIGHTNESS:
                return None, 0
                
            best_letter, best_score = None, 0
            
            for letter, template in self.templates:
                if template.shape[0] > gray.shape[0] or template.shape[1] > gray.shape[1]:
                    continue
                result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
                _, score, _, _ = cv2.minMaxLoc(result)
                if score > 0.98:
                    return letter, score
                if score > best_score:
                    best_score, best_letter = score, letter
                    
            return (best_letter, best_score) if best_score >= self.DETECTION_THRESHOLD else (None, best_score)
        except Exception as e:
            self.log(f"Detection error: {e}")
            return None, 0
        
    def macro_loop(self):
        self.log("Letter macro running")
        type_count = 0
        
        try:
            with mss.mss() as sct:
                while self.enabled:
                    try:
                        if self.parent and self.parent.game_active:
                            img = np.array(sct.grab(self.region))
                            letter, score = self.detect_in_region(img)
                            
                            if letter:
                                self.log(f"Typing '{letter}'")
                                keyboard.press_and_release(letter.lower())
                                type_count += 1
                                time.sleep(self.KEY_DELAY)
                        else:
                            time.sleep(0.5)
                        
                        time.sleep(self.FAST_POLL)
                    except Exception as e:
                        self.log(f"Loop error: {e}")
                        time.sleep(1)
        except Exception as e:
            self.log(f"Macro error: {e}")
                    
        self.log(f"Stopped - typed {type_count} letters")
        self.running = False
        
    def start(self):
        if not self.running and not self.enabled:
            self.enabled = True
            self.running = True
            self.thread = threading.Thread(target=self.macro_loop, daemon=True)
            self.thread.start()
            self.log("Started")
            return True
        return False
        
    def stop(self):
        self.enabled = False
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.log("Stopped")
        
    def set_delay(self, ms):
        self.KEY_DELAY = ms / 1000


class MATEWmacro:
    def __init__(self):
        self.state_file = os.path.join(os.path.dirname(__file__), "state.txt")
        self.game_active = False
        self.letter_macro = None
        self.letter_macro_enabled = False
        
        with open(self.state_file, 'w') as f:
            f.write("0,0,0,0")
        
        ahk_script = os.path.join(os.path.dirname(__file__), "macros.ahk")
        if os.path.exists(ahk_script):
            subprocess.Popen([ahk_script], shell=True)
        
        self.macros = [
            {"name": "Dodge Cancel", "hotkey": "q", "desc": "Q → delay → right click"},
            {"name": "Macro 2", "hotkey": "XButton1", "desc": "Mouse back → 9"},
            {"name": "Macro 3", "hotkey": "XButton2", "desc": "Mouse forward → 8"},
            {"name": "Letter Macro", "hotkey": "", "desc": "Types letters"},
        ]
        
        self.buttons = []
        self.letter_status = ""
        
        self.setup_gui()
        Thread(target=self.monitor_roblox, daemon=True).start()
        self.letter_macro = LetterMacro(self, self.update_letter_status)
        print("✅ Letter macro initialized")
        
    def update_letter_status(self, message):
        if "Typing" in message:
            self.letter_status = message
            self.root.after(0, self.update_buttons)
    
    def monitor_roblox(self):
        try:
            import pywinctl as pwc
            while True:
                try:
                    active = pwc.getActiveWindow()
                    self.game_active = active and "roblox" in active.title.lower()
                except:
                    self.game_active = False
                time.sleep(0.5)
        except ImportError:
            self.game_active = True
    
    def read_states(self):
        try:
            with open(self.state_file, 'r') as f:
                content = f.read().strip()
                if content:
                    return [x == "1" for x in content.split(",")]
                return [False, False, False, False]
        except:
            return [False, False, False, False]
    
    def write_states(self, states):
        with open(self.state_file, 'w') as f:
            f.write(",".join(["1" if s else "0" for s in states]))
    
    def toggle_macro(self, index):
        states = self.read_states()
        states[index] = not states[index]
        self.write_states(states)
        
        if index == 3:
            if states[3]:
                if not self.letter_macro_enabled and self.letter_macro:
                    if self.letter_macro.start():
                        self.letter_macro_enabled = True
            else:
                if self.letter_macro_enabled and self.letter_macro:
                    self.letter_macro.stop()
                    self.letter_macro_enabled = False
        
        self.update_buttons()
    
    def update_letter_delay(self, val=None):
        if self.letter_macro:
            ms = self.letter_delay_var.get()
            self.letter_macro.set_delay(ms)
            self.letter_delay_label.config(text=f"{ms}ms")
    
    def update_buttons(self):
        try:
            states = self.read_states()
            
            for i, btn in enumerate(self.buttons):
                if i < 3:
                    btn.config(
                        text=f"{self.macros[i]['name']}: {'ON' if states[i] else 'OFF'}",
                        bg="green" if states[i] else "lightgray",
                        fg="white" if states[i] else "black"
                    )
                else:
                    if states[i] and self.letter_status:
                        display_text = f"Letter: {self.letter_status[-20:]}"
                    else:
                        display_text = f"{self.macros[i]['name']}: {'ON' if states[i] else 'OFF'}"
                    
                    btn.config(
                        text=display_text,
                        bg="green" if states[i] else "lightgray",
                        fg="white" if states[i] else "black"
                    )
            
            self.status_label.config(
                text=f"Roblox: {'ACTIVE' if self.game_active else 'INACTIVE'}",
                fg="green" if self.game_active else "red"
            )
            
        except Exception as e:
            print(f"Update error: {e}")
        
        self.root.after(500, self.update_buttons)
    
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)
        self.root.title("MATEW MACRO")
        self.root.geometry("500x250")
        
        main = tk.Frame(self.root, padx=20, pady=20)
        main.pack()
        
        self.status_label = tk.Label(main, text="Roblox: INACTIVE", 
                                    font=("Arial", 10, "bold"), fg="red")
        self.status_label.pack(pady=(0, 10))
        
        for i, m in enumerate(self.macros):
            frame = tk.Frame(main)
            frame.pack(fill=tk.X, pady=3)
            
            hotkey_text = f"[{m['hotkey']}]" if m['hotkey'] else "    "
            tk.Label(frame, text=hotkey_text, width=8, 
                    fg="blue", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            
            btn = tk.Button(frame, text=f"{m['name']}: OFF",
                          command=lambda idx=i: self.toggle_macro(idx),
                          width=18, bg="lightgray")
            btn.pack(side=tk.LEFT, padx=5)
            self.buttons.append(btn)
            
            if i == 3:
                slider_frame = tk.Frame(main)
                slider_frame.pack(fill=tk.X, pady=(0, 10), padx=(40, 0))
                
                tk.Label(slider_frame, text="Delay:", width=8, 
                        font=("Arial", 8)).pack(side=tk.LEFT)
                
                self.letter_delay_var = tk.IntVar(value=100)
                delay_slider = tk.Scale(slider_frame, from_=100, to=200, 
                                       orient="horizontal", variable=self.letter_delay_var,
                                       length=150, command=self.update_letter_delay,
                                       showvalue=False)
                delay_slider.pack(side=tk.LEFT, padx=5)
                
                self.letter_delay_label = tk.Label(slider_frame, text="100ms", 
                                                  width=5, font=("Arial", 8))
                self.letter_delay_label.pack(side=tk.LEFT)
            else:
                tk.Label(frame, text=m["desc"], fg="gray", 
                        font=("Arial", 8)).pack(side=tk.LEFT)
    
    def exit_app(self):
        if self.letter_macro and self.letter_macro_enabled:
            self.letter_macro.stop()
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    app = MATEWmacro()
    app.root.mainloop()