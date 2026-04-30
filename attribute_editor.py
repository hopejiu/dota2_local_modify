"""属性编辑 Tab 组件"""

import tkinter as tk
from tkinter import ttk

from hero_constants import HERO_ATTRIBUTES, BASE_DEFAULTS


class AttributeEditor:
    """封装属性 Tab 的 UI 构建、数据加载、修改检测、校验、保存"""

    def __init__(self, on_change_callback=None):
        self.entry_widgets = {}   # 属性键名 → Entry 控件
        self.original_values = {} # 属性键名 → 原始值
        self._has_changes = False
        self._on_change_callback = on_change_callback  # 外部变更通知回调

        # UI 引用
        self.scrollable_frame = None
        self.canvas = None
        self.canvas_window = None

    def build(self, parent: ttk.Frame):
        """构建属性编辑 Tab 的 UI"""
        # 可滚动属性区域
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                                  command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame,
                                                        anchor=tk.NW)
        self.canvas.configure(yscrollcommand=v_scroll.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # 构建属性编辑字段
        self._build_attribute_fields()

    def _build_attribute_fields(self):
        """构建属性编辑字段"""
        for group_name, attrs in HERO_ATTRIBUTES.items():
            # 分组标题
            group_label = ttk.Label(self.scrollable_frame, text=group_name,
                                     font=("Microsoft YaHei UI", 11))
            group_label.pack(anchor=tk.W, pady=(10, 5), padx=5)

            # 分组内容用 grid 布局，3列
            grid_frame = ttk.Frame(self.scrollable_frame)
            grid_frame.pack(fill=tk.X, padx=10)

            for i, (key, label_text) in enumerate(attrs):
                row, col = divmod(i, 3)

                field_frame = ttk.Frame(grid_frame)
                field_frame.grid(row=row, column=col, sticky=tk.W, padx=(0, 15), pady=3)

                ttk.Label(field_frame, text=label_text,
                          font=("Microsoft YaHei UI", 9)).pack(anchor=tk.W)

                entry = tk.Entry(field_frame, width=12, font=("Microsoft YaHei UI", 9))
                entry.pack(anchor=tk.W)

                self.entry_widgets[key] = entry

    def load(self, hero_data: dict):
        """加载指定英雄的属性到编辑框"""
        # 填充属性值（合并 base 默认值），记录原始值
        for key, entry in self.entry_widgets.items():
            value = hero_data.get(key, BASE_DEFAULTS.get(key, ""))
            str_value = str(value)
            self.original_values[key] = str_value

            entry.configure(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.insert(0, str_value)

            # 重置背景色
            entry.configure(bg="white")

            # 绑定修改检测
            entry.unbind("<KeyRelease>")
            entry.bind("<KeyRelease>", lambda e, k=key: self._on_value_change(k))

        self._has_changes = False

    def validate(self) -> tuple:
        """校验所有输入值

        返回: (is_valid, error_message)
        """
        for key, entry in self.entry_widgets.items():
            val = entry.get().strip()
            if not val:
                continue
            try:
                float(val)
            except ValueError:
                label = self._get_label_for_key(key)
                return False, f"\"{label}\" 的值 \"{val}\" 不是有效数字"
        return True, ""

    def apply_changes(self, hero_data: dict):
        """将编辑框中的值应用到英雄数据 dict"""
        for key, entry in self.entry_widgets.items():
            val = entry.get().strip()
            if val:
                hero_data[key] = val

    def has_changes(self) -> bool:
        """是否有未保存的修改"""
        return self._has_changes

    def reset_changes_flag(self):
        """重置修改标记"""
        self._has_changes = False

    def _on_value_change(self, key: str):
        """属性值变化时，根据是否与原始值不同来标记背景色"""
        entry = self.entry_widgets.get(key)
        if not entry:
            return
        current = entry.get().strip()
        original = self.original_values.get(key, "")
        if current != original:
            entry.configure(bg="#FFFACD")  # 淡黄色背景
            self._has_changes = True
        else:
            entry.configure(bg="white")
            self._check_unsaved_changes()

        # 通知外部
        if self._on_change_callback:
            self._on_change_callback()

    def _check_unsaved_changes(self):
        """检查所有属性是否与原始值相同，更新未保存标记"""
        for key, entry in self.entry_widgets.items():
            current = entry.get().strip()
            original = self.original_values.get(key, "")
            if current != original:
                self._has_changes = True
                return
        self._has_changes = False

    def _get_label_for_key(self, key: str) -> str:
        """根据属性键名获取中文标签"""
        for group_attrs in HERO_ATTRIBUTES.values():
            for attr_key, label in group_attrs:
                if attr_key == key:
                    return label
        return key

    def _on_canvas_configure(self, event):
        """Canvas 大小变化时，调整内部 frame 宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, event):
        """绑定鼠标滚轮"""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        """解绑鼠标滚轮"""
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        """鼠标滚轮滚动"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
