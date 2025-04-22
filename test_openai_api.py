import unittest
import os
import json
from unittest.mock import patch, MagicMock
import tempfile
import asyncio
from openai_api import OpenAI_API

class TestOpenAIAPI(unittest.TestCase):
    """Unit tests for the OpenAI API integration."""
    
    def setUp(self):
        """Setup test environment with test API key."""
        # Create a temporary .env file with a fake API key
        os.environ["OPENAI_API_KEY"] = "test_api_key_for_unit_tests"
        self.temp_image = self.create_temp_image()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test environment variable
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        # Remove temporary files
        if hasattr(self, 'temp_image') and os.path.exists(self.temp_image):
            os.remove(self.temp_image)
    
    def create_temp_image(self):
        """Create a small temporary test image."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        # Create minimal valid PNG file bytes
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n\x0b\x94\x00\x00\x00\x00IEND\xaeB`\x82'
        temp_file.write(png_header)
        temp_file.close()
        return temp_file.name
    
    @patch('openai_api.OpenAI')
    def test_init_with_valid_api_key(self, mock_openai):
        """Test client initialization with valid API key."""
        # Arrange
        mock_openai.return_value = MagicMock()
        
        # Act
        api = OpenAI_API()
        
        # Assert
        self.assertIsNotNone(api.client)
        mock_openai.assert_called_once()
        
    @patch('openai_api.OpenAI')
    def test_encode_image(self, mock_openai):
        """Test image encoding function with a test image."""
        # Arrange
        mock_openai.return_value = MagicMock()
        api = OpenAI_API()
        
        # Act
        result = api.encode_image(self.temp_image)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Base64 strings are typically longer than the binary data
        self.assertGreater(len(result), 20)
    
    @patch('openai_api.OpenAI')
    def test_send_request_text_only(self, mock_openai):
        """Test sending a request with text only (no images)."""
        # Arrange
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # Set up the mock response chain
        mock_message.content = "Test response"
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_openai.return_value = mock_client
        
        api = OpenAI_API()
        
        # Act
        response = api.send_request("Test instruction")
        
        # Assert
        self.assertEqual(response, "Test response")
        mock_client.chat.completions.create.assert_called_once()
        
        # Check that the correct message format was used
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args['model'], "gpt-4o")
        self.assertEqual(len(call_args['messages']), 1)
        self.assertEqual(call_args['messages'][0]['role'], "user")
        self.assertEqual(len(call_args['messages'][0]['content']), 1)
        self.assertEqual(call_args['messages'][0]['content'][0]['type'], "text")
    
    @patch('openai_api.OpenAI')
    def test_send_request_with_images(self, mock_openai):
        """Test sending a request with both text and image."""
        # Arrange
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # Set up the mock response chain
        mock_message.content = "Test response with image"
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_openai.return_value = mock_client
        
        api = OpenAI_API()
        
        # Act
        response = api.send_request(
            "Test instruction with image",
            screenshot_path=self.temp_image
        )
        
        # Assert
        self.assertEqual(response, "Test response with image")
        mock_client.chat.completions.create.assert_called_once()
        
        # Check that the correct message format was used with image
        call_args = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_args['model'], "gpt-4o")
        self.assertEqual(len(call_args['messages']), 1)
        self.assertEqual(call_args['messages'][0]['role'], "user")
        
        # Should have 2 content items (text + image)
        content_items = call_args['messages'][0]['content']
        self.assertEqual(len(content_items), 2)
        self.assertEqual(content_items[0]['type'], "text")
        self.assertEqual(content_items[1]['type'], "image_url")
        self.assertTrue("data:image/jpeg;base64," in content_items[1]['image_url']['url'])
    
    @patch('openai_api.OpenAI')
    def test_error_handling(self, mock_openai):
        """Test error handling when API call fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_openai.return_value = mock_client
        
        api = OpenAI_API()
        
        # Act
        response = api.send_request("Test instruction")
        
        # Assert
        self.assertTrue("Error:" in response)
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('openai_api.OpenAI')
    def test_check_api_key_success(self, mock_openai):
        """Test API key validation when successful."""
        # Arrange
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        
        # Set up the mock response chain
        mock_message.content = "Test"
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        
        mock_openai.return_value = mock_client
        
        api = OpenAI_API()
        
        # Act
        result = api.check_api_key()
        
        # Assert
        self.assertTrue(result)
        self.assertTrue(mock_client.chat.completions.create.called)
    
    @patch('openai_api.OpenAI')
    def test_check_api_key_failure(self, mock_openai):
        """Test API key validation when it fails."""
        # Arrange
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Invalid API key")
        mock_openai.return_value = mock_client
        
        api = OpenAI_API()
        
        # Act
        result = api.check_api_key()
        
        # Assert
        self.assertFalse(result)
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('openai_api.OpenAI')
    @patch('asyncio.wait_for')
    async def test_send_request_async(self, mock_wait_for, mock_openai):
        """Test the async request method."""
        # Arrange
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the wait_for to return a predefined response
        mock_wait_for.return_value = "Async test response"
        
        api = OpenAI_API()
        
        # Act
        response = await api.send_request_async("Async test instruction")
        
        # Assert
        self.assertEqual(response, "Async test response")
        self.assertTrue(mock_wait_for.called)

if __name__ == '__main__':
    unittest.main() 