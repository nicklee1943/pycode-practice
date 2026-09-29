"""解題引導的組合邏輯（與題目資料分開）：把約束條件、pseudo code、骨架、完整實作組成 4 個階段。

題目資料來源有兩種，都用同一套邏輯：
- 開發時：guides.py + guides_ext/*.py（原始碼）
- 部署時：題庫封裝檔 *.pcbank 裡的 guides.json
"""
import re
from textwrap import dedent


def _clean(text):
    return dedent(text).strip("\n")


def sol(id, name, uses, pseudo, skeleton, code, complexity):
    return {"id": id, "name": name, "uses": uses, "pseudo": _clean(pseudo),
            "skeleton": _clean(skeleton) + "\n", "code": _clean(code) + "\n", "complexity": complexity}


# ================================================================ 組合成 4 個階段
STAGES = ["約束條件", "中文 Pseudo code", "函式骨架", "完整實作"]


def _comment_block(title, text, indent):
    lines = [f"{indent}# 【{title}】"]
    for line in _clean(text).splitlines():
        lines.append(f"{indent}# {line}" if line.strip() else f"{indent}#")
    return lines


def _anchor_re(problem):
    """約束條件要插在哪一行後面：一般題是主要方法的 def，設計題是 class 那一行。"""
    if problem.get("kind") == "design":
        return rf"\s*class {problem['class_name']}\b"
    return rf"\s*def {problem['method']}\("


def _insert_after_def(code, anchor, block):
    """把註解區塊插在錨點那一行後面。"""
    lines = code.rstrip("\n").splitlines()
    for i, line in enumerate(lines):
        if re.match(anchor, line):
            return "\n".join(lines[:i + 1] + block + lines[i + 1:]) + "\n"
    return code


def _sync_signatures(code, starter):
    """讓解答裡的方法簽名和 starter（官方初始程式碼）完全一致，例如 List[int] → list[int]。"""
    sigs = {}
    for line in starter.splitlines():
        m = re.match(r"(\s*)def (\w+)\(", line)
        if m:
            sigs[(m.group(1), m.group(2))] = line
    out = []
    for line in code.splitlines():
        m = re.match(r"(\s*)def (\w+)\(", line)
        key = m and (m.group(1), m.group(2))
        out.append(sigs.get(key, line) if key else line)
    return "\n".join(out) + ("\n" if code.endswith("\n") else "")


def pseudo_lines(s):
    """Pseudo code 的每一行（去掉空行，保留開頭縮排），交錯顯示時逐行插進程式碼。"""
    return [l.rstrip() for l in s["pseudo"].splitlines() if l.strip()]


def _interleave(code, lines, positions, drop=()):
    """把 Pseudo code 逐行以註解插進程式碼：positions[i] = 第 i 行要插在程式碼第幾行（1 起算）之前。
    註解的縮排跟著下一行程式碼（空行或檔尾就跟著上一行）。drop = 要拿掉的純註解行（和 Pseudo code 重複的提示）。"""
    src = code.rstrip("\n").splitlines()
    before = {}
    for i, pos in enumerate(positions):
        before.setdefault(pos, []).append(lines[i])

    def indent_at(k):  # 第 k 行（1 起算）的縮排
        for j in list(range(k - 1, len(src))) + list(range(k - 2, -1, -1)):
            if 0 <= j < len(src) and src[j].strip():
                return src[j][:len(src[j]) - len(src[j].lstrip())]
        return ""

    out = []
    for k in range(1, len(src) + 2):
        group = before.get(k, [])
        # 同一個位置有多行時，保留它們在 Pseudo code 裡的相對縮排（看得出巢狀關係）
        base = min((len(t) - len(t.lstrip()) for t in group), default=0)
        for text in group:
            extra = " " * (len(text) - len(text.lstrip()) - base)
            out.append(f"{indent_at(k)}# {extra}{text.strip()}")
        if k <= len(src) and k not in drop:
            out.append(src[k - 1])
    return "\n".join(out) + "\n"


def check_anchors(s, anchor):
    """交錯位置的格式檢查；回傳錯誤訊息清單（空＝合格）。"""
    errs, n = [], len(pseudo_lines(s))
    for key in ("skeleton", "code"):
        pos = (s.get("anchors") or {}).get(key)
        if pos is None:
            errs.append(f"缺少 anchors.{key}")
            continue
        src = s[key].rstrip("\n").splitlines()
        start = next((i + 1 for i, l in enumerate(src) if re.match(anchor, l)), None)
        if len(pos) != n:
            errs.append(f"anchors.{key} 有 {len(pos)} 個位置，但 Pseudo code 有 {n} 行")
        elif any(not isinstance(p, int) or not (start is not None and start < p <= len(src) + 1) for p in pos):
            errs.append(f"anchors.{key} 的位置必須在主要的 def/class 那一行（第 {start} 行）之後、最多到 {len(src) + 1}")
        drop = (s.get("anchors") or {}).get(f"{key}_drop") or []
        if any(not isinstance(d, int) or not (start is not None and start < d <= len(src))
               or not src[d - 1].strip().startswith("#") for d in drop):
            errs.append(f"anchors.{key}_drop 只能是主要 def/class 之後、只有註解的行")
    return errs


def build_solutions(pid, problem, constraints, solutions):
    """把一題的約束條件與解題方式（原始資料）組合成 4 個階段的程式碼。"""
    if not solutions.get(pid):
        return []  # 自動匯入的題目沒有解題引導
    anchor = _anchor_re(problem)
    starter = problem["starter"]
    def_line = next(l for l in starter.splitlines() if re.match(anchor, l))
    indent = " " * (len(def_line) - len(def_line.lstrip()) + 4)
    head = starter[:starter.index(def_line) + len(def_line)]
    cons = _comment_block("約束條件", constraints.get(pid, ""), indent)
    design = problem.get("kind") == "design"

    result = []
    for s in solutions.get(pid, []):
        pseudo = _comment_block("Pseudo code", s["pseudo"], indent)
        if design:
            # 設計題：保留 starter 的所有方法，把註解插在 class 那一行後面
            stage1 = _insert_after_def(starter, anchor, cons)
            stage2 = _insert_after_def(starter, anchor, cons + [indent + "#"] + pseudo)
        else:
            stage1 = head + "\n" + "\n".join(cons) + "\n" + indent
            stage2 = head + "\n" + "\n".join(cons + [indent + "#"] + pseudo) + "\n" + indent
        # 各階段是「逐步擴增」的：Pseudo code 的每一行以註解保留在程式碼裡，下方接著這一步的程式碼。
        # 階段 3 = 約束條件 + （Pseudo code 逐行 + 骨架）；階段 4 = 約束條件 + （Pseudo code 逐行 + 完整實作）
        anchors = s.get("anchors") or {}
        lines = pseudo_lines(s)
        stages = []
        for key, title in (("skeleton", "函式骨架"), ("code", "Code")):
            src = s[key]
            if anchors.get(key) and not check_anchors(s, anchor):
                src = _interleave(src, lines, anchors[key], anchors.get(f"{key}_drop") or ())
                block = cons + [indent + "#", f"{indent}# 【{title}】"]
            else:  # 還沒有交錯位置：維持原本的整段置換（約束條件 + 該階段的程式碼）
                block = cons
            stages.append(_insert_after_def(_sync_signatures(src, starter), anchor, block))
        codes = [stage1, stage2, *stages]
        steps = [{"title": title, "explain": "", "code": code} for title, code in zip(STAGES, codes)]
        steps[-1]["explain"] = f"**複雜度：** {s['complexity']}"
        result.append({"id": s["id"], "name": s["name"], "uses": s["uses"], "steps": steps})
    return result
