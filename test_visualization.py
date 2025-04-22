import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import tkinter as tk
from app import App
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for testing
import json
from datetime import datetime

class TestVisualization(unittest.TestCase):
    """Tests for visualization-related methods in the App class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a proper mock root to fix tkinter issues
        self.root = MagicMock(spec=tk.Tk)
        self.root.children = {}
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
        
        # Patch FigureCanvasTkAgg
        self.canvas_patcher = patch('app.FigureCanvasTkAgg')
        self.mock_canvas = self.canvas_patcher.start()
        
        # Patch Toplevel windows
        self.toplevel_patcher = patch('tkinter.Toplevel')
        self.mock_toplevel = self.toplevel_patcher.start()
        
        # Create App instance with patches
        self.app = App(self.root)
        
        # Mock session history
        self.app.session_history = [
            {
                'date': '2023-06-15 14:30:00',
                'duration': 30,
                'cycles': 1,
                'task': 'Test task 1',
                'focus_percentage': 75.5,
                'focus_scores': [70.0, 80.0, 76.5]
            },
            {
                'date': '2023-06-16 09:15:00',
                'duration': 45,
                'cycles': 2,
                'task': 'Test task 2',
                'focus_percentage': 85.0,
                'focus_scores': [85.0, 85.0]
            }
        ]
        
        # Set up other required attributes
        self.app.total_duration_seconds = 1800
        self.app.focus_intervals = 3
        self.app.task_text = MagicMock()
        self.app.task_text.get.return_value = "Test task"
    
    def tearDown(self):
        """Clean up after tests."""
        self.openai_patcher.stop()
        self.style_patcher.stop()
        self.msgbox_patcher.stop()
        self.canvas_patcher.stop()
        self.toplevel_patcher.stop()
        self.widgets_patcher.stop()
    
    @patch('app.plt.figure')
    @patch('app.plt.subplot2grid')
    def test_plot_focus_history(self, mock_subplot, mock_figure):
        """Test the plot_focus_history method."""
        # Set up
        parent = MagicMock()
        mock_ax = MagicMock()
        mock_subplot.return_value = mock_ax
        
        # Execute
        self.app.plot_focus_history(parent)
        
        # Verify
        mock_figure.assert_called_once()
        self.mock_canvas.assert_called_once()
    
    @patch('app.plt.figure')
    def test_plot_focus_history_empty(self, mock_figure):
        """Test plotting with empty history."""
        # Set up
        parent = MagicMock()
        self.app.session_history = []
        
        # Execute
        self.app.plot_focus_history(parent)
        
        # Verify
        mock_figure.assert_not_called()
    
    @patch('app.ttk.Frame')
    @patch('app.ttk.Label')
    def test_show_focus_report_good_score(self, mock_label, mock_frame):
        """Test the focus report with a good score."""
        # Execute
        self.app.show_focus_report(85.0)
        
        # Verify
        self.mock_toplevel.assert_called_once()
        
        # Get the mock window instance
        window = self.mock_toplevel.return_value
        
        # Window should have been configured
        window.title.assert_called_once_with("Session Report")
        window.geometry.assert_called_once()
        window.configure.assert_called_once()
    
    @patch('app.ttk.Frame')
    @patch('app.ttk.Label')
    def test_show_focus_report_poor_score(self, mock_label, mock_frame):
        """Test the focus report with a poor score."""
        # Execute
        self.app.show_focus_report(40.0)
        
        # Verify
        self.mock_toplevel.assert_called_once()
    
    @patch('json.dump')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_save_session(self, mock_open, mock_json_dump):
        """Test the save_session method."""
        # Set up
        self.app.focus_scores = [0.75, 0.8, 0.9]
        self.app.total_focus_score = 2.45
        self.app.focus_intervals = 3
        self.app.show_focus_report = MagicMock()
        
        # Execute
        self.app.save_session()
        
        # Verify
        mock_open.assert_called_once_with('session_history.json', 'w')
        mock_json_dump.assert_called_once()
        self.app.show_focus_report.assert_called_once()
        
        # Verify session data
        session = self.app.session_history[-1]
        self.assertEqual(session['duration'], 30)  # 1800 seconds / 60
        self.assertEqual(round(session['focus_percentage']), 82)  # 2.45/3 * 100
        self.assertEqual(len(session['focus_scores']), 3)
    
    @patch('app.ttk.Scrollbar')
    @patch('app.tk.Canvas')
    def test_show_history(self, mock_canvas, mock_scrollbar):
        """Test the show_history method."""
        # Set up mock canvas
        canvas_instance = MagicMock()
        mock_canvas.return_value = canvas_instance
        
        # Make canvas_widget mock available for FigureCanvasTkAgg
        canvas_widget_mock = MagicMock()
        self.mock_canvas.return_value.get_tk_widget.return_value = canvas_widget_mock
        
        # Execute
        self.app.show_history()
        
        # Verify
        self.mock_toplevel.assert_called_once()
        
        # Get the mock window instance
        window = self.mock_toplevel.return_value
        
        # Window should have been configured
        window.title.assert_called_once_with("Focus History")
        window.geometry.assert_called_once()
        window.configure.assert_called_once()

if __name__ == "__main__":
    unittest.main() 