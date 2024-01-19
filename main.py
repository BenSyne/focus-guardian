
import time
from datetime import datetime, timedelta
from settings import TASK_DESCRIPTION, SESSION_DURATION, CHECK_INTERVAL, INSTRUCTION_BLOCK, HISTORY_LIMIT
from screenshot import take_screenshot, image_to_base64
from openai_api import OpenAI_API
from history import History
import subprocess
from audio_feedback import provide_audio_feedback

def main():
    print("Initializing OpenAI API...")
    openai_api = OpenAI_API()
    print("OpenAI API initialized.")

    print("Initializing history...")
    history = History()
    print("History initialized.")

    print("Calculating end time...")
    end_time = datetime.now() + timedelta(minutes=SESSION_DURATION)
    print(f"End time calculated: {end_time}")

    print("Entering main loop...")
    interval_count = 0  # Initialize interval count
    while datetime.now() < end_time:
        print(f"Starting interval {interval_count + 1}...")  # Print the interval count

        print("Capturing screenshot...")
        screenshot_filename = "screenshot.png"
        take_screenshot(screenshot_filename)
        print(f"Screenshot captured: {screenshot_filename}")
        
        print("Converting screenshot to base64...")
        screenshot_base64 = image_to_base64(screenshot_filename)
        print("Screenshot converted to base64.")
        
        print("Sending request to OpenAI API...")
        instruction = INSTRUCTION_BLOCK
        response = openai_api.send_request(instruction, screenshot_filename, history.get_history())
        report = response['choices'][0]['message']['content']
        print(f"Received response from OpenAI API: {report}")

        print("Adding response to history...")
        history.add_to_history(response)
        print("Response added to history.")

        print("Providing audio feedback...")
        provide_audio_feedback(report)
        print("Audio feedback provided.")

        print("Waiting for the next check interval...")
        time.sleep(CHECK_INTERVAL)
        print("Check interval ended.")

        interval_count += 1  # Increment the interval count

if __name__ == "__main__":
    print("Starting main function...")
    main()
    print("Main function ended.")

