import os
import base64

def take_screenshot(filename):
    """
    Function to take a screenshot using the Mac's 'screencapture' command.
    """
    try:
        # Execute the 'screencapture' command with the filename
        os.system(f'screencapture {filename}')
    except Exception as e:
        print(f"Error while trying to take screenshot: {str(e)}")

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