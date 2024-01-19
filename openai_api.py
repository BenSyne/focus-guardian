import os
import base64
import requests
from settings import OPENAI_API_KEY

class OpenAI_API:
    def __init__(self):
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_API_KEY}'
        }

    @staticmethod
    def encode_image(image_path):
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def send_request(self, instruction_block, image_path, history):
        base64_image = self.encode_image(image_path)

        payload = {
            'model': 'gpt-4-vision-preview',
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': instruction_block
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': f'data:image/jpeg;base64,{base64_image}'
                            }
                        }
                    ]
                }
            ],
            'max_tokens': 300
        }

        response = requests.post('https://api.openai.com/v1/chat/completions', headers=self.headers, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'OpenAI API request failed with status code {response.status_code}')

def main():
    # Initialize the OpenAI API client
    client = OpenAI_API()

    # Define the instruction block and the image path
    instruction_block = "What’s in this image?"
    image_path = "screenshot.png"

    # Define the history (empty in this example)
    history = []

    # Send the request to the OpenAI API
    response = client.send_request(instruction_block, image_path, history)

    # Print the response
    print(response)

if __name__ == "__main__":
    main()