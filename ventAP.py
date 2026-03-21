import mss
import numpy as np
import cv2
import time
import threading
import tkinter as tk
import os
from datetime import datetime
import keyboard

# ========== CONFIGURATION ==========
TARGET_BLUES_RGB = [
    [34, 43, 92], [17, 35, 81], [25, 50, 106],
    [10, 41, 95], [23, 42, 98], [34, 44, 102],
    [25, 46, 96], [18, 42, 93], [27, 60, 122],
]

TARGET_BLUES_BGR = np.array([[b, g, r] for r, g, b in TARGET_BLUES_RGB])

# Settings
PADDING = 5
GROUP_THRESHOLD = 600
SCAN_REGION = {'left': 720, 'top': 320, 'width': 470, 'height': 400}
COOLDOWN = 3.0  # 3 seconds between actions
FPS = 30
# ===================================

# Calculate color range
LOWER_RANGE = np.clip(np.min(TARGET_BLUES_BGR, axis=0) - PADDING, 0, 255)
UPPER_RANGE = np.clip(np.max(TARGET_BLUES_BGR, axis=0) + PADDING, 0, 255)

class TintDetector:
    def __init__(self):
        self.running = False
        self.detection_count = 0
        self.last_action = 0
        
        # Create folder
        self.session_folder = f"detections_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.session_folder, exist_ok=True)
        
        # Setup GUI
        self.root = tk.Tk()
        self.root.title("Tint Detector")
        self.root.geometry("300x220")
        self.root.attributes('-topmost', True)
        
        # ON/OFF Button
        self.button = tk.Button(self.root, text="OFF", command=self.toggle,
                                bg="red", fg="white", font=("Arial", 18, "bold"),
                                width=8, height=1)
        self.button.pack(pady=10)
        
        # Status
        self.status_label = tk.Label(self.root, text="Status: STOPPED", fg="red")
        self.status_label.pack()
        
        # Count
        self.count_label = tk.Label(self.root, text="Detections: 0", font=("Arial", 10))
        self.count_label.pack(pady=5)
        
        # Cooldown display
        self.cooldown_label = tk.Label(self.root, text="Cooldown: Ready", font=("Arial", 8), fg="green")
        self.cooldown_label.pack()
        
        # Last detection
        self.last_label = tk.Label(self.root, text="Last: --", font=("Arial", 8), fg="gray")
        self.last_label.pack()
        
        # Action label
        self.action_label = tk.Label(self.root, text="Action: Presses 'F'", font=("Arial", 8), fg="blue")
        self.action_label.pack(pady=5)
        
        # Start thread
        self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.detection_thread.start()
        
        # Cooldown update thread
        self.cooldown_thread = threading.Thread(target=self.cooldown_update_loop, daemon=True)
        self.cooldown_thread.start()
        
        print(f"\nTint Detector Ready")
        print(f"Threshold: {GROUP_THRESHOLD}px | Cooldown: {COOLDOWN}s | FPS: {FPS}")
        print(f"Action: Presses 'F' key when tint detected")
        print(f"Saving to: {self.session_folder}/\n")
    
    def toggle(self):
        self.running = not self.running
        if self.running:
            self.button.config(text="ON", bg="green")
            self.status_label.config(text="Status: RUNNING", fg="green")
            print("✓ ACTIVE - Will press 'F' when tint detected")
        else:
            self.button.config(text="OFF", bg="red")
            self.status_label.config(text="Status: STOPPED", fg="red")
            print(f"✓ STOPPED - {self.detection_count} actions performed")
    
    def press_f_key(self):
        """Press the F key"""
        keyboard.press('f')
        keyboard.release('f')
        print("  ⌨️ Pressed 'F' key")
    
    def cooldown_update_loop(self):
        """Update cooldown display"""
        while True:
            if self.running:
                remaining = max(0, self.last_action + COOLDOWN - time.time())
                if remaining > 0:
                    self.cooldown_label.config(text=f"Cooldown: {remaining:.1f}s", fg="red")
                else:
                    self.cooldown_label.config(text="Cooldown: Ready", fg="green")
            else:
                self.cooldown_label.config(text="Cooldown: --", fg="gray")
            time.sleep(0.1)
    
    def detection_loop(self):
        with mss.mss() as sct:
            while True:
                if self.running:
                    # Capture
                    img = sct.grab(SCAN_REGION)
                    frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
                    
                    # Detect blue
                    mask = cv2.inRange(frame, LOWER_RANGE, UPPER_RANGE)
                    blue_pixels = np.count_nonzero(mask)
                    
                    # Find largest group
                    largest_group = 0
                    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8, cv2.CV_32S)
                    for i in range(1, num_labels):
                        size = stats[i, cv2.CC_STAT_AREA]
                        if size > largest_group:
                            largest_group = size
                    
                    # Trigger with cooldown
                    if largest_group >= GROUP_THRESHOLD:
                        if time.time() - self.last_action >= COOLDOWN:
                            self.detection_count += 1
                            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
                            filename = f"{self.session_folder}/detect_{self.detection_count:04d}_{timestamp}.png"
                            cv2.imwrite(filename, frame)
                            
                            # PRESS THE F KEY!
                            self.press_f_key()
                            
                            # Update GUI
                            self.count_label.config(text=f"Detections: {self.detection_count}")
                            self.last_label.config(text=f"Last: {timestamp[:8]} | Group: {largest_group}px")
                            
                            print(f"\n✅ #{self.detection_count} | Group: {largest_group}px | Blue: {blue_pixels}px")
                            
                            self.last_action = time.time()
                
                time.sleep(1.0 / FPS)
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def on_close(self):
        self.running = False
        time.sleep(0.2)
        self.root.destroy()
        print(f"\nStopped | {self.detection_count} actions performed")
        print(f"Saved to: {self.session_folder}/")

if __name__ == "__main__":
    detector = TintDetector()
    detector.run()