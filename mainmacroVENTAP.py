import tkinter as tk
import os
import subprocess
import time
import cv2
import numpy as np
import mss
import keyboard
import mouse
import threading
import sys
import shutil
import tkinter.messagebox as mb

# ============ CONFIGURATION ============
def get_paths():
    """Get internal and external paths for both script and compiled exe"""
    if getattr(sys, 'frozen', False):
        internal = sys._MEIPASS
        external = os.path.dirname(sys.executable)
    else:
        internal = external = os.path.dirname(os.path.abspath(__file__))
    return internal, external

INTERNAL_PATH, EXTERNAL_PATH = get_paths()

# Path definitions
TEMPLATE_FOLDER = os.path.join(INTERNAL_PATH, "letter_templates")
AHK_SCRIPT_SOURCE = os.path.join(INTERNAL_PATH, "macros.ahk")
STATE_FILE = os.path.join(EXTERNAL_PATH, "state.txt")
PID_FILE = os.path.join(EXTERNAL_PATH, "python_pid.txt")
EXIT_SIGNAL = os.path.join(EXTERNAL_PATH, "exit_signal.txt")
AHK_SCRIPT_DEST = os.path.join(EXTERNAL_PATH, "macros.ahk")

# Screen regions
SLOT1_LOCATION = {'left': 860, 'top': 200, 'width': 50, 'height': 100}
TINT_SCAN_REGION = {'left': 830, 'top': 350, 'width': 250, 'height': 250}

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

TINT_PADDING = 10
TINT_MIN_GROUP = 300
TINT_MAX_GROUP = 1800
TINT_COOLDOWN = 1.0
TINT_FPS = 30
MERGE_DISTANCE = 5  # Fixed merge distance

MACROS = [
    {"name": "Dodge Cancel", "hotkey": "Q", "desc": "Q → delay → right click", "type": "ahk"},
    {"name": "b mbutton -> 9", "hotkey": "XButton1", "desc": "Mouse back → 9", "type": "ahk"},
    {"name": "f mbutton -> 8", "hotkey": "XButton2", "desc": "Mouse forward → 8", "type": "ahk"},
    {"name": "Roll Parry", "hotkey": "CTRL+F", "desc": "hold ctrl and m1 after for insta uppercut", "type": "ahk"},
    {"name": "Ritual Cast", "hotkey": "", "desc": "Automatic Ritual Caster", "type": "python"},
    {"name": "Vent Predict", "hotkey": "", "desc": "Computer Vision Vent Reader", "type": "tint"},
]

if not os.path.exists(TEMPLATE_FOLDER):
    mb.showerror("Error", f"Templates folder not found!\n\n{TEMPLATE_FOLDER}")
    sys.exit(1)


class BaseMacro:
    """Base class for all macros"""
    def __init__(self, parent, status_callback=None):
        self.parent = parent
        self.running = False
        self.status_callback = status_callback
        self.thread = None
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            return True
        return False
    
    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
    
    def run(self):
        """Override in child classes"""
        pass
    
    def update_status(self, message):
        if self.status_callback:
            self.status_callback(message)


class TintDetectorMacro(BaseMacro):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent, status_callback)
        self.last_action = 0
        self.in_combat = False
        self.require_combat = True
        self.cooldown = TINT_COOLDOWN
    
    def check_combat_status(self, sct):
        for point, target in zip(COMBAT_POINTS, COMBAT_COLORS_BGR):
            region = {'left': point[0], 'top': point[1], 'width': 1, 'height': 1}
            pixel = np.array(sct.grab(region))[0, 0, :3]
            if not np.all(np.abs(pixel - target) <= COMBAT_TOLERANCE):
                return False
        return True
    
    def find_similar_color_groups(self, frame):
        """Group pixels by color similarity instead of exact color match"""
        mask = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
        
        for target_color in TARGET_BLUES_BGR:
            diff = frame.astype(np.float32) - target_color.astype(np.float32)
            distance = np.sqrt(np.sum(diff ** 2, axis=2))
            mask[distance <= TINT_PADDING] = 255
        
        return mask
    
    def merge_nearby_groups(self, stats):
        """Merge groups that are close to each other"""
        num_groups = len(stats)
        if num_groups <= 1:
            return [], []
        
        groups = []
        for i in range(1, num_groups):
            groups.append({
                'index': i,
                'center': (stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH] // 2,
                          stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] // 2),
                'area': stats[i, cv2.CC_STAT_AREA],
                'x': stats[i, cv2.CC_STAT_LEFT],
                'y': stats[i, cv2.CC_STAT_TOP],
                'w': stats[i, cv2.CC_STAT_WIDTH],
                'h': stats[i, cv2.CC_STAT_HEIGHT]
            })
        
        merged_groups = []
        used = set()
        
        for i, group in enumerate(groups):
            if i in used:
                continue
            
            merged = {
                'areas': [group['area']],
                'total_area': group['area'],
                'min_x': group['x'],
                'min_y': group['y'],
                'max_x': group['x'] + group['w'],
                'max_y': group['y'] + group['h'],
                'groups': [group]
            }
            used.add(i)
            
            changed = True
            while changed:
                changed = False
                for j, other in enumerate(groups):
                    if j in used:
                        continue
                    
                    for g in merged['groups']:
                        dist = np.sqrt((g['center'][0] - other['center'][0])**2 + 
                                     (g['center'][1] - other['center'][1])**2)
                        if dist <= MERGE_DISTANCE:
                            merged['areas'].append(other['area'])
                            merged['total_area'] += other['area']
                            merged['min_x'] = min(merged['min_x'], other['x'])
                            merged['min_y'] = min(merged['min_y'], other['y'])
                            merged['max_x'] = max(merged['max_x'], other['x'] + other['w'])
                            merged['max_y'] = max(merged['max_y'], other['y'] + other['h'])
                            merged['groups'].append(other)
                            used.add(j)
                            changed = True
                            break
            
            merged_groups.append(merged)
        
        return merged_groups, groups
    
    def press_sequence(self):
        """Execute right-click then F key sequence"""
        mouse.press("right")
        time.sleep(0.01)
        mouse.release("right")
        time.sleep(0.01)
        keyboard.press('f')
        time.sleep(0.01)
        keyboard.release('f')
    
    def run(self):
        with mss.mss() as sct:
            while self.running:
                if self.parent.game_active:
                    in_combat = self.check_combat_status(sct)
                    
                    if in_combat != self.in_combat:
                        self.in_combat = in_combat
                        combat_status = "⚔️ IN COMBAT" if in_combat else "🛡️ Out of combat"
                        if not self.require_combat:
                            combat_status += " (Ignored)"
                        self.update_status(combat_status)
                    
                    should_process = not self.require_combat or in_combat
                    
                    if should_process:
                        full_screen = np.array(sct.grab(sct.monitors[1]))
                        full_screen_rgb = cv2.cvtColor(full_screen[:, :, :3], cv2.COLOR_BGRA2BGR)
                        
                        region_frame = full_screen_rgb[
                            TINT_SCAN_REGION['top']:TINT_SCAN_REGION['top'] + TINT_SCAN_REGION['height'],
                            TINT_SCAN_REGION['left']:TINT_SCAN_REGION['left'] + TINT_SCAN_REGION['width']
                        ]
                        
                        mask = self.find_similar_color_groups(region_frame)
                        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)
                        merged_groups, _ = self.merge_nearby_groups(stats)
                        
                        # Check for detection trigger
                        detection_triggered = any(
                            TINT_MIN_GROUP <= g['total_area'] <= TINT_MAX_GROUP 
                            for g in merged_groups
                        )
                        
                        if detection_triggered and time.time() - self.last_action >= self.cooldown:
                            self.press_sequence()
                            self.last_action = time.time()
                
                time.sleep(1.0 / TINT_FPS)
    
    def set_require_combat(self, value):
        self.require_combat = value
        return self.require_combat


class LetterMacro(BaseMacro):
    def __init__(self, parent, status_callback=None):
        super().__init__(parent, status_callback)
        self.region = SLOT1_LOCATION
        self.templates = []
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
            gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
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
    
    def run(self):
        with mss.mss() as sct:
            while self.running:
                if self.parent.game_active:
                    img = np.array(sct.grab(self.region))
                    letter = self.detect_in_region(img)
                    if letter:
                        keyboard.press_and_release(letter.lower())
                        time.sleep(self.KEY_DELAY)
                time.sleep(self.FAST_POLL)


class MATEWmacro:
    def __init__(self):
        self.game_active = False
        self.macro_configs = MACROS
        self.python_macros = [None] * len(self.macro_configs)
        self.python_macro_states = [False] * len(self.macro_configs)
        self.macro_statuses = {}
        
        # Initialize files
        self.init_files()
        
        # Start AHK scripts if available
        self.start_ahk_scripts()
        
        # Initialize macros
        self.init_macros()
        
        # Setup GUI
        self.setup_gui()
        
        # Start background threads
        threading.Thread(target=self.monitor_roblox, daemon=True).start()
        threading.Thread(target=self.update_combat_indicators, daemon=True).start()
    
    def init_files(self):
        """Initialize state and PID files"""
        if not os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'w') as f:
                f.write(",".join(["0"] * len(self.macro_configs)))
        
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    
    def start_ahk_scripts(self):
        """Start AHK scripts if available"""
        if os.path.exists(AHK_SCRIPT_SOURCE):
            if not os.path.exists(AHK_SCRIPT_DEST):
                shutil.copy2(AHK_SCRIPT_SOURCE, AHK_SCRIPT_DEST)
            if os.path.exists(AHK_SCRIPT_DEST):
                subprocess.Popen([AHK_SCRIPT_DEST], shell=True)
    
    def init_macros(self):
        """Initialize Python-based macros"""
        for i, config in enumerate(self.macro_configs):
            macro_type = config.get("type")
            if macro_type == "python":
                self.python_macros[i] = LetterMacro(self, 
                    lambda msg, idx=i: self.update_macro_status(idx, msg))
            elif macro_type == "tint":
                self.python_macros[i] = TintDetectorMacro(self, 
                    lambda msg, idx=i: self.update_macro_status(idx, msg))
    
    def update_macro_status(self, index, message):
        self.macro_statuses[index] = message
        self.root.after(0, self.update_buttons)
    
    def monitor_roblox(self):
        """Monitor if Roblox is active"""
        try:
            import pywinctl as pwc
            while True:
                active = pwc.getActiveWindow()
                self.game_active = active and "roblox" in active.title.lower()
                time.sleep(0.5)
        except:
            self.game_active = True
    
    def read_states(self):
        """Read macro states from file"""
        try:
            with open(STATE_FILE, 'r') as f:
                return [x == "1" for x in f.read().strip().split(",")]
        except:
            return [False] * len(self.macro_configs)
    
    def write_states(self, states):
        """Write macro states to file"""
        with open(STATE_FILE, 'w') as f:
            f.write(",".join(["1" if s else "0" for s in states]))
    
    def toggle_macro(self, index):
        """Toggle macro on/off"""
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
    
    def toggle_combat_requirement(self, index):
        """Toggle combat requirement for tint detector"""
        macro = self.python_macros[index]
        if macro and hasattr(macro, 'set_require_combat'):
            new_state = not macro.require_combat
            macro.set_require_combat(new_state)
            
            if index in self.combat_toggle_buttons:
                self.combat_toggle_buttons[index].config(
                    text="✅ Combat Only" if new_state else "🌍 Always On",
                    bg="green" if new_state else "orange"
                )
            self.update_macro_status(index, f"Mode: {'Combat Only' if new_state else 'Always On'}")
    
    def update_buttons(self):
        """Update GUI button states"""
        states = self.read_states()
        for i, btn in enumerate(self.buttons):
            config = self.macro_configs[i]
            is_on = states[i]
            status = self.macro_statuses.get(i, "")
            text = f"{config['name']}: {status[-25:]}" if is_on and status else f"{config['name']}: {'ON' if is_on else 'OFF'}"
            btn.config(text=text, bg="green" if is_on else "lightgray", fg="white" if is_on else "black")
        
        self.status_label.config(
            text=f"Roblox: {'ACTIVE' if self.game_active else 'INACTIVE'}",
            fg="green" if self.game_active else "red"
        )
        self.root.after(500, self.update_buttons)
    
    def update_combat_indicators(self):
        """Update combat indicator UI elements"""
        while True:
            for i, config in enumerate(self.macro_configs):
                if config.get("type") == "tint" and i in self.combat_indicators:
                    macro = self.python_macros[i]
                    if macro:
                        in_combat = getattr(macro, 'in_combat', False)
                        require_combat = getattr(macro, 'require_combat', True)
                        
                        if require_combat:
                            text, color = ("[IN COMBAT]" if in_combat else "[OUT]", 
                                         "red" if in_combat else "gray")
                        else:
                            text, color = ("[ALWAYS ON]", "orange")
                        
                        self.combat_indicators[i].config(text=text, fg=color)
            time.sleep(0.2)
    
    def setup_gui(self):
        """Setup the main GUI window"""
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)
        self.root.title("MATEW MACRO")
        self.root.geometry(f"650x{100 + len(self.macro_configs) * 45}")
        
        main = tk.Frame(self.root, padx=20, pady=20)
        main.pack()
        
        # Status label
        self.status_label = tk.Label(main, text="Roblox: INACTIVE", font=("Arial", 10, "bold"), fg="red")
        self.status_label.pack(pady=(0, 10))
        
        # Buttons and controls
        self.buttons = []
        self.combat_indicators = {}
        self.combat_toggle_buttons = {}
        
        for i, config in enumerate(self.macro_configs):
            frame = tk.Frame(main)
            frame.pack(fill=tk.X, pady=3)
            
            # Hotkey label
            hotkey = f"[{config['hotkey']}]" if config['hotkey'] else "    "
            tk.Label(frame, text=hotkey, width=8, fg="blue", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            
            # Toggle button
            btn = tk.Button(frame, text=f"{config['name']}: OFF", 
                          command=lambda idx=i: self.toggle_macro(idx), 
                          width=20, bg="lightgray")
            btn.pack(side=tk.LEFT, padx=5)
            self.buttons.append(btn)
            
            # Description
            tk.Label(frame, text=config["desc"], fg="gray", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
            
            # Additional controls for specific macro types
            self.add_macro_controls(i, config)
            
            self.macro_statuses[i] = ""
        
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)
        self.update_buttons()
    
    def add_macro_controls(self, index, config):
        """Add macro-specific controls"""
        macro_type = config.get("type")
        
        if macro_type == "tint":
            # Create a single row frame for tint controls
            controls_frame = tk.Frame(self.root)
            controls_frame.pack(fill=tk.X, pady=(0, 5), padx=(40, 0))
            
            # Combat indicator and toggle only
            combat_frame = tk.Frame(controls_frame)
            combat_frame.pack(side=tk.LEFT)
            
            combat_indicator = tk.Label(combat_frame, text="[OUT]", fg="gray", font=("Arial", 8, "bold"))
            combat_indicator.pack(side=tk.LEFT, padx=2)
            self.combat_indicators[index] = combat_indicator
            
            combat_toggle = tk.Button(combat_frame, text="✅ Combat Only", 
                                    command=lambda idx=index: self.toggle_combat_requirement(idx),
                                    bg="green", fg="white", font=("Arial", 7), 
                                    width=12, height=1)
            combat_toggle.pack(side=tk.LEFT, padx=2)
            self.combat_toggle_buttons[index] = combat_toggle
    
    def exit_app(self):
        """Clean up and exit"""
        with open(EXIT_SIGNAL, 'w') as f:
            f.write("exit")
        
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        
        time.sleep(0.3)
        
        for macro, enabled in zip(self.python_macros, self.python_macro_states):
            if macro and enabled:
                macro.stop()
        
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    MATEWmacro().root.mainloop()