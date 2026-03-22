import tkinter as tk
import os
import subprocess
import time
import cv2
import numpy as np
import mss
import keyboard
import threading
import sys
import shutil
import tkinter.messagebox as mb

# ============ CONFIGURATION ============
# Get correct path for both script and compiled exe
if getattr(sys, 'frozen', False):
    INTERNAL_PATH = sys._MEIPASS
    EXTERNAL_PATH = os.path.dirname(sys.executable)
else:
    INTERNAL_PATH = os.path.dirname(os.path.abspath(__file__))
    EXTERNAL_PATH = INTERNAL_PATH

# Internal paths
TEMPLATE_FOLDER = os.path.join(INTERNAL_PATH, "letter_templates")
AHK_SCRIPT_SOURCE = os.path.join(INTERNAL_PATH, "macros.ahk")

# External paths
STATE_FILE = os.path.join(EXTERNAL_PATH, "state.txt")
PID_FILE = os.path.join(EXTERNAL_PATH, "python_pid.txt")
EXIT_SIGNAL = os.path.join(EXTERNAL_PATH, "exit_signal.txt")
AHK_SCRIPT_DEST = os.path.join(EXTERNAL_PATH, "macros.ahk")

SLOT1_LOCATION = {'left': 860, 'top': 200, 'width': 50, 'height': 100}

# Tint Detection Settings
TARGET_BLUES_RGB = [
    [34, 43, 92], [17, 35, 81], [25, 50, 106],
    [10, 41, 95], [23, 42, 98], [34, 44, 102],
    [25, 46, 96], [18, 42, 93], [27, 60, 122],
]
TARGET_BLUES_BGR = np.array([[b, g, r] for r, g, b in TARGET_BLUES_RGB])

COMBAT_POINTS = [(960, 89), (964, 85), (975, 75)]
COMBAT_COLORS_BGR = [[98, 98, 202], [92, 92, 195], [92, 92, 195]]
COMBAT_TOLERANCE = 20

TINT_PADDING = 5
TINT_MIN_GROUP = 600
TINT_MAX_GROUP = 2000
TINT_SCAN_REGION = {'left': 720, 'top': 320, 'width': 470, 'height': 400}
TINT_COOLDOWN = 1.0
TINT_FPS = 30

MACROS = [
    {"name": "Dodge Cancel", "hotkey": "Q", "desc": "Q → delay → right click", "type": "ahk"},
    {"name": "b mbutton -> 9", "hotkey": "XButton1", "desc": "Mouse back → 9", "type": "ahk"},
    {"name": "f mbutton -> 8", "hotkey": "XButton2", "desc": "Mouse forward → 8", "type": "ahk"},
    {"name": "Roll Parry", "hotkey": "CTRL+F", "desc": "hold ctrl and m1 after for insta uppercut", "type": "ahk"},
    {"name": "Ritual Cast", "hotkey": "", "desc": "automatic ritual caster", "type": "python", 
     "delay": 100, "delay_min": 100, "delay_max": 200},
    {"name": "Tint Detector", "hotkey": "", "desc": "Right click → F when tint detected", "type": "tint",
     "min_group": 600, "padding": 5},
]

# Check if templates exist
if not os.path.exists(TEMPLATE_FOLDER):
    mb.showerror("Error", f"Templates folder not found!\n\n{TEMPLATE_FOLDER}")
    sys.exit(1)

class TintDetectorMacro:
    def __init__(self, parent, status_callback=None):
        self.parent = parent
        self.running = False
        self.detection_count = 0
        self.last_action = 0
        self.min_threshold = TINT_MIN_GROUP
        self.max_threshold = TINT_MAX_GROUP
        self.padding = TINT_PADDING
        self.cooldown = TINT_COOLDOWN
        self.in_combat = False
        self.status_callback = status_callback
        self.thread = None
        self.update_color_range()
    
    def update_color_range(self):
        self.LOWER_RANGE = np.clip(np.min(TARGET_BLUES_BGR, axis=0) - self.padding, 0, 255)
        self.UPPER_RANGE = np.clip(np.max(TARGET_BLUES_BGR, axis=0) + self.padding, 0, 255)
    
    def check_combat_status(self, sct):
        for point, target in zip(COMBAT_POINTS, COMBAT_COLORS_BGR):
            region = {'left': point[0], 'top': point[1], 'width': 1, 'height': 1}
            pixel = np.array(sct.grab(region))[0, 0, :3]
            if not np.all(np.abs(pixel - target) <= COMBAT_TOLERANCE):
                return False
        return True
    
    def press_sequence(self):
        keyboard.press('right')
        keyboard.release('right')
        time.sleep(0.1)
        keyboard.press('f')
        keyboard.release('f')
    
    def detection_loop(self):
        with mss.mss() as sct:
            while self.running:
                if self.parent.game_active:
                    in_combat = self.check_combat_status(sct)
                    
                    if in_combat != self.in_combat:
                        self.in_combat = in_combat
                        if self.status_callback:
                            self.status_callback("⚔️ IN COMBAT" if in_combat else "🛡️ Out of combat")
                    
                    if in_combat:
                        frame = cv2.cvtColor(np.array(sct.grab(TINT_SCAN_REGION)), cv2.COLOR_BGRA2BGR)
                        mask = cv2.inRange(frame, self.LOWER_RANGE, self.UPPER_RANGE)
                        
                        largest = 0
                        _, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)
                        for i in range(1, len(stats)):
                            largest = max(largest, stats[i, cv2.CC_STAT_AREA])
                        
                        if self.min_threshold <= largest <= self.max_threshold and time.time() - self.last_action >= self.cooldown:
                            self.detection_count += 1
                            self.press_sequence()
                            self.last_action = time.time()
                            if self.status_callback:
                                self.status_callback(f"✅ #{self.detection_count}")
                
                time.sleep(1.0 / TINT_FPS)
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.thread.start()
            return True
        return False
    
    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
    
    def set_min_group(self, value):
        self.min_threshold = int(value)
    
    def set_padding(self, value):
        self.padding = int(value)
        self.update_color_range()

class LetterMacro:
    def __init__(self, parent, status_callback=None):
        self.enabled = False
        self.region = SLOT1_LOCATION
        self.templates = []
        self.status_callback = status_callback
        self.parent = parent
        self.thread = None
        self.DETECTION_THRESHOLD = 0.85
        self.MIN_BRIGHTNESS = 10
        self.FAST_POLL = 0.05
        self.KEY_DELAY = 0.10
        self.load_templates()
        
    def load_templates(self):
        self.templates = []
        for f in os.listdir(TEMPLATE_FOLDER):
            if not f.lower().endswith('.png'):
                continue
            letter = f[1].upper() if f.startswith('p') else f[0].upper()
            img = cv2.imread(os.path.join(TEMPLATE_FOLDER, f), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self.templates.append((letter, img))
        
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
        except:
            return None
        
    def macro_loop(self):
        type_count = 0
        with mss.mss() as sct:
            while self.enabled:
                if self.parent.game_active:
                    img = np.array(sct.grab(self.region))
                    letter = self.detect_in_region(img)
                    if letter:
                        keyboard.press_and_release(letter.lower())
                        type_count += 1
                        time.sleep(self.KEY_DELAY)
                time.sleep(self.FAST_POLL)
        
    def start(self):
        if not self.enabled:
            self.enabled = True
            self.thread = threading.Thread(target=self.macro_loop, daemon=True)
            self.thread.start()
            return True
        return False
        
    def stop(self):
        self.enabled = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
    def set_delay(self, ms):
        self.KEY_DELAY = ms / 1000

class MATEWmacro:
    def __init__(self):
        self.state_file = STATE_FILE
        self.game_active = False
        self.macro_configs = MACROS
        self.pid_file = PID_FILE
        
        if not os.path.exists(self.state_file):
            with open(self.state_file, 'w') as f:
                f.write(",".join(["0"] * len(self.macro_configs)))
        
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        if os.path.exists(AHK_SCRIPT_SOURCE):
            if not os.path.exists(AHK_SCRIPT_DEST):
                shutil.copy2(AHK_SCRIPT_SOURCE, AHK_SCRIPT_DEST)
            if os.path.exists(AHK_SCRIPT_DEST):
                subprocess.Popen([AHK_SCRIPT_DEST], shell=True)
        
        self.python_macros = [None] * len(self.macro_configs)
        self.python_macro_states = [False] * len(self.macro_configs)
        
        for i, config in enumerate(self.macro_configs):
            if config.get("type") == "python":
                self.python_macros[i] = LetterMacro(self, lambda msg, idx=i: self.update_macro_status(idx, msg))
            elif config.get("type") == "tint":
                self.python_macros[i] = TintDetectorMacro(self, lambda msg, idx=i: self.update_macro_status(idx, msg))
        
        self.setup_gui()
        threading.Thread(target=self.monitor_roblox, daemon=True).start()
    
    def update_macro_status(self, index, message):
        self.macro_statuses[index] = message
        self.root.after(0, self.update_buttons)
    
    def monitor_roblox(self):
        try:
            import pywinctl as pwc
            while True:
                active = pwc.getActiveWindow()
                self.game_active = active and "roblox" in active.title.lower()
                time.sleep(0.5)
        except:
            self.game_active = True
    
    def read_states(self):
        try:
            with open(self.state_file, 'r') as f:
                return [x == "1" for x in f.read().strip().split(",")]
        except:
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
            text = f"{config['name']}: {self.macro_statuses[i][-25:]}" if is_on and i in self.macro_statuses else f"{config['name']}: {'ON' if is_on else 'OFF'}"
            btn.config(text=text, bg="green" if is_on else "lightgray", fg="white" if is_on else "black")
        
        self.status_label.config(text=f"Roblox: {'ACTIVE' if self.game_active else 'INACTIVE'}", fg="green" if self.game_active else "red")
        self.root.after(500, self.update_buttons)
    
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)
        self.root.title("MATEW MACRO")
        self.root.geometry(f"580x{100 + len(self.macro_configs) * 45}")
        
        main = tk.Frame(self.root, padx=20, pady=20)
        main.pack()
        
        self.status_label = tk.Label(main, text="Roblox: INACTIVE", font=("Arial", 10, "bold"), fg="red")
        self.status_label.pack(pady=(0, 10))
        
        self.buttons = []
        self.macro_statuses = {}
        self.combat_indicators = {}
        
        for i, config in enumerate(self.macro_configs):
            frame = tk.Frame(main)
            frame.pack(fill=tk.X, pady=3)
            
            hotkey = f"[{config['hotkey']}]" if config['hotkey'] else "    "
            tk.Label(frame, text=hotkey, width=8, fg="blue", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            
            btn = tk.Button(frame, text=f"{config['name']}: OFF", command=lambda idx=i: self.toggle_macro(idx), width=20, bg="lightgray")
            btn.pack(side=tk.LEFT, padx=5)
            self.buttons.append(btn)
            
            tk.Label(frame, text=config["desc"], fg="gray", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
            
            if config.get("type") == "tint":
                slider_frame = tk.Frame(main)
                slider_frame.pack(fill=tk.X, pady=(0, 5), padx=(40, 0))
                
                combat_indicator = tk.Label(slider_frame, text="[OUT]", fg="gray", font=("Arial", 8, "bold"))
                combat_indicator.pack(side=tk.LEFT, padx=5)
                self.combat_indicators[i] = combat_indicator
                
                min_var = tk.IntVar(value=config["min_group"])
                tk.Label(slider_frame, text="Min:", font=("Arial", 7)).pack(side=tk.LEFT, padx=(5,0))
                tk.Scale(slider_frame, from_=200, to=2500, orient="horizontal", variable=min_var, length=100,
                        command=lambda v, idx=i: self.python_macros[idx].set_min_group(v), showvalue=False).pack(side=tk.LEFT, padx=2)
                tk.Label(slider_frame, textvariable=min_var, width=4, font=("Arial", 7)).pack(side=tk.LEFT)
                
                tk.Label(slider_frame, text=f"Max:{TINT_MAX_GROUP}px", font=("Arial", 7), fg="blue").pack(side=tk.LEFT, padx=5)
                
                pad_var = tk.IntVar(value=config["padding"])
                tk.Label(slider_frame, text="Pad:", font=("Arial", 7)).pack(side=tk.LEFT, padx=(5,0))
                tk.Scale(slider_frame, from_=0, to=15, orient="horizontal", variable=pad_var, length=60,
                        command=lambda v, idx=i: self.python_macros[idx].set_padding(v), showvalue=False).pack(side=tk.LEFT, padx=2)
                tk.Label(slider_frame, textvariable=pad_var, width=2, font=("Arial", 7)).pack(side=tk.LEFT)
            
            elif config.get("type") == "python" and "delay" in config:
                slider_frame = tk.Frame(main)
                slider_frame.pack(fill=tk.X, pady=(0, 10), padx=(40, 0))
                
                tk.Label(slider_frame, text="Delay:", font=("Arial", 8)).pack(side=tk.LEFT)
                delay_var = tk.IntVar(value=config["delay"])
                delay_label = tk.Label(slider_frame, text=f"{delay_var.get()}ms", width=5, font=("Arial", 8))
                tk.Scale(slider_frame, from_=config["delay_min"], to=config["delay_max"], orient="horizontal", 
                        variable=delay_var, length=150, command=lambda v, idx=i: self.python_macros[idx].set_delay(int(v)), showvalue=False).pack(side=tk.LEFT, padx=5)
                delay_label.pack(side=tk.LEFT)
            
            self.macro_statuses[i] = ""
        
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.update_buttons()
        
        def update_combat_indicators():
            while True:
                for i, config in enumerate(self.macro_configs):
                    if config.get("type") == "tint" and i in self.combat_indicators and self.python_macros[i]:
                        in_combat = getattr(self.python_macros[i], 'in_combat', False)
                        self.combat_indicators[i].config(text="[IN COMBAT]" if in_combat else "[OUT]", fg="red" if in_combat else "gray")
                time.sleep(0.2)
        threading.Thread(target=update_combat_indicators, daemon=True).start()
    
    def exit_app(self):
        with open(EXIT_SIGNAL, 'w') as f:
            f.write("exit")
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
        time.sleep(0.3)
        for macro, enabled in zip(self.python_macros, self.python_macro_states):
            if macro and enabled:
                macro.stop()
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    MATEWmacro().root.mainloop()