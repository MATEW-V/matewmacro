import mss
import numpy as np
import cv2
import time
import threading
import tkinter as tk
import keyboard

# ========== CONFIGURATION ==========
TARGET_BLUES_RGB = [
    [34, 43, 92], [17, 35, 81], [25, 50, 106],
    [10, 41, 95], [23, 42, 98], [34, 44, 102],
    [25, 46, 96], [18, 42, 93], [27, 60, 122],
]
TARGET_BLUES_BGR = np.array([[b, g, r] for r, g, b in TARGET_BLUES_RGB])

# Combat Verification Points
COMBAT_POINTS = [(960, 89), (964, 85), (975, 75)]
COMBAT_COLORS_RGB = [[202, 98, 98], [195, 92, 92], [195, 92, 92]]
COMBAT_COLORS_BGR = [[b, g, r] for r, g, b in COMBAT_COLORS_RGB]
COMBAT_TOLERANCE = 20

# Detection settings
PADDING = 5
MIN_GROUP = 600
MAX_GROUP = 2000
SCAN_REGION = {'left': 720, 'top': 320, 'width': 470, 'height': 400}
COOLDOWN = 1.0
FPS = 30
# ===================================

class TintDetector:
    def __init__(self):
        self.running = False
        self.detection_count = 0
        self.last_action = 0
        self.min_threshold = MIN_GROUP
        self.max_threshold = MAX_GROUP
        self.padding = PADDING
        self.in_combat = False
        self.update_color_range()
        
        self.setup_gui()
        
        threading.Thread(target=self.detection_loop, daemon=True).start()
        threading.Thread(target=self.cooldown_update_loop, daemon=True).start()
        
        print(f"\nTint Detector Ready | Min: {MIN_GROUP}px | Max: {MAX_GROUP}px | Padding: ±{PADDING}")
        print(f"Combat Points: {len(COMBAT_POINTS)} | Tolerance: ±{COMBAT_TOLERANCE}")
    
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Tint Detector")
        self.root.geometry("320x340")
        self.root.attributes('-topmost', True)
        
        self.button = tk.Button(self.root, text="OFF", command=self.toggle,
                                bg="red", fg="white", font=("Arial", 18, "bold"), width=8)
        self.button.pack(pady=10)
        
        self.status_label = tk.Label(self.root, text="Status: STOPPED", fg="red")
        self.status_label.pack()
        
        self.combat_label = tk.Label(self.root, text="⚔️ COMBAT: OUT", fg="gray", font=("Arial", 10, "bold"))
        self.combat_label.pack(pady=5)
        
        self.count_label = tk.Label(self.root, text="Detections: 0")
        self.count_label.pack(pady=5)
        
        # Min slider
        f = tk.Frame(self.root)
        f.pack(pady=5)
        tk.Label(f, text="Min Group Size:").pack(side=tk.LEFT)
        self.min_slider = tk.Scale(f, from_=200, to=2500, orient=tk.HORIZONTAL, length=200, command=self.update_min)
        self.min_slider.set(self.min_threshold)
        self.min_slider.pack(side=tk.LEFT, padx=5)
        self.min_label = tk.Label(f, text=f"{self.min_threshold}px", width=8)
        self.min_label.pack(side=tk.LEFT)
        
        # Max display (read-only)
        f = tk.Frame(self.root)
        f.pack(pady=5)
        tk.Label(f, text="Max Group Size:").pack(side=tk.LEFT)
        tk.Label(f, text=f"{self.max_threshold}px", font=("Arial", 9, "bold"), fg="blue").pack(side=tk.LEFT, padx=5)
        tk.Label(f, text="(fixed)").pack(side=tk.LEFT)
        
        # Padding slider
        f = tk.Frame(self.root)
        f.pack(pady=5)
        tk.Label(f, text="Color Padding:").pack(side=tk.LEFT)
        self.pad_slider = tk.Scale(f, from_=5, to=15, orient=tk.HORIZONTAL, length=200, command=self.update_padding)
        self.pad_slider.set(self.padding)
        self.pad_slider.pack(side=tk.LEFT, padx=5)
        self.pad_label = tk.Label(f, text=str(self.padding), width=3)
        self.pad_label.pack(side=tk.LEFT)
        
        self.cooldown_label = tk.Label(self.root, text="Cooldown: Ready", fg="green")
        self.cooldown_label.pack(pady=5)
        self.last_label = tk.Label(self.root, text="Last: --", fg="gray")
        self.last_label.pack()
        self.current_label = tk.Label(self.root, text="Current Group: 0px", fg="blue")
        self.current_label.pack(pady=2)
        tk.Label(self.root, text="Action: Presses 'F' key", fg="blue").pack(pady=5)
    
    def update_color_range(self):
        self.LOWER_RANGE = np.clip(np.min(TARGET_BLUES_BGR, axis=0) - self.padding, 0, 255)
        self.UPPER_RANGE = np.clip(np.max(TARGET_BLUES_BGR, axis=0) + self.padding, 0, 255)
    
    def update_min(self, v):
        self.min_threshold = int(v)
        self.min_label.config(text=f"{self.min_threshold}px")
    
    def update_padding(self, v):
        self.padding = int(v)
        self.pad_label.config(text=str(self.padding))
        self.update_color_range()
    
    def check_combat_status(self, sct):
        for point, target in zip(COMBAT_POINTS, COMBAT_COLORS_BGR):
            region = {'left': point[0], 'top': point[1], 'width': 1, 'height': 1}
            pixel = np.array(sct.grab(region))[0, 0, :3]
            if not np.all(np.abs(pixel - target) <= COMBAT_TOLERANCE):
                return False
        return True
    
    def toggle(self):
        self.running = not self.running
        self.button.config(text="ON" if self.running else "OFF", bg="green" if self.running else "red")
        self.status_label.config(text=f"Status: {'RUNNING' if self.running else 'STOPPED'}", 
                                fg="green" if self.running else "red")
        print(f"{'✓ ACTIVE' if self.running else '✓ STOPPED'}")
    
    def press_f(self):
        keyboard.press('f')
        keyboard.release('f')
        print("  ⌨️ Pressed 'F'")
    
    def cooldown_update_loop(self):
        while True:
            if self.running:
                remaining = max(0, self.last_action + COOLDOWN - time.time())
                self.cooldown_label.config(
                    text=f"Cooldown: {remaining:.1f}s" if remaining > 0 else "Cooldown: Ready",
                    fg="red" if remaining > 0 else "green")
            else:
                self.cooldown_label.config(text="Cooldown: --", fg="gray")
            time.sleep(0.1)
    
    def detection_loop(self):
        with mss.mss() as sct:
            while True:
                if self.running:
                    in_combat = self.check_combat_status(sct)
                    
                    if in_combat != self.in_combat:
                        self.in_combat = in_combat
                        self.combat_label.config(text="⚔️ COMBAT: IN" if in_combat else "⚔️ COMBAT: OUT", 
                                                fg="red" if in_combat else "gray")
                        if in_combat:
                            print("⚔️ COMBAT DETECTED")
                    
                    if in_combat:
                        frame = cv2.cvtColor(np.array(sct.grab(SCAN_REGION)), cv2.COLOR_BGRA2BGR)
                        mask = cv2.inRange(frame, self.LOWER_RANGE, self.UPPER_RANGE)
                        
                        largest = 0
                        _, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)
                        for i in range(1, len(stats)):
                            largest = max(largest, stats[i, cv2.CC_STAT_AREA])
                        
                        self.current_label.config(text=f"Current Group: {largest}px")
                        
                        if self.min_threshold <= largest <= self.max_threshold and time.time() - self.last_action >= COOLDOWN:
                            self.detection_count += 1
                            self.press_f()
                            self.count_label.config(text=f"Detections: {self.detection_count}")
                            self.last_label.config(text=f"Last: {time.strftime('%H:%M:%S')} | Group: {largest}px")
                            print(f"\n✅ #{self.detection_count} | Group: {largest}px")
                            self.last_action = time.time()
                    else:
                        self.current_label.config(text="Current Group: -- (Out of Combat)")
                
                time.sleep(1.0 / FPS)
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, 'running', False), time.sleep(0.2), self.root.destroy()))
        self.root.mainloop()

if __name__ == "__main__":
    TintDetector().run()