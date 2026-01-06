@echo off
python test_reminders_gemini.py > output.txt 2>&1
type output.txt
