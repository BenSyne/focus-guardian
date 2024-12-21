import os
import base64
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

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
        self.conversation_history = []
        self.executor = ThreadPoolExecutor(max_workers=1)

    @staticmethod
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def send_request_async(self, instruction_block, screenshot_path=None, camera_image_path=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.send_request, 
            instruction_block, 
            screenshot_path, 
            camera_image_path
        )

    def send_request(self, instruction_block, screenshot_path=None, camera_image_path=None):
        messages = [
            {
                "role": "user",
                "content": instruction_block if not (screenshot_path or camera_image_path) else [
                    {"type": "text", "text": instruction_block}
                ]
            }
        ]

        # Only add image content if we have images
        if screenshot_path is not None or camera_image_path is not None:
            messages[0]["content"] = [{"type": "text", "text": instruction_block}]
            
            if screenshot_path is not None:
                try:
                    base64_image = self.encode_image(screenshot_path)
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    })
                except Exception as e:
                    logging.error(f"Error encoding screenshot: {str(e)}")

            if camera_image_path is not None:
                try:
                    base64_image = self.encode_image(camera_image_path)
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    })
                except Exception as e:
                    logging.error(f"Error encoding camera image: {str(e)}")

        try:
            # Always use gpt-4o model
            model = "gpt-4o"
            
            logging.info(f"Sending request to OpenAI API with model: {model}")
            logging.info(f"Instruction block: {instruction_block[:100]}...")  # Log first 100 chars
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=300
            )

            if response.choices:
                ai_message = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": ai_message})
                return ai_message
            else:
                logging.error("No choices in OpenAI response")
                return "I apologize, but I encountered an error while processing your request."
        except Exception as e:
            logging.error(f"Error in OpenAI API request: {str(e)}")
            error_msg = str(e)
            if "API key" in error_msg:
                return "Error: OpenAI API key is invalid or not properly configured."
            elif "Rate limit" in error_msg:
                return "Error: Rate limit exceeded. Please try again in a moment."
            elif "model" in error_msg.lower():
                return "Error: There was an issue with the AI model. Please try again."
            else:
                return "I apologize, but I encountered an error while processing your request."

    def __del__(self):
        self.executor.shutdown(wait=False)

async def main():
    # Initialize the OpenAI API client
    client = OpenAI_API()

    # Define the instruction block and the image path
    instruction_block = "What's in this image?"
    screenshot_path = "screenshot.png"
    camera_image_path = "camera_image.png"

    # Send the request to the OpenAI API
    response = await client.send_request_async(instruction_block, screenshot_path, camera_image_path)

    # Print the response
    print(response)

if __name__ == "__main__":
    asyncio.run(main())