import uuid
import os
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_

from extensions import db
from models.meeting import Meeting
from middleware.auth import auth_required

meetings_bp = Blueprint("meetings", __name__)


# ── GET /api/meetings/ ────────────────────────────────────────────────────────
@meetings_bp.route("/", methods=["GET"])
@auth_required
def list_meetings(current_user):
    search       = request.args.get("search", "")
    status       = request.args.get("status", "")
    page         = int(request.args.get("page", 1))
    limit        = min(int(request.args.get("limit", 20)), 100)
    sort         = request.args.get("sort", "-createdAt")

    q = Meeting.query.filter_by(user_id=current_user.id)
    if status:
        q = q.filter(Meeting.status == status)
    if search:
        q = q.filter(or_(
            Meeting.title.ilike(f"%{search}%"),
            Meeting.description.ilike(f"%{search}%"),
        ))

    # Sorting
    asc   = not sort.startswith("-")
    field = sort.lstrip("-")
    col_map = {
        "createdAt": Meeting.created_at,
        "title":     Meeting.title,
        "duration":  Meeting.duration,
    }
    col = col_map.get(field, Meeting.created_at)
    q = q.order_by(col.asc() if asc else col.desc())

    total    = q.count()
    meetings = q.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "success": True,
        "meetings": [m.to_dict(exclude_transcript=True) for m in meetings],
        "pagination": {
            "total": total,
            "page":  page,
            "limit": limit,
            "pages": -(-total // limit),
        },
    })


# ── GET /api/meetings/stats/overview ─────────────────────────────────────────
@meetings_bp.route("/stats/overview", methods=["GET"])
@auth_required
def stats_overview(current_user):
    uid = current_user.id
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total      = Meeting.query.filter_by(user_id=uid).count()
    completed  = Meeting.query.filter_by(user_id=uid, status="completed").count()
    pending    = Meeting.query.filter(
                     Meeting.user_id == uid,
                     Meeting.status.in_(["processing", "transcribing", "analyzing"])
                 ).count()
    this_month = Meeting.query.filter(
                     Meeting.user_id == uid,
                     Meeting.created_at >= month_start
                 ).count()

    recent = (Meeting.query
              .filter_by(user_id=uid, status="completed")
              .order_by(Meeting.created_at.desc())
              .limit(5).all())

    # Action item stats
    all_meetings = Meeting.query.filter_by(user_id=uid).with_entities(Meeting.action_items).all()
    done_ai = pending_ai = 0
    for (items,) in all_meetings:
        for item in (items or []):
            if item.get("completed"):
                done_ai += 1
            else:
                pending_ai += 1

    return jsonify({
        "success": True,
        "stats": {
            "total": total, "completed": completed,
            "pending": pending, "thisMonth": this_month,
            "actionItems": {"completed": done_ai, "pending": pending_ai},
        },
        "recentMeetings": [m.to_dict(exclude_transcript=True) for m in recent],
    })


# ── GET /api/meetings/shared/<token> (public) ─────────────────────────────────
@meetings_bp.route("/shared/<token>", methods=["GET"])
def get_shared(token):
    meeting = Meeting.query.filter_by(share_token=token, is_shared=True).first()
    if not meeting:
        return jsonify({"success": False, "message": "Shared meeting not found"}), 404
    d = meeting.to_dict()
    d.pop("userId", None)
    return jsonify({"success": True, "meeting": d})


# ── GET /api/meetings/<id> ────────────────────────────────────────────────────
@meetings_bp.route("/<meeting_id>", methods=["GET"])
@auth_required
def get_meeting(current_user, meeting_id):
    meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first()
    if not meeting:
        return jsonify({"success": False, "message": "Meeting not found"}), 404
    return jsonify({"success": True, "meeting": meeting.to_dict()})


# ── GET /api/meetings/<id>/status ─────────────────────────────────────────────
@meetings_bp.route("/<meeting_id>/status", methods=["GET"])
@auth_required
def meeting_status(current_user, meeting_id):
    meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first()
    if not meeting:
        return jsonify({"success": False, "message": "Meeting not found"}), 404
    return jsonify({
        "success": True,
        "status":  meeting.status,
        "error":   meeting.processing_error,
        "title":   meeting.title,
    })


# ── PUT /api/meetings/<id> ────────────────────────────────────────────────────
@meetings_bp.route("/<meeting_id>", methods=["PUT"])
@auth_required
def update_meeting(current_user, meeting_id):
    meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first()
    if not meeting:
        return jsonify({"success": False, "message": "Meeting not found"}), 404

    data = request.get_json() or {}
    if data.get("title"):        meeting.title        = data["title"]
    if "description" in data:    meeting.description  = data["description"]
    if data.get("tags"):         meeting.tags         = data["tags"]
    if data.get("participants"): meeting.participants = data["participants"]
    db.session.commit()
    return jsonify({"success": True, "meeting": meeting.to_dict()})


# ── PATCH /api/meetings/<id>/action-items/<item_id> ───────────────────────────
@meetings_bp.route("/<meeting_id>/action-items/<item_id>", methods=["PATCH"])
@auth_required
def update_action_item(current_user, meeting_id, item_id):
    meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first()
    if not meeting:
        return jsonify({"success": False, "message": "Meeting not found"}), 404

    data  = request.get_json() or {}
    items = list(meeting.action_items or [])
    idx   = next((i for i, x in enumerate(items) if x.get("id") == item_id), None)
    if idx is None:
        return jsonify({"success": False, "message": "Action item not found"}), 404

    if "completed" in data: items[idx]["completed"] = data["completed"]
    if "assignee"  in data: items[idx]["assignee"]  = data["assignee"]
    if "dueDate"   in data: items[idx]["dueDate"]   = data["dueDate"]
    if "priority"  in data: items[idx]["priority"]  = data["priority"]

    meeting.action_items = items
    db.session.commit()
    return jsonify({"success": True, "meeting": meeting.to_dict()})


# ── POST /api/meetings/<id>/share ─────────────────────────────────────────────
@meetings_bp.route("/<meeting_id>/share", methods=["POST"])
@auth_required
def share_meeting(current_user, meeting_id):
    meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first()
    if not meeting:
        return jsonify({"success": False, "message": "Meeting not found"}), 404

    token            = str(uuid.uuid4())
    meeting.share_token = token
    meeting.is_shared   = True
    db.session.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5000")
    return jsonify({
        "success":    True,
        "shareUrl":   f"{frontend_url}/shared/{token}",
        "shareToken": token,
    })


# ── DELETE /api/meetings/<id> ─────────────────────────────────────────────────
@meetings_bp.route("/<meeting_id>", methods=["DELETE"])
@auth_required
def delete_meeting(current_user, meeting_id):
    meeting = Meeting.query.filter_by(id=meeting_id, user_id=current_user.id).first()
    if not meeting:
        return jsonify({"success": False, "message": "Meeting not found"}), 404
    db.session.delete(meeting)
    db.session.commit()
    return jsonify({"success": True, "message": "Meeting deleted"})
