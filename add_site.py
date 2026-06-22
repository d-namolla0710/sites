#!/usr/bin/env python3
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from pathlib import Path

SITES_JSON = Path(__file__).parent / "sites.json"
DEFAULT_DOMAIN = "minchan.app"


def normalize_url(raw: str) -> str:
    s = raw.strip().rstrip("/")
    if not s:
        return ""
    if "://" in s:
        return s + "/"
    if "." not in s:
        return f"https://{s}.{DEFAULT_DOMAIN}/"
    return f"https://{s}/"


def load() -> dict:
    if SITES_JSON.exists():
        return json.loads(SITES_JSON.read_text(encoding="utf-8"))
    return {"sites": []}


def save(data: dict):
    SITES_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def git_push(message: str) -> str:
    repo = SITES_JSON.parent
    try:
        subprocess.run(["git", "add", "sites.json"], cwd=repo, check=True,
                       capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo, capture_output=True, text=True,
        )
        out = result.stdout + result.stderr
        if "nothing to commit" in out:
            return "변경사항 없음"
        if result.returncode != 0:
            return f"커밋 실패: {result.stderr.strip()}"
        subprocess.run(["git", "push"], cwd=repo, check=True, capture_output=True)
        return "✓ GitHub 배포 완료"
    except FileNotFoundError:
        return "git을 찾을 수 없어요 (PATH 확인 필요)"
    except subprocess.CalledProcessError as e:
        return f"Git 오류: {e}"


# ── 색상 팔레트 ──────────────────────────────────────────────────────────────

BG       = "#f5f5f7"
SURFACE  = "#ffffff"
ACCENT   = "#4f46e5"
DANGER   = "#ef4444"
WARNING  = "#f59e0b"
TEXT     = "#1d1d1f"
MUTED    = "#6e6e73"
BORDER   = "#e5e5ea"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sites Manager")
        self.geometry("860x580")
        self.minsize(700, 480)
        self.configure(bg=BG)

        self._selected_idx: int | None = None

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
                        background=SURFACE, foreground=TEXT,
                        rowheight=26, fieldbackground=SURFACE,
                        bordercolor=BORDER, relief="flat")
        style.configure("Treeview.Heading",
                        background=BG, foreground=MUTED,
                        font=("", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#e0e7ff")],
                  foreground=[("selected", ACCENT)])

        self._build()
        self._refresh()

    # ── UI 구성 ──────────────────────────────────────────────────────────────

    def _build(self):
        # 헤더
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill=tk.X, padx=20, pady=(18, 4))
        tk.Label(hdr, text="Sites Manager", bg=BG, fg=TEXT,
                 font=("", 16, "bold")).pack(side=tk.LEFT)
        self._status = tk.StringVar()
        tk.Label(hdr, textvariable=self._status, bg=BG, fg=MUTED,
                 font=("", 10)).pack(side=tk.RIGHT, padx=4)

        # 구분선
        tk.Frame(self, bg=BORDER, height=1).pack(fill=tk.X)

        # 목록
        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)

        cols = ("name", "url", "tags", "added")
        headers = {"name": ("이름", 170), "url": ("URL", 300),
                   "tags": ("태그", 150), "added": ("추가일", 90)}

        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                 selectmode="browse")
        for c, (label, w) in headers.items():
            self.tree.heading(c, text=label)
            self.tree.column(c, width=w, minwidth=60)

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # 구분선
        tk.Frame(self, bg=BORDER, height=1).pack(fill=tk.X)

        # 폼
        form = tk.Frame(self, bg=SURFACE, pady=14)
        form.pack(fill=tk.X)

        self._entries: dict[str, tk.Entry] = {}
        fields = [("이름 *", "name"), ("URL *", "url"),
                  ("설명", "description"), ("태그 (공백 구분)", "tags")]

        for i, (label, key) in enumerate(fields):
            row = i // 2
            col_base = (i % 2) * 3

            tk.Label(form, text=label, bg=SURFACE, fg=MUTED,
                     font=("", 9), anchor="w"
                     ).grid(row=row * 2, column=col_base, columnspan=2,
                            padx=(20 if col_base == 0 else 12, 4),
                            pady=(6, 1), sticky="w")

            e = tk.Entry(form, font=("", 10), relief="flat",
                         bg=BG, fg=TEXT, insertbackground=TEXT)
            e.grid(row=row * 2 + 1, column=col_base, columnspan=2,
                   padx=(20 if col_base == 0 else 12, 4),
                   pady=(0, 4), ipady=5, sticky="ew")
            self._entries[key] = e

        form.columnconfigure(1, weight=1)
        form.columnconfigure(4, weight=1)

        # URL 미리보기
        self._url_preview = tk.StringVar()
        tk.Label(form, textvariable=self._url_preview, bg=SURFACE,
                 fg=ACCENT, font=("", 8)).grid(
            row=3, column=3, columnspan=2, padx=(12, 20),
            pady=(0, 4), sticky="w")
        self._entries["url"].bind("<KeyRelease>", self._update_url_preview)

        # 버튼
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill=tk.X, padx=20, pady=12)

        self._btn("새로고침", self._refresh, btn_row, bg=BG, fg=MUTED,
                  side=tk.LEFT)
        self._btn("삭제", self._remove, btn_row, bg=DANGER)
        self._btn("수정", self._edit, btn_row, bg=WARNING)
        self._btn("추가", self._add, btn_row, bg=ACCENT)

    def _btn(self, text, cmd, parent, bg=ACCENT, fg="white", side=tk.RIGHT):
        tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  font=("", 10, "bold"), relief="flat",
                  padx=18, pady=6, cursor="hand2",
                  activebackground=bg, activeforeground=fg
                  ).pack(side=side, padx=(0, 6) if side == tk.RIGHT else (0, 8))

    # ── 이벤트 ───────────────────────────────────────────────────────────────

    def _update_url_preview(self, _=None):
        raw = self._entries["url"].get().strip()
        if raw:
            self._url_preview.set(f"→ {normalize_url(raw)}")
        else:
            self._url_preview.set("")

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self._selected_idx = idx
        sites = load().get("sites", [])
        if idx >= len(sites):
            return
        s = sites[idx]
        for key in ("name", "url", "description"):
            self._entries[key].delete(0, tk.END)
            self._entries[key].insert(0, s.get(key, ""))
        self._entries["tags"].delete(0, tk.END)
        self._entries["tags"].insert(0, " ".join(s.get("tags", [])))
        self._update_url_preview()

    # ── CRUD ────────────────────────────────────────────────────────────────

    def _get_form(self):
        name = self._entries["name"].get().strip()
        url  = normalize_url(self._entries["url"].get())
        desc = self._entries["description"].get().strip()
        tags = self._entries["tags"].get().strip().split()
        return name, url, desc, tags

    def _add(self):
        name, url, desc, tags = self._get_form()
        if not name or not url:
            messagebox.showwarning("입력 오류", "이름과 URL은 필수예요.", parent=self)
            return
        data = load()
        if any(s["url"] == url for s in data["sites"]):
            messagebox.showwarning("중복", f"이미 있는 URL이에요:\n{url}", parent=self)
            return
        data["sites"].append({
            "name": name, "url": url, "description": desc,
            "tags": tags, "added": str(date.today()),
        })
        save(data)
        self._refresh()
        self._set_status(git_push(f"add: {name}"))

    def _edit(self):
        if self._selected_idx is None:
            messagebox.showwarning("선택 없음", "수정할 사이트를 목록에서 선택하세요.", parent=self)
            return
        name, url, desc, tags = self._get_form()
        if not name or not url:
            messagebox.showwarning("입력 오류", "이름과 URL은 필수예요.", parent=self)
            return
        data = load()
        s = data["sites"][self._selected_idx]
        s.update(name=name, url=url, description=desc, tags=tags)
        save(data)
        self._refresh()
        self._set_status(git_push(f"edit: {name}"))

    def _remove(self):
        if self._selected_idx is None:
            messagebox.showwarning("선택 없음", "삭제할 사이트를 목록에서 선택하세요.", parent=self)
            return
        data = load()
        s = data["sites"][self._selected_idx]
        if not messagebox.askyesno("삭제 확인", f"'{s['name']}' 을(를) 삭제할까요?",
                                   parent=self):
            return
        name = s["name"]
        data["sites"].pop(self._selected_idx)
        save(data)
        self._refresh()
        self._set_status(git_push(f"remove: {name}"))

    def _refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for s in load().get("sites", []):
            self.tree.insert("", tk.END, values=(
                s.get("name", ""),
                s.get("url", ""),
                " ".join(s.get("tags", [])),
                s.get("added", ""),
            ))
        self._selected_idx = None
        for e in self._entries.values():
            e.delete(0, tk.END)
        self._url_preview.set("")

    def _set_status(self, msg: str):
        self._status.set(msg)
        self.after(4000, lambda: self._status.set(""))


if __name__ == "__main__":
    app = App()
    app.mainloop()
