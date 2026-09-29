"""LeetCode 練習平台後端 (Flask)。

啟動: python app.py  然後打開 http://127.0.0.1:5000
"""
import hashlib
import mimetypes
import json
import os
import threading
import time
import random
import re
import runpy

import auth
import bank as bankmod
import store as storemod
from guide_engine import build_solutions
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory

BASE = Path(__file__).parent
PROBLEMS_FILE = BASE / "problems.json"
PROBLEMS_EXT_DIR = BASE / "problems_ext"  # 擴充題目（每個檔案是一個題目 JSON 陣列）
SOLUTIONS_DIR = BASE / "solutions"
HARNESS = BASE / "harness.py"
GUIDES_FILE = BASE / "guides.py"
SET_FILE = SOLUTIONS_DIR / "current_set.json"  # 本次練習抽到的題目
SETTINGS_FILE = SOLUTIONS_DIR / "settings.json"  # 目前選擇的題庫
SET_SIZE = 3  # 每次刷新抽幾題（比照公司線上測驗 2～4 題）
TIMEOUT_SEC = 5
# 多人模式：程式在沙箱服務（sandbox_runner.py）的容器裡執行；沒設定就在本機執行（單人模式）
RUNNER_URL = os.environ.get("PYCODE_RUNNER_URL", "").rstrip("/")
SANDBOX_TIMEOUT, SANDBOX_TIMEOUT_TRACE = 10, 15  # 判題／逐步除錯的時間上限（秒）
RUN_PER_MINUTE = 20  # 每人每分鐘最多執行幾次

app = Flask(__name__, static_folder="static")
SOLUTIONS_DIR.mkdir(exist_ok=True)
auth.init_app(app)  # 多人模式：登入檢查；單人模式不做任何事


def load_problems():
    # 題庫來源：bank/*.pcbank 封裝檔，沒有的話用原始碼（見 bank.py）；換檔案後自動重新載入
    return sorted(bankmod.load().problems, key=lambda p: p["number"])


def get_problem(pid):
    for p in load_problems():
        if p["id"] == pid:
            return p
    abort(404, "找不到題目")


def st():
    """目前使用者的資料（程式碼、完成紀錄、題組…）：單人模式是 solutions/ 的檔案，多人模式是資料庫。"""
    if storemod.MODE == "single":
        return storemod.FileStore(SOLUTIONS_DIR)
    return storemod.DbStore(auth.current_user()["id"])


def can_manage_bank():
    """能不能匯出／更換題庫檔：單人模式可以；多人模式只有管理員。"""
    return storemod.MODE == "single" or bool((auth.current_user() or {}).get("is_admin"))


def load_guides(p):
    data = bankmod.load()
    return build_solutions(p["id"], p, data.constraints, data.solutions)


def public_view(p):
    """前端只看得到非隱藏測資。"""
    view = {k: v for k, v in p.items() if k != "tests"}
    view["examples"] = [t for t in p["tests"] if not t.get("hidden")]
    view["total_tests"] = len(p["tests"])
    return view


def status_of(p, rec):
    """solved = 提交通過過；attempted = 有寫過程式碼（和初始程式碼不同）；none = 還沒做。
    rec = 這題的紀錄（store.records() 的一筆），一次讀出所有題目的紀錄，避免逐題查詢。"""
    if rec.get("solved_at"):
        return "solved"
    if rec.get("code") is not None and rec["code"].strip() != p["starter"].strip():
        return "attempted"
    return "none"


def summary(p, records=None):
    rec = (records if records is not None else st().records()).get(p["id"], {})
    s = status_of(p, rec)
    return {"id": p["id"], "number": p["number"], "title": p["title"], "difficulty": p["difficulty"],
            "tags": p.get("tags", []), "solved": s == "solved", "status": s, "solved_at": rec.get("solved_at")}


# ---------- 題庫選擇 ----------
DEFAULT_BANK = "basic"


def bank_names():
    """題庫（basic / top150 / all）的顯示名稱，來自題庫封裝檔的 manifest。"""
    return bankmod.load().bank_names


def current_bank():
    bank = st().get_bank()
    return bank if bank in bank_names() else DEFAULT_BANK


def bank_problems(bank=None):
    bank = bank or current_bank()
    problems = load_problems()
    return problems if bank == "all" else [p for p in problems if bank in p.get("banks", ["basic"])]


def top150_categories():
    """官方題單的章節順序（題庫清單「依章節」分類用）。"""
    return bankmod.load().categories


# ---------- 本次練習的題目組（從目前題庫隨機抽出） ----------
def load_set(problems):
    ids = {p["id"] for p in problems}
    chosen = [i for i in (st().get_set() or []) if i in ids]
    return chosen or draw_set(problems, exclude=set())


def draw_set(problems, exclude):
    """隨機抽 SET_SIZE 題，盡量避開 exclude（目前這組），題庫不夠時才用重複的補。"""
    fresh = [p["id"] for p in problems if p["id"] not in exclude]
    rest = [p["id"] for p in problems if p["id"] in exclude]
    random.shuffle(fresh)
    random.shuffle(rest)
    chosen = (fresh + rest)[:SET_SIZE]
    st().set_set(chosen)
    return chosen


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/tags.js")
def tags_js():
    """標籤分類（資料結構／解題技巧），來自目前的題庫。"""
    body = "window.TAGS = " + json.dumps(bankmod.load().tags, ensure_ascii=False) + ";\n"
    return Response(body, mimetype="application/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/bank")
def bank_page():
    return send_from_directory(app.static_folder, "bank.html")


@app.get("/api/problems")
def list_problems():
    """本次練習的題目（依抽出的順序 = Question 1, 2, 3）。"""
    problems = bank_problems()
    by_id = {p["id"]: p for p in problems}
    records = st().records()
    return jsonify([summary(by_id[i], records) for i in load_set(problems)])


@app.post("/api/set/refresh")
def refresh_set():
    """換一組新題目。已寫過的程式碼、完成紀錄都保留在 solutions/。"""
    problems = bank_problems()
    draw_set(problems, exclude=set(load_set(problems)))
    return list_problems()


@app.post("/api/set/custom")
def custom_set():
    """手動組成題組：依使用者點選的順序（= Question 1, 2, 3…）。題目必須在目前的題庫中。"""
    ids = (request.get_json(silent=True) or {}).get("ids") or []
    known = {p["id"] for p in bank_problems()}
    chosen = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in known))  # 去重、保留順序
    if not chosen:
        return jsonify({"error": "沒有可用的題目（題目必須在目前的題庫中）"}), 400
    st().set_set(chosen)
    return list_problems()


@app.get("/api/banks")
def banks():
    all_problems = load_problems()
    return jsonify({
        "current": current_bank(),
        "banks": [{"id": b, "name": name, "count": len(all_problems) if b == "all"
                   else sum(b in p.get("banks", ["basic"]) for p in all_problems)}
                  for b, name in bank_names().items()],
    })


@app.post("/api/banks/select")
def select_bank():
    """切換題庫，並從新題庫重新抽一組題目。已寫過的程式碼、完成紀錄都保留。"""
    bank = (request.get_json(silent=True) or {}).get("bank")
    if bank not in bank_names():
        abort(400, "未知的題庫")
    st().set_bank(bank)
    draw_set(bank_problems(bank), exclude=set())
    return list_problems()


@app.get("/api/bank")
def bank():
    """目前題庫的所有題目，含完成狀態與是否在本次題目中。"""
    problems = bank_problems()
    current = load_set(problems)
    records = st().records()
    return jsonify({
        "bank": current_bank(),
        "bank_name": bank_names()[current_bank()],
        "categories": top150_categories(),
        "problems": [
            {**summary(p, records), "category": p.get("category"),
             "question": current.index(p["id"]) + 1 if p["id"] in current else None}
            for p in problems
        ],
    })


# ---------- 匯出 / 匯入（程式碼與紀錄） ----------
EXPORTS_DIR = BASE / "exports"
EXPORT_APP = "pycode-practice"


def _yaml_dump(data):
    import yaml

    class Dumper(yaml.SafeDumper):
        pass

    def str_presenter(dumper, s):  # 多行字串（程式碼）用 | 區塊格式，比較好讀
        return dumper.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None)

    Dumper.add_representer(str, str_presenter)
    return yaml.dump(data, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=1000)


def collect_export(guides):
    """收集所有有紀錄的題目：程式碼、引導前備份、完成時間、引導進度。"""
    problems = {}
    s = st()
    records = s.records()
    for p in load_problems():
        pid = p["id"]
        rec = {}
        r = records.get(pid, {})
        if r.get("code") is not None and r["code"].strip() != p["starter"].strip():
            rec["code"] = r["code"]
        backup = s.get_backup(pid) if r else None
        if backup is not None:
            rec["backup_code"] = backup
        if r.get("solved_at"):
            rec["solved_at"] = r["solved_at"]
        if isinstance(guides.get(pid), dict):
            rec["guide"] = guides[pid]
        if rec:
            problems[pid] = {"number": p["number"], "title": p["title"], **rec}
    return {"app": EXPORT_APP, "version": 1, "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "problems": problems}


def user_exports_dir():
    """匯出檔的資料夾：單人模式是 exports/；多人模式每個使用者一個子資料夾，彼此看不到。"""
    if storemod.MODE == "single":
        return EXPORTS_DIR
    return EXPORTS_DIR / "users" / str(auth.current_user()["id"])


def _write_export(data, fmt, prefix):
    d = user_exports_dir()
    d.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.{'yaml' if fmt == 'yaml' else 'json'}"
    text = _yaml_dump(data) if fmt == "yaml" else json.dumps(data, ensure_ascii=False, indent=2)
    (d / name).write_text(text, encoding="utf-8")
    return name, text


@app.post("/api/export")
def export_data():
    body = request.get_json(silent=True) or {}
    fmt = "yaml" if body.get("format") == "yaml" else "json"
    data = collect_export(body.get("guides") or {})
    name, text = _write_export(data, fmt, "pycode-export")
    return jsonify({"filename": name, "content": text, "count": len(data["problems"])})


@app.get("/api/exports")
def list_exports():
    d = user_exports_dir()
    files = sorted((f for f in d.glob("*") if f.is_file()), key=lambda f: f.stat().st_mtime, reverse=True) if d.exists() else []
    return jsonify([{"name": f.name, "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                    for f in files if f.suffix in (".json", ".yaml", ".yml")])


def parse_import(text, filename=""):
    """解析匯入檔（YAML 或 JSON）並檢查格式；回傳 (整理後的資料, 錯誤訊息)。"""
    import yaml
    try:
        data = json.loads(text) if filename.lower().endswith(".json") else yaml.safe_load(text)
    except Exception as e:  # noqa: BLE001
        return None, f"檔案無法解析：{e}"
    if not isinstance(data, dict) or not isinstance(data.get("problems"), dict):
        return None, "這不是 PyCode 練習的匯出檔（找不到 problems 資料）"
    known = {p["id"] for p in load_problems()}
    clean, unknown = {}, []
    for pid, rec in data["problems"].items():
        if pid not in known or not isinstance(rec, dict):
            unknown.append(str(pid))
            continue
        item = {}
        for k in ("code", "backup_code", "solved_at"):
            if isinstance(rec.get(k), str):
                item[k] = rec[k]
        if isinstance(rec.get("guide"), dict):
            item["guide"] = rec["guide"]
        if item:
            clean[pid] = item
    return {"problems": clean, "unknown": unknown, "exported_at": data.get("exported_at")}, None


@app.post("/api/import/preview")
def import_preview():
    body = request.get_json(silent=True) or {}
    if body.get("server_file"):
        f = user_exports_dir() / pathlib_name(body["server_file"])
        if not f.is_file():
            return jsonify({"error": "找不到這個檔案"}), 404
        text, name = f.read_text(encoding="utf-8"), f.name
    else:
        text, name = body.get("content") or "", body.get("filename") or ""
    data, err = parse_import(text, name)
    if err:
        return jsonify({"error": err}), 400
    ps = data["problems"].values()
    data["summary"] = {"problems": len(data["problems"]), "codes": sum("code" in r for r in ps),
                       "solved": sum("solved_at" in r for r in ps), "guides": sum("guide" in r for r in ps)}
    return jsonify(data)


def pathlib_name(name):
    """只取檔名，避免 ../ 之類的路徑。"""
    return Path(str(name)).name


@app.post("/api/import/apply")
def import_apply():
    body = request.get_json(silent=True) or {}
    guides_now = body.get("guides_now") or {}
    data, err = parse_import(json.dumps({"problems": body.get("problems") or {}}), "import.json")
    if err:
        return jsonify({"error": err}), 400
    # 匯入前先自動備份目前所有資料，匯入後覆蓋的內容隨時可以還原
    backup_name, _ = _write_export(collect_export(guides_now), "json", "auto-backup-before-import")
    s = st()
    for pid, rec in data["problems"].items():
        if "code" in rec:
            s.set_code(pid, rec["code"])
        if "backup_code" in rec:
            s.set_backup(pid, rec["backup_code"])
        if "solved_at" in rec:
            s.set_solved(pid, rec["solved_at"])
    return jsonify({"imported": len(data["problems"]), "backup": backup_name, "problems": data["problems"]})


# ---------- 題庫封裝檔：匯出 / 更換 ----------
BANK_EXT = ".pcbank"


def build_current_bank(name):
    """把目前使用中的題庫（含執行時快取的官方內容與圖片）封裝成 .pcbank bytes。"""
    data = bankmod.load()
    problems = load_problems()
    official, images = {}, {}
    for p in problems:
        off = data.official(p["id"])
        if not off and (OFFICIAL_DIR / f"{p['id']}.json").exists():
            off = json.loads((OFFICIAL_DIR / f"{p['id']}.json").read_text(encoding="utf-8"))
        if off:
            official[p["id"]] = off
            for _, url, _ in _IMG_SRC.findall(off["html"]):
                img = _img_file(url)
                blob = _local_image(img)
                if blob is not None:
                    images[img] = blob
    return bankmod.build_bytes(name, problems, data.constraints, data.solutions, data.tags,
                               data.categories, data.bank_names, official, images)


def _bank_summary(data, filename):
    return {"file": filename, "name": data.info.get("name"), "built_at": data.info.get("built_at"),
            "problems": len(data.problems),
            "banks": {b: (len(data.problems) if b == "all" else sum(b in p.get("banks", ["basic"]) for p in data.problems))
                      for b in data.bank_names},
            "bank_names": data.bank_names}


@app.get("/api/bankfile")
def bankfile_info():
    """目前使用中的題庫來源，以及 exports/ 裡可以用來更換的題庫檔。"""
    data = bankmod.load()
    files = sorted(EXPORTS_DIR.glob(f"*{BANK_EXT}"), key=lambda f: f.stat().st_mtime, reverse=True) if EXPORTS_DIR.exists() else []
    if not can_manage_bank():
        files = []  # 多人模式：只有管理員看得到、換得了題庫檔
    return jsonify({"current": {**data.info, "problems": len(data.problems)},
                    "files": [{"name": f.name, "size": f.stat().st_size,
                               "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")} for f in files]})


@app.post("/api/bankfile/export")
def bankfile_export():
    """匯出題庫：使用中的是題庫檔時，原樣複製 bank/ 裡的檔案（保留建立時間）；開發模式才從原始碼封裝。"""
    auth.require_admin()
    EXPORTS_DIR.mkdir(exist_ok=True)
    current = bankmod.bank_file()
    if current is not None:
        name, blob = current.name, current.read_bytes()
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name, blob = f"question-bank-{stamp}{BANK_EXT}", build_current_bank(f"PyCode 題庫 {stamp}")
    (EXPORTS_DIR / name).write_bytes(blob)
    return jsonify({"filename": name, "size": len(blob), "problems": len(load_problems()),
                    "copied": current is not None})


def _built_time(info):
    """題庫的建立時間（封裝檔 manifest 裡的 built_at）；原始碼模式或沒有題庫時回傳 None。"""
    try:
        return datetime.strptime(info.get("built_at") or "", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _is_older(new_info, cur_info):
    new_t, cur_t = _built_time(new_info), _built_time(cur_info)
    return new_t is not None and cur_t is not None and new_t < cur_t


@app.get("/api/bankfile/download/<name>")
def bankfile_download(name):
    auth.require_admin()
    return send_from_directory(EXPORTS_DIR, pathlib_name(name), as_attachment=True)


@app.post("/api/bankfile/upload")
def bankfile_upload():
    """上傳題庫檔（原始 bytes），先存到 exports/，回傳檢查結果；真正更換要再呼叫 /replace。"""
    auth.require_admin()
    blob = request.get_data()
    orig = pathlib_name(urllib.parse.unquote(request.headers.get("X-Filename") or "uploaded.pcbank"))
    if not blob:
        return jsonify({"error": "檔案是空的"}), 400
    EXPORTS_DIR.mkdir(exist_ok=True)
    name = f"uploaded-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{Path(orig).stem}{BANK_EXT}"
    (EXPORTS_DIR / name).write_bytes(blob)
    return bankfile_inspect_file(name)


def bankfile_inspect_file(name):
    path = EXPORTS_DIR / pathlib_name(name)
    if not path.exists():
        return jsonify({"error": "找不到這個題庫檔"}), 404
    try:
        new = bankmod.inspect_file(path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    cur = bankmod.load()
    cur_ids = {p["id"] for p in load_problems()}
    new_ids = {p["id"] for p in new.problems}
    return jsonify({"staged": path.name, "new": _bank_summary(new, path.name),
                    "current": _bank_summary(cur, cur.info.get("file") or "原始碼"),
                    "older": _is_older(new.info, cur.info),
                    "added": len(new_ids - cur_ids), "removed": sorted(cur_ids - new_ids)})


@app.post("/api/bankfile/inspect")
def bankfile_inspect():
    auth.require_admin()
    return bankfile_inspect_file((request.get_json(silent=True) or {}).get("server_file", ""))


@app.post("/api/bankfile/replace")
def bankfile_replace():
    """以 exports/ 裡的題庫檔取代目前題庫。取代前會把目前題庫備份到 exports/。"""
    auth.require_admin()
    name = pathlib_name((request.get_json(silent=True) or {}).get("server_file", ""))
    src = EXPORTS_DIR / name
    if not src.exists():
        return jsonify({"error": "找不到這個題庫檔"}), 404
    try:
        new = bankmod.inspect_file(src)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    cur = bankmod.load()
    if _is_older(new.info, cur.info):  # 不允許換成比目前更舊的題庫
        return jsonify({"error": f"這個題庫（建立於 {new.info.get('built_at')}）比目前使用中的題庫"
                                 f"（建立於 {cur.info.get('built_at')}）舊，不允許更換。"}), 409
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = None
    current = bankmod.bank_file()
    if current is not None:  # 原樣備份（保留建立時間）
        backup = f"bank-backup-before-replace-{stamp}-{current.name}"
        (EXPORTS_DIR / backup).write_bytes(current.read_bytes())
    elif load_problems():  # 開發模式：從原始碼封裝一份備份；第一次載入（沒有題庫）則不需要
        backup = f"bank-backup-before-replace-{stamp}{BANK_EXT}"
        (EXPORTS_DIR / backup).write_bytes(build_current_bank(f"更換前的題庫備份 {stamp}"))
    bankmod.BANK_DIR.mkdir(exist_ok=True)
    for old in bankmod.BANK_DIR.glob(f"*{BANK_EXT}"):
        old.unlink()  # 已經備份在 exports/
    target = bankmod.BANK_DIR / (name if not name.startswith("uploaded-") else name.split("-", 3)[-1])
    target.write_bytes(src.read_bytes())
    data = bankmod.load()  # 重新載入
    return jsonify({"current": {**data.info, "problems": len(data.problems)}, "backup": backup})


# ---------- 官方題目內容（直接從 LeetCode 取得並快取，畫面上原樣顯示） ----------
OFFICIAL_DIR = BASE / "cache" / "official"
OFFICIAL_IMG_DIR = OFFICIAL_DIR / "img"
_IMG_SRC = re.compile(r'(<img\b[^>]*?\bsrc=")((?:https?:)?//[^"]+)(")', re.I)


def _img_file(url):
    """圖片網址 → 本機快取檔名。"""
    url = "https:" + url if url.startswith("//") else url
    ext = Path(url.split("?")[0]).suffix.lower()
    return hashlib.sha1(url.encode()).hexdigest()[:16] + (ext if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp") else ".png")


def fetch_official_images(html):
    """把題目裡的圖片存到本機（離線也能顯示）。已存在的略過；失敗的留待下次。回傳失敗數。"""
    failed = 0
    for _, url, _ in _IMG_SRC.findall(html):
        dest = OFFICIAL_IMG_DIR / _img_file(url)
        if dest.exists():
            continue
        try:
            full = "https:" + url if url.startswith("//") else url
            data = urllib.request.urlopen(urllib.request.Request(full, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read()
            OFFICIAL_IMG_DIR.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        except Exception:  # noqa: BLE001
            failed += 1
    return failed


def _local_image(name):
    """圖片內容：先找題庫（封裝檔或原始碼快取），再找執行時的快取。"""
    name = Path(name).name
    data = bankmod.load().image(name)
    if data is None and (OFFICIAL_IMG_DIR / name).exists():
        data = (OFFICIAL_IMG_DIR / name).read_bytes()
    return data


def localize_images(html):
    """本機有存的圖片改用本機網址，沒有的保留原網址。"""
    def sub(m):
        name = _img_file(m.group(2))
        return m.group(1) + (f"/official-img/{name}" if _local_image(name) is not None else m.group(2)) + m.group(3)
    return _IMG_SRC.sub(sub, html)


@app.get("/official-img/<name>")
def official_img(name):
    data = _local_image(name)
    if data is None:
        abort(404)
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return Response(data, mimetype=mime, headers={"Cache-Control": "max-age=86400"})


def official_content(pid):
    """回傳 LeetCode 官方題目內容（HTML）。先看題庫，再看執行時快取，都沒有才向 LeetCode 取得；失敗回傳 None。"""
    data = bankmod.load().official(pid)
    if data:
        return data
    path = OFFICIAL_DIR / f"{pid}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    query = "query q($s: String!) { question(titleSlug: $s) { content } }"
    req = urllib.request.Request(
        "https://leetcode.com/graphql",
        data=json.dumps({"query": query, "variables": {"s": pid}}).encode(),
        headers={"Content-Type": "application/json", "Referer": f"https://leetcode.com/problems/{pid}/",
                 "User-Agent": "Mozilla/5.0"})
    try:
        content = json.loads(urllib.request.urlopen(req, timeout=15).read())["data"]["question"]["content"]
    except Exception as e:  # noqa: BLE001 — 離線或 LeetCode 無回應時退回本機版本
        print(f"[官方內容] {pid} 取得失敗：{e}", file=sys.stderr)
        return None
    if not content:
        return None
    data = {"html": content, "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    fetch_official_images(content)  # 圖片也存到本機，之後離線也能顯示
    return data


@app.get("/api/problems/<pid>/official")
def problem_official(pid):
    get_problem(pid)
    data = official_content(pid)
    if data is None:
        return jsonify({"error": "無法連線到 LeetCode"}), 503
    return jsonify({**data, "html": localize_images(data["html"])})


@app.get("/api/problems/<pid>")
def problem_detail(pid):
    p = get_problem(pid)
    view = public_view(p)
    s = st()
    view["saved_code"] = s.get_code(pid)
    view["backup_code"] = s.get_backup(pid)
    view["guides"] = load_guides(p)
    return jsonify(view)


@app.route("/api/problems/<pid>/backup", methods=["PUT", "DELETE"])
def save_backup(pid):
    get_problem(pid)
    if request.method == "DELETE":
        st().delete_backup(pid)
    else:
        data = request.get_json(force=True, silent=True) or {}
        st().set_backup(pid, data.get("code", ""))
    return jsonify({"ok": True})


@app.route("/api/problems/<pid>/code", methods=["PUT", "POST"])  # POST 給關閉頁面時的 sendBeacon 用
def save_code(pid):
    get_problem(pid)
    data = request.get_json(force=True, silent=True) or {}
    st().set_code(pid, data.get("code", ""))
    return jsonify({"ok": True})


@app.delete("/api/problems/<pid>/code")
def reset_code(pid):
    st().delete_code(pid)
    return jsonify({"ok": True})


def run_tests(p, code, tests, trace=False):
    spec = {
        "code": code,
        "tests": tests,
        "trace": trace,  # 逐步除錯：記錄每一步的執行過程
        "compare": p.get("compare", "exact"),
        # 其餘題型設定（見 tools/AUTHORING.md）原樣傳給 harness
        **{k: p.get(k) for k in ("method", "arg_types", "return_type", "inplace_arg", "kind",
                                 "class_name", "ctor_types", "node_class", "checker")},
    }
    if RUNNER_URL:  # 多人模式：交給沙箱服務，在隔離的容器裡執行
        limit = SANDBOX_TIMEOUT_TRACE if trace else SANDBOX_TIMEOUT
        try:
            req = urllib.request.Request(RUNNER_URL + "/run", data=json.dumps({"spec": spec, "timeout": limit}).encode(),
                                         headers={"Content-Type": "application/json"})
            out = json.loads(urllib.request.urlopen(req, timeout=limit + 30).read())
        except Exception as e:  # noqa: BLE001
            return {"status": "Runtime Error", "message": f"執行環境暫時無法使用，請稍後再試（{e}）"}
        if out.get("timeout"):
            return {"status": "Time Limit Exceeded", "message": f"執行超過 {limit} 秒"}
        if out.get("oom"):
            return {"status": "Runtime Error", "message": "記憶體用量超過 256 MB，程式被強制結束"}
        stdout, stderr = out.get("stdout", ""), out.get("stderr", "")
    else:  # 單人模式：直接在本機執行
        try:
            proc = subprocess.run(
                [sys.executable, "-X", "utf8", str(HARNESS)],
                input=json.dumps(spec), capture_output=True, text=True,
                encoding="utf-8", timeout=TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired:
            return {"status": "Time Limit Exceeded", "message": f"執行超過 {TIMEOUT_SEC} 秒"}
        stdout, stderr = proc.stdout, proc.stderr

    marker = stdout.rfind("__RESULT__")
    if marker == -1:
        return {"status": "Runtime Error", "message": (stderr or stdout or "未知錯誤")[-3000:]}

    result = json.loads(stdout[marker + len("__RESULT__"):])
    if result["compile_error"]:
        result["status"] = "Compile Error"
    elif any(t.get("error") for t in result["tests"]):
        result["status"] = "Runtime Error"
    elif all(t["passed"] for t in result["tests"]) and len(result["tests"]) == len(tests):
        result["status"] = "Accepted"
    else:
        result["status"] = "Wrong Answer"
    return result


# ---------- 執行次數限制（每人同時 1 個、每分鐘最多 RUN_PER_MINUTE 次） ----------
_run_locks, _run_times, _run_guard = {}, {}, threading.Lock()


def _user_key():
    u = auth.current_user()
    return u["id"] if u else 0


def run_limited(fn):
    """包住執行／除錯：同一個人同時只能有一個在跑，每分鐘有次數上限（避免把執行環境塞滿）。"""
    key = _user_key()
    with _run_guard:
        lock = _run_locks.setdefault(key, threading.Lock())
        now_t = time.time()
        recent = [t for t in _run_times.get(key, []) if now_t - t < 60]
        if len(recent) >= RUN_PER_MINUTE:
            _run_times[key] = recent
            return jsonify({"status": "Rate Limited", "message": f"每分鐘最多執行 {RUN_PER_MINUTE} 次，請稍後再試"}), 429
        recent.append(now_t)
        _run_times[key] = recent
    if not lock.acquire(blocking=False):
        return jsonify({"status": "Busy", "message": "你有一個程式正在執行，請等它完成"}), 429
    try:
        return fn()
    finally:
        lock.release()


@app.post("/api/problems/<pid>/run")
def run(pid):
    return run_limited(lambda: _run(pid))


def _run(pid):
    """Run: 只跑範例測資；Submit: 跑全部測資 (包含隱藏)。"""
    p = get_problem(pid)
    code = request.json.get("code", "")
    submit = request.json.get("submit", False)
    st().set_code(pid, code)

    tests = p["tests"] if submit else [t for t in p["tests"] if not t.get("hidden")]
    result = run_tests(p, code, tests)
    result["total"] = len(tests)

    if submit:
        # 比照線上測驗：隱藏測資只回報結果，不揭露輸入、輸出與錯誤內容
        tests_run = result.get("tests", [])
        result["passed_count"] = sum(t["passed"] for t in tests_run)
        result["tests"] = [
            t if not t["hidden"] else {
                "hidden": True, "passed": t["passed"],
                "verdict": "Passed" if t["passed"] else ("Runtime Error" if t.get("error") else "Wrong Answer"),
            }
            for t in tests_run
        ]
        if result["status"] == "Accepted":
            # 記錄最新一次通過的時間
            st().set_solved(pid, datetime.now().strftime("%Y-%m-%d %H:%M"))
    return jsonify(result)



@app.post("/api/problems/<pid>/trace")
def trace(pid):
    return run_limited(lambda: _trace(pid))


def _trace(pid):
    """逐步除錯：用指定的範例測資執行一次，回傳每一步的行號、變數與呼叫堆疊（只能用非隱藏的範例）。"""
    p = get_problem(pid)
    code = request.json.get("code", "")
    st().set_code(pid, code)
    examples = [t for t in p["tests"] if not t.get("hidden")]
    i = int(request.json.get("index", 0))
    if not 0 <= i < len(examples):
        abort(400, "沒有這個範例")
    result = run_tests(p, code, [examples[i]], trace=True)
    result["total"] = 1
    result["index"] = i
    return jsonify(result)


# ---------- 目前使用者 / 管理員（多人模式） ----------
@app.get("/api/me")
def me():
    """前端用來決定要不要顯示登出、管理員頁、題庫檔按鈕。"""
    u = auth.current_user()
    return jsonify({"mode": storemod.MODE, "can_manage_bank": can_manage_bank(),
                    "user": None if u is None else {"id": u["id"], "username": u["username"], "is_admin": bool(u["is_admin"])}})


@app.get("/admin")
def admin_page():
    if storemod.MODE != "multi":
        abort(404)
    auth.require_admin()
    return send_from_directory(app.static_folder, "admin.html")


def _progress(uid):
    """某個使用者每一題的進度（有寫過或通過過的題目），最近的在前面。"""
    by_id = {p["id"]: p for p in load_problems()}
    rows = []
    for pid, rec in storemod.DbStore(uid).records().items():
        p = by_id.get(pid)
        if p is None:
            continue
        s = status_of(p, rec)
        if s == "none":
            continue
        rows.append({"id": pid, "number": p["number"], "title": p["title"], "difficulty": p["difficulty"],
                     "status": s, "solved_at": rec.get("solved_at"), "updated_at": rec.get("updated_at")})
    rows.sort(key=lambda r: max(r["updated_at"] or "", r["solved_at"] or ""), reverse=True)
    return rows


@app.get("/api/admin/users")
def admin_users():
    auth.require_admin()
    out = []
    for u in auth.list_users():
        prog = _progress(u["id"])
        latest = prog[0] if prog else None
        out.append({**u, "solved": sum(r["status"] == "solved" for r in prog),
                    "attempted": sum(r["status"] == "attempted" for r in prog),
                    "latest": latest and {"id": latest["id"], "number": latest["number"], "title": latest["title"],
                                          "time": max(latest["updated_at"] or "", latest["solved_at"] or "")}})
    return jsonify(out)


@app.post("/api/admin/users")
def admin_create_user():
    auth.require_admin()
    body = request.get_json(silent=True) or {}
    try:
        uid = auth.create_user(body.get("username"), body.get("password"), bool(body.get("is_admin")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(auth.get_user(uid))


@app.post("/api/admin/users/<int:uid>")
def admin_update_user(uid):
    auth.require_admin()
    body = request.get_json(silent=True) or {}
    if uid == auth.current_user()["id"] and (body.get("active") is False or body.get("is_admin") is False):
        return jsonify({"error": "不能停用自己，或取消自己的管理員身分"}), 400
    if auth.get_user(uid) is None:
        abort(404)
    try:
        auth.update_user(uid, password=body.get("password") or None,
                         active=body.get("active"), is_admin=body.get("is_admin"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(auth.get_user(uid))


@app.get("/api/admin/users/<int:uid>/progress")
def admin_progress(uid):
    auth.require_admin()
    if auth.get_user(uid) is None:
        abort(404)
    return jsonify(_progress(uid))


@app.get("/api/admin/users/<int:uid>/code/<pid>")
def admin_code(uid, pid):
    auth.require_admin()
    p = get_problem(pid)
    s = storemod.DbStore(uid)
    return jsonify({"id": pid, "number": p["number"], "title": p["title"],
                    "code": s.get_code(pid), "solved_at": s.get_solved(pid)})


if __name__ == "__main__":
    # 不開自動重啟：它會監看 solutions/*.py，每次存檔都會讓伺服器重啟而連線失敗
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
