"""題庫載入：把「題目、解題引導、官方內容與圖片、標籤、題單章節」統一成同一份資料。

兩種來源（自動判斷）：
1. 題庫封裝檔：bank/ 資料夾裡的 *.pcbank（有多個時用最新的那個）。部署時使用。
   要更新題庫，只要換掉這個檔案；每次請求都會檢查檔案是否變動，換了馬上生效，不用重啟。
2. 原始碼：problems.json + problems_ext/、guides.py + guides_ext/、cache/official/。開發時使用。

封裝檔格式（zip）：
    manifest.json        題庫名稱、建立時間、題數、題庫（basic/top150…）名稱
    problems.json        所有題目（含測資）
    guides.json          {題目 id: {"constraints": "...", "solutions": [ {...}, ... ]}}
    tags.json            標籤分類 {"dataStructures": [...], "techniques": [...]}
    categories.json      官方題單章節順序
    official/<id>.json   LeetCode 官方題目內容（HTML）
    official/img/<檔名>  題目裡的圖片
"""
import json
import runpy
import threading
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
BANK_DIR = BASE / "bank"
FORMAT = "pycode-bank"
DEFAULT_BANK_NAMES = {"basic": "基礎練習", "top150": "LeetCode Top Interview 150", "all": "全部題目"}

_lock = threading.Lock()
_cache = {"key": None, "data": None}


class BankData:
    def __init__(self, problems, constraints, solutions, tags, categories, bank_names, info,
                 official_reader, image_reader):
        self.problems = problems            # list[dict]
        self.constraints = constraints      # {pid: str}
        self.solutions = solutions          # {pid: [sol dict]}
        self.tags = tags                    # {"dataStructures": [...], "techniques": [...]}
        self.categories = categories        # list[str]
        self.bank_names = bank_names        # {"basic": "...", ...}
        self.info = info                    # 題庫來源說明（顯示用）
        self._official = official_reader    # pid -> dict | None
        self._image = image_reader          # name -> bytes | None

    def official(self, pid):
        return self._official(pid)

    def image(self, name):
        return self._image(name)


def bank_file():
    """bank/ 裡最新的 *.pcbank；沒有就回傳 None（改用原始碼）。"""
    files = sorted(BANK_DIR.glob("*.pcbank"), key=lambda f: f.stat().st_mtime) if BANK_DIR.exists() else []
    return files[-1] if files else None


def load():
    """取得目前的題庫資料；來源檔案變動時自動重新載入。"""
    f = bank_file()
    if f is not None:
        st = f.stat()
        key = ("file", str(f), st.st_mtime, st.st_size)
    elif (BASE / "problems.json").exists():
        key = ("source", _source_signature())  # 原始碼有任何檔案變動就重新讀
    else:
        key = ("none",)    # 剛安裝、還沒載入題庫
    with _lock:
        if _cache["key"] == key:
            return _cache["data"]
        data = _load_file(f) if key[0] == "file" else _load_source() if key[0] == "source" else _empty()
        _cache.update(key=key, data=data)
        return data


def _empty():
    info = {"source": "none", "file": None, "name": "尚未載入題庫", "built_at": None, "problems": 0}
    return BankData([], {}, {}, {"dataStructures": [], "techniques": []}, [], dict(DEFAULT_BANK_NAMES), info,
                    lambda pid: None, lambda name: None)


# ---------------------------------------------------------------- 建立與檢查封裝檔
def build_bytes(name, problems, constraints, solutions, tags, categories, bank_names, official, images):
    """把題庫資料封裝成 .pcbank（zip）並回傳 bytes。official: {pid: {...}}，images: {檔名: bytes}。"""
    import io
    from datetime import datetime
    ids = {p["id"] for p in problems}
    counts = {b: (len(problems) if b == "all" else sum(b in p.get("banks", ["basic"]) for p in problems))
              for b in bank_names}
    manifest = {"format": FORMAT, "version": 1, "name": name,
                "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "problems": len(problems), "bank_names": bank_names, "bank_counts": counts}
    guides = {pid: {"constraints": constraints.get(pid, ""), "solutions": solutions.get(pid, [])} for pid in sorted(ids)}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1)  # noqa: E731
        z.writestr("manifest.json", dump(manifest))
        z.writestr("problems.json", dump(sorted(problems, key=lambda p: p["number"])))
        z.writestr("guides.json", dump(guides))
        z.writestr("tags.json", dump(tags))
        z.writestr("categories.json", dump(categories))
        for pid, data in sorted(official.items()):
            if pid in ids and data:
                z.writestr(f"official/{pid}.json", json.dumps(data, ensure_ascii=False))
        for img, data in sorted(images.items()):
            z.writestr(f"official/img/{img}", data)
    return buf.getvalue()


def inspect_file(path):
    """檢查封裝檔是否可用，回傳摘要（不會套用）。有問題時丟出 ValueError。"""
    try:
        data = _load_file(Path(path))
    except (zipfile.BadZipFile, KeyError, ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"不是有效的 PyCode 題庫檔：{e}") from e
    for p in data.problems:
        missing = [k for k in ("id", "number", "title", "starter", "tests") if k not in p]
        if missing:
            raise ValueError(f"題目 {p.get('id', '?')} 缺少欄位 {missing}")
    return data


# ---------------------------------------------------------------- 封裝檔
def _load_file(path):
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        manifest = json.loads(z.read("manifest.json"))
        if manifest.get("format") != FORMAT:
            raise ValueError(f"{path.name} 不是 PyCode 題庫封裝檔")
        problems = json.loads(z.read("problems.json"))
        guides = json.loads(z.read("guides.json"))
        tags = json.loads(z.read("tags.json"))
        categories = json.loads(z.read("categories.json")) if "categories.json" in names else []
        # 官方內容與圖片不大（數 MB），一次讀進記憶體，之後檔案被替換也不受影響
        official = {n[len("official/"):-len(".json")]: json.loads(z.read(n))
                    for n in names if n.startswith("official/") and n.endswith(".json") and "/img/" not in n}
        images = {n[len("official/img/"):]: z.read(n) for n in names if n.startswith("official/img/") and not n.endswith("/")}
    info = {"source": "file", "file": path.name, "name": manifest.get("name"), "built_at": manifest.get("built_at"),
            "problems": len(problems)}
    return BankData(
        problems=problems,
        constraints={pid: g.get("constraints", "") for pid, g in guides.items()},
        solutions={pid: g.get("solutions", []) for pid, g in guides.items()},
        tags=tags, categories=categories,
        bank_names=_all_last({**DEFAULT_BANK_NAMES, **manifest.get("bank_names", {})}),
        info=info, official_reader=official.get, image_reader=images.get)


def _all_last(names):
    """「全部題目」固定排在題庫選單的最後。"""
    return {**{k: v for k, v in names.items() if k != "all"}, "all": names.get("all", DEFAULT_BANK_NAMES["all"])}


# ---------------------------------------------------------------- 原始碼
def _source_signature():
    """原始碼相關檔案的修改時間；任何一個變動就重新載入。"""
    files = [BASE / "problems.json", BASE / "guides.py", BASE / "guide_engine.py", BASE / "static" / "tags.js",
             BASE / "tools" / "top150_list.py",
             *sorted((BASE / "problems_ext").glob("*.json")), *sorted((BASE / "guides_ext").glob("*.py")),
             *sorted((BASE / "guides_ext" / "annotations").glob("*.json"))]
    return tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in files if f.exists())


def bank_names_for(problems):
    """題庫顯示名稱；LeetCode database 題庫的名稱會帶上實際題數。"""
    names = {k: v for k, v in DEFAULT_BANK_NAMES.items() if k != "all"}
    n = sum("db" in p.get("banks", []) for p in problems)
    if n:
        names["db"] = f"LeetCode database ({n})"
    names["all"] = DEFAULT_BANK_NAMES["all"]
    return names


def _load_source():
    problems = json.loads((BASE / "problems.json").read_text(encoding="utf-8"))
    for path in sorted((BASE / "problems_ext").glob("*.json")):
        try:
            problems.extend(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as e:  # 單一檔案壞掉時略過，不影響其他題目
            import sys
            print(f"[略過] {path.name}: {e}", file=sys.stderr)
    g = runpy.run_path(str(BASE / "guides.py"))
    for p in problems:  # 自動匯入的題目：中文說明與解題方向寫在 guides_ext 的 ZH 裡
        for k, v in g.get("ZH", {}).get(p["id"], {}).items():
            if not p.get(k):
                p[k] = v
    t = (BASE / "static" / "tags.js").read_text(encoding="utf-8")
    tags = json.loads(t[t.index("{"):t.rindex("}") + 1])
    top = BASE / "tools" / "top150_list.py"
    categories = list(dict.fromkeys(r[4] for r in runpy.run_path(str(top))["TOP150"])) if top.exists() else []
    off_dir = BASE / "cache" / "official"

    def official(pid):
        f = off_dir / f"{Path(pid).name}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def image(name):
        f = off_dir / "img" / Path(name).name
        return f.read_bytes() if f.exists() else None

    info = {"source": "source", "file": None, "name": "原始碼（開發模式）", "built_at": None, "problems": len(problems)}
    return BankData(problems, g["CONSTRAINTS"], g["SOLUTIONS"], tags, categories, bank_names_for(problems), info,
                    official, image)
