# WonderBox Backend

Production-ready foundation for the WonderBox device backend (Sticker Mode v1).

Run locally (development):

1. Create virtualenv and install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run app:

```bash
uvicorn app.main:app --reload
```

This scaffold implements a mocked `/sticker` pipeline to accept audio and return a TLV binary image.
