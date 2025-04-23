# Veklo - Dynamic Head Tracking Audio Balance System

Veklo is a camera-based head tracking system that automatically adjusts your Mac's audio balance based on your head position. As you move left or right, the audio balance follows you, creating a "sweet spot" that moves with you.

## Features

- **Dynamic audio balance adjustment**: Audio balance changes based on your head position
- **Cartoon filter mode**: Optional stylized video display 
- **Calibration options**: Set your preferred "sweet spot" position
- **Sensitivity control**: Adjust how quickly balance changes with movement
- **Simple terminal control**: Easy-to-use keyboard commands
- **eqMac compatibility**: Works with system audio or eqMac

## Installation

### Prerequisites

- macOS (tested on macOS Sequoia/15)
- Python 3.x
- A webcam (built-in or external)

### Setup

1. Clone this repository:
```bash
git clone https://github.com/halapenyoharry/veklo.git
cd veklo
```

2. Install the required packages:
```bash
pip3 install opencv-python numpy pyobjc
```

3. Make sure your camera permissions are enabled in System Preferences > Security & Privacy > Camera

4. For full functionality, enable Accessibility permissions in System Preferences > Security & Privacy > Accessibility for Terminal/iTerm

## Usage

Run the application from the terminal:

```bash
python3 head_track_audio.py
```

### Commands

When the application is running, use these terminal commands:

- Type `c` and press Enter to calibrate (set the current position as your sweet spot)
- Type `s` and press Enter to adjust sensitivity
- Type `m` and press Enter to toggle between eqMac and system audio
- Type `f` and press Enter to toggle cartoon filter
- Type `q` and press Enter to quit

If the video window is visible, you can also press the corresponding keys in that window.

## How It Works

Veklo uses:
- OpenCV for face detection through your camera
- PyObjC for macOS integration 
- AppleScript to adjust system audio balance
- A threading approach to handle both video and audio processing

The system continuously tracks your face position and converts it to an audio balance value. The balance is inverted so that audio is stronger on the side you're sitting on, creating a more natural listening experience.

## Tips for Best Results

1. **Calibration**: Type 'c' while sitting in your preferred position to set your "sweet spot"
2. **Adjust Sensitivity**: If balance changes too quickly or slowly as you move, use 's' to adjust
3. **Lighting**: Ensure your face is well-lit for best tracking performance
4. **Camera Position**: Position your camera so your face is clearly visible when seated normally
5. **Audio Setup**: Works best with stereo speakers positioned on either side of your display

## Troubleshooting

- **No Video Preview**: If the video window doesn't appear, the app still works - just use terminal commands
- **Camera Access**: If camera doesn't activate, check your privacy settings
- **Audio Balance Issues**: Ensure Terminal has Accessibility permissions in System Preferences

## Future Enhancements

- Menubar app integration
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