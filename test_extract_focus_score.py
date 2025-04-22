import unittest
import logging
import sys
from unittest.mock import patch, MagicMock
import re

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    stream=sys.stdout)

class TestFocusScoreExtraction(unittest.TestCase):
    """Test the focus score extraction logic independent of the App class."""
    
    def extract_focus_score(self, response):
        """Focus score extraction logic copied from app.py"""
        lines = response.split('\n')
        # First try looking for "Focus Score: X.XX" or "Focus Score: XX%" pattern
        for line in lines:
            line = line.strip()
            if line.lower().startswith("focus score:"):
                try:
                    # Extract the number part
                    score_part = line.split(":", 1)[1].strip()
                    # Handle percentage format (XX%)
                    if "%" in score_part:
                        score_part = score_part.replace("%", "")
                        # Convert percentage to decimal (0-1)
                        score = float(score_part) / 100
                    else:
                        # Extract just the number part if there's additional text
                        number_match = re.search(r'(-?\d+(\.\d+)?)', score_part)
                        if number_match:
                            score = float(number_match.group(1))
                        else:
                            score = float(score_part)
                    # Ensure score is between 0 and 1
                    return max(0, min(1, score))
                except (ValueError, IndexError) as e:
                    logging.error(f"Error parsing focus score '{line}': {e}")
                    
        # If no score found, search for numerical values with context
        # Look for 'focus score' followed by various separators
        for line in lines:
            line = line.lower().strip()
            # Match "focus score" followed by various separators (-, =, etc.)
            if re.search(r'focus\s+score\s*[-:=]\s*', line):
                try:
                    # Extract the number using regex, allowing for negative numbers
                    number_match = re.search(r'[-:=]\s*(-?\d+(\.\d+)?)', line)
                    if number_match:
                        score = float(number_match.group(1))
                        # If score looks like a percentage (>1), convert to decimal
                        if score > 1:
                            score = score / 100
                        return max(0, min(1, score))
                except Exception as e:
                    logging.error(f"Error extracting focus score from '{line}': {e}")
            
            # Also try the general approach for lines with "focus" and "score"
            elif "focus" in line and "score" in line:
                try:
                    # Try to extract the number from this line with regex
                    # Include negative sign in regex
                    number_match = re.search(r'(-?\d+(\.\d+)?)', line)
                    if number_match:
                        score = float(number_match.group(1))
                        # If score looks like a percentage (>1), convert to decimal
                        if score > 1:
                            score = score / 100
                        return max(0, min(1, score))
                except Exception as e:
                    logging.error(f"Error extracting focus score from '{line}': {e}")
        
        # Log the raw response for debugging
        logging.warning("Could not extract focus score from response. Raw response:")
        logging.warning(response[:500])  # Log first 500 chars to avoid excessive log entries
        
        # If no score found, default to a neutral score
        return 0.5  # 50% (neutral) as fallback
    
    def test_extract_focus_score_standard_format(self):
        """Test extracting focus score from standard format."""
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
            score = self.extract_focus_score(response)
            self.assertEqual(score, expected, f"Failed for response: {response}")
    
    def test_extract_focus_score_non_standard_format(self):
        """Test extracting focus score from non-standard format."""
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
            score = self.extract_focus_score(response)
            self.assertEqual(score, expected, f"Failed for response: {response}")

if __name__ == "__main__":
    unittest.main() 