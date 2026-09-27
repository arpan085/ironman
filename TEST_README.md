# Ironman Gesture Vision Suite — Full Technical README

> This is the **deep-dive** companion document. It covers everything: architecture,
> every command, every mode with its exact key bindings, the config schema, the
> test suite, known bugs, and troubleshooting. The shorter marketing-style overview
> lives in `README.md`.

---

## 1. What is this project?

A modular **Python 3.11+ computer-vision application** that turns a webcam into a
gesture-controlled console. It bundles **30 switchable "modes"** (drawing, games,
system control, filters, music, effects, productivity) into a single OpenCV
`imshow` window with a dark themed shell, an optional Tkinter sidebar, logging,
screenshot/video capture, and synthesized music (no audio files needed).

It uses the **modern MediaPipe `tasks` API** (`HandLandmarker`, VIDEO mode) with
handedness-aware finger counting, and auto-downloads its model on first run.

- Language: Python 3.11 (project is type-hinted, uses `slots=True` dataclasses)
- GUI: OpenCV HighGUI (main loop) + optional Tkinter (sidebar)
- Platform: primarily Windows (pycaw volume, `screen-brightness-control`, `os.startfile`), degrades gracefully elsewhere

---

## 2. Project structure

```
ironman/
├── gesture_vision/
│   ├── __init__.py
│   ├── app.py                 # GestureVisionApp: camera loop, key dispatch, shell UI
│   ├── config.py              # AppConfig dataclass + JSON loader
│   ├── logger.py              # file + console logging setup
│   ├── main.py                # CLI entrypoint (argparse)
│   ├── assets/
│   │   ├── icons/.gitkeep
│   │   ├── sounds/.gitkeep
│   │   └── models/            # auto-downloaded .task / .xml (git-ignored)
│   ├── config/
│   │   └── default_config.json
│   ├── core/
│   │   ├── base_mode.py       # BaseMode ABC
│   │   ├── hand_tracker.py    # MediaPipe HandLandmarker wrapper + finger counting
│   │   ├── mode_manager.py    # mode registry, switching, shortcut lookup
│   │   ├── model_cache.py     # download/cache of model assets (retry + timeout)
│   │   ├── recorder.py        # screenshots + MP4 recording
│   │   ├── smoothing.py       # PointFilter (exponential moving average)
│   │   ├── soundgen.py        # numpy + pygame wavetable synth (drums/notes/chords)
│   │   └── system_controls.py # volume, brightness, distance/normalize helpers
│   ├── modes/                 # 30 mode classes (see section 5)
│   │   └── common.py          # shared helpers (finger_xy, hand_count, etc.)
│   └── ui/
│       └── tkinter_ui.py      # optional dark sidebar window (threaded)
├── images/                    # drop .png/.jpg/.jpeg here → Image Viewer (F4)
├── music/                     # drop .mp3/.wav/.ogg here → Music Player (F5)
├── captures/                  # screenshots (shot_*.png) + recordings (rec_*.mp4)
├── signatures/                # Air Signature saves (signature_*.png)
├── tests/                     # unittest suites (47 tests)
│   ├── test_core.py
│   ├── test_feature_modes.py
│   └── test_new_modes.py
├── gesture_vision.log         # runtime log (git-ignored)
├── requirements.txt
└── .gitignore
```

### Git-ignored content
`.gitignore` ignores: `__pycache__/`, `*.pyc`, `.venv/`, `captures/`, `signatures/`,
`gesture_vision.log`, downloaded models (`assets/models/*.task`, `*.xml`), and the
contents of `images/` and `music/` (with `.gitkeep` placeholders committed).

---

## 3. Setup & all commands

### 3.1 Create environment & install dependencies

```powershell
python -m venv .venv
.venv\Scripts\activate            # Windows
# or: source .venv/bin/activate   # Linux/macOS
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt`:

| Package | Version | Purpose | Hard requirement? |
|---|---|---|---|
| opencv-python | >=4.10.0 | video capture, rendering | **required** |
| mediapipe | >=0.10.35 | hand landmarking | **required** (falls back to no-hand mode) |
| numpy | >=1.26.0 | canvas / synth math | required |
| Pillow | >=10.4.0 | emoji rendering, font loading | optional-ish |
| psutil | >=5.9.0 | CPU % in Performance HUD | optional |
| pygame | >=2.6.0 | audio playback / synth | optional (silent fallback) |
| pyautogui | >=0.9.54 | virtual mouse, slide control | optional |
| screen-brightness-control | >=0.24.0 | brightness mode | optional (Windows) |
| pycaw | >=20240210 | volume mode | optional (Windows) |
| comtypes | >=1.4.5 | pycaw COM interop | optional |

The app is designed to keep running even when optional deps are missing.

### 3.2 Run the app

```powershell
python -m gesture_vision.main
# or, directly as a script:
python gesture_vision/main.py
```

First run downloads the MediaPipe `hand_landmarker.task` (~7.8 MB) and, on demand,
the OpenCV Haar cascade (`haarcascade_frontalface_default.xml`, ~0.9 MB) into
`gesture_vision/assets/models/`. They are cached for later runs.

### 3.3 Run with options

```powershell
# Pick a different camera
python -m gesture_vision.main --camera 1

# Cap the target frame rate (clamped to 1..60)
python -m gesture_vision.main --fps 30

# Enable / disable the Tkinter sidebar (default: disabled so it doesn't steal focus)
python -m gesture_vision.main --sidebar
python -m gesture_vision.main --no-sidebar

# Combined
python -m gesture_vision.main --camera 1 --fps 30 --sidebar
```

CLI flags override the values in `gesture_vision/config/default_config.json`
(`--fps` is clamped with `max(1, min(60, fps))`).

### 3.4 Run the tests

```powershell
# Full suite (47 tests)
python -m unittest discover -s tests -v

# A single file
python -m unittest tests.test_core -v
python -m unittest tests.test_feature_modes -v
python -m unittest tests.test_new_modes -v

# A single test class
python -m unittest tests.test_core.UtilityTests -v

# A single test
python -m unittest tests.test_new_modes.GestureSnakeTests.test_clear_restarts -v
```

**Current status: all 47 tests pass on Python 3.11.9.** (Verified `2026-08-02`.)

> ⚠️ One test has a real side effect — `MacroPadTests.test_keyboard_selection`
> fires slot 3 (`start https://www.google.com`), so running the suite on Windows
> opens a browser tab. See bug #11.

### 3.5 Other useful commands

```powershell
# Lint-free check is not configured (no ruff/flake8 config in the repo).
# The code uses # type: ignore comments and noqa markers for the tools it assumes.

# Verify the package imports cleanly
python -c "from gesture_vision.app import GestureVisionApp; print('ok')"
```

---

## 4. The 30 modes & how to switch

Modes are registered in **registration order** in `GestureVisionApp.__init__`
(`app.py`), which is also the order the help overlay and sidebar list them.
Switching is case-insensitive and handled in `ModeManager.switch_by_shortcut`.

### Core modes — number keys `1`–`0`

| # | Shortcut | Mode (class / module) | What it does |
|---|---|---|---|
| 1 | `1` | Virtual Drawing Canvas (`drawing_canvas.py`) | draw with fingertip, palette, undo, clear |
| 2 | `2` | Air Painter (`air_painter.py`) | smooth neon/rainbow brush with glow |
| 3 | `3` | Finger Counter (`finger_counter.py`) | shows raised-finger count |
| 4 | `4` | Rock Paper Scissors AI (`rps_ai.py`) | play vs computer, `Enter` to play round |
| 5 | `5` | Gesture Volume Controller (`volume_controller.py`) | thumb–index distance → system volume |
| 6 | `6` | Brightness Controller (`brightness_controller.py`) | thumb–index distance → monitor brightness |
| 7 | `7` | Virtual Mouse (`virtual_mouse.py`) | move cursor, click gestures, pyautogui |
| 8 | `8` | Finger Keyboard (`finger_keyboard.py`) | hover to type on an on-screen keyboard |
| 9 | `9` | Gesture Calculator (`gesture_calculator.py`) | type arithmetic, `=`/`Enter` evaluates |
| 0 | `0` | Virtual Whiteboard (`virtual_whiteboard.py`) | fullscreen white board with markers |

### Extended modes — `F1`–`F20`

| # | Shortcut | Mode (class / module) | What it does |
|---|---|---|---|
| 11 | `F1` | Color Tracking (`color_tracking.py`) | tracks a yellow blob (HSV), draws trail |
| 12 | `F2` | Object Measurement (`object_measurement.py`) | pinch distance → approximate cm |
| 13 | `F3` | Face Filter (`face_filter.py`) | sunglasses / hat / cartoon (Haar cascade) |
| 14 | `F4` | Image Viewer (`image_viewer.py`) | browse/zoom `images/` folder |
| 15 | `F5` | Music Player (`music_player.py`) | play tracks from `music/` folder |
| 16 | `F6` | Hand Animation Effects (`hand_animation.py`) | particle rings around fingertip |
| 17 | `F7` | Gesture Games (`gesture_games.py`) | fruit slice / balloons / catcher / maze |
| 18 | `F8` | Finger Magic (`finger_magic.py`) | laser / circle / energy / lightning |
| 19 | `F9` | Emoji Detector (`emoji_detector.py`) | emoji overlay by finger count |
| 20 | `F10` | Performance HUD (`performance_hud.py`) | FPS / CPU / resolution |
| 21 | `F11` | Gesture Snake (`gesture_snake.py`) | follow-the-finger snake game |
| 22 | `F12` | Air Drums (`air_drums.py`) | tap 4 synthesized pads |
| 23 | `F13` | Air Piano (`air_piano.py`) | hover keys to play C4–C5 |
| 24 | `F14` | Slide Controller (`slide_controller.py`) | swipe to change slides, optional PPT control |
| 25 | `F15` | Virtual Theremin (`theremin.py`) | height = pitch, hand distance = volume |
| 26 | `F16` | Air Guitar (`air_guitar.py`) | left hand = chord, right hand = strum |
| 27 | `F17` | Magic Wand (`magic_wand.py`) | particle trail, pinch = burst |
| 28 | `F18` | Smart Magnifier (`magnifier.py`) | PiP zoom follows fingertip |
| 29 | `F19` | Gesture Macro Pad (`macro_pad.py`) | launch apps by finger count + fist |
| 30 | `F20` | Air Signature (`air_signature.py`) | write signature, `S` saves PNG |

---

## 5. Global keyboard controls

Handled in `GestureVisionApp._handle_key` (`app.py`).

| Key | Action |
|---|---|
| `1`–`0` | switch core modes |
| `F1`–`F20` | switch extended modes |
| `H` | toggle help overlay |
| `C` | clear / restart (drawing modes, calculator, keyboard, snake) |
| `U` | undo (drawing canvas) |
| `E` | toggle eraser (drawing canvas, whiteboard) |
| `P` | palette / style toggle (canvas, whiteboard, air painter, face filter) |
| `Y` | toggle style (face filter) |
| `X` | next effect (hand animation) |
| `M` | next effect (finger magic) |
| `G` | next game (gesture games) |
| `S` | screenshot → `captures/shot_*.png` (+ any mode-local `snapshot()`) |
| `V` | start recording → `captures/rec_*.mp4` |
| `Z` | stop recording |
| `Q` / `Esc` | quit |
| `Enter` | RPS: play round; Calculator: evaluate; Macro Pad: fire slot |

### How the F-key detection works
`_resolve_fkey` (`app.py:50`) maps several backend encodings to `F1..F20`:
- Windows: `key = VK << 16` → `0x70..0x83` (F1..F20)
- X11/GTK: raw codes `65470..65489`
- Qt: `63236..63255`
- legacy HighGUI: low-byte `190..209`

### Mode-specific keys

- **Finger Keyboard (`8`):** hover the index fingertip over a key; `Backspace` deletes, `C` clears.
- **Gesture Calculator (`9`):** digits/operators typed directly; `=`/`Enter` evaluates, `Backspace` deletes.
- **Image Viewer (`F4`):** `[`/`]` or `p`/`n` navigate; `-`/`+` (or `_`/`=`) zoom; `r` reset.
- **Music Player (`F5`):** `n` next, `b` back, `Space` play/pause.
- **RPS AI (`4`):** `Enter` plays a round using current finger count.
- **Virtual Mouse (`7`):** index moves cursor; 2 fingers left-click, 3 right-click, 4 double-click, 5 scroll.
- **Gesture Snake (`F11`):** fingertip steers; `C` restarts on game over.
- **Air Drums (`F12`):** tap 4 pads with index finger (kick/snare/hihat/tom, synthesized).
- **Air Piano (`F13`):** hover keys to play C4–C5; keys `1..8` are a backup.
- **Slide Controller (`F14`):** swipe left/right; `P` toggles external PowerPoint/PDF key control (via pyautogui).
- **Virtual Theremin (`F15`):** hand height = pitch; two-hand separation = volume.
- **Air Guitar (`F16`):** show 1–5 fingers with one hand = chord (C/G/Am/Em/F); other hand crosses the string line to strum.
- **Magic Wand (`F17`):** move fingertip = color trail; pinch thumb+index = spark burst.
- **Smart Magnifier (`F18`):** `+`/`-` adjust zoom strength.
- **Gesture Macro Pad (`F19`):** 1–5 fingers select a slot (Notepad, Calc, Browser, Paint, Explorer); fist (or `Enter`) launches.
- **Air Signature (`F20`):** index finger draws, `S` saves PNG, `C` clears.

---

## 6. Configuration reference

Runtime settings come from `gesture_vision/config/default_config.json` and are
parsed/validated in `gesture_vision/config.py` (`load_config` → `AppConfig`).

```json
{
  "app_name": "Ironman Gesture Vision Suite",
  "camera_index": 0,
  "target_fps": 30,
  "window_width": 1280,
  "window_height": 720,
  "theme": "dark",
  "brush_size": 10,
  "draw_color": [0, 255, 255],
  "eraser_size": 40,
  "smooth_factor": 0.35,
  "record_output_dir": "captures",
  "sidebar_enabled": false
}
```

| Field | Used by | Clamping / notes |
|---|---|---|
| `app_name` | window title, shell bar | string |
| `camera_index` | `VideoCapture(index)` | int |
| `target_fps` | frame pacing + recorder FPS | `max(1, …)`; CLI clamps to 1–60 |
| `window_width` / `window_height` | `cap.set(CAP_PROP_*)` request | `>= 320` / `>= 240` |
| `theme` | `_draw_shell` top/bottom bars | `"dark"` (default) or anything else → light shell |
| `brush_size` | drawing canvas + whiteboard stroke width | wired through mode constructors |
| `draw_color` | drawing canvas + whiteboard initial color | wired through mode constructors |
| `eraser_size` | drawing canvas + whiteboard eraser width | wired through mode constructors |
| `smooth_factor` | `PointFilter` alpha in canvas + whiteboard | wired through mode constructors |
| `record_output_dir` | `Recorder` output | screenshots + recordings |
| `sidebar_enabled` | launch Tkinter sidebar | bool; `--sidebar`/`--no-sidebar` override |

---

## 7. Architecture notes

### Main loop (`app.py:137`)
1. Open camera, request configured resolution.
2. If `sidebar_enabled`, spawn `SidebarUI` in a daemon thread.
3. Per frame:
   - `cap.read()`; on failure, release + reopen the camera (auto-recovery).
   - `cv2.flip(frame, 1)` (mirror).
   - `tracker.process(frame)` → landmarks dict (`hands`, `handedness`, `fingers`,
     `fingers_up`, `index_tip`, `thumb_tip`).
   - `active_mode.process(frame, landmarks, context)` → rendered frame.
   - `_draw_shell`: dark top bar (app + mode name), bottom status bar
     (FPS / REC / help hint), optional full-screen help overlay.
   - `recorder.write(frame)`; `cv2.imshow`; `_handle_key`.
4. FPS is an EMA (`inst_fps * 0.1 + fps * 0.9`); loop sleeps to honor `target_fps`.

### Hand tracking (`core/hand_tracker.py`)
- Uses `mediapipe.tasks.python.vision.HandLandmarker` in **VIDEO** mode with
  `detect_for_video(image, frame_id)` (frame id is required for VIDEO mode).
- Finger counting: thumb is handedness-aware (x-position heuristic), the other
  four fingers compare tip vs PIP `y`.
- Sets `GLOG_minloglevel=2` and `TF_CPP_MIN_LOG_LEVEL=3` before importing.

### Mode lifecycle
`BaseMode` (ABC) defines `process()` (abstract), plus optional `on_enter`,
`on_exit`, `on_key`, `clear`, `undo`, `eraser`, `toggle_style`, `next_effect`,
`next_game`, `snapshot`, `play_round`. `ModeManager` calls `on_enter`/`on_exit`
on switches; `app.py` uses `hasattr` for optional behaviors.

### Audio (`core/soundgen.py`)
Synthesizes everything with numpy + pygame: `drum` (kick/snare/hihat/tom),
`note` (decaying sine+octave), `tone` (sustained, for the theremin), `chord`
(strummed). `soundgen.init()` is idempotent. Every audio path degrades to
"visual only" without pygame/audio device.

### System control (`core/system_controls.py`)
- `set_volume` — pycaw COM API (Windows). Silently no-ops on failure.
- `set_brightness` — `screen-brightness-control`. Silently no-ops on failure.
- `normalize_percentage(raw, low=0.02, high=0.30)` — maps normalized pinch
  distance to 0–100.

---

## 8. Test suite

Written with `unittest`; `tests/test_core.py` manipulates `sys.path` to import
the package root. No pytest, no external test deps.

- `test_core.py` — config loading/clamping, mode manager switching, smoothing,
  distance/normalize, calculator security (`eval` sandbox), finger counting
  (handedness), keyboard/calculator/viewer/player/games/canvas/whiteboard.
- `test_feature_modes.py` — F15–F20 key mapping, theremin pitch/volume, air
  guitar chords/strum, magic wand particles, magnifier zoom/PiP, macro pad
  selection/fire, air signature draw/save/clear.
- `test_new_modes.py` — F11–F14 key mapping, snake, piano, drums, slide swipe.

Run: `python -m unittest discover -s tests -v`

---

## 9. Known bugs & issues

Bugs found by code review + test runs. `✓` = confirmed, `~` = minor / low impact.

### High confidence

1. **✓ Music Player: Next/Previous pauses instead of playing**
   `gesture_vision/modes/music_player.py:64-76`. `next_track()`/`prev_track()`
   increment the index and then call `play_pause()`. `play_pause()` toggles, so
   when a track is currently playing, `n`/`b` **pause** the new track instead of
   playing it (and the label shows "Paused" with the new track name). Fix: load
   + `play()` the new track directly rather than going through the toggle.
   **[FIXED]** — `next_track`/`prev_track` now call `_play_current()` which loads
   and starts playback regardless of prior state.

2. **✓ Whiteboard "P Palette" is dead** `gesture_vision/modes/virtual_whiteboard.py`.
   The HUD says `P Palette`, and `cycle_palette()` exists (line 28), but the mode
   implements neither `on_key` nor `toggle_style`, and `app.py:276` only calls
   `toggle_style()` on `P`. Result: the `P` key does nothing in Whiteboard mode.
   **[FIXED]** — `VirtualWhiteboardMode` now defines `toggle_style()` which calls
   `cycle_palette()`, so the global `P` key works.

3. **✓ Dead config fields** `gesture_vision/config.py:17-24` + `default_config.json`.
   `theme`, `brush_size`, `eraser_size`, `smooth_factor`, and `draw_color` are
   loaded and validated but **never consumed** by any mode or the app.
   `drawing_canvas.py:25` hardcodes its own `brush_size = 8`; the whiteboard
   hardcodes sizes too. Editing these config values has zero effect.
   **[FIXED]** — `brush_size`, `eraser_size`, `draw_color`, `smooth_factor` are
   now passed into `VirtualDrawingCanvasMode` and `VirtualWhiteboardMode` from
   `AppConfig` (canvas/whiteboard strokes also smoothed via `PointFilter`).
   `theme` now switches the top/bottom shell bars between dark and light in
   `_draw_shell` (default `"dark"`).

4. **✓ `H` help key blocks typing "h" in Finger Keyboard** `gesture_vision/app.py:256-258`.
   The `typed == "h"` help toggle runs *before* the active mode's `on_key`. The
   virtual keyboard layout includes `H` (row 2: `ASDFGHJKL`), so it can never be
   typed by hovering. (`C` is similarly consumed by the global clear path, but
   FingerKeyboard's own `on_key` handles `c` first, so that one works.)
   *(still open)*

5. **✓ Help overlay is stale/truncated** `gesture_vision/app.py:223-230`. The
   header says `"Modes (F1-F14):"` but the app has 30 modes and the loop lists
   them all; it also hard-breaks once `y > h - 60`, so the list is cut off and
   the footer lines may draw over the last entries on short windows.
   **[FIXED]** — header now shows `Modes (30):`, entries render in two columns
   with row spacing derived from the frame height, and the footer is pinned to
   the bottom so it never overlaps the list.

6. **✓ Keys ≥ 256 that aren't F-keys are silently dropped** `gesture_vision/app.py:247-248`.
   After F-key resolution, any other keycode ≥ 256 is ignored, so arrow keys and
   other special keys do nothing anywhere. Intentional for F-keys only, but it
   also swallows keys other modes could use. *(still open)*

7. **✓ Air Signature pen-state mismatch with docs** `gesture_vision/modes/air_signature.py:35-41`.
   The HUD and README say "pinch lifts the pen", but `_pen_down()` only checks
   whether the index fingertip is above the PIP (`points[8].y < points[6].y`).
   There is no pinch detection, so you cannot lift the pen with a pinch.
   **[FIXED]** — `_pen_down()` now requires the index to be extended **and** the
   thumb–index distance to exceed `PINCH_THRESHOLD` (0.05), using the shared
   `distance()` helper from `core/system_controls.py`.

### Medium / low impact

8. **~ Magic Wand: `vx` is computed but never used** `gesture_vision/modes/magic_wand.py:36`.
   Particle `x` motion uses `vx2` (a stored random *angle*) and `y` uses `vy`;
   the intended horizontal velocity `vx` is dead. Trails drift in a biased way.

9. **~ Recorder doesn't verify the writer opened** `gesture_vision/core/recorder.py:36-51`.
   `start_video()` never checks `writer.isOpened()`; if `mp4v` is unavailable the
   status bar still shows `REC` while nothing is written.

10. **~ `images/` and `music/` are resolved relative to CWD** `image_viewer.py:17-24`,
    `music_player.py:17-21`. If the app is launched from another working directory
    (e.g. `python C:\...\ironman\gesture_vision\main.py` from elsewhere), the
    folders won't be found. Launch from the project root to avoid this.

11. **✓ Tests have a side effect: they open a browser** `tests/test_feature_modes.py:165-172`.
    `MacroPadTests.test_keyboard_selection` selects slot 3 (Browser,
    `start https://www.google.com`) and `_fire` launches it for real on Windows.
    The full suite leaves a browser tab open. (Also emits a `ResourceWarning` for
    the leaked subprocess.)

12. **~ `config.sidebar_enabled` bool parsing** `gesture_vision/config.py:59`.
    `bool(raw.get("sidebar_enabled", False))` — if a JSON file contained the
    *string* `"false"`, it would evaluate truthy and enable the sidebar. Only the
    JSON boolean works correctly.

13. **~ Finger Keyboard auto-repeats while hovering** `finger_keyboard.py:83-85`.
    Cooldown decrements every frame even while the fingertip stays on one key, so
    holding a key retypes it roughly every 18 frames (works like key repeat, but
    there's no press/release edge detection).

14. **~ Snake food range is hardcoded for ~640×480** `gesture_snake.py:40`.
    `random.randint(60, 580)` / `(80, 400)` can place food outside the visible
    play area on smaller windows (walls trigger game-over long before the apple
    is reachable). Harmless on default sizes.

15. **~ Theremin shows "Step N" instead of the note name** `theremin.py:86`.
    `note_name = f"Step {self._current_step or 0}"` — only displays an index, not
    the pitch/name, which makes the HUD less useful.

16. **~ `start `-prefixed MacroPad actions are Windows-only** `macro_pad.py:56-57`.
    On non-Windows, `subprocess.Popen(command, shell=True)` with `"start ..."` is
    a no-op/failure. App still won't crash (exceptions swallowed).

17. **~ Emoji detector can mis-slice when frame < 180px wide** `emoji_detector.py:58-63`.
    `x = w - 180` can be negative on tiny windows, producing out-of-bounds slices
    (guarded by `try/except`, so it fails silently).

18. **~ Drawing canvas snapshot edge-case after `undo()`** `drawing_canvas.py:74-84`.
    `undo()` replaces `self.canvas` but does not reset `self.prev`; the next
    stroke may begin without a fresh undo snapshot until the finger is lifted.

19. **~ Virtual Mouse moves the real cursor with no idle safety** `virtual_mouse.py:44-48`.
    Whenever an index fingertip is detected the system cursor jumps to the mapped
    position; if tracking drops the cursor stays where it last was. There's no
    guard/activation gesture, so the physical mouse user and the webcam can fight.

20. **~ Whiteboard returns a full board copy, discarding the camera feed**
    `virtual_whiteboard.py:58-59`. Intended, but the mode completely replaces the
    video — if that's surprising, note it as a design quirk.

### Non-bugs worth knowing

- **`eval` in the calculator is sandboxed** (`gesture_calculator.py:30`) with
  `{"__builtins__": {}}` plus a strict character whitelist. Attribute access is
  theoretically possible but can't be typed through the whitelist.
- **Finger counting is based on mirrored frames** — the app flips the frame
  before tracking, so MediaPipe's `Left`/`Right` labels are relative to the
  mirrored image. Consistent for the user, but note it if you rely on labels.
- **All `except Exception` paths silently degrade** (audio, pycaw, downloads).
  Failures are visible only via the log (`gesture_vision.log`) or the on-screen
  "Audio device unavailable" note.

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| "Unable to open webcam (index 0)" | Camera busy or not connected. Try `--camera 1` or close other apps using the webcam. |
| No hand tracking / landmarks | Model missing or download failed. Check `gesture_vision.log`; delete `assets/models/hand_landmarker.task` and rerun to force re-download. |
| Audio modes show "visual only" | pygame cannot init the mixer (no audio device). Fix: ensure a default audio device is present. |
| Volume / brightness do nothing | `pycaw` / `screen-brightness-control` are Windows-only and fail silently elsewhere. |
| F-keys don't switch modes | Different OpenCV backend encoding. The mapping covers Windows/GTK/Qt/legacy — report the raw `waitKey` code if it still fails. |
| No images/tracks in viewer/player | Files must live in `./images` and `./music` and the app must be launched from the project root (bug #10). |
| `H` won't type `h` in keyboard mode | Known bug #4. |
| Test suite opens a browser | Known bug #11 — isolate `tests.test_core` or mock `_fire`. |
| High CPU | MediaPipe + OpenCV at high res; lower `window_width/height` in config or `--fps`. |

---

## 11. Git history

```
7e29f1c k
c3b2868 W
e3c8593 Merge pull request #1 ... (copilot/advanced-python-computer-vision-project)
1b73251 Scaffold modular gesture vision suite
027124b Initial plan
e321a13 Initial commit
```

Current branch `main` is **1 commit ahead** of `origin/main` and the working tree
is clean.

---

## 12. Quick cheat sheet

```powershell
pip install -r requirements.txt                          # setup
python -m gesture_vision.main                            # run
python -m gesture_vision.main --camera 1 --fps 30 --sidebar   # run tuned
python -m unittest discover -s tests -v                  # test all
```
