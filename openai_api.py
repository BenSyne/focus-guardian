import os
import base64
import time
from openai import OpenAI
import os
from dotenv import load_dotenv
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests.exceptions

load_dotenv()

class OpenAI_API:
    def __init__(self):
        load_dotenv()  # Load .env file again in case it was updated
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in a .env file.")
            
        # Use more workers to avoid blocking
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.conversation_history = []  # Initialize conversation history
        
        try:
            # Initialize the client with a timeout
            self.client = OpenAI(api_key=api_key, timeout=10.0)
            logging.info("OpenAI API initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI client: {e}")
            raise

    @staticmethod
    def encode_image(image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logging.error(f"Error encoding image {image_path}: {e}")
            raise

    async def send_request_async(self, instruction_block, screenshot_path=None, camera_image_path=None):
        """Send request asynchronously with a timeout."""
        try:
            loop = asyncio.get_event_loop()
            # Use a timeout for the executor call
            return await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor, 
                    self.send_request, 
                    instruction_block, 
                    screenshot_path, 
                    camera_image_path
                ),
                timeout=30  # 30 second overall timeout
            )
        except asyncio.TimeoutError:
            logging.error("Async OpenAI request timed out after 30 seconds")
            return "Error: OpenAI request timed out. Please try again."
        except Exception as e:
            logging.error(f"Error in async OpenAI request: {e}")
            return f"Error: {str(e)}"

    def send_request(self, instruction_block, screenshot_path=None, camera_image_path=None):
        messages = [
            {
                "role": "user",
                "content": []  # Will be filled below
            }
        ]
        
        # First, add text content
        messages[0]["content"].append({
            "type": "text", 
            "text": instruction_block
        })
        
        # Then, add image content if available and exists
        if screenshot_path is not None and os.path.exists(screenshot_path):
            try:
                base64_image = self.encode_image(screenshot_path)
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })
                logging.info("Screenshot added to API request")
            except Exception as e:
                logging.error(f"Error encoding screenshot: {str(e)}")
                # Continue without this image rather than failing completely

        if camera_image_path is not None and os.path.exists(camera_image_path):
            try:
                base64_image = self.encode_image(camera_image_path)
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })
                logging.info("Camera image added to API request")
            except Exception as e:
                logging.error(f"Error encoding camera image: {str(e)}")
                # Continue without this image rather than failing completely

        try:
            # Use gpt-4o model (modern)
            model = "gpt-4o"
            
            logging.info(f"Sending request to OpenAI API with model: {model}")
            logging.info(f"Instruction block: {instruction_block[:100]}...")  # Log first 100 chars
            logging.info(f"Sending with {len(messages[0]['content'])} content items")
            
            # Use a timeout
            start_time = time.time()
            
            # New API call style for v1.0+
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=300
            )
            
            elapsed = time.time() - start_time
            logging.info(f"OpenAI API call completed in {elapsed:.2f} seconds")

            # New response access pattern for v1.0+
            if response.choices:
                ai_message = response.choices[0].message.content
                logging.info(f"Received response from OpenAI API: {ai_message[:100]}...")  # Log first 100 chars
                self.conversation_history.append({"role": "assistant", "content": ai_message})
                return ai_message
            else:
                logging.error("No choices in OpenAI response")
                return "I apologize, but I encountered an error while processing your request."
                
        except requests.exceptions.Timeout:
            logging.error("OpenAI API request timed out")
            return "Error: The request to the AI service timed out. Please try again."
            
        except requests.exceptions.ConnectionError:
            logging.error("OpenAI API connection error")
            return "Error: Could not connect to the AI service. Please check your internet connection."
            
        except Exception as e:
            logging.error(f"Error in OpenAI API request: {str(e)}")
            error_msg = str(e)
            if "API key" in error_msg.lower():
                return "Error: OpenAI API key is invalid or not properly configured."
            elif "Rate limit" in error_msg.lower():
                return "Error: Rate limit exceeded. Please try again in a moment."
            elif "model" in error_msg.lower():
                return "Error: There was an issue with the AI model. Please try again."
            else:
                return f"Error: {error_msg}"

    def __del__(self):
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)

    def check_api_key(self):
        """Verify API key is present and log informative message if not."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.error("OPENAI_API_KEY environment variable is not set")
            return False
        
        # Test with a very simple request to confirm API key works
        try:
            test_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello! This is a test."}],
                max_tokens=5
            )
            if test_response.choices:
                logging.info("API key validation successful")
                return True
            else:
                logging.error("API key validation failed: No response choices")
                return False
        except Exception as e:
            logging.error(f"API key validation failed: {str(e)}")
            return False

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