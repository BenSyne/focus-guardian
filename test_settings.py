import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import json

from settings import Settings, create_default_settings

class TestSettings(unittest.TestCase):
    def test_default_settings_creation(self):
        # Test that the default settings have the expected values
        default_settings = create_default_settings()
        
        # Check all expected keys exist
        self.assertIn('openai_api_key', default_settings)
        self.assertIn('cycle_duration', default_settings)
        self.assertIn('break_duration', default_settings)
        self.assertIn('check_interval', default_settings)
        self.assertIn('theme', default_settings)
        self.assertIn('sound_enabled', default_settings)
        self.assertIn('notification_enabled', default_settings)
        
        # Check default values
        self.assertEqual(default_settings['cycle_duration'], 25)
        self.assertEqual(default_settings['break_duration'], 5)
        self.assertEqual(default_settings['check_interval'], 5)
        self.assertEqual(default_settings['theme'], 'light')
        self.assertEqual(default_settings['sound_enabled'], True)
        self.assertEqual(default_settings['notification_enabled'], True)
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_settings_file_exists(self, mock_json_load, mock_file, mock_exists):
        # Setup
        mock_exists.return_value = True
        test_settings = {
            'openai_api_key': 'test_key',
            'cycle_duration': 30,
            'break_duration': 10,
            'check_interval': 3,
            'theme': 'dark',
            'sound_enabled': False,
            'notification_enabled': True
        }
        mock_json_load.return_value = test_settings
        
        # Execute
        settings = Settings()
        settings.load_settings()
        
        # Assert
        mock_exists.assert_called_once_with('settings.json')
        mock_file.assert_called_once_with('settings.json', 'r')
        mock_json_load.assert_called_once()
        
        self.assertEqual(settings.settings, test_settings)
        self.assertEqual(settings.get('openai_api_key'), 'test_key')
        self.assertEqual(settings.get('cycle_duration'), 30)
        self.assertEqual(settings.get('theme'), 'dark')
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_load_settings_file_doesnt_exist(self, mock_json_dump, mock_file, mock_exists):
        # Setup
        mock_exists.return_value = False
        
        # Execute
        settings = Settings()
        settings.load_settings()
        
        # Assert
        mock_exists.assert_called_once_with('settings.json')
        mock_file.assert_called_once_with('settings.json', 'w')
        mock_json_dump.assert_called_once()
        
        # Check default settings were created
        default_settings = create_default_settings()
        self.assertEqual(settings.settings, default_settings)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_settings(self, mock_json_dump, mock_file):
        # Setup
        test_settings = {
            'openai_api_key': 'test_key',
            'cycle_duration': 30,
            'break_duration': 10,
            'check_interval': 3,
            'theme': 'dark',
            'sound_enabled': False,
            'notification_enabled': True
        }
        
        # Execute
        settings = Settings()
        settings.settings = test_settings
        settings.save_settings()
        
        # Assert
        mock_file.assert_called_once_with('settings.json', 'w')
        mock_json_dump.assert_called_once_with(test_settings, mock_file(), indent=4)
    
    def test_get_setting(self):
        # Setup
        settings = Settings()
        settings.settings = {
            'openai_api_key': 'test_key',
            'cycle_duration': 30
        }
        
        # Execute & Assert
        self.assertEqual(settings.get('openai_api_key'), 'test_key')
        self.assertEqual(settings.get('cycle_duration'), 30)
        self.assertIsNone(settings.get('nonexistent_key'))
        self.assertEqual(settings.get('nonexistent_key', 'default_value'), 'default_value')
    
    def test_set_setting(self):
        # Setup
        settings = Settings()
        settings.settings = {'openai_api_key': 'old_key'}
        
        # Execute
        settings.set('openai_api_key', 'new_key')
        settings.set('new_setting', 'new_value')
        
        # Assert
        self.assertEqual(settings.settings['openai_api_key'], 'new_key')
        self.assertEqual(settings.settings['new_setting'], 'new_value')
    
    @patch.object(Settings, 'save_settings')
    def test_set_setting_with_save(self, mock_save):
        # Setup
        settings = Settings()
        settings.settings = {'theme': 'light'}
        
        # Execute
        settings.set('theme', 'dark', save=True)
        
        # Assert
        self.assertEqual(settings.settings['theme'], 'dark')
        mock_save.assert_called_once()
    
    def test_set_multiple_settings(self):
        # Setup
        settings = Settings()
        settings.settings = {
            'cycle_duration': 25,
            'break_duration': 5
        }
        
        # Execute
        settings.set_multiple({
            'cycle_duration': 30,
            'break_duration': 10,
            'new_setting': 'value'
        })
        
        # Assert
        self.assertEqual(settings.settings['cycle_duration'], 30)
        self.assertEqual(settings.settings['break_duration'], 10)
        self.assertEqual(settings.settings['new_setting'], 'value')
    
    @patch.object(Settings, 'save_settings')
    def test_set_multiple_settings_with_save(self, mock_save):
        # Setup
        settings = Settings()
        
        # Execute
        settings.set_multiple({
            'cycle_duration': 30,
            'break_duration': 10
        }, save=True)
        
        # Assert
        mock_save.assert_called_once()


if __name__ == '__main__':
    unittest.main() 