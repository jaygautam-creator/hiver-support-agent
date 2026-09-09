"""Lists the models the key can actually reach, so model IDs are verified
rather than assumed. Run once after setting GOOGLE_API_KEY."""
from src.llm import client

for m in client().models.list():
    actions = getattr(m, "supported_actions", None) or []
    if not actions or "generateContent" in actions:
        print(f"{m.name:<45} {getattr(m, 'display_name', '')}")
