"""
Configuration for pytest that ensures the root directory is in the Python path.
This allows imports from the 'common' module to work correctly in tests.
"""
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))