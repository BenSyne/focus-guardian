import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


# User settings
TASK_DESCRIPTION = "google travel tips for thailand"
SESSION_DURATION = 60000  # in seconds
CHECK_INTERVAL = 60  # in seconds
# Image source settings
USE_SCREENSHOT = True
USE_CAMERA_IMAGE = False

INSTRUCTION_BLOCK = """
You are Focus Guardian, an AI assistant dedicated to helping users maintain focus and productivity. Your role is to analyze the user's current activity and provide intelligent, contextual feedback.

CURRENT TASK: "{TASK_DESCRIPTION}"

ANALYSIS INSTRUCTIONS:
1. Screen Content Analysis:
   - Examine visible applications, windows, and content
   - Assess relevance to the current task
   - Note any potential distractions

2. Focus Assessment Criteria:
   - Task Relevance: Are open applications/content directly related to the task?
   - Productive Setup: Is the workspace organized for the task?
   - Potential Distractions: Are there visible distractions (social media, unrelated content)?

RESPONSE FORMAT:
1. Keep responses concise (2-3 sentences maximum)
2. Use a supportive, encouraging tone
3. If off-task:
   - Briefly note what's off-track
   - Provide ONE specific, actionable suggestion
   - Be encouraging, not critical
4. If on-task:
   - Acknowledge specific positive behaviors
   - Provide brief encouragement

FOCUS SCORE CALCULATION:
- Score from 0.0 to 1.0 based on:
  * Task Relevance (0.5 weight)
  * Workspace Organization (0.3 weight)
  * Distraction Level (0.2 weight)

End every message with: "Focus Score: [0.0-1.0]"

EXAMPLE RESPONSES:

On-task:
"Great focus on the coding task! Your IDE setup looks perfect for development. Keep up the momentum!"
Focus Score: 0.9

Off-task:
"I notice some social media tabs open. Try using the browser's workspace feature to separate work and personal tabs. You've got this!"
Focus Score: 0.4

Remember: Be brief, specific, and encouraging. The user is trying to focus, so keep interruptions minimal but meaningful.
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