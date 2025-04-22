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
import atexit # Import atexit
import uuid # Import uuid for session IDs
import pkg_resources  # For checking package versions

# Check if OpenAI package is installed and get its version
def check_openai_version():
    try:
        openai_version = pkg_resources.get_distribution("openai").version
        logging.info(f"OpenAI package version: {openai_version}")
        
        # Parse version string into components
        version_parts = openai_version.split('.')
        major_version = int(version_parts[0]) if version_parts else 0
        
        if major_version < 1:
            logging.warning(f"OpenAI package version {openai_version} is outdated. Version 1.0.0+ is recommended.")
            return False, openai_version
        return True, openai_version
    except Exception as e:
        logging.error(f"Error checking OpenAI version: {e}")
        return False, "unknown"

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Focus Guardian")
        self.root.geometry("800x900")
        self.root.configure(bg='#f0f0f0')
        
        # Set up protocol for handling window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        style = ThemedStyle(self.root)
        style.set_theme("equilux")
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Helvetica', 24, 'bold'), padding=10)
        style.configure('Header.TLabel', font=('Helvetica', 18), padding=5)
        style.configure('Stats.TLabel', font=('Helvetica', 14), padding=3)
        style.configure('Custom.TButton', font=('Helvetica', 12), padding=5)
        style.configure('Task.TLabelframe', padding=15)
        style.configure('Task.TLabelframe.Label', font=('Helvetica', 14, 'bold'))
        
        # Check OpenAI version
        is_version_ok, openai_version = check_openai_version()
        if not is_version_ok:
            warning_message = f"Warning: You are using OpenAI SDK version {openai_version}. Version 1.0.0+ is recommended. This may cause compatibility issues."
            messagebox.showwarning("OpenAI Version Warning", warning_message)
        
        try:
            self.client = OpenAI_API()
            # Test API key validity
            if not self.client.check_api_key():
                messagebox.showerror("API Key Error", 
                                    "OpenAI API key is missing or invalid. Please add your API key to the .env file.")
        except Exception as e:
            logging.error(f"Error initializing OpenAI API: {e}")
            messagebox.showerror("API Error", 
                               f"Failed to initialize OpenAI API: {str(e)}\n\nPlease check your API key and internet connection.")
            
        self.initialize_variables()
        self.create_widgets()
        self.bind_shortcuts()
        self.session_history = []
        self.load_session_history() # Load existing history
        
        # Initialize async event loop
        self.loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.async_thread.start()
        
        # Thread lock for shared state variables
        self.state_lock = threading.Lock()
        
        # Queue for async tasks
        self.task_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
        # Start the response processing thread
        self.response_thread = threading.Thread(target=self._process_responses, daemon=True)
        self.response_thread.start()

        self.temp_files = set() # Set to track temporary files
        self.current_session_id = None # Identifier for the current running session
        self.focus_score_label = None # Label to display the latest focus score
        
        # Register cleanup function to run on exit
        atexit.register(self.cleanup_on_exit)

    def _run_async_loop(self):
        """Run the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        except Exception as e:
            logging.error(f"Error in async loop: {e}")
        finally:
            # Close the loop when done
            if not self.loop.is_closed():
                self.loop.close()
                logging.info("Async loop closed.")

    def _on_close(self):
        """Clean up resources and close the window."""
        logging.info("Application closing, cleaning up resources...")
        
        # Stop the async loop
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            logging.info("Stopping async loop...")
        
        # Stop response thread
        if hasattr(self, 'response_queue'):
            logging.info("Stopping response processing thread...")
            self.response_queue.put((None, None, None, None))  # Signal to stop
        
        # Cleanup temp files
        self.cleanup_on_exit()
        
        # Close the window
        self.root.destroy()
        logging.info("Application closed.")

    def _process_responses(self):
        while True:
            try:
                response, screenshot_filename, camera_image_filename, session_id = self.response_queue.get()
                if response is None:
                    break
                
                # Check if the response belongs to the currently active session
                with self.state_lock:
                    active_session_id = self.current_session_id
                
                if session_id != active_session_id:
                    print(f"Ignoring stale response from session {session_id} (current: {active_session_id})")
                    # Clean up files associated with the stale response
                    self.root.after(0, self.clean_up_files, screenshot_filename, camera_image_filename)
                    self.response_queue.task_done()
                    continue # Skip processing this stale response
                
                # Process the response within a try-except block
                try:
                    focus_score = self.extract_focus_score(response)
                    self.update_focus_stats(focus_score)
                    
                    # Schedule UI updates on the main thread
                    self.root.after(0, self.provide_audio_feedback, response)
                    # Cleanup files only after successful processing
                    self.root.after(0, self.clean_up_files, screenshot_filename, camera_image_filename)
                
                except Exception as e:
                    # Log the error and show a message to the user
                    logging.error(f"Error processing OpenAI response: {str(e)}")
                    self.root.after(0, lambda: messagebox.showerror("Processing Error", f"Failed to process the focus analysis response: {str(e)}"))
                    # Attempt to clean up files even if processing failed
                    self.root.after(0, self.clean_up_files, screenshot_filename, camera_image_filename)
                finally:
                    self.response_queue.task_done()
            except Exception as e:
                logging.error(f"Error processing response: {str(e)}")

    def bind_shortcuts(self):
        self.root.bind('<Control-s>', lambda e: self.start_task_thread())
        self.root.bind('<Control-p>', lambda e: self.pause_task())
        self.root.bind('<Control-r>', lambda e: self.reset_task())
        self.root.bind('<Control-h>', lambda e: self.show_history())

    def initialize_variables(self, test_mode=False):
        """Initialize variables for the application. 
        
        Args:
            test_mode: If True, use StringVar without a default root for testing.
        """
        self.cycle_count = 0
        self.total_duration_seconds = 0
        self.is_paused = False
        self.is_reset = False
        self.is_running = False
        self.current_thread = None
        self.pomodoro_count = 0
        self.current_phase = "Work"
        
        # Create StringVar properly with the root
        if not hasattr(self, 'mode') or self.mode is None:
            self.mode = tk.StringVar(master=self.root, value="regular")
            self.mode.trace("w", self.on_mode_change)
        
        # Create BooleanVars with master
        if not hasattr(self, 'use_screenshots_var') or self.use_screenshots_var is None:
            self.use_screenshots_var = tk.BooleanVar(master=self.root, value=True)
        
        if not hasattr(self, 'use_photos_var') or self.use_photos_var is None:
            self.use_photos_var = tk.BooleanVar(master=self.root, value=False)
        
        if not hasattr(self, 'interval_unit') or self.interval_unit is None:
            self.interval_unit = tk.StringVar(master=self.root, value="minutes")
        
        # Initialize other variables
        self.focus_scores = []
        self.total_focus_score = 0
        self.focus_intervals = 0
        self.pause_time = 0          # Raw start time of the current pause
        self.accumulated_pause_time = 0 # Total duration paused in seconds
        self.current_screenshot = None
        self.current_camera_image = None
        self.screenshot_label = None
        self.camera_label = None

    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10") # Reduced padding for main frame
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top Bar (Title and History)
        top_bar = ttk.Frame(main_frame, padding=(0, 0, 0, 10))
        top_bar.pack(fill=tk.X)

        title_label = ttk.Label(top_bar, text="Focus Guardian", style='Title.TLabel')
        title_label.pack(side=tk.LEFT, padx=(10, 0))

        self.history_button = ttk.Button(top_bar, text="History", command=self.show_history, style='Custom.TButton')
        self.history_button.pack(side=tk.RIGHT, padx=10)

        # Main Paned Window (Left: Config, Right: Status)
        main_paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        # Create Left Pane (Configuration & Controls)
        left_pane_frame = ttk.Frame(main_paned_window, padding=10)
        self.create_left_pane(left_pane_frame)
        main_paned_window.add(left_pane_frame, weight=1) # Add with weight

        # Create Right Pane (Status & Monitoring)
        right_pane_frame = ttk.Frame(main_paned_window, padding=10)
        self.create_right_pane(right_pane_frame)
        main_paned_window.add(right_pane_frame, weight=1) # Add with weight

    def create_left_pane(self, parent):
        parent.columnconfigure(0, weight=1) # Allow content to expand horizontally

        # 1. Task Definition Frame
        task_frame = ttk.LabelFrame(parent, text="1. Define Task", padding="10")
        task_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        task_frame.columnconfigure(0, weight=1) # Allow text areas to expand

        # Task description text area
        ttk.Label(task_frame, text="What would you like to focus on?", style='Stats.TLabel').grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.task_text = scrolledtext.ScrolledText(
            task_frame, height=5, wrap=tk.WORD, font=('Helvetica', 12),
            bg='#2b2b2b', fg='#ffffff', insertbackground='#ffffff', relief=tk.FLAT, borderwidth=1
        )
        self.task_text.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.task_text.insert(tk.END, TASK_DESCRIPTION)
        self.task_text.bind('<KeyRelease>', self.update_ai_instructions)
        task_frame.rowconfigure(1, weight=1) # Allow text area to expand vertically

        # AI Instructions text area
        ttk.Label(task_frame, text="AI Instructions (Auto-generated)", style='Stats.TLabel').grid(row=2, column=0, sticky="w", pady=(5, 5))
        self.ai_instructions_text = scrolledtext.ScrolledText(
            task_frame, height=7, wrap=tk.WORD, font=('Helvetica', 11),
            bg='#3c3f41', fg='#a0a0a0', insertbackground='#ffffff', relief=tk.FLAT, borderwidth=1,
            state='disabled' # Make read-only initially
        )
        self.ai_instructions_text.grid(row=3, column=0, sticky="nsew")
        self.update_ai_instructions() # Populate initially
        task_frame.rowconfigure(3, weight=1) # Allow text area to expand vertically

        # 2. Session Settings Frame
        settings_frame = ttk.LabelFrame(parent, text="2. Configure Session", padding="10")
        settings_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1) # Allow space between label and controls

        # Mode selection
        ttk.Label(settings_frame, text="Mode:", style='Stats.TLabel').grid(row=0, column=0, sticky="w", padx=(0, 10))
        modes_subframe = ttk.Frame(settings_frame)
        modes_subframe.grid(row=0, column=1, sticky="ew")
        ttk.Radiobutton(modes_subframe, text="Regular", variable=self.mode, value="regular").pack(side='left', padx=(0, 5))
        ttk.Radiobutton(modes_subframe, text="Pomodoro", variable=self.mode, value="pomodoro").pack(side='left', padx=5)

        # Duration settings
        ttk.Label(settings_frame, text="Duration (min):", style='Stats.TLabel').grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        self.duration_spinbox = ttk.Spinbox(settings_frame, from_=1, to=480, width=5)
        self.duration_spinbox.grid(row=1, column=1, sticky="w")
        self.duration_spinbox.set(30)

        # Interval settings
        ttk.Label(settings_frame, text="Check Interval:", style='Stats.TLabel').grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        interval_subframe = ttk.Frame(settings_frame)
        interval_subframe.grid(row=2, column=1, sticky="ew")
        self.interval_spinbox = ttk.Spinbox(interval_subframe, from_=1, to=3600, width=5)
        self.interval_spinbox.pack(side='left', padx=(0, 5))
        self.interval_spinbox.set(1)
        ttk.Radiobutton(interval_subframe, text="Min", variable=self.interval_unit, value="minutes").pack(side='left')
        ttk.Radiobutton(interval_subframe, text="Sec", variable=self.interval_unit, value="seconds").pack(side='left')

        # Monitoring options
        ttk.Label(settings_frame, text="Monitoring:", style='Stats.TLabel').grid(row=3, column=0, sticky="w", padx=(0, 10), pady=5)
        monitor_subframe = ttk.Frame(settings_frame)
        monitor_subframe.grid(row=3, column=1, sticky="ew")
        ttk.Checkbutton(monitor_subframe, text="Screenshots", variable=self.use_screenshots_var).pack(side='left', padx=(0, 5))
        ttk.Checkbutton(monitor_subframe, text="Camera", variable=self.use_photos_var).pack(side='left', padx=5)

        # 3. Control Frame
        control_frame = ttk.LabelFrame(parent, text="3. Start Focusing", padding="10")
        control_frame.grid(row=2, column=0, sticky="nsew")
        control_frame.columnconfigure((0, 1, 2), weight=1) # Distribute buttons

        self.start_button = ttk.Button(control_frame, text="Start", command=self.start_task_thread, style='Custom.TButton')
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.pause_button = ttk.Button(control_frame, text="Pause", command=self.pause_task, state="disabled", style='Custom.TButton')
        self.pause_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.reset_button = ttk.Button(control_frame, text="Reset", command=self.reset_task, state="disabled", style='Custom.TButton')
        self.reset_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        parent.rowconfigure(0, weight=3) # Give more weight to task frame
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(2, weight=0) # Control frame less vertical space

    def create_right_pane(self, parent):
        parent.columnconfigure(0, weight=1) # Allow content to expand horizontally

        # 1. Timer & Status Frame
        timer_frame = ttk.LabelFrame(parent, text="Session Status", padding="10")
        timer_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        timer_frame.columnconfigure(0, weight=1)

        # Timer display (Large)
        self.timer_label = ttk.Label(timer_frame, text="00:00", font=("Helvetica", 48), anchor="center")
        self.timer_label.grid(row=0, column=0, columnspan=2, pady=(5, 10), sticky="ew")

        # Phase and Cycle Time (Smaller, below timer)
        self.phase_label = ttk.Label(timer_frame, text="Phase", style='Header.TLabel', anchor="center")
        self.phase_label.grid(row=1, column=0, columnspan=2, pady=(0, 5), sticky="ew")

        self.cycle_timer_label = ttk.Label(timer_frame, text="Cycle: 00:00", style='Stats.TLabel', anchor="center")
        self.cycle_timer_label.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky="ew")

        # Progress bar
        self.progress_bar = ttk.Progressbar(timer_frame, orient="horizontal", length=200, mode="determinate", style='Horizontal.TProgressbar')
        self.progress_bar.grid(row=3, column=0, columnspan=2, pady=(5, 10), sticky="ew")

        # Pomodoro count (conditionally visible maybe later?)
        self.pomo_count_label = ttk.Label(timer_frame, text="Pomodoros: 0", style='Stats.TLabel', anchor="center")
        self.pomo_count_label.grid(row=4, column=0, columnspan=2, pady=(0, 5), sticky="ew")
        # Hide initially if needed: self.pomo_count_label.grid_remove()

        # 2. Focus Insights Frame
        focus_frame = ttk.LabelFrame(parent, text="Live Focus", padding="10")
        focus_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        focus_frame.columnconfigure(0, weight=1)

        self.focus_score_label = ttk.Label(focus_frame, text="Focus: --%", font=('Helvetica', 18, 'bold'), anchor="center")
        self.focus_score_label.grid(row=0, column=0, pady=5, sticky="ew")

        # 3. Monitoring Preview Frame
        preview_frame = ttk.LabelFrame(parent, text="Monitoring Preview", padding="10")
        preview_frame.grid(row=2, column=0, sticky="nsew")
        preview_frame.columnconfigure((0, 1), weight=1) # Make columns equal
        preview_frame.rowconfigure(1, weight=1) # Allow labels to expand vertically

        ttk.Label(preview_frame, text="Screenshot", style='Stats.TLabel').grid(row=0, column=0, pady=(0, 5))
        self.screenshot_label = ttk.Label(preview_frame, background='#e0e0e0', relief=tk.SUNKEN, anchor="center")
        self.screenshot_label.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        ttk.Label(preview_frame, text="Camera", style='Stats.TLabel').grid(row=0, column=1, pady=(0, 5))
        self.camera_label = ttk.Label(preview_frame, background='#e0e0e0', relief=tk.SUNKEN, anchor="center")
        self.camera_label.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        # Adjust row weights for right pane
        parent.rowconfigure(0, weight=1) # Timer gets some space
        parent.rowconfigure(1, weight=0) # Focus score less space
        parent.rowconfigure(2, weight=2) # Previews get more space

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
        logging.info("Creating timer thread...")
        self.current_thread.start()
        logging.info("Timer thread started.")
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.reset_button.config(state="normal")

    def start_task(self):
        self.is_reset = False
        self.is_running = True
        self.is_paused = False
        
        with self.state_lock:
            self.pause_time = 0
            self.accumulated_pause_time = 0
            # Generate a unique ID for this new session
            self.current_session_id = str(uuid.uuid4())
            logging.info(f"Starting session: {self.current_session_id}")
        
        logging.info(f"Start_task beginning for session {self.current_session_id}")
        
        task = self.task_text.get("1.0", tk.END).strip()

        if self.mode.get() == "pomodoro":
            logging.info("Running Pomodoro cycle...")
            self.run_pomodoro_cycle(task)
        else:
            logging.info("Running Regular cycle...")
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
        
        with self.state_lock: # Acquire lock
            self.is_paused = not self.is_paused
            is_now_paused = self.is_paused # Local copy while holding lock
            
            if is_now_paused:
                # Pausing: Record the time immediately
                self.pause_time = time.time()
            else:
                # Resuming: Calculate accumulated pause ONLY if pause_time was set
                if self.pause_time > 0:
                    pause_duration = time.time() - self.pause_time
                    self.accumulated_pause_time += pause_duration
                    self.pause_time = 0 # Reset pause start time after calculating
        # Release lock automatically at end of 'with' block
        
        # Update UI outside the lock
        if is_now_paused:
            self.pause_button.config(text="Resume")
            self.start_button.config(state="normal") # Allow start button to act as resume
        else:
            self.pause_button.config(text="Pause")
            self.start_button.config(state="disabled")

    def reset_task(self):
        if not messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the task?"):
            return
            
        logging.info(f"Reset task called, invalidating session {self.current_session_id}")
        with self.state_lock: # Acquire lock
            self.is_reset = True
            self.is_running = False # Also set running to false
            self.is_paused = False
            self.pause_time = 0
            self.accumulated_pause_time = 0
            # Invalidate the session ID
            self.current_session_id = None
        # Release lock
        
        # If a timer thread is running, signal it to stop (it checks self.is_reset)
        # Consider joining the thread if necessary, though checking is_reset should suffice
        
        # Reset UI state (safe to do from main thread)
        self.initialize_variables()

        # Update UI elements that might have changed
        # Ensure labels/widgets exist before configuring
        if hasattr(self, 'timer_label') and self.timer_label is not None:
            self.timer_label.config(text="00:00")
        if hasattr(self, 'cycle_timer_label') and self.cycle_timer_label is not None:
            self.cycle_timer_label.config(text="Cycle: 00:00")
        if hasattr(self, 'phase_label') and self.phase_label is not None:
            self.phase_label.config(text="Phase") # Reset to neutral
        if hasattr(self, 'progress_bar') and self.progress_bar is not None:
            self.progress_bar['value'] = 0
        if hasattr(self, 'focus_score_label') and self.focus_score_label is not None:
            self.focus_score_label.config(text="Focus: --%", foreground='black') # Reset focus score display
        if hasattr(self, 'pomo_count_label') and self.pomo_count_label is not None:
            self.update_pomodoro_count_label() # Update pomo count based on reset value
        
        # Reset buttons (ensure they exist)
        if hasattr(self, 'start_button') and self.start_button is not None:
            self.start_button.config(state="normal")
        if hasattr(self, 'pause_button') and self.pause_button is not None:
            self.pause_button.config(state="disabled", text="Pause")
        if hasattr(self, 'reset_button') and self.reset_button is not None:
            self.reset_button.config(state="disabled")
        
        # Reset settings widgets (ensure they exist)
        if hasattr(self, 'interval_spinbox') and self.interval_spinbox is not None:
            self.interval_spinbox.set(1)
        if hasattr(self, 'duration_spinbox') and self.duration_spinbox is not None:
            self.duration_spinbox.set(30)
        if hasattr(self, 'interval_unit') and self.interval_unit is not None:
            self.interval_unit.set("minutes")

        # Clear image previews
        if hasattr(self, 'screenshot_label') and self.screenshot_label is not None:
            self.screenshot_label.configure(image='')
        if hasattr(self, 'camera_label') and self.camera_label is not None:
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
        # Schedule phase label update on main thread
        self.root.after(0, lambda: self.phase_label.config(text=f"{phase} Phase"))

        # Variables for periodic focus checks during Work phase
        last_check_time = start_time # Initialize with start time
        check_interval_seconds = 0
        if phase == "Work":
            try:
                interval_value = int(self.interval_spinbox.get())
                unit = self.interval_unit.get()
                check_interval_seconds = interval_value * 60 if unit == "minutes" else interval_value
                if check_interval_seconds <= 0:
                    check_interval_seconds = 60 # Default to 60 seconds if invalid
            except ValueError:
                check_interval_seconds = 60 # Default if spinbox value is invalid

        logging.info(f"Run_timer starting for phase '{phase}', duration {duration}s, interval {check_interval_seconds}s")
        while True: # Loop condition managed inside
            current_time = time.time()
            should_break = False
            is_currently_paused = False
            current_acc_pause_time = 0
            
            with self.state_lock: # Acquire lock to check state
                if self.is_reset:
                    should_break = True
                is_currently_paused = self.is_paused
                current_acc_pause_time = self.accumulated_pause_time
                # Read pause_time safely if needed for logic below
                current_pause_start_time = self.pause_time
            # Release lock

            if should_break:
                logging.info("Run_timer loop breaking due to reset.")
                break # Exit loop if reset

            if is_currently_paused:
                # We don't need to update pause_time here as it's done in pause_task
                time.sleep(0.1)
                continue
            # else: logging.debug("Run_timer loop running.") # Optional: too verbose?

            # Note: Resume logic (updating accumulated_pause_time) is now handled in pause_task
                
            # Adjust current time for all pauses (use the value read safely earlier)
            adjusted_current = current_time - current_acc_pause_time

            # Check if timer duration is exceeded
            if adjusted_current >= interval_end_time:
                logging.info(f"Run_timer loop breaking because time is up ({adjusted_current} >= {interval_end_time}).")
                break # Exit loop if time is up
            
            # Perform periodic focus check if it's Work phase and interval has passed
            if phase == "Work" and check_interval_seconds > 0:
                if adjusted_current - last_check_time >= check_interval_seconds:
                    print(f"Performing focus check at {datetime.now()}") # Debug print
                    # Use a separate thread for the check to avoid blocking timer
                    threading.Thread(target=self.perform_task, args=(task,), daemon=True).start()
                    last_check_time = adjusted_current # Update last check time
            
            # Calculate remaining times
            interval_remaining = max(0, int(interval_end_time - adjusted_current))
            if cycle_end_time:
                # Adjust cycle_end_time based on accumulated pauses as well
                adjusted_cycle_end_time = cycle_end_time # No, cycle_end_time should be absolute
                total_remaining = max(0, int(adjusted_cycle_end_time - adjusted_current))
            else:
                total_remaining = interval_remaining
            
            # Update display using root.after
            interval_minutes, interval_seconds = divmod(interval_remaining, 60)
            total_minutes, total_seconds = divmod(total_remaining, 60)
            
            interval_text = f"{interval_minutes:02d}:{interval_seconds:02d}"
            cycle_text = f"Cycle: {total_minutes:02d}:{total_seconds:02d}"
            
            self.root.after(0, lambda it=interval_text: self.timer_label.config(text=it))
            self.root.after(0, lambda ct=cycle_text: self.cycle_timer_label.config(text=ct))
            
            # Update progress using root.after
            elapsed = adjusted_current - start_time
            # Ensure duration is not zero to avoid division error
            progress = min(100, (elapsed / duration * 100) if duration > 0 else 0)
            self.root.after(0, lambda p=progress: self.progress_bar.config(value=p))
            
            time.sleep(0.1) # Keep sleep for yielding

        time.sleep(0.1) # Short sleep before potential next phase

    def update_progress(self, total_duration, elapsed):
        # This method is now effectively replaced by the logic within run_timer using root.after
        # We can remove it or leave it unused. Let's comment it out for now.
        # progress = min(100, (elapsed / total_duration) * 100)
        # self.progress_bar['value'] = progress
        pass

    async def _perform_task_async(self, task, screenshot_filename, camera_image_filename):
        current_instructions = self.ai_instructions_text.get("1.0", tk.END).strip()
        response = await self.client.send_request_async(
            current_instructions,
            screenshot_filename,
            camera_image_filename
        )
        return response

    def perform_task(self, task):
        logging.info("Perform_task called.")
        screenshot_filename = None
        camera_image_filename = None
        perform_check = False
        
        # Check if still running and not paused before proceeding
        with self.state_lock:
            if self.is_running and not self.is_paused:
                 perform_check = True
        
        if not perform_check:
            # print("Skipping focus check because task is paused or stopped.") # Reduce noise
            return

        # Get the session ID safely
        with self.state_lock:
             session_id = self.current_session_id
        
        if not session_id: # Check if session was reset right before check
            print("Skipping focus check because session was reset.")
            return

        try:
            # Show status indicator
            self.root.config(cursor="watch")  # Change cursor to indicate processing
            if hasattr(self, 'focus_score_label') and self.focus_score_label is not None:
                self.root.after(0, lambda: self.focus_score_label.config(text="Analyzing...", foreground="blue"))
                
            logging.info("Proceeding with focus check...")
            if self.use_screenshots_var.get():
                logging.info("Taking screenshot...")
                screenshot_filename = f"screenshot_{int(time.time())}.png"
                take_screenshot(screenshot_filename)
                logging.info(f"Screenshot taken: {screenshot_filename}")
                self.temp_files.add(screenshot_filename) # Track file
                # Update the preview immediately after taking the screenshot
                self.root.after(0, self.update_image_preview, screenshot_filename, None)

            if self.use_photos_var.get():
                logging.info("Capturing camera image...")
                camera_image_filename = f"camera_image_{int(time.time())}.png"
                capture_camera_image(camera_image_filename)
                logging.info(f"Camera image captured: {camera_image_filename}")
                self.temp_files.add(camera_image_filename) # Track file
                # Update the preview immediately after taking the photo
                self.root.after(0, self.update_image_preview, None, camera_image_filename)

            # Schedule the async task, passing the current session ID
            logging.info(f"Scheduling async task for session {session_id}")
            future = asyncio.run_coroutine_threadsafe(
                self._perform_task_async(task, screenshot_filename, camera_image_filename),
                self.loop
            )
            
            # Add callback to handle the response or exception
            future.add_done_callback(
                lambda f: self.handle_async_task_result(f, screenshot_filename, camera_image_filename, session_id)
            )
            
            # Reset cursor after task is scheduled
            self.root.config(cursor="")

        except Exception as e:
            # Reset cursor
            self.root.config(cursor="")
            if hasattr(self, 'focus_score_label') and self.focus_score_label is not None:
                self.root.after(0, lambda: self.focus_score_label.config(text="Focus: --% (Error)", foreground="red"))
                
            logging.error(f"Error in perform_task setup: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Monitoring Error", f"Failed to capture images or schedule analysis: {str(e)}"))
            if screenshot_filename:
                self.clean_up_files(screenshot_filename, None)
            if camera_image_filename:
                self.clean_up_files(None, camera_image_filename)

    def handle_async_task_result(self, future, screenshot_filename, camera_image_filename, session_id):
        """Callback function to handle the result (or exception) of the async task."""
        try:
            # .result() will re-raise any exception that occurred in the task
            response = future.result()
            
            # Check if the session ID is still valid before queueing
            with self.state_lock:
                active_session_id = self.current_session_id
            
            if session_id == active_session_id:
                 # Put the successful result onto the queue for processing
                 self.response_queue.put((response, screenshot_filename, camera_image_filename, session_id))
            else:
                 print(f"Discarding result from stale session {session_id} in callback.")
                 # Clean up files associated with the stale task
                 self.root.after(0, self.clean_up_files, screenshot_filename, camera_image_filename)
        except Exception as e:
            # Log the error from the async task (e.g., OpenAI API error)
            logging.error(f"Error during focus analysis API call: {str(e)}")

    def update_image_preview(self, screenshot_path=None, camera_path=None):
        # Update screenshot preview
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                # Load and resize the screenshot
                img = Image.open(screenshot_path)
                # Calculate aspect ratio and resize to fit label space
                label_width = self.screenshot_label.winfo_width() # Get current label width
                label_height = self.screenshot_label.winfo_height() # Get current label height
                # Avoid division by zero if label not rendered yet
                if label_width <= 1 or label_height <= 1: label_width, label_height = 150, 150 # Default guess
                
                img.thumbnail((label_width - 10, label_height - 10), Image.Resampling.LANCZOS) # Use thumbnail to resize preserving aspect ratio

                # Ensure image is in RGB format for compatibility with ImageTk
                if img.mode != 'RGB':
                    img = img.convert('RGB')

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
                # Calculate aspect ratio and resize to fit label space
                label_width = self.camera_label.winfo_width()
                label_height = self.camera_label.winfo_height()
                if label_width <= 1 or label_height <= 1: label_width, label_height = 150, 150

                img.thumbnail((label_width - 10, label_height - 10), Image.Resampling.LANCZOS)

                # Ensure image is in RGB format
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                photo = ImageTk.PhotoImage(img)
                self.current_camera_image = photo  # Keep a reference
                self.camera_label.configure(image=photo)
            except Exception as e:
                logging.error(f"Error updating camera preview: {str(e)}")

    def extract_focus_score(self, response):
        lines = response.split('\n')
        # First try looking for "Focus Score: X.XX" or "Focus Score: XX%" pattern
        for line in lines:
            line = line.strip()
            if line.lower().startswith("focus score:"):
                try:
                    # Extract the number part
                    score_part = line.split(":", 1)[1].strip()
                    # Handle percentage format (XX%)
                    if "%" in score_part:
                        score_part = score_part.replace("%", "")
                        # Convert percentage to decimal (0-1)
                        score = float(score_part) / 100
                    else:
                        # Extract just the number part if there's additional text
                        import re
                        # Include negative sign in the match pattern
                        number_match = re.search(r'(-?\d+(\.\d+)?)', score_part)
                        if number_match:
                            score = float(number_match.group(1))
                        else:
                            score = float(score_part)
                    # Ensure score is between 0 and 1
                    return max(0, min(1, score))
                except (ValueError, IndexError) as e:
                    logging.error(f"Error parsing focus score '{line}': {e}")
                    
        # If no score found, search for numerical values with context
        # Look for 'focus score' followed by various separators
        for line in lines:
            line = line.lower().strip()
            # Match "focus score" followed by various separators (-, =, etc.)
            import re
            if re.search(r'focus\s+score\s*[-:=]\s*', line):
                try:
                    # Extract the number using regex, allowing for negative numbers
                    number_match = re.search(r'[-:=]\s*(-?\d+(\.\d+)?)', line)
                    if number_match:
                        score = float(number_match.group(1))
                        # If score looks like a percentage (>1), convert to decimal
                        if score > 1:
                            score = score / 100
                        return max(0, min(1, score))
                except Exception as e:
                    logging.error(f"Error extracting focus score from '{line}': {e}")
            
            # Also try the general approach for lines with "focus" and "score"
            elif "focus" in line and "score" in line:
                try:
                    # Try to extract the number from this line with regex
                    # Include negative sign in regex
                    number_match = re.search(r'(-?\d+(\.\d+)?)', line)
                    if number_match:
                        score = float(number_match.group(1))
                        # If score looks like a percentage (>1), convert to decimal
                        if score > 1:
                            score = score / 100
                        return max(0, min(1, score))
                except Exception as e:
                    logging.error(f"Error extracting focus score from '{line}': {e}")
        
        # Log the raw response for debugging
        logging.warning("Could not extract focus score from response. Raw response:")
        logging.warning(response[:500])  # Log first 500 chars to avoid excessive log entries
        
        # If no score found, default to a neutral score
        return 0.5  # 50% (neutral) as fallback

    def update_focus_stats(self, focus_score):
        # Ensure focus_score is between 0 and 1
        focus_score = max(0, min(1, focus_score))
        self.focus_scores.append(focus_score)
        self.total_focus_score += focus_score
        self.focus_intervals += 1

        # Update the Focus Score Label in the UI (Right Pane)
        focus_percentage = focus_score * 100
        score_text = f"Focus: {focus_percentage:.0f}%"
        # Determine color based on score
        score_color = '#4CAF50' if focus_percentage >= 75 else '#FFC107' if focus_percentage >= 50 else '#F44336' # Green, Amber, Red

        # Schedule UI update on main thread
        if hasattr(self, 'focus_score_label') and self.focus_score_label is not None:
             self.root.after(0, lambda: self.focus_score_label.config(text=score_text, foreground=score_color))

    def provide_audio_feedback(self, message):
        try:
            message = message.replace("'", "\\'").replace("(", "\\(").replace(")", "\\)")
            subprocess.call(['say', message])
        except Exception as e:
            print(f"Error while trying to provide audio feedback: {str(e)}")

    def clean_up_files(self, screenshot_filename, camera_image_filename):
        files_to_clean = [screenshot_filename, camera_image_filename]
        for filename in files_to_clean:
            if filename and os.path.exists(filename):
                try:
                    os.remove(filename)
                    print(f"Cleaned up temporary file: {filename}")
                    # Remove from tracking set if successfully deleted
                    if filename in self.temp_files:
                        self.temp_files.remove(filename)
                except OSError as e:
                    logging.error(f"Error deleting file {filename}: {e}")
            elif filename in self.temp_files:
                # If file doesn't exist but is tracked, remove from set
                 self.temp_files.remove(filename)

    def cleanup_on_exit(self):
        """Attempts to clean up any remaining temporary files on application exit."""
        print("Running cleanup on exit...")
        # Create a copy of the set to iterate over, as removing modifies the set
        files_to_remove = list(self.temp_files)
        for filename in files_to_remove:
             if os.path.exists(filename):
                 try:
                     os.remove(filename)
                     print(f"Cleaned up remaining file on exit: {filename}")
                 except OSError as e:
                     # Log error, but don't prevent app exit
                     print(f"Error cleaning up {filename} on exit: {e}") 
        self.temp_files.clear()

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
            font=('Helvetica', 11, 'bold'), # Slightly smaller bold for instructions
            foreground='#4a9eff'
        )
        
        # Enable updates, insert, apply tags, then disable again
        self.ai_instructions_text.config(state='normal')
        self.ai_instructions_text.delete("1.0", tk.END)
        self.ai_instructions_text.insert(tk.END, instructions)
        self.apply_instruction_tags(instructions) # Apply tags separately
        self.ai_instructions_text.config(state='disabled')

    def apply_instruction_tags(self, instructions):
        """Applies 'heading' tag to relevant lines in the AI instructions."""
        if not hasattr(self, 'ai_instructions_text'): return # Guard clause

        current_index = "1.0"
        for line in instructions.split('\\n'):
            trimmed_line = line.strip()
            if trimmed_line.endswith(':') or trimmed_line.isupper() and trimmed_line:
                start_index = self.ai_instructions_text.search(line, current_index, stopindex=tk.END)
                if start_index:
                    end_index = f"{start_index}+{len(line)}c"
                    self.ai_instructions_text.tag_add("heading", start_index, end_index)
                    current_index = end_index # Move search start past this line
                else:
                    # If search fails, move to next line approx
                    current_index = f"{int(float(current_index)) + 1}.0"
            else:
                current_index = f"{int(float(current_index)) + 1}.0" # Approx next line start

    def start(self):
        self.root.mainloop()

    def __del__(self):
        """Destructor to ensure resources are freed."""
        # Most cleanup should happen in _on_close, this is just a backup
        if hasattr(self, 'loop') and self.loop.is_running():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass  # Ignore errors during shutdown
        
        if hasattr(self, 'response_queue'):
            try:
                self.response_queue.put((None, None, None, None))
            except Exception:
                pass  # Ignore errors during shutdown

    # Add method to load history
    def load_session_history(self):
        try:
            if os.path.exists('session_history.json'):
                with open('session_history.json', 'r') as f:
                    loaded_history = json.load(f)
                    # Basic validation: check if it's a list
                    if isinstance(loaded_history, list):
                        self.session_history = loaded_history
                    else:
                        print("Warning: session_history.json is not a list. Starting fresh.")
                        self.session_history = []
            else:
                self.session_history = [] # Ensure it's an empty list if file doesn't exist
        except (json.JSONDecodeError, IOError, TypeError) as e:
            logging.error(f"Error loading session history: {e}")
            # Use root.after to schedule messagebox for the main thread if root exists
            if self.root:
                 self.root.after(0, lambda: messagebox.showerror("History Error", f"Could not load session history file: {e}. Starting with empty history."))
            else:
                 print(f"Error loading session history: {e}. Starting with empty history.")
            self.session_history = [] # Reset to empty list on error

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s',
                       handlers=[
                           logging.FileHandler("focus_guardian.log"),
                           logging.StreamHandler()  # Also output to console
                       ])
    
    try:
        root = tk.Tk()
        app = App(root)
        app.start()
    except Exception as e:
        logging.error(f"Unhandled application error: {e}", exc_info=True)
        messagebox.showerror("Application Error", 
                            f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check the log file for details.")