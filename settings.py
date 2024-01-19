import os
import dotenv

# User settings
TASK_DESCRIPTION = "Your task description here"
SESSION_DURATION = 15  # in minutes
CHECK_INTERVAL = 5  # in seconds
INSTRUCTION_BLOCK = "Your instruction block here"

# History settings
HISTORY_LIMIT = 5

# OpenAI API settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_ENDPOINT = "https://api.openai.com/v1/engines/davinci-codex/completions"

# Screenshot settings
SCREENSHOT_PATH = "./screenshots/"

# Audio feedback settings
import pyautogui
import os
import time
from settings import SCREENSHOT_PATH

def capture_screenshot(filename):
    """
    Function to capture a screenshot and save it to the specified path.
    """
    # Ensure the screenshot directory exists
    if not os.path.exists(SCREENSHOT_PATH):
        os.makedirs(SCREENSHOT_PATH)

    # Capture the screenshot
    screenshot = pyautogui.screenshot()

    # Save the screenshot
    screenshot.save(os.path.join(SCREENSHOT_PATH, filename))

def capture_screenshots(interval, duration):
    """
    Function to capture screenshots at regular intervals for a specified duration.
    """
    # Calculate the number of screenshots to take
    num_screenshots = int(duration / interval)

    # Loop for the specified number of screenshots
    for i in range(num_screenshots):
        # Capture a screenshot
        capture_screenshot(f"screenshot_{i+1}.png")

        # Wait for the specified interval before taking the next screenshot
        time.sleep(interval * 60)  # Convert minutes to seconds
