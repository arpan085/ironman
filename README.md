# Ironman Gesture Vision Suite

A modular **Python 3.11+** computer-vision project that bundles multiple gesture-controlled modes in one app for demos, reels, and portfolio use.

## Highlights

- OpenCV + MediaPipe (modern `tasks` API) hand tracking pipeline with handedness awareness
- 30 integrated modes (drawing, games, system controls, filters, music, and effects)
- Auto-downloads the `hand_landmarker.task` model on first run (cached locally)
- Dark-themed app shell with status bar (FPS/record) + built-in help overlay (`H`)
- Optional Tkinter sidebar (off by default - enable with `--sidebar` or config)
- Synthesized music modes (theremin, air guitar, drums, piano) - no audio files needed
- OOP architecture with separate modules
- Config-driven runtime settings
- Logging + screenshot/video capture utilities
- Throttled system volume/brightness control, debounced mouse actions
- Live mode input (type on a virtual keyboard, use the gesture calculator, control music/images with keys)

## Project Structure

```text
ironman/
├── gesture_vision/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── logger.py
│   ├── main.py
│   ├── assets/
│   │   ├── icons/
│   │   ├── sounds/
│   │   └── models/          # auto-downloaded hand/face models (git-ignored)
│   ├── config/
│   │   └── default_config.json
│   ├── core/
│   │   ├── base_mode.py
│   │   ├── hand_tracker.py
│   │   ├── mode_manager.py
│   │   ├── model_cache.py
│   │   ├── recorder.py
│   │   ├── smoothing.py
│   │   └── system_controls.py
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── air_drums.py
│   │   ├── air_guitar.py
│   │   ├── air_painter.py
│   │   ├── air_piano.py
│   │   ├── air_signature.py
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
│   │   ├── gesture_snake.py
│   │   ├── hand_animation.py
│   │   ├── image_viewer.py
│   │   ├── macro_pad.py
│   │   ├── magic_wand.py
│   │   ├── magnifier.py
│   │   ├── music_player.py
│   │   ├── object_measurement.py
│   │   ├── performance_hud.py
│   │   ├── rps_ai.py
│   │   ├── slide_controller.py
│   │   ├── theremin.py
│   │   ├── virtual_mouse.py
│   │   ├── virtual_whiteboard.py
│   │   └── volume_controller.py
│   └── ui/
│       └── tkinter_ui.py
├── images/                  # drop images here for Image Viewer (F4)
├── music/                   # drop mp3/wav/ogg here for Music Player (F5)
├── captures/                # screenshots and recordings land here
├── signatures/              # Air Signature PNGs land here (F20)
├── tests/
│   ├── test_core.py
│   ├── test_feature_modes.py
│   └── test_new_modes.py
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
21. Gesture Snake (F11) - follow-the-finger snake game
22. Air Drums (F12) - tap synthesized drum pads
23. Air Piano (F13) - hover to play one octave of notes
24. Slide Controller (F14) - swipe to advance presentation slides
25. Virtual Theremin (F15) - hand height picks the note, hand distance controls volume
26. Air Guitar (F16) - left hand finger count picks a chord, right hand swipes the strings
27. Magic Wand (F17) - glowing particle trail; pinch fires a spark burst
28. Smart Magnifier (F18) - picture-in-picture zoom that follows your fingertip
29. Gesture Macro Pad (F19) - pick an app with fingers, fire it with a fist
30. Air Signature (F20) - write your signature in the air and save it as a PNG

## Keyboard Controls

- `1..0` switch core modes
- `F1..F20` switch extended modes
- `H` toggle the help overlay
- `C` clear (drawing modes / calculator / keyboard / snake restart)
- `U` undo (drawing canvas)
- `E` eraser toggle (drawing canvas / whiteboard)
- `P` palette / style toggle (canvas, whiteboard, air painter, face filter)
- `X` next effect (hand animation)
- `M` next effect (finger magic)
- `G` next game (gesture games)
- `Y` toggle style (face filter)
- `S` screenshot
- `V` start video recording
- `Z` stop recording
- `Q` or `Esc` quit

### Mode-specific keys

- **Finger Keyboard (8):** hover the index fingertip over a key to type; `Backspace` deletes.
- **Gesture Calculator (9):** type digits/operators directly; `=`/`Enter` evaluates; `Backspace` deletes.
- **Image Viewer (F4):** `[`/`]` (or `p`/`n`) navigate, `-`/`+` zoom, `r` reset.
- **Music Player (F5):** `n` next, `b` back, `Space` play/pause.
- **RPS AI (4):** `Enter` plays a round using your current finger count.
- **Virtual Mouse (7):** index moves cursor; `2` fingers left-click, `3` right-click, `4` double-click, `5` scroll.
- **Gesture Snake (F11):** move your fingertip to steer the snake away from walls; `C` restarts on game over.
- **Air Drums (F12):** tap the four pads with your index finger to play kick/snare/hihat/tom (synthesized, no audio files needed).
- **Air Piano (F13):** hover over the keys to play C4..C5; physical keys `1..8` play notes as a backup.
- **Slide Controller (F14):** swipe your finger left/right to change slides; `P` toggles optional PowerPoint/PDF control.
- **Virtual Theremin (F15):** raise/lower your hand to change pitch; spread your hands apart to increase volume.
- **Air Guitar (F16):** show 1-5 fingers with one hand to pick a chord (C/G/Am/Em/F); swipe the other hand across the string line to strum.
- **Magic Wand (F17):** move your fingertip to leave a color-shifting particle trail; pinch your thumb and index finger to fire a spark burst.
- **Smart Magnifier (F18):** zoom follows your fingertip; `+`/`-` adjust magnification strength.
- **Gesture Macro Pad (F19):** hold up 1-5 fingers to select a slot (Notepad, Calculator, Browser, Paint, Explorer); make a fist (or press `Enter`) to launch it.
- **Air Signature (F20):** extend your index finger to draw in the air, pinch to lift the pen, `S` to save the signature PNG, `C` to clear.

## Run

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m gesture_vision.main
```

Optional flags:

```powershell
python -m gesture_vision.main --camera 1 --fps 30 --sidebar
```

- `--camera N` override the camera index
- `--fps N` cap the target frame rate (1-60)
- `--sidebar` / `--no-sidebar` toggle the Tkinter mode sidebar (default off so it does not steal focus)

On first launch the app downloads the MediaPipe hand landmarker model
(~8 MB) into `gesture_vision/assets/models/` and uses it afterwards from
cache. The face filter falls back to a downloaded Haar cascade when the
installed OpenCV build does not ship one.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Notes

- `pycaw` volume control and `screen-brightness-control` are Windows-oriented and fail safely on unsupported systems.
- Missing optional dependencies are handled gracefully to keep the app running.
- Target FPS can be tuned in `gesture_vision/config/default_config.json`.
- The camera loop auto-recovers from dropped frames and is capped at the configured target FPS.
