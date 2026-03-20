import tkinter as tk
import os
import subprocess
import time
import cv2
import numpy as np
import mss
import keyboard
import threading
from datetime import datetime
import sys
import shutil
import tkinter.messagebox as mb

# ============ CONFIGURATION ============
# Get correct path for both script and compiled exe
if getattr(sys, 'frozen', False):
    # Running as compiled .exe - files are extracted to _MEIPASS
    INTERNAL_PATH = sys._MEIPASS
    EXTERNAL_PATH = os.path.dirname(sys.executable)
else:
    # Running as script
    INTERNAL_PATH = os.path.dirname(os.path.abspath(__file__))
    EXTERNAL_PATH = INTERNAL_PATH

# Internal paths (files inside the exe)
TEMPLATE_FOLDER = os.path.join(INTERNAL_PATH, "letter_templates")
AHK_SCRIPT_SOURCE = os.path.join(INTERNAL_PATH, "macros.ahk")

# External paths (files created/used in user's folder)
STATE_FILE = os.path.join(EXTERNAL_PATH, "state.txt")
PID_FILE = os.path.join(EXTERNAL_PATH, "python_pid.txt")
EXIT_SIGNAL = os.path.join(EXTERNAL_PATH, "exit_signal.txt")
AHK_SCRIPT_DEST = os.path.join(EXTERNAL_PATH, "macros.ahk")

SLOT1_LOCATION = {'left': 860, 'top': 200, 'width': 50, 'height': 100}

MACROS = [
    {"name": "Dodge Cancel", "hotkey": "Q", "desc": "Q → delay → right click", "type": "ahk"},
    {"name": "b mbutton -> 9", "hotkey": "XButton1", "desc": "Mouse back → 9", "type": "ahk"},
    {"name": "f mbutton -> 8", "hotkey": "XButton2", "desc": "Mouse forward → 8", "type": "ahk"},
    {"name": "Roll Parry", "hotkey": "CTRL+F", "desc": "hold ctrl and m1 after for insta uppercut", "type": "ahk"},
    {"name": "Ritual Cast", "hotkey": "", "desc": "automatic ritual caster", "type": "python", 
     "delay": 100, "delay_min": 100, "delay_max": 200},
]

# Check if templates exist (inside exe)
if not os.path.exists(TEMPLATE_FOLDER):
    print(f"❌ ERROR: Templates folder not found: {TEMPLATE_FOLDER}")
    mb.showerror("Error", f"Templates folder not found!\n\n{TEMPLATE_FOLDER}")
    sys.exit(1)

print("=" * 50)
print(f"Internal Path: {INTERNAL_PATH}")
print(f"External Path: {EXTERNAL_PATH}")
print(f"Templates: {TEMPLATE_FOLDER}")
print("=" * 50)

class LetterMacro:
    def __init__(self, parent, status_callback=None):
        self.enabled = False
        self.region = SLOT1_LOCATION
        self.templates = []
        self.debug = True
        self.status_callback = status_callback
        self.parent = parent
        self.thread = None
        
        self.DETECTION_THRESHOLD = 0.85
        self.MIN_BRIGHTNESS = 10
        self.FAST_POLL = 0.05
        self.KEY_DELAY = 0.10
        
        self.load_templates()
        
    def log(self, message):
        if self.debug:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            if self.status_callback:
                self.status_callback(message)
        
    def load_templates(self):
        self.log("Loading templates...")
        self.templates = []
        
        for f in os.listdir(TEMPLATE_FOLDER):
            if not f.lower().endswith('.png'):
                continue
                
            letter = f[1].upper() if f.startswith('p') else f[0].upper()
            img = cv2.imread(os.path.join(TEMPLATE_FOLDER, f), cv2.IMREAD_GRAYSCALE)
            
            if img is not None:
                self.templates.append((letter, img))
                self.log(f"Loaded: {f} -> {letter}")
                
        self.log(f"Loaded {len(self.templates)} templates")
        return len(self.templates) > 0
        
    def detect_in_region(self, img):
        try:
            gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY) if img.shape[2] == 4 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if np.mean(gray) < self.MIN_BRIGHTNESS:
                return None
                
            best_letter, best_score = None, 0
            
            for letter, template in self.templates:
                if template.shape[0] > gray.shape[0] or template.shape[1] > gray.shape[1]:
                    continue
                score = cv2.minMaxLoc(cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED))[1]
                if score > 0.98:
                    return letter
                if score > best_score:
                    best_score, best_letter = score, letter
                    
            return best_letter if best_score >= self.DETECTION_THRESHOLD else None
        except Exception as e:
            self.log(f"Detection error: {e}")
            return None
        
    def macro_loop(self):
        self.log("Letter macro running")
        type_count = 0
        
        with mss.mss() as sct:
            while self.enabled:
                try:
                    if self.parent.game_active:
                        img = np.array(sct.grab(self.region))
                        letter = self.detect_in_region(img)
                        
                        if letter:
                            self.log(f"Typing '{letter}'")
                            keyboard.press_and_release(letter.lower())
                            type_count += 1
                            time.sleep(self.KEY_DELAY)
                    
                    time.sleep(self.FAST_POLL)
                except Exception as e:
                    self.log(f"Loop error: {e}")
                    time.sleep(0.1)
                    
        self.log(f"Stopped - typed {type_count} letters")
        
    def start(self):
        if not self.enabled:
            self.enabled = True
            self.thread = threading.Thread(target=self.macro_loop, daemon=True)
            self.thread.start()
            self.log("Started")
            return True
        return False
        
    def stop(self):
        self.enabled = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.log("Stopped")
        
    def set_delay(self, ms):
        self.KEY_DELAY = ms / 1000


class MATEWmacro:
    def __init__(self):
        self.state_file = STATE_FILE
        self.game_active = False
        self.macro_configs = MACROS
        
        # Only create state file if it doesn't exist (don't overwrite)
        if not os.path.exists(self.state_file):
            with open(self.state_file, 'w') as f:
                f.write(",".join(["0"] * len(self.macro_configs)))
            print(f"✅ Created state file: {self.state_file}")
        
        # Write Python PID for AHK to monitor
        self.pid_file = PID_FILE
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            print(f"✅ Python PID: {os.getpid()}")
        except Exception as e:
            print(f"⚠️ Could not write PID file: {e}")
        
        # Copy AHK script from internal to external if needed
        if os.path.exists(AHK_SCRIPT_SOURCE):
            if not os.path.exists(AHK_SCRIPT_DEST):
                try:
                    shutil.copy2(AHK_SCRIPT_SOURCE, AHK_SCRIPT_DEST)
                    print(f"✅ AHK script copied to: {AHK_SCRIPT_DEST}")
                except Exception as e:
                    print(f"⚠️ Could not copy AHK script: {e}")
            
            # Launch AHK script from external location
            if os.path.exists(AHK_SCRIPT_DEST):
                subprocess.Popen([AHK_SCRIPT_DEST], shell=True)
                print(f"✅ AHK script launched from: {AHK_SCRIPT_DEST}")
            else:
                print(f"⚠️ AHK script not found at: {AHK_SCRIPT_DEST}")
        else:
            print(f"⚠️ Internal AHK script not found: {AHK_SCRIPT_SOURCE}")
        
        # Initialize Python macros
        self.python_macros = [None] * len(self.macro_configs)
        self.python_macro_states = [False] * len(self.macro_configs)
        
        for i, config in enumerate(self.macro_configs):
            if config.get("type") == "python":
                self.python_macros[i] = LetterMacro(self, lambda msg, idx=i: self.update_macro_status(idx, msg))
        
        self.setup_gui()
        threading.Thread(target=self.monitor_roblox, daemon=True).start()
        print(f"✅ Initialized {len(self.macro_configs)} macros")
    
    def update_macro_status(self, index, message):
        if "Typing" in message:
            self.macro_statuses[index] = message
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
        except:
            pass
        return [False] * len(self.macro_configs)
    
    def write_states(self, states):
        with open(self.state_file, 'w') as f:
            f.write(",".join(["1" if s else "0" for s in states]))
    
    def toggle_macro(self, index):
        states = self.read_states()
        states[index] = not states[index]
        self.write_states(states)
        
        macro = self.python_macros[index]
        if macro:
            if states[index] and not self.python_macro_states[index]:
                if macro.start():
                    self.python_macro_states[index] = True
            elif not states[index] and self.python_macro_states[index]:
                macro.stop()
                self.python_macro_states[index] = False
        
        self.update_buttons()
    
    def update_buttons(self):
        states = self.read_states()
        
        for i, btn in enumerate(self.buttons):
            config = self.macro_configs[i]
            is_on = states[i]
            
            if config.get("type") == "python" and is_on and i in self.macro_statuses:
                text = f"{config['name']}: {self.macro_statuses[i][-20:]}"
            else:
                text = f"{config['name']}: {'ON' if is_on else 'OFF'}"
            
            btn.config(text=text, bg="green" if is_on else "lightgray", fg="white" if is_on else "black")
        
        self.status_label.config(
            text=f"Roblox: {'ACTIVE' if self.game_active else 'INACTIVE'}",
            fg="green" if self.game_active else "red"
        )
        
        self.root.after(500, self.update_buttons)
    
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)
        self.root.title("MATEW MACRO")
        
        window_height = 100 + len(self.macro_configs) * 35
        self.root.geometry(f"500x{window_height}")
        
        main = tk.Frame(self.root, padx=20, pady=20)
        main.pack()
        
        self.status_label = tk.Label(main, text="Roblox: INACTIVE", font=("Arial", 10, "bold"), fg="red")
        self.status_label.pack(pady=(0, 10))
        
        self.buttons = []
        self.macro_statuses = {}
        
        for i, config in enumerate(self.macro_configs):
            frame = tk.Frame(main)
            frame.pack(fill=tk.X, pady=3)
            
            hotkey = f"[{config['hotkey']}]" if config['hotkey'] else "    "
            tk.Label(frame, text=hotkey, width=8, fg="blue", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            
            btn = tk.Button(frame, text=f"{config['name']}: OFF", 
                          command=lambda idx=i: self.toggle_macro(idx), 
                          width=18, bg="lightgray")
            btn.pack(side=tk.LEFT, padx=5)
            self.buttons.append(btn)
            
            tk.Label(frame, text=config["desc"], fg="gray", font=("Arial", 8)).pack(side=tk.LEFT)
            
            # Slider only for Python macro
            if config.get("type") == "python" and "delay" in config:
                slider_frame = tk.Frame(main)
                slider_frame.pack(fill=tk.X, pady=(0, 10), padx=(40, 0))
                
                tk.Label(slider_frame, text="Delay:", width=8, font=("Arial", 8)).pack(side=tk.LEFT)
                
                delay_var = tk.IntVar(value=config["delay"])
                self.delay_var = delay_var
                self.delay_label = tk.Label(slider_frame, text=f"{delay_var.get()}ms", width=5, font=("Arial", 8))
                
                tk.Scale(slider_frame, from_=config["delay_min"], to=config["delay_max"], 
                        orient="horizontal", variable=delay_var, length=150,
                        command=lambda val: self.python_macros[i].set_delay(int(val)),
                        showvalue=False).pack(side=tk.LEFT, padx=5)
                
                self.delay_label.pack(side=tk.LEFT)
            
            self.macro_statuses[i] = ""
        
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.update_buttons()
    
    def exit_app(self):
        print("🛑 Closing application...")
        
        # Create exit signal file for AHK
        try:
            with open(EXIT_SIGNAL, 'w') as f:
                f.write("exit")
            print(f"✅ Exit signal sent: {EXIT_SIGNAL}")
        except Exception as e:
            print(f"⚠️ Could not create exit signal: {e}")
        
        # Clean up PID file
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
                print(f"✅ PID file cleaned up: {self.pid_file}")
        except Exception as e:
            print(f"⚠️ Could not remove PID file: {e}")
        
        time.sleep(0.3)
        
        for macro, enabled in zip(self.python_macros, self.python_macro_states):
            if macro and enabled:
                macro.stop()
        
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    MATEWmacro().root.mainloop()