"""Asking for a story skips the picture and tells the device to play one."""

import pytest

from app.services.story_intent import is_story_request

STORY = [
    ("Tell me a story", ""),
    ("Can you tell me a story about a lion?", ""),
    ("I want another story", ""),
    ("story please", ""),
    ("Play a story", ""),
    ("ಕಥೆ ಹೇಳು", "Tell a story"),
    ("ನನಗೆ ಒಂದು ಕಥೆ ಹೇಳು", ""),          # no translation needed
    ("ಕಥೆ ಬೇಕು", ""),
    ("कहानी सुनाओ", "Tell a story"),
    ("मुझे एक कहानी सुनाओ", ""),
]
PICTURE = [
    ("A lion telling a story to a mouse", ""),
    ("A girl reading a storybook under a tree", ""),
    ("Lion playing football", ""),
    ("ಆನೆ ಮರಿ ಡ್ಯಾನ್ಸ್ ಮಾಡ್ತಿದೆ", "The baby elephant is dancing"),
    ("हाथी स्काई में उड़ रहा है", "The elephant is flying in the sky."),
    ("A storybook with a dragon on the cover", ""),
]


@pytest.mark.parametrize("text,english", STORY)
def test_story_requests(text, english):
    assert is_story_request(text, english)


@pytest.mark.parametrize("text,english", PICTURE)
def test_picture_requests(text, english):
    assert not is_story_request(text, english)


def test_story_request_skips_the_picture(pipeline):
    job, images = pipeline({"text": "ಕಥೆ ಹೇಳು", "language": "kn", "english_text": "Tell a story"})
    assert images == 0
    assert job["status"] == "done" and job["intent"] == "story"
    assert job["language"] == "kn" and job["text"] == "ಕಥೆ ಹೇಳು"
    assert job["error"] is None


def test_picture_request_keeps_sticker_intent(pipeline):
    job, images = pipeline({"text": "a lion", "language": "en"})
    assert images >= 1 and job["intent"] == "sticker"
