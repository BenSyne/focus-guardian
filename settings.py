import os
import dotenv

# User settings
TASK_DESCRIPTION = "google travel tips for thailand"
SESSION_DURATION = 60000  # in minutes
CHECK_INTERVAL = 60  # in seconds
INSTRUCTION_BLOCK = """

Your name is focus guardian, you are a guardian that helps people stay focused on their tasks.

Ben the user is supposed to be doing the following task:

TASK_DESCRIPTION = "using clickup, notion and the browser and google sheets, finish working on revenu projects and expenses for your business plan for your company brainbox labs"

check if the user seems to be doing the right thing by looking at the image and seeing if what they have on screen seems to be associated with their task. If it isn't reply with a simple message reminded them to get back on track. If it does seem like what they are doing is on tasks, congradulate them on their focus on wish them luck.

Be brief given that the user is trying to focus

always end every message with, good luck Ben!

"""

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

# def capture_screenshot(filename):
#     """
#     Function to capture a screenshot and save it to the specified path.
#     """
#     # Ensure the screenshot directory exists
#     if not os.path.exists(SCREENSHOT_PATH):
#         os.makedirs(SCREENSHOT_PATH)

#     # Capture the screenshot
#     screenshot = pyautogui.screenshot()

#     # Save the screenshot
#     screenshot.save(os.path.join(SCREENSHOT_PATH, filename))

# def capture_screenshots(interval, duration):
#     """
#     Function to capture screenshots at regular intervals for a specified duration.
#     """
#     # Calculate the number of screenshots to take
#     num_screenshots = int(duration / interval)

#     # Loop for the specified number of screenshots
#     for i in range(num_screenshots):
#         # Capture a screenshot
#         capture_screenshot(f"screenshot_{i+1}.png")

#         # Wait for the specified interval before taking the next screenshot
#         time.sleep(interval * 60)  # Convert minutes to seconds
