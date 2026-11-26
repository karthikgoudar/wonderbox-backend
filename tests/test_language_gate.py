"""The sticker pipeline stops before the picture for languages that are not allowed."""

import pytest


def test_tamil_speech_stops_with_friendly_message(pipeline):
    job, images = pipeline({"text": "எனக்கு யானை வேண்டும்", "language": "ta"})
    assert images == 0
    assert job["status"] == "error"
    assert job["error"] == {"code": "LANGUAGE_NOT_SUPPORTED",
                            "message": "Please speak in English, Kannada or Hindi"}
    assert job["language"] == "ta"


@pytest.mark.parametrize("lang", ["en", "kn", "hi"])
def test_allowed_languages_reach_the_picture_step(pipeline, lang):
    job, images = pipeline({"text": "a lion", "language": lang, "english_text": "a lion"})
    assert images >= 1
    assert job["error"]["code"] != "LANGUAGE_NOT_SUPPORTED"
