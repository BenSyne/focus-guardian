import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from ttkthemes import ThemedStyle
from openai_api import OpenAI_API
from screenshot import take_screenshot
from camera import capture_camera_image
import threading
import time
import subprocess
import os
import logging
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from settings import TASK_DESCRIPTION, INSTRUCTION_BLOCK
import asyncio
import queue
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageTk

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Focus Guardian")
        self.root.geometry("800x900")
        self.root.configure(bg='#f0f0f0')
        
        style = ThemedStyle(self.root)
        style.set_theme("equilux")
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Helvetica', 24, 'bold'), padding=10)
        style.configure('Header.TLabel', font=('Helvetica', 18), padding=5)
        style.configure('Stats.TLabel', font=('Helvetica', 14), padding=3)
        style.configure('Custom.TButton', font=('Helvetica', 12), padding=5)
        style.configure('Task.TLabelframe', padding=15)
        style.configure('Task.TLabelframe.Label', font=('Helvetica', 14, 'bold'))
        
        self.client = OpenAI_API()
        self.initialize_variables()
        self.create_widgets()
        self.bind_shortcuts()
        self.session_history = []
        
        # Initialize async event loop
        self.loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()
        
        # Queue for async tasks
        self.task_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
        # Start the response processing thread
        self.response_thread = threading.Thread(target=self._process_responses, daemon=True)
        self.response_thread.start()

    def _run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _process_responses(self):
        while True:
            try:
                response, screenshot_filename, camera_image_filename = self.response_queue.get()
                if response is None:
                    break
                
                # Process the response
                focus_score = self.extract_focus_score(response)
                self.update_focus_stats(focus_score)
                
                # Schedule UI updates on the main thread
                self.root.after(0, self.provide_audio_feedback, response)
                self.root.after(0, self.clean_up_files, screenshot_filename, camera_image_filename)
                
                self.response_queue.task_done()
            except Exception as e:
                logging.error(f"Error processing response: {str(e)}")

    def bind_shortcuts(self):
        self.root.bind('<Control-s>', lambda e: self.start_task_thread())
        self.root.bind('<Control-p>', lambda e: self.pause_task())
        self.root.bind('<Control-r>', lambda e: self.reset_task())
        self.root.bind('<Control-h>', lambda e: self.show_history())

    def initialize_variables(self):
        self.cycle_count = 0
        self.total_duration_seconds = 0
        self.is_paused = False
        self.is_reset = False
        self.is_running = False
        self.current_thread = None
        self.pomodoro_count = 0
        self.current_phase = "Work"
        self.mode = tk.StringVar(value="regular")
        self.mode.trace("w", self.on_mode_change)
        self.use_screenshots_var = tk.BooleanVar(value=True)
        self.use_photos_var = tk.BooleanVar(value=False)
        self.focus_scores = []
        self.total_focus_score = 0
        self.focus_intervals = 0
        self.interval_unit = tk.StringVar(value="minutes")
        self.pause_time = 0
        self.accumulated_pause_time = 0
        self.current_screenshot = None
        self.current_camera_image = None
        self.screenshot_label = None
        self.camera_label = None

    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Focus Guardian", style='Title.TLabel')
        title_label.pack(fill='x', pady=(0, 20))

        # Top section: Timer and Controls
        self.create_timer_section(main_frame)
        
        # Middle section: Mode Selection and Settings
        self.create_settings_section(main_frame)
        
        # Image Preview section
        self.create_image_preview_section(main_frame)
        
        # Bottom section: Task Description
        self.create_task_section(main_frame)

    def create_timer_section(self, parent):
        timer_frame = ttk.LabelFrame(parent, text="", padding="10")
        timer_frame.pack(fill='x', pady=(0, 20))

        # Timer display
        timer_display = ttk.Frame(timer_frame)
        timer_display.pack(fill='x', pady=(0, 10))

        self.timer_label = ttk.Label(timer_display, text="25:00", font=("Helvetica", 48))
        self.timer_label.pack(side='left', padx=20)

        timer_info = ttk.Frame(timer_display)
        timer_info.pack(side='left', fill='y', padx=20)

        self.phase_label = ttk.Label(timer_info, text="Work Phase", style='Header.TLabel')
        self.phase_label.pack(anchor='w')

        self.cycle_timer_label = ttk.Label(timer_info, text="Cycle: 00:00", style='Stats.TLabel')
        self.cycle_timer_label.pack(anchor='w')

        # Progress bar
        self.progress_bar = ttk.Progressbar(timer_frame, orient="horizontal", length=200, mode="determinate", style='Horizontal.TProgressbar')
        self.progress_bar.pack(fill='x', pady=10)

        # Control buttons
        controls = ttk.Frame(timer_frame)
        controls.pack(fill='x', pady=(10, 0))

        self.start_button = ttk.Button(controls, text="Start", command=self.start_task_thread, style='Custom.TButton')
        self.start_button.pack(side='left', padx=5)

        self.pause_button = ttk.Button(controls, text="Pause", command=self.pause_task, state="disabled", style='Custom.TButton')
        self.pause_button.pack(side='left', padx=5)

        self.reset_button = ttk.Button(controls, text="Reset", command=self.reset_task, state="disabled", style='Custom.TButton')
        self.reset_button.pack(side='left', padx=5)

        self.history_button = ttk.Button(controls, text="History", command=self.show_history, style='Custom.TButton')
        self.history_button.pack(side='right', padx=5)

    def create_settings_section(self, parent):
        settings_frame = ttk.LabelFrame(parent, text="Settings", padding="10")
        settings_frame.pack(fill='x', pady=(0, 20))

        # Mode selection
        modes_frame = ttk.Frame(settings_frame)
        modes_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(modes_frame, text="Mode:", style='Stats.TLabel').pack(side='left', padx=(0, 10))
        ttk.Radiobutton(modes_frame, text="Regular", variable=self.mode, value="regular").pack(side='left', padx=5)
        ttk.Radiobutton(modes_frame, text="Pomodoro", variable=self.mode, value="pomodoro").pack(side='left', padx=5)

        self.pomo_count_label = ttk.Label(modes_frame, text="Completed Pomodoros: 0", style='Stats.TLabel')
        self.pomo_count_label.pack(side='right', padx=5)

        # Duration settings
        duration_frame = ttk.Frame(settings_frame)
        duration_frame.pack(fill='x', pady=(0, 10))

        # Interval settings with unit selection
        interval_frame = ttk.Frame(duration_frame)
        interval_frame.pack(side='left', padx=(0, 20))
        
        ttk.Label(interval_frame, text="Interval:", style='Stats.TLabel').pack(side='left', padx=(0, 5))
        self.interval_spinbox = ttk.Spinbox(interval_frame, from_=1, to=3600, width=5)
        self.interval_spinbox.pack(side='left', padx=(0, 5))
        self.interval_spinbox.set(1)
        
        # Unit selection for interval
        unit_frame = ttk.Frame(interval_frame)
        unit_frame.pack(side='left')
        ttk.Radiobutton(unit_frame, text="Min", variable=self.interval_unit, value="minutes").pack(side='left')
        ttk.Radiobutton(unit_frame, text="Sec", variable=self.interval_unit, value="seconds").pack(side='left')

        # Duration settings (always in minutes)
        ttk.Label(duration_frame, text="Duration (min):", style='Stats.TLabel').pack(side='left', padx=(0, 5))
        self.duration_spinbox = ttk.Spinbox(duration_frame, from_=1, to=480, width=5)
        self.duration_spinbox.pack(side='left')
        self.duration_spinbox.set(30)

        # Monitoring options
        monitoring_frame = ttk.Frame(settings_frame)
        monitoring_frame.pack(fill='x')

        ttk.Label(monitoring_frame, text="Monitoring:", style='Stats.TLabel').pack(side='left', padx=(0, 10))
        ttk.Checkbutton(monitoring_frame, text="Screenshots", variable=self.use_screenshots_var).pack(side='left', padx=5)
        ttk.Checkbutton(monitoring_frame, text="Camera", variable=self.use_photos_var).pack(side='left', padx=5)

    def create_image_preview_section(self, parent):
        preview_frame = ttk.LabelFrame(parent, text="Monitoring Preview", padding="10", style='Task.TLabelframe')
        preview_frame.pack(fill='x', pady=(0, 20))

        # Create a frame for the images
        images_frame = ttk.Frame(preview_frame)
        images_frame.pack(fill='x', expand=True)

        # Screenshot preview
        screenshot_frame = ttk.LabelFrame(images_frame, text="Screenshot", padding="5")
        screenshot_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        self.screenshot_label = ttk.Label(screenshot_frame)
        self.screenshot_label.pack(fill='both', expand=True)

        # Camera preview
        camera_frame = ttk.LabelFrame(images_frame, text="Camera", padding="5")
        camera_frame.pack(side='right', fill='both', expand=True, padx=5)
        
        self.camera_label = ttk.Label(camera_frame)
        self.camera_label.pack(fill='both', expand=True)

    def create_task_section(self, parent):
        # Main task frame with custom style
        task_frame = ttk.LabelFrame(parent, text="Task Description", padding="15", style='Task.TLabelframe')
        task_frame.pack(fill='both', expand=True, pady=(0, 20))

        # Task description header
        task_header = ttk.Label(task_frame, 
                              text="What would you like to focus on?",
                              style='Header.TLabel')
        task_header.pack(fill='x', pady=(0, 10))

        # Task description text area with custom font and colors
        self.task_text = scrolledtext.ScrolledText(
            task_frame, 
            height=4,
            wrap=tk.WORD,
            font=('Helvetica', 14),
            bg='#2b2b2b',
            fg='#ffffff',
            insertbackground='#ffffff'  # Cursor color
        )
        self.task_text.pack(fill='both', expand=True, pady=(0, 15))
        self.task_text.insert(tk.END, TASK_DESCRIPTION)
        self.task_text.bind('<KeyRelease>', self.update_ai_instructions)

        # Add a separator
        ttk.Separator(task_frame, orient='horizontal').pack(fill='x', pady=15)

        # AI Instructions section
        ai_frame = ttk.LabelFrame(task_frame, text="AI Instructions", padding="15", style='Task.TLabelframe')
        ai_frame.pack(fill='both', expand=True)

        # Instructions header
        instructions_header = ttk.Label(
            ai_frame,
            text="Focus Guardian's Instructions",
            style='Header.TLabel'
        )
        instructions_header.pack(fill='x', pady=(0, 10))

        # Instructions text area with custom font and colors
        self.ai_instructions_text = scrolledtext.ScrolledText(
            ai_frame,
            height=6,
            wrap=tk.WORD,
            font=('Helvetica', 13),
            bg='#2b2b2b',
            fg='#a0a0a0',  # Slightly dimmer than task text
            insertbackground='#ffffff'
        )
        self.ai_instructions_text.pack(fill='both', expand=True)
        self.update_ai_instructions()

        # Style the text areas
        for text_widget in (self.task_text, self.ai_instructions_text):
            text_widget.configure(
                padx=10,
                pady=10,
                selectbackground='#404040',
                selectforeground='#ffffff',
                relief=tk.FLAT,
                borderwidth=0
            )
            
            # Create a frame for the border effect
            border_frame = ttk.Frame(text_widget.master)
            border_frame.pack(fill='x', pady=5)
            ttk.Separator(border_frame, orient='horizontal').pack(fill='x')

    def on_mode_change(self, *args):
        if self.mode.get() == "pomodoro":
            self.timer_label.config(text="25:00")
        else:
            self.timer_label.config(text="01:00")  # Set to 1 minute for regular mode

    def start_task_thread(self):
        if self.is_running and not self.is_paused:
            return
            
        if self.is_running and self.is_paused:
            # If we're paused, just resume
            self.pause_task()
            return
            
        # Starting fresh
        self.current_thread = threading.Thread(target=self.start_task)
        self.current_thread.start()
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.reset_button.config(state="normal")

    def start_task(self):
        self.is_reset = False
        self.is_running = True
        self.is_paused = False
        self.pause_time = 0
        self.accumulated_pause_time = 0
        task = self.task_text.get("1.0", tk.END).strip()

        if self.mode.get() == "pomodoro":
            self.run_pomodoro_cycle(task)
        else:
            self.run_regular_cycle(task)

        if not self.is_reset and not self.is_paused:
            self.is_running = False
            self.start_button.config(state="normal")
            self.pause_button.config(state="disabled")
            self.reset_button.config(state="disabled")
            self.save_session()

    def pause_task(self):
        if not self.is_running:
            return
            
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            # Pausing
            self.pause_time = time.time()
            self.pause_button.config(text="Resume")
            self.start_button.config(state="normal")
        else:
            # Resuming
            if self.pause_time > 0:
                self.accumulated_pause_time += time.time() - self.pause_time
                self.pause_time = 0
            self.pause_button.config(text="Pause")
            self.start_button.config(state="disabled")

    def reset_task(self):
        if not messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the task?"):
            return
            
        self.is_reset = True
        self.is_running = False
        self.is_paused = False
        self.pause_time = 0
        self.accumulated_pause_time = 0
        
        # Reset UI state
        self.initialize_variables()
        self.timer_label.config(text="00:00")
        self.cycle_timer_label.config(text="Cycle: 00:00")
        self.phase_label.config(text="Work Phase")
        self.progress_bar['value'] = 0
        
        # Reset buttons
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled", text="Pause")
        self.reset_button.config(state="disabled")
        
        # Reset settings
        self.interval_spinbox.set(1)
        self.duration_spinbox.set(30)
        self.interval_unit.set("minutes")

        # Clear image previews
        if self.screenshot_label:
            self.screenshot_label.configure(image='')
        if self.camera_label:
            self.camera_label.configure(image='')

    def run_regular_cycle(self, task):
        # Convert interval to seconds based on selected unit
        interval = int(self.interval_spinbox.get())
        if self.interval_unit.get() == "minutes":
            interval *= 60
            
        duration = int(self.duration_spinbox.get()) * 60  # Duration always in minutes
        end_time = time.time() + duration
        self.total_duration_seconds = duration

        while time.time() < end_time and not self.is_reset:
            if self.is_paused:
                time.sleep(0.1)
                continue
            self.run_timer(interval, "Work", task, end_time)
            if self.is_reset or self.is_paused:
                break

    def run_pomodoro_cycle(self, task):
        work_duration = 25 * 60
        short_break = 5 * 60
        long_break = 15 * 60

        for i in range(4):
            if self.is_reset or self.is_paused:
                break
            self.run_timer(work_duration, "Work", task)
            if self.is_reset or self.is_paused:
                break
            if i < 3:
                self.run_timer(short_break, "Short Break")
            else:
                self.run_timer(long_break, "Long Break")
                self.pomodoro_count += 1
                self.update_pomodoro_count_label()

    def run_timer(self, duration, phase, task=None, cycle_end_time=None):
        start_time = time.time() - self.accumulated_pause_time  # Adjust start time for accumulated pauses
        interval_end_time = start_time + duration
        self.phase_label.config(text=f"{phase} Phase")

        while time.time() - self.accumulated_pause_time < interval_end_time and not self.is_reset:
            current_time = time.time()
            
            if self.is_paused:
                # When paused, we don't accumulate the pause time yet
                # That happens when we resume
                time.sleep(0.1)
                continue
                
            # Adjust current time for all pauses
            adjusted_current = current_time - self.accumulated_pause_time
            
            # Calculate remaining times
            interval_remaining = max(0, int(interval_end_time - adjusted_current))
            if cycle_end_time:
                total_remaining = max(0, int((cycle_end_time - self.accumulated_pause_time) - adjusted_current))
            else:
                total_remaining = interval_remaining
            
            # Update display
            interval_minutes, interval_seconds = divmod(interval_remaining, 60)
            total_minutes, total_seconds = divmod(total_remaining, 60)
            
            self.timer_label.config(text=f"{interval_minutes:02d}:{interval_seconds:02d}")
            self.cycle_timer_label.config(text=f"Cycle: {total_minutes:02d}:{total_seconds:02d}")
            
            # Update progress
            elapsed = adjusted_current - start_time
            self.update_progress(duration, elapsed)
            self.root.update()
            
            time.sleep(0.1)

        if not self.is_reset and not self.is_paused and phase == "Work":
            threading.Thread(target=self.perform_task, args=(task,), daemon=True).start()

        time.sleep(0.1)

    def update_progress(self, total_duration, elapsed):
        progress = min(100, (elapsed / total_duration) * 100)
        self.progress_bar['value'] = progress

    async def _perform_task_async(self, task, screenshot_filename, camera_image_filename):
        current_instructions = self.ai_instructions_text.get("1.0", tk.END).strip()
        response = await self.client.send_request_async(
            current_instructions,
            screenshot_filename,
            camera_image_filename
        )
        return response

    def perform_task(self, task):
        screenshot_filename = None
        camera_image_filename = None

        try:
            if self.use_screenshots_var.get():
                screenshot_filename = f"screenshot_{int(time.time())}.png"
                take_screenshot(screenshot_filename)
                # Update the preview immediately after taking the screenshot
                self.root.after(0, self.update_image_preview, screenshot_filename, None)

            if self.use_photos_var.get():
                camera_image_filename = f"camera_image_{int(time.time())}.png"
                capture_camera_image(camera_image_filename)
                # Update the preview immediately after taking the photo
                self.root.after(0, self.update_image_preview, None, camera_image_filename)

            # Schedule the async task
            future = asyncio.run_coroutine_threadsafe(
                self._perform_task_async(task, screenshot_filename, camera_image_filename),
                self.loop
            )
            
            # Add callback to handle the response
            future.add_done_callback(
                lambda f: self.response_queue.put((f.result(), screenshot_filename, camera_image_filename))
            )

        except Exception as e:
            logging.error(f"Error in perform_task: {str(e)}")
            if screenshot_filename:
                self.clean_up_files(screenshot_filename, None)
            if camera_image_filename:
                self.clean_up_files(None, camera_image_filename)

    def update_image_preview(self, screenshot_path=None, camera_path=None):
        # Update screenshot preview
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                # Load and resize the screenshot
                img = Image.open(screenshot_path)
                # Calculate aspect ratio
                aspect_ratio = img.width / img.height
                new_width = 300
                new_height = int(new_width / aspect_ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.current_screenshot = photo  # Keep a reference
                self.screenshot_label.configure(image=photo)
            except Exception as e:
                logging.error(f"Error updating screenshot preview: {str(e)}")

        # Update camera preview
        if camera_path and os.path.exists(camera_path):
            try:
                # Load and resize the camera image
                img = Image.open(camera_path)
                # Calculate aspect ratio
                aspect_ratio = img.width / img.height
                new_width = 300
                new_height = int(new_width / aspect_ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.current_camera_image = photo  # Keep a reference
                self.camera_label.configure(image=photo)
            except Exception as e:
                logging.error(f"Error updating camera preview: {str(e)}")

    def extract_focus_score(self, response):
        lines = response.split('\n')
        for line in reversed(lines):
            if line.startswith("Focus Score:"):
                try:
                    score = float(line.split(":")[1].strip())
                    # Ensure score is between 0 and 1
                    return max(0, min(1, score))
                except ValueError:
                    return 0
        return 0

    def update_focus_stats(self, focus_score):
        # Ensure focus_score is between 0 and 1
        focus_score = max(0, min(1, focus_score))
        self.focus_scores.append(focus_score)
        self.total_focus_score += focus_score
        self.focus_intervals += 1

    def provide_audio_feedback(self, message):
        try:
            message = message.replace("'", "\\'").replace("(", "\\(").replace(")", "\\)")
            subprocess.call(['say', message])
        except Exception as e:
            print(f"Error while trying to provide audio feedback: {str(e)}")

    def clean_up_files(self, screenshot_filename, camera_image_filename):
        if screenshot_filename and os.path.exists(screenshot_filename):
            os.remove(screenshot_filename)
        if camera_image_filename and os.path.exists(camera_image_filename):
            os.remove(camera_image_filename)

    def reset_pomodoro_count(self):
        self.pomodoro_count = 0
        self.update_pomodoro_count_label()

    def update_pomodoro_count_label(self):
        self.pomo_count_label.config(text=f"Completed Pomodoros: {self.pomodoro_count}")

    def save_session(self):
        if self.focus_intervals > 0:
            avg_focus_score = self.total_focus_score / self.focus_intervals
        else:
            avg_focus_score = 0
            
        focus_percentage = min(100, avg_focus_score * 100)
        session = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'duration': max(0, self.total_duration_seconds) // 60,  # Convert to minutes
            'cycles': max(0, self.cycle_count),
            'task': self.task_text.get("1.0", tk.END).strip(),
            'focus_percentage': round(focus_percentage, 2),
            'focus_scores': [round(score * 100, 2) for score in self.focus_scores]  # Convert to percentages
        }
        self.session_history.append(session)
        with open('session_history.json', 'w') as f:
            json.dump(self.session_history, f)
        
        self.show_focus_report(focus_percentage)

    def show_focus_report(self, focus_percentage):
        report_window = tk.Toplevel(self.root)
        report_window.title("Session Report")
        report_window.geometry("400x300")
        report_window.configure(bg='#f0f0f0')
        
        frame = ttk.Frame(report_window, padding="20")
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text="Session Complete!", style='Header.TLabel').pack(pady=(0, 20))
        
        # Focus score with color indicator
        score_frame = ttk.Frame(frame)
        score_frame.pack(fill='x', pady=10)
        
        score_color = '#4CAF50' if focus_percentage >= 75 else '#FF9800' if focus_percentage >= 50 else '#F44336'
        
        ttk.Label(score_frame, text=f"Focus Score:", style='Stats.TLabel').pack(side='left')
        score_label = ttk.Label(score_frame, text=f"{focus_percentage:.1f}%", 
                               font=('Helvetica', 24, 'bold'))
        score_label.pack(side='left', padx=10)
        
        # Session stats
        stats_frame = ttk.LabelFrame(frame, text="Session Statistics", padding="10")
        stats_frame.pack(fill='x', pady=20)
        
        duration = self.total_duration_seconds // 60
        ttk.Label(stats_frame, text=f"Duration: {duration} minutes", 
                 style='Stats.TLabel').pack(anchor='w', pady=2)
        ttk.Label(stats_frame, text=f"Focus Checks: {self.focus_intervals}", 
                 style='Stats.TLabel').pack(anchor='w', pady=2)
        
        # Motivational message
        if focus_percentage >= 75:
            msg = "Excellent focus! Keep up the great work!"
        elif focus_percentage >= 50:
            msg = "Good session! There's room for improvement."
        else:
            msg = "Stay positive! Each session is a chance to improve."
        
        ttk.Label(frame, text=msg, style='Stats.TLabel', wraplength=300).pack(pady=20)

    def show_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("Focus History")
        history_window.geometry("800x600")
        history_window.configure(bg='#f0f0f0')

        # Create a canvas with scrollbar
        canvas = tk.Canvas(history_window, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(history_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add history entries
        for session in self.session_history:
            session_frame = ttk.LabelFrame(scrollable_frame, padding="10")
            session_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(session_frame, text=f"Date: {session['date']}", style='Stats.TLabel').pack(anchor=tk.W)
            ttk.Label(session_frame, text=f"Duration: {session['duration']} minutes", style='Stats.TLabel').pack(anchor=tk.W)
            ttk.Label(session_frame, text=f"Focus Score: {session['focus_percentage']}%", style='Stats.TLabel').pack(anchor=tk.W)
            
            task_label = ttk.Label(session_frame, text=f"Task: {session['task'][:50]}...", style='Stats.TLabel', wraplength=700)
            task_label.pack(anchor=tk.W)

        # Add the focus history plot
        self.plot_focus_history(scrollable_frame)

        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def plot_focus_history(self, parent):
        if not self.session_history:
            ttk.Label(parent, text="No focus history available yet", style='Stats.TLabel').pack(pady=20)
            return

        # Create figure with subplots
        fig = plt.figure(figsize=(10, 6))
        
        # Focus score trend
        ax1 = plt.subplot2grid((2, 2), (0, 0), colspan=2)
        dates = [session['date'] for session in self.session_history]
        focus_percentages = [session['focus_percentage'] for session in self.session_history]
        
        ax1.plot(dates, focus_percentages, marker='o', color='#2196F3')
        ax1.set_xlabel('Session Date')
        ax1.set_ylabel('Focus Score (%)')
        ax1.set_title('Focus Score Trend')
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Session duration
        ax2 = plt.subplot2grid((2, 2), (1, 0))
        durations = [session['duration'] for session in self.session_history]
        ax2.bar(range(len(durations)), durations, color='#4CAF50')
        ax2.set_xlabel('Session')
        ax2.set_ylabel('Duration (min)')
        ax2.set_title('Session Durations')
        
        # Average focus by time of day
        ax3 = plt.subplot2grid((2, 2), (1, 1))
        times = [datetime.strptime(session['date'], "%Y-%m-%d %H:%M:%S").hour for session in self.session_history]
        scores = [session['focus_percentage'] for session in self.session_history]
        
        # Group scores by time of day
        time_groups = {'Morning (6-12)': [], 'Afternoon (12-18)': [], 'Evening (18-24)': [], 'Night (0-6)': []}
        for time, score in zip(times, scores):
            if 6 <= time < 12:
                time_groups['Morning (6-12)'].append(score)
            elif 12 <= time < 18:
                time_groups['Afternoon (12-18)'].append(score)
            elif 18 <= time < 24:
                time_groups['Evening (18-24)'].append(score)
            else:
                time_groups['Night (0-6)'].append(score)
        
        labels = []
        averages = []
        for period, scores in time_groups.items():
            if scores:  # Only include periods with data
                labels.append(period)
                averages.append(sum(scores) / len(scores))
        
        if labels:  # Only create plot if we have data
            ax3.bar(range(len(labels)), averages, color='#FF9800')
            ax3.set_xticks(range(len(labels)))
            ax3.set_xticklabels(labels, rotation=45, ha='right')
            ax3.set_ylabel('Avg Focus Score (%)')
            ax3.set_title('Focus by Time of Day')
        
        plt.tight_layout()
        
        # Add to the window
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(pady=20)

    def update_ai_instructions(self, event=None):
        task = self.task_text.get("1.0", tk.END).strip()
        instructions = INSTRUCTION_BLOCK.replace(
            '{TASK_DESCRIPTION}',
            task
        )
        
        # Clear and insert with custom tags
        self.ai_instructions_text.delete("1.0", tk.END)
        self.ai_instructions_text.insert(tk.END, instructions)
        
        # Add some visual structure to the instructions
        self.ai_instructions_text.tag_configure(
            "heading",
            font=('Helvetica', 13, 'bold'),
            foreground='#4a9eff'
        )
        
        # Highlight important sections
        for line in instructions.split('\n'):
            if line.strip().endswith(':') or line.strip().isupper():
                start = f"{instructions.find(line)}.0"
                end = f"{instructions.find(line)}.end"
                self.ai_instructions_text.tag_add("heading", start, end)

    def start(self):
        self.root.mainloop()

    def __del__(self):
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if hasattr(self, 'response_queue'):
            self.response_queue.put((None, None, None))  # Signal to stop response thread

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    app.start()