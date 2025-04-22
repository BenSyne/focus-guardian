import os
import base64
import logging
import time

def take_screenshot(filename):
    """
    Function to take a screenshot using the Mac's 'screencapture' command.
    """
    logging.info(f"Taking screenshot... {filename}")
    try:
        # Execute the 'screencapture' command with the filename - add -x flag for non-interactive mode
        logging.info("Executing screencapture command in non-interactive mode...")
        os.system(f'screencapture -x {filename}')
        
        # Check if file was created with timeout
        max_wait = 5  # seconds
        wait_time = 0
        interval = 0.1
        while not os.path.exists(filename) and wait_time < max_wait:
            time.sleep(interval)
            wait_time += interval
            
        if not os.path.exists(filename):
            logging.error(f"Screenshot file not created after {max_wait}s")
            return False
            
        logging.info(f"Screenshot saved to {filename}")
        return True
    except Exception as e:
        logging.error(f"Error taking screenshot: {e}")
        return False

def image_to_base64(filename):
    """
    Function to convert an image file to a base64 string.
    """
    with open(filename, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

if __name__ == "__main__":
    # Test the functions
    take_screenshot("screenshot.png")
    screenshot_base64 = image_to_base64("screenshot.png")
    print("Screenshot taken and converted to base64.")