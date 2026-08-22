"""
api_client.py — HTTP client for the VDS backend.

Two behaviours in the previous version caused real damage and are gone:

1. _request_with_retry answered any 401 by logging back in with hardcoded founder
   credentials. Every user therefore had full write access to every institution
   regardless of the account they signed in with, and the credentials shipped inside
   the binary. A 401 now surfaces as a failed request; only a genuine re-login with
   the user's own stored token is attempted.

2. pull_all_from_rtdb wrote the server's "meta" object straight into the local
   meta.json — and that object still contained the entire version history, because
   the old backend stored versions inside institution meta. Each institution's
   meta.json therefore grew to the size of its whole schedule history, and
   get_institution_meta() (called dozens of times per dashboard refresh) re-parsed
   it every time. Meta and version payloads are now strictly separated.

The sync itself is now incremental: /api/sync/delta returns only what changed since
the client's stored cursor, instead of re-downloading every schedule every 15s.
"""
import json
import os
import re
import shutil
import threading

import requests

BASE_URL = os.environ.get("CHENKI_API_URL", "http://213.142.159.36")

# Network calls happen from the GUI thread (rarely), several background workers and
# the sync loop. Sessions are per-thread; this lock only serialises token refresh so
# two threads can't both decide to re-login at once.
_AUTH_LOCK = threading.Lock()


def _config_dir() -> str:
    base_dir = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass
    return base_dir


def _get_token_file_path() -> str:
    return os.path.join(_config_dir(), "bgz_auth_token.json")


def _get_cursor_file_path() -> str:
    return os.path.join(_config_dir(), "sync_cursor.json")


def _strip_versions(meta: dict) -> dict:
    """Institution meta must never carry version payloads — see the module docstring."""
    if not isinstance(meta, dict):
        return {}
    return {k: v for k, v in meta.items() if k != "versions"}


class APIClient:
    def __init__(self):
        self.base_url = BASE_URL.rstrip("/")
        self.token = self.load_token()
        self._local = threading.local()
        self._supports_delta = None  # probed once, then remembered

    # ── Session ───────────────────────────────────────────────────────────

    @property
    def session(self):
        if not hasattr(self._local, "session"):
            sess = requests.Session()
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=4, pool_maxsize=8, max_retries=0
            )
            sess.mount("http://", adapter)
            sess.mount("https://", adapter)
            self._local.session = sess
        return self._local.session

    # ── Token storage ─────────────────────────────────────────────────────

    def load_token(self):
        try:
            with open(_get_token_file_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None
        tok = data.get("access_token")
        # "local_*" tokens come from the offline fallback below and are meaningless
        # to the server; sending one just produces a 401 loop.
        if tok and not str(tok).startswith("local_") and not data.get("is_local"):
            return tok
        return None

    def save_token(self, token_data):
        self.token = (
            token_data.get("access_token") if isinstance(token_data, dict) else None
        )
        if self.token and str(self.token).startswith("local_"):
            self.token = None
        try:
            with open(_get_token_file_path(), "w", encoding="utf-8") as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[APIClient] save_token warning: {exc}")

    def delete_token(self):
        self.token = None
        try:
            path = _get_token_file_path()
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def _stored_credentials(self):
        """Email/password the user themselves signed in with, for silent refresh.

        Only ever the current user's own credentials — never a built-in admin.
        """
        try:
            with open(_get_token_file_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("email"), data.get("_refresh")
        except Exception:
            return None, None

    # ── Auth ──────────────────────────────────────────────────────────────

    # Offline fallback. These unlock the LOCAL, on-disk data when the VDS cannot be
    # reached; they never yield a cloud token and never grant server-side write
    # access, which is enforced by the backend rather than trusted from here.
    LOCAL_ACCOUNTS = {
        "sehersanli@chenki.net": {"password": "seher2311", "role": "admin", "uid": "seher_admin", "full_name": "Seher Şanlı"},
        "admin@chenki.net": {"password": "seher2311", "role": "admin", "uid": "admin_chenki", "full_name": "Seher Şanlı"},
        "bireykurum@chenki.net": {"password": "birey19", "role": "viewer", "uid": "birey_viewer", "full_name": "Birey Kurum"},
        "birey@chenki.net": {"password": "birey19", "role": "viewer", "uid": "birey_viewer", "full_name": "Birey Kurum"},
    }

    def login(self, email, password):
        url = f"{self.base_url}/auth/login"
        try:
            resp = self.session.post(
                url, data={"username": email, "password": password}, timeout=8
            )
            if resp.status_code == 200:
                token_data = resp.json()
                token_data["email"] = email
                token_data.setdefault("role", "viewer")
                if not token_data.get("full_name"):
                    token_data["full_name"] = email.split("@")[0].capitalize()
                token_data["name"] = token_data["full_name"]
                # Kept so an expired token can be renewed without prompting again.
                token_data["_refresh"] = password
                self.save_token(token_data)
                return True, token_data
            if resp.status_code == 401:
                return False, "E-posta veya şifre hatalı."
        except Exception:
            pass  # unreachable server -> offline fallback below

        account = self.LOCAL_ACCOUNTS.get((email or "").strip().lower())
        if account and account["password"] == password:
            token_data = {
                "access_token": f"local_{account['uid']}",
                "email": email,
                "uid": account["uid"],
                "role": account["role"],
                "full_name": account["full_name"],
                "name": account["full_name"],
                "is_local": True,
                "is_offline": True,
            }
            self.save_token(token_data)
            return True, token_data

        return False, "E-posta veya şifre hatalı."

    def get_current_role(self):
        try:
            with open(_get_token_file_path(), "r", encoding="utf-8") as f:
                return json.load(f).get("role", "viewer")
        except Exception:
            return "viewer"

    def is_admin(self):
        return self.get_current_role() == "admin"

    def ensure_authenticated(self) -> bool:
        """True when a usable server token is held.

        Never falls back to built-in credentials; if the stored token is gone the
        user is asked to sign in again, which is the only correct outcome.
        """
        if self.token and not str(self.token).startswith("local_"):
            return True
        with _AUTH_LOCK:
            if self.token and not str(self.token).startswith("local_"):
                return True
            self.token = self.load_token()
            if self.token:
                return True
            email, password = self._stored_credentials()
            if email and password:
                ok, _ = self.login(email, password)
                return bool(ok and self.token)
        return False

    def get_headers(self):
        if not self.ensure_authenticated():
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def _request_with_retry(self, method, url, **kwargs):
        headers = kwargs.pop("headers", None) or self.get_headers()
        timeout = kwargs.pop("timeout", 10)
        try:
            resp = self.session.request(method, url, headers=headers, timeout=timeout, **kwargs)
        except Exception:
            return None

        if resp.status_code != 401:
            return resp

        # Token expired: renew with the signed-in user's own credentials, once.
        email, password = self._stored_credentials()
        if not (email and password):
            return resp
        with _AUTH_LOCK:
            ok, _ = self.login(email, password)
        if not ok:
            return resp
        try:
            return self.session.request(
                method, url, headers=self.get_headers(), timeout=timeout, **kwargs
            )
        except Exception:
            return None

    # ── Sync cursor ───────────────────────────────────────────────────────

    def _load_cursor(self) -> int:
        try:
            with open(_get_cursor_file_path(), "r", encoding="utf-8") as f:
                return int(json.load(f).get("rev", 0))
        except Exception:
            return 0

    def _save_cursor(self, rev: int):
        try:
            with open(_get_cursor_file_path(), "w", encoding="utf-8") as f:
                json.dump({"rev": int(rev)}, f)
        except Exception:
            pass

    def reset_cursor(self):
        """Forces the next sync to be a full reconciliation."""
        self._save_cursor(0)

    # ── Pull ──────────────────────────────────────────────────────────────

    def pull_all_from_rtdb(self, auth_data=None):
        """Brings local storage in line with the VDS.

        Prefers the incremental /api/sync/delta endpoint and falls back to the full
        /api/institutions listing against an older server.
        """
        if self._supports_delta is not False:
            result = self._pull_delta()
            if result is not None:
                return result
        return self._pull_full()

    def _pull_delta(self):
        """Incremental sync. Returns None if the server has no delta endpoint."""
        since = self._load_cursor()
        resp = self._request_with_retry(
            "GET", f"{self.base_url}/api/sync/delta", params={"since": since}, timeout=20
        )
        if resp is None:
            return False, "Sunucuya ulaşılamadı.", 0
        if resp.status_code == 404:
            self._supports_delta = False
            return None  # old server — caller falls back to the full pull
        if resp.status_code != 200:
            return False, f"Buluttan veri çekilemedi (HTTP {resp.status_code})", 0

        try:
            payload = resp.json()
        except Exception as exc:
            return False, f"Sunucu yanıtı okunamadı ({exc})", 0

        self._supports_delta = True

        import version_store
        base_dir = version_store._ensure_base()
        changed = 0

        for inst in payload.get("institutions", []):
            slug = inst.get("slug")
            if not slug:
                continue
            inst_dir = os.path.join(base_dir, slug)
            if inst.get("deleted"):
                if os.path.isdir(inst_dir):
                    shutil.rmtree(inst_dir, ignore_errors=True)
                    changed += 1
                continue
            os.makedirs(os.path.join(inst_dir, "versions"), exist_ok=True)
            self._merge_meta(inst_dir, _strip_versions(inst.get("meta") or {}), inst.get("name"))
            changed += 1

        # Local tombstones are read once per institution rather than per version;
        # each read parses meta.json.
        tombstones_by_slug = {}

        def _tombstones(slug):
            if slug not in tombstones_by_slug:
                tombstones_by_slug[slug] = version_store.list_tombstones(slug)
            return tombstones_by_slug[slug]

        for ver in payload.get("versions", []):
            slug = ver.get("slug")
            filename = ver.get("filename")
            if not (slug and filename):
                continue
            ver_dir = os.path.join(base_dir, slug, "versions")
            target = os.path.join(ver_dir, filename)

            if ver.get("deleted"):
                # The server says this was deleted. Record it locally as well, so the
                # deletion survives even if this device never sees that delta again.
                version_store.merge_tombstones(slug, [filename])
                tombstones_by_slug.pop(slug, None)
                if os.path.exists(target):
                    try:
                        os.remove(target)
                        version_store.invalidate_version_summary(slug, filename)
                        changed += 1
                    except OSError:
                        pass
                continue

            # THE resurrection bug. This branch used to write whatever the server
            # sent, with no regard for whether the user had deleted it here. So a
            # delete that had not yet stuck server-side — or that another device had
            # re-uploaded — came straight back down on the very next poll, over and
            # over. A locally tombstoned version is never written, and any copy
            # already on disk is removed instead.
            if filename in _tombstones(slug):
                if os.path.exists(target):
                    try:
                        os.remove(target)
                        version_store.invalidate_version_summary(slug, filename)
                        changed += 1
                    except OSError:
                        pass
                # Re-assert the deletion against the server; it evidently still has it.
                version_store.queue_cloud_delete(slug, filename)
                continue

            data = ver.get("data")
            if not isinstance(data, dict) or not data:
                continue
            os.makedirs(ver_dir, exist_ok=True)
            if self._write_if_different(target, data):
                version_store.invalidate_version_summary(slug, filename)
                changed += 1

        head = int(payload.get("head", 0) or 0)
        if head:
            self._save_cursor(head)
        version_store.invalidate_cross_busy_cache()

        if changed:
            return True, f"Senkronizasyon tamamlandı ({changed} değişiklik).", changed
        return True, "Her şey güncel.", 0

    def _pull_full(self):
        """Full reconciliation — first run, or an older server without /api/sync/delta."""
        resp = self._request_with_retry(
            "GET", f"{self.base_url}/api/institutions", timeout=30
        )
        if resp is None or resp.status_code != 200:
            code = resp.status_code if resp is not None else "timeout"
            return False, f"Buluttan veri çekilemedi (HTTP {code})", 0

        try:
            data = resp.json()
        except Exception as exc:
            return False, f"Sunucu yanıtı okunamadı ({exc})", 0
        if not isinstance(data, dict):
            return True, "Bulutta kayıtlı kurum bulunamadı.", 0

        import version_store
        base_dir = version_store._ensure_base()
        synced = 0
        cloud_slugs = set(data.keys())

        # Institutions the server no longer has.
        try:
            for item in os.listdir(base_dir):
                path = os.path.join(base_dir, item)
                if (os.path.isdir(path) and item not in cloud_slugs
                        and item not in ("backups", "temp", "cache")):
                    shutil.rmtree(path, ignore_errors=True)
        except Exception as exc:
            print(f"[APIClient] cleanup notice: {exc}")

        base_dir = version_store._ensure_base()
        
        del_inst = []
        tomb_file = os.path.join(base_dir, "deleted_institutions.json")
        try:
            if os.path.exists(tomb_file):
                with open(tomb_file, "r", encoding="utf-8") as f:
                    del_inst = json.load(f)
        except Exception:
            pass
            
        existing_local = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))] if os.path.exists(base_dir) else []
        remote_slugs = set(data.keys())
        for l_slug in existing_local:
            if l_slug not in remote_slugs or l_slug in del_inst:
                try:
                    import shutil
                    shutil.rmtree(os.path.join(base_dir, l_slug), ignore_errors=True)
                    synced += 1
                except Exception:
                    pass

        for slug, inst_obj in data.items():
            if slug in del_inst:
                try:
                    self.delete_institution_from_rtdb(slug)
                except Exception:
                    pass
                continue
            if not isinstance(inst_obj, dict):
                continue
            inst_dir = os.path.join(base_dir, slug)
            ver_dir = os.path.join(inst_dir, "versions")
            os.makedirs(ver_dir, exist_ok=True)

            self._merge_meta(inst_dir, _strip_versions(inst_obj.get("meta") or {}))

            # Tombstones tell us which local files to drop. Record them locally too,
            # so this device keeps refusing the version even if the server later
            # forgets (an older build, or a purge of old tombstones).
            server_tombstones = inst_obj.get("tombstones", []) or []
            if server_tombstones:
                version_store.merge_tombstones(slug, server_tombstones)
            for filename in server_tombstones:
                target = os.path.join(ver_dir, filename)
                if os.path.exists(target):
                    try:
                        os.remove(target)
                        version_store.invalidate_version_summary(slug, filename)
                        synced += 1
                    except OSError:
                        pass

            # Anything tombstoned locally but still present on disk (restored by an
            # older build before these rules existed) goes now.
            synced += version_store.enforce_tombstones(slug)

            index = inst_obj.get("version_index")
            if index:
                synced += self._sync_from_index(slug, ver_dir, index)
                continue

            local_meta = version_store.get_institution_meta(slug)
            local_tombstones = set(local_meta.get("tombstones", []) or [])

            # Legacy shape: full payloads inline.
            remote_filenames = set()
            for v_key, roz in (inst_obj.get("versions") or {}).items():
                if not isinstance(roz, dict):
                    continue
                filename = (roz.get("_version_meta") or {}).get("filename") or _key_to_filename(str(v_key))

                # NEVER restore tombstoned (deleted) versions!
                if filename in local_tombstones:
                    target = os.path.join(ver_dir, filename)
                    if os.path.exists(target):
                        try:
                            os.remove(target)
                            version_store.invalidate_version_summary(slug, filename)
                        except OSError:
                            pass
                    continue

                remote_filenames.add(filename)
                if self._write_if_different(os.path.join(ver_dir, filename), roz):
                    version_store.invalidate_version_summary(slug, filename)
                    synced += 1

            # A version missing from the server's payload is NOT evidence that it was
            # deleted. It is far more often one this device just created whose upload
            # has not landed yet, or one the server omitted from a partial response.
            # Deleting on that basis (the old rule: gone from the payload and older
            # than ten seconds) destroyed freshly saved schedules — the work was on
            # screen one moment and the file was gone the next.
            #
            # Deletions travel as tombstones, which are applied above. That is the only
            # thing allowed to remove a local version.

        version_store.invalidate_cross_busy_cache()
        return True, f"Senkronizasyon tamamlandı ({len(data)} kurum, {synced} değişiklik).", synced

    def _sync_from_index(self, slug, ver_dir, index) -> int:
        """Downloads only the versions this device doesn't already hold.

        The index carries each version's content hash, so an unchanged schedule costs
        one string comparison instead of re-downloading and rewriting the file — the
        old pull rewrote everything on every poll.
        """
        import version_store

        synced = 0
        wanted = set()
        # Deleted here means deleted, whatever the server's index still advertises.
        # Without this check the index branch happily re-downloaded a version the
        # user had just removed.
        tombstoned = version_store.list_tombstones(slug)

        for entry in index:
            filename = entry.get("filename")
            if not filename:
                continue
            if filename in tombstoned:
                target = os.path.join(ver_dir, filename)
                if os.path.exists(target):
                    try:
                        os.remove(target)
                        version_store.invalidate_version_summary(slug, filename)
                        synced += 1
                    except OSError:
                        pass
                version_store.queue_cloud_delete(slug, filename)
                continue
            wanted.add(filename)
            target = os.path.join(ver_dir, filename)
            remote_hash = entry.get("content_hash") or ""

            if os.path.exists(target) and remote_hash:
                try:
                    with open(target, "r", encoding="utf-8") as f:
                        local = json.load(f)
                    if version_store.compute_data_hash(local) == remote_hash:
                        continue  # identical content, nothing to fetch
                except Exception:
                    pass

            body = self._request_with_retry(
                "GET",
                f"{self.base_url}/api/sync/{slug}/{filename_to_key(filename)}",
                timeout=25,
            )
            if body is None or body.status_code != 200:
                continue
            try:
                roz = body.json()
            except Exception:
                continue
            if isinstance(roz, dict) and self._write_if_different(target, roz):
                version_store.invalidate_version_summary(slug, filename)
                synced += 1

        return synced

    @staticmethod
    def _write_if_different(path: str, payload: dict) -> bool:
        """Writes only when remote content is actually newer or different, never reverts newer local changes."""
        import version_store

        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)

                local_meta = existing.get("_version_meta", {}) if isinstance(existing, dict) else {}
                remote_meta = payload.get("_version_meta", {}) if isinstance(payload, dict) else {}

                # Only a real last_modified on BOTH sides can decide this. The old code
                # fell back to "timestamp", which is the version's CREATION time and
                # never changes — so a local file that had merely been opened could
                # out-rank a genuinely newer edit from another computer and block it
                # forever. Mixing the two fields compared a modification time against
                # a creation time, which is not a comparison at all.
                local_ts = str(local_meta.get("last_modified") or "")
                remote_ts = str(remote_meta.get("last_modified") or "")
                if local_ts and remote_ts and local_ts > remote_ts:
                    return False

                # If content hash and folder_id are identical, nothing to rewrite
                if (version_store.compute_data_hash(existing) == version_store.compute_data_hash(payload)
                        and local_meta.get("folder_id") == remote_meta.get("folder_id")):
                    return False
        except Exception:
            pass
        return version_store._atomic_write_json(path, payload)

    @staticmethod
    def _merge_meta(inst_dir: str, remote_meta: dict, name: str = None):
        """Merges server meta into local meta.json without losing local-only state.

        Folders are union-merged by id. A folder is created locally first and pushed
        from a background thread; a pull landing in between used to overwrite the
        local list and delete the folder the user had just made.
        """
        import version_store

        meta_path = os.path.join(inst_dir, "meta.json")
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                local_meta = json.load(f)
        except Exception:
            local_meta = {}

        merged = dict(local_meta)
        merged.update(remote_meta)
        if name:
            merged.setdefault("name", name)
        merged.pop("versions", None)

        # Tombstones are UNIONED, never replaced. merged.update() above takes the
        # server's list wholesale, and the server is always at least one round-trip
        # behind a delete made here a moment ago — so overwriting would silently drop
        # that tombstone and let the version come back on the very next pull. This is
        # also how a deletion made on Windows reaches a Mac: the union travels in
        # both directions through the institution meta.
        combined_tombstones = list(local_meta.get("tombstones", []) or [])
        for name_ in (remote_meta.get("tombstones", []) or []):
            if name_ not in combined_tombstones:
                combined_tombstones.append(name_)
        if combined_tombstones:
            merged["tombstones"] = combined_tombstones[-2000:]

        local_folders = {f.get("id"): f for f in local_meta.get("folders", []) if isinstance(f, dict) and f.get("id")}
        remote_folders = {f.get("id"): f for f in remote_meta.get("folders", []) if isinstance(f, dict) and f.get("id")}
        deleted_folders = set(local_meta.get("deleted_folders", []))
        
        combined = {}
        for fid, folder in remote_folders.items():
            if fid not in deleted_folders:
                combined[fid] = folder
                
        for fid, folder in local_folders.items():
            if fid not in deleted_folders:
                combined.setdefault(fid, folder)
                
        if combined:
            merged["folders"] = list(combined.values())
        else:
            merged["folders"] = []
            
        if deleted_folders:
            merged["deleted_folders"] = list(deleted_folders)

        # Teacher hour reservations and published availability are stamped with the
        # time they were last edited. merged.update() above would hand the win to the
        # server unconditionally, and the server is a round-trip behind an edit made
        # here seconds ago — so a reservation could vanish the moment a poll landed.
        # Keep whichever side is actually newer; that also lets an edit made on another
        # computer win here, which is the point of syncing them at all.
        for block_key in ("teacher_reservations", "teacher_availability"):
            local_block = local_meta.get(block_key)
            remote_block = remote_meta.get(block_key)
            if not isinstance(local_block, dict):
                continue
            if not isinstance(remote_block, dict):
                merged[block_key] = local_block
                continue
            if str(local_block.get("updated") or "") > str(remote_block.get("updated") or ""):
                merged[block_key] = local_block

        version_store._atomic_write_json(meta_path, merged)
        version_store._invalidate_meta_cache(os.path.basename(inst_dir.rstrip(os.sep)))

    # ── Push ──────────────────────────────────────────────────────────────

    def push_version_to_rtdb(self, slug, filename, roz_data, auth_data=None):
        if not isinstance(roz_data, dict) or not roz_data:
            return False

        # Never upload something this device has deleted. This is the half of the
        # loop that made a delete un-stick across machines: device A deletes, device
        # B still has the file and pushes it on its next save or manual sync, and the
        # version reappears on A. Re-assert the deletion instead.
        import version_store
        if version_store.is_tombstoned(slug, filename):
            version_store.queue_cloud_delete(slug, filename)
            return False

        url = f"{self.base_url}/api/sync/{slug}/{filename_to_key(filename)}"
        resp = self._request_with_retry("PUT", url, json=roz_data, timeout=25)
        if resp is None or resp.status_code not in (200, 201):
            return False

        # The server reports when it folded this push into an existing identical
        # version, or refused to resurrect a deleted one. Acting on that here is what
        # keeps the two sides from disagreeing about which files exist.
        try:
            info = resp.json()
        except Exception:
            return True

        if info.get("deleted"):
            self._drop_local_version(slug, filename)
        elif info.get("deduplicated") and info.get("filename") and info["filename"] != filename:
            self._drop_local_version(slug, filename)
        return True

    @staticmethod
    def _drop_local_version(slug, filename):
        import version_store

        path = os.path.join(version_store._versions_dir(slug), filename)
        try:
            if os.path.exists(path):
                os.remove(path)
                version_store.invalidate_version_summary(slug, filename)
        except OSError:
            pass

    def push_institution_meta(self, slug: str, meta: dict) -> bool:
        payload = {"slug": slug, "meta": _strip_versions(meta)}
        resp = self._request_with_retry(
            "POST", f"{self.base_url}/api/institutions", json=payload, timeout=15
        )
        return resp is not None and resp.status_code in (200, 201)

    def delete_institution_from_rtdb(self, slug: str, auth_data=None) -> bool:
        resp = self._request_with_retry(
            "DELETE", f"{self.base_url}/api/institutions/{slug}", timeout=15
        )
        return resp is not None and resp.status_code in (200, 204)

    def delete_version_from_rtdb(self, slug: str, filename: str, auth_data=None) -> bool:
        resp = self._request_with_retry(
            "DELETE",
            f"{self.base_url}/api/sync/{slug}/{filename_to_key(filename)}",
            timeout=15,
        )
        return resp is not None and resp.status_code in (200, 204)

    # ── Updates ───────────────────────────────────────────────────────────

    def get_latest_release(self):
        """Update manifest, or None. Needs no authentication by design."""
        try:
            resp = self.session.get(f"{self.base_url}/api/updates", timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, dict) and data.get("version") else None
        except Exception:
            pass
        return None


def filename_to_key(filename: str) -> str:
    """Escapes a .roz filename for use in a URL path segment."""
    return re.sub(r"[\.\$#\[\]/]", "_", filename or "")


def _key_to_filename(version_key: str) -> str:
    """Inverse of filename_to_key.

    Only the trailing "_roz" is the extension. str.replace("_roz", ".roz") rewrote
    every occurrence and corrupted any filename containing "_roz" earlier on.
    """
    key = (version_key or "").strip()
    if key.endswith("_roz"):
        return key[: -len("_roz")] + ".roz"
    return key if key.endswith(".roz") else key + ".roz"


api_client = APIClient()
# Older call sites referred to this name; main.py's logout path imported
# `token_manager` and silently swallowed the ImportError, so signing out never
# actually cleared the stored token.
token_manager = api_client
