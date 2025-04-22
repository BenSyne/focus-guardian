import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
import cv2
import numpy as np
from camera import capture_camera_image
from screenshot import take_screenshot, image_to_base64

class TestScreenshotAndCamera(unittest.TestCase):
    """Unit tests for the screenshot and camera functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    
    def tearDown(self):
        """Clean up after tests."""
        if hasattr(self, 'test_file') and os.path.exists(self.test_file):
            os.remove(self.test_file)
    
    @patch('screenshot.os.system')
    def test_take_screenshot(self, mock_system):
        """Test screenshot functionality."""
        # Arrange
        mock_system.return_value = 0  # Success
        
        # Create a dummy file to simulate screencapture creating a file
        with open(self.test_file, 'wb') as f:
            f.write(b'test image data')
        
        # Act
        with patch('screenshot.os.path.exists', return_value=True):
            result = take_screenshot(self.test_file)
        
        # Assert
        self.assertTrue(result)
        mock_system.assert_called_once_with(f'screencapture -x {self.test_file}')
    
    @patch('screenshot.os.system')
    def test_take_screenshot_failure(self, mock_system):
        """Test screenshot failure handling."""
        # Arrange
        mock_system.return_value = 1  # Command failed
        
        # Act
        with patch('screenshot.os.path.exists', return_value=False):
            result = take_screenshot(self.test_file)
        
        # Assert
        self.assertFalse(result)
        mock_system.assert_called_once()
    
    def test_image_to_base64(self):
        """Test converting image to base64."""
        # Arrange
        with open(self.test_file, 'wb') as f:
            f.write(b'test image data')
        
        # Act
        with patch('builtins.open', unittest.mock.mock_open(read_data=b'test image data')):
            result = image_to_base64(self.test_file)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        self.assertEqual(result, "dGVzdCBpbWFnZSBkYXRh")  # 'test image data' in base64
    
    @patch('cv2.VideoCapture')
    @patch('cv2.imwrite')
    def test_capture_camera_image(self, mock_imwrite, mock_video_capture):
        """Test camera capture functionality."""
        # Arrange
        mock_cap = MagicMock()
        mock_video_capture.return_value = mock_cap
        
        # Setup mock camera to return a test frame
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)  # Black image
        mock_cap.read.return_value = (True, test_frame)
        mock_cap.isOpened.return_value = True
        
        mock_imwrite.return_value = True
        
        # Act
        result = capture_camera_image(self.test_file)
        
        # Assert
        self.assertTrue(result)
        mock_video_capture.assert_called_once_with(0)
        mock_cap.read.assert_called_once()
        mock_imwrite.assert_called_once_with(self.test_file, test_frame)
        mock_cap.release.assert_called_once()
    
    @patch('cv2.VideoCapture')
    def test_capture_camera_image_device_not_available(self, mock_video_capture):
        """Test camera not available handling."""
        # Arrange
        mock_cap = MagicMock()
        mock_video_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = False
        
        # Act & Assert
        result = capture_camera_image(self.test_file)
        
        # Assert
        self.assertFalse(result)
        mock_video_capture.assert_called_once_with(0)
        mock_cap.release.assert_not_called()  # Should not be called if isOpened fails
    
    @patch('cv2.VideoCapture')
    def test_capture_camera_image_read_failure(self, mock_video_capture):
        """Test camera read failure handling."""
        # Arrange
        mock_cap = MagicMock()
        mock_video_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)  # read() failure
        
        # Act
        result = capture_camera_image(self.test_file)
        
        # Assert
        self.assertFalse(result)
        mock_video_capture.assert_called_once_with(0)
        mock_cap.read.assert_called_once()
        mock_cap.release.assert_called_once()

if __name__ == "__main__":
    unittest.main() 