// Python 語法速查（編輯器右鍵說明用）。只收錄 LeetCode 解題常用的內建函式、型別方法與標準函式庫。
// owner：builtin = 內建函式／型別；keyword = 關鍵字；list/dict/str/set/deque/Counter/heap = 物件方法；
//        collections/heapq/bisect/math/itertools/functools/string/random/typing = 模組。
window.PYDOC = (() => {
  const E = {};
  const add = (name, owner, sig, desc, example) => (E[name] = E[name] || []).push({ owner, sig, desc, example });

  // ---------------------------------------------------------------- 內建函式
  add('len', 'builtin', 'len(s)', '回傳容器（list、str、dict、set…）的元素個數。O(1)。',
    'len([3, 1, 2])      # 3\nlen("abc")          # 3\nlen({"a": 1})       # 1');
  add('range', 'builtin', 'range(stop) / range(start, stop[, step])', '產生整數序列，不包含 stop。step 可以是負數（倒著數）。',
    'list(range(4))         # [0, 1, 2, 3]\nlist(range(2, 8, 2))   # [2, 4, 6]\nlist(range(3, -1, -1)) # [3, 2, 1, 0]');
  add('enumerate', 'builtin', 'enumerate(iterable, start=0)', '走訪時同時取得索引與值。',
    'for i, x in enumerate(["a", "b"]):\n    print(i, x)   # 0 a / 1 b\nlist(enumerate("ab", 1))  # [(1, "a"), (2, "b")]');
  add('zip', 'builtin', 'zip(*iterables)', '把多個序列「對齊」成一組組 tuple，長度以最短的為準。zip(*matrix) 可轉置矩陣。',
    'list(zip([1, 2], "ab"))       # [(1, "a"), (2, "b")]\nlist(zip(*[[1, 2], [3, 4]]))  # [(1, 3), (2, 4)] 轉置');
  add('sorted', 'builtin', 'sorted(iterable, key=None, reverse=False)', '回傳排序後的新 list（原本的不變）。穩定排序，O(n log n)。key 指定排序依據。',
    'sorted([3, 1, 2])                    # [1, 2, 3]\nsorted(["bb", "a"], key=len)         # ["a", "bb"]\nsorted(pairs, key=lambda p: (p[0], -p[1]))  # 先依 p[0] 遞增，再依 p[1] 遞減');
  add('reversed', 'builtin', 'reversed(seq)', '回傳倒序的迭代器（不建立新 list）。',
    'list(reversed([1, 2, 3]))  # [3, 2, 1]\nfor i in reversed(range(3)): ...  # 2, 1, 0');
  add('sum', 'builtin', 'sum(iterable, start=0)', '加總。',
    'sum([1, 2, 3])            # 6\nsum(x * x for x in nums)  # 平方和\nsum(row.count(1) for row in grid)');
  add('min', 'builtin', 'min(iterable, key=None, default=...) / min(a, b, ...)', '取最小值。空序列會出錯，可給 default。',
    'min(3, 1, 2)                  # 1\nmin(words, key=len)           # 最短的字串\nmin([], default=0)            # 0');
  add('max', 'builtin', 'max(iterable, key=None, default=...) / max(a, b, ...)', '取最大值。空序列會出錯，可給 default。',
    'max([3, 1, 2])                # 3\nmax(cnt, key=cnt.get)         # 出現次數最多的 key\nbest = max(best, cur)');
  add('abs', 'builtin', 'abs(x)', '絕對值。', 'abs(-5)   # 5\nabs(a - b)');
  add('divmod', 'builtin', 'divmod(a, b)', '同時回傳 (a // b, a % b)。', 'q, r = divmod(17, 5)   # q = 3, r = 2');
  add('pow', 'builtin', 'pow(base, exp[, mod])', '次方；給 mod 時用快速冪計算 base**exp % mod，也可用 exp = -1 求模反元素。',
    'pow(2, 10)            # 1024\npow(2, 100, 10**9 + 7)\npow(3, -1, 7)         # 5，因為 3*5 % 7 == 1');
  add('round', 'builtin', 'round(x, ndigits=None)', '四捨五入（.5 時取偶數，銀行家捨入）。', 'round(2.5)      # 2\nround(3.14159, 2)  # 3.14');
  add('int', 'builtin', 'int(x) / int(s, base)', '轉成整數；字串可指定進位。對浮點數是無條件捨去（往 0）。',
    'int("42")        # 42\nint("1011", 2)   # 11\nint(-3.7)        # -3');
  add('str', 'builtin', 'str(x)', '轉成字串。', 'str(123)          # "123"\n"".join(str(d) for d in digits)');
  add('float', 'builtin', 'float(x)', '轉成浮點數；float("inf") 是正無窮大，常當初始最小值。', 'best = float("inf")\nfloat("3.5")   # 3.5');
  add('bool', 'builtin', 'bool(x)', '轉成布林值。0、空字串、空容器、None 都是 False。', 'bool([])   # False\nbool("0")  # True');
  add('list', 'builtin', 'list(iterable)', '建立 list；也可用來複製。', 'list("abc")      # ["a", "b", "c"]\ncopy = list(nums)\ngrid = [[0] * n for _ in range(m)]  # 二維陣列（不要用 [[0]*n]*m）');
  add('dict', 'builtin', 'dict(...)', '建立字典（雜湊表），查詢／插入平均 O(1)。', 'd = {}\nd = dict(zip(keys, values))\nd = {x: i for i, x in enumerate(nums)}');
  add('set', 'builtin', 'set(iterable)', '建立集合（不重複），查詢 x in s 平均 O(1)。', 'seen = set()\nset([1, 1, 2])   # {1, 2}\na & b, a | b, a - b   # 交集、聯集、差集');
  add('tuple', 'builtin', 'tuple(iterable)', '不可變的序列；可以當 dict 的 key 或放進 set。', 'seen.add(tuple(path))\nkey = tuple(sorted(word))');
  add('frozenset', 'builtin', 'frozenset(iterable)', '不可變的集合，可以當 dict 的 key。', 'memo[frozenset(used)] = ans');
  add('ord', 'builtin', 'ord(c)', '字元 → Unicode 編碼（整數）。', 'ord("a")               # 97\nord(c) - ord("a")      # 0~25，常用來當陣列索引');
  add('chr', 'builtin', 'chr(i)', 'Unicode 編碼 → 字元。', 'chr(97)                # "a"\nchr(ord("a") + 2)      # "c"');
  add('bin', 'builtin', 'bin(x)', '轉成二進位字串（前面有 "0b"）。', 'bin(5)            # "0b101"\nbin(5).count("1") # 2，1 的個數');
  add('hex', 'builtin', 'hex(x)', '轉成十六進位字串（前面有 "0x"）。', 'hex(255)   # "0xff"');
  add('any', 'builtin', 'any(iterable)', '只要有一個為 True 就回傳 True（空序列為 False）。', 'any(x < 0 for x in nums)');
  add('all', 'builtin', 'all(iterable)', '全部為 True 才回傳 True（空序列為 True）。', 'all(c.isdigit() for c in s)');
  add('map', 'builtin', 'map(func, iterable)', '對每個元素套用函式，回傳迭代器。', 'list(map(int, "123"))   # [1, 2, 3]\nlist(map(str, nums))');
  add('filter', 'builtin', 'filter(func, iterable)', '留下 func 回傳 True 的元素，回傳迭代器。', 'list(filter(str.isalnum, "a,b!"))  # ["a", "b"]');
  add('isinstance', 'builtin', 'isinstance(obj, type)', '判斷物件型別。', 'isinstance(x, int)\nisinstance(x, (list, tuple))');
  add('print', 'builtin', 'print(*values, sep=" ", end="\\n")', '輸出到標準輸出（執行結果的 stdout 會顯示）。除錯用。', 'print(i, dp)\nprint(*nums)   # 用空白分隔印出');
  add('iter', 'builtin', 'iter(iterable)', '取得迭代器，搭配 next 逐一取值。', 'it = iter(nums)\nnext(it)   # 第一個元素');
  add('next', 'builtin', 'next(iterator[, default])', '取迭代器的下一個值；沒有了回傳 default（沒給會出錯）。', 'first = next((i for i, x in enumerate(nums) if x > 0), -1)');
  add('hash', 'builtin', 'hash(obj)', '回傳不可變物件的雜湊值。', 'hash((1, 2))');
  add('id', 'builtin', 'id(obj)', '物件的唯一識別碼（記憶體位址）。判斷兩個節點是不是「同一個物件」可用 is。', 'a is b   # 比較是否為同一個物件');
  add('super', 'builtin', 'super()', '呼叫父類別的方法。', 'class A(B):\n    def __init__(self):\n        super().__init__()');
  add('lambda', 'keyword', 'lambda 參數: 運算式', '匿名函式，常用在 sorted / max 的 key。', 'sorted(intervals, key=lambda x: x[0])\nf = lambda a, b: a + b');
  add('yield', 'keyword', 'yield 值', '讓函式變成產生器，逐一產生值（不一次建立整個 list）。', 'def gen(n):\n    for i in range(n):\n        yield i * i\nlist(gen(3))   # [0, 1, 4]');
  add('nonlocal', 'keyword', 'nonlocal 變數', '在內層函式中修改外層函式的變數（例如 DFS 裡更新答案）。',
    'def solve():\n    best = 0\n    def dfs(node):\n        nonlocal best\n        best = max(best, node.val)');
  add('global', 'keyword', 'global 變數', '在函式內修改模組層級的全域變數。', 'count = 0\ndef inc():\n    global count\n    count += 1');
  add('None', 'keyword', 'None', '代表「沒有值」。判斷時用 is None。', 'if node is None:\n    return 0');
  add('self', 'keyword', 'self', '方法的第一個參數，代表物件本身；用 self.x 存取屬性。', 'class Counter:\n    def __init__(self):\n        self.n = 0\n    def add(self):\n        self.n += 1');
  add('Solution', 'keyword', 'class Solution', 'LeetCode 的解答類別，判題時會建立 Solution() 並呼叫題目指定的方法。', 'class Solution:\n    def twoSum(self, nums, target): ...');
  add('ListNode', 'keyword', 'class ListNode: val, next', 'LeetCode 單向鏈結串列節點（系統已提供，不用自己定義）。',
    'dummy = ListNode(0)\ncur = dummy\ncur.next = ListNode(5)\nreturn dummy.next');
  add('TreeNode', 'keyword', 'class TreeNode: val, left, right', 'LeetCode 二元樹節點（系統已提供，不用自己定義）。',
    'def depth(node):\n    if not node:\n        return 0\n    return 1 + max(depth(node.left), depth(node.right))');
  add('Optional', 'typing', 'Optional[T]', '型別註記：可能是 T 或 None（只是提示，不影響執行）。', 'def f(root: Optional[TreeNode]) -> int: ...');
  add('List', 'typing', 'List[T]', '型別註記：元素型別為 T 的 list（等同 list[T]，只是提示）。', 'def f(nums: List[int]) -> List[int]: ...');

  // ---------------------------------------------------------------- list 方法
  add('append', 'list', 'lst.append(x)', '在尾端加入一個元素。O(1)。', 'stack.append(5)\nres.append(path[:])   # 加入複本，避免之後被修改');
  add('pop', 'list', 'lst.pop(i=-1)', '移除並回傳索引 i 的元素（預設最後一個）。pop() 是 O(1)，pop(0) 是 O(n)，佇列請用 deque。',
    'top = stack.pop()\nfirst = lst.pop(0)   # O(n)');
  add('extend', 'list', 'lst.extend(iterable)', '把另一個序列的元素全部加到尾端。', 'a = [1]\na.extend([2, 3])   # [1, 2, 3]');
  add('insert', 'list', 'lst.insert(i, x)', '在索引 i 插入元素。O(n)。', 'lst.insert(0, x)   # 插到最前面');
  add('remove', 'list', 'lst.remove(x)', '刪除第一個等於 x 的元素，不存在會出錯。O(n)。', 'lst.remove(3)');
  add('index', 'list', 'lst.index(x[, start[, end]])', '回傳第一個等於 x 的索引，不存在會出錯。O(n)。', '[5, 7, 5].index(5)   # 0');
  add('count', 'list', 'lst.count(x)', '計算 x 出現幾次。O(n)。', '[1, 2, 1].count(1)   # 2');
  add('sort', 'list', 'lst.sort(key=None, reverse=False)', '原地排序（回傳 None）。O(n log n)。',
    'nums.sort()\nnums.sort(reverse=True)\nintervals.sort(key=lambda x: x[1])');
  add('reverse', 'list', 'lst.reverse()', '原地反轉（回傳 None）。也可用切片 lst[::-1] 產生反轉後的新 list。', 'nums.reverse()\nrev = nums[::-1]');
  add('copy', 'list', 'lst.copy()', '淺複製，等同 lst[:]。', 'b = a.copy()');
  add('clear', 'list', 'x.clear()', '清空容器（list / dict / set / deque 都有）。', 'seen.clear()');

  // ---------------------------------------------------------------- str 方法
  add('split', 'str', 's.split(sep=None)', '切割字串。不給 sep 時以任意空白切割並忽略多餘空白。', '"a  b c".split()     # ["a", "b", "c"]\n"1,2,3".split(",")   # ["1", "2", "3"]');
  add('join', 'str', 'sep.join(iterable)', '用 sep 把字串序列接起來（元素必須是字串）。比在迴圈裡用 + 快。', '"".join(["a", "b"])        # "ab"\n" ".join(reversed(words))\n",".join(map(str, nums))');
  add('strip', 'str', 's.strip(chars=None)', '去掉頭尾的空白（或指定字元）。另有 lstrip / rstrip。', '"  hi  ".strip()   # "hi"\n"00120".lstrip("0")  # "120"');
  add('lstrip', 'str', 's.lstrip(chars=None)', '去掉開頭的空白（或指定字元）。', '"007".lstrip("0")   # "7"');
  add('rstrip', 'str', 's.rstrip(chars=None)', '去掉結尾的空白（或指定字元）。', '"ab  ".rstrip()   # "ab"');
  add('replace', 'str', 's.replace(old, new[, count])', '取代子字串，回傳新字串。', '"a-b-c".replace("-", "")   # "abc"');
  add('find', 'str', 's.find(sub[, start])', '回傳子字串第一次出現的索引，找不到回傳 -1。', '"hello".find("ll")   # 2\n"hello".find("z")    # -1');
  add('startswith', 'str', 's.startswith(prefix)', '是否以 prefix 開頭。', '"apple".startswith("ap")   # True');
  add('endswith', 'str', 's.endswith(suffix)', '是否以 suffix 結尾。', '"test.py".endswith(".py")   # True');
  add('isdigit', 'str', 's.isdigit()', '是否全部是數字字元。', '"123".isdigit()   # True');
  add('isalpha', 'str', 's.isalpha()', '是否全部是字母。', '"abc".isalpha()   # True');
  add('isalnum', 'str', 's.isalnum()', '是否全部是字母或數字。', '"a1".isalnum()    # True\n[c for c in s if c.isalnum()]');
  add('lower', 'str', 's.lower()', '轉小寫。', '"AbC".lower()   # "abc"');
  add('upper', 'str', 's.upper()', '轉大寫。', '"abc".upper()   # "ABC"');
  add('isupper', 'str', 's.isupper()', '是否全部是大寫字母。', '"A".isupper()   # True');
  add('islower', 'str', 's.islower()', '是否全部是小寫字母。', '"a".islower()   # True');
  add('zfill', 'str', 's.zfill(width)', '左邊補 0 到指定長度。', '"101".zfill(8)   # "00000101"');
  add('format', 'str', 'format(x, spec) / "{}".format(...)', '格式化。常用 f-string：f"{x:.2f}"。', 'format(5, "b")    # "101"\nf"{3.14159:.2f}"   # "3.14"');
  add('ascii_lowercase', 'string', 'string.ascii_lowercase', '字串 "abcdefghijklmnopqrstuvwxyz"。', 'for c in string.ascii_lowercase: ...');

  // ---------------------------------------------------------------- dict 方法
  add('get', 'dict', 'd.get(key, default=None)', '取值；key 不存在時回傳 default，不會出錯。', 'cnt[x] = cnt.get(x, 0) + 1\nidx = pos.get(target - x)');
  add('items', 'dict', 'd.items()', '同時走訪 key 與 value。', 'for k, v in d.items():\n    ...');
  add('keys', 'dict', 'd.keys()', '所有 key。', 'for k in d.keys(): ...   # 等同 for k in d');
  add('values', 'dict', 'd.values()', '所有 value。', 'list(groups.values())\nmax(cnt.values())');
  add('setdefault', 'dict', 'd.setdefault(key, default)', 'key 不存在時先設成 default，再回傳 d[key]。', 'groups.setdefault(key, []).append(word)');
  add('pop', 'dict', 'd.pop(key[, default])', '刪除 key 並回傳它的值；不存在時回傳 default（沒給會出錯）。', 'd.pop("a", None)');
  add('update', 'dict', 'd.update(other)', '把另一個 dict 的內容合併進來（set 也有 update：加入多個元素）。', 'd.update({"a": 1})\ns.update([1, 2])');

  // ---------------------------------------------------------------- set 方法
  add('add', 'set', 's.add(x)', '加入元素。平均 O(1)。', 'seen.add(node)');
  add('discard', 'set', 's.discard(x)', '刪除元素；不存在也不會出錯（remove 會出錯）。', 'window.discard(c)');
  add('remove', 'set', 's.remove(x)', '刪除元素；不存在會出錯。', 's.remove(3)');
  add('union', 'set', 'a.union(b) / a | b', '聯集。', '{1, 2} | {2, 3}   # {1, 2, 3}');
  add('intersection', 'set', 'a.intersection(b) / a & b', '交集。', '{1, 2} & {2, 3}   # {2}');
  add('difference', 'set', 'a.difference(b) / a - b', '差集。', '{1, 2} - {2, 3}   # {1}');
  add('issubset', 'set', 'a.issubset(b) / a <= b', '是否為子集合。', '{1} <= {1, 2}   # True');

  // ---------------------------------------------------------------- collections
  add('defaultdict', 'collections', 'defaultdict(default_factory)', '有預設值的 dict：存取不存在的 key 時，自動用 default_factory() 建立初始值。',
    'cnt = defaultdict(int)     # 預設 0\ncnt["a"] += 1\ng = defaultdict(list)      # 預設 []\ng[u].append(v)             # 建圖');
  add('Counter', 'collections', 'Counter(iterable)', '計數器（dict 的子類別）：統計每個元素出現幾次，不存在的 key 回傳 0。',
    'c = Counter("aab")        # {"a": 2, "b": 1}\nc["z"]                    # 0\nc.most_common(1)          # [("a", 2)]\nCounter(s) == Counter(t)  # 是否為重組字');
  add('most_common', 'Counter', 'c.most_common(n=None)', '依出現次數由多到少回傳 (元素, 次數)；給 n 只取前 n 個。', 'Counter(nums).most_common(2)   # 出現最多的兩個');
  add('deque', 'collections', 'deque(iterable=(), maxlen=None)', '雙端佇列：兩端加入／取出都是 O(1)。BFS 佇列、單調佇列常用。',
    'q = deque([start])\nwhile q:\n    node = q.popleft()\n    q.append(nxt)');
  add('popleft', 'deque', 'q.popleft()', '從左端取出並回傳元素。O(1)。', 'x = q.popleft()');
  add('appendleft', 'deque', 'q.appendleft(x)', '在左端加入元素。O(1)。', 'q.appendleft(0)');
  add('rotate', 'deque', 'q.rotate(n=1)', '向右旋轉 n 步（負數向左）。', 'q = deque([1, 2, 3]); q.rotate(1)   # [3, 1, 2]');
  add('OrderedDict', 'collections', 'OrderedDict()', '記住插入順序的 dict；move_to_end 與 popitem(last=False) 可做 LRU 快取。',
    'od = OrderedDict()\nod.move_to_end(key)        # 移到最後（最近使用）\nod.popitem(last=False)     # 移除最舊的');
  add('move_to_end', 'OrderedDict', 'od.move_to_end(key, last=True)', '把 key 移到尾端（last=False 移到開頭）。', 'cache.move_to_end(key)');
  add('popitem', 'dict', 'd.popitem()', '移除並回傳最後插入的 (key, value)。OrderedDict 可用 last=False 移除最舊的。', 'k, v = od.popitem(last=False)');
  add('namedtuple', 'collections', 'namedtuple(name, fields)', '建立有欄位名稱的 tuple。', 'P = namedtuple("P", "x y")\np = P(1, 2); p.x   # 1');

  // ---------------------------------------------------------------- heapq（最小堆積）
  add('heapq', 'heapq', 'import heapq', '最小堆積（優先佇列）模組，直接操作一般 list。heap[0] 是最小值。要最大堆積就存負數。',
    'h = []\nheapq.heappush(h, 3)\nsmallest = heapq.heappop(h)\nheapq.heappush(h, -x)   # 最大堆積技巧');
  add('heappush', 'heapq', 'heapq.heappush(heap, item)', '加入元素並維持堆積。O(log n)。可以放 tuple，依第一個欄位比較。',
    'heappush(h, (dist, node))');
  add('heappop', 'heapq', 'heapq.heappop(heap)', '取出並回傳最小元素。O(log n)。', 'd, u = heappop(h)');
  add('heapify', 'heapq', 'heapq.heapify(lst)', '把 list 原地轉成堆積。O(n)。', 'h = nums[:]\nheapify(h)');
  add('heappushpop', 'heapq', 'heapq.heappushpop(heap, item)', '先加入 item 再取出最小值，比分開做快。', 'heappushpop(h, x)   # 維持大小為 k 的堆積');
  add('heapreplace', 'heapq', 'heapq.heapreplace(heap, item)', '先取出最小值再加入 item。', 'heapreplace(h, x)');
  add('nlargest', 'heapq', 'heapq.nlargest(k, iterable, key=None)', '回傳最大的 k 個（由大到小）。', 'nlargest(2, [5, 1, 8, 3])   # [8, 5]');
  add('nsmallest', 'heapq', 'heapq.nsmallest(k, iterable, key=None)', '回傳最小的 k 個（由小到大）。', 'nsmallest(2, points, key=lambda p: p[0]**2 + p[1]**2)');

  // ---------------------------------------------------------------- bisect（二分搜尋，list 必須已排序）
  add('bisect_left', 'bisect', 'bisect.bisect_left(a, x, lo=0, hi=len(a), key=None)', '回傳 x 應插入的位置（放在相等元素的左邊）＝第一個 ≥ x 的索引。O(log n)。',
    'a = [1, 2, 2, 4]\nbisect_left(a, 2)   # 1\nbisect_left(a, 3)   # 3');
  add('bisect_right', 'bisect', 'bisect.bisect_right(a, x, lo=0, hi=len(a), key=None)', '回傳 x 應插入的位置（放在相等元素的右邊）＝第一個 > x 的索引。O(log n)。',
    'a = [1, 2, 2, 4]\nbisect_right(a, 2)  # 3\nbisect_right(a, 2) - bisect_left(a, 2)   # 2 的個數');
  add('bisect', 'bisect', 'bisect.bisect(a, x)', '同 bisect_right。', 'bisect([1, 3], 3)   # 2');
  add('insort', 'bisect', 'bisect.insort(a, x)', '把 x 插入已排序的 list 並維持排序。搜尋 O(log n)，插入 O(n)。', 'insort(window, x)');

  // ---------------------------------------------------------------- math
  add('math', 'math', 'import math', '數學函式模組。', 'math.gcd(12, 18)   # 6\nmath.inf');
  add('gcd', 'math', 'math.gcd(*integers)', '最大公因數。', 'gcd(12, 18)   # 6');
  add('lcm', 'math', 'math.lcm(*integers)', '最小公倍數。', 'lcm(4, 6)   # 12');
  add('sqrt', 'math', 'math.sqrt(x)', '平方根（浮點數）。整數平方根請用 isqrt，避免誤差。', 'sqrt(2)   # 1.414...');
  add('isqrt', 'math', 'math.isqrt(n)', '整數平方根：⌊√n⌋，沒有浮點誤差。', 'isqrt(10)   # 3\nisqrt(n) ** 2 == n   # 是否為完全平方數');
  add('ceil', 'math', 'math.ceil(x)', '無條件進位。整數除法的進位可以寫 (a + b - 1) // b 或 -(-a // b)。', 'ceil(7 / 2)   # 4\n-(-7 // 2)    # 4');
  add('floor', 'math', 'math.floor(x)', '無條件捨去（往負無窮）。', 'floor(-2.5)   # -3');
  add('log2', 'math', 'math.log2(x)', '以 2 為底的對數。', 'log2(8)   # 3.0');
  add('log', 'math', 'math.log(x[, base])', '對數（預設自然對數）。', 'log(100, 10)   # 2.0');
  add('comb', 'math', 'math.comb(n, k)', '組合數 C(n, k)。', 'comb(5, 2)   # 10');
  add('perm', 'math', 'math.perm(n, k=None)', '排列數 P(n, k)。', 'perm(5, 2)   # 20');
  add('factorial', 'math', 'math.factorial(n)', '階乘 n!。', 'factorial(5)   # 120');
  add('inf', 'math', 'math.inf', '正無窮大（浮點數），等同 float("inf")。', 'best = math.inf');
  add('hypot', 'math', 'math.hypot(x, y)', '√(x² + y²)，點到原點的距離。', 'hypot(3, 4)   # 5.0');

  // ---------------------------------------------------------------- itertools
  add('permutations', 'itertools', 'itertools.permutations(iterable, r=None)', '所有排列（依位置，元素重複也會重複產生）。', 'list(permutations([1, 2, 3], 2))   # (1,2) (1,3) (2,1) ...');
  add('combinations', 'itertools', 'itertools.combinations(iterable, r)', '所有取 r 個的組合（不考慮順序）。', 'list(combinations("abc", 2))   # ("a","b") ("a","c") ("b","c")');
  add('product', 'itertools', 'itertools.product(*iterables, repeat=1)', '笛卡兒積，等同巢狀 for 迴圈。', 'for dx, dy in product((-1, 0, 1), repeat=2): ...');
  add('accumulate', 'itertools', 'itertools.accumulate(iterable, func=add, initial=None)', '前綴累積（預設是前綴和）。', 'list(accumulate([1, 2, 3]))              # [1, 3, 6]\nlist(accumulate([1, 2, 3], initial=0))   # [0, 1, 3, 6]\nlist(accumulate(nums, max))              # 前綴最大值');
  add('groupby', 'itertools', 'itertools.groupby(iterable, key=None)', '把「相鄰且相同」的元素分成一組。', '[(k, len(list(g))) for k, g in groupby("aabccc")]\n# [("a", 2), ("b", 1), ("c", 3)]');
  add('pairwise', 'itertools', 'itertools.pairwise(iterable)', '相鄰兩兩一組。', 'list(pairwise([1, 2, 3]))   # [(1, 2), (2, 3)]');
  add('chain', 'itertools', 'itertools.chain(*iterables)', '把多個序列串起來走訪。', 'list(chain([1], [2, 3]))   # [1, 2, 3]');
  add('count', 'itertools', 'itertools.count(start=0, step=1)', '無限遞增的計數器。', 'for i in count(1): ...');
  add('zip_longest', 'itertools', 'itertools.zip_longest(*iterables, fillvalue=None)', '像 zip，但以最長的為準，不足的補 fillvalue。', 'list(zip_longest("ab", "x", fillvalue=""))   # [("a","x"), ("b","")]');

  // ---------------------------------------------------------------- functools
  add('lru_cache', 'functools', '@lru_cache(maxsize=None)', '記憶化：相同參數只計算一次（參數必須可雜湊）。遞迴 DP 常用。',
    '@lru_cache(maxsize=None)\ndef dp(i, j):\n    ...\n# 多筆測資之間可呼叫 dp.cache_clear()');
  add('cache', 'functools', '@cache', '等同 @lru_cache(maxsize=None)。', '@cache\ndef fib(n):\n    return n if n < 2 else fib(n - 1) + fib(n - 2)');
  add('reduce', 'functools', 'functools.reduce(func, iterable[, initial])', '把序列兩兩累積成一個值。', 'reduce(lambda a, b: a ^ b, nums)   # 全部 XOR\nreduce(gcd, nums)');
  add('cmp_to_key', 'functools', 'functools.cmp_to_key(cmp)', '把「比較函式」轉成 sort 的 key。cmp(a, b) 回傳負數表示 a 排前面。',
    'nums.sort(key=cmp_to_key(lambda a, b: -1 if a + b > b + a else 1))   # 最大數');

  // ---------------------------------------------------------------- random
  add('randint', 'random', 'random.randint(a, b)', '回傳 [a, b] 之間的隨機整數（包含兩端）。', 'randint(1, 6)');
  add('choice', 'random', 'random.choice(seq)', '從序列中隨機選一個。', 'choice(nums)');
  add('shuffle', 'random', 'random.shuffle(lst)', '原地隨機打亂 list。', 'random.shuffle(arr)');
  add('random', 'random', 'random.random()', '回傳 [0, 1) 的隨機浮點數。', 'if random.random() < 0.5: ...');

  const TYPE_OWNERS = ['list', 'str', 'dict', 'set', 'deque', 'Counter', 'OrderedDict'];
  const MODULES = ['collections', 'heapq', 'bisect', 'math', 'itertools', 'functools', 'string', 'random', 'typing'];

  // prefix：名稱前面「.」之前的識別字（例如 heapq.heappush 的 heapq）；沒有就是 null
  function lookup(name, prefix) {
    const all = E[name] || [];
    if (!all.length) return [];
    if (prefix && MODULES.includes(prefix)) {
      const m = all.filter((e) => e.owner === prefix);
      return m.length ? m : all;
    }
    if (prefix) {  // 物件的方法：只顯示型別方法
      const m = all.filter((e) => TYPE_OWNERS.includes(e.owner));
      return m.length ? m : all;
    }
    const top = all.filter((e) => !TYPE_OWNERS.includes(e.owner));
    return top.length ? top : all;
  }
  return { lookup, entries: E };
})();
