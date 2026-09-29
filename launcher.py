"""PyCode 練習的啟動程式（run.sh / run.bat 會呼叫這支）。

- 使用 vendor/ 裡附帶的 Flask、PyYAML，不需要 pip install、不需要網路
- 預設只在本機開放（127.0.0.1），自動找可用的連接埠並開啟瀏覽器

用法：
    python launcher.py [--port 5000] [--host 127.0.0.1] [--no-browser]
"""
import argparse
import os
import socket
import sys
import threading
import webbrowser

MIN_PY = (3, 10)
ROOT = os.path.dirname(os.path.abspath(__file__))


def free_port(host, start):
    """從 start 開始找第一個沒被佔用的連接埠。"""
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    sys.exit(f"找不到可用的連接埠（{start}～{start + 19} 都被佔用）")


def main():
    if sys.version_info < MIN_PY:
        sys.exit(f"需要 Python {MIN_PY[0]}.{MIN_PY[1]} 以上，目前是 {sys.version.split()[0]}")

    parser = argparse.ArgumentParser(description="PyCode 練習")
    parser.add_argument("--host", default="127.0.0.1",
                        help="預設 127.0.0.1（只有本機能連）。設成 0.0.0.0 會開放給區網，任何人都能在你的電腦上執行程式碼，請小心。")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--no-browser", action="store_true", help="不要自動開啟瀏覽器")
    args = parser.parse_args()

    os.chdir(ROOT)
    sys.path.insert(0, os.path.join(ROOT, "vendor"))  # 附帶的第三方套件優先
    sys.path.insert(0, ROOT)
    import app  # noqa: E402  (要在設定好 sys.path 之後才能匯入)

    port = free_port(args.host, args.port)
    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{port}"
    print("=" * 56)
    print(f"  PyCode 練習已啟動：{url}")
    if args.host not in ("127.0.0.1", "localhost"):
        print(f"  ⚠ 已開放給 {args.host}：區網內的人都能連線並執行程式碼")
    print("  關閉：在這個視窗按 Ctrl+C")
    print("=" * 56)
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.app.run(host=args.host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
