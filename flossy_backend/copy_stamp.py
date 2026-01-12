import shutil
import os

src = r"C:\Users\Prachi Swarnim\.gemini\antigravity\brain\b712e96c-e54c-44db-b33e-74cc29ac4132\uploaded_image_0_1767950674098.png"
dst = r"c:\Users\Prachi Swarnim\Desktop\Flossy\flossy-ui\public\static\assets\blue_stamp.png"

try:
    shutil.copy2(src, dst)
    print(f"Successfully copied to {dst}")
except Exception as e:
    print(f"Error copying file: {e}")
