import pyautogui
import keyboard
import time

print("=" * 50)
print("FIND COMBAT INDICATOR COLOR")
print("=" * 50)
print("\nInstructions:")
print("1. Go into combat in your game")
print("2. Move mouse over the combat indicator")
print("3. Press F5 to capture that pixel")
print("4. Press ESC to exit")
print("=" * 50)

def capture_pixel():
    x, y = pyautogui.position()
    pixel = pyautogui.pixel(x, y)
    
    print(f"\n📍 Position: ({x}, {y})")
    print(f"🎨 RGB: ({pixel[0]}, {pixel[1]}, {pixel[2]})")
    print(f"💠 Hex: #{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}")
    print("-" * 40)

keyboard.add_hotkey('f5', capture_pixel)
print("\nREADY - Move mouse over combat indicator and press F5")
keyboard.wait('esc')