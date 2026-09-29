"""多人模式的管理工具（在伺服器上執行）。

    python manage.py create-admin <帳號> [密碼]          建立管理員（沒給密碼會詢問）
    python manage.py create-user <帳號> [密碼]           建立一般使用者
    python manage.py set-password <帳號> [密碼]         重設密碼
    python manage.py import-files <solutions 資料夾> <帳號>
        把單人版的練習資料（程式碼、引導前備份、完成紀錄、題組、題庫選擇）匯入到某個帳號
    python manage.py list-users

資料庫位置：環境變數 PYCODE_DATA（預設 ./data）。
"""
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auth  # noqa: E402
import store  # noqa: E402


def _password(argv, i):
    if len(argv) > i:
        return argv[i]
    if os.environ.get("PYCODE_PASSWORD"):  # 自動化部署／測試用：從環境變數讀密碼
        return os.environ["PYCODE_PASSWORD"]
    pw = getpass.getpass("密碼（至少 6 個字元）：")
    if pw != getpass.getpass("再輸入一次：") :
        sys.exit("兩次輸入的密碼不同")
    return pw


def _uid(username):
    with store.db() as c:
        r = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if not r:
        sys.exit(f"找不到帳號「{username}」")
    return r["id"]


def import_files(directory, username):
    """單人版 solutions/ → 某個帳號。已存在的程式碼會被覆蓋，完成紀錄會合併。"""
    src = store.FileStore(directory)
    dst = store.DbStore(_uid(username))
    n_code = n_solved = n_backup = 0
    for f in Path(directory).glob("*.py"):
        if f.name.endswith(".backup.py"):
            dst.set_backup(f.name[:-len(".backup.py")], f.read_text(encoding="utf-8"))
            n_backup += 1
        else:
            dst.set_code(f.stem, f.read_text(encoding="utf-8"))
            n_code += 1
    for f in Path(directory).glob("*.solved"):
        dst.set_solved(f.stem, src.get_solved(f.stem))
        n_solved += 1
    if src.get_set():
        dst.set_set(src.get_set())
    if src.get_bank():
        dst.set_bank(src.get_bank())
    print(f"已匯入到「{username}」：程式碼 {n_code} 題、引導前備份 {n_backup} 題、完成紀錄 {n_solved} 題")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = argv[1]
    try:
        if cmd in ("create-admin", "create-user"):
            uid = auth.create_user(argv[2], _password(argv, 3), is_admin=cmd == "create-admin")
            print(f"已建立{'管理員' if cmd == 'create-admin' else '使用者'}「{argv[2]}」（id {uid}）")
        elif cmd == "set-password":
            auth.update_user(_uid(argv[2]), password=_password(argv, 3))
            print("已重設密碼")
        elif cmd == "import-files":
            import_files(argv[2], argv[3])
        elif cmd == "list-users":
            for u in auth.list_users():
                print(f"{u['id']:3d}  {u['username']:<20} {'管理員' if u['is_admin'] else '使用者'}  "
                      f"{'啟用' if u['active'] else '停用'}  最後上線 {u['last_seen'] or '-'}")
        else:
            sys.exit(f"不認識的指令：{cmd}\n{__doc__}")
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main(sys.argv)
