#!/usr/bin/env python3

import cv2
import numpy as np
import time
import subprocess
import sys
import threading
import rumps
import objc
from Foundation import NSObject, NSLog, NSApplication, NSApp
from AppKit import NSStatusBar, NSMenu, NSMenuItem, NSWindow, NSImage, NSSlider
import Cocoa
import os

class VekloMenubarApp(rumps.App):
    def __init__(self):
        # Use text instead of emoji for icon
        super(VekloMenubarApp, self).__init__("Veklo", icon=None, title="V ◯")
        
        # Initialize variables
        self.tracker_thread = None
        self.running = False
        self.sensitivity = 0.8
        self.use_system_audio = True
        self.balance = 0.0  # -1 to 1 range
        
        # Setup menu items
        self.menu = ["Start Tracking", None, "Head Position: ---", "Balance: 0.0", "Sensitivity: 0.8", None, "Quit"]
        
        # Create slider for balance
        self.balance_slider_item = rumps.SliderMenuItem(
            callback=self.on_balance_change,
            min_value=-1.0,
            max_value=1.0,
            value=0.0
        )
        self.menu.insert_before("Sensitivity: 0.8", self.balance_slider_item)
        
        # Create slider for sensitivity
        self.sensitivity_slider_item = rumps.SliderMenuItem(
            callback=self.on_sensitivity_change,
            min_value=0.2,
            max_value=2.0,
            value=0.8
        )
        self.menu.insert_before("Quit", self.sensitivity_slider_item)
        
        # Initialize face tracking
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.cap = None
        self.last_face_position = None
        self.last_balance_update = time.time()
        self.update_frequency = 0.2  # seconds between balance updates
        
        # Initialize video window
        self.video_window = None
        
    @rumps.clicked("Start Tracking")
    def toggle_tracking(self, sender):
        if not self.running:
            # Start tracking
            self.running = True
            sender.title = "Stop Tracking"
            
            # Initialize the camera if needed
            if self.cap is None:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    rumps.alert("Error", "Could not open camera.")
                    self.running = False
                    sender.title = "Start Tracking"
                    return
                    
            # Start the tracking thread
            self.tracker_thread = threading.Thread(target=self.track_head)
            self.tracker_thread.daemon = True
            self.tracker_thread.start()
            
            # Show a notification
            rumps.notification("Veklo", "Head Tracking Active", 
                              "Veklo is now tracking your head position to adjust audio balance.")
        else:
            # Stop tracking
            self.running = False
            sender.title = "Start Tracking"
            
            # Clean up
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                
            # Reset audio balance
            self.set_audio_balance(0)
            
            # Reset menu title
            self.title = "V ◯"
            self.menu["Head Position: ---"].title = "Head Position: ---"
            
            # Close video window if open
            if self.video_window:
                cv2.destroyAllWindows()
                self.video_window = None
                
            # Show notification
            rumps.notification("Veklo", "Head Tracking Stopped", 
                              "Veklo has stopped tracking your head position.")
    
    @rumps.clicked("Quit")
    def quit_app(self, _):
        # Clean up
        if self.running:
            self.running = False
            if self.cap is not None:
                self.cap.release()
            if self.video_window:
                cv2.destroyAllWindows()
            self.set_audio_balance(0)
        rumps.quit_application()
    
    def on_balance_change(self, sender):
        """Manual balance adjustment via slider"""
        self.balance = sender.value
        self.menu["Balance: 0.0"].title = f"Balance: {self.balance:.1f}"
        self.update_menubar_title()
        self.set_audio_balance(self.balance)
    
    def on_sensitivity_change(self, sender):
        """Sensitivity adjustment via slider"""
        self.sensitivity = sender.value
        self.menu["Sensitivity: 0.8"].title = f"Sensitivity: {self.sensitivity:.1f}"
    
    def update_menubar_title(self):
        """Update the menubar title to show position and balance"""
        if self.last_face_position is None:
            return
            
        # Create a visual representation of the balance
        if self.balance < -0.6:
            indicator = "◀◀◀"  # Far left
        elif self.balance < -0.3:
            indicator = "◀◀○"  # Moderate left
        elif self.balance < -0.1:
            indicator = "◀○○"  # Slight left
        elif self.balance < 0.1:
            indicator = "○○○"  # Center
        elif self.balance < 0.3:
            indicator = "○○▶"  # Slight right
        elif self.balance < 0.6:
            indicator = "○▶▶"  # Moderate right
        else:
            indicator = "▶▶▶"  # Far right
            
        self.title = f"V {indicator}"
    
    def track_head(self):
        """Background thread to track head position and adjust audio balance"""
        try:
            while self.running:
                if not self.cap.isOpened():
                    break
                    
                ret, frame = self.cap.read()
                if not ret:
                    break
                
                # Process the frame
                # 1. Apply blur for privacy
                blurred = cv2.GaussianBlur(frame, (25, 25), 0)
                
                # 2. Convert to grayscale and increase contrast for shadow effect
                gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
                _, shadow = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
                
                # 3. Detect faces
                faces = self.face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                # Create display frame
                display_frame = np.zeros_like(frame)
                display_frame[:,:] = (30, 30, 30)  # Dark background
                
                # Add shadow effect
                shadow_display = cv2.cvtColor(shadow, cv2.COLOR_GRAY2BGR)
                display_frame = cv2.addWeighted(display_frame, 0.7, shadow_display, 0.3, 0)
                
                # Process the largest face if any are detected
                if len(faces) > 0:
                    # Find the largest face
                    largest_face = max(faces, key=lambda x: x[2] * x[3])
                    x, y, w, h = largest_face
                    
                    # Draw a subtle hint of the face position
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (70, 70, 70), 2)
                    
                    # Calculate face center position
                    face_center_x = x + w // 2
                    self.last_face_position = face_center_x
                    
                    # Update position info in menu
                    frame_width = frame.shape[1]
                    relative_position = int((face_center_x / frame_width) * 100)
                    self.menu["Head Position: ---"].title = f"Head Position: {relative_position}%"
                    
                    # Update audio balance (not too frequently)
                    current_time = time.time()
                    if current_time - self.last_balance_update > self.update_frequency:
                        offset = face_center_x - (frame_width / 2)
                        
                        # Calculate balance based on sensitivity
                        balance = offset / ((frame_width / 2) * self.sensitivity)
                        balance = max(-1.0, min(1.0, balance))
                        balance = -balance  # Invert so sound is stronger on the side the user is on
                        
                        # Only update if user isn't manually adjusting
                        try:
                            if not hasattr(self.balance_slider_item, 'slider') or not self.balance_slider_item.slider.highlighted:
                                self.balance = balance
                                self.set_audio_balance(balance)
                                # Update the menu and slider
                                self.menu["Balance: 0.0"].title = f"Balance: {balance:.1f}"
                                self.balance_slider_item.value = balance
                                # Update menubar title
                                self.update_menubar_title()
                        except:
                            # If we can't check if the slider is highlighted, just update anyway
                            self.balance = balance
                            self.set_audio_balance(balance)
                            self.menu["Balance: 0.0"].title = f"Balance: {balance:.1f}"
                            self.balance_slider_item.value = balance
                            self.update_menubar_title()
                            
                        self.last_balance_update = current_time
                
                # Add balance meter
                if self.last_face_position is not None:
                    meter_width = frame.shape[1] - 100
                    meter_x = 50
                    meter_y = frame.shape[0] - 50
                    meter_height = 20
                    
                    # Draw meter background
                    cv2.rectangle(display_frame, (meter_x, meter_y),
                                 (meter_x + meter_width, meter_y + meter_height),
                                 (50, 50, 50), -1)
                    
                    # Draw balance indicator
                    indicator_pos = int(meter_x + (meter_width * (self.balance + 1) / 2))
                    cv2.circle(display_frame, (indicator_pos, meter_y + meter_height//2),
                              10, (100, 100, 255), -1)
                    
                    # Add L/R labels
                    cv2.putText(display_frame, "L", (meter_x - 15, meter_y + 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    cv2.putText(display_frame, "R", (meter_x + meter_width + 5, meter_y + 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                    # Show information on screen
                    status_text = f"Position: {int((self.last_face_position / frame.shape[1]) * 100)}% | "
                    status_text += f"Balance: {self.balance:.2f}"
                    cv2.putText(display_frame, status_text, (20, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
                
                # Display the frame
                cv2.imshow('Veklo Head Tracking', display_frame)
                self.video_window = True
                
                # Check for window close
                if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                    break
                    
                time.sleep(0.03)  # ~30fps
                
        except Exception as e:
            print(f"Error in tracking thread: {e}")
        finally:
            if self.video_window:
                cv2.destroyAllWindows()
                self.video_window = None

    def set_audio_balance(self, balance):
        """Set system audio balance (-1.0 to 1.0 range)"""
        # Convert to percentage (0-100)
        balance_percentage = int((balance + 1) * 50)
        
        # Set the system audio balance via AppleScript
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


if __name__ == "__main__":
    # Create and run the app
    app = VekloMenubarApp()
    app.run() 