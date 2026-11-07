"""
Story Seeding Script
====================
Populates wonderbox.db with 3 showcase pre-recorded stories for V1 demo:
1. Pip the Brave Penguin (English, 3-6 years)
2. Tara and the Magic Tree (English, 7-9 years)
3. Chintu aur Udan Khatola (Hindi, 3-6 years)

Generates:
- 16kHz 16-bit mono WAV audio tracks for each scene (compatible with I2S DAC and Pi speaker)
- 512x512 line-art illustrations (display PNG)
- 384px 24-row strip ESC/POS binary files (.bin) for thermal printing

Run directly:
    python -m app.db.seed_stories
"""

import io
import math
import os
import struct
import uuid
import wave
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.init_db import init_db
from app.db.session import engine
from app.models.story import Story, StoryScene
from app.services.image_processing import process_thermal_assets_sync


def _create_sample_audio_wav(output_path: str, duration_sec: float = 15.0, base_freq: float = 440.0) -> None:
    """Generate a clean 16kHz 16-bit mono WAV audio track with melodic chimes."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)

    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        buf = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            # Melodic arpeggio pattern: cycles through chords every 2.5 seconds
            chord_note = (int(t / 2.5) % 4)
            freq_mult = [1.0, 1.25, 1.5, 1.875][chord_note]
            f = base_freq * freq_mult

            # Envelope: decay within each note period
            note_phase = (t % 2.5) / 2.5
            envelope = math.exp(-2.0 * note_phase) * 0.4

            # Dual harmonic chime
            val = math.sin(2.0 * math.pi * f * t) + 0.5 * math.sin(2.0 * math.pi * (f * 2.0) * t)
            sample = int(32767.0 * envelope * val * 0.5)
            sample = max(-32768, min(32767, sample))
            buf += struct.pack("<h", sample)

        wav_file.writeframesraw(buf)


def _draw_scene_illustration(title: str, scene_num: int) -> bytes:
    """Generate a clean, high-contrast coloring book illustration."""
    img = Image.new("RGB", (512, 512), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Thick decorative border
    draw.rectangle([16, 16, 496, 496], outline=(0, 0, 0), width=6)
    draw.rectangle([24, 24, 488, 488], outline=(0, 0, 0), width=2)

    # Drawing based on scene content
    if "Penguin" in title:
        if scene_num == 1:
            # Penguin sliding on ice hill
            draw.arc([100, 250, 412, 500], 0, 180, fill=(0, 0, 0), width=6)
            # Body
            draw.ellipse([200, 160, 312, 340], outline=(0, 0, 0), width=6)
            draw.ellipse([225, 210, 287, 320], outline=(0, 0, 0), width=4)
            # Eyes & beak
            draw.ellipse([235, 190, 247, 202], fill=(0, 0, 0))
            draw.ellipse([265, 190, 277, 202], fill=(0, 0, 0))
            draw.polygon([(256, 205), (246, 220), (266, 220)], fill=(0, 0, 0))
            # Flippers
            draw.arc([170, 220, 220, 280], 90, 270, fill=(0, 0, 0), width=6)
            draw.arc([292, 220, 342, 280], 270, 90, fill=(0, 0, 0), width=6)
        else:
            # Penguin with lost seal friend
            draw.ellipse([140, 200, 260, 380], outline=(0, 0, 0), width=6)
            draw.ellipse([280, 240, 420, 380], outline=(0, 0, 0), width=6)
            draw.line([(100, 420), (420, 420)], fill=(0, 0, 0), width=6)

    elif "Tree" in title:
        # Magic tree with thick outlines
        draw.rectangle([236, 280, 276, 450], outline=(0, 0, 0), fill=(0, 0, 0))
        draw.ellipse([136, 120, 376, 320], outline=(0, 0, 0), width=8)
        draw.ellipse([100, 180, 260, 320], outline=(0, 0, 0), width=6)
        draw.ellipse([252, 180, 412, 320], outline=(0, 0, 0), width=6)
        # Magic stars
        for center_x, center_y in [(180, 170), (330, 160), (256, 140), (220, 240), (300, 230)]:
            draw.line([(center_x - 12, center_y), (center_x + 12, center_y)], fill=(0, 0, 0), width=4)
            draw.line([(center_x, center_y - 12), (center_x, center_y + 12)], fill=(0, 0, 0), width=4)

    else:
        # Hot air balloon (Udan Khatola)
        draw.ellipse([176, 90, 336, 270], outline=(0, 0, 0), width=7)
        draw.arc([196, 90, 316, 270], 0, 360, fill=(0, 0, 0), width=4)
        draw.line([(220, 270), (230, 330)], fill=(0, 0, 0), width=4)
        draw.line([(292, 270), (282, 330)], fill=(0, 0, 0), width=4)
        draw.rectangle([225, 330, 287, 375], outline=(0, 0, 0), width=6)
        # Clouds
        draw.arc([70, 360, 170, 420], 180, 360, fill=(0, 0, 0), width=5)
        draw.arc([340, 340, 450, 400], 180, 360, fill=(0, 0, 0), width=5)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def seed_stories():
    """Seed database with 3 showcase stories and generate their static assets."""
    db = Session(engine)

    try:
        existing_count = db.query(Story).count()
        if existing_count > 0:
            print(f"Stories already seeded ({existing_count} stories found in DB). Skipping.")
            return

        print("Seeding 3 showcase pre-recorded stories...")
        base_url = settings.BASE_URL.rstrip("/")
        stories_dir = os.path.join(settings.STORAGE_DIR, "stories")
        os.makedirs(stories_dir, exist_ok=True)

        story_definitions = [
            {
                "id": uuid.UUID("7c9e6679-7425-40de-944b-e07fc1f90ae1"),
                "title": "Pip the Brave Penguin",
                "description": "Pip learns to slide across the giant ice hill and makes a new friend.",
                "age_group": "early_childhood",
                "language": "en",
                "duration_seconds": 35,
                "scenes": [
                    {
                        "order_index": 1,
                        "duration_seconds": 18,
                        "desc": "Pip standing at the top of the shiny ice hill, ready to slide."
                    },
                    {
                        "order_index": 2,
                        "duration_seconds": 17,
                        "desc": "Pip sliding down fast and landing beside a friendly baby seal."
                    }
                ]
            },
            {
                "id": uuid.UUID("7c9e6679-7425-40de-944b-e07fc1f90ae2"),
                "title": "Tara and the Magic Tree",
                "description": "Tara discovers a glowing tree in the forest that whispers ancient secrets.",
                "age_group": "middle_childhood",
                "language": "en",
                "duration_seconds": 40,
                "scenes": [
                    {
                        "order_index": 1,
                        "duration_seconds": 20,
                        "desc": "Tara finding the giant magic tree covered in glowing golden stars."
                    },
                    {
                        "order_index": 2,
                        "duration_seconds": 20,
                        "desc": "The tree gently leaves a glowing leaf on Tara's open hand."
                    }
                ]
            },
            {
                "id": uuid.UUID("7c9e6679-7425-40de-944b-e07fc1f90ae3"),
                "title": "Chintu aur Udan Khatola",
                "description": "Chintu builds a flying basket and visits the colorful clouds above his village.",
                "age_group": "early_childhood",
                "language": "hi",
                "duration_seconds": 36,
                "scenes": [
                    {
                        "order_index": 1,
                        "duration_seconds": 18,
                        "desc": "Chintu flying high in his magical hot air balloon above green fields."
                    },
                    {
                        "order_index": 2,
                        "duration_seconds": 18,
                        "desc": "Chintu waving hello to a flock of friendly white birds in the sky."
                    }
                ]
            }
        ]

        for s_def in story_definitions:
            story = Story(
                id=s_def["id"],
                title=s_def["title"],
                description=s_def["description"],
                age_group=s_def["age_group"],
                language=s_def["language"],
                duration_seconds=s_def["duration_seconds"],
                is_active=True,
            )
            db.add(story)
            db.flush()

            # Generate cover image
            slug = s_def["title"].lower().replace(" ", "_")
            cover_png_bytes = _draw_scene_illustration(s_def["title"], 1)
            cover_assets = process_thermal_assets_sync(cover_png_bytes)
            cover_path = os.path.join(stories_dir, f"{slug}_cover.png")
            with open(cover_path, "wb") as f:
                f.write(cover_assets["display_png"])
            story.cover_image_url = f"{base_url}/storage/stories/{slug}_cover.png"

            # Create scenes
            for sc_def in s_def["scenes"]:
                sc_idx = sc_def["order_index"]
                scene_prefix = f"{slug}_scene_{sc_idx}"

                # 1. Generate audio track (WAV 16kHz 16-bit mono)
                wav_file = os.path.join(stories_dir, f"{scene_prefix}.wav")
                _create_sample_audio_wav(wav_file, duration_sec=float(sc_def["duration_seconds"]), base_freq=400.0 + sc_idx * 50.0)

                # 2. Generate line-art illustration
                raw_art = _draw_scene_illustration(s_def["title"], sc_idx)
                assets = process_thermal_assets_sync(raw_art)

                # 3. Save display PNG, visual 1-bit PNG, and 24-row strip .bin file
                disp_file = os.path.join(stories_dir, f"{scene_prefix}.png")
                bin_file = os.path.join(stories_dir, f"{scene_prefix}_384_strips.bin")

                with open(disp_file, "wb") as f:
                    f.write(assets["display_png"])
                with open(bin_file, "wb") as f:
                    f.write(assets["print_bin"])

                scene = StoryScene(
                    id=uuid.uuid4(),
                    story_id=story.id,
                    order_index=sc_idx,
                    audio_url=f"{base_url}/storage/stories/{scene_prefix}.wav",
                    image_url=f"{base_url}/storage/stories/{scene_prefix}.png",
                    print_url=f"{base_url}/storage/stories/{scene_prefix}_384_strips.bin",
                    duration_seconds=sc_def["duration_seconds"],
                )
                db.add(scene)

            print(f"✓ Created story: '{story.title}' ({len(s_def['scenes'])} scenes)")

        db.commit()
        print("✓ Successfully seeded all 3 showcase stories with valid audio and strip-chunked print binaries!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding stories: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_stories()
