import tkinter as tk
import keyboard
import pywinctl as pwc
import time
from threading import Thread

class RobloxMacro:
    def __init__(self):
        self.macro_enabled = False  # Master OFF
        self.game_active = False
        self.monitor_running = True
        
        # Individual macro toggles - start OFF to match master
        self.m1 = False
        self.m2 = False
        self.m3 = False
        
        Thread(target=self.monitor_loop, daemon=True).start()
        self.setup_hotkeys()
        self.setup_gui()
    
    def monitor_loop(self):
        while self.monitor_running:
            try:
                active = pwc.getActiveWindow()
                self.game_active = active and "roblox" in active.title.lower()
            except:
                self.game_active = False
            time.sleep(0.1)
    
    def macro_1(self):
        if self.macro_enabled and self.game_active and self.m1:
            print("Macro 1")
    
    def macro_2(self):
        if self.macro_enabled and self.game_active and self.m2:
            print("Macro 2")
    
    def macro_3(self):
        if self.macro_enabled and self.game_active and self.m3:
            print("Macro 3")
    
    def setup_hotkeys(self):
        keyboard.add_hotkey('f2', self.macro_1)
        keyboard.add_hotkey('f3', self.macro_2)
        keyboard.add_hotkey('f4', self.macro_3)
    
    def toggle_1(self):
        self.m1 = not self.m1
        self.b1.config(text=f"1: {'ON' if self.m1 else 'OFF'}")
    
    def toggle_2(self):
        self.m2 = not self.m2
        self.b2.config(text=f"2: {'ON' if self.m2 else 'OFF'}")
    
    def toggle_3(self):
        self.m3 = not self.m3
        self.b3.config(text=f"3: {'ON' if self.m3 else 'OFF'}")
    
    def toggle_all(self):
        self.macro_enabled = not self.macro_enabled
        
        # Set all individual toggles to match ALL button
        status = self.macro_enabled
        self.m1 = status
        self.m2 = status
        self.m3 = status
        
        # Update ALL button
        self.all_btn.config(text="ENABLE ALL: ON" if status else "ENABLE ALL: OFF")
        
        # Update individual buttons
        self.b1.config(text=f"Macro 1: {'ON' if status else 'OFF'}")
        self.b2.config(text=f"Macro 2: {'ON' if status else 'OFF'}")
        self.b3.config(text=f"Macro 3: {'ON' if status else 'OFF'}")
    
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.attributes('-topmost', True)  # Line 1 - keeps on top
        self.root.title("MATEW MACRO")
        self.root.geometry("800x400")
        
        self.all_btn = tk.Button(self.root, text="ENABLE ALL: OFF", command=self.toggle_all)
        self.all_btn.pack(pady=2)
        
        self.b1 = tk.Button(self.root, text="Macro 1: OFF", command=self.toggle_1)
        self.b1.pack(pady=2)
        
        self.b2 = tk.Button(self.root, text="Macro 2: OFF", command=self.toggle_2)
        self.b2.pack(pady=2)
        
        self.b3 = tk.Button(self.root, text="Macro 3: OFF", command=self.toggle_3)
        self.b3.pack(pady=2)
        
        self.status = tk.Label(self.root, text="Waiting...")
        self.status.pack(pady=2)
        
        self.update()
    
    def update(self):
        game = "Roblox" if self.game_active else "No Game"
        self.status.config(text=game)
        self.root.after(100, self.update)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RobloxMacro()
    app.run()