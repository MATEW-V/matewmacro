# global key_delay
# global macro_thread
# global debug_win
# global debug_text_widget
# global mini_window
# global stop_hotkeys
# global last_debug_time
# import os
# import sys
# import time
# import threading
# import cv2
# import numpy as np
# import mss
# import keyboard
# import tkinter as tk
# from tkinter import ttk
# from tkinter import messagebox
# from PIL import Image, ImageTk
# if getattr(sys,'frozen',False) and hasattr(sys,'_MEIPASS'):
#   SCRIPT_DIR = sys._MEIPASS
# else:
#   SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# DETECTION_THRESHOLD = 0.85
# MIN_ACCEPT_SCORE = 0.8
# FAST_POLL = 0.0001
# MAX_SCAN_ATTEMPTS = 10
# SCAN_TIMEOUT = 2
# TEMPLATE_FOLDER = os.path.join(SCRIPT_DIR,'letter_templates')
# if not os.path.isdir(TEMPLATE_FOLDER):
#   raise FileNotFoundError(f'''Template folder not found: {TEMPLATE_FOLDER}''')

# root = tk.Tk()
# root.title('RITUALCASTER')
# root.geometry('350x200')
# root.resizable(False,False)
# enabled = tk.BooleanVar(value=False)
# replace_z_with_y = tk.BooleanVar(value=False)
# enable_debug = tk.BooleanVar(value=False)
# ping_value = tk.StringVar(value='10')
# status_text = tk.StringVar(value='Macro Disabled')
# key_delay = 0.01
# macro_thread = None
# _macro_thread_lock = threading.Lock()
# debug_win = None
# debug_text_widget = None
# _debug_lock = threading.Lock()
# mini_window = None
# templates = {}
# filename_to_key = {}
# template_gray = {}
# template_data = []
# LETTER_REGIONS = [{'left':860,'top':200,'width':50,'height':100},{'left':940,'top':200,'width':50,'height':100},{'left':1020,'top':200,'width':50,'height':100},{'left':1100,'top':200,'width':50,'height':100}]
# LETTER_REGIONS_MSS = [{'left':r['left'],'top':r['top'],'width':r['width'],'height':r['height']} for r in LETTER_REGIONS]
# hotkey_thread = None
# stop_hotkeys = False
# last_debug_time = 0
# DEBUG_THROTTLE = 0.1
# region_arrays = [None]*len(LETTER_REGIONS)
# def set_window_icon(root):
#   ico_path = os.path.join(TEMPLATE_FOLDER,'icon.ico')
#   png_path = os.path.join(TEMPLATE_FOLDER,'icon.png')
#   try:
#     if os.path.isfile(ico_path) and sys.platform.startswith('win'):
#       root.iconbitmap(os.path.abspath(ico_path))
#       return None
#     else:
#       if os.path.isfile(png_path):
#         img = tk.PhotoImage(file=os.path.abspath(png_path))
#         root.iconphoto(True,img)
#         return None
#       else:
#         return None

#   except Exception:
#     return None

# pass
# pass
# def create_outlined_text(canvas,x,y,text,fill='white',outline='black',outline_width=1,font=('Arial',10)):
#   '''Create text with outline effect on canvas'''
#   outline_ids = []
#   for dx in (-(outline_width),0,outline_width):
#     for dy in (-(outline_width),0,outline_width):
#       if dx != 0 and dy != 0:
#         continue

#       outline_id = kwargs
#       outline_ids.append(outline_id)
#       continue
#       {'text':text,'fill':outline,'font':font}

#     continue
#     (x+dx,y+dy)

#   main_id = kwargs
#   return (main_id,outline_ids)

# def open_debug_window():
#   global debug_win
#   global debug_text_widget
#   if debug_win and tk.Toplevel.winfo_exists(debug_win):
#     debug_win.lift()
#     debug_win.focus_force()
#     return None
#   else:
#     debug_win = tk.Toplevel(root)
#     debug_win.title('Debug')
#     debug_win.geometry('500x300')
#     debug_win.attributes('-topmost',True)
#     set_window_icon(debug_win)
#     text = tk.Text(debug_win,wrap='none',state='disabled')
#     text.pack(fill='both',expand=True)
#     debug_text_widget = text
#     def on_close():
#       enable_debug.set(False)
#       close_debug_window()

#     debug_win.protocol('WM_DELETE_WINDOW',on_close)
#     debug_win.lift()
#     debug_win.focus_force()
#     return None

# def close_debug_window():
#   global debug_win
#   global debug_text_widget
#   try:
#     if debug_win and tk.Toplevel.winfo_exists(debug_win):
#       debug_win.destroy()

#   except Exception:
#     pass

#   debug_win = None
#   debug_text_widget = None

# def on_debug_toggle():
#   if enable_debug.get():
#     open_debug_window()
#     write_debug('Debug enabled')
#     write_debug(f'''Script directory: {SCRIPT_DIR}''')
#     write_debug(f'''Template folder: {TEMPLATE_FOLDER}''')
#     return None
#   else:
#     write_debug('Debug disabled.')
#     close_debug_window()
#     return None

# def write_debug(msg):
#   global last_debug_time
#   if enable_debug.get():
#     return None
#   else:
#     current_time = time.time()
#     if current_time-last_debug_time < DEBUG_THROTTLE:
#       return None
#     else:
#       last_debug_time = current_time
#       timestamped = f'''[{time.strftime('%H:%M:%S')}] {msg}\n'''
#       def _append():
#         if debug_text_widget:
#           if tk.Text.winfo_exists(debug_text_widget):
#             debug_text_widget.configure(state='normal')
#             debug_text_widget.insert('end',timestamped)
#             debug_text_widget.see('end')
#             debug_text_widget.configure(state='disabled')
#             return None
#           else:
#             return None

#         else:
#           return None

#       try:
#         root.after(0,_append)
#         return None
#       except Exception:
#         return None

# def convert_mss_to_bgr_fast(img):
#   '''FASTER: Optimized conversion without unnecessary function calls'''
#   arr = np.array(img)
#   if arr.ndim == 3 and arr.shape[2] == 4:
#     return arr[(:,:,:3)]
#   else:
#     return arr

# def detect_letter_in_region_optimized(region_img,template_list):
#   '''OPTIMIZED: Pre-allocated matching with early termination'''
#   best_letter = None
#   best_score = 0
#   region_gray = cv2.cvtColor(region_img,cv2.COLOR_BGR2GRAY)
#   if np.mean(region_gray) < 10:
#     return (None,0)
#   else:
#     for template_item in template_list:
#       letter,template = template_item
#       template_h,template_w = template.shape[:2]
#       region_h,region_w = region_gray.shape[:2]
#       if template_h > region_h or template_w > region_w:
#         continue

#       try:
#         res = cv2.matchTemplate(region_gray,template,cv2.TM_CCOEFF_NORMED)
#         if max_val > 0.98:
#           (letter,max_val)
#           return
#         else:
#           if max_val > best_score:
#             if max_val >= DETECTION_THRESHOLD:
#               _,max_val,_,best_score = cv2.minMaxLoc(res)
#               best_letter = letter
#               continue

#             continue

#           continue
#           max_val
#           return (best_letter,best_score)

#       except Exception:
#         pass

# def grab_regions_fast(sct):
#   '''OPTIMIZED: Grab all regions at once and reuse arrays'''
#   for i,roi in enumerate(LETTER_REGIONS_MSS):
#     img = sct.grab(roi)
#     if region_arrays[i].shape != (roi['height'],roi['width'],3):
#       region_arrays[i] = np.array(img)
#       continue

#     np.copyto(region_arrays[i],np.array(img))

#   return region_arrays

# def scan_until_all_found_optimized(sct,template_list):
#   '''OPTIMIZED: Faster scanning with better algorithms'''
#   detected_letters = [None]*len(LETTER_REGIONS)
#   attempts = 0
#   start_time = time.time()
#   if attempts < MAX_SCAN_ATTEMPTS:
#     while time.time()-start_time < SCAN_TIMEOUT:
#       region_images = grab_regions_fast(sct)
#       all_found = True
#       for i,color_img in enumerate(region_images):
#         if detected_letters[i] is not None:
#           continue

#         letter,score = detect_letter_in_region_optimized(color_img,template_list)
#         if letter and score >= DETECTION_THRESHOLD:
#           detected_letters[i] = letter
#           if enable_debug.get():
#             write_debug(f'''Slot {i+1}: \'{letter}\' score {score:.3f}''')
#             continue

#           continue

#         all_found = False

#       if all_found:
#         if enable_debug.get():
#           write_debug('All slots found!')

#         break
#       else:
#         attempts += 1
#         time.sleep(0.005)
#         if attempts < MAX_SCAN_ATTEMPTS:
#           continue

#   if enable_debug.get():
#     if all((letter is not None for letter in detected_letters)):
#       write_debug(f'''Successfully found all slots in {attempts+1} attempts''')
#       return detected_letters
#     else:
#       write_debug(f'''Could not find all slots after {attempts+1} attempts''')
#       write_debug(f'''Found: {detected_letters}''')

#   return detected_letters

# def press_key_fast(key,key_delay):
#   '''OPTIMIZED: Faster key pressing'''
#   keyboard.press(key.lower())
#   keyboard.release(key.lower())
#   if key_delay > 0:
#     time.sleep(key_delay)
#     return None
#   else:
#     return None

# def safe_send_sequence_fast(sequence,key_delay):
#   '''OPTIMIZED: Faster sequence sending'''
#   if sequence:
#     return None
#   else:
#     modified_sequence = []
#     for letter in sequence:
#       if letter:
#         base_letter = letter.upper()
#         if __CHAOS_PY_NULL_PTR_VALUE_ERR__ == base_letter:
#           pass

#         modified_sequence.append(base_letter)
#         continue
#         (replace_z_with_y.get() and 'Z')

#     for ch in modified_sequence:
#       press_key_fast(ch,key_delay)
#       continue
#       'Y'

#     return None

# def macro_loop_optimized():
#   sct = mss.mss()
#   write_debug('Macro loop started (OPTIMIZED MODE)')
#   template_list = [(k,v) for k,v in template_gray.items()]
#   base_delay = 0.115
#   while enabled.get():
#     try:
#       detected_letters = scan_until_all_found_optimized(sct,template_list)
#       sequence = [letter for letter in detected_letters]
#       if sequence:
#         if enable_debug.get():
#           write_debug(f'''Full slots: {detected_letters}''')
#           write_debug(f'''Sending sequence: {sequence}''')

#         safe_send_sequence_fast(sequence,key_delay)

#       time.sleep(FAST_POLL)
#     except Exception as e:
#       if enable_debug.get():
#         write_debug(f'''Macro error: {e}''')

#       time.sleep(0.005)

# def start_macro():
#   global macro_thread
#   if macro_thread:
#     if macro_thread.is_alive():
#       return None
#     else:
#       enabled.set(True)
#       macro_thread = threading.Thread(target=macro_loop_optimized,daemon=True)
#       macro_thread.start()
#       status_text.set('Macro Enabled')
#       write_debug('Macro started (OPTIMIZED MODE)')
#       return None

# def stop_macro():
#   enabled.set(False)
#   status_text.set('Macro Disabled')
#   write_debug('Macro stopped')

# def update_key_delay():
#   global key_delay
#   try:
#     ping_ms = float(ping_value.get())
#     ping_delay = ping_ms*0.001
#     key_delay = 0.09+ping_delay
#     write_debug(f'''Key delay updated to: {key_delay:.4f}s''')
#     return None
#   except ValueError:
#     write_debug(f'''Invalid ping value: {ping_value.get()}''')
#     return None

# def hotkey_listener():
#   def on_f1():
#     if enabled.get():
#       write_debug('F1 pressed - starting macro')
#       start_macro()
#       return None
#     else:
#       return None

#   def on_f2():
#     if enabled.get():
#       write_debug('F2 pressed - stopping macro')
#       stop_macro()
#       return None
#     else:
#       return None

#   keyboard.on_press_key('f1',lambda _: on_f1())
#   keyboard.on_press_key('f2',lambda _: on_f2())
#   write_debug('Hotkeys activated - F1 to start, F2 to stop macro')

# def setup_hotkeys():
#   global stop_hotkeys
#   stop_hotkeys = False
#   hotkey_listener()

# def stop_hotkey_listener():
#   global stop_hotkeys
#   stop_hotkeys = True
#   keyboard.unhook_all()
#   write_debug('Hotkey listener stopped')

# def minimize_to_tray():
#   global mini_window
#   root.withdraw()
#   mini_window = tk.Toplevel(root)
#   mini_window.overrideredirect(True)
#   mini_window.attributes('-topmost',True)
#   mini_window.attributes('-alpha',0.9)
#   screen_width = mini_window.winfo_screenwidth()
#   screen_height = mini_window.winfo_screenheight()
#   mini_width = 120
#   mini_height = 30
#   x = 10
#   y = screen_height-mini_height-50
#   mini_window.geometry(f'''{mini_width}x{mini_height}+{x}+{y}''')
#   mini_canvas = tk.Canvas(mini_window,width=mini_width,height=mini_height,bg='black',highlightthickness=0)
#   mini_canvas.pack()
#   status_indicator = mini_canvas.create_rectangle(5,5,15,15,fill='#FF003F',outline='white')
#   mini_canvas.create_text(mini_width//2,mini_height//2,text='WISP',fill='white',font=('Arial',8,'bold'))
#   def update_mini_status():
#     if enabled.get():
#       mini_canvas.itemconfig(status_indicator,fill='#00C619')
#       return None
#     else:
#       mini_canvas.itemconfig(status_indicator,fill='#FF003F')
#       return None

#   enabled.trace_add('write',lambda : update_mini_status())
#   update_mini_status()
#   def restore_from_tray(event):
#     close_mini_window()
#     root.deiconify()
#     root.lift()
#     root.focus_force()

#   mini_canvas.bind('<Button-1>',restore_from_tray)
#   def show_mini_menu(event):
#     menu = tk.Menu(mini_window,tearoff=0)
#     menu.add_command(label='Restore',command=lambda : restore_from_tray(None))
#     menu.add_command(label='Exit',command=close_app)
#     menu.tk_popup(event.x_root,event.y_root)

#   mini_canvas.bind('<Button-3>',show_mini_menu)
#   def keep_on_top():
#     if mini_window:
#       if tk.Toplevel.winfo_exists(mini_window):
#         mini_window.lift()
#         mini_window.after(1000,keep_on_top)
#         return None
#       else:
#         return None

#     else:
#       return None

#   keep_on_top()

# def close_mini_window():
#   global mini_window
#   if mini_window:
#     mini_window.destroy()
#     mini_window = None
#     return None
#   else:
#     return None

# def center_window(window):
#   window.update_idletasks()
#   width = window.winfo_width()
#   height = window.winfo_height()
#   x = window.winfo_screenwidth()//2-width//2
#   y = window.winfo_screenheight()//2-height//2
#   window.geometry(f'''+{x}+{y}''')

# def custom_minimize():
#   minimize_to_tray()

# root.protocol('WM_ICONIFY',custom_minimize)
# def close_app():
#   stop_macro()
#   stop_hotkey_listener()
#   close_mini_window()
#   root.quit()
#   root.destroy()

# def load_templates_optimized():
#   write_debug('Loading templates (OPTIMIZED)...')
#   skip_files = ['icon.ico','icon.png','background.png']
#   loaded_count = 0
#   for filename in os.listdir(TEMPLATE_FOLDER):
#     if filename.lower() in skip_files:
#       continue

#     if filename.lower().endswith('.png'):
#       continue

#     stem = os.path.splitext(filename)[0]
#     key_char = None
#     for ch in reversed(stem):
#       if ch.isalpha():
#         key_char = ch.upper()
#         break

#     if key_char is None:
#       continue

#     path = os.path.join(TEMPLATE_FOLDER,filename)
#     img = cv2.imread(path,cv2.IMREAD_GRAYSCALE)
#     if img is None:
#       write_debug(f'''Failed to load: {filename}''')
#       continue

#     templates[key_char] = img
#     template_gray[key_char] = img
#     filename_to_key[filename] = key_char
#     loaded_count += 1

#   if templates:
#     write_debug('ERROR: No valid templates found!')
#     messagebox.showerror('Error','No valid templates found in letter_templates folder!')
#     return False
#   else:
#     write_debug(f'''Successfully loaded {loaded_count} templates: {list(templates.keys())}''')
#     return True

# bg_path = os.path.join(TEMPLATE_FOLDER,'background.png')
# if not os.path.isfile(bg_path):
#   raise FileNotFoundError(f'''Background image not found: {bg_path}''')

# bg_pil = Image.open(bg_path)
# bg_resized = bg_pil.resize((350,200),Image.Resampling.LANCZOS)
# bg_image = ImageTk.PhotoImage(bg_resized)
# canvas = tk.Canvas(root,width=350,height=200,highlightthickness=0)
# canvas.pack(fill='both',expand=True)
# canvas.create_image(0,0,image=bg_image,anchor='nw')
# status_display,status_outline_ids = create_outlined_text(canvas,175,20,'Macro Disabled',fill='white',outline='black',font=('Arial',12,'bold'))
# def update_status_display():
#   canvas.itemconfig(status_display,text=status_text.get())
#   for outline_id in status_outline_ids:
#     canvas.itemconfig(outline_id,text=status_text.get())

# status_text.trace_add('write',update_status_display)
# checkbox_elements = {}
# def create_checkbox(x,y,text,variable):
#   rect = canvas.create_rectangle(x,y,x+20,y+20,outline='black',fill='white',width=1)
#   text_id,outline_ids = create_outlined_text(canvas,x+30,y+10,text,fill='white',outline='black',font=('Arial',10,'bold'),anchor='w')
#   def toggle_checkbox(event=None):
#     variable.set(not(variable.get()))
#     update_checkbox_display()

#   def update_checkbox_display():
#     if variable.get():
#       canvas.itemconfig(rect,fill='#00C619')
#       return None
#     else:
#       canvas.itemconfig(rect,fill='white')
#       return None

#   canvas.tag_bind(rect,'<Button-1>',toggle_checkbox)
#   canvas.tag_bind(text_id,'<Button-1>',toggle_checkbox)
#   for outline_id in outline_ids:
#     canvas.tag_bind(outline_id,'<Button-1>',toggle_checkbox)

#   return (rect,text_id,outline_ids,update_checkbox_display)

# replace_rect,replace_text,replace_outlines,update_replace = create_checkbox(20,80,'Replace Z with Y',replace_z_with_y)
# debug_rect,debug_text,debug_outlines,update_debug = create_checkbox(20,110,'Enable Debug',enable_debug)
# checkbox_updaters = {'replace':update_replace,'debug':update_debug}
# replace_z_with_y.trace_add('write',lambda : update_replace())
# enable_debug.trace_add('write',lambda : (update_debug(),on_debug_toggle()))
# ping_label,ping_outline_ids = create_outlined_text(canvas,20,60,'Ping (ms):',fill='white',outline='black',font=('Arial',10,'bold'),anchor='w')
# ping_entry = tk.Entry(root,textvariable=ping_value,width=8,font=('Calibri',9),justify='center',bd=2,relief='sunken',highlightthickness=1,highlightbackground='black',highlightcolor='black')
# ping_entry_window = canvas.create_window(100,60,anchor='w',window=ping_entry)
# ping_value.trace_add('write',update_key_delay)
# btn_start = tk.Button(root,text='Start',command=start_macro,fg='black',bg='#00C619',font=('Arial',10,'bold'),relief='raised',bd=2,width=8)
# btn_stop = tk.Button(root,text='Stop',command=stop_macro,fg='black',bg='#FF003F',font=('Arial',10,'bold'),relief='raised',bd=2,width=8)
# btn_start_window = canvas.create_window(100,150,anchor='nw',window=btn_start)
# btn_stop_window = canvas.create_window(200,150,anchor='nw',window=btn_stop)
# root.bg_image = bg_image
# update_key_delay()
# set_window_icon(root)
# if not load_templates_optimized():
#   btn_start.config(state='disabled')
#   status_text.set('Templates Missing')

# setup_hotkeys()
# root.update_idletasks()
# width = root.winfo_width()
# height = root.winfo_height()
# x = root.winfo_screenwidth()//2-width//2
# y = root.winfo_screenheight()//2-height//2
# root.geometry(f'''+{x}+{y}''')
# def on_focus_out(event):
#   if root.focus_get() is None:
#     if root.state() != 'iconic':
#       custom_minimize()
#       return None
#     else:
#       return None

#   else:
#     return None

# root.bind('<FocusOut>',on_focus_out)
# root.bind('<Unmap>',lambda e: __CHAOS_PY_NULL_PTR_VALUE_ERR__)
# root.mainloop()