import unittest
import time
from unittest.mock import patch, MagicMock, PropertyMock
import tkinter as tk
from app import App

class TestTimerFunctions(unittest.TestCase):
    """Tests for timer-related functions in the App class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock root with children dict to fix tkinter issues
        self.root = MagicMock(spec=tk.Tk)
        self.root.children = {}
        
        # Set up necessary attributes to avoid ttk.Frame issues
        self.root._w = "."
        self.root.tk = MagicMock()
        
        # Patch ThemedStyle to avoid tkinter-related issues
        self.style_patcher = patch('app.ThemedStyle')
        self.mock_style = self.style_patcher.start()
        
        # Patch OpenAI_API to avoid actual API calls
        self.openai_patcher = patch('app.OpenAI_API')
        self.mock_openai = self.openai_patcher.start()
        
        # Patch messagebox to avoid dialog boxes
        self.msgbox_patcher = patch('app.messagebox')
        self.mock_msgbox = self.msgbox_patcher.start()
        
        # Patch App.create_widgets to avoid UI creation
        self.widgets_patcher = patch('app.App.create_widgets')
        self.mock_widgets = self.widgets_patcher.start()
        
        # Create App instance with patches
        self.app = App(self.root)
        
        # Mock the required UI elements manually
        self.app.phase_label = MagicMock()
        self.app.timer_label = MagicMock()
        self.app.cycle_timer_label = MagicMock()
        self.app.progress_bar = MagicMock()
        self.app.start_button = MagicMock()
        self.app.pause_button = MagicMock()
        self.app.reset_button = MagicMock()
        self.app.pomo_count_label = MagicMock()
        
        # Mock interval and duration spinboxes
        self.app.interval_spinbox = MagicMock()
        self.app.interval_spinbox.get.return_value = "5"
        
        self.app.duration_spinbox = MagicMock()
        self.app.duration_spinbox.get.return_value = "30"
        
        # Mock interval unit
        self.app.interval_unit = MagicMock()
        self.app.interval_unit.get.return_value = "minutes"
        
        # Mock mode
        self.app.mode = MagicMock()
        self.app.mode.get.return_value = "regular"
        
        # Add state_lock
        self.app.state_lock = MagicMock()
        self.app.state_lock.__enter__.return_value = None
        self.app.state_lock.__exit__.return_value = None
        
        # Setup threading
        self.threading_patcher = patch('app.threading.Thread')
        self.mock_thread = self.threading_patcher.start()
        
        # Setup perform_task
        self.app.perform_task = MagicMock()
        
        # Setup update_pomodoro_count_label
        self.app.update_pomodoro_count_label = MagicMock()
    
    def tearDown(self):
        """Clean up after tests."""
        self.openai_patcher.stop()
        self.style_patcher.stop()
        self.msgbox_patcher.stop()
        self.threading_patcher.stop()
        self.widgets_patcher.stop()
    
    @patch('time.time')
    @patch('time.sleep')
    def test_run_timer_basic(self, mock_sleep, mock_time):
        """Test basic timer functionality."""
        # Set up mock time to advance 1 second per call
        mock_time.side_effect = [100, 101, 102, 103, 104, 105, 106]
        
        # Initialize app state
        self.app.is_reset = False
        self.app.is_paused = False
        self.app.accumulated_pause_time = 0
        
        # Run a 5-second timer
        self.app.run_timer(5, "Test Phase")
        
        # Verify phase label was updated
        self.app.root.after.assert_any_call(0, unittest.mock.ANY)
        
        # Verify sleep was called (for yielding)
        self.assertTrue(mock_sleep.called)
    
    @patch('time.time')
    @patch('time.sleep')
    def test_run_timer_pause_and_resume(self, mock_sleep, mock_time):
        """Test pausing and resuming a timer."""
        # Set up mock time to advance normally
        mock_time.side_effect = [100, 101, 102, 103, 104, 105, 106]
        
        # Initialize app state
        self.app.is_reset = False
        self.app.is_paused = False
        self.app.accumulated_pause_time = 0
        
        # Setup a side effect to pause after 2 calls, then resume after 2 more
        pause_count = [0]  # Use a list for mutable reference
        
        def pause_side_effect(*args, **kwargs):
            pause_count[0] += 1
            if pause_count[0] == 2:
                self.app.is_paused = True
            elif pause_count[0] == 4:
                self.app.is_paused = False
                self.app.accumulated_pause_time = 2  # Simulate 2 seconds paused
            return None
        
        # Apply the side effect
        mock_sleep.side_effect = pause_side_effect
        
        # Run a 5-second timer
        self.app.run_timer(5, "Test Phase")
        
        # Verify sleep was called multiple times
        self.assertGreater(mock_sleep.call_count, 4)
    
    @patch('time.time')
    @patch('time.sleep')
    def test_run_timer_reset(self, mock_sleep, mock_time):
        """Test resetting a timer."""
        # Set up mock time to advance normally
        mock_time.side_effect = [100, 101, 102, 103, 104, 105]
        
        # Initialize app state
        self.app.is_reset = False
        self.app.is_paused = False
        self.app.accumulated_pause_time = 0
        
        # Setup a side effect to reset after 2 calls
        reset_count = [0]  # Use a list for mutable reference
        
        def reset_side_effect(*args, **kwargs):
            reset_count[0] += 1
            if reset_count[0] == 2:
                self.app.is_reset = True
            return None
        
        # Apply the side effect
        mock_sleep.side_effect = reset_side_effect
        
        # Run a 5-second timer
        self.app.run_timer(5, "Test Phase")
        
        # Verify that the timer stopped after reset
        self.assertEqual(mock_sleep.call_count, 2)
    
    @patch('app.App.run_timer')
    def test_run_regular_cycle(self, mock_run_timer):
        """Test running a regular cycle."""
        # Setup
        self.app.is_reset = False
        self.app.is_paused = False
        
        # Mock time.time() to return advancing values
        with patch('time.time') as mock_time:
            mock_time.side_effect = [100, 110, 120, 130]  # Start time + checks
            
            # Execute
            self.app.run_regular_cycle("Test task")
            
            # Verify
            mock_run_timer.assert_called_once()
            self.assertEqual(self.app.total_duration_seconds, 30 * 60)  # 30 minutes
    
    @patch('app.App.run_timer')
    def test_run_pomodoro_cycle(self, mock_run_timer):
        """Test running a pomodoro cycle."""
        # Setup
        self.app.is_reset = False
        self.app.is_paused = False
        self.app.pomodoro_count = 0
        
        # Execute - with reset after first pomodoro
        with patch.object(type(self.app), 'is_reset', new_callable=PropertyMock) as mock_is_reset:
            # Not reset initially, then reset after first work period
            mock_is_reset.side_effect = [False, False, True]
            self.app.run_pomodoro_cycle("Test task")
        
        # Verify timer was called
        mock_run_timer.assert_called_once_with(25 * 60, "Work", "Test task")
        self.assertEqual(self.app.pomodoro_count, 0)  # Should not increment since we reset
        
        # Reset mocks
        mock_run_timer.reset_mock()
        
        # Execute - full cycle
        self.app.is_reset = False
        with patch.object(type(self.app), 'is_reset', new_callable=PropertyMock) as mock_is_reset:
            # Never reset during the entire cycle
            mock_is_reset.side_effect = [False] * 20
            self.app.run_pomodoro_cycle("Test task")
        
        # Verify timer was called multiple times
        self.assertGreater(mock_run_timer.call_count, 1)
        self.assertEqual(self.app.pomodoro_count, 1)  # Should increment after completing a full cycle

if __name__ == "__main__":
    unittest.main() 