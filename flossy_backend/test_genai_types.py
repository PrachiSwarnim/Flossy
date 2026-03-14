
import sys
import os

# Add the current directory to path
sys.path.append(os.getcwd())

try:
    from google.genai import types
    print("google.genai.types found")
    print(dir(types.Part))
except Exception as e:
    print(f"Error: {e}")
