import os
import base64
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

logging.basicConfig(filename='focus_guardian.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class OpenAI_API:
    def __init__(self):
        load_dotenv()
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = 'gpt-4o'
        self.conversation_history = []

    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def send_request(self, instruction_block, screenshot_path=None, camera_image_path=None):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction_block}
                ]
            }
        ]

        if screenshot_path is not None:
            base64_image = self.encode_image(screenshot_path)
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

        if camera_image_path is not None:
            base64_image = self.encode_image(camera_image_path)
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=300
            )

            if response.choices:
                ai_message = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": ai_message})
                return ai_message
            else:
                return "I apologize, but I encountered an error while processing your request."
        except Exception as e:
            logging.error(f"Error in OpenAI API request: {str(e)}")
            return "I apologize, but I encountered an error while processing your request."

def main():
    # Initialize the OpenAI API client
    client = OpenAI_API()

    # Define the instruction block and the image path
    instruction_block = "What's in this image?"
    screenshot_path = "screenshot.png"
    camera_image_path = "camera_image.png"

    # Send the request to the OpenAI API
    response = client.send_request(instruction_block, screenshot_path, camera_image_path)

    # Print the response
    print(response)

if __name__ == "__main__":
    main()