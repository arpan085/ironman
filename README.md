# Ironman Gesture Vision Suite

A modular **Python 3.12+** computer-vision project that bundles multiple gesture-controlled modes in one app for demos, reels, and portfolio use.

## Highlights

- OpenCV + MediaPipe Hands hand tracking pipeline
- 20 integrated modes (drawing, games, system controls, filters, and effects)
- Dark-themed app shell + optional Tkinter sidebar
- OOP architecture with separate modules
- Config-driven runtime settings
- Logging + screenshot/video capture utilities
- Gesture recording hooks and keyboard shortcut controls

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
- `Q` or `Esc` quit

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m gesture_vision.main
```

## Notes

- `pycaw` volume control is Windows-only and fails safely on unsupported systems.
- Missing optional dependencies are handled gracefully to keep the app running.
- Target FPS can be tuned in `gesture_vision/config/default_config.json`.
