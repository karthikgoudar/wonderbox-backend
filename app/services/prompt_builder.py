from typing import Optional


_BASE_STYLE = "simple black and white line drawing, bold outlines, sticker style"


def build_sticker_prompt(text: str, child_age: Optional[int] = None) -> str:
    """Build a normalized sticker prompt from raw text.

    `child_age` is reserved for future style tuning.
    """
    clean_text = (text or "").strip()

    if child_age is not None and child_age <= 6:
        return f"{clean_text}, {_BASE_STYLE}"

    return f"{clean_text}, {_BASE_STYLE}"
