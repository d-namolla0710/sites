#!/usr/bin/env python3
"""sites.json 관리 + GitHub 자동 배포 CLI 툴

URL 규칙:
  abc          → https://abc.minchan.app/
  abc.com      → https://abc.com/
  https://...  → 그대로 (trailing slash만 정리)
"""
import json
import argparse
import subprocess
from datetime import date
from pathlib import Path

SITES_JSON = Path(__file__).parent / "sites.json"
DEFAULT_DOMAIN = "minchan.app"


# ── URL 정규화 ────────────────────────────────────────────────────────────────

def normalize_url(raw: str) -> str:
    s = raw.strip().rstrip("/")
    if "://" in s:                          # 프로토콜 있으면 그대로
        return s + "/"
    if "." not in s:                        # 점 없으면 .minchan.app 붙임
        return f"https://{s}.{DEFAULT_DOMAIN}/"
    return f"https://{s}/"                  # 점 있으면 https만 붙임


# ── JSON 로드/저장 ─────────────────────────────────────────────────────────────

def load() -> dict:
    if SITES_JSON.exists():
        return json.loads(SITES_JSON.read_text(encoding="utf-8"))
    return {"sites": []}


def save(data: dict):
    SITES_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# ── GitHub 자동 배포 ──────────────────────────────────────────────────────────

def git_push(message: str):
    repo = SITES_JSON.parent
    try:
        subprocess.run(["git", "add", "sites.json"], cwd=repo, check=True)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo, capture_output=True, text=True,
        )
        if "nothing to commit" in result.stdout + result.stderr:
            print("(변경사항 없음, push 생략)")
            return
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, "git commit", result.stderr)
        subprocess.run(["git", "push"], cwd=repo, check=True)
        print("GitHub 배포 완료.")
    except subprocess.CalledProcessError as e:
        print(f"Git 오류: {e}")


# ── 커맨드 ────────────────────────────────────────────────────────────────────

def cmd_add(args):
    url = normalize_url(args.url)
    data = load()
    for s in data["sites"]:
        if s["url"] == url:
            print(f"이미 있어요: {s['name']} ({url})")
            return
    data["sites"].append({
        "name": args.name,
        "url": url,
        "description": args.description,
        "tags": args.tags or [],
        "added": str(date.today()),
    })
    save(data)
    print(f"추가됨: {args.name} → {url}")
    git_push(f"add: {args.name}")


def cmd_edit(args):
    url = normalize_url(args.url)
    data = load()
    for s in data["sites"]:
        if s["url"] == url:
            if args.name:        s["name"]        = args.name
            if args.description: s["description"] = args.description
            if args.tags is not None: s["tags"]   = args.tags
            save(data)
            print(f"수정됨: {s['name']} ({url})")
            git_push(f"edit: {s['name']}")
            return
    print(f"없는 URL이에요: {url}")


def cmd_remove(args):
    url = normalize_url(args.url)
    data = load()
    targets = [s for s in data["sites"] if s["url"] == url]
    if not targets:
        print(f"없는 URL이에요: {url}")
        return
    data["sites"] = [s for s in data["sites"] if s["url"] != url]
    save(data)
    print(f"삭제됨: {targets[0]['name']} ({url})")
    git_push(f"remove: {targets[0]['name']}")


def cmd_list(args):
    sites = load().get("sites", [])
    if not sites:
        print("아직 사이트가 없어요.")
        return
    for i, s in enumerate(sites, 1):
        tags = f"  [{', '.join(s['tags'])}]" if s.get("tags") else ""
        print(f"{i}. {s['name']}{tags}")
        print(f"   {s['url']}")
        if s.get("description"):
            print(f"   {s['description']}")


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="sites.json 관리 툴",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""예시:
  python add_site.py add "My Game" game "브라우저 게임" --tags game web
  python add_site.py add "Portfolio" portfolio.myname.dev "포트폴리오"
  python add_site.py edit game --name "My New Game" --tags game
  python add_site.py remove game
  python add_site.py list""",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="사이트 추가")
    p.add_argument("name",        help="사이트 이름")
    p.add_argument("url",         help="URL (abc → https://abc.minchan.app/, abc.com → https://abc.com/)")
    p.add_argument("description", help="짧은 설명")
    p.add_argument("--tags", nargs="*", default=[], metavar="TAG")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("edit", help="사이트 수정")
    p.add_argument("url",          help="수정할 사이트 URL")
    p.add_argument("--name",        help="새 이름")
    p.add_argument("--description", help="새 설명")
    p.add_argument("--tags", nargs="*", metavar="TAG", default=None)
    p.set_defaults(func=cmd_edit)

    p = sub.add_parser("remove", help="사이트 삭제")
    p.add_argument("url", help="삭제할 사이트 URL")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("list", help="전체 목록 보기")
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
