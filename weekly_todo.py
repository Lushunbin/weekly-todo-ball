import os
import sqlite3
import sys
import tkinter as tk
import calendar
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk


BG = "#F5F5F7"
CARD = "#FFFFFF"
INK = "#1D1D1F"
MUTED = "#86868B"
ACCENT = "#007AFF"
ACCENT_LIGHT = "#EAF3FF"
BORDER = "#E5E5EA"
ROW = "#FFFFFF"
FONT = "Microsoft YaHei UI"


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def monday_for(day: date) -> date:
    return day - timedelta(days=day.weekday())


def display_week(start: date) -> str:
    return f"{start:%Y年%m月%d日} — {(start + timedelta(days=6)):%m月%d日}"


class TodoDatabase:
    def __init__(self):
        preferred = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "WeeklyTodoBall")
        root = preferred
        try:
            os.makedirs(root, exist_ok=True)
        except OSError:
            # A portable fallback keeps the app usable in locked-down Windows profiles.
            root = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "WeeklyTodoBallData")
            os.makedirs(root, exist_ok=True)
        self.path = os.path.join(root, "todo.db")
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS weeks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_id INTEGER NOT NULL REFERENCES weeks(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_todos_week ON todos(week_id);
            """
        )
        self.conn.commit()

    def ensure_week(self, start: date) -> int:
        key = start.isoformat()
        row = self.conn.execute("SELECT id FROM weeks WHERE week_start=?", (key,)).fetchone()
        if row:
            return int(row["id"])
        cur = self.conn.execute("INSERT INTO weeks(week_start) VALUES (?)", (key,))
        self.conn.commit()
        return int(cur.lastrowid)

    def items(self, start: date):
        week_id = self.ensure_week(start)
        return self.conn.execute(
            "SELECT id,title,completed,created_at,completed_at FROM todos WHERE week_id=? ORDER BY completed ASC, id ASC",
            (week_id,),
        ).fetchall()

    def add(self, start: date, title: str):
        week_id = self.ensure_week(start)
        self.conn.execute(
            "INSERT INTO todos(week_id,title,created_at) VALUES (?,?,?)",
            (week_id, title, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def update_title(self, item_id: int, title: str):
        self.conn.execute("UPDATE todos SET title=? WHERE id=?", (title, item_id))
        self.conn.commit()

    def set_completed(self, item_id: int, completed: bool):
        self.conn.execute(
            "UPDATE todos SET completed=?, completed_at=? WHERE id=?",
            (1 if completed else 0, datetime.now().isoformat(timespec="seconds") if completed else None, item_id),
        )
        self.conn.commit()

    def delete(self, item_id: int):
        self.conn.execute("DELETE FROM todos WHERE id=?", (item_id,))
        self.conn.commit()

    def history(self, query: str):
        query = (query or "").strip()
        if query:
            like = f"%{query}%"
            return self.conn.execute(
                """
                SELECT w.week_start, t.id, t.title, t.completed, t.completed_at
                FROM weeks w LEFT JOIN todos t ON t.week_id=w.id
                WHERE w.week_start LIKE ? OR t.title LIKE ?
                ORDER BY w.week_start DESC, t.id ASC
                """,
                (like, like),
            ).fetchall()
        return self.conn.execute(
            """
            SELECT w.week_start, t.id, t.title, t.completed, t.completed_at
            FROM weeks w LEFT JOIN todos t ON t.week_id=w.id
            ORDER BY w.week_start DESC, t.id ASC
            """
        ).fetchall()

    def close(self):
        self.conn.close()


class CircleCheck(tk.Canvas):
    def __init__(self, master, checked=False, command=None, size=28, **kwargs):
        super().__init__(master, width=size, height=size, highlightthickness=0, bg=kwargs.pop("bg", CARD), **kwargs)
        self.checked = bool(checked)
        self.command = command
        self.size = size
        self.bind("<Button-1>", self._click)
        self.draw()

    def _click(self, _event=None):
        self.checked = not self.checked
        self.draw()
        if self.command:
            self.command(self.checked)

    def set(self, checked: bool):
        self.checked = bool(checked)
        self.draw()

    def draw(self):
        self.delete("all")
        p = 4
        if self.checked:
            self.create_oval(p, p, self.size - p, self.size - p, fill=ACCENT, outline=ACCENT)
            self.create_line(self.size * .28, self.size * .52, self.size * .44, self.size * .69,
                             self.size * .74, self.size * .32, fill="white", width=2.2, capstyle=tk.ROUND, joinstyle=tk.ROUND)
        else:
            self.create_oval(p, p, self.size - p, self.size - p, fill=CARD, outline="#B8C3D8", width=1.7)


class PillButton(tk.Canvas):
    """A lightweight rounded button, using only the standard Tk canvas."""

    def __init__(self, master, text, command, width=88, height=34, primary=False, font=None, surface=BG):
        super().__init__(master, width=width, height=height, bg=surface, highlightthickness=0, bd=0, cursor="hand2")
        self.text = text
        self.command = command
        self.primary = primary
        self.surface = surface
        self.font = font or (FONT, 10)
        self.hovered = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<Configure>", lambda _event: self.draw())
        self.draw()

    def rounded_rect(self, x1, y1, x2, y2, radius, fill):
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline="")
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline="")
        self.create_oval(x1, y1, x1 + radius * 2, y1 + radius * 2, fill=fill, outline="")
        self.create_oval(x2 - radius * 2, y1, x2, y1 + radius * 2, fill=fill, outline="")
        self.create_oval(x1, y2 - radius * 2, x1 + radius * 2, y2, fill=fill, outline="")
        self.create_oval(x2 - radius * 2, y2 - radius * 2, x2, y2, fill=fill, outline="")

    def draw(self):
        self.delete("all")
        fill = ACCENT if self.primary else CARD
        if self.hovered:
            fill = "#006FE6" if self.primary else ACCENT_LIGHT
        self.rounded_rect(1, 1, self.winfo_reqwidth() - 1, self.winfo_reqheight() - 1, 16, fill)
        self.create_text(self.winfo_reqwidth() / 2, self.winfo_reqheight() / 2, text=self.text,
                         fill="white" if self.primary else INK, font=self.font)

    def on_enter(self, _event=None):
        self.hovered = True
        self.draw()

    def on_leave(self, _event=None):
        self.hovered = False
        self.draw()

    def on_click(self, _event=None):
        if self.command:
            self.command()


class TodoRow(tk.Frame):
    def __init__(self, master, db: TodoDatabase, item, on_change, compact=False):
        super().__init__(master, bg=ROW, height=52, highlightthickness=0)
        self.db, self.item, self.on_change, self.compact = db, item, on_change, compact
        self.pack_propagate(False)
        self.columnconfigure(1, weight=1)
        check = CircleCheck(self, item["completed"], self.toggle, bg=ROW, size=28)
        check.grid(row=0, column=0, padx=(13, 10), pady=12, sticky="n")
        self.check = check
        self.label = tk.Label(self, text=item["title"], anchor="w", bg=ROW, fg=MUTED if item["completed"] else INK,
                              font=(FONT, 10), padx=0)
        self.label.grid(row=0, column=1, sticky="ew", pady=13)
        self.edit_var = tk.StringVar(value=item["title"])
        self.edit = tk.Entry(self, textvariable=self.edit_var, font=(FONT, 10), relief="solid", bd=1)
        self.edit.grid(row=0, column=1, sticky="ew", pady=9)
        self.edit.grid_remove()
        if not compact:
            self.edit_btn = tk.Button(self, text="编辑", command=self.toggle_edit, width=5, relief="flat", bd=0,
                                      bg=ROW, fg=ACCENT, activebackground=ACCENT_LIGHT, font=(FONT, 9), cursor="hand2")
            self.edit_btn.grid(row=0, column=2, padx=(8, 2))
            self.delete_btn = tk.Button(self, text="删除", command=self.remove, width=5, relief="flat", bd=0,
                                        bg=ROW, fg="#B0636B", activebackground="#FCEBEC", font=(FONT, 9), cursor="hand2")
            self.delete_btn.grid(row=0, column=3, padx=(0, 9))
        self.bind("<Double-Button-1>", lambda _e: self.toggle_edit())
        self.label.bind("<Double-Button-1>", lambda _e: self.toggle_edit())

    def toggle(self, value):
        self.db.set_completed(self.item["id"], value)
        self.on_change()

    def toggle_edit(self):
        if self.edit.winfo_ismapped():
            value = self.edit_var.get().strip()
            if not value:
                return
            self.db.update_title(self.item["id"], value)
            self.label.configure(text=value)
            self.edit.grid_remove()
            self.label.grid()
            if hasattr(self, "edit_btn"):
                self.edit_btn.configure(text="编辑")
            self.on_change()
        else:
            self.edit_var.set(self.label.cget("text"))
            self.label.grid_remove()
            self.edit.grid()
            if hasattr(self, "edit_btn"):
                self.edit_btn.configure(text="保存")
            self.edit.focus_set()
            self.edit.selection_range(0, tk.END)

    def remove(self):
        if messagebox.askyesno("删除待办", "确定删除这项待办吗？"):
            self.db.delete(self.item["id"])
            self.on_change()


class HistoryWindow(tk.Toplevel):
    def __init__(self, master, db: TodoDatabase):
        super().__init__(master)
        self.db = db
        self.title("待办记录查询")
        self.geometry("760x520")
        self.minsize(620, 420)
        self.configure(bg=BG)
        self.transient(master)
        self.build()
        self.refresh()

    def build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=22, pady=(18, 12))
        tk.Label(top, text="历史记录", bg=BG, fg=INK, font=(FONT, 17, "bold")).pack(side="left")
        self.search = tk.Entry(top, font=(FONT, 10), relief="solid", bd=1)
        self.search.pack(side="left", padx=(30, 0), fill="x", expand=True, ipady=6)
        self.search.insert(0, "")
        self.search.bind("<KeyRelease>", lambda _e: self.refresh())
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=(0, 22))
        self.week_list = tk.Listbox(body, width=29, bd=0, highlightthickness=0, bg=CARD, fg=INK,
                                    selectbackground=ACCENT_LIGHT, selectforeground=INK, font=(FONT, 10), activestyle="none")
        self.week_list.pack(side="left", fill="both", expand=False)
        self.week_list.bind("<<ListboxSelect>>", lambda _e: self.show_detail())
        self.detail = tk.Text(body, bd=0, wrap="word", bg=CARD, fg=INK, padx=18, pady=16, font=(FONT, 10), state="disabled")
        self.detail.pack(side="left", fill="both", expand=True, padx=(12, 0))

    def refresh(self):
        rows = self.db.history(self.search.get())
        grouped = {}
        for row in rows:
            bucket = grouped.setdefault(row["week_start"], [])
            if row["id"] is not None:
                bucket.append(row)
        self.groups = list(grouped.items())
        self.week_list.delete(0, tk.END)
        for key, items in self.groups:
            done = sum(1 for x in items if x["completed"])
            self.week_list.insert(tk.END, f"{key}    {done}/{len(items)}")
        if self.groups:
            self.week_list.selection_set(0)
            self.show_detail()
        else:
            self.set_detail("没有匹配的记录。")

    def set_detail(self, text):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", tk.END)
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def show_detail(self):
        selection = self.week_list.curselection()
        if not selection:
            return
        key, items = self.groups[selection[0]]
        try:
            start = date.fromisoformat(key)
            heading = f"{display_week(start)}\n共 {len(items)} 项，已完成 {sum(1 for x in items if x['completed'])} 项\n\n"
        except ValueError:
            heading = f"{key}\n\n"
        lines = []
        for item in items:
            if item["id"] is None:
                continue
            completed_time = ""
            if item["completed_at"]:
                try:
                    completed_time = f"  ({datetime.fromisoformat(item['completed_at']):%m-%d %H:%M} 完成)"
                except ValueError:
                    pass
            lines.append(f"{'✓' if item['completed'] else '○'}  {item['title']}{completed_time}")
        self.set_detail(heading + ("\n".join(lines) if lines else "暂无待办。"))


class CalendarPicker(tk.Toplevel):
    """Small dependency-free calendar used to choose the target week."""

    def __init__(self, master, selected_day: date, on_select):
        super().__init__(master)
        self.on_select = on_select
        self.selected_day = selected_day
        self.year = selected_day.year
        self.month = selected_day.month
        self.title("选择日期")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.transient(master)
        self.grab_set()
        self.render()

    def render(self):
        for child in self.winfo_children():
            child.destroy()

        root = tk.Frame(self, bg=BG, padx=16, pady=14)
        root.pack(fill="both", expand=True)
        head = tk.Frame(root, bg=BG)
        head.pack(fill="x", pady=(0, 10))
        tk.Button(head, text="‹", command=lambda: self.move_month(-1), width=3, relief="flat", bd=0,
                  bg=CARD, fg=INK, activebackground=ACCENT_LIGHT, cursor="hand2").pack(side="left")
        tk.Label(head, text=f"{self.year}年{self.month}月", bg=BG, fg=INK, font=(FONT, 12, "bold")).pack(side="left", expand=True)
        tk.Button(head, text="›", command=lambda: self.move_month(1), width=3, relief="flat", bd=0,
                  bg=CARD, fg=INK, activebackground=ACCENT_LIGHT, cursor="hand2").pack(side="right")

        grid = tk.Frame(root, bg=BG)
        grid.pack()
        for column, text in enumerate(("一", "二", "三", "四", "五", "六", "日")):
            tk.Label(grid, text=text, width=4, bg=BG, fg=MUTED, font=(FONT, 9)).grid(row=0, column=column, padx=2, pady=(0, 4))

        for row_index, week in enumerate(calendar.monthcalendar(self.year, self.month), start=1):
            for column, day_number in enumerate(week):
                if day_number == 0:
                    tk.Label(grid, text="", width=4, bg=BG).grid(row=row_index, column=column, padx=2, pady=2)
                    continue
                current = date(self.year, self.month, day_number)
                selected = current == self.selected_day
                is_today = current == date.today()
                button = tk.Button(
                    grid,
                    text=str(day_number),
                    width=4,
                    command=lambda picked=current: self.pick(picked),
                    relief="flat",
                    bd=0,
                    bg=ACCENT if selected else (ACCENT_LIGHT if is_today else CARD),
                    fg="white" if selected else (ACCENT if is_today else INK),
                    activebackground=ACCENT,
                    activeforeground="white",
                    font=(FONT, 9),
                    cursor="hand2",
                )
                button.grid(row=row_index, column=column, padx=2, pady=2)

        tk.Button(root, text="今天", command=lambda: self.pick(date.today()), relief="flat", bd=0,
                  bg=BG, fg=ACCENT, activebackground=ACCENT_LIGHT, cursor="hand2", font=(FONT, 9)).pack(pady=(10, 0))

    def move_month(self, offset):
        self.month += offset
        if self.month == 0:
            self.year -= 1
            self.month = 12
        elif self.month == 13:
            self.year += 1
            self.month = 1
        self.render()

    def pick(self, picked_day: date):
        self.on_select(picked_day)
        self.destroy()


class FloatingBall(tk.Toplevel):
    """A draggable ball that expands only after a deliberate single click."""

    def __init__(self, master, db: TodoDatabase, restore_callback, initial_position=None):
        super().__init__(master)
        self.db, self.restore_callback = db, restore_callback
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=ACCENT)
        self.compact_size = 76
        self.expanded = False
        self.expanded_frame = None
        self.drag_start = None
        self.dragging = False
        self.single_click_id = None
        self.compact_position = initial_position

        self.ball = tk.Canvas(self, width=self.compact_size, height=self.compact_size, bg=ACCENT, highlightthickness=0)
        self.ball.pack()
        self.ball.bind("<ButtonPress-1>", self.start_drag)
        self.ball.bind("<B1-Motion>", self.drag)
        self.ball.bind("<ButtonRelease-1>", self.end_drag)
        self.ball.bind("<Double-Button-1>", self.open_editor)
        self.position_compact()
        self.refresh_ball()
        self.monitor_id = self.after(180, self.monitor)

    def work_area(self):
        # Keep the panel above the taskbar, while leaving a narrow safety margin.
        return self.winfo_screenwidth(), max(260, self.winfo_screenheight() - 48)

    def clamp_compact_position(self, x, y):
        width, height = self.work_area()
        return (
            max(8, min(int(x), max(8, width - self.compact_size - 8))),
            max(8, min(int(y), max(8, height - self.compact_size - 8))),
        )

    def position_compact(self):
        if self.compact_position is None:
            width, height = self.work_area()
            self.compact_position = (width - self.compact_size - 30, height - self.compact_size - 18)
        self.compact_position = self.clamp_compact_position(*self.compact_position)
        x, y = self.compact_position
        self.geometry(f"{self.compact_size}x{self.compact_size}+{x}+{y}")
        self.draw_ball()

    def cancel_single_click(self):
        if self.single_click_id is not None:
            try:
                self.after_cancel(self.single_click_id)
            except tk.TclError:
                pass
            self.single_click_id = None

    def start_drag(self, event):
        self.cancel_single_click()
        self.dragging = False
        self.drag_start = (event.x_root, event.y_root, self.winfo_x(), self.winfo_y())

    def drag(self, event):
        if not self.drag_start or self.expanded:
            return
        start_x, start_y, window_x, window_y = self.drag_start
        delta_x, delta_y = event.x_root - start_x, event.y_root - start_y
        if abs(delta_x) + abs(delta_y) >= 3:
            self.dragging = True
        x, y = self.clamp_compact_position(window_x + delta_x, window_y + delta_y)
        self.geometry(f"+{x}+{y}")

    def end_drag(self, _event=None):
        self.drag_start = None
        if self.dragging:
            self.compact_position = self.clamp_compact_position(self.winfo_x(), self.winfo_y())
            self.dragging = False
            return
        # Delay the action just enough to distinguish one click from a double click.
        self.cancel_single_click()
        self.single_click_id = self.after(260, self.expand)

    def open_editor(self, _event=None):
        self.cancel_single_click()
        self.restore()
        return "break"

    def draw_ball(self):
        self.ball.delete("all")
        self.ball.create_oval(5, 5, self.compact_size - 5, self.compact_size - 5, fill=ACCENT, outline="")
        items = self.db.items(monday_for(date.today()))
        pending = sum(1 for row in items if not row["completed"])
        text = "✓\n完成" if pending == 0 else f"{pending}\n待办"
        self.ball.create_text(self.compact_size / 2, self.compact_size / 2, text=text, fill="white", font=(FONT, 10, "bold"))

    def expanded_geometry(self, width, height):
        screen_width, work_height = self.work_area()
        ball_x, ball_y = self.compact_position
        # Keep the ball's corner fixed: left-bottom expands right-up; left-top right-down.
        expand_right = ball_x + self.compact_size / 2 <= screen_width / 2
        expand_down = ball_y + self.compact_size / 2 <= work_height / 2
        x = ball_x if expand_right else ball_x + self.compact_size - width
        y = ball_y if expand_down else ball_y + self.compact_size - height
        x = max(8, min(x, max(8, screen_width - width - 8)))
        y = max(8, min(y, max(8, work_height - height - 8)))
        return int(x), int(y)

    def expand(self):
        self.single_click_id = None
        if self.expanded:
            return
        items = self.db.items(monday_for(date.today()))
        screen_width, work_height = self.work_area()
        width = min(340, max(280, screen_width - 16))
        desired_height = 162 + max(1, len(items)) * 47
        height = min(max(220, desired_height), max(220, work_height - 16))
        x, y = self.expanded_geometry(width, height)

        self.expanded = True
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(bg=BG)
        self.ball.pack_forget()
        self.expanded_frame = tk.Frame(self, bg=BG, padx=18, pady=16)
        self.expanded_frame.pack(fill="both", expand=True)
        head = tk.Frame(self.expanded_frame, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text="本周待办", bg=BG, fg=INK, font=(FONT, 15, "bold")).pack(side="left")
        tk.Button(head, text="编辑", command=self.restore, relief="flat", bd=0, bg=ACCENT, fg="white",
                  activebackground=ACCENT, font=(FONT, 9), padx=10, cursor="hand2").pack(side="right")
        tk.Label(self.expanded_frame, text="移出面板自动收起；双击悬浮球可直接编辑", bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(3, 9))
        self.footer = tk.Label(self.expanded_frame, text="", bg=BG, fg=MUTED, font=(FONT, 9), anchor="w")
        self.footer.pack(fill="x", side="bottom", pady=(8, 0))

        list_holder = tk.Frame(self.expanded_frame, bg=BG)
        list_holder.pack(fill="both", expand=True)
        self.items_canvas = tk.Canvas(list_holder, bg=BG, highlightthickness=0)
        self.items_scroll = ttk.Scrollbar(list_holder, orient="vertical", command=self.items_canvas.yview)
        self.items_frame = tk.Frame(self.items_canvas, bg=BG)
        self.items_window_id = self.items_canvas.create_window((0, 0), window=self.items_frame, anchor="nw")
        self.items_frame.bind("<Configure>", lambda _e: self.items_canvas.configure(scrollregion=self.items_canvas.bbox("all")))
        self.items_canvas.bind("<Configure>", lambda event: self.items_canvas.itemconfigure(self.items_window_id, width=event.width))
        self.items_canvas.configure(yscrollcommand=self.items_scroll.set)
        self.items_canvas.pack(side="left", fill="both", expand=True)
        self.items_scroll.pack(side="right", fill="y")
        self.refresh_expanded()

    def refresh_ball(self):
        if not self.expanded:
            self.draw_ball()

    def refresh_expanded(self):
        if not self.expanded:
            return
        for child in self.items_frame.winfo_children():
            child.destroy()
        items = self.db.items(monday_for(date.today()))
        for item in items:
            row = tk.Frame(self.items_frame, bg=CARD, height=42)
            row.pack(fill="x", pady=(0, 5))
            row.pack_propagate(False)
            row.columnconfigure(1, weight=1)
            CircleCheck(row, item["completed"], lambda value, item_id=item["id"]: self.set_float_done(item_id, value), bg=CARD, size=26).grid(row=0, column=0, padx=(9, 8), pady=8)
            tk.Label(row, text=item["title"], bg=CARD, fg=MUTED if item["completed"] else INK, anchor="w", font=(FONT, 9)).grid(row=0, column=1, sticky="ew", pady=10)
        if not items:
            tk.Label(self.items_frame, text="暂无待办", bg=BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=10)
        self.footer.configure(text=f"未完成 {sum(1 for row in items if not row['completed'])} 项 · 数据保存在本机")

    def set_float_done(self, item_id, value):
        self.db.set_completed(item_id, value)
        self.refresh_expanded()

    def monitor(self):
        if self.winfo_exists():
            if self.expanded:
                x, y = self.winfo_pointerxy()
                if not (self.winfo_rootx() <= x <= self.winfo_rootx() + self.winfo_width() and self.winfo_rooty() <= y <= self.winfo_rooty() + self.winfo_height()):
                    self.collapse()
            self.monitor_id = self.after(180, self.monitor)

    def collapse(self):
        if not self.expanded:
            return
        self.expanded = False
        if self.expanded_frame:
            self.expanded_frame.destroy()
        self.configure(bg=ACCENT)
        self.ball.pack()
        self.position_compact()

    def restore(self):
        self.cancel_single_click()
        try:
            self.after_cancel(self.monitor_id)
        except tk.TclError:
            pass
        self.restore_callback(self.compact_position)
        self.destroy()

    def destroy(self):
        try:
            self.after_cancel(self.monitor_id)
        except Exception:
            pass
        self.cancel_single_click()
        super().destroy()


class WeeklyTodoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = TodoDatabase()
        self.week_start = monday_for(date.today())
        self.floating_position = None
        self.floating = None
        self.minimize_check_scheduled = False
        self.title("每周待办 · Weekly Todo")
        self.geometry("860x650")
        self.minsize(700, 500)
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.bind("<Unmap>", self.on_window_unmap)
        self.build()
        self.refresh()

    def style_button(self, button, primary=False):
        button.configure(relief="flat", bd=0, highlightthickness=0, padx=10, pady=4,
                         bg=ACCENT if primary else CARD, fg="white" if primary else INK,
                         activebackground=ACCENT if primary else ACCENT_LIGHT, activeforeground="white" if primary else INK,
                         font=(FONT, 10), cursor="hand2")

    def build(self):
        outer = tk.Frame(self, bg=BG, padx=26, pady=22)
        outer.pack(fill="both", expand=True)
        footer = tk.Frame(outer, bg=BG, height=50)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        self.summary = tk.Label(footer, bg=BG, fg=MUTED, font=(FONT, 9), anchor="w")
        self.summary.pack(side="left", pady=8)
        history_btn = PillButton(footer, "记录查询", self.show_history, width=92, surface=BG)
        history_btn.pack(side="right", pady=2)
        export_btn = PillButton(footer, "导出本周", self.export_week, width=92, surface=BG)
        export_btn.pack(side="right", padx=(0, 10), pady=2)

        input_frame = tk.Frame(outer, bg=BG, height=52)
        input_frame.pack(side="top", fill="x", pady=(10, 10))
        self.input_var = tk.StringVar()
        self.input = tk.Entry(input_frame, textvariable=self.input_var, font=(FONT, 10), relief="flat", bd=0,
                              bg=CARD, fg=INK, insertbackground=INK, highlightthickness=1, highlightbackground=BORDER,
                              highlightcolor=ACCENT)
        self.input.pack(side="left", fill="x", expand=True, ipady=9)
        self.input.bind("<Return>", lambda _e: self.add_item())
        add_btn = PillButton(input_frame, "添加", self.add_item, width=76, height=38, primary=True, surface=BG)
        add_btn.pack(side="left", padx=(10, 0))

        self.list_card = tk.Frame(outer, bg=CARD, padx=18, pady=16, highlightbackground=BORDER, highlightthickness=1)
        self.list_card.pack(side="top", fill="both", expand=True)
        self.list_canvas = tk.Canvas(self.list_card, bg=CARD, highlightthickness=0)
        self.scroll = ttk.Scrollbar(self.list_card, orient="vertical", command=self.list_canvas.yview)
        self.rows_frame = tk.Frame(self.list_canvas, bg=CARD)
        self.rows_frame.bind("<Configure>", lambda _e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.list_canvas.configure(yscrollcommand=self.scroll.set)
        self.list_canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        self.list_canvas.bind("<Configure>", lambda e: self.list_canvas.itemconfigure(1, width=e.width))

        header = tk.Frame(outer, bg=BG, height=72)
        header.pack(side="top", fill="x")
        tk.Label(header, text="本周待办", bg=BG, fg=INK, font=(FONT, 22, "bold")).pack(anchor="w")
        self.week_label = tk.Label(header, text="", bg=BG, fg=MUTED, font=(FONT, 10))
        self.week_label.pack(anchor="w", pady=(3, 0))
        self.week_label.bind("<Button-1>", lambda _e: self.open_calendar())
        self.week_label.configure(cursor="hand2")
        nav = tk.Frame(header, bg=BG)
        nav.place(relx=1, rely=0, anchor="ne")
        calendar_btn = PillButton(nav, "日历", self.open_calendar, width=58, surface=BG)
        calendar_btn.pack(side="left", padx=(0, 7))
        for text, command, width, pixels in (("‹", lambda: self.change_week(-7), 3, 34), ("›", lambda: self.change_week(7), 3, 34), ("回到本周", self.go_today, 8, 78)):
            btn = PillButton(nav, text, command, width=pixels, surface=BG,
                             font=("Segoe UI", 13) if text in ("‹", "›") else (FONT, 9))
            btn.pack(side="left", padx=(0, 7))
        # Header was created after the content cards so it is explicitly moved
        # to the top of the pack order.
        header.pack_forget()
        header.pack(side="top", fill="x", before=input_frame)

    def add_item(self):
        title = self.input_var.get().strip()
        if not title:
            return
        self.db.add(self.week_start, title)
        self.input_var.set("")
        self.refresh()

    def change_week(self, days):
        self.week_start += timedelta(days=days)
        self.refresh()

    def go_today(self):
        self.week_start = monday_for(date.today())
        self.refresh()

    def open_calendar(self):
        # Any date in the calendar maps to its Monday, so the view always stays weekly.
        CalendarPicker(self, self.week_start, self.choose_calendar_date)

    def choose_calendar_date(self, selected_day):
        self.week_start = monday_for(selected_day)
        self.refresh()

    def export_week(self):
        items = self.db.items(self.week_start)
        suggested_name = f"待办_{self.week_start:%Y%m%d}.txt"
        target = filedialog.asksaveasfilename(
            parent=self,
            title="导出本周待办",
            initialfile=suggested_name,
            defaultextension=".txt",
            filetypes=(("文本文件", "*.txt"), ("所有文件", "*.*")),
        )
        if not target:
            return
        lines = [f"本周待办（{display_week(self.week_start)}）", ""]
        if items:
            for index, item in enumerate(items, start=1):
                suffix = " [已完成]" if item["completed"] else ""
                lines.append(f"{index}. {item['title']}{suffix}")
        else:
            lines.append("本周暂无待办。")
        try:
            with open(target, "w", encoding="utf-8-sig", newline="\n") as output:
                output.write("\n".join(lines))
            messagebox.showinfo("导出完成", f"已导出 {len(items)} 项待办：\n{target}", parent=self)
        except OSError as error:
            messagebox.showerror("导出失败", f"无法写入文件：\n{error}", parent=self)

    def refresh(self):
        items = self.db.items(self.week_start)
        self.week_label.configure(text=f"{display_week(self.week_start)}   ·   {sum(1 for x in items if not x['completed'])} 项未完成")
        self.summary.configure(text=f"已完成 {sum(1 for x in items if x['completed'])} / 共 {len(items)} 项")
        for child in self.rows_frame.winfo_children():
            child.destroy()
        if not items:
            tk.Label(self.rows_frame, text="这周还没有待办，先添加一项吧。", bg=CARD, fg=MUTED, font=(FONT, 10), pady=30).pack(fill="x")
        else:
            for item in items:
                TodoRow(self.rows_frame, self.db, item, self.refresh).pack(fill="x", pady=(0, 8))

    def show_history(self):
        HistoryWindow(self, self.db)

    def on_window_unmap(self, event):
        if event.widget is not self or self.minimize_check_scheduled:
            return
        self.minimize_check_scheduled = True
        self.after(60, self.convert_minimize_to_float)

    def convert_minimize_to_float(self):
        self.minimize_check_scheduled = False
        if self.state() == "iconic":
            self.enter_float()

    def enter_float(self):
        if self.floating is not None:
            try:
                if self.floating.winfo_exists():
                    return
            except tk.TclError:
                pass
        self.withdraw()
        self.floating = FloatingBall(self, self.db, self.restore_main, self.floating_position)

    def restore_main(self, floating_position=None):
        if floating_position is not None:
            self.floating_position = floating_position
        self.floating = None
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()
        self.refresh()

    def close_app(self):
        if self.floating is not None:
            try:
                self.floating.destroy()
            except tk.TclError:
                pass
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = WeeklyTodoApp()
    app.mainloop()
