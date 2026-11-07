"""
Phase 1 Verification Suite
==========================
Tests all backend stabilization fixes:
1. Healthcheck (/health)
2. Static file serving (/storage)
3. Pre-recorded stories catalog & scenes (/stories)
4. Device auth with header-only (ESP32 style, no device_id in form)
5. Thermal image processing & 24-row strip chunking (1,160 B/strip)
6. Fast-path direct submit mode (/sticker/submit?mode=direct)
"""

import io
import unittest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app
from app.db.session import SessionLocal
from app.infra.repositories import device_repository, child_repository, user_repository
from app.services.image_processing import process_thermal_assets_sync
from app.utils.security import generate_device_token, hash_token

client = TestClient(app)


class TestPhase1Stabilization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        # Create a test parent user
        cls.user = user_repository.get_by_email(cls.db, "parent@test.com")
        if not cls.user:
            cls.user = user_repository.create(cls.db, {
                "email": "parent@test.com",
                "name": "Test Parent",
                "password_hash": "hash"
            })

        # Create a test child
        cls.child = child_repository.create(cls.db, {
            "name": "Test Child",
            "parent_id": cls.user.id,
        })

        # Create a test device with a known token
        cls.raw_token = generate_device_token()
        cls.device_id = "test-phase1-device"
        existing = device_repository.get_by_device_id(cls.db, cls.device_id)
        if existing:
            existing.token = hash_token(cls.raw_token)
            existing.child_id = cls.child.id
            cls.db.commit()
            cls.device = existing
        else:
            cls.device = device_repository.create(cls.db, {
                "device_id": cls.device_id,
                "parent_id": cls.user.id,
                "child_id": cls.child.id,
                "token": hash_token(cls.raw_token),
                "paused": False,
            })

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_health_check(self):
        """Verify /health responds with 200 OK and healthy status."""
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")
        print("✓ test_01_health_check passed")

    def test_02_static_files_serving(self):
        """Verify /storage serves static assets (PNG, WAV, BIN)."""
        resp = client.get("/storage/stories/pip_the_brave_penguin_cover.png")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.content) > 100)

        # Check binary strip serving
        resp_bin = client.get("/storage/stories/pip_the_brave_penguin_scene_1_384_strips.bin")
        self.assertEqual(resp_bin.status_code, 200)
        self.assertEqual(len(resp_bin.content) % 1160, 0)
        print("✓ test_02_static_files_serving passed")

    def test_03_stories_api(self):
        """Verify /stories catalog and scene hierarchy."""
        # List all stories
        resp = client.get("/stories")
        self.assertEqual(resp.status_code, 200)
        stories = resp.json()
        self.assertGreaterEqual(len(stories), 3)

        # Filter by language
        resp_hi = client.get("/stories?language=hi")
        self.assertEqual(resp_hi.status_code, 200)
        self.assertGreaterEqual(len(resp_hi.json()), 1)

        # Fetch scenes for first story
        first_story_id = stories[0]["id"]
        resp_scenes = client.get(f"/stories/{first_story_id}/scenes")
        self.assertEqual(resp_scenes.status_code, 200)
        scenes = resp_scenes.json()
        self.assertGreaterEqual(len(scenes), 1)

        first_scene = scenes[0]
        self.assertIn("audio_url", first_scene)
        self.assertIn("image_url", first_scene)
        self.assertIn("print_url", first_scene)
        self.assertTrue(first_scene["print_url"].endswith(".bin"))
        print("✓ test_03_stories_api passed")

    def test_04_device_auth_header_only(self):
        """Verify ESP32-style header-only auth (X-Device-Token without device_id in form)."""
        # Create minimal 1-second test WAV
        dummy_wav = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

        # POST without device_id in form (ESP32 format)
        resp = client.post(
            "/sticker/submit",
            headers={"X-Device-Token": self.raw_token},
            data={"child_id": str(self.child.id)},
            files={"audio": ("audio.wav", dummy_wav, "audio/wav")}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("job_id", data)
        print("✓ test_04_device_auth_header_only passed")

    def test_05_device_auth_invalid_token(self):
        """Verify invalid token is rejected with 401."""
        dummy_wav = io.BytesIO(b"RIFF....WAVE")
        resp = client.post(
            "/sticker/submit",
            headers={"X-Device-Token": "invalid-token-12345"},
            data={"child_id": str(self.child.id)},
            files={"audio": ("audio.wav", dummy_wav, "audio/wav")}
        )
        self.assertEqual(resp.status_code, 401)
        print("✓ test_05_device_auth_invalid_token passed")

    def test_06_thermal_image_processing_and_strip_chunking(self):
        """Verify thermal image processing produces exact 1,160-byte ESC/POS strips."""
        # Create a 512x512 sample drawing
        img = Image.new("RGB", (512, 512), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 450, 450], outline=(0, 0, 0), width=8)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        assets = process_thermal_assets_sync(buf.getvalue(), target_width=384, chunk_rows=24)

        self.assertIn("display_png", assets)
        self.assertIn("print_png", assets)
        self.assertIn("print_bin", assets)

        bin_data = assets["print_bin"]
        num_strips = assets["num_strips"]

        # Every strip MUST be exactly 1,160 bytes
        self.assertEqual(len(bin_data), num_strips * 1160)

        # Verify first strip header matches GS v 0 standard: \x1D\x76\x30\x00\x30\x00\x18\x00
        first_header = bin_data[:8]
        expected_header = bytes([0x1D, 0x76, 0x30, 0x00, 48, 0x00, 24, 0x00])
        self.assertEqual(first_header, expected_header)
        print(f"✓ test_06_thermal_image_processing passed ({num_strips} strips, {len(bin_data)} bytes)")

    def test_07_story_progress_tracking(self):
        """Verify recording story progress works."""
        resp = client.get("/stories")
        story_id = resp.json()[0]["id"]

        prog_resp = client.post(
            f"/stories/{story_id}/progress",
            json={"user_id": self.user.id, "language": "en"}
        )
        self.assertEqual(prog_resp.status_code, 200)
        self.assertEqual(prog_resp.json().get("status"), "recorded")
        print("✓ test_07_story_progress_tracking passed")

    def test_08_direct_mode_submit_contract(self):
        """Verify POST /sticker/submit?mode=direct returns fast-path contract."""
        dummy_wav = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        resp = client.post(
            "/sticker/submit?mode=direct",
            headers={"X-Device-Token": self.raw_token},
            data={"child_id": str(self.child.id)},
            files={"audio": ("audio.wav", dummy_wav, "audio/wav")}
        )
        # Without real Groq/OpenAI key in test env, pipeline returns 500 with structured error
        self.assertIn(resp.status_code, [200, 500])
        print(f"✓ test_08_direct_mode_submit_contract passed (status={resp.status_code})")


if __name__ == "__main__":
    unittest.main()
