import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedStyle
from tkinter import messagebox, filedialog
from openai_api import OpenAI_API
from screenshot import take_screenshot, image_to_base64
from camera import capture_camera_image
import threading
import time
import subprocess

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("FOCUS GUARDIAN")
        self.create_widgets()
        self.client = OpenAI_API()
        self.cycle_count = 0
        self.total_duration_seconds = 0
        self.is_paused = False
        self.is_reset = False
        self.is_running = False

    def create_widgets(self):
        style = ThemedStyle(self.root)
        style.set_theme("equilux")  # Use the 'equilux' theme

        # Main frame for setup steps and action items
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame for setup steps
        setup_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE)
        setup_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Group the checkbox options together
        options_frame = tk.Frame(setup_frame)
        options_frame.pack(pady=10)

        self.use_screenshots_var = tk.BooleanVar(value=True)
        self.use_screenshots_checkbutton = tk.Checkbutton(options_frame, text="Use screenshots", variable=self.use_screenshots_var)
        self.use_screenshots_checkbutton.pack(side=tk.LEFT, padx=5)

        self.use_photos_var = tk.BooleanVar()
        self.use_photos_checkbutton = tk.Checkbutton(options_frame, text="Use photos", variable=self.use_photos_var)
        self.use_photos_checkbutton.pack(side=tk.LEFT, padx=5)

        self.interval_label = tk.Label(setup_frame, text="Interval (minutes):")
        self.interval_label.pack()
        self.interval_spinbox = tk.Spinbox(setup_frame, from_=1, to=60)
        self.interval_spinbox.pack()

        self.duration_label = tk.Label(setup_frame, text="Duration (minutes):")
        self.duration_label.pack()
        self.duration_spinbox = tk.Spinbox(setup_frame, from_=1, to=60)
        self.duration_spinbox.pack()

        self.task_label = tk.Label(setup_frame, text="Task:")
        self.task_label.pack(fill=tk.X)

        default_task_text = (
            "Your name is focus guardian, you are a guardian that helps people stay focused on their tasks.\n\n"
            "Ben the user is supposed to be doing the following task:\n\n"
            "TASK_DESCRIPTION = \"Get your code organized and do some research into the trading strategies for the Rick ai\"\n\n"
            "check if the user seems to be doing the right thing by looking at the image and seeing if what they have on screen seems to be associated with their task. If it isn't reply with a simple message reminded them to get back on track. If it does seem like what they are doing is on tasks, congratulate them on their focus on wish them luck.\n\n"
            "Be brief given that the user is trying to focus. If they are on task, say \"That's awesome\" and if they are not on task, say \"That's not awesome\"\n\n"
            "always end every message with, good luck Ben!"
        )
        
        # Increase the size of the task description box
        self.task_text = tk.Text(setup_frame, height=10, font=("Arial", 12))
        self.task_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.task_text.insert(tk.END, default_task_text)

        # Frame for action items
        action_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.cycle_count_label = tk.Label(action_frame, text="Cycle Count: 0")
        self.cycle_count_label.pack()

        self.cycle_timer_label = tk.Label(action_frame, text="Cycle Timer: 0:00")
        self.cycle_timer_label.pack()

        self.total_duration_label = tk.Label(action_frame, text="Total Duration: 0:00")
        self.total_duration_label.pack()

        # Ensure consistent styling for buttons
        button_style = {'padx': 5, 'pady': 5, 'width': 10}
        self.start_button = tk.Button(action_frame, text="Start", command=self.start_task_thread, **button_style)
        self.start_button.pack(side=tk.TOP, pady=5)

        self.pause_button = tk.Button(action_frame, text="Pause", command=self.pause_task, **button_style)
        self.pause_button.pack(side=tk.TOP, pady=5)

        self.reset_button = tk.Button(action_frame, text="Reset", command=self.reset_task, **button_style)
        self.reset_button.pack(side=tk.TOP, pady=5)

    def start_task_thread(self):
        threading.Thread(target=self.start_task).start()

    def pause_task(self):
        self.is_paused = not self.is_paused
        self.pause_button.config(text="Resume" if self.is_paused else "Pause")

    def reset_task(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the task?"):
            self.is_reset = True
            self.is_running = False
            self.cycle_count = 0
            self.total_duration_seconds = 0
            self.cycle_count_label.config(text="Cycle Count: 0")
            self.cycle_timer_label.config(text="Cycle Timer: 0:00")
            self.total_duration_label.config(text="Total Duration: 0:00")

    def start_task(self):
        self.is_reset = False
        self.is_running = True
        interval = int(self.interval_spinbox.get())
        duration = int(self.duration_spinbox.get())
        task = self.task_text.get("1.0", tk.END).strip()

        self.perform_task(task)

        self.total_duration_seconds = duration * 60

        for cycle in range(duration):
            if self.is_reset:
                self.is_reset = False
                return

            self.cycle_count += 1
            self.update_labels()

            for i in range(interval * 60, -1, -1):
                while self.is_paused:
                    time.sleep(1)
                    if self.is_reset:
                        self.is_reset = False
                        return
                minutes, seconds = divmod(i, 60)
                time_format = f"{minutes}:{seconds:02d}"
                self.cycle_timer_label.config(text=f"Cycle Timer: {time_format}")
                self.total_duration_seconds -= 1
                total_minutes, total_seconds = divmod(self.total_duration_seconds, 60)
                self.total_duration_label.config(text=f"Total Duration: {total_minutes}:{total_seconds:02d}")
                if not self.is_running:
                    return
                time.sleep(1)

            self.perform_task(task)

    def perform_task(self, task):
        screenshot_filename = None
        camera_image_filename = None
        if self.use_screenshots_var.get():
            screenshot_filename = "screenshot.png"
            take_screenshot(screenshot_filename)

        if self.use_photos_var.get():
            camera_image_filename = "camera_image.png"
            capture_camera_image(camera_image_filename)

        print("Sending request to OpenAI API...")
        response = self.client.send_request(task, screenshot_filename, camera_image_filename)
        print("Received response from OpenAI API.")
        report = response['choices'][0]['message']['content']
        print(report)
        self.provide_audio_feedback(report)
        print("Waiting for the next cycle...")

    def provide_audio_feedback(self, message):
        """
        Function to provide audio feedback using the system's text-to-speech functionality.
        """
        try:
            # Replace problematic characters in the message
            message = message.replace("'", "\\'").replace("(", "\\(").replace(")", "\\)")
            # Execute the 'say' command with the message
            subprocess.call(['say', message])
        except Exception as e:
            print(f"Error while trying to provide audio feedback: {str(e)}")

    def update_labels(self):
        self.cycle_count_label.config(text=f"Cycle Count: {self.cycle_count}")
        total_minutes, total_seconds = divmod(self.total_duration_seconds, 60)
        self.total_duration_label.config(text=f"Total Duration: {total_minutes}:{total_seconds:02d}")

    def start(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()  # Create a Tk root widget
    style = ThemedStyle(theme="equilux")  # Set the theme
    app = App(root)
    app.start()

