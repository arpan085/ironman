---
description: Structure optional voice assistant features and overlays in the gesture app without breaking baseline runtime behavior.
applyTo: "gesture_vision/**/*.py"
---

# Optional Voice Assistant Features and Overlay Structure

When adding voice-assistant capabilities, keep them optional and consistent with current app architecture:

1. **Config-gated and off by default**
   - Add new toggles to [default_config.json](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/config/default_config.json).
   - Mirror each toggle in [AppConfig](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/config.py:28) with safe defaults (`False` for enable flags).
   - Parse booleans with existing `_coerce_bool` in [config.py](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/config.py).

2. **Optional dependency loading**
   - Treat speech libraries as optional dependencies; initialize lazily inside runtime methods or feature-specific classes.
   - Follow the readiness-flag pattern used by optional media integrations (for example `_ready` handling in [MusicPlayerMode](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/modes/music_player.py:12)).
   - If unavailable, keep the app running and surface clear in-frame status text instead of crashing.

3. **Overlay layering and rendering placement**
   - Keep voice overlays as dedicated draw helpers (for example `_draw_voice_overlay`) on [GestureVisionApp](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/app.py:38) or a focused helper module.
   - Preserve frame composition order in [run](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/app.py:83): mode output first, optional overlays next, help overlay, then shell/title bar last.
   - Reuse mode banner conventions from [draw_instruction](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/modes/common.py:34) for consistent typography and placement.

4. **Input and state integration**
   - Add voice feature state on `GestureVisionApp` instance fields (same pattern as `show_help`).
   - Route keyboard toggles through [GestureVisionApp._handle_key](C:/Users/LENOVO/ironman.worktrees/voice-assistant-features-guidelines/gesture_vision/app.py:159) so voice toggles align with existing global shortcut flow.
   - Avoid hard-wiring voice behavior inside unrelated modes unless the mode explicitly owns that interaction.

## Right vs Wrong

- **Right:** Add `voice_assistant_enabled` to config, keep default `false`, lazily initialize speech backend, draw a small status overlay only when enabled.
- **Wrong:** Import speech backend at module top-level and fail app startup when microphone/speech package is missing.
