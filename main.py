
import time
from datetime import datetime, timedelta
from settings import TASK_DESCRIPTION, SESSION_DURATION, CHECK_INTERVAL, INSTRUCTION_BLOCK, HISTORY_LIMIT
from screenshot import take_screenshot, image_to_base64
from openai_api import OpenAI_API
from history import History
import subprocess
from audio_feedback import provide_audio_feedback

def main():
    # Initialize OpenAI API
    openai_api = OpenAI_API()

    # Initialize history
    history = History()

    # Calculate end time
    end_time = datetime.now() + timedelta(minutes=SESSION_DURATION)

    # Main loop
    while datetime.now() < end_time:
        # Capture screenshot
        screenshot_filename = "screenshot.png"
        take_screenshot(screenshot_filename)
        
        # screenshot_base64 = image_to_base64(screenshot_filename)
        print("Screenshot taken and converted to base64.")
        # Send screenshot to OpenAI API
        print("Sending request to OpenAI API...")
        instruction = INSTRUCTION_BLOCK
        response = openai_api.send_request(instruction, screenshot_filename, history.get_history())
        report = response['choices'][0]['message']['content']
        # Add response to history
        history.add_to_history(response)

        # Provide audio feedback
        
        provide_audio_feedback(report)

        # Wait for the next check interval
        time.sleep(CHECK_INTERVAL * 60)

if __name__ == "__main__":
    main()

