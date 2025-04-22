import unittest
import os
import json
import time
import tempfile
from unittest.mock import patch, MagicMock, Mock, PropertyMock
import tkinter as tk
from app import App, check_openai_version
from openai_api import OpenAI_API
from screenshot import take_screenshot, image_to_base64
from camera import capture_camera_image

class TestAppClass(unittest.TestCase):
    """Tests for the App class functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a more realistic tk mock with a tk attribute
        self.root = MagicMock(spec=tk.Tk)
        # Add a tk attribute to the mock
        type(self.root).tk = PropertyMock(return_value=MagicMock())
        
        # Patch ThemedStyle to avoid tkinter-related issues
        self.style_patcher = patch('app.ThemedStyle')
        self.mock_style = self.style_patcher.start()
        
        # Patch OpenAI_API to avoid actual API calls
        self.openai_patcher = patch('app.OpenAI_API')
        self.mock_openai = self.openai_patcher.start()
        
        # Mock client, API responses, etc.
        self.mock_client_instance = MagicMock()
        self.mock_openai.return_value = self.mock_client_instance
        
        # Create temp files for tests if needed
        self.temp_dir = tempfile.TemporaryDirectory()
    
    def tearDown(self):
        """Clean up after tests."""
        self.openai_patcher.stop()
        self.style_patcher.stop()
        self.temp_dir.cleanup()
    
    @patch('app.messagebox')
    def test_extract_focus_score_standard_format(self, mock_msgbox):
        """Test extracting focus score from standard format."""
        # Create app instance with multiple patches
        app = App(self.root)  # Should work now with the patched style
        
        # Test cases with different formats
        test_cases = [
            # Standard format
            ("Analysis complete.\nFocus Score: 0.85\nSuggestions:", 0.85),
            # Percentage format
            ("You're doing well.\nFocus Score: 75%\nKeep going!", 0.75),
            # Mixed format with extra text
            ("Focus Score: 0.5 (moderate focus)", 0.5),
            # Very high score (should be capped at 1.0)
            ("Focus Score: 1.2", 1.0),
            # Very low score (should be floored at 0.0)
            ("Focus Score: -0.1", 0.0),
        ]
        
        for response, expected in test_cases:
            score = app.extract_focus_score(response)
            self.assertEqual(score, expected, f"Failed for response: {response}")
    
    @patch('app.messagebox')
    def test_extract_focus_score_non_standard_format(self, mock_msgbox):
        """Test extracting focus score from non-standard format."""
        app = App(self.root)
        
        # Test cases with non-standard formats
        test_cases = [
            # Different spelling/capitalization
            ("focus score: 0.65", 0.65),
            # Different separator
            ("Focus Score - 0.9", 0.9),
            # Score embedded in text
            ("Your focus score is currently 0.78 out of 1.0", 0.78),
            # No valid score (should return 0.5 as neutral)
            ("No focus score present", 0.5),
        ]
        
        for response, expected in test_cases:
            score = app.extract_focus_score(response)
            self.assertEqual(score, expected, f"Failed for response: {response}")
    
    @patch('app.messagebox')
    def test_update_focus_stats(self, mock_msgbox):
        """Test updating focus statistics."""
        app = App(self.root)
            
        # Mock the focus_score_label
        app.focus_score_label = MagicMock()
        
        # Test updating stats with different scores
        test_scores = [0.85, 0.2, 0.5, 0.9]
        
        for score in test_scores:
            app.update_focus_stats(score)
        
        # Verify stats were updated correctly
        self.assertEqual(len(app.focus_scores), len(test_scores))
        self.assertEqual(app.focus_intervals, len(test_scores))
        self.assertAlmostEqual(app.total_focus_score, sum(test_scores))
        
        # Verify the label was updated (focus_score_label.config should be called)
        self.assertTrue(app.focus_score_label.config.called)
    
    @patch('app.messagebox')
    @patch('app.take_screenshot')
    @patch('app.capture_camera_image')
    @patch('asyncio.run_coroutine_threadsafe')
    def test_perform_task(self, mock_run_coroutine, mock_capture_camera, mock_take_screenshot, mock_msgbox):
        """Test the perform_task method."""
        app = App(self.root)
        
        # Mock dependencies
        app.loop = MagicMock()
        app.is_running = True
        app.is_paused = False
        app.current_session_id = "test_session"
        
        # Setup BooleanVar mocks
        app.use_screenshots_var = MagicMock()
        app.use_screenshots_var.get.return_value = True
        app.use_photos_var = MagicMock()
        app.use_photos_var.get.return_value = False
        
        app.client = MagicMock()
        app._perform_task_async = MagicMock()
        
        # Mock screenshot functions
        mock_take_screenshot.return_value = True
        
        # Mock future
        mock_future = MagicMock()
        mock_run_coroutine.return_value = mock_future
        
        # Call the method
        app.perform_task("Test task")
        
        # Verify screenshot was taken
        self.assertTrue(mock_take_screenshot.called)
        
        # Verify camera was not used (since it's disabled)
        self.assertFalse(mock_capture_camera.called)
        
        # Verify asyncio task was scheduled
        self.assertTrue(mock_run_coroutine.called)
        
        # Verify callback was added
        self.assertTrue(mock_future.add_done_callback.called)
    
    @patch('app.messagebox')
    def test_initialize_variables(self, mock_msgbox):
        """Test variable initialization."""
        app = App(self.root)
        
        # Reset all variables to ensure clean state
        app.initialize_variables()
        
        # Check default values
        self.assertEqual(app.cycle_count, 0)
        self.assertEqual(app.total_duration_seconds, 0)
        self.assertFalse(app.is_paused)
        self.assertFalse(app.is_reset)
        self.assertFalse(app.is_running)
        self.assertEqual(app.pomodoro_count, 0)
        self.assertEqual(app.current_phase, "Work")
        self.assertEqual(app.focus_scores, [])
        self.assertEqual(app.total_focus_score, 0)
        self.assertEqual(app.focus_intervals, 0)
        self.assertEqual(app.pause_time, 0)
        self.assertEqual(app.accumulated_pause_time, 0)
    
    def test_check_openai_version(self):
        """Test OpenAI package version checking."""
        # Mock pkg_resources.get_distribution
        with patch('pkg_resources.get_distribution') as mock_get_dist:
            # Test with old version
            mock_dist = Mock()
            mock_dist.version = "0.28.0"
            mock_get_dist.return_value = mock_dist
            
            is_ok, version = check_openai_version()
            self.assertFalse(is_ok)
            self.assertEqual(version, "0.28.0")
            
            # Test with new version
            mock_dist.version = "1.5.0"
            is_ok, version = check_openai_version()
            self.assertTrue(is_ok)
            self.assertEqual(version, "1.5.0")
            
            # Test with error
            mock_get_dist.side_effect = Exception("Package not found")
            is_ok, version = check_openai_version()
            self.assertFalse(is_ok)
            self.assertEqual(version, "unknown")
    
    @patch('app.messagebox')
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_save_and_load_session(self, mock_exists, mock_open, mock_msgbox):
        """Test session save and load functionality."""
        # Setup
        mock_exists.return_value = True
        
        # Create test session data
        test_sessions = [
            {
                'date': '2024-06-15 14:30:00',
                'duration': 30,
                'cycles': 1,
                'task': 'Test task 1',
                'focus_percentage': 75.5,
                'focus_scores': [70.0, 80.0, 76.5]
            },
            {
                'date': '2024-06-16 09:15:00',
                'duration': 45,
                'cycles': 2,
                'task': 'Test task 2',
                'focus_percentage': 85.0,
                'focus_scores': [85.0, 85.0]
            }
        ]
        
        # Configure mock open
        mock_file_handle = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file_handle
        mock_file_handle.read.return_value = json.dumps(test_sessions)
        
        # Create app and test load
        app = App(self.root)
        app.session_history = []  # Clear any existing history
        app.load_session_history()
        
        # Verify load
        self.assertEqual(len(app.session_history), 2)
        self.assertEqual(app.session_history[0]['task'], 'Test task 1')
        self.assertEqual(app.session_history[1]['focus_percentage'], 85.0)
    
    @patch('app.messagebox')
    @patch('threading.Thread')
    def test_start_and_pause_task(self, mock_thread, mock_msgbox):
        """Test starting and pausing a task."""
        app = App(self.root)
        
        # Setup mock UI components
        app.start_button = MagicMock()
        app.pause_button = MagicMock()
        app.reset_button = MagicMock()
        
        # Setup mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # Test start_task_thread
        app.start_task_thread()
        
        # Verify thread was created and started
        self.assertTrue(mock_thread.called)
        self.assertTrue(mock_thread_instance.start.called)
        
        # Verify button states updated
        self.assertEqual(app.start_button.config.call_args[1]['state'], "disabled")
        self.assertEqual(app.pause_button.config.call_args[1]['state'], "normal")
        self.assertEqual(app.reset_button.config.call_args[1]['state'], "normal")
            
        # Test pause_task
        app.is_running = True
        app.is_paused = False
        app.state_lock = MagicMock()
        app.state_lock.__enter__.return_value = None
        app.state_lock.__exit__.return_value = None
        
        # Call the method
        app.pause_task()
        
        # Verify button states
        # Since we mocked state_lock, is_paused won't be toggled automatically
        # So we need to simulate that manually
        app.is_paused = True # Simulate the lock setting is_paused = True
        app.pause_button.config.assert_called_with(text="Resume")
        
        # Test resume (pause again)
        app.pause_task()
        
        # Simulate pause toggle again
        app.is_paused = False # Simulate the lock setting is_paused = False
        app.pause_button.config.assert_called_with(text="Pause")

class TestOpenAIAPI(unittest.TestCase):
    @patch('openai_api.OpenAI')
    @patch('os.getenv')
    def test_init_with_valid_api_key(self, mock_getenv, mock_openai):
        # Setup
        mock_getenv.return_value = "test_api_key"
        
        # Execute
        api = OpenAI_API()
        
        # Assert
        self.assertIsNotNone(api.client)
        mock_openai.assert_called_once_with(api_key="test_api_key")
    
    @patch('os.getenv')
    def test_init_with_missing_api_key(self, mock_getenv):
        # Setup
        mock_getenv.return_value = None
        
        # Execute & Assert
        with self.assertRaises(ValueError):
            OpenAI_API()
    
    @patch('openai_api.OpenAI')
    @patch('os.getenv')
    @patch('openai_api.OpenAI_API.encode_image')
    def test_send_request(self, mock_encode, mock_getenv, mock_openai):
        # Setup
        mock_getenv.return_value = "test_api_key"
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_encode.return_value = "base64_encoded_image"
        
        # Create a mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Execute
        api = OpenAI_API()
        response = api.send_request("Test prompt", "test_screenshot.png", "test_camera.png")
        
        # Assert
        self.assertEqual(response, "Test response")
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)
        mock_encode.assert_any_call("test_screenshot.png")
        mock_encode.assert_any_call("test_camera.png")

    @patch('openai_api.OpenAI')
    @patch('os.getenv')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_image_data')
    @patch('base64.b64encode')
    def test_encode_image(self, mock_b64encode, mock_file, mock_getenv, mock_openai):
        # Setup
        mock_getenv.return_value = "test_api_key"
        mock_b64encode.return_value = b'base64_encoded_test_image'
        
        # Execute
        api = OpenAI_API()
        result = api.encode_image("test_image.png")
        
        # Assert
        mock_file.assert_called_once_with("test_image.png", "rb")
        mock_b64encode.assert_called_once_with(b'test_image_data')
        self.assertEqual(result, "base64_encoded_test_image")

class TestScreenshot(unittest.TestCase):
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('time.time')
    def test_take_screenshot_success(self, mock_time, mock_exists, mock_run):
        # Setup
        mock_time.side_effect = [0, 1]  # Start time, check time
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)
        
        # Execute
        result = take_screenshot("test_screenshot.png")
        
        # Assert
        self.assertTrue(result)
        mock_run.assert_called_once()
        mock_exists.assert_called_once_with("test_screenshot.png")
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_take_screenshot_failure(self, mock_exists, mock_run):
        # Setup
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=1)
        
        # Execute
        result = take_screenshot("test_screenshot.png")
        
        # Assert
        self.assertFalse(result)
        mock_run.assert_called_once()
    
    @patch('builtins.open', new_callable=mock_open, read_data=b'test_image_data')
    @patch('base64.b64encode')
    def test_image_to_base64(self, mock_b64encode, mock_file):
        # Setup
        mock_b64encode.return_value = b'base64_encoded_test_image'
        
        # Execute
        result = image_to_base64("test_image.png")
        
        # Assert
        mock_file.assert_called_once_with("test_image.png", "rb")
        mock_b64encode.assert_called_once_with(b'test_image_data')
        self.assertEqual(result, "base64_encoded_test_image")

class TestCamera(unittest.TestCase):
    @patch('cv2.VideoCapture')
    @patch('cv2.imwrite')
    @patch('time.sleep')
    def test_capture_camera_image_success(self, mock_sleep, mock_imwrite, mock_video_capture):
        # Setup
        mock_camera = MagicMock()
        mock_camera.isOpened.return_value = True
        mock_camera.read.return_value = (True, "mock_frame")
        mock_video_capture.return_value = mock_camera
        
        # Execute
        result = capture_camera_image("test_camera.png")
        
        # Assert
        self.assertTrue(result)
        mock_camera.isOpened.assert_called_once()
        mock_camera.read.assert_called_once()
        mock_imwrite.assert_called_once_with("test_camera.png", "mock_frame")
        mock_camera.release.assert_called_once()
    
    @patch('cv2.VideoCapture')
    def test_capture_camera_image_cannot_open(self, mock_video_capture):
        # Setup
        mock_camera = MagicMock()
        mock_camera.isOpened.return_value = False
        mock_video_capture.return_value = mock_camera
        
        # Execute
        result = capture_camera_image("test_camera.png")
        
        # Assert
        self.assertFalse(result)
        mock_camera.isOpened.assert_called_once()
    
    @patch('cv2.VideoCapture')
    def test_capture_camera_image_read_failure(self, mock_video_capture):
        # Setup
        mock_camera = MagicMock()
        mock_camera.isOpened.return_value = True
        mock_camera.read.return_value = (False, None)
        mock_video_capture.return_value = mock_camera
        
        # Execute
        result = capture_camera_image("test_camera.png")
        
        # Assert
        self.assertFalse(result)
        mock_camera.read.assert_called_once()
        mock_camera.release.assert_called_once()

class TestAppFunctions(unittest.TestCase):
    @patch('tkinter.Tk')
    def setUp(self, mock_tk):
        self.root = mock_tk.return_value
        self.app = App(self.root)
        # Mock the OpenAI client
        self.app.client = MagicMock()
    
    def test_extract_focus_score_percentage(self):
        # Test extracting score in percentage format
        response = "Focus analysis complete.\nFocus Score: 75%\nOther details..."
        score = self.app.extract_focus_score(response)
        self.assertEqual(score, 0.75)
    
    def test_extract_focus_score_decimal(self):
        # Test extracting score in decimal format
        response = "Focus analysis complete.\nFocus Score: 0.85\nOther details..."
        score = self.app.extract_focus_score(response)
        self.assertEqual(score, 0.85)
    
    def test_extract_focus_score_fallback(self):
        # Test fallback when no score is found
        response = "Some response without a focus score"
        score = self.app.extract_focus_score(response)
        self.assertEqual(score, 0.5)  # Default fallback
    
    def test_update_focus_stats(self):
        # Setup initial state
        self.app.focus_scores = []
        self.app.total_focus_score = 0
        self.app.focus_intervals = 0
        self.app.focus_score_label = MagicMock()
        
        # Execute
        self.app.update_focus_stats(0.75)
        
        # Assert
        self.assertEqual(self.app.focus_scores, [0.75])
        self.assertEqual(self.app.total_focus_score, 0.75)
        self.assertEqual(self.app.focus_intervals, 1)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_session(self, mock_json_dump, mock_open_file):
        # Setup
        self.app.focus_scores = [0.75, 0.80, 0.85]
        self.app.total_focus_score = 2.4
        self.app.focus_intervals = 3
        self.app.total_duration_seconds = 1800  # 30 minutes
        self.app.cycle_count = 2
        self.app.task_text = MagicMock()
        self.app.task_text.get.return_value = "Test task"
        self.app.session_history = []
        self.app.show_focus_report = MagicMock()
        
        # Execute
        self.app.save_session()
        
        # Assert
        self.assertEqual(len(self.app.session_history), 1)
        session = self.app.session_history[0]
        self.assertEqual(session['duration'], 30)
        self.assertEqual(session['cycles'], 2)
        self.assertEqual(session['task'], "Test task")
        self.assertEqual(session['focus_percentage'], 80.0)  # (0.75+0.80+0.85)/3 * 100
        self.assertEqual(session['focus_scores'], [75.0, 80.0, 85.0])
        
        mock_open_file.assert_called_once_with('session_history.json', 'w')
        mock_json_dump.assert_called_once()
        self.app.show_focus_report.assert_called_once_with(80.0)
    
    @patch('os.path.exists')
    @patch('os.remove')
    def test_clean_up_files(self, mock_remove, mock_exists):
        # Setup
        mock_exists.return_value = True
        self.app.temp_files = {"test_screenshot.png", "test_camera.png"}
        
        # Execute
        self.app.clean_up_files("test_screenshot.png", "test_camera.png")
        
        # Assert
        self.assertEqual(mock_remove.call_count, 2)
        self.assertEqual(len(self.app.temp_files), 0)
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='[]')
    @patch('json.load')
    def test_load_session_history_empty(self, mock_json_load, mock_open_file, mock_exists):
        # Setup
        mock_exists.return_value = True
        mock_json_load.return_value = []
        
        # Execute
        self.app.load_session_history()
        
        # Assert
        self.assertEqual(self.app.session_history, [])
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_session_history_with_data(self, mock_json_load, mock_open_file, mock_exists):
        # Setup
        mock_exists.return_value = True
        test_history = [{'date': '2023-01-01', 'focus_percentage': 75.0}]
        mock_json_load.return_value = test_history
        
        # Execute
        self.app.load_session_history()
        
        # Assert
        self.assertEqual(self.app.session_history, test_history)

if __name__ == '__main__':
    unittest.main() 