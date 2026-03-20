# import os
# import cv2
# import numpy as np
# import mss
# import keyboard
# import time
# import tkinter as tk
# from tkinter import messagebox
# import threading
# from datetime import datetime

# # HARDCODED PATHS AND LOCATIONS
# TEMPLATE_FOLDER = r"c:\Users\Matthew V\Desktop\MATEWMACRO\util\ritualcast.exe_extracted\letter_templates"
# SLOT1_LOCATION = {'left': 860, 'top': 200, 'width': 50, 'height': 100}

# # Verify folder exists
# print("=" * 50)
# print("PATH DEBUG INFORMATION")
# print("=" * 50)
# print(f"Templates folder: {TEMPLATE_FOLDER}")
# print(f"Folder exists? {os.path.exists(TEMPLATE_FOLDER)}")

# if os.path.exists(TEMPLATE_FOLDER):
#     print(f"Files found: {os.listdir(TEMPLATE_FOLDER)}")
# else:
#     print(f"❌ ERROR: Templates folder not found!")
#     print(f"Please check the path: {TEMPLATE_FOLDER}")
#     input("Press Enter to exit...")
#     sys.exit(1)
# print("=" * 50)

# class LetterMacro:
#     def __init__(self):
#         self.enabled = False
#         self.running = False
#         self.region = SLOT1_LOCATION
#         self.templates = []
#         self.debug = True
        
#         # Core values
#         self.DETECTION_THRESHOLD = 0.85
#         self.MIN_BRIGHTNESS = 10
#         self.FAST_POLL = 0.1
#         self.KEY_DELAY = 0.10  # 100ms default
        
#         self.setup_gui()
#         self.load_templates()
        
#     def log(self, message):
#         if self.debug:
#             print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
#     def setup_gui(self):
#         self.root = tk.Tk()
#         self.root.title("Letter Macro - Slot 1 Only")
#         self.root.geometry("400x250")
        
#         # Status
#         self.status_var = tk.StringVar(value="Stopped")
#         status_label = tk.Label(self.root, textvariable=self.status_var, font=("Arial", 14, "bold"))
#         status_label.pack(pady=10)
        
#         # Show hardcoded region
#         region_frame = tk.LabelFrame(self.root, text="First Letter Slot", padx=5, pady=5)
#         region_frame.pack(pady=5, padx=10, fill="x")
#         tk.Label(region_frame, 
#             text=f"x={SLOT1_LOCATION['left']}, y={SLOT1_LOCATION['top']}, w={SLOT1_LOCATION['width']}, h={SLOT1_LOCATION['height']}", 
#             bg="lightgreen").pack(pady=2)
        
#         # Speed control - 100 to 200ms range
#         speed_frame = tk.Frame(self.root)
#         speed_frame.pack(pady=5)
#         tk.Label(speed_frame, text="Press Delay (ms):").pack(side="left")
        
#         self.delay_var = tk.IntVar(value=100)  # Default 100ms
#         delay_slider = tk.Scale(speed_frame, from_=100, to=200, orient="horizontal", 
#                                variable=self.delay_var, length=150,
#                                command=self.update_delay)
#         delay_slider.pack(side="left", padx=5)
#         tk.Label(speed_frame, text="(100-200ms)").pack(side="left")
        
#         # Debug toggle
#         self.debug_var = tk.BooleanVar(value=self.debug)
#         tk.Checkbutton(self.root, text="Debug Output", variable=self.debug_var, 
#                       command=lambda: setattr(self, 'debug', self.debug_var.get())).pack()
        
#         # Single toggle button
#         self.toggle_button = tk.Button(self.root, text="START", command=self.toggle_macro,
#                                       bg="green", fg="white", width=20, height=2,
#                                       font=("Arial", 10, "bold"))
#         self.toggle_button.pack(pady=10)
        
#         # Exit button
#         tk.Button(self.root, text="Exit", command=self.exit_app,
#                  bg="gray", fg="white", width=20).pack(pady=5)
        
#     def toggle_macro(self):
#         if not self.running:
#             # Turn ON
#             self.enabled = True
#             self.running = True
#             self.status_var.set("RUNNING")
#             self.toggle_button.config(text="STOP", bg="red")
#             threading.Thread(target=self.macro_loop, daemon=True).start()
#             self.log("▶️ Macro turned ON")
#         else:
#             # Turn OFF
#             self.enabled = False
#             self.running = False
#             self.status_var.set("Stopped")
#             self.toggle_button.config(text="START", bg="green")
#             self.log("⏹️ Macro turned OFF")
            
#     def exit_app(self):
#         self.enabled = False
#         self.running = False
#         self.root.quit()
#         self.root.destroy()
        
#     def update_delay(self, val=None):
#         self.KEY_DELAY = self.delay_var.get() / 1000
#         self.log(f"Press delay set to {self.KEY_DELAY*1000:.0f}ms")
        
#     def load_templates(self):
#         """Load templates into flat list"""
#         self.log("Loading templates...")
#         self.templates = []
#         loaded = 0
        
#         for f in os.listdir(TEMPLATE_FOLDER):
#             if not f.lower().endswith('.png'):
#                 continue
                
#             # Extract letter (pC.png -> C, C.png -> C)
#             letter = f[1].upper() if f.startswith('p') else f[0].upper()
                
#             path = os.path.join(TEMPLATE_FOLDER, f)
#             img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            
#             if img is not None:
#                 self.templates.append((letter, img))
#                 loaded += 1
#                 self.log(f"  Loaded: {f} -> {letter}")
                
#         self.log(f"✅ Loaded {loaded} templates")
#         return loaded > 0
        
#     def detect_in_region(self, img):
#         """Core detection logic"""
#         # Convert to grayscale
#         gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY) if img.shape[2] == 4 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#         brightness = np.mean(gray)
        
#         # Skip dark regions
#         if brightness < self.MIN_BRIGHTNESS:
#             return None, 0
            
#         best_letter, best_score = None, 0
        
#         for letter, template in self.templates:
#             if template.shape[0] > gray.shape[0] or template.shape[1] > gray.shape[1]:
#                 continue
                
#             score = cv2.minMaxLoc(cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED))[1]
            
#             if score > 0.98:  # Perfect match
#                 return letter, score
#             if score > best_score:
#                 best_score, best_letter = score, letter
                
#         return (best_letter, best_score) if best_score >= self.DETECTION_THRESHOLD else (None, best_score)
        
#     def macro_loop(self):
#         """Main macro loop"""
#         self.log("🚀 Macro running")
#         type_count = scan_count = 0
        
#         with mss.mss() as sct:
#             while self.enabled:
#                 try:
#                     scan_count += 1
#                     img = np.array(sct.grab(self.region))
                    
#                     if scan_count % 30 == 0:
#                         self.log(f"⏳ Scanning... ({scan_count} scans)")
                    
#                     letter, score = self.detect_in_region(img)
                    
#                     if letter:
#                         self.log(f"🎯 '{letter}' ({score:.3f}) - TYPING")
#                         keyboard.press_and_release(letter.lower())
#                         type_count += 1
#                         time.sleep(self.KEY_DELAY)
                    
#                     time.sleep(self.FAST_POLL)
                        
#                 except Exception as e:
#                     self.log(f"❌ Error: {e}")
#                     time.sleep(1)
                    
#         self.log(f"🛑 Stopped - typed {type_count} letters")
        
#     def run(self):
#         self.root.mainloop()

# if __name__ == "__main__":
#     LetterMacro().run()