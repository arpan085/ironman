# Ironman Gesture Vision Suite

A modular **Python 3.12+** computer-vision project that bundles multiple gesture-controlled modes in one app for demos, reels, and portfolio use.

## Highlights

- OpenCV + MediaPipe Hands hand tracking pipeline
- 20 integrated modes (drawing, games, system controls, filters, and effects)
- Dark-themed app shell + optional Tkinter sidebar with config-driven enablement
- OOP architecture with separate modules
- Config-driven runtime settings including drawing colors, brush sizes, and help toggle behavior
- Logging + screenshot/video capture utilities
- Gesture recording hooks and keyboard shortcut controls
- Jarvis-style wake word hooks, cinematic HUD shell effects, and suit-status voice telemetry
- Startup splash initialization screen with optional skip flag and fullscreen startup support

## Project Structure

```text
/home/runner/work/ironman/ironman/
├── gesture_vision/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── logger.py
│   ├── main.py
│   ├── config/
│   │   └── default_config.json
│   ├── core/
│   │   ├── base_mode.py
│   │   ├── hand_tracker.py
│   │   ├── mode_manager.py
│   │   ├── recorder.py
│   │   ├── smoothing.py
│   │   ├── suit_ai.py
│   │   └── system_controls.py
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── air_painter.py
│   │   ├── brightness_controller.py
│   │   ├── color_tracking.py
│   │   ├── common.py
│   │   ├── drawing_canvas.py
│   │   ├── emoji_detector.py
│   │   ├── face_filter.py
│   │   ├── finger_counter.py
│   │   ├── finger_keyboard.py
│   │   ├── finger_magic.py
│   │   ├── gesture_calculator.py
│   │   ├── gesture_games.py
│   │   ├── hand_animation.py
│   │   ├── image_viewer.py
│   │   ├── music_player.py
│   │   ├── object_measurement.py
│   │   ├── performance_hud.py
│   │   ├── rps_ai.py
│   │   ├── virtual_mouse.py
│   │   ├── virtual_whiteboard.py
│   │   └── volume_controller.py
│   ├── ui/
│   │   └── tkinter_ui.py
│   └── assets/
│       ├── icons/
│       └── sounds/
├── tests/
│   └── test_core.py
└── requirements.txt
```

## Implemented Modes

1. Virtual Drawing Canvas
2. Air Painter
3. Finger Counter
4. Rock Paper Scissors AI
5. Gesture Volume Controller
6. Brightness Controller
7. Virtual Mouse
8. Finger Keyboard
9. Gesture Calculator
10. Virtual Whiteboard
11. Color Tracking
12. Object Measurement
13. Face Filter
14. Gesture Image Viewer
15. Gesture Music Player
16. Hand Animation Effects
17. Gesture Game Collection
18. Finger Magic Effects
19. Emoji Detector
20. Performance HUD (FPS/CPU/Resolution)

## Keyboard Controls

- `1..0` switch core modes
- `F1..F10` switch extended modes
- `C` clear (drawing modes)
- `U` undo
- `E` eraser toggle
- `P/Y/X/G/M` effect/style/game toggles (mode dependent)
- `S` screenshot
- `V` start video recording
- `Z` stop recording
- `T` speak suit-status telemetry
- `J` enter/exit the Jarvis cinematic overlay and temporarily pause normal camera mode
- `R` soft reset active mode/session state (unless consumed by active mode)
- `H` toggle help overlay
- `L` toggle compact mode list overlay
- `Q` or `Esc` quit

## Run

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m gesture_vision.main
python -m gesture_vision.main --no-splash
```

If `pip` cannot build `PyAudio` on Windows, install a wheel instead:

```powershell
python -m pip install pipwin
python -m pipwin install pyaudio
```

## Notes

- `pycaw` volume control is Windows-only and fails safely on unsupported systems.
- Missing optional dependencies are handled gracefully to keep the app running.
- Target FPS can be tuned in `gesture_vision/config/default_config.json`.
- Wake-word listening uses `SpeechRecognition` and microphone support. If `PyAudio` is missing or your mic backend is unavailable, Jarvis still speaks and the app keeps running; voice input simply becomes unavailable until the mic backend is fixed.
- Voice responses use `pyttsx3` and Windows SAPI on supported machines.
- Jarvis can now respond to greetings, switch modes by voice, and open common targets such as YouTube and Google.
- Splash/fullscreen/assistant toggles are configurable in `gesture_vision/config/default_config.json`.
hey there! I am Arpan. I am 17 at the moment. I am currently living in kathmandu nepal. i am not from rich background. i am currently studing in grade 12 computer science and i am good at study as well . i have college from 6 am to 2:30 pm. and i wanna earn so badly , like so badly i am so in need of money , i need a job but i don't have any skills. but i can promise i can learn any skills so fastly. and can do things perfectly. but i don't know the way how can i do this or anything
