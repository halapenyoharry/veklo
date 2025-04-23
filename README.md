# Veklo - Dynamic Head Tracking Audio Balance System

Veklo is a camera-based head tracking system that automatically adjusts your audio balance based on your head position. As you move left or right, the audio balance follows you, creating a "sweet spot" that moves with you.

## Features

- **Dynamic audio balance adjustment**: Audio balance changes based on your head position
- **Cartoon filter mode**: Optional stylized video display 
- **Calibration options**: Set your preferred "sweet spot" position
- **Sensitivity control**: Adjust how quickly balance changes with movement
- **Simple terminal control**: Easy-to-use keyboard commands
- **eqMac compatibility**: Works with system audio or eqMac

## Demo

![Veklo Demo](veklo_demo.gif)

## Installation

### Prerequisites

- macOS (tested on macOS Sequoia/15)
- Python 3.x
- A webcam (built-in or external)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/yourusername/veklo.git
cd veklo
```

2. Install the required packages:
```bash
pip3 install opencv-python numpy pyobjc
```

3. Make sure your camera permissions are enabled in System Preferences > Security & Privacy > Camera

4. For full functionality, enable Accessibility permissions in System Preferences > Security & Privacy > Accessibility for Terminal/iTerm

## Usage

Run the main application:

```bash
python3 head_track_audio.py
```

### Commands

When the application is running, you can use the following commands:

- Type `c` and press Enter to calibrate (set the current position as your sweet spot)
- Type `s` and press Enter to adjust sensitivity
- Type `m` and press Enter to toggle between eqMac and system audio
- Type `f` and press Enter to toggle cartoon filter
- Type `q` and press Enter to quit

You can also press the corresponding keys in the video window if it's visible.

## How It Works

Veklo uses:
- OpenCV for face detection through your camera
- PyObjC for macOS integration 
- AppleScript to adjust system audio balance
- A threading approach to handle both video and audio processing

The system continuously tracks your face position and converts it to an audio balance value. The balance is inverted so that audio is stronger on the side you're sitting on, creating a more natural listening experience.

## Customization

You can modify the code to:
- Change the sensitivity of balance adjustment
- Customize the cartoon filter effects
- Add additional audio balance modes
- Create a custom UI

## Future Enhancements

- Proper menubar application (in development)
- Additional video filters
- Support for external audio interfaces
- Dark mode/light mode themes
- Save and load user preferences

## License

MIT License

## Acknowledgments

- OpenCV for computer vision capabilities
- PyObjC for macOS integration
- The eqMac team for their great audio software 