import os
import json
import re

# ── Gemini client setup ───────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

genai_client       = None
file_manager       = None
USE_DEMO_MODE      = True

if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        from google.generativeai import types as genai_types
        genai.configure(api_key=GEMINI_API_KEY)
        genai_client = genai
        USE_DEMO_MODE = False
        print("✅ Gemini AI initialised")
    except ImportError:
        print("⚠️  google-generativeai not installed — running in demo mode")
else:
    print("⚠️  No API key found — running in demo mode")


# ── Demo data ─────────────────────────────────────────────────────────────────
DEMO_TRANSCRIPT = {
    "full": "Alice: Good morning everyone. Let's start with the Q4 review. Bob: Sure. We hit 112% of our revenue target this quarter. Alice: Excellent! What drove the growth? Bob: The new enterprise tier was the biggest factor. We closed 8 deals. Alice: What about the product roadmap for Q1? Carol: We're prioritising the analytics dashboard and API performance improvements. Bob: We also need to allocate budget for the security audit. Alice: Agreed. Let's wrap up — Bob owns the budget proposal, Carol leads roadmap planning.",
    "segments": [
        {"speaker": "Speaker 1 (Alice)", "text": "Good morning everyone. Let's start with the Q4 review."},
        {"speaker": "Speaker 2 (Bob)",   "text": "Sure. We hit 112% of our revenue target this quarter."},
        {"speaker": "Speaker 1 (Alice)", "text": "Excellent! What drove the growth?"},
        {"speaker": "Speaker 2 (Bob)",   "text": "The new enterprise tier was the biggest factor. We closed 8 deals."},
        {"speaker": "Speaker 1 (Alice)", "text": "What about the product roadmap for Q1?"},
        {"speaker": "Speaker 3 (Carol)", "text": "We're prioritising the analytics dashboard and API performance improvements."},
        {"speaker": "Speaker 2 (Bob)",   "text": "We also need to allocate budget for the security audit."},
        {"speaker": "Speaker 1 (Alice)", "text": "Agreed. Let's wrap up — Bob owns the budget proposal, Carol leads roadmap planning."},
    ],
    "language": "en",
    "duration": 0,
}

DEMO_ANALYSIS = {
    "summary": {
        "overview":   "Q4 business review covering 112% revenue attainment, enterprise deal momentum, and Q1 product roadmap planning including an analytics dashboard, API improvements, and a security audit.",
        "keyPoints":  [
            "Q4 revenue exceeded target by 12% (112% attainment)",
            "8 enterprise tier deals closed — primary growth driver",
            "Q1 priorities: analytics dashboard & API performance",
            "Security audit budget needs to be allocated",
        ],
        "topics": ["Q4 Review", "Revenue", "Enterprise Sales", "Product Roadmap", "Security"],
    },
    "actionItems": [
        {"id": "ai_1", "task": "Prepare Q1 budget proposal including security audit costs",  "assignee": "Bob",   "priority": "high",   "dueDate": None, "completed": False},
        {"id": "ai_2", "task": "Lead Q1 roadmap planning for analytics dashboard",             "assignee": "Carol", "priority": "high",   "dueDate": None, "completed": False},
        {"id": "ai_3", "task": "Schedule and initiate security audit",                         "assignee": "",      "priority": "medium", "dueDate": None, "completed": False},
        {"id": "ai_4", "task": "Document enterprise tier deal learnings for Q1 strategy",      "assignee": "Bob",   "priority": "low",    "dueDate": None, "completed": False},
    ],
    "participants": [
        {"name": "Alice", "role": "Meeting Chair"},
        {"name": "Bob",   "role": "Sales / Revenue"},
        {"name": "Carol", "role": "Product"},
    ],
    "tags":           ["Q4 Review", "Revenue", "Roadmap", "Enterprise"],
    "meetingType":    "review",
    "suggestedTitle": "Q4 Business Review & Q1 Planning",
}


# ── Transcription ─────────────────────────────────────────────────────────────
def transcribe_audio(file_path: str, is_youtube: bool = False) -> dict:
    if USE_DEMO_MODE:
        print("🎭 Demo mode: returning sample transcript")
        return DEMO_TRANSCRIPT

    if is_youtube:
        return _transcribe_youtube(file_path)

    import google.generativeai as genai
    from google.generativeai import types as genai_types

    import pathlib, time
    print(f"Uploading to Gemini: {file_path}")
    ext = pathlib.Path(file_path).suffix.lower()
    mime_map = {".wav": "audio/wav", ".mp3": "audio/mp3", ".m4a": "audio/mp4",
                ".ogg": "audio/ogg", ".webm": "audio/webm", ".mp4": "video/mp4"}
    mime = mime_map.get(ext, "audio/mp3")

    uploaded = genai.upload_file(file_path, mime_type=mime)
    print(f"Uploaded: {uploaded.uri}")

    # Wait for processing
    while uploaded.state.name == "PROCESSING":
        print("Waiting for Gemini to process…")
        time.sleep(3)
        uploaded = genai.get_file(uploaded.name)

    if uploaded.state.name == "FAILED":
        raise RuntimeError("Gemini failed to process the audio file")

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config=genai_types.GenerationConfig(response_mime_type="application/json"),
    )

    prompt = """You are a professional transcription and speaker diarization system.
Return ONLY valid JSON in this exact format:
{
  "full": "entire raw combined transcript without speaker labels",
  "segments": [{"speaker": "Speaker 1", "text": "..."}],
  "language": "en"
}"""

    result = model.generate_content([{"file_data": {"mime_type": mime, "file_uri": uploaded.uri}}, prompt])

    try:
        data = json.loads(result.text)
    except json.JSONDecodeError:
        data = {"full": result.text, "segments": [], "language": "en"}

    try:
        genai.delete_file(uploaded.name)
    except Exception:
        pass

    return {
        "full":     data.get("full", ""),
        "segments": data.get("segments", []) if isinstance(data.get("segments"), list) else [],
        "language": data.get("language", "en"),
        "duration": 0,
    }


def _transcribe_youtube(youtube_url: str) -> dict:
    import tempfile, uuid as uuid_mod
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp not installed. Run: pip install yt-dlp")

    tmp_path = os.path.join("uploads", f"{uuid_mod.uuid4()}_yt.mp3")
    ydl_opts = {
        "format":            "bestaudio/best",
        "outtmpl":           tmp_path.replace(".mp3", ""),
        "postprocessors":    [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
        "quiet":             True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

    result = transcribe_audio(tmp_path)
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    return result


# ── Analysis ──────────────────────────────────────────────────────────────────
def analyze_meeting(transcript_text: str) -> dict:
    if USE_DEMO_MODE:
        print("🎭 Demo mode: returning sample analysis")
        return DEMO_ANALYSIS

    import google.generativeai as genai
    from google.generativeai import types as genai_types

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config=genai_types.GenerationConfig(response_mime_type="application/json"),
    )

    prompt = f"""You are a strict JSON generator. Return ONLY valid JSON, no extra text.

Format:
{{
  "summary": {{"overview": "", "keyPoints": [], "topics": []}},
  "actionItems": [{{"task": "", "assignee": "", "priority": "medium", "dueDate": null}}],
  "participants": [{{"name": "", "role": ""}}],
  "tags": [],
  "meetingType": "",
  "suggestedTitle": ""
}}

Analyse this transcript:
{transcript_text}"""

    result = model.generate_content(prompt)

    # Strip markdown fences if present
    text = result.text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$",    "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError("Gemini returned non-JSON response for analysis")

    # Normalise participants
    if not isinstance(data.get("participants"), list):
        data["participants"] = []
    data["participants"] = [
        {"name": p if isinstance(p, str) else p.get("name", ""), "role": "" if isinstance(p, str) else p.get("role", "")}
        for p in data["participants"]
    ]

    # Normalise action items
    if not isinstance(data.get("actionItems"), list):
        data["actionItems"] = []
    data["actionItems"] = [
        {
            "id":        item.get("id", f"ai_{i+1}"),
            "task":      item.get("task", "Action item") if isinstance(item, dict) else str(item),
            "assignee":  item.get("assignee", "") if isinstance(item, dict) else "",
            "priority":  item.get("priority", "medium") if isinstance(item, dict) else "medium",
            "dueDate":   item.get("dueDate", None) if isinstance(item, dict) else None,
            "completed": False,
        }
        for i, item in enumerate(data["actionItems"])
    ]

    if not data.get("summary"):
        data["summary"] = {"overview": "", "keyPoints": [], "topics": []}

    return data
