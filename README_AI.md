Futuristic AI Desktop Assistant - Interactive Prototype

This prototype provides:
- A PySide6-based UI with an animated holographic AI core.
- Chat panel with conversation history and markdown-like code blocks.
- Voice capture using SpeechRecognition and microphone input (requires PyAudio).
- Offline Text-to-Speech using pyttsx3.
- Assistant manager that uses OpenAI if OPENAI_API_KEY is set; otherwise a deterministic fallback.

Run

1. python -m venv .venv
2. .venv\Scripts\activate
3. pip install -r requirements-prototype.txt
4. python main.py

Notes

- On Windows, install PortAudio (for PyAudio) if microphone capture fails.
- This is a foundation: add providers (Ollama, Anthropic), shaders, and more widgets incrementally.
