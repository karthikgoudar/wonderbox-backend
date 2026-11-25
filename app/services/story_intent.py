"""Spot when a child asks for a story instead of a picture.

Checked right after speech-to-text, on the English version (Sarvam
translates Kannada and Hindi) and on the original words. Only clear
requests count ("tell me a story", "ಕಥೆ ಹೇಳು", "कहानी सुनाओ"); a picture
that merely mentions a story ("a lion telling a story to a mouse",
"a girl reading a storybook") stays a picture.
"""

import re

_STORY = r"stor(?:y|ies)"
_ENGLISH = [
    # "tell me a story", "can you play a story", "I want another story"
    re.compile(
        r"\b(?:tell|play|read|narrate|say|hear|listen|want|give|start|share|"
        r"another|one more|new)\b(?:\s+\S+){0,4}?\s+" + _STORY + r"\b",
        re.IGNORECASE,
    ),
    # just "story" / "story please" / "story time"
    re.compile(r"^\W*(?:a\s+)?" + _STORY + r"(?:\s+(?:please|time|now))?\W*$", re.IGNORECASE),
]
_NOT_A_REQUEST = re.compile(r"\bstory\s?books?\b", re.IGNORECASE)

# Kannada: ಕಥೆ/ಕತೆ (story) with ಹೇಳು/ಹೇಳಿ (tell), ಬೇಕು (want), ಕೇಳ (hear)
_KANNADA = re.compile(r"(?:ಕಥೆ|ಕತೆ)\S*\s*(?:\S+\s+){0,2}?(?:ಹೇಳ|ಬೇಕು|ಕೇಳ|ಓದ)")
# Hindi: कहानी/किस्सा (story) with सुना (tell), बता (say), चाहिए (want)
_HINDI = re.compile(r"(?:कहानी|कहानियां|कहानियाँ|किस्सा)\S*\s*(?:\S+\s+){0,2}?(?:सुना|बता|चाहिए|पढ़)")


def is_story_request(text: str, english: str = "") -> bool:
    for words in (english, text):
        words = (words or "").strip()
        if not words or _NOT_A_REQUEST.search(words):
            continue
        if any(p.search(words) for p in _ENGLISH):
            return True
    native = text or ""
    return bool(_KANNADA.search(native) or _HINDI.search(native))
