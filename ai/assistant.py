"""Assistant manager with simple provider fallback.
If OPENAI_API_KEY is configured in the environment, uses OpenAI (basic sync call).
Otherwise falls back to a local deterministic responder.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import openai
except Exception:
    openai = None

class Assistant:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if openai and self.api_key:
            openai.api_key = self.api_key
            logger.info("OpenAI enabled for Assistant")
        else:
            logger.info("OpenAI not configured; using fallback responder")

    def ask(self, prompt: str) -> str:
        prompt = prompt.strip()
        if not prompt:
            return "I didn't catch that. Can you repeat?"
        # try OpenAI (synchronous simple completion) if available
        if openai and self.api_key:
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.6,
                )
                text = resp['choices'][0]['message']['content'].strip()
                return text
            except Exception as e:
                logger.exception("OpenAI query failed: %s", e)
                # fall through to fallback
        # deterministic fallback responder
        lower = prompt.lower()
        if any(k in lower for k in ["hello", "hi", "hey"]):
            return "Hello — I'm your futuristic assistant. How can I help you today?"
        if 'time' in lower:
            import datetime
            return f"The time is {datetime.datetime.now().strftime('%H:%M:%S')}"
        if 'weather' in lower:
            return "I cannot fetch live weather in this prototype, but it looks sunny in the simulation."
        if 'open' in lower and 'browser' in lower:
            return "Opening the default browser (prototype mode)."
        # default echo-ish
        return f"[Assistant fallback] You said: {prompt}"
