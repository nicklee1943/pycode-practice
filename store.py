"""使用者資料的儲存：程式碼、引導前備份、完成紀錄、目前題組、題庫選擇。

兩種實作，介面相同，app.py 只透過 current_store() 存取：
- FileStore：單人模式（預設）。資料是 solutions/ 裡的檔案，和原本完全一樣。
- DbStore：多人模式（環境變數 PYCODE_MODE=multi）。資料在 SQLite，每個使用者分開。
"""
import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODE = "multi" if os.environ.get("PYCODE_MODE") == "multi" else "single"
DATA_DIR = Path(os.environ.get("PYCODE_DATA") or BASE / "data")
DB_FILE = DATA_DIR / "pycode.db"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- 單人模式：檔案
class FileStore:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(exist_ok=True)

    def _p(self, pid, suffix=".py"):
        return self.dir / f"{pid.replace('/', '_')}{suffix}"

    def get_code(self, pid):
        f = self._p(pid)
        return f.read_text(encoding="utf-8") if f.exists() else None

    def set_code(self, pid, code):
        self._p(pid).write_text(code, encoding="utf-8")

    def delete_code(self, pid):
        self._p(pid).unlink(missing_ok=True)

    def get_backup(self, pid):
        f = self._p(pid, ".backup.py")
        return f.read_text(encoding="utf-8") if f.exists() else None

    def set_backup(self, pid, code):
        self._p(pid, ".backup.py").write_text(code, encoding="utf-8")

    def delete_backup(self, pid):
        self._p(pid, ".backup.py").unlink(missing_ok=True)

    def get_solved(self, pid):
        f = self._p(pid, ".solved")
        if not f.exists():
            return None
        return f.read_text(encoding="utf-8").strip() or datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    def set_solved(self, pid, when):
        self._p(pid, ".solved").write_text(when, encoding="utf-8")

    def _json(self, name):
        try:
            return json.loads((self.dir / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def get_set(self):
        return self._json("current_set.json").get("ids")

    def set_set(self, ids):
        (self.dir / "current_set.json").write_text(json.dumps({"ids": ids}, ensure_ascii=False), encoding="utf-8")

    def get_bank(self):
        return self._json("settings.json").get("bank")

    def set_bank(self, bank):
        (self.dir / "settings.json").write_text(json.dumps({"bank": bank}, ensure_ascii=False), encoding="utf-8")

    def records(self):
        """所有題目的紀錄 {pid: {"code", "solved_at", "updated_at"}}（題庫清單一次算完所有題目的狀態用）。"""
        out = {}
        for f in self.dir.glob("*.py"):
            if f.name.endswith(".backup.py"):
                continue
            out.setdefault(f.stem, {})["code"] = f.read_text(encoding="utf-8")
            out[f.stem]["updated_at"] = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        for f in self.dir.glob("*.solved"):
            out.setdefault(f.stem, {})["solved_at"] = self.get_solved(f.stem)
        return out


# ---------------------------------------------------------------- 多人模式：SQLite
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pw_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_seen TEXT
);
CREATE TABLE IF NOT EXISTS codes (
    user_id INTEGER NOT NULL, pid TEXT NOT NULL, code TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, pid)
);
CREATE TABLE IF NOT EXISTS backups (
    user_id INTEGER NOT NULL, pid TEXT NOT NULL, code TEXT NOT NULL,
    PRIMARY KEY (user_id, pid)
);
CREATE TABLE IF NOT EXISTS solved (
    user_id INTEGER NOT NULL, pid TEXT NOT NULL, solved_at TEXT NOT NULL,
    PRIMARY KEY (user_id, pid, solved_at)
);
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY, bank TEXT, set_ids TEXT
);
"""
_init_lock = threading.Lock()
_initialized = [False]


def db():
    """每次操作開一個連線（SQLite 開連線很便宜，也避免跨執行緒共用連線）。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    if not _initialized[0]:
        with _init_lock:
            if not _initialized[0]:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(SCHEMA)
                _initialized[0] = True
    return conn


class DbStore:
    def __init__(self, user_id):
        self.uid = user_id

    def _one(self, sql, *args):
        with db() as c:
            row = c.execute(sql, (self.uid, *args)).fetchone()
        return row[0] if row else None

    def _exec(self, sql, *args):
        with db() as c:
            c.execute(sql, (self.uid, *args))

    def get_code(self, pid):
        return self._one("SELECT code FROM codes WHERE user_id=? AND pid=?", pid)

    def set_code(self, pid, code):
        self._exec("INSERT INTO codes(user_id, pid, code, updated_at) VALUES(?,?,?,?) "
                   "ON CONFLICT(user_id, pid) DO UPDATE SET code=excluded.code, updated_at=excluded.updated_at",
                   pid, code, now())

    def delete_code(self, pid):
        self._exec("DELETE FROM codes WHERE user_id=? AND pid=?", pid)

    def get_backup(self, pid):
        return self._one("SELECT code FROM backups WHERE user_id=? AND pid=?", pid)

    def set_backup(self, pid, code):
        self._exec("INSERT INTO backups(user_id, pid, code) VALUES(?,?,?) "
                   "ON CONFLICT(user_id, pid) DO UPDATE SET code=excluded.code", pid, code)

    def delete_backup(self, pid):
        self._exec("DELETE FROM backups WHERE user_id=? AND pid=?", pid)

    def get_solved(self, pid):
        """最新一次通過的時間。"""
        return self._one("SELECT MAX(solved_at) FROM solved WHERE user_id=? AND pid=?", pid)

    def set_solved(self, pid, when):
        self._exec("INSERT OR IGNORE INTO solved(user_id, pid, solved_at) VALUES(?,?,?)", pid, when)

    def _settings(self):
        with db() as c:
            row = c.execute("SELECT bank, set_ids FROM settings WHERE user_id=?", (self.uid,)).fetchone()
        return row

    def get_set(self):
        row = self._settings()
        return json.loads(row["set_ids"]) if row and row["set_ids"] else None

    def set_set(self, ids):
        self._exec("INSERT INTO settings(user_id, set_ids) VALUES(?,?) "
                   "ON CONFLICT(user_id) DO UPDATE SET set_ids=excluded.set_ids", json.dumps(ids))

    def get_bank(self):
        row = self._settings()
        return row["bank"] if row else None

    def set_bank(self, bank):
        self._exec("INSERT INTO settings(user_id, bank) VALUES(?,?) "
                   "ON CONFLICT(user_id) DO UPDATE SET bank=excluded.bank", bank)

    def records(self):
        out = {}
        with db() as c:
            for r in c.execute("SELECT pid, code, updated_at FROM codes WHERE user_id=?", (self.uid,)):
                out.setdefault(r["pid"], {}).update(code=r["code"], updated_at=r["updated_at"])
            for r in c.execute("SELECT pid, MAX(solved_at) AS t FROM solved WHERE user_id=? GROUP BY pid", (self.uid,)):
                out.setdefault(r["pid"], {})["solved_at"] = r["t"]
        return out
