#!/usr/bin/env python
import sys
try:
    from livekit.agents import voice
    print("=== livekit.agents.voice contents ===")
    for item in dir(voice):
        if not item.startswith('_'):
            print(f"  - {item}")
    
    # Try to find any class that might work
    for item in dir(voice):
        obj = getattr(voice, item)
        if isinstance(obj, type) and 'assistant' in item.lower():
            print(f"\nFound Assistant-like class: {item}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
