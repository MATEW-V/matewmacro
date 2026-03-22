import tkinter as tk
import tkinter.font as tkfont
import threading
import time

class DetectionWindowTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Detection Window Tool")
        self.root.attributes('-topmost', True)
        self.root.geometry("300x250")
        
        # Variables
        self.left = tk.IntVar(value=720)
        self.top = tk.IntVar(value=320)
        self.width = tk.IntVar(value=470)
        self.height = tk.IntVar(value=400)
        self.preview_window = None
        self.overlay = None
        self.dragging = False
        self.drag_start = None
        
        self.setup_gui()
        
    def setup_gui(self):
        # Title
        title_font = tkfont.Font(size=12, weight="bold")
        tk.Label(self.root, text="Detection Window Configurator", font=title_font).pack(pady=10)
        
        # Input frame
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10)
        
        # Left
        tk.Label(input_frame, text="Left:", width=8, anchor='w').grid(row=0, column=0, sticky='w', padx=5)
        left_entry = tk.Entry(input_frame, textvariable=self.left, width=8)
        left_entry.grid(row=0, column=1, padx=5)
        tk.Label(input_frame, text="px").grid(row=0, column=2, sticky='w')
        
        # Top
        tk.Label(input_frame, text="Top:", width=8, anchor='w').grid(row=1, column=0, sticky='w', padx=5)
        top_entry = tk.Entry(input_frame, textvariable=self.top, width=8)
        top_entry.grid(row=1, column=1, padx=5)
        tk.Label(input_frame, text="px").grid(row=1, column=2, sticky='w')
        
        # Width
        tk.Label(input_frame, text="Width:", width=8, anchor='w').grid(row=2, column=0, sticky='w', padx=5)
        width_entry = tk.Entry(input_frame, textvariable=self.width, width=8)
        width_entry.grid(row=2, column=1, padx=5)
        tk.Label(input_frame, text="px").grid(row=2, column=2, sticky='w')
        
        # Height
        tk.Label(input_frame, text="Height:", width=8, anchor='w').grid(row=3, column=0, sticky='w', padx=5)
        height_entry = tk.Entry(input_frame, textvariable=self.height, width=8)
        height_entry.grid(row=3, column=1, padx=5)
        tk.Label(input_frame, text="px").grid(row=3, column=2, sticky='w')
        
        # Buttons frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Show Overlay", command=self.show_overlay, 
                 bg="green", fg="white", width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Hide Overlay", command=self.hide_overlay,
                 bg="red", fg="white", width=12).pack(side=tk.LEFT, padx=5)
        
        # Code output frame
        output_frame = tk.Frame(self.root)
        output_frame.pack(pady=10, fill=tk.X)
        
        tk.Label(output_frame, text="Generated Code:", font=("Arial", 9, "bold")).pack()
        self.code_text = tk.Text(output_frame, height=4, width=35, font=("Courier", 8))
        self.code_text.pack(pady=5)
        
        # Copy button
        tk.Button(output_frame, text="Copy to Clipboard", command=self.copy_code,
                 bg="blue", fg="white").pack()
        
        # Status label
        self.status_label = tk.Label(self.root, text="Ready", fg="gray", font=("Arial", 8))
        self.status_label.pack(pady=5)
        
        # Update code when values change
        self.update_code()
        self.left.trace('w', lambda *args: self.update_code())
        self.top.trace('w', lambda *args: self.update_code())
        self.width.trace('w', lambda *args: self.update_code())
        self.height.trace('w', lambda *args: self.update_code())
        
    def update_code(self):
        """Update the generated code display"""
        code = f"# Detection Region\n"
        code += f"SCAN_REGION = {{\n"
        code += f"    'left': {self.left.get()},\n"
        code += f"    'top': {self.top.get()},\n"
        code += f"    'width': {self.width.get()},\n"
        code += f"    'height': {self.height.get()}\n"
        code += f"}}"
        
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, code)
    
    def copy_code(self):
        """Copy the generated code to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.code_text.get(1.0, tk.END).strip())
        self.status_label.config(text="Copied to clipboard!", fg="green")
        self.root.after(2000, lambda: self.status_label.config(text="Ready", fg="gray"))
    
    def show_overlay(self):
        """Create and show the overlay window"""
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.destroy()
            
        # Create overlay window
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("Detection Overlay")
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.3)
        self.overlay.overrideredirect(True)
        
        # Set window geometry
        x = self.left.get()
        y = self.top.get()
        w = self.width.get()
        h = self.height.get()
        
        self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        
        # Create canvas for drawing
        canvas = tk.Canvas(self.overlay, bg='red', highlightthickness=2, highlightbackground='yellow')
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw crosshair in center
        canvas.create_line(w//2, 0, w//2, h, fill='white', width=2)
        canvas.create_line(0, h//2, w, h//2, fill='white', width=2)
        
        # Draw border indicators
        canvas.create_rectangle(0, 0, w, h, outline='yellow', width=3)
        
        # Add coordinate labels
        canvas.create_text(5, 5, text=f"{x},{y}", anchor='nw', fill='white', font=('Arial', 8))
        canvas.create_text(w-5, 5, text=f"{x+w},{y}", anchor='ne', fill='white', font=('Arial', 8))
        canvas.create_text(5, h-5, text=f"{x},{y+h}", anchor='sw', fill='white', font=('Arial', 8))
        canvas.create_text(w-5, h-5, text=f"{x+w},{y+h}", anchor='se', fill='white', font=('Arial', 8))
        
        # Add size label
        canvas.create_text(w//2, h-10, text=f"{w}x{h}", fill='white', font=('Arial', 9, 'bold'))
        
        self.status_label.config(text=f"Overlay shown at ({x}, {y}) size {w}x{h}", fg="blue")
        
        # Bind mouse events for moving/resizing
        self.overlay.bind('<Button-1>', self.start_drag)
        self.overlay.bind('<B1-Motion>', self.on_drag)
        self.overlay.bind('<ButtonRelease-1>', self.stop_drag)
        
    def start_drag(self, event):
        """Start dragging the overlay"""
        self.dragging = True
        self.drag_start = (event.x_root - self.overlay.winfo_x(), 
                          event.y_root - self.overlay.winfo_y())
        
    def on_drag(self, event):
        """Handle dragging movement"""
        if self.dragging:
            x = event.x_root - self.drag_start[0]
            y = event.y_root - self.drag_start[1]
            self.overlay.geometry(f"+{x}+{y}")
            
            # Update input values
            self.left.set(x)
            self.top.set(y)
            
    def stop_drag(self, event):
        """Stop dragging"""
        self.dragging = False
        
    def hide_overlay(self):
        """Hide the overlay window"""
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.destroy()
            self.status_label.config(text="Overlay hidden", fg="gray")

def main():
    app = DetectionWindowTool()
    app.root.mainloop()

if __name__ == "__main__":
    main()