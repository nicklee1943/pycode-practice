"""多人模式的帳號與登入。單人模式（預設）完全不需要登入，這個模組的檢查都會直接放行。

- 帳號由管理員建立（沒有自行註冊）；密碼以 Werkzeug 的雜湊儲存。
- 登入狀態存在簽章過的 Cookie，記住 30 天。
- 同一個帳號連續輸錯 5 次，鎖 10 分鐘。
"""
import secrets
import threading
import time
from datetime import timedelta

from flask import abort, g, jsonify, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash

import store

MAX_FAILS, LOCK_SEC = 5, 600
_fails = {}  # username（小寫） -> [失敗次數, 鎖定到期時間]
_fails_lock = threading.Lock()

# 不需要登入就能存取的路徑
PUBLIC = ("/login", "/api/login", "/static/", "/favicon")


def secret_key():
    """簽章 Cookie 用的金鑰；第一次啟動時產生，存在資料夾裡（重啟後登入狀態仍有效）。"""
    f = store.DATA_DIR / "secret.key"
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        f.write_text(secrets.token_hex(32), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------- 帳號資料
def _row(r):
    return None if r is None else {k: r[k] for k in r.keys() if k != "pw_hash"}


def get_user(uid):
    with store.db() as c:
        return _row(c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())


def list_users():
    with store.db() as c:
        return [_row(r) for r in c.execute("SELECT * FROM users ORDER BY id")]


def check_username(name):
    name = (name or "").strip()
    if not (1 <= len(name) <= 32) or any(ch.isspace() for ch in name):
        raise ValueError("帳號需為 1～32 個字元，不能有空白")
    return name


def check_password(pw):
    if len(pw or "") < 6:
        raise ValueError("密碼至少 6 個字元")
    return pw


def create_user(username, password, is_admin=False):
    username, password = check_username(username), check_password(password)
    with store.db() as c:
        if c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise ValueError(f"帳號「{username}」已經存在")
        cur = c.execute("INSERT INTO users(username, pw_hash, is_admin, created_at) VALUES(?,?,?,?)",
                        (username, generate_password_hash(password), int(bool(is_admin)), store.now()))
        return cur.lastrowid


def update_user(uid, password=None, active=None, is_admin=None):
    sets, args = [], []
    if password is not None:
        sets.append("pw_hash=?")
        args.append(generate_password_hash(check_password(password)))
    if active is not None:
        sets.append("active=?")
        args.append(int(bool(active)))
    if is_admin is not None:
        sets.append("is_admin=?")
        args.append(int(bool(is_admin)))
    if sets:
        with store.db() as c:
            c.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", (*args, uid))


def verify(username, password):
    """回傳 (使用者, 錯誤訊息)。"""
    key = (username or "").strip().lower()
    with _fails_lock:
        n, until = _fails.get(key, (0, 0))
        if until > time.time():
            return None, f"輸入錯誤太多次，請 {int((until - time.time()) // 60) + 1} 分鐘後再試"
    with store.db() as c:
        r = c.execute("SELECT * FROM users WHERE username=?", ((username or "").strip(),)).fetchone()
    ok = r is not None and r["active"] and check_password_hash(r["pw_hash"], password or "")
    with _fails_lock:
        if ok:
            _fails.pop(key, None)
        else:
            n = _fails.get(key, (0, 0))[0] + 1
            _fails[key] = (n, time.time() + LOCK_SEC if n >= MAX_FAILS else 0)
    if not ok:
        return None, "帳號或密碼錯誤" if r is None or r["active"] else "這個帳號已停用"
    return _row(r), None


# ---------------------------------------------------------------- Flask 整合
def current_user():
    return getattr(g, "user", None)


def require_admin():
    if store.MODE == "multi" and not (current_user() or {}).get("is_admin"):
        abort(403, "只有管理員可以使用這個功能")


def init_app(app):
    if store.MODE != "multi":
        return
    app.secret_key = secret_key()
    app.permanent_session_lifetime = timedelta(days=30)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

    @app.before_request
    def _login_required():
        g.user = None
        uid = session.get("uid")
        if uid:
            u = get_user(uid)
            if u and u["active"]:
                g.user = u
                _touch(uid)
        if g.user or request.path.startswith(PUBLIC):
            return None
        if request.path.startswith("/api/"):
            return jsonify({"error": "請先登入", "login": True}), 401
        return redirect("/login?next=" + request.full_path.rstrip("?"))

    @app.get("/login")
    def login_page():
        return app.send_static_file("login.html")

    @app.post("/api/login")
    def api_login():
        body = request.get_json(silent=True) or {}
        user, err = verify(body.get("username"), body.get("password"))
        if err:
            return jsonify({"error": err}), 401
        session.clear()
        session.permanent = True
        session["uid"] = user["id"]
        return jsonify({"ok": True, "user": user})

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return jsonify({"ok": True})


_last_touch = {}


def _touch(uid):
    """更新「最後上線時間」（每分鐘最多寫一次資料庫）。"""
    t = time.time()
    if t - _last_touch.get(uid, 0) < 60:
        return
    _last_touch[uid] = t
    with store.db() as c:
        c.execute("UPDATE users SET last_seen=? WHERE id=?", (store.now(), uid))
