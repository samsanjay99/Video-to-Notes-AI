import os
import uuid
import threading
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from extensions import db
from models.meeting import Meeting
from middleware.auth import auth_required
from services.ai_service import transcribe_audio, analyze_meeting

upload_bp = Blueprint("upload", __name__)

ALLOWED_AUDIO = {"mp3", "wav", "m4a", "ogg", "webm"}
ALLOWED_VIDEO = {"mp4", "mkv", "mov"}
ALLOWED_EXTS  = ALLOWED_AUDIO | ALLOWED_VIDEO


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _is_video(filename: str) -> bool:
    return _ext(filename) in ALLOWED_VIDEO


def _convert_to_mp3(input_path: str, output_path: str):
    """Use ffmpeg-python or subprocess to strip video to audio."""
    try:
        import ffmpeg
        ffmpeg.input(input_path).output(output_path, acodec="libmp3lame", audio_bitrate="64k", vn=None).overwrite_output().run(quiet=True)
    except ImportError:
        import subprocess
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-vn", "-acodec", "libmp3lame", "-ab", "64k", "-y", output_path],
            check=True, capture_output=True,
        )


# ── POST /api/upload/ ─────────────────────────────────────────────────────────
@upload_bp.route("/", methods=["POST"])
@auth_required
def upload_file(current_user):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    youtube_url   = request.form.get("youtubeUrl", "").strip()
    title         = request.form.get("title", "").strip()
    description   = request.form.get("description", "").strip()
    recorded_at   = request.form.get("recordedAt", "")
    is_youtube    = False

    file_path     = None
    original_name = ""
    file_size     = 0
    mime_type     = ""

    # ── Branch 1: file upload ─────────────────────────────────────────────────
    if "file" in request.files and request.files["file"].filename:
        f = request.files["file"]
        ext = _ext(f.filename)
        if ext not in ALLOWED_EXTS:
            return jsonify({"success": False, "message": f"Unsupported file type: .{ext}"}), 400

        unique_name = f"{uuid.uuid4()}.{ext}"
        save_path   = os.path.join(upload_folder, unique_name)
        f.save(save_path)

        # Convert video → audio
        if _is_video(f.filename):
            audio_path = save_path + ".mp3"
            try:
                _convert_to_mp3(save_path, audio_path)
                file_path = audio_path
            except Exception as e:
                file_path = save_path   # fall back; Gemini can handle video too
                print(f"⚠️  ffmpeg conversion failed: {e} — using original video")
        else:
            file_path = save_path

        original_name = f.filename
        mime_type     = f.content_type or "audio/mpeg"
        file_size     = os.path.getsize(save_path)

    # ── Branch 2: YouTube URL ─────────────────────────────────────────────────
    elif youtube_url:
        import re
        yt_pattern = r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+"
        if not re.match(yt_pattern, youtube_url):
            return jsonify({"success": False, "message": "Invalid YouTube URL"}), 400
        # Store the URL; actual download happens in the background worker
        tmp_path = os.path.join(upload_folder, f"{uuid.uuid4()}_yt_url.txt")
        with open(tmp_path, "w") as fh:
            fh.write(youtube_url)
        file_path     = tmp_path
        original_name = "YouTube Video"
        mime_type     = "text/plain"
        file_size     = 0
        is_youtube    = True
    else:
        return jsonify({"success": False, "message": "No file or YouTube URL provided"}), 400

    # ── Create Meeting record ─────────────────────────────────────────────────
    meeting = Meeting(
        user_id     = current_user.id,
        title       = title or original_name.rsplit(".", 1)[0] or "Untitled Meeting",
        description = description,
        youtube_url = youtube_url if is_youtube else None,
        audio_file  = {
            "originalName": original_name,
            "filename":     os.path.basename(file_path),
            "path":         file_path,
            "size":         file_size,
            "mimetype":     mime_type,
        },
        status = "processing",
        meta   = {"recordedAt": recorded_at or None, "meetingType": "general"},
    )
    db.session.add(meeting)
    db.session.commit()

    # Detach from session before handing off to thread
    meeting_id  = meeting.id
    _youtube_url = youtube_url if is_youtube else None

    # ── Respond immediately; process in background ────────────────────────────
    threading.Thread(
        target  = _process_meeting_worker,
        args    = (meeting_id, file_path, _youtube_url, current_app._get_current_object()),
        daemon  = True,
    ).start()

    return jsonify({
        "success": True,
        "meeting": meeting.to_dict(),
        "message": "Upload successful, processing started",
    })


# ── Background worker ─────────────────────────────────────────────────────────
def _process_meeting_worker(meeting_id: str, file_path: str, youtube_url, app):
    with app.app_context():
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return

        try:
            meeting.status = "transcribing"
            db.session.commit()

            transcript_data = (
                transcribe_audio(youtube_url, is_youtube=True)
                if youtube_url
                else transcribe_audio(file_path)
            )

            meeting.status = "analyzing"
            db.session.commit()

            analysis = analyze_meeting(transcript_data["full"])

            meeting.status      = "completed"
            meeting.transcript  = {"full": transcript_data["full"], "segments": transcript_data.get("segments", [])}
            meeting.summary     = analysis.get("summary", {})
            meeting.action_items = [
                {**item, "id": item.get("id") or f"ai_{i}"}
                for i, item in enumerate(analysis.get("actionItems", []))
            ]
            meeting.participants = analysis.get("participants", [])
            meeting.tags         = analysis.get("tags", [])
            meeting.duration     = transcript_data.get("duration", 0)
            meeting.word_count   = len(transcript_data["full"].split())
            if analysis.get("suggestedTitle"):
                meeting.title = analysis["suggestedTitle"]
            if meeting.meta:
                meeting.meta["meetingType"] = analysis.get("meetingType", "general")
            db.session.commit()
            print(f"✅ Meeting {meeting_id} processed")

        except Exception as exc:
            print(f"❌ Meeting {meeting_id} failed: {exc}")
            meeting = Meeting.query.get(meeting_id)
            if meeting:
                meeting.status           = "failed"
                meeting.processing_error = str(exc)
                db.session.commit()
