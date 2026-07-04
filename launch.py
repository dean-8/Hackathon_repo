"""Start study chat, wait for user, then launch Shape Shooter."""
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.getenv("STUDY_CHAT_PORT", "8765"))
BASE_URL = f"http://127.0.0.1:{PORT}"
CHAT_URL = f"{BASE_URL}/"


def _get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=2) as resp:
        import json
        return json.loads(resp.read().decode())


def _wait_for_server(timeout: float = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = _get_json("/api/health")
            if data.get("ok"):
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.25)
    return False


def _wait_for_game_ready(timeout: float = 3600) -> bool:
    """Wait until user clicks Start Game (default max 1 hour)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if _get_json("/api/ready-for-game").get("ready"):
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.4)
    return False


def main():
    print("Starting study chat server…")
    server = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "study_chat.server:app",
            "--host", "127.0.0.1",
            "--port", str(PORT),
            "--log-level", "warning",
        ],
        cwd=str(ROOT),
    )

    try:
        if not _wait_for_server():
            print("Study chat server did not start in time.")
            return 1

        print(f"Study chat: {CHAT_URL}")
        webbrowser.open(CHAT_URL)
        print("Chat opened in your browser.")
        print("Talk to the assistant, then click «Start Game» when you're ready.\n")

        if not _wait_for_game_ready():
            print("Timed out waiting for Start Game.")
            return 1

        print("Launching Shape Shooter…")
        env = os.environ.copy()
        env["SHAPE_SHOOTER_FROM_LAUNCHER"] = "1"
        game = subprocess.run(
            [sys.executable, str(ROOT / "sharpshooter.py")],
            cwd=str(ROOT),
            env=env,
        )
        return game.returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main() or 0)
