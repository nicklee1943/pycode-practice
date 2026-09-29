"""在獨立子行程中執行使用者的解答並比對測資。

從 stdin 讀入 JSON 規格，將結果以 JSON 寫到 stdout 的最後一行。
支援的題型與型別轉換請見 tools/AUTHORING.md。
"""
import collections
import contextlib
import copy
import io
import json
import linecache
import sys
import time
import traceback

# 模擬 LeetCode 環境中常見的預先匯入
PRELUDE = """
from typing import *
from collections import *
from functools import lru_cache, cache, reduce, cmp_to_key
from itertools import *
from heapq import *
from bisect import *
import math, heapq, bisect, collections, itertools, functools, string, re, random
"""


# ---------------------------------------------------------------- 節點類別
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

    def __repr__(self):
        return f"ListNode({self.val})"


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self):
        return f"TreeNode({self.val})"


class RandomNode:  # 138. Copy List with Random Pointer
    def __init__(self, x: int, next=None, random=None):
        self.val = int(x)
        self.next = next
        self.random = random


class GraphNode:  # 133. Clone Graph
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


class NextNode:  # 117. Populating Next Right Pointers
    def __init__(self, val=0, left=None, right=None, next=None):
        self.val = val
        self.left = left
        self.right = right
        self.next = next


class QuadNode:  # 427. Construct Quad Tree
    def __init__(self, val=False, isLeaf=False, topLeft=None, topRight=None, bottomLeft=None, bottomRight=None):
        self.val = val
        self.isLeaf = isLeaf
        self.topLeft = topLeft
        self.topRight = topRight
        self.bottomLeft = bottomLeft
        self.bottomRight = bottomRight


NODE_CLASSES = {"random": RandomNode, "graph": GraphNode, "next": NextNode, "quad": QuadNode}


# ---------------------------------------------------------------- 轉換：JSON -> Python 物件
def list_to_linked(values):
    dummy = cur = ListNode()
    for v in values:
        cur.next = ListNode(v)
        cur = cur.next
    return dummy.next


def list_to_cycle(arg):
    """[values, pos]：pos 為尾巴接回的位置，-1 表示沒有環。"""
    values, pos = arg
    nodes = [ListNode(v) for v in values]
    for a, b in zip(nodes, nodes[1:]):
        a.next = b
    if nodes and pos >= 0:
        nodes[-1].next = nodes[pos]
    return nodes[0] if nodes else None


def list_to_tree(values, cls=TreeNode):
    if not values or values[0] is None:
        return None
    root = cls(values[0])
    queue, i = [root], 1
    while queue and i < len(values):
        node = queue.pop(0)
        if i < len(values) and values[i] is not None:
            node.left = cls(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = cls(values[i])
            queue.append(node.right)
        i += 1
    return root


def list_to_random(pairs):
    """[[val, random_index 或 null], ...]"""
    nodes = [RandomNode(v) for v, _ in pairs]
    for a, b in zip(nodes, nodes[1:]):
        a.next = b
    for node, (_, r) in zip(nodes, pairs):
        node.random = nodes[r] if r is not None else None
    return nodes[0] if nodes else None


def adj_to_graph(adj):
    """鄰接串列（節點值 1..n）-> 節點 1。"""
    if not adj:
        return None
    nodes = [GraphNode(i + 1) for i in range(len(adj))]
    for node, nbrs in zip(nodes, adj):
        node.neighbors = [nodes[v - 1] for v in nbrs]
    return nodes[0]


TO_PY = {
    "ListNode": list_to_linked,
    "ListNodeCycle": list_to_cycle,
    "ListNodeList": lambda lists: [list_to_linked(x) for x in lists],
    "TreeNode": list_to_tree,
    "NextTree": lambda v: list_to_tree(v, NextNode),
    "RandomList": list_to_random,
    "GraphNode": adj_to_graph,
}


# ---------------------------------------------------------------- 轉換：Python 物件 -> JSON
def linked_to_list(node, limit=10000):
    out = []
    while node is not None and len(out) < limit:
        out.append(node.val)
        node = node.next
    return out


def tree_to_list(root):
    if root is None:
        return []
    out, queue = [], [root]
    while queue:
        node = queue.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


def random_to_list(head, limit=10000):
    nodes = []
    while head is not None and len(nodes) < limit:
        nodes.append(head)
        head = head.next
    index = {id(n): i for i, n in enumerate(nodes)}
    return [[n.val, index.get(id(n.random)) if n.random is not None else None] for n in nodes]


def graph_to_adj(node):
    if node is None:
        return []
    seen, queue = {node.val: node}, [node]
    while queue:
        cur = queue.pop(0)
        for nb in cur.neighbors:
            if nb.val not in seen:
                seen[nb.val] = nb
                queue.append(nb)
    return [[nb.val for nb in seen[v].neighbors] for v in sorted(seen)]


def next_tree_to_list(root):
    """LeetCode 117 的輸出格式：每層依 next 串起來，層與層之間用 '#' 分隔。"""
    out, level = [], root
    while level is not None:
        nxt_level, cur = None, level
        while cur is not None:
            out.append(cur.val)
            if nxt_level is None:
                nxt_level = cur.left or cur.right
            cur = cur.next
        out.append("#")
        # 下一層最左邊的節點：從這一層依 next 找第一個有子節點的
        cur, nxt_level = level, None
        while cur is not None and nxt_level is None:
            nxt_level = cur.left or cur.right
            cur = cur.next
        level = nxt_level
    return out


def quad_to_list(root):
    if root is None:
        return []
    out, queue = [], [root]
    while queue:
        node = queue.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append([int(bool(node.isLeaf)), int(bool(node.val))])
        if node.isLeaf:  # LeetCode 格式：葉節點的 4 個子節點以 null 表示
            queue.extend([None, None, None, None])
        else:
            queue.extend([node.topLeft, node.topRight, node.bottomLeft, node.bottomRight])
    while out and out[-1] is None:
        out.pop()
    return out


FROM_PY = {
    "ListNode": linked_to_list,
    "ListNodeCycle": linked_to_list,
    "ListNodeList": lambda xs: xs if xs is None else [linked_to_list(x) for x in xs],
    "TreeNode": tree_to_list,
    "TreeNodeVal": lambda n: None if n is None else n.val,
    "NextTree": next_tree_to_list,
    "RandomList": random_to_list,
    "GraphNode": graph_to_adj,
    "QuadTree": quad_to_list,
}


def collect_nodes(obj, limit=100000):
    """收集一個結構中所有節點物件的 id（用來檢查是否真的深拷貝）。"""
    seen, stack = set(), [obj]
    while stack and len(seen) < limit:
        n = stack.pop()
        if isinstance(n, (list, tuple)):
            stack.extend(n)
            continue
        if n is None or id(n) in seen or isinstance(n, (int, float, str, bool, dict)):
            continue
        seen.add(id(n))
        for attr in ("next", "random", "left", "right"):
            stack.append(getattr(n, attr, None))
        stack.extend(getattr(n, "neighbors", []) or [])
    return seen


# ---------------------------------------------------------------- 比對
def approx(a, b, tol=1e-5):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol * max(1.0, abs(b))
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(approx(x, y, tol) for x, y in zip(a, b))
    return a == b


def normalize(value, mode):
    if mode == "unordered":
        return sorted(value, key=repr)
    if mode == "unordered_nested":
        return sorted((sorted(x, key=repr) for x in value), key=repr)
    return value


def equal(actual, expected, mode):
    try:
        if mode == "float":
            return approx(actual, expected)
        return normalize(actual, mode) == normalize(expected, mode)
    except Exception:
        return False


def format_error(e):
    """只保留使用者程式碼 (solution.py) 的堆疊。"""
    frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "solution.py"]
    head = "Traceback (most recent call last):\n" if frames else ""
    return head + "".join(traceback.format_list(frames)) + "".join(traceback.format_exception_only(type(e), e))


# ---------------------------------------------------------------- 執行單一測資
def convert_args(args, arg_types):
    call_args = [
        TO_PY[arg_types[i]](a) if i < len(arg_types) and arg_types[i] in TO_PY else a
        for i, a in enumerate(args)
    ]
    # CyclePos：和 LeetCode 141 一樣，輸入是 head = [...], pos = k；pos 只用來接成環，不傳給方法
    if "CyclePos" in arg_types:
        i = arg_types.index("CyclePos")
        head, pos = call_args[i - 1], args[i]
        if head is not None and pos >= 0:
            nodes, cur = [], head
            while cur is not None:
                nodes.append(cur)
                cur = cur.next
            nodes[-1].next = nodes[pos]
        del call_args[i]
    # TreeNodeRef：用節點值在第一個樹狀參數中找到對應的節點（例如 LCA 的 p、q）
    if "TreeNodeRef" in arg_types:
        root = next((call_args[i] for i, t in enumerate(arg_types) if t in ("TreeNode", "NextTree")), None)
        by_val, stack = {}, [root]
        while stack:
            n = stack.pop()
            if n is not None:
                by_val.setdefault(n.val, n)
                stack.extend([n.left, n.right])
        for i, t in enumerate(arg_types):
            if t == "TreeNodeRef":
                call_args[i] = by_val.get(args[i])
    return call_args


def run_function_test(spec, solution_cls, test, checker):
    arg_types = spec.get("arg_types") or []
    ret_type = spec.get("return_type")
    mode = spec.get("compare", "exact")
    inplace = spec.get("inplace_arg")
    entry = {"args": test["args"], "expected": test["expected"], "hidden": test.get("hidden", False)}

    call_args = convert_args(copy.deepcopy(test["args"]), arg_types)
    input_nodes = collect_nodes(call_args) if ret_type in ("RandomList", "GraphNode") else set()
    start = time.perf_counter()
    output = getattr(solution_cls(), spec["method"])(*call_args)
    entry["time_ms"] = round((time.perf_counter() - start) * 1000, 2)

    if input_nodes and collect_nodes(output) & input_nodes:
        entry["actual"] = "（回傳的結構用到了原本的節點，必須建立全新的節點＝深拷貝）"
        entry["passed"] = False
        return entry
    if inplace is not None:
        t = arg_types[inplace] if inplace < len(arg_types) else None
        output = FROM_PY[t](call_args[inplace]) if t in FROM_PY else call_args[inplace]
    elif ret_type in FROM_PY:
        output = FROM_PY[ret_type](output)
    json.dumps(output)  # 確認可序列化
    entry["actual"] = output

    if checker:
        after = [FROM_PY[arg_types[i]](a) if i < len(arg_types) and arg_types[i] in FROM_PY else a
                 for i, a in enumerate(call_args)]
        entry["passed"] = bool(checker(copy.deepcopy(test["args"]), output, test["expected"], after))
    else:
        entry["passed"] = equal(output, test["expected"], mode)
    return entry


def run_design_test(spec, ns, test):
    """設計題：ops[0] 是建構子，其餘依序呼叫方法，比對每一步的回傳值。"""
    ops, args, expected = test["ops"], test["args"], test["expected"]
    ctor_types = spec.get("ctor_types") or []
    mode = spec.get("compare", "exact")
    entry = {"ops": ops, "args": args, "expected": expected, "hidden": test.get("hidden", False)}

    start = time.perf_counter()
    obj = ns[spec["class_name"]](*convert_args(copy.deepcopy(args[0]), ctor_types))
    outputs = [None]
    for op, a in zip(ops[1:], args[1:]):
        outputs.append(getattr(obj, op)(*copy.deepcopy(a)))
    entry["time_ms"] = round((time.perf_counter() - start) * 1000, 2)
    json.dumps(outputs)
    entry["actual"] = outputs

    def ok(out, exp):
        if isinstance(exp, dict) and "any_of" in exp:
            return any(ok(out, e) for e in exp["any_of"])
        return approx(out, exp) if mode == "float" else out == exp

    bad = next((i for i, (o, e) in enumerate(zip(outputs, expected)) if not ok(o, e)), None)
    entry["passed"] = bad is None and len(outputs) == len(expected)
    if bad is not None:
        entry["mismatch_index"] = bad
    return entry


# ---------------------------------------------------------------- 逐步除錯：錄製執行過程
MAX_STEPS = 2000  # 錄製上限（超過就只執行、不再記錄）


def _short(v, depth=0):
    """變數值的簡短顯示（容器只顯示前 20 個，巢狀最多 3 層）。無法顯示的（函式、模組）回傳 None。"""
    try:
        if v is None or isinstance(v, (bool, int, float)):
            return repr(v)
        if isinstance(v, str):
            return repr(v) if len(v) <= 60 else repr(v[:60]) + "…"
        if isinstance(v, (ListNode, RandomNode)):
            vals, seen, cur = [], set(), v
            while cur is not None and id(cur) not in seen and len(vals) < 20:
                seen.add(id(cur))
                vals.append(_short(cur.val, depth + 1))
                cur = cur.next
            tail = "→…" if cur is not None else ""
            return f"{type(v).__name__}({'→'.join(vals)}{tail})"
        if isinstance(v, (TreeNode, NextNode)):
            kids = [("L", v.left), ("R", v.right)]
            return f"{type(v).__name__}(val={_short(v.val, depth + 1)}" + "".join(
                f", {k}={'∅' if c is None else _short(c.val, depth + 1)}" for k, c in kids) + ")"
        if isinstance(v, GraphNode):
            return f"Node(val={v.val}, 鄰居={[n.val for n in v.neighbors][:20]})"
        if depth >= 3:
            return "…"
        if isinstance(v, dict):
            items = list(v.items())
            body = ", ".join(f"{_short(k, depth + 1)}: {_short(x, depth + 1)}" for k, x in items[:20])
            name = "" if type(v) is dict else type(v).__name__
            return f"{name}{{{body}{', …' if len(items) > 20 else ''}}}"
        if isinstance(v, (list, tuple, set, frozenset, collections.deque)):
            items = list(v)
            body = ", ".join(_short(x, depth + 1) for x in items[:20]) + (", …" if len(items) > 20 else "")
            if isinstance(v, list):
                return f"[{body}]"
            if isinstance(v, tuple):
                return f"({body}{',' if len(items) == 1 else ''})"
            return f"{type(v).__name__}({body})" if not isinstance(v, set) else ("{" + body + "}" if items else "set()")
        if callable(v) or isinstance(v, type(sys)):
            return None
        if hasattr(v, "__dict__"):
            attrs = {k: x for k, x in vars(v).items() if not k.startswith("_") or k == "__class__"}
            body = ", ".join(f"{k}={_short(x, depth + 1)}" for k, x in list(attrs.items())[:10])
            return f"{type(v).__name__}({body})"
        r = repr(v)
        return r if len(r) <= 80 else r[:80] + "…"
    except Exception:  # noqa: BLE001 — 顯示用，失敗就略過
        return "<?>"


class Recorder:
    """用 sys.settrace 記錄使用者程式（solution.py）每一步：行號、函式、呼叫堆疊、區域變數、已輸出多少字。"""

    def __init__(self, out):
        self.out, self.steps, self.truncated = out, [], False

    def global_trace(self, frame, event, arg):
        if self.truncated or frame.f_code.co_filename != "solution.py":
            return None
        self._add(frame, "call", arg)
        return self.local_trace

    def local_trace(self, frame, event, arg):
        if self.truncated:
            return None
        if event in ("line", "return", "exception"):
            self._add(frame, event, arg)
        return self.local_trace

    def _add(self, frame, event, arg):
        if len(self.steps) >= MAX_STEPS:
            self.truncated = True
            return
        stack, f = [], frame
        while f is not None:
            if f.f_code.co_filename == "solution.py":
                stack.append({"func": f.f_code.co_name, "line": f.f_lineno})
            f = f.f_back
        stack.reverse()
        local = {}
        for k, v in frame.f_locals.items():
            if k.startswith("__"):
                continue
            s = _short(v)
            if s is not None:
                local[k] = s
        step = {"event": event, "line": frame.f_lineno, "func": frame.f_code.co_name,
                "depth": len(stack), "stack": stack, "vars": local, "out": self.out.tell()}
        if event == "return":
            step["value"] = _short(arg)
        elif event == "exception":
            step["value"] = f"{arg[0].__name__}: {arg[1]}"
        self.steps.append(step)


# ---------------------------------------------------------------- 主程式
def main():
    sys.setrecursionlimit(10000)
    spec = json.loads(sys.stdin.read())
    real_stdout = sys.stdout
    result = {"compile_error": None, "tests": []}
    design = spec.get("kind") == "design"

    ns = {"ListNode": ListNode, "TreeNode": TreeNode, "__name__": "__solution__"}
    if spec.get("node_class") in NODE_CLASSES:
        ns["Node"] = NODE_CLASSES[spec["node_class"]]
    top_out = io.StringIO()
    target = None
    try:
        with contextlib.redirect_stdout(top_out):
            exec(PRELUDE, ns)
            # 讓 traceback 能顯示使用者程式碼的原始行
            code = spec["code"]
            linecache.cache["solution.py"] = (len(code), None, code.splitlines(True), "solution.py")
            exec(compile(code, "solution.py", "exec"), ns)
        target = ns[spec["class_name"] if design else "Solution"]
    except KeyError:
        result["compile_error"] = f"找不到 class {spec['class_name'] if design else 'Solution'}"
    except Exception as e:
        result["compile_error"] = format_error(e)

    checker = None
    if spec.get("checker"):
        cns = {}
        exec(PRELUDE, cns)
        exec(spec["checker"], cns)
        checker = cns["check"]

    if result["compile_error"] is None:
        for test in spec["tests"]:
            buf = io.StringIO()
            rec = Recorder(buf) if spec.get("trace") else None
            try:
                with contextlib.redirect_stdout(buf):
                    if rec:
                        sys.settrace(rec.global_trace)
                    try:
                        entry = run_design_test(spec, ns, test) if design else run_function_test(spec, target, test, checker)
                    finally:
                        sys.settrace(None)
            except Exception as e:
                entry = {k: test[k] for k in ("args", "ops", "expected") if k in test}
                entry["hidden"] = test.get("hidden", False)
                entry["error"] = format_error(e)
                entry["passed"] = False
            entry["stdout"] = buf.getvalue()[:5000] if not rec else buf.getvalue()[:50000]
            if rec:
                entry["trace"], entry["trace_truncated"] = rec.steps, rec.truncated
            result["tests"].append(entry)

    result["stdout"] = top_out.getvalue()[:5000]
    real_stdout.write("\n__RESULT__" + json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
