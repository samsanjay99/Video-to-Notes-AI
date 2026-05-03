import uuid
import bcrypt
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id          = db.Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name        = db.Column(String(255), nullable=False)
    email       = db.Column(String(255), nullable=False, unique=True, index=True)
    password    = db.Column(String(255), nullable=False)
    avatar      = db.Column(String(500), default="")
    role        = db.Column(Enum("user", "admin", name="user_role"), default="user")
    preferences = db.Column(JSON, default=lambda: {"theme": "dark", "notifications": True})
    created_at  = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    def set_password(self, raw: str):
        hashed = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt())
        self.password = hashed.decode("utf-8")

    def verify_password(self, raw: str) -> bool:
        try:
            return bcrypt.checkpw(raw.encode("utf-8"), self.password.encode("utf-8"))
        except Exception:
            return False

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "name":        self.name,
            "email":       self.email,
            "avatar":      self.avatar or "",
            "role":        self.role,
            "preferences": self.preferences or {},
            "createdAt":   self.created_at.isoformat() if self.created_at else None,
        }
