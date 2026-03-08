#!/usr/bin/env python3
"""
DashScope sensevoice-v1 ASR wrapper for OpenClaw
Mimics whisper-cli interface: whisper-cli -m <model> -otxt -of <output_base> -np -nt <audio_file>
Routes transcription through Aliyun DashScope API (sensevoice-v1) using async batch mode.
Audio is base64-encoded as a data: URI to avoid needing a public HTTP server.
"""

import sys
import os
import json
import base64
import time
import subprocess
import tempfile
import urllib.request


def log(msg):
    print(f"[dashscope-asr] {msg}", file=sys.stderr)


def get_api_key():
    return os.environ.get("DASHSCOPE_API_KEY", "")


def audio_to_wav_base64(path):
    """Convert any audio file to 16kHz mono WAV and return base64 string."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        wav_path = t.name
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", path, "-ar", "16000", "-ac", "1", "-f", "wav", "-y", wav_path],
            capture_output=True, timeout=30
        )
        if result.returncode != 0:
            log(f"ffmpeg error: {result.stderr.decode()[:200]}")
            return None
        with open(wav_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    finally:
        try:
            os.unlink(wav_path)
        except Exception:
            pass


def transcribe(audio_path, language="zh"):
    api_key = get_api_key()
    if not api_key:
        log("DASHSCOPE_API_KEY not found in environment")
        return None

    log(f"Converting audio: {audio_path}")
    b64 = audio_to_wav_base64(audio_path)
    if not b64:
        log("Audio conversion failed")
        return None

    data_url = f"data:audio/wav;base64,{b64}"
    log(f"Submitting {len(b64)} chars to sensevoice-v1")

    body = json.dumps({
        "model": "sensevoice-v1",
        "input": {"file_urls": [data_url]},
        "parameters": {"language_hints": [language]}
    }).encode()

    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        task_id = result["output"]["task_id"]
        log(f"Task submitted: {task_id}")
    except Exception as e:
        log(f"Submit failed: {e}")
        return None

    # Poll up to 60 seconds
    for attempt in range(30):
        time.sleep(2)
        poll_req = urllib.request.Request(
            f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        try:
            with urllib.request.urlopen(poll_req, timeout=15) as pr:
                poll = json.loads(pr.read())
            status = poll["output"]["task_status"]
            log(f"Poll {attempt + 1}: {status}")

            if status == "SUCCEEDED":
                results = poll["output"].get("results", [])
                if not results:
                    return ""
                result0 = results[0]

                # New API format: transcription_url points to a JSON file
                transcription_url = result0.get("transcription_url", "")
                if transcription_url:
                    try:
                        with urllib.request.urlopen(transcription_url, timeout=15) as tr:
                            tdata = json.loads(tr.read())
                        transcripts = tdata.get("transcripts", [])
                        if transcripts:
                            text = transcripts[0].get("text", "")
                        else:
                            text = ""
                    except Exception as e:
                        log(f"Failed to fetch transcription_url: {e}")
                        text = ""
                else:
                    # Legacy format: inline transcription field
                    text = result0.get("transcription", "")
                    try:
                        if isinstance(text, str) and text.strip().startswith("{"):
                            d = json.loads(text)
                            sentences = d.get("transcripts", [{}])[0].get("sentences", [])
                            text = " ".join(s.get("text", "") for s in sentences)
                    except Exception:
                        pass

                # Strip sensevoice annotation tags like <|Speech|>, <|zh|>, <|NEUTRAL|> etc.
                import re
                text = re.sub(r'<\|[^|]+\|>', '', text).strip()

                log(f"Result: {text}")
                return text

            elif status == "FAILED":
                code = poll["output"].get("code", "")
                msg = poll["output"].get("message", "")
                log(f"FAILED: {code} - {msg}")
                return None

        except Exception as e:
            log(f"Poll error: {e}")

    log("Timeout waiting for result")
    return None


def main():
    # Parse whisper-cli args: -m <model> -otxt -of <output_base> -np -nt <audio_file>
    args = sys.argv[1:]
    output_base = None
    audio_file = None
    language = "zh"

    i = 0
    while i < len(args):
        if args[i] == "-of" and i + 1 < len(args):
            output_base = args[i + 1]
            i += 2
        elif args[i] == "-l" and i + 1 < len(args):
            language = args[i + 1]
            i += 2
        elif args[i] in ("-m", "--model") and i + 1 < len(args):
            i += 2  # ignore model path, we use sensevoice-v1 always
        elif args[i] in ("-otxt", "-np", "-nt", "--print-realtime", "--print-progress"):
            i += 1
        elif not args[i].startswith("-"):
            audio_file = args[i]
            i += 1
        else:
            i += 1

    if not audio_file:
        log("No audio file specified")
        sys.exit(1)

    if not output_base:
        output_base = audio_file.rsplit(".", 1)[0]

    log(f"Audio: {audio_file} → {output_base}.txt")

    text = transcribe(audio_file, language)
    if text is None:
        log("Transcription failed")
        sys.exit(1)

    output_file = f"{output_base}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text + "\n")

    log(f"Written: {output_file}")
    print(text)


if __name__ == "__main__":
    main()
