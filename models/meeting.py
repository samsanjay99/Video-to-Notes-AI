import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Enum, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from extensions import db


class Meeting(db.Model):
    __tablename__ = "meetings"

    id               = db.Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id          = db.Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title            = db.Column(String(500), nullable=False)
    description      = db.Column(Text, default="")
    youtube_url      = db.Column(String(1000), nullable=True)
    audio_file       = db.Column(JSON, default=dict)
    status           = db.Column(
                           Enum("uploading","processing","transcribing","analyzing","completed","failed",
                                name="meeting_status"),
                           default="uploading", index=True)
    transcript       = db.Column(JSON, default=lambda: {"full": "", "segments": []})
    summary          = db.Column(JSON, default=lambda: {"overview": "", "keyPoints": [], "topics": []})
    action_items     = db.Column(JSON, default=list)
    participants     = db.Column(JSON, default=list)
    tags             = db.Column(ARRAY(String), default=list)
    share_token      = db.Column(String(255), unique=True, nullable=True)
    is_shared        = db.Column(Boolean, default=False)
    duration         = db.Column(Integer, default=0)
    word_count       = db.Column(Integer, default=0)
    processing_error = db.Column(Text, nullable=True)
    meta             = db.Column("metadata", JSON, default=lambda: {"recordedAt": None, "meetingType": "general"})
    created_at       = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at       = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                                 onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self, exclude_transcript: bool = False) -> dict:
        d = {
            "id":             self.id,
            "userId":         self.user_id,
            "title":          self.title,
            "description":    self.description or "",
            "youtubeUrl":     self.youtube_url,
            "audioFile":      self.audio_file or {},
            "status":         self.status,
            "summary":        self.summary or {},
            "actionItems":    self.action_items or [],
            "participants":   self.participants or [],
            "tags":           self.tags or [],
            "shareToken":     self.share_token,
            "isShared":       self.is_shared,
            "duration":       self.duration or 0,
            "wordCount":      self.word_count or 0,
            "processingError": self.processing_error,
            "metadata":       self.meta or {},
            "createdAt":      self.created_at.isoformat() if self.created_at else None,
            "updatedAt":      self.updated_at.isoformat() if self.updated_at else None,
        }
        if not exclude_transcript:
            d["transcript"] = self.transcript or {}
        return d
