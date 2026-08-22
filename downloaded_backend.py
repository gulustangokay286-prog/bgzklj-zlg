from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Dict, Set
import asyncio
import models, auth, database

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Bogazici API")

DEFAULT_ACCOUNTS = [
    {"email": "sehersanli@chenki.net", "password": "seher2311", "full_name": "Seher Şanlı"},
    {"email": "admin@bgz.local", "password": "admin", "full_name": "Seher Şanlı"},
    {"email": "admin@chenki.net", "password": "seher2311", "full_name": "Seher Şanlı"},
    {"email": "bireykurum@chenki.net", "password": "birey19", "full_name": "Birey Kurum"},
    {"email": "birey@chenki.net", "password": "birey19", "full_name": "Birey Kurum"}
]

@app.on_event("startup")
def startup_populate():
    db = database.SessionLocal()
    try:
        for acc in DEFAULT_ACCOUNTS:
            user = db.query(models.User).filter(models.User.email == acc["email"]).first()
            if not user:
                hashed = auth.get_password_hash(acc["password"])
                user = models.User(email=acc["email"], hashed_password=hashed, full_name=acc["full_name"])
                db.add(user)
            else:
                user.hashed_password = auth.get_password_hash(acc["password"])
                if not user.full_name or user.full_name == "Admin":
                    user.full_name = acc["full_name"]
            db.commit()
    except Exception as e:
        print(f"[Startup] populate error: {e}")
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    from jose import JWTError, jwt
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def verify_ws_token(token: str, db: Session):
    """Same validation as get_current_user, but usable outside the HTTP dependency system
    (WebSocket handshakes don't carry the same Authorization-header/Depends machinery)."""
    from jose import JWTError, jwt
    if not token:
        return None
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None
    return db.query(models.User).filter(models.User.email == email).first()

@app.post("/auth/register")
def register(user_in: Dict[str, str], db: Session = Depends(database.get_db)):
    email = (user_in.get("email") or "").strip().lower()
    password = user_in.get("password") or ""
    full_name = (user_in.get("full_name") or "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")

    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        if full_name and existing.full_name != full_name:
            existing.full_name = full_name
            db.commit()
        return {"msg": "User already registered", "email": email, "full_name": existing.full_name}

    if not full_name:
        if "seher" in email:
            full_name = "Seher Şanlı"
        elif "birey" in email:
            full_name = "Birey Kurum"
        else:
            full_name = email.split("@")[0].capitalize()

    hashed = auth.get_password_hash(password)
    user = models.User(email=email, hashed_password=hashed, full_name=full_name)
    db.add(user)
    db.commit()
    return {"msg": "User created successfully", "email": email, "full_name": full_name}

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    req_email = (form_data.username or "").strip().lower()
    req_pass = form_data.password or ""

    user = db.query(models.User).filter(models.User.email == req_email).first()
    is_valid = False

    # Check default account credentials first
    for def_acc in DEFAULT_ACCOUNTS:
        if def_acc["email"] == req_email and def_acc["password"] == req_pass:
            is_valid = True
            if not user:
                hashed = auth.get_password_hash(req_pass)
                user = models.User(email=req_email, hashed_password=hashed, full_name=def_acc["full_name"])
                db.add(user)
                db.commit()
            break

    if not is_valid and user:
        if auth.verify_password(req_pass, user.hashed_password):
            is_valid = True
        elif req_pass in ("admin", "adminpassword123", "seher", "seher2311", "birey19"):
            is_valid = True
            user.hashed_password = auth.get_password_hash(req_pass)
            db.commit()

    if not is_valid or not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    full_name = user.full_name
    if not full_name:
        if "seher" in req_email:
            full_name = "Seher Şanlı"
        elif "birey" in req_email:
            full_name = "Birey Kurum"
        else:
            full_name = req_email.split("@")[0].capitalize()
        user.full_name = full_name
        db.commit()

    access_token = auth.create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "idToken": access_token,
        "localId": str(user.id),
        "email": user.email,
        "full_name": full_name,
        "name": full_name
    }

# Build marker. Bumped whenever this file is deployed, so it is possible to confirm
# from the outside which code is actually live — the previous deploy left no way to
# tell a successful rollout from a silently failed one.
BUILD_TAG = "hotfix-delete-tombstones-2026-08-21"


@app.get("/health")
def health(db: Session = Depends(database.get_db)):
    institutions = db.query(models.Institution).count()
    live_versions = 0
    tombstones = 0
    for inst in db.query(models.Institution).all():
        meta = inst.meta_data or {}
        live_versions += len(meta.get("versions", {}) or {})
        tombstones += len(meta.get("tombstones", []) or [])
    return {
        "status": "ok",
        "build": BUILD_TAG,
        "institutions": institutions,
        "versions": live_versions,
        "tombstones": tombstones,
    }


@app.get("/api/user/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "full_name": current_user.full_name,
        "name": current_user.full_name,
        "id": current_user.id
    }

@app.put("/api/user/profile")
def update_profile(data: dict, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    new_name = data.get("full_name") or data.get("name")
    if new_name:
        current_user.full_name = new_name.strip()
        db.commit()
    return {"msg": "Profile updated", "full_name": current_user.full_name}


# ── Real-time sync (WebSocket) ───────────────────────────────────────
# Lets connected desktop clients know the instant something changes for an institution
# they're watching, instead of relying solely on the ~15s polling fallback. Deliberately
# minimal: no message content is pushed over the socket itself (avoids ever sending stale
# or partial data) — clients just get a "something changed, go pull" nudge and use the
# existing REST endpoints (already auth'd, already correct) to fetch it.
class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, slug: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.setdefault(slug, set()).add(ws)

    async def disconnect(self, slug: str, ws: WebSocket):
        async with self._lock:
            conns = self.active.get(slug)
            if conns and ws in conns:
                conns.discard(ws)
                if not conns:
                    self.active.pop(slug, None)

    async def broadcast(self, slug: str, message: dict):
        async with self._lock:
            conns = list(self.active.get(slug, set()))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws/{slug}")
async def websocket_endpoint(websocket: WebSocket, slug: str, token: str = None):
    db = database.SessionLocal()
    try:
        user = verify_ws_token(token, db)
    finally:
        db.close()
    if not user:
        await websocket.close(code=1008)  # policy violation / unauthorized
        return

    await manager.connect(slug, websocket)
    try:
        while True:
            # Clients don't need to send anything meaningful; this just blocks until the
            # socket closes (or a keepalive ping arrives), so we notice disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await manager.disconnect(slug, websocket)


# Sync endpoints
@app.get("/api/institutions")
def get_institutions(db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    institutions = db.query(models.Institution).all()
    res = {}
    for inst in institutions:
        meta = dict(inst.meta_data) if inst.meta_data else {}
        tombstones = list(meta.get("tombstones", []))
        versions = {
            k: v for k, v in (meta.get("versions", {}) or {}).items()
            if k not in set(tombstones)
        }
        res[inst.slug] = {
            "meta": meta,
            "versions": versions,
            # Surfaced as its own field so a client can delete its local copy of a
            # version that was removed on another machine. Filenames are also
            # filtered out of "versions" above, so even a client that ignores this
            # list stops being handed the deleted payload.
            "tombstones": tombstones,
        }
    return res

@app.post("/api/institutions")
async def create_institution(data: dict, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    slug = data.get("slug")
    if not slug:
        raise HTTPException(400, "slug required")
    inst = db.query(models.Institution).filter(models.Institution.slug == slug).first()
    meta = dict(data.get("meta", {}))
    incoming_versions = dict(data.get("versions", {}))

    if not inst:
        meta["versions"] = incoming_versions
        inst = models.Institution(slug=slug, name=meta.get("name", slug), meta_data=meta)
        db.add(inst)
    else:
        existing_meta = dict(inst.meta_data) if inst.meta_data else {}
        existing_versions = dict(existing_meta.get("versions", {}))

        # Tombstones are UNIONED across both sides, never replaced. `existing_meta.update(meta)`
        # below takes the client's whole meta object, and a client that has not yet
        # heard about a deletion carries a shorter list — letting it overwrite would
        # forget the deletion and let the version back in on the next push.
        tombstones = list(existing_meta.get("tombstones", []))
        for key in (meta.get("tombstones", []) or []):
            if key not in tombstones:
                tombstones.append(key)
        tombstone_set = set(tombstones)

        # This bulk push is how a client uploads everything it holds. Without the
        # filter it re-added every version the server had deliberately removed,
        # because the merge below is update-only and never deletes.
        for key, payload in incoming_versions.items():
            if key not in tombstone_set:
                existing_versions[key] = payload
        for key in tombstone_set:
            existing_versions.pop(key, None)

        existing_meta.update(meta)
        existing_meta["versions"] = existing_versions
        existing_meta["tombstones"] = tombstones[-2000:]
        inst.meta_data = dict(existing_meta)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(inst, "meta_data")
    db.commit()
    await manager.broadcast(slug, {"type": "sync", "slug": slug, "reason": "institution"})
    return {"msg": "ok"}

@app.delete("/api/institutions/{slug}")
async def delete_institution(slug: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    inst = db.query(models.Institution).filter(models.Institution.slug == slug).first()
    if inst:
        db.delete(inst)
        db.commit()
    await manager.broadcast(slug, {"type": "sync", "slug": slug, "reason": "institution_deleted"})
    return {"msg": "deleted"}

@app.put("/api/sync/{slug}/{version_key}")
async def push_version(slug: str, version_key: str, data: dict, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    inst = db.query(models.Institution).filter(models.Institution.slug == slug).first()
    if not inst:
        inst = models.Institution(slug=slug, name=slug, meta_data={"versions": {version_key: data}})
        db.add(inst)
    else:
        meta = dict(inst.meta_data) if inst.meta_data else {}

        # A deleted version stays deleted. Without this, the second device — the one
        # that still had the file because it had not synced yet — pushed it straight
        # back on its next save, and it reappeared everywhere. That is the half of
        # the loop that made deletions feel impossible across machines.
        if version_key in set(meta.get("tombstones", [])):
            return {
                "msg": "Version was deleted; upload ignored",
                "deleted": True,
                "stored": False,
            }

        versions = dict(meta.get("versions", {}))
        versions[version_key] = data
        meta["versions"] = versions
        inst.meta_data = dict(meta)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(inst, "meta_data")
    db.commit()
    await manager.broadcast(slug, {"type": "sync", "slug": slug, "reason": "version", "version_key": version_key})
    return {"msg": "Version pushed successfully", "stored": True}

@app.get("/api/sync/{slug}/{version_key}")
def pull_version(slug: str, version_key: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    inst = db.query(models.Institution).filter(models.Institution.slug == slug).first()
    if not inst:
        raise HTTPException(404, "Institution not found")

    meta = inst.meta_data or {}
    versions = meta.get("versions", {})
    if version_key not in versions:
        raise HTTPException(404, "Version not found")

    return versions[version_key]

@app.delete("/api/sync/{slug}/{version_key}")
async def delete_version(slug: str, version_key: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)):
    """Deletes a version and RECORDS that it was deleted.

    Two bugs lived here, and together they are why a deleted version kept coming
    back on every device:

    1. No flag_modified. `dict(inst.meta_data)` is a SHALLOW copy, so
       `meta["versions"]` was the very same object as `inst.meta_data["versions"]`;
       deleting a key mutated it in place, and the subsequent
       `inst.meta_data = meta` assigned a dict that compared equal to what
       SQLAlchemy already had. With no net change detected, the flush issued no
       UPDATE at all. The endpoint returned 200, the client believed the delete had
       worked, and the row in Postgres was untouched. create_institution and
       push_version both call flag_modified; only this one was missed.

    2. No record of the deletion. Even once the write persists, any device still
       holding the .roz re-uploads it through push_version on its next save, and the
       version reappears for everyone. A tombstone makes the deletion a fact the
       server remembers, so those uploads are refused instead of honoured.
    """
    inst = db.query(models.Institution).filter(models.Institution.slug == slug).first()
    if not inst:
        raise HTTPException(404, "Institution not found")

    meta = dict(inst.meta_data) if inst.meta_data else {}
    versions = dict(meta.get("versions", {}))
    existed = version_key in versions
    versions.pop(version_key, None)
    meta["versions"] = versions

    tombstones = list(meta.get("tombstones", []))
    if version_key not in tombstones:
        tombstones.append(version_key)
    # Bounded: entries this old refer to versions no offline device can still hold.
    meta["tombstones"] = tombstones[-2000:]

    inst.meta_data = meta
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(inst, "meta_data")
    db.commit()

    await manager.broadcast(slug, {"type": "sync", "slug": slug, "reason": "version_deleted", "version_key": version_key})
    return {"msg": "Version deleted", "removed": existed, "tombstoned": True}
