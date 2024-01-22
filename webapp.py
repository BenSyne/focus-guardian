from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from openai_api import OpenAI_API
from screenshot import take_screenshot, image_to_base64
from camera import capture_camera_image
import threading
import time
import subprocess
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a real secret key

# Initialize OpenAI API client
client = OpenAI_API()

# Global variables to keep track of the task state
task_state = {
    'cycle_count': 0,
    'total_duration_seconds': 0,
    'is_paused': False,
    'is_reset': False,
    'is_running': False,
    'task': '',
    'interval': 0,
    'duration': 0
}

def perform_task(task, use_screenshots, use_photos):
    screenshot_filename = None
    camera_image_filename = None
    if use_screenshots:
        screenshot_filename = "screenshot.png"
        take_screenshot(screenshot_filename)

    if use_photos:
        camera_image_filename = "camera_image.png"
        capture_camera_image(camera_image_filename)

    print("Sending request to OpenAI API...")
    response = client.send_request(task, screenshot_filename, camera_image_filename)
    print("Received response from OpenAI API.")
    report = response['choices'][0]['message']['content']
    print(report)
    provide_audio_feedback(report)
    print("Waiting for the next cycle...")

def provide_audio_feedback(message):
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

def start_task():
    task_state['is_reset'] = False
    task_state['is_running'] = True
    interval = task_state['interval']
    duration = task_state['duration']
    task = task_state['task']

    perform_task(task, task_state['use_screenshots'], task_state['use_photos'])

    task_state['total_duration_seconds'] = duration * 60

    for cycle in range(duration):
        if task_state['is_reset']:
            task_state['is_reset'] = False
            return

        task_state['cycle_count'] += 1
        update_labels()

        for i in range(interval * 60, -1, -1):
            while task_state['is_paused']:
                time.sleep(1)
                if task_state['is_reset']:
                    task_state['is_reset'] = False
                    return
            minutes, seconds = divmod(i, 60)
            time_format = f"{minutes}:{seconds:02d}"
            task_state['total_duration_seconds'] -= 1
            if not task_state['is_running']:
                return
            time.sleep(1)

        perform_task(task, task_state['use_screenshots'], task_state['use_photos'])

def update_labels():
    total_minutes, total_seconds = divmod(task_state['total_duration_seconds'], 60)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle form submission
        task_state['use_screenshots'] = 'use_screenshots' in request.form
        task_state['use_photos'] = 'use_photos' in request.form
        task_state['interval'] = int(request.form['interval'])
        task_state['duration'] = int(request.form['duration'])
        task_state['task'] = request.form['task']

        # Start the task in a new thread
        threading.Thread(target=start_task).start()

        flash('Task started successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('index.html', task_state=task_state)

@app.route('/pause', methods=['POST'])
def pause_task():
    task_state['is_paused'] = not task_state['is_paused']
    return jsonify(success=True)

@app.route('/reset', methods=['POST'])
def reset_task():
    task_state['is_reset'] = True
    task_state['is_running'] = False
    task_state['cycle_count'] = 0
    task_state['totalnt']['total_duration_seconds'] = 0
    return jsonify(success=True)

@app.route('/status')
def get_status():
    # Endpoint to get the current status of the task
    total_minutes, total_seconds = divmod(task_state['total_duration_seconds'], 60)
    return jsonify({
        'cycle_count': task_state['cycle_count'],
        'cycle_timer': f"{total_minutes}:{total_seconds:02d}",
        'total_duration': f"{total_minutes}:{total_seconds:02d}",
        'is_paused': task_state['is_paused'],
        'is_running': task_state['is_running']
    })

def start():
    app.run(debug=True)

if __name__ == '__main__':
    start()