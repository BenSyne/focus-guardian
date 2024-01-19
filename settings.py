import os
import dotenv

# User settings
TASK_DESCRIPTION = "google travel tips for thailand"
SESSION_DURATION = 60000  # in minutes
CHECK_INTERVAL = 10  # in seconds
# Image source settings
USE_SCREENSHOT = True
USE_CAMERA_IMAGE = True

INSTRUCTION_BLOCK = """

Okay, I want you to help me focus, so check in the first image if I have an application open related to coding, since that's what I should be focusing on. In the second image, make sure that I am looking at the computer screen or one of them, which either means I'm looking directly at the camera or just to the left of it at the second monitor. If I'm looking elsewhere or down, which is probably me looking at my phone, gently remind me to get back on task. If I am doing the right thing, simply say, great job, keep going then.

keep the message very short, since I am trying to focus.

write your reply as one continues block of text with no new lines please and dont use any special characters but still keep it short please 

only respond with either a encouragement or a reminder to get back on task

"""


# INSTRUCTION_BLOCK = """

# Your name is focus guardian, you are a guardian that helps people stay focused on their tasks.

# Ben the user is supposed to be doing the following task:

# TASK_DESCRIPTION = "degbug the potts website and either be looking at pots site, replit with code, github or the clickup list of bugs"

# check if the user seems to be doing the right thing by looking at the image and seeing if what they have on screen seems to be associated with their task. If it isn't reply with a simple message reminded them to get back on track. If it does seem like what they are doing is on tasks, congradulate them on their focus on wish them luck.

# Be brief given that the user is trying to focus

# always end every message with, good luck Ben!

# """

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
