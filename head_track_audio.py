import cv2
import numpy as np
import time
import subprocess
import sys
import select
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
        self.show_preview = True  # Toggle this to enable/disable video preview
        
        # Calibration parameters
        self.calibrated = False
        self.calibration_center_x = None  # This will be the sweet spot position
        self.sensitivity = 0.8  # Adjust this to change how quickly balance changes with movement
        self.original_system_balance = None
        
        # Audio balance mode
        self.use_eqmac = True  # Set to True to use eqMac, False to use system audio
        
        # Last detected face position
        self.last_face_position = None
        
        # Cartoon filter parameters
        self.use_cartoon_filter = True
        
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
                        try:
                            return int(parts[0]), int(parts[1])
                        except ValueError:
                            # Try to handle more complex formats
                            pass
        except Exception as e:
            print(f"Error getting screen dimensions: {e}")
        
        # Fallback to standard iMac dimensions if we can't detect them
        return 1920, 1080

    def get_current_system_balance(self):
        """Get the current system audio balance setting (0-100)"""
        if self.use_eqmac:
            # For eqMac we will just assume 50 (center) as default
            # since we don't have a direct way to query eqMac's balance via script
            return 50
            
        # System audio balance via AppleScript
        applescript = '''
        tell application "System Events"
            tell application process "SystemUIServer"
                set theVolume to first slider of group 1 of menu bar item 1 of menu bar 1
                tell theVolume
                    return the value of the attribute "AXValue"
                end tell
            end tell
        end tell
        '''
        
        try:
            result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
            balance = int(result.stdout.strip())
            return balance
        except Exception as e:
            print(f"Error getting system balance: {e}")
            return 50  # Default to center

    def calculate_audio_balance(self, face_x, frame_width):
        # If calibrated, use the calibration position as the center
        if self.calibrated and self.calibration_center_x is not None:
            center_position = self.calibration_center_x
        else:
            center_position = frame_width / 2
        
        # Calculate how far off-center the face is
        offset = face_x - center_position
        
        # Convert to a -1 to 1 range (normalized by half the frame width)
        balance = offset / (center_position * self.sensitivity)
        
        # Clamp the value to stay within -1 to 1
        balance = max(-1.0, min(1.0, balance))
        
        # Invert the balance since we want sound to be stronger on the side the user is on
        return -balance

    def set_audio_balance(self, balance):
        # Balance ranges from -1.0 (full left) to 1.0 (full right)
        balance_percentage = int((balance + 1) * 50)  # Convert to 0-100 scale
        
        if self.use_eqmac:
            self.set_eqmac_balance(balance_percentage)
        else:
            self.set_system_balance(balance_percentage)

    def set_system_balance(self, balance_percentage):
        """Set system audio balance via AppleScript (0-100)"""
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
            print(f"Error setting system audio balance: {e}")

    def set_eqmac_balance(self, balance_percentage):
        """Set eqMac audio balance via AppleScript (0-100)"""
        # Adjust this AppleScript to match eqMac's UI or API
        # This is a placeholder and needs to be customized for eqMac
        applescript = f'''
        tell application "System Events"
            if exists process "eqMac" then
                tell process "eqMac"
                    # This is a placeholder - you need to adjust this for eqMac's actual UI elements
                    # Below is pseudo-code for demonstration
                    set frontmost to true
                    delay 0.2
                    # Access eqMac's balance slider and set it
                    # For example:
                    # click menu item "Balance" of menu "Controls" of menu bar 1
                    # set value of slider 1 of window 1 to {balance_percentage}
                end tell
            end if
        end tell
        '''
        
        # For testing, print what we would set the balance to
        print(f"Would set eqMac balance to: {balance_percentage}")
        
        # IMPORTANT: This is a placeholder. You need to customize this for eqMac.
        # Since we can't know exactly how to script eqMac without more details,
        # you'll need to adjust this based on your knowledge of eqMac's interface
        # or simply use the eqMac GUI manually for now.
        
        # Once you have the correct AppleScript for eqMac, uncomment this:
        # try:
        #     subprocess.run(['osascript', '-e', applescript], capture_output=True)
        # except Exception as e:
        #     print(f"Error setting eqMac balance: {e}")

    def calibrate(self, face_x=None):
        """Store the current face position as the calibration center"""
        if face_x is None:
            if self.last_face_position is not None:
                face_x = self.last_face_position
            else:
                print("Cannot calibrate: No face detected yet")
                return
                
        self.calibration_center_x = face_x
        self.calibrated = True
        print(f"Calibrated: Sweet spot set at position {face_x}")
        
        # Store the original system balance in case we want to restore it later
        self.original_system_balance = self.get_current_system_balance()

    def adjust_sensitivity(self, increment=0.1):
        """Adjust the sensitivity of the head tracking"""
        self.sensitivity = max(0.2, min(2.0, self.sensitivity + increment))
        if self.sensitivity > 1.9 and increment > 0:
            self.sensitivity = 0.2  # Loop back to lowest setting
        print(f"Sensitivity adjusted to {self.sensitivity:.1f}")

    def toggle_audio_mode(self):
        """Toggle between eqMac and system audio"""
        self.use_eqmac = not self.use_eqmac
        print(f"Audio balance mode switched to: {'eqMac' if self.use_eqmac else 'System Audio'}")
        
    def toggle_cartoon_filter(self):
        """Toggle cartoon filter on/off"""
        self.use_cartoon_filter = not self.use_cartoon_filter
        print(f"Cartoon filter: {'ON' if self.use_cartoon_filter else 'OFF'}")
        
    def apply_cartoon_effect(self, img):
        """Apply a cartoon-like effect to the image"""
        # Convert image to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply median blur
        gray = cv2.medianBlur(gray, 5)
        
        # Detect edges
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                     cv2.THRESH_BINARY, 9, 9)
        
        # Convert back to color for bilateral filter
        color = cv2.bilateralFilter(img, 9, 300, 300)
        
        # Combine edges with color image
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        
        return cartoon

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
        print(f"Audio balance mode: {'eqMac' if self.use_eqmac else 'System Audio'}")
        print("Head tracking started. Press Ctrl+C to quit.")
        print("COMMANDS:")
        print("  Type 'c' and press Enter to calibrate the current position as the sweet spot")
        print("  Type 's' and press Enter to increase sensitivity (currently {:.1f})".format(self.sensitivity))
        print("  Type 'm' and press Enter to toggle between eqMac and system audio")
        print("  Type 'f' and press Enter to toggle cartoon filter")
        print("  Type 'q' and press Enter to quit")

        # Start a separate thread to handle terminal input
        input_thread = Thread(target=self.handle_terminal_input)
        input_thread.daemon = True
        input_thread.start()

        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Could not read frame.")
                    break

                # Process frame with cartoon filter if enabled
                if self.use_cartoon_filter:
                    try:
                        # Apply cartoon effect to the full frame
                        frame = self.apply_cartoon_effect(frame)
                    except Exception as e:
                        print(f"Error applying cartoon filter: {e}")

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
                    
                    # Calculate face center position
                    face_center_x = x + w // 2
                    self.last_face_position = face_center_x
                    
                    # Update audio balance (not too frequently)
                    current_time = time.time()
                    if current_time - self.last_balance_update > self.update_frequency:
                        balance = self.calculate_audio_balance(face_center_x, frame_width)
                        self.set_audio_balance(balance)
                        self.last_balance_update = current_time
                        
                        calibration_status = "CALIBRATED" if self.calibrated else "Not calibrated"
                        audio_mode = "eqMac" if self.use_eqmac else "System"
                        print(f"Face position: {face_center_x}, Balance: {balance:.2f} [{calibration_status}] [{audio_mode}]")
                
                # Try to display the frame with face detection, but continue if it fails
                if self.show_preview:
                    try:
                        # Draw rectangle around the face for visual feedback
                        if len(faces) > 0:
                            x, y, w, h = largest_face
                            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                            
                            # Add a fun emoji or text near the face
                            emoji = "😎" if self.calibrated else "🔍"
                            cv2.putText(frame, emoji, (x + w//2 - 20, y - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                            
                            # Show the calibration center if calibrated
                            if self.calibrated and self.calibration_center_x is not None:
                                cv2.line(frame, 
                                       (self.calibration_center_x, 0), 
                                       (self.calibration_center_x, frame_height), 
                                       (0, 255, 0), 1)
                            
                        # Add a balance meter at the bottom of the screen
                        if self.last_face_position is not None:
                            balance = self.calculate_audio_balance(self.last_face_position, frame_width)
                            meter_width = frame_width - 100
                            meter_x = 50
                            meter_y = frame_height - 50
                            meter_height = 20
                            
                            # Draw the meter background
                            cv2.rectangle(frame, (meter_x, meter_y), 
                                         (meter_x + meter_width, meter_y + meter_height), 
                                         (100, 100, 100), -1)
                            
                            # Draw the balance indicator
                            indicator_pos = int(meter_x + (meter_width * (balance + 1) / 2))
                            cv2.circle(frame, (indicator_pos, meter_y + meter_height//2), 
                                       10, (0, 255, 255), -1)
                            
                            # Add text indicators for left and right
                            cv2.putText(frame, "L", (meter_x - 20, meter_y + 15), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            cv2.putText(frame, "R", (meter_x + meter_width + 10, meter_y + 15), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            
                        # Show status info on screen
                        status_text = f"Balance: {'-' if balance < 0 else '+'}{abs(balance):.2f} | "
                        status_text += "CALIBRATED" if self.calibrated else "Not calibrated"
                        cv2.putText(frame, status_text, (20, 30), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        
                        cv2.imshow('Head Tracking Audio Balancer', frame)
                        
                        # Check for user input
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            self.running = False
                            break
                        elif key == ord('c') and len(faces) > 0:
                            # Calibrate to current position
                            self.calibrate(face_center_x)
                        elif key == ord('s'):
                            # Adjust sensitivity
                            self.adjust_sensitivity()
                        elif key == ord('m'):
                            # Toggle between eqMac and system audio
                            self.toggle_audio_mode()
                        elif key == ord('f'):
                            # Toggle cartoon filter
                            self.toggle_cartoon_filter()
                            
                    except Exception as e:
                        print(f"Warning: Could not display video preview: {e}")
                        self.show_preview = False
                        print("Continuing with audio balance adjustment only (no video preview)")
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.01)
                
        except Exception as e:
            print(f"Error in tracking loop: {e}")
        finally:
            # Cleanup
            self.cap.release()
            if self.show_preview:
                try:
                    cv2.destroyAllWindows()
                except:
                    pass
            
            # Reset audio balance to center or original balance
            if self.original_system_balance is not None:
                balance_normalized = (self.original_system_balance / 50) - 1
                print(f"Restoring original system balance: {self.original_system_balance}")
                self.set_audio_balance(balance_normalized)
            else:
                self.set_audio_balance(0)
            print("Head tracking stopped. Audio balance reset.")
            
    def handle_terminal_input(self):
        """Handle terminal input for commands when GUI is not available"""
        print("Terminal command mode active. Type commands and press Enter.")
        
        while self.running:
            try:
                # Use a non-blocking read with a timeout to prevent CPU hogging
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    line = sys.stdin.readline().strip().lower()
                    
                    if line == 'q':
                        print("Quitting...")
                        self.running = False
                    elif line == 'c':
                        self.calibrate()
                    elif line == 's':
                        self.adjust_sensitivity()
                    elif line == 'm':
                        self.toggle_audio_mode()
                    elif line == 'f':
                        self.toggle_cartoon_filter()
                    
                time.sleep(0.1)  # Sleep to prevent CPU hogging
            except Exception as e:
                print(f"Error handling terminal input: {e}")

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