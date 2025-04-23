# Guide to Creating a Head-Tracking Audio Balance System for iMac

## Overview
This guide will help you create an application that uses your iMac's camera to track your head position and dynamically adjust the audio balance to create a "sweet spot" that follows you as you move.

## Step 1: Setting Up Your Development Environment

First, you'll need to install the necessary development tools:

1. Install Xcode from the Mac App Store (this provides the development environment)
2. Install Homebrew (a package manager) by opening Terminal and running:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Install Python using Homebrew:
   ```
   brew install python
   ```
4. Install necessary Python packages:
   ```
   pip3 install opencv-python numpy pyobjc
   ```

## Step 2: Creating the Application

Create a new Python script named `head_track_audio.py` with the following code:

```python
import cv2
import numpy as np
import time
import subprocess
import sys
from threading import Thread

# Import macOS-specific modules
from AppKit import NSSound, NSApplication, NSApp
from Foundation import NSObject, NSLog

class HeadTrackingAudioBalancer:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.cap = cv2.VideoCapture(0)
        self.running = True
        self.last_balance_update = time.time()
        self.update_frequency = 0.2  # seconds between balance updates
        self.screen_center_x = None  # Will be set when video capture starts
        
    def get_screen_dimensions(self):
        # Get screen width from system_profiler
        try:
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'], 
                capture_output=True, 
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'Resolution' in line:
                    # Extract resolution from line like "Resolution: 1920 x 1080"
                    parts = line.split(':')[1].strip().split(' x ')
                    if len(parts) == 2:
                        return int(parts[0]), int(parts[1])
        except Exception as e:
            print(f"Error getting screen dimensions: {e}")
        
        # Fallback to standard iMac dimensions if we can't detect them
        return 1920, 1080

    def calculate_audio_balance(self, face_x, frame_width):
        # Convert face position to audio balance value (-1.0 to 1.0)
        # Where -1.0 is full left, 0.0 is center, and 1.0 is full right
        center_position = frame_width / 2
        
        # Calculate how far off-center the face is
        offset = face_x - center_position
        
        # Convert to a -1 to 1 range (normalized by half the frame width)
        balance = offset / (center_position * 0.8)  # Using 0.8 to make it less sensitive
        
        # Clamp the value to stay within -1 to 1
        balance = max(-1.0, min(1.0, balance))
        
        # Invert the balance since we want sound to be stronger on the side the user is on
        return -balance

    def set_audio_balance(self, balance):
        # AppleScript to set the audio balance
        # Balance ranges from -1.0 (full left) to 1.0 (full right)
        balance_percentage = int((balance + 1) * 50)  # Convert to 0-100 scale
        
        applescript = f'''
        tell application "System Events"
            tell application process "SystemUIServer"
                set theVolume to first slider of group 1 of menu bar item 1 of menu bar 1
                tell theVolume
                    set balance to {balance_percentage}
                end tell
            end tell
        end tell
        '''
        
        try:
            subprocess.run(['osascript', '-e', applescript], capture_output=True)
        except Exception as e:
            print(f"Error setting audio balance: {e}")

    def track_head(self):
        if not self.cap.isOpened():
            print("Error: Could not open camera.")
            return

        # Get the first frame to determine dimensions
        ret, frame = self.cap.read()
        if not ret:
            print("Error: Could not read from camera.")
            return
        
        frame_height, frame_width = frame.shape[:2]
        screen_width, screen_height = self.get_screen_dimensions()
        self.screen_center_x = screen_width / 2
        
        print(f"Camera resolution: {frame_width}x{frame_height}")
        print(f"Screen resolution: {screen_width}x{screen_height}")
        print("Head tracking started. Press 'q' to quit.")

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Could not read frame.")
                break

            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Process the largest face if any are detected
            if len(faces) > 0:
                # Find the largest face
                largest_face = max(faces, key=lambda x: x[2] * x[3])
                x, y, w, h = largest_face
                
                # Draw rectangle around the face for visual feedback
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # Calculate face center position
                face_center_x = x + w // 2
                
                # Update audio balance (not too frequently)
                current_time = time.time()
                if current_time - self.last_balance_update > self.update_frequency:
                    balance = self.calculate_audio_balance(face_center_x, frame_width)
                    self.set_audio_balance(balance)
                    self.last_balance_update = current_time
                    print(f"Face position: {face_center_x}, Audio balance: {balance:.2f}")
            
            # Display the frame with face detection
            cv2.imshow('Head Tracking Audio Balancer', frame)
            
            # Check for quit key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        
        # Reset audio balance to center
        self.set_audio_balance(0)
        print("Head tracking stopped. Audio balance reset to center.")

    def start(self):
        tracking_thread = Thread(target=self.track_head)
        tracking_thread.start()
        return tracking_thread

if __name__ == "__main__":
    balancer = HeadTrackingAudioBalancer()
    thread = balancer.start()
    
    # Keep the main thread running
    try:
        while thread.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping head tracking...")
        balancer.running = False
        thread.join()
```

## Step 3: Creating a Simple macOS Application Wrapper

To make this easier to launch, let's create a simple macOS application wrapper:

1. Open "Script Editor" (found in Applications > Utilities)
2. Paste the following AppleScript:
   ```applescript
   -- HeadTrackAudio Launcher
   
   on run
      set pythonScript to (path to home folder as text) & "head_track_audio.py"
      do shell script "python3 " & quoted form of POSIX path of pythonScript
   end run
   ```
3. Save as an application: File > Export > File Format: Application
4. Name it "HeadTrackAudio" and save to Applications folder

## Step 4: System Permissions

For this to work properly, you'll need to grant permissions:

1. Camera access: The first time you run the app, macOS will ask for camera permission
2. Accessibility access: Go to System Preferences > Security & Privacy > Privacy > Accessibility and add your new application

## Step 5: Running the Application

1. Launch the "HeadTrackAudio" application you created
2. The camera will activate and begin tracking your face
3. Move your head left and right to experience the audio balance changing
4. Press 'q' on the keyboard while the tracking window is active to quit

## How It Works

This application uses:
- OpenCV for face detection through your iMac camera
- PyObjC for macOS integration
- AppleScript to adjust system audio balance
- A threading approach to keep the UI responsive

## Customization Options

You can modify the code to:
- Adjust sensitivity of the balance change by modifying the '0.8' value in the calculate_audio_balance function
- Change update frequency by modifying the 'update_frequency' variable
- Improve face detection by trying different OpenCV detection parameters

## Troubleshooting

If you encounter issues:
- Make sure camera permissions are granted
- Check if AppleScript has the necessary permissions to control system settings
- Verify that all required packages are installed
