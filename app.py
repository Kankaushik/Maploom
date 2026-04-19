from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from dotenv import load_dotenv
load_dotenv()

from .db import engine, Base, get_db
from .models import User, Map, MapVersion, Feedback
from .auth import init_app as init_auth, login_user, admin_required
from .sanitizer import sanitize_html

app = Flask(__name__, static_folder="static", static_url_path="/")
CORS(app, resources={r"/api/*": {"origins": "*"}})  # okay if you keep same-origin; safe to leave enabled
init_auth(app)

# ---------- DB bootstrap ----------
def bootstrap():
    Base.metadata.create_all(bind=engine)
    # Seed default users if not present
    with Session(engine) as db:
        if not db.scalar(select(User).where(User.username == "admin")):
            admin = User.make("admin", "admin123", "admin")
            user1 = User.make("user1", "user123", "user")
            user2 = User.make("user2", "user234", "user")
            db.add_all([admin, user1, user2])
            db.commit()
bootstrap()

# ---------- Static hosting ----------
@app.get('/')
def root_index():
    return send_from_directory(app.static_folder, 'index.html')

# ---------- Auth ----------
@app.post('/api/login')
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.username == username))
        if user and user.verify(password):
            login_user(user.id, user.role)
            return jsonify({"success": True, "role": user.role})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

# ---------- Maps ----------
@app.get('/api/maps/list')
def list_maps():
    with Session(engine) as db:
        rows = db.scalars(select(Map.name)).all()
    return jsonify(rows)

@app.get('/api/maps/<string:name>')
def get_map(name: str):
    with Session(engine) as db:
        m = db.get(Map, name)
        if not m:
            return jsonify({"error": "Not found"}), 404
        out = {
            "geojson": json.loads(m.geojson) if m.geojson else None,
            "areaData": json.loads(m.areaData) if m.areaData else {},
            "imgData": {"imgSrc": m.imgSrc, "imgW": m.imgW, "imgH": m.imgH},
        }
        return jsonify(out)

@app.post('/api/maps/save')
@admin_required
def save_map():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    geojson = payload.get("geojson")
    areaData = payload.get("areaData") or {}
    imgData = payload.get("imgData") or {}

    with Session(engine) as db:
        m = db.get(Map, name)
        if m:
            # snapshot before overwrite
            snap = MapVersion(
                mapName=name,
                geojson=m.geojson,
                areaData=m.areaData,
                imgSrc=m.imgSrc,
                imgW=m.imgW,
                imgH=m.imgH,
            )
            db.add(snap)
        else:
            m = Map(name=name)
            db.add(m)

        m.geojson = json.dumps(geojson) if geojson is not None else None
        m.areaData = json.dumps(areaData) if areaData is not None else None
        m.imgSrc = imgData.get("imgSrc")
        m.imgW = imgData.get("imgW")
        m.imgH = imgData.get("imgH")
        db.commit()
        return jsonify({"ok": True})

@app.delete('/api/maps/<string:name>')
@admin_required
def delete_map(name: str):
    with Session(engine) as db:
        m = db.get(Map, name)
        if not m:
            return jsonify({"error": "Not found"}), 404
        db.delete(m)
        db.commit()
    return jsonify({"ok": True})

# ---------- Versions ----------
@app.get('/api/maps/<string:name>/versions')
@admin_required
def list_versions(name: str):
    with Session(engine) as db:
        m = db.get(Map, name)
        if not m:
            return jsonify([])
        q = select(MapVersion).where(MapVersion.mapName == name).order_by(MapVersion.id.desc())
        rows = db.scalars(q).all()
        out = [{"id": r.id, "savedAt": r.savedAt.isoformat()} for r in rows]
        return jsonify(out)

@app.post('/api/maps/<string:name>/rollback')
@admin_required
def rollback_version(name: str):
    data = request.get_json(silent=True) or {}
    snap_id = data.get("id")
    if not snap_id:
        return jsonify({"error": "id is required"}), 400

    with Session(engine) as db:
        snap = db.get(MapVersion, snap_id)
        if not snap or snap.mapName != name:
            return jsonify({"error": "Snapshot not found"}), 404
        m = db.get(Map, name)
        if not m:
            m = Map(name=name)
            db.add(m)
        # snapshot current before overwrite
        if any([m.geojson, m.areaData, m.imgSrc]):
            db.add(MapVersion(mapName=name, geojson=m.geojson, areaData=m.areaData, imgSrc=m.imgSrc, imgW=m.imgW, imgH=m.imgH))
        # restore
        m.geojson = snap.geojson
        m.areaData = snap.areaData
        m.imgSrc = snap.imgSrc
        m.imgW = snap.imgW
        m.imgH = snap.imgH
        db.commit()
        return jsonify({"ok": True})

# ---------- Feedback ----------
@app.post('/api/feedback')
def post_feedback():
    data = request.get_json(silent=True) or {}
    mapName = (data.get("mapName") or "").strip() or None
    note_raw = data.get("note") or ""
    note = sanitize_html(note_raw)
    geojson = data.get("geojson")
    with Session(engine) as db:
        fb = Feedback(mapName=mapName, note=note, geojson=json.dumps(geojson) if geojson else None)
        db.add(fb)
        db.commit()
        return jsonify({"ok": True, "id": fb.id})

@app.get('/api/feedback/list')
@admin_required
def list_feedback():
    map_name = request.args.get("map")
    with Session(engine) as db:
        q = select(Feedback).order_by(Feedback.id.desc())
        if map_name:
            q = q.where(Feedback.mapName == map_name)
        rows = db.scalars(q).all()
        out = [{
            "id": r.id,
            "mapName": r.mapName,
            "note": r.note,
            "geojson": json.loads(r.geojson) if r.geojson else None,
            "created": r.created.isoformat(),
        } for r in rows]
        return jsonify(out)

@app.delete('/api/feedback/<int:fbid>')
@admin_required
def delete_feedback(fbid: int):
    with Session(engine) as db:
        r = db.get(Feedback, fbid)
        if not r:
            return jsonify({"error": "Not found"}), 404
        db.delete(r)
        db.commit()
        return jsonify({"ok": True})

def create_app():
    return app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
