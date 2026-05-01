"""通用 Tooltip 组件 — 鼠标悬停显示提示文字"""

import tkinter as tk


class ToolTip:
    """为任意 tkinter 控件添加悬停提示"""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500):
        self.widget = widget
        self.text = text
        self.delay = delay  # 毫秒
        self._tip_window = None
        self._after_id = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def update_text(self, text: str):
        self.text = text

    def _on_enter(self, event):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show_tip)

    def _on_leave(self, event):
        self._cancel()
        self._hide_tip()

    def _cancel(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show_tip(self):
        if self._tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#FFFFDD", foreground="#333333",
            relief=tk.SOLID, borderwidth=1,
            font=("Microsoft YaHei UI", 9), padx=6, pady=3,
        )
        label.pack()

    def _hide_tip(self):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None
