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

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("FOCUS GUARDIAN")
        self.client = OpenAI_API()
        self.initialize_variables()
        self.create_widgets()
        self.bind_shortcuts()
        self.session_history = []

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

    def create_widgets(self):
        style = ThemedStyle(self.root)
        style.set_theme("equilux")

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_mode_selection_frame(main_frame)
        self.create_timer_frame(main_frame)
        self.create_task_frame(main_frame)
        self.create_control_frame(main_frame)
        self.create_info_frame(main_frame)

    def create_mode_selection_frame(self, parent):
        mode_frame = ttk.LabelFrame(parent, text="Mode Selection", padding="5")
        mode_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(mode_frame, text="Regular", variable=self.mode, value="regular").pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Pomodoro", variable=self.mode, value="pomodoro").pack(side="left", padx=5)

        self.pomo_count_label = ttk.Label(mode_frame, text="Completed Pomodoros: 0")
        self.pomo_count_label.pack(side="right", padx=5)

        ttk.Button(mode_frame, text="Reset Count", command=self.reset_pomodoro_count).pack(side="right", padx=5)

        ttk.Checkbutton(mode_frame, text="Use Screenshots", variable=self.use_screenshots_var).pack(side="left", padx=5)
        ttk.Checkbutton(mode_frame, text="Use Photos", variable=self.use_photos_var).pack(side="left", padx=5)

    def create_timer_frame(self, parent):
        timer_frame = ttk.LabelFrame(parent, text="Timer", padding="5")
        timer_frame.pack(fill="x", pady=5)

        self.timer_label = ttk.Label(timer_frame, text="25:00", font=("Arial", 24))
        self.timer_label.pack(side="left", padx=5)

        self.phase_label = ttk.Label(timer_frame, text="Work Phase")
        self.phase_label.pack(side="left", padx=5)

        self.cycle_timer_label = ttk.Label(timer_frame, text="Cycle: 00:00", font=("Arial", 18))
        self.cycle_timer_label.pack(side="left", padx=5)

        self.progress_bar = ttk.Progressbar(timer_frame, orient="horizontal", length=200, mode="determinate")
        self.progress_bar.pack(side="right", padx=5)

    def create_task_frame(self, parent):
        task_frame = ttk.LabelFrame(parent, text="Task", padding="5")
        task_frame.pack(fill="both", expand=True, pady=5)

        self.task_text = scrolledtext.ScrolledText(task_frame, height=5, wrap=tk.WORD)
        self.task_text.pack(fill="both", expand=True)
        self.task_text.insert(tk.END, TASK_DESCRIPTION)
        self.task_text.bind('<KeyRelease>', self.update_ai_instructions)

        self.create_interval_duration_frame(task_frame)

        ai_instructions_frame = ttk.LabelFrame(task_frame, text="AI Instructions", padding="5")
        ai_instructions_frame.pack(fill="both", expand=True, pady=5)

        self.ai_instructions_text = scrolledtext.ScrolledText(ai_instructions_frame, height=5, wrap=tk.WORD)
        self.ai_instructions_text.pack(fill="both", expand=True)
        self.update_ai_instructions()

    def create_interval_duration_frame(self, parent):
        interval_duration_frame = ttk.Frame(parent)
        interval_duration_frame.pack(fill="x", pady=5)

        ttk.Label(interval_duration_frame, text="Interval (minutes):").pack(side="left", padx=5)
        self.interval_spinbox = ttk.Spinbox(interval_duration_frame, from_=1, to=60, width=5)
        self.interval_spinbox.pack(side="left", padx=5)
        self.interval_spinbox.set(1)  # Default value changed to 1

        ttk.Label(interval_duration_frame, text="Duration (minutes):").pack(side="left", padx=5)
        self.duration_spinbox = ttk.Spinbox(interval_duration_frame, from_=1, to=480, width=5)
        self.duration_spinbox.pack(side="left", padx=5)
        self.duration_spinbox.set(30)  # Default value changed to 30

    def create_control_frame(self, parent):
        control_frame = ttk.Frame(parent, padding="5")
        control_frame.pack(fill="x", pady=5)

        self.start_button = ttk.Button(control_frame, text="Start", command=self.start_task_thread)
        self.start_button.pack(side="left", padx=5)

        self.pause_button = ttk.Button(control_frame, text="Pause", command=self.pause_task, state="disabled")
        self.pause_button.pack(side="left", padx=5)

        self.reset_button = ttk.Button(control_frame, text="Reset", command=self.reset_task, state="disabled")
        self.reset_button.pack(side="left", padx=5)

        self.history_button = ttk.Button(control_frame, text="Show History", command=self.show_history)
        self.history_button.pack(side="right", padx=5)

    def create_info_frame(self, parent):
        info_frame = ttk.LabelFrame(parent, text="How it works", padding="5")
        info_frame.pack(fill="both", expand=True, pady=5)

        info_text = scrolledtext.ScrolledText(info_frame, height=5, wrap=tk.WORD)
        info_text.pack(fill="both", expand=True)
        info_text.insert(tk.END, self.get_info_text())
        info_text.config(state="disabled")

    def get_info_text(self):
        return """
Regular Mode: Set your own work interval.
Pomodoro Mode: 25min work, 5min break, repeat 4 times, then 15min long break.
The app checks your focus at the end of each work session.
Use the task box to describe what you should be working on.
Stay focused and good luck!
        """

    def on_mode_change(self, *args):
        if self.mode.get() == "pomodoro":
            self.timer_label.config(text="25:00")
        else:
            self.timer_label.config(text="01:00")  # Set to 1 minute for regular mode

    def start_task_thread(self):
        if self.is_running:
            return
        self.current_thread = threading.Thread(target=self.start_task)
        self.current_thread.start()
        self.start_button.config(state="disabled")
        self.pause_button.config(state="normal")
        self.reset_button.config(state="normal")

    def start_task(self):
        self.is_reset = False
        self.is_running = True
        task = self.task_text.get("1.0", tk.END).strip()

        if self.mode.get() == "pomodoro":
            self.run_pomodoro_cycle(task)
        else:
            self.run_regular_cycle(task)

        self.is_running = False
        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled")
        self.reset_button.config(state="disabled")
        
        self.save_session()

    def run_regular_cycle(self, task):
        interval = int(self.interval_spinbox.get()) * 60  # Convert to seconds
        duration = int(self.duration_spinbox.get()) * 60  # Convert to seconds
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
        interval_end_time = time.time() + duration
        self.phase_label.config(text=f"{phase} Phase")

        while time.time() < interval_end_time and not self.is_reset:
            if not self.is_paused:
                interval_remaining = int(interval_end_time - time.time())
                total_remaining = int(cycle_end_time - time.time()) if cycle_end_time else interval_remaining
                
                interval_minutes, interval_seconds = divmod(interval_remaining, 60)
                total_minutes, total_seconds = divmod(total_remaining, 60)
                
                self.timer_label.config(text=f"{interval_minutes:02d}:{interval_seconds:02d}")
                self.cycle_timer_label.config(text=f"Cycle: {total_minutes:02d}:{total_seconds:02d}")
                
                self.update_progress(duration, interval_remaining)
                self.root.update()
                time.sleep(1)
            else:
                time.sleep(0.1)

        if not self.is_reset and not self.is_paused and phase == "Work":
            threading.Thread(target=self.perform_task, args=(task,)).start()

    def update_progress(self, total_duration, remaining):
        progress = ((total_duration - remaining) / total_duration) * 100
        self.progress_bar['value'] = progress

    def perform_task(self, task):
        screenshot_filename = None
        camera_image_filename = None

        if self.use_screenshots_var.get():
            screenshot_filename = f"screenshot_{int(time.time())}.png"
            take_screenshot(screenshot_filename)

        if self.use_photos_var.get():
            camera_image_filename = f"camera_image_{int(time.time())}.png"
            capture_camera_image(camera_image_filename)

        current_instructions = self.ai_instructions_text.get("1.0", tk.END).strip()
        response = self.client.send_request(current_instructions, screenshot_filename, camera_image_filename)
        print(f"OpenAI Response: {response}")
        self.provide_audio_feedback(response)

        self.clean_up_files(screenshot_filename, camera_image_filename)

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

    def pause_task(self):
        self.is_paused = not self.is_paused
        self.pause_button.config(text="Resume" if self.is_paused else "Pause")

    def reset_task(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the task?"):
            self.is_reset = True
            self.is_running = False
            self.initialize_variables()
            self.timer_label.config(text="00:00")
            self.cycle_timer_label.config(text="Cycle: 00:00")
            self.phase_label.config(text="Work Phase")
            self.progress_bar['value'] = 0
            self.start_button.config(state="normal")
            self.pause_button.config(state="disabled")
            self.reset_button.config(state="disabled")
            self.interval_spinbox.set(1)  # Reset to default
            self.duration_spinbox.set(30)  # Reset to default

    def reset_pomodoro_count(self):
        self.pomodoro_count = 0
        self.update_pomodoro_count_label()

    def update_pomodoro_count_label(self):
        self.pomo_count_label.config(text=f"Completed Pomodoros: {self.pomodoro_count}")

    def save_session(self):
        session = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'duration': self.duration,
            'cycles': self.cycle_count,
            'task': self.task_text.get("1.0", tk.END).strip()
        }
        self.session_history.append(session)
        with open('session_history.json', 'w') as f:
            json.dump(self.session_history, f)

    def show_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("Session History")
        
        for session in self.session_history:
            session_frame = tk.Frame(history_window, relief=tk.RAISED, borderwidth=1)
            session_frame.pack(fill=tk.X, padx=5, pady=5)
            
            tk.Label(session_frame, text=f"Date: {session['date']}").pack(anchor=tk.W)
            tk.Label(session_frame, text=f"Duration: {session['duration']} minutes").pack(anchor=tk.W)
            tk.Label(session_frame, text=f"Cycles: {session['cycles']}").pack(anchor=tk.W)
            tk.Label(session_frame, text=f"Task: {session['task'][:50]}...").pack(anchor=tk.W)

    def update_ai_instructions(self, event=None):
        task = self.task_text.get("1.0", tk.END).strip()
        instructions = INSTRUCTION_BLOCK.replace(
            'TASK_DESCRIPTION = "Get your code organized and do some research into the trading strategies for the Rick ai"',
            f'TASK_DESCRIPTION = "{task}"'
        )
        self.ai_instructions_text.delete("1.0", tk.END)
        self.ai_instructions_text.insert(tk.END, instructions)

    def start(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    app.start()