# Ironman Gesture Vision Suite // Version 3.0 (Mark LXXXV Cinema Edition)

A modular **Python 3.11+** computer-vision and AI suite that bundles gesture-controlled tracking modes with an interactive **Stark HUD Dock**, an authentic **Iron Man Boot Sequence**, full **Mouse & Touch Click Controls**, an acoustic-grade **Cinema Sound Synthesizer**, and an integrated **J.A.R.V.I.S. AI Voice & Multimodal Vision Assistant** powered by the **Google Gemini API ("yourself api")**, synthesized Iron Man audio physics, and real-time holographic HUD interfaces.

---

## What's New in Version 3.0

- 🎶 **Acoustic-Grade Cinema Sound Synthesizer**: Completely eliminated all irritating screeching / piercing sounds. Replaced with warm, velvety, cinema-quality sounds:
  - **Mode Switching Whoosh**: Silky 440→220 Hz downward glide with soft hanning envelope, filtered warm air wash, and 329 Hz E4 bell overtone.
  - **UI Tap**: Warm 587 Hz D5 acoustic marimba glass tap with soft envelope, replacing harsh beeps.
  - **J.A.R.V.I.S. Chime**: Majestic C-Major 9th chord (C5, E5, G5, B5, D6) with warm chorus.
  - **Repulsor Turbine Surge & Blast**: Deep 65–280 Hz turbine engine surge and 45 Hz sub-bass punch with low-pass air displacement shockwave.
  - **Master Volume & Mute**: Global volume control (`+/-` keys, `M` mute key, clickable `[ 🔊 / 🔇 ]` dock button, voice commands).
- 🦾 **Mark LXXXV Nanotech Cybernetic Hand Tracking**: High-tech dual-layer glowing plasma conduits, micro-bearing knuckle nodes with holographic targeting brackets, and an interactive glowing palm Arc Repulsor core.
- ⚡ **Unibeam Weapon Discharge**: High-energy Arc Reactor beam discharge with particle shockwaves. Activated via palms together gesture, voice command (*"J.A.R.V.I.S., fire unibeam"*), or the `U` key.
- 🛡️ **Nanotech Energy Shield**: Shimmering hexagonal forcefield barrier. Activated via crossed wrists gesture, voice command (*"Deploy shield"*), or the `D` key.
- 💓 **Live Biometric ECG Telemetry**: Real-time dynamic P-Q-R-S-T cardiac waveform monitor integrated directly into the Mark LXXXV HUD telemetry dock.
- 🎙️ **Real-Time Voice Recognition ("Ear")**: Continuous microphone hearing with offline natural-language parser + Gemini fallback. Obeying all pilot commands hands-free!

---

## Highlights

- **J.A.R.V.I.S. AI Assistant**: Built-in AI assistant powered by Google Gemini API ("yourself api") for multimodal visual cognition, camera scene reasoning, and hands-free voice commands.
- **Offline Stark Tactical Fallback**: Complete offline natural-language command parser for instant 0-latency execution (mode switching, suit diagnostics, screenshot, video, audio control).
- **Asynchronous Voice Synthesis**: Non-blocking voice synthesizer (Windows SAPI / PowerShell background daemon) with animated HUD audio equalizer waveforms and subtitles.
- **Gesture-Activated Repulsor Blaster**: Hold up an open palm facing the camera to charge the repulsor capacitor with rising pitch whine -> automatic explosive 1.2GW repulsor discharge with screen flash, particle shockwave, and synthesized audio boom!
- **Center Arc Reactor**: Multi-ring animated plasma core with rotating segmented rings, unibeam geometry, and power telemetry.
- **Biometric Target Lock**: Real-time facial target tracking with pilot identification (`TONY STARK`), vital signs telemetry, and tactical crosshair brackets.
- **OpenCV + MediaPipe** (modern `tasks` API) hand tracking pipeline with handedness awareness, palm center, pinch detection, and finger states.
- **31 Integrated Modes**: Drawing, games, audio synthesizers, system tools, filters, magic effects, and tactical Stark HUD.
- **Global J.A.R.V.I.S. Prompt**: Press `J` or click `[ CHAT (J) ]` on the bottom dock in any mode to summon the holographic Stark command prompt.
- **Synthesized Iron Man Sound Effects**: Repulsor charge, repulsor blast, Jarvis chime, target lock, arc reactor hum, and UI pings (zero audio files needed).
- **Stark Tech HUD & Dark Sidebar**: Futuristic translucent UI panels, FPS/telemetry status bar, and scrollable Tkinter sidebar.

---

## Project Structure

```text
ironman/
├── gesture_vision/
│   ├── __init__.py
│   ├── app.py                     # v2.0: Boot sequence, mouse dock, drawer & orchestration
│   ├── config.py                  # Strongly-typed configuration loader (.env + JSON)
│   ├── logger.py
│   ├── main.py                    # Entrypoint CLI
│   ├── assets/
│   │   ├── icons/
│   │   ├── sounds/
│   │   └── models/                # Auto-downloaded hand/face models (cached locally)
│   ├── config/
│   │   └── default_config.json    # Default app settings & Gemini configuration
│   ├── core/
│   │   ├── base_mode.py
│   │   ├── hand_tracker.py        # 21 landmarks + palm center + pinch + fist + open palm
│   │   ├── jarvis.py              # J.A.R.V.I.S. AI, Gemini REST client, offline parser & voice
│   │   ├── mode_manager.py
│   │   ├── model_cache.py
│   │   ├── recorder.py
│   │   ├── smoothing.py
│   │   ├── soundgen.py            # Synthesizer for notes, drums, chords, repulsor blasts & chimes
│   │   └── system_controls.py     # Throttled volume, brightness, and scalar getters
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── air_drums.py           # F12
│   │   ├── air_guitar.py          # F16
│   │   ├── air_painter.py         # 2
│   │   ├── air_piano.py           # F13
│   │   ├── air_signature.py       # F20
│   │   ├── brightness_controller.py # 6
│   │   ├── color_tracking.py      # F1
│   │   ├── common.py              # Stark HUD drawing primitives & geometry helpers
│   │   ├── drawing_canvas.py      # 1
│   │   ├── emoji_detector.py      # F9
│   │   ├── face_filter.py         # F3 (Iron Man HUD, Stark Visor, Aviators, Hat, Cartoon)
│   │   ├── finger_counter.py      # 3
│   │   ├── finger_keyboard.py     # 8
│   │   ├── finger_magic.py        # F8
│   │   ├── gesture_calculator.py  # 9
│   │   ├── gesture_games.py       # F7
│   │   ├── gesture_snake.py       # F11
│   │   ├── hand_animation.py      # F6
│   │   ├── image_viewer.py        # F4
│   │   ├── ironman_jarvis.py      # F21 / J (Iron Man Tactical Cockpit & Repulsor HUD)
│   │   ├── macro_pad.py           # F19
│   │   ├── magic_wand.py          # F17
│   │   ├── magnifier.py           # F18
│   │   ├── music_player.py        # F5
│   │   ├── object_measurement.py  # F2
│   │   ├── performance_hud.py     # F10
│   │   ├── rps_ai.py              # 4
│   │   ├── slide_controller.py    # F14
│   │   ├── theremin.py            # F15
│   │   ├── virtual_mouse.py       # 7
│   │   ├── virtual_whiteboard.py  # 0
│   │   └── volume_controller.py   # 5
│   └── ui/
│       └── tkinter_ui.py          # Scrollable dark Stark Tech sidebar
├── images/                        # Drop images here for Image Viewer (F4)
├── music/                         # Drop mp3/wav/ogg here for Music Player (F5)
├── captures/                      # Screenshots and flight recordings land here
├── signatures/                    # Air Signature PNGs land here (F20)
├── tests/
│   ├── test_core.py               # Core manager, config, and utility tests
│   ├── test_feature_modes.py      # F15-F20 mode tests
│   ├── test_new_modes.py          # F11-F14 mode tests
│   ├── test_jarvis.py             # J.A.R.V.I.S. AI, Gemini client & sound synthesis tests
│   └── test_ironman_mode.py       # Iron Man HUD, v2.0 dock, boot sequence, and gesture tests
├── .env                           # User Gemini API key and configuration
├── .env.example                   # Environment configuration template
└── requirements.txt
```

---

## 31 Implemented Modes (Clickable & Keybinds)

| # | Key | Mode | Description |
|---|---|---|---|
| 1 | `1` | **Virtual Drawing Canvas** | Finger-drawn sketch pad with undo, eraser, and color cycling |
| 2 | `2` | **Air Painter** | High-speed air calligraphy trail tracking index finger |
| 3 | `3` | **Finger Counter** | Handedness-aware raised finger counter |
| 4 | `4` | **Rock Paper Scissors AI** | Real-time RPS game against AI |
| 5 | `5` | **Gesture Volume Controller** | Pinch distance adjusts Windows master volume |
| 6 | `6` | **Brightness Controller** | Pinch distance adjusts monitor brightness |
| 7 | `7` | **Virtual Mouse** | 1 finger moves cursor, 2 left-click, 3 right-click, 4 double-click, 5 scroll |
| 8 | `8` | **Finger Keyboard** | Hover over keys or use physical keyboard to type |
| 9 | `9` | **Gesture Calculator** | Gesture math calculator with arithmetic safety |
| 10 | `0` | **Virtual Whiteboard** | Digital whiteboard with palette selection |
| 11 | `F1` | **Color Tracking** | HSV color range tracking with bounding boxes |
| 12 | `F2` | **Object Measurement** | Dynamic centimeter distance estimation between fingertips |
| 13 | `F3` | **Face Filter** | Iron Man HUD, Stark Visor, Aviator sunglasses, Stark cap, and cartoon filter |
| 14 | `F4` | **Gesture Image Viewer** | Swipe and zoom through gallery images |
| 15 | `F5` | **Gesture Music Player** | Gesture audio track player (Next, Back, Play/Pause) |
| 16 | `F6` | **Hand Animation Effects** | Matrix trails, electric arcs, and cyber skeleton visuals |
| 17 | `F7` | **Gesture Games** | Balloon popping and target shooting mini-games |
| 18 | `F8` | **Finger Magic Effects** | Particle fire, glowing sparklers, and ice trails |
| 19 | `F9` | **Emoji Detector** | Real-time hand sign to emoji detector |
| 20 | `F10` | **Performance HUD** | Stark telemetry panel with FPS, CPU load, RAM usage, and resolution |
| 21 | `F11` | **Gesture Snake** | Follow-the-finger snake game |
| 22 | `F12` | **Air Drums** | Four synthesized drum pads (kick, snare, hi-hat, tom) |
| 23 | `F13` | **Air Piano** | Synthesized one-octave piano keyboard |
| 24 | `F14` | **Slide Controller** | Swipe finger left/right to change presentation slides |
| 25 | `F15` | **Virtual Theremin** | Hand height controls pitch, hand distance controls volume |
| 26 | `F16` | **Air Guitar** | Left hand picks chords (C, G, Am, Em, F), right hand strums |
| 27 | `F17` | **Magic Wand** | Color-shifting particle wand; pinch creates spark bursts |
| 28 | `F18` | **Smart Magnifier** | Picture-in-picture zoom following index fingertip |
| 29 | `F19` | **Gesture Macro Pad** | Show 1-5 fingers to pick an app; make a fist to launch |
| 30 | `F20` | **Air Signature** | Write your signature in the air and press `S` to export PNG |
| 31 | `F21` / `J` | **Iron Man J.A.R.V.I.S. Mode** | Arc Reactor core, repulsor blast, biometric lock, and Gemini vision AI |

---

## On-Screen Mouse & Touch Controls

You can control everything directly with your **mouse** without memorizing shortcuts:
- **`[ < ]` and `[ > ]`**: Step to previous/next mode.
- **`[ 📂 MODES ]`**: Open the 31-mode visual selector drawer. Click any mode card to switch immediately!
- **`[ ⚡ IRON MAN ]`**: Instant shortcut to Mode 31 (Mark LXXXV Cockpit & Repulsor Blaster).
- **`[ J.A.R.V.I.S.: ON / OFF ]`**: Click to toggle voice synthesis and AI audio on or off.
- **`[ 💬 CHAT (J) ]`**: Click to open the voice/text command dialog.
- **`[ 📸 SNAP (S) ]`**: Click to save a high-resolution screenshot.
- **`[ 🔴 REC (V) ]`**: Click to start or stop flight video recording.
- **`[ 🧹 CLEAR (C) ]`**: Click to clear canvas or restart game.
- **`[ ? HELP ]`**: Click to toggle the full shortcuts overlay.
- **`[ ✕ QUIT ]`**: Click to safely exit.

---

## Keyboard Controls Summary

- **Navigation**:
  - `[` or `Left Arrow`: Previous Mode
  - `]` or `Right Arrow`: Next Mode
  - `Tab`: Cycle to next mode
  - `1..9, 0` or Numpad `0..9`: Switch to core modes 1-10
  - `F1..F21`: Switch extended modes (`F21` = Iron Man J.A.R.V.I.S. Cockpit)
- **J.A.R.V.I.S.**:
  - `J`: Open J.A.R.V.I.S. holographic prompt
  - `Space` (in Mode 31): Inspect camera frame with Gemini Multimodal Vision
  - `T` or `/` (in Mode 31): Open in-cockpit chat
  - `S` (in Mode 31): Instant status diagnostics report
  - `R` (in Mode 31): Test repulsor blast
- **General Actions**:
  - `H`: Toggle shortcuts overlay
  - `C`: Clear canvas / restart game
  - `U`: Undo stroke (Drawing Canvas)
  - `E`: Eraser toggle (Drawing Canvas / Whiteboard)
  - `P`: Palette / style cycle
  - `S`: Screenshot (saved to `captures/`)
  - `V`: Start video recording
  - `Z`: Stop video recording
  - `Q` or `Esc`: Quit application

---

## J.A.R.V.I.S. AI Configuration

Your `.env` file is already active and configured with:
```env
GEMINI_API_KEY=your_key_here
JARVIS_MODEL=gemini-3.8-flash
JARVIS_VOICE=true
```

J.A.R.V.I.S. automatically connects to **Gemini 3.8 Flash** with automatic fallback to local Stark tactical rules whenever offline!

---

## Run

```powershell
.venv\Scripts\python -m gesture_vision.main
```

Optional CLI flags:

```powershell
.venv\Scripts\python -m gesture_vision.main --camera 0 --fps 30 --sidebar
```

---

## Test Suite

Run all 69 unit tests:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

**Results: 69 tests passing (100% OK)**
- [`tests/test_core.py`](file:///c:/Users/LENOVO/ironman/tests/test_core.py)
- [`tests/test_feature_modes.py`](file:///c:/Users/LENOVO/ironman/tests/test_feature_modes.py)
- [`tests/test_new_modes.py`](file:///c:/Users/LENOVO/ironman/tests/test_new_modes.py)
- [`tests/test_jarvis.py`](file:///c:/Users/LENOVO/ironman/tests/test_jarvis.py)
- [`tests/test_ironman_mode.py`](file:///c:/Users/LENOVO/ironman/tests/test_ironman_mode.py)
