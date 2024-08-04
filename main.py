import time
from datetime import datetime, timedelta
from settings import TASK_DESCRIPTION, SESSION_DURATION, CHECK_INTERVAL, INSTRUCTION_BLOCK, HISTORY_LIMIT, USE_SCREENSHOT, USE_CAMERA_IMAGE
from screenshot import take_screenshot, image_to_base64
from camera import capture_camera_image
from openai_api import OpenAI_API
from history import History
import subprocess
from audio_feedback import provide_audio_feedback

def main():
    openai_api = OpenAI_API()
    history = History()
    end_time = datetime.now() + timedelta(seconds=SESSION_DURATION)
    
    interval_count = 0
    while datetime.now() < end_time:
        print(f"Starting interval {interval_count + 1}...")
        
        # Wait for the check interval
        time.sleep(CHECK_INTERVAL)
        
        screenshot_filename = None
        camera_image_filename = None
        
        if USE_SCREENSHOT:
            print("Capturing screenshot...")
            screenshot_filename = f"screenshot_{interval_count}.png"
            take_screenshot(screenshot_filename)
        
        if USE_CAMERA_IMAGE:
            print("Capturing camera image...")
            camera_image_filename = f"camera_image_{interval_count}.png"
            capture_camera_image(camera_image_filename)
        
        print("Sending request to OpenAI API...")
        response = openai_api.send_request(
            INSTRUCTION_BLOCK,
            screenshot_filename,
            camera_image_filename,
            history.get_history()
        )
        
        print(f"Received response from OpenAI API: {response}")
        
        history.add_to_history(response)
        
        print("Providing audio feedback...")
        provide_audio_feedback(response)
        
        print("Waiting for the next check interval...\n\n")
        
        interval_count += 1

if __name__ == "__main__":
    print("Starting main function...")
    main()
    print("Main function ended.")