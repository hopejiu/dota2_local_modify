"""英雄编辑器主窗口 — 协调属性编辑和技能编辑"""

import os
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import vdf

from hero_constants import EN_TO_CN, HERO_ATTRIBUTES, BASE_DEFAULTS, get_pak01_dir, get_npc_heroes_path
from attribute_editor import AttributeEditor
from skill_editor import SkillEditor
from tooltip import ToolTip
import unpack


class HeroEditorWindow:
    def __init__(self, parent, file_path: str):
        self.parent = parent
        self.file_path = file_path
        self.heroes_data = None  # vdf 加载的完整数据
        self.hero_keys = []  # 所有英雄的 vdf 键名列表
        self.filtered_keys = []  # 当前过滤后显示的英雄键名列表
        self.current_hero_key = None  # 当前选中的英雄键名

        # 编辑器组件
        self.attr_editor = AttributeEditor(on_change_callback=self._on_edit_change)
        self.skill_editor = SkillEditor(file_path, on_change_callback=self._on_edit_change)

        # 延迟自动写入定时器
        self._auto_save_timer_id = None
        self._pending_status_message = ""

        self._create_window()
        self._load_data()
        self._backup_heroes_file()
        self._build_ui()

        # 窗口关闭确认
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        # 撤销/重做快捷键
        self.win.bind("<Control-z>", self._on_undo)
        self.win.bind("<Control-y>", self._on_redo)

    def _create_window(self):
        self.win = tk.Toplevel(self.parent)
        self.win.title("英雄属性编辑")
        self.win.resizable(True, True)

        # 窗口大小和居中（加宽以容纳技能编辑区）
        w, h = 1050, 700
        sx = (self.win.winfo_screenwidth() - w) // 2
        sy = (self.win.winfo_screenheight() - h) // 2
        self.win.geometry(f"{w}x{h}+{sx}+{sy}")
        self.win.minsize(w, h)

        # 图标
        icon_path = os.path.join(unpack.get_app_dir(), "icon.ico")
        if os.path.exists(icon_path):
            self.win.iconbitmap(icon_path)

    def _backup_heroes_file(self):
        """备份 npc_heroes.txt（仅首次），并加载备份数据用于对比"""
        npc_heroes_path = get_npc_heroes_path()
        self.heroes_backup_path = npc_heroes_path + ".bak"
        if os.path.exists(npc_heroes_path) and not os.path.exists(self.heroes_backup_path):
            shutil.copy2(npc_heroes_path, self.heroes_backup_path)

        # 加载备份数据用于对比（变黄判断）
        self._backup_heroes_data = None
        if os.path.exists(self.heroes_backup_path):
            try:
                with open(self.heroes_backup_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = unpack.preprocess_vdf_content(content)
                self._backup_heroes_data = vdf.loads(content)
            except Exception:
                pass

    def _load_data(self):
        """自动解压（如需要）并加载英雄数据"""
        # 检测游戏是否运行
        if unpack.is_dota2_running():
            messagebox.showwarning("警告",
                                   "检测到 Dota2 正在运行！\n\n"
                                   "游戏运行时修改文件可能导致冲突或无法保存。\n"
                                   "建议先关闭游戏再进行编辑。")

        pak01_dir = get_pak01_dir()
        npc_heroes_path = get_npc_heroes_path()

        # 检查是否需要解压
        if not os.path.exists(pak01_dir):
            try:
                unpack.unpack_from_vpk(self.file_path)
            except Exception as e:
                messagebox.showerror("解压失败",
                    f"自动解压游戏数据失败，请确认 dota2.exe 路径正确且游戏未在运行。\n\n"
                    f"详细信息：{e}")
                self.win.destroy()
                return

        # 检查 npc_heroes.txt 是否存在
        if not os.path.exists(npc_heroes_path):
            messagebox.showerror("找不到数据",
                "找不到英雄数据文件，请先在主界面点击「解压文件」。")
            self.win.destroy()
            return

        # 加载 VDF 数据
        try:
            with open(npc_heroes_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = unpack.preprocess_vdf_content(content)
            self.heroes_data = vdf.loads(content)
        except Exception as e:
            messagebox.showerror("加载失败",
                f"加载英雄数据失败，请尝试在主界面重新解压文件。\n\n"
                f"详细信息：{e}")
            self.win.destroy()
            return

        # 构建英雄列表（排除 base）
        dota_heroes = self.heroes_data.get("DOTAHeroes", {})
        self.hero_keys = [
            k for k in dota_heroes.keys()
            if k.startswith("npc_dota_hero_") and k != "npc_dota_hero_base"
               and isinstance(dota_heroes[k], dict)
        ]

    def _build_ui(self):
        if self.heroes_data is None:
            return

        # ---- 主容器 ----
        main_frame = ttk.Frame(self.win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ---- 左侧面板：英雄列表 ----
        left_frame = ttk.LabelFrame(main_frame, text="英雄列表", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # 搜索框（带占位提示）
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        self._search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        self._search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._search_placeholder = True
        self._show_search_placeholder()
        self._search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self._search_entry.bind("<FocusOut>", self._on_search_focus_out)
        ttk.Button(search_frame, text="×", width=3,
                   command=self._clear_search).pack(side=tk.LEFT, padx=(3, 0))

        # 英雄列表
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.hero_listbox = tk.Listbox(list_frame, width=18, height=28,
                                        font=("Microsoft YaHei UI", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                   command=self.hero_listbox.yview)
        self.hero_listbox.configure(yscrollcommand=scrollbar.set)
        self.hero_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.hero_listbox.bind("<<ListboxSelect>>", self._on_hero_select)

        # 填充列表
        self._populate_hero_list()

        # 批量修改按钮
        batch_frame = ttk.Frame(left_frame)
        batch_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(batch_frame, text="批量修改", width=18,
                   command=self._open_batch_modify).pack()

        # 还原全部英雄按钮
        ttk.Button(batch_frame, text="还原全部英雄", width=18,
                   command=self._reset_all).pack(pady=(3, 0))

        # ---- 右侧面板：Notebook（属性 Tab + 技能 Tab）----
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 英雄名称标题
        self.hero_title_label = ttk.Label(right_frame, text="请选择英雄",
                                           font=("Microsoft YaHei UI", 14, "bold"))
        self.hero_title_label.pack(anchor=tk.W, pady=(0, 10))

        # Notebook Tab 切换
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 图例提示
        legend_frame = ttk.Frame(right_frame)
        legend_frame.pack(fill=tk.X, pady=(2, 0))
        legend_label = tk.Label(legend_frame, text="  ■ ", fg="#FFFACD", bg="#FFFACD",
                                font=("", 10), relief=tk.RIDGE, padx=2, pady=1)
        legend_label.pack(side=tk.LEFT)
        ttk.Label(legend_frame, text=" = 已修改（自动保存到文件，需打包后才在游戏中生效）",
                  font=("", 9), foreground="gray").pack(side=tk.LEFT)

        # 属性 Tab
        attr_tab = ttk.Frame(self.notebook)
        self.notebook.add(attr_tab, text="属性")
        self.attr_editor.build(attr_tab)

        # 技能 Tab
        skill_tab = ttk.Frame(self.notebook)
        self.notebook.add(skill_tab, text="技能")
        self.skill_editor.build(skill_tab)

        # ---- 底部按钮 ----
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        # #14 撤销/重做按钮
        self._undo_btn = ttk.Button(btn_frame, text="撤销", width=6,
                                     command=self._do_undo, state=tk.DISABLED)
        self._undo_btn.pack(side=tk.LEFT, padx=(0, 2))
        ToolTip(self._undo_btn, "撤销上一步修改 (Ctrl+Z)")

        self._redo_btn = ttk.Button(btn_frame, text="重做", width=6,
                                     command=self._do_redo, state=tk.DISABLED)
        self._redo_btn.pack(side=tk.LEFT, padx=(0, 8))
        ToolTip(self._redo_btn, "重做上一步修改 (Ctrl+Y)")

        # #12 按钮改名
        self.save_button = ttk.Button(btn_frame, text="保存并打包到游戏", width=16,
                                       command=self._save, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(self.save_button, "将修改写入文件并打包，使修改在游戏中生效")

        self.open_skill_button = ttk.Button(btn_frame, text="打开技能文件", width=14,
                                             command=self._open_skill_file, state=tk.DISABLED)
        self.open_skill_button.pack(side=tk.LEFT)
        ToolTip(self.open_skill_button, "用外部编辑器打开当前英雄的技能文件")

        # #15 还原此英雄
        self.reset_button = ttk.Button(btn_frame, text="还原此英雄", width=14,
                                        command=self._reset_to_original, state=tk.DISABLED)
        self.reset_button.pack(side=tk.RIGHT)
        ToolTip(self.reset_button, "从VPK重新提取原始数据，撤销当前英雄的所有修改")

        # ---- 状态栏 ----
        status_frame = ttk.Frame(right_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        self._status_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self._status_var,
                  font=("", 8), foreground="gray").pack(side=tk.LEFT)

        # ---- 修改日志（可折叠）----
        log_toggle_frame = ttk.Frame(right_frame)
        log_toggle_frame.pack(fill=tk.X, pady=(3, 0))
        self._log_visible = False
        self._log_toggle_btn = ttk.Button(log_toggle_frame, text="▶ 修改日志",
                                           command=self._toggle_log, width=12)
        self._log_toggle_btn.pack(side=tk.LEFT)

        self._log_frame = ttk.Frame(right_frame)
        # 默认隐藏

        self._log_text = tk.Text(self._log_frame, height=5, font=("Consolas", 8),
                                  state=tk.DISABLED, wrap=tk.WORD, bg="#F5F5F5")
        log_scroll = ttk.Scrollbar(self._log_frame, orient=tk.VERTICAL,
                                    command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._log_entries = []  # 日志条目列表

    def _populate_hero_list(self, filter_text=""):
        """填充英雄列表，支持过滤"""
        self.hero_listbox.delete(0, tk.END)
        self.filtered_keys = []
        filter_lower = filter_text.lower()

        for key in self.hero_keys:
            en_name = key.replace("npc_dota_hero_", "")
            cn_name = EN_TO_CN.get(en_name, "")

            if filter_lower:
                if filter_lower not in cn_name and filter_lower not in en_name:
                    continue

            display_name = cn_name if cn_name else en_name
            self.hero_listbox.insert(tk.END, display_name)
            self.filtered_keys.append(key)

    def _on_search(self, *args):
        """搜索框输入时过滤列表"""
        if not self._search_placeholder:
            self._populate_hero_list(self.search_var.get())

    def _clear_search(self):
        """清空搜索"""
        self.search_var.set("")
        self._search_placeholder = False
        self._search_entry.configure(foreground="black")

    def _show_search_placeholder(self):
        """显示搜索框占位文字"""
        self._search_placeholder = True
        self.search_var.set("搜索英雄名...")
        self._search_entry.configure(foreground="gray")

    def _on_search_focus_in(self, event):
        """搜索框获得焦点时清除占位文字"""
        if self._search_placeholder:
            self._search_placeholder = False
            self.search_var.set("")
            self._search_entry.configure(foreground="black")

    def _on_search_focus_out(self, event):
        """搜索框失去焦点时恢复占位文字"""
        if not self.search_var.get().strip():
            self._show_search_placeholder()

    def _on_hero_select(self, event):
        """选择英雄时加载属性和技能"""
        selection = self.hero_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        item_key = self.filtered_keys[idx]

        # #1: 切换英雄时若有修改，提示已自动保存
        if self.current_hero_key and self._has_any_unsaved_changes():
            self._set_status("✓ 修改已自动保存到文件（修改需打包后才在游戏中生效）", 5000)

        self.current_hero_key = item_key
        self._load_hero_data(item_key)
        self.save_button.configure(state=tk.NORMAL)
        self.open_skill_button.configure(state=tk.NORMAL)
        self.reset_button.configure(state=tk.NORMAL)
        self._undo_btn.configure(state=tk.NORMAL)
        self._redo_btn.configure(state=tk.NORMAL)

    def _load_hero_data(self, hero_key: str):
        """加载指定英雄的属性和技能"""
        assert self.heroes_data is not None
        dota_heroes = self.heroes_data.get("DOTAHeroes", {})
        hero_data = dota_heroes.get(hero_key, {})

        # 更新标题
        en_name = hero_key.replace("npc_dota_hero_", "")
        cn_name = EN_TO_CN.get(en_name, "")
        title = f"{cn_name} ({en_name})" if cn_name else en_name
        self.hero_title_label.configure(text=title)

        # 获取备份数据中的原始英雄数据（用于变黄对比）
        original_hero_data = None
        if self._backup_heroes_data is not None:
            backup_heroes = self._backup_heroes_data.get("DOTAHeroes", {})
            original_hero_data = backup_heroes.get(hero_key, {})

        # 加载属性（传入原始数据用于对比）
        self.attr_editor.load(hero_data, original_data=original_hero_data)

        # 加载技能
        self.skill_editor.load(hero_key, self.heroes_data)

    def _on_edit_change(self, message: str = ""):
        """编辑器内容变化时的回调 — 延迟500ms自动写入txt文件"""
        # 取消上一次的定时器
        if self._auto_save_timer_id is not None:
            self.win.after_cancel(self._auto_save_timer_id)
        # 保存消息供 _auto_save 使用
        if message:
            self._pending_status_message = message
        # 500ms 后执行自动写入
        self._auto_save_timer_id = self.win.after(500, self._auto_save)

    def _auto_save(self):
        """将属性+技能修改自动写入txt文件（不打包VPK）"""
        self._auto_save_timer_id = None
        status_msg = self._pending_status_message
        self._pending_status_message = ""
        if not self.current_hero_key:
            return

        # 校验
        attr_valid, attr_err = self.attr_editor.validate()
        if not attr_valid:
            self._set_status(f"自动保存失败：{attr_err}", 5000)
            return
        skill_valid, skill_err = self.skill_editor.validate()
        if not skill_valid:
            self._set_status(f"自动保存失败：{skill_err}", 5000)
            return

        # 写入属性到 npc_heroes.txt
        assert self.heroes_data is not None
        dota_heroes = self.heroes_data.get("DOTAHeroes", {})
        hero_data = dota_heroes.get(self.current_hero_key, {})
        self.attr_editor.apply_changes(hero_data)
        dota_heroes[self.current_hero_key] = hero_data

        npc_heroes_path = get_npc_heroes_path()
        try:
            with open(npc_heroes_path, "w", encoding="utf-8") as f:
                vdf.dump(self.heroes_data, f, pretty=True)
        except Exception as e:
            self._set_status(f"自动保存失败：{e}", 5000)
            return

        # 写入技能到技能文件
        skill_ok = self.skill_editor.save_changes_to_file()
        if not skill_ok:
            self._set_status("自动保存失败：技能文件写入失败", 5000)
            return

        self._set_status(status_msg or "✓ 已自动保存到文件（修改需打包后才在游戏中生效）", 5000)

        # 记录修改日志
        en_name = self.current_hero_key.replace("npc_dota_hero_", "")
        cn_name = EN_TO_CN.get(en_name, en_name)
        self._add_log(f"{cn_name}: 修改已自动保存到文件")

    def _has_any_unsaved_changes(self) -> bool:
        """检查是否有任何未保存的修改"""
        return self.attr_editor.has_changes() or self.skill_editor.has_changes()

    def _set_status(self, text: str, duration: int = 3000):
        """更新状态栏提示，duration 毫秒后自动清除（0=不清除）"""
        self._status_var.set(text)
        if duration > 0 and text:
            self.win.after(duration, lambda: self._status_var.set(""))

    def _on_undo(self, event):
        """Ctrl+Z 撤销"""
        self._do_undo()

    def _on_redo(self, event):
        """Ctrl+Y 重做"""
        self._do_redo()

    def _do_undo(self):
        """执行撤销操作"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            desc = self.attr_editor.undo()
        else:
            desc = self.skill_editor.undo()
        if desc:
            self._set_status(f"已撤销: {desc}")

    def _do_redo(self):
        """执行重做操作"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 0:
            desc = self.attr_editor.redo()
        else:
            desc = self.skill_editor.redo()
        if desc:
            self._set_status(f"已重做: {desc}")

    def _toggle_log(self):
        """切换修改日志显示"""
        self._log_visible = not self._log_visible
        if self._log_visible:
            self._log_frame.pack(fill=tk.X, pady=(2, 0))
            self._log_toggle_btn.configure(text="▼ 修改日志")
        else:
            self._log_frame.pack_forget()
            self._log_toggle_btn.configure(text="▶ 修改日志")

    def _add_log(self, message: str):
        """添加一条修改日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._log_entries.append(entry)
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, entry + "\n")
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

        # #27 首次添加日志时自动展开
        if len(self._log_entries) == 1 and not self._log_visible:
            self._log_visible = True
            self._log_frame.pack(fill=tk.X, pady=(2, 0))
            self._log_toggle_btn.configure(text="▼ 修改日志")

    def _on_close(self):
        """窗口关闭时，如果有未打包的修改则提示确认"""
        # 取消未执行的自动保存定时器
        if self._auto_save_timer_id is not None:
            self.win.after_cancel(self._auto_save_timer_id)
            self._auto_save_timer_id = None

        if self._has_any_unsaved_changes():
            if not messagebox.askyesno("确认关闭",
                                       "有修改尚未打包VPK，关闭后修改仍保留在文件中。\n\n"
                                       "如需在游戏中生效，请重新打开编辑器并点击「保存并打包到游戏」。\n\n"
                                       "确定要关闭吗？"):
                return
        self.win.destroy()

    def _reset_to_original(self):
        """恢复当前英雄的属性和技能文件到初始状态"""
        if not self.current_hero_key:
            return

        en_name = self.current_hero_key.replace("npc_dota_hero_", "")
        cn_name = EN_TO_CN.get(en_name, en_name)
        display = cn_name if cn_name != en_name else en_name

        if not messagebox.askyesno("确认恢复", f"确定要将 {display} 的属性和技能文件恢复到初始状态吗？"):
            return

        # 1. 恢复英雄属性：从备份文件重新加载该英雄的数据
        try:
            with open(self.heroes_backup_path, "r", encoding="utf-8") as f:
                backup_content = f.read()
            backup_content = unpack.preprocess_vdf_content(backup_content)
            backup_data = vdf.loads(backup_content)

            backup_heroes = backup_data.get("DOTAHeroes", {})
            backup_hero = backup_heroes.get(self.current_hero_key, {})
            assert self.heroes_data is not None
            current_heroes = self.heroes_data.get("DOTAHeroes", {})
            current_heroes[self.current_hero_key] = dict(backup_hero)
        except Exception as e:
            messagebox.showerror("还原失败",
                f"恢复英雄属性失败，请尝试在主界面重新解压文件。\n\n"
                f"详细信息：{e}")
            return

        # 2. 恢复技能文件：从 VPK 重新提取
        success, err_msg = self.skill_editor.restore_skill_file(self.current_hero_key)
        if not success:
            messagebox.showerror("错误", err_msg)
            return

        # 3. 刷新界面显示
        self._load_hero_data(self.current_hero_key)
        messagebox.showinfo("成功", f"{display} 已恢复到初始状态")
        self._add_log(f"{display}: 已还原到初始数据")

    def _reset_all(self):
        """重置所有英雄的修改：从备份恢复属性，从VPK恢复技能文件"""
        if not messagebox.askyesno("确认还原",
                                   "确定要还原全部英雄的修改吗？\n\n"
                                   "此操作将：\n"
                                   "• 从备份恢复 npc_heroes.txt\n"
                                   "• 从VPK重新提取所有技能文件\n\n"
                                   "此操作不可撤销！"):
            return

        # 1. 从备份恢复 npc_heroes.txt
        try:
            if os.path.exists(self.heroes_backup_path):
                npc_heroes_path = get_npc_heroes_path()
                shutil.copy2(self.heroes_backup_path, npc_heroes_path)
                # 重新加载
                with open(npc_heroes_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = unpack.preprocess_vdf_content(content)
                self.heroes_data = vdf.loads(content)
        except Exception as e:
            messagebox.showerror("还原失败",
                f"恢复属性文件失败，请尝试在主界面重新解压文件。\n\n"
                f"详细信息：{e}")
            return

        # 2. 从VPK批量恢复所有技能文件（只打开一次VPK）
        restored_count, errors = self.skill_editor.restore_all_skill_files(self.hero_keys)

        # 3. 刷新当前英雄
        if self.current_hero_key:
            self._load_hero_data(self.current_hero_key)

        self._add_log(f"已重置所有修改：属性+{restored_count}个技能文件已恢复")
        self._set_status(f"已重置所有修改（{restored_count}个技能文件已恢复）")
        messagebox.showinfo("成功", "所有英雄的修改已重置！")

    def _open_skill_file(self):
        """用外部编辑器打开英雄技能文件"""
        if not self.current_hero_key:
            return

        file_path = os.path.join(get_pak01_dir(), "scripts", "npc", "heroes",
                                  f"{self.current_hero_key}.txt")

        if not os.path.exists(file_path):
            messagebox.showwarning("提示", f"技能文件不存在:\n{file_path}")
            return

        editor = shutil.which("code") or "notepad"
        try:
            subprocess.Popen([editor, file_path])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开编辑器: {e}")

    def _save(self):
        """保存修改：属性 + 技能 → 写回文件 → 打包 VPK"""
        if not self.current_hero_key:
            return

        # 校验属性
        attr_valid, attr_err = self.attr_editor.validate()
        if not attr_valid:
            messagebox.showerror("输入错误", attr_err)
            return

        # 校验技能
        skill_valid, skill_err = self.skill_editor.validate()
        if not skill_valid:
            messagebox.showerror("输入错误", skill_err)
            return

        # 保存属性到 heroes_data
        assert self.heroes_data is not None
        dota_heroes = self.heroes_data.get("DOTAHeroes", {})
        hero_data = dota_heroes.get(self.current_hero_key, {})
        self.attr_editor.apply_changes(hero_data)
        dota_heroes[self.current_hero_key] = hero_data

        # 写回 npc_heroes.txt
        npc_heroes_path = get_npc_heroes_path()
        try:
            with open(npc_heroes_path, "w", encoding="utf-8") as f:
                vdf.dump(self.heroes_data, f, pretty=True)
        except Exception as e:
            messagebox.showerror("写入失败",
                f"写入文件失败，请确认文件未被其他程序占用。\n\n"
                f"详细信息：{e}")
            return

        # 保存技能到技能文件
        skill_success, skill_err = self.skill_editor.save_changes()
        if not skill_success:
            messagebox.showerror("错误", skill_err)
            return

        # 打包 VPK
        try:
            warning_str = unpack.pack_to_vpk(self.file_path)
            if warning_str:
                messagebox.showwarning("警告", warning_str)
                return
            unpack.add_local_modify_to_gi(self.file_path)
        except Exception as e:
            messagebox.showerror("打包失败",
                f"打包失败，常见原因：\n"
                f"1. 游戏正在运行（请先关闭游戏）\n"
                f"2. 需要管理员权限（请右键以管理员身份运行）\n"
                f"3. 文件被其他程序占用\n\n"
                f"详细信息：{e}")
            return

        # 重置修改标记
        self.attr_editor.reset_changes_flag()
        self.skill_editor.reset_changes_flag()

        # 刷新当前英雄数据（确保内存与文件一致）
        if self.current_hero_key:
            self._load_hero_data(self.current_hero_key)

        # 保存成功后提示启动游戏
        if messagebox.askyesno("成功", "修改已保存并打包成功！是否立即启动游戏？"):
            webbrowser.open("steam://run/570")

        # 记录日志
        en_name = self.current_hero_key.replace("npc_dota_hero_", "")
        cn_name = EN_TO_CN.get(en_name, en_name)
        self._add_log(f"{cn_name}: 修改已打包VPK并应用到游戏")

    def _open_batch_modify(self):
        """打开批量修改对话框"""
        if self.heroes_data is None:
            return

        dialog = tk.Toplevel(self.win)
        dialog.title("批量修改英雄属性")
        dialog.resizable(False, False)
        dialog.transient(self.win)
        dialog.grab_set()

        # 居中
        w, h = 450, 520
        x = self.win.winfo_x() + (self.win.winfo_width() - w) // 2
        y = self.win.winfo_y() + (self.win.winfo_height() - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

# 属性选择
        ttk.Label(dialog, text="选择属性：", font=("", 10)).pack(anchor=tk.W, padx=15, pady=(15, 5))

        attr_var = tk.StringVar()
        attr_combo = ttk.Combobox(dialog, textvariable=attr_var, state="readonly", width=30)
        # #16 只显示中文标签，key存入映射
        attr_labels = []
        attr_key_map = {}  # label → key
        for group_name, attrs in HERO_ATTRIBUTES.items():
            for key, label in attrs:
                attr_labels.append(label)
                attr_key_map[label] = key
        attr_combo["values"] = attr_labels
        if attr_labels:
            attr_combo.current(0)
        attr_combo.pack(padx=15, fill=tk.X)
        ToolTip(attr_combo, attr_key_map.get(attr_labels[0], "") if attr_labels else "")

        # 修改方式
        ttk.Label(dialog, text="修改方式：", font=("", 10)).pack(anchor=tk.W, padx=15, pady=(10, 5))

        mode_var = tk.StringVar(value="add")
        mode_frame = ttk.Frame(dialog)
        mode_frame.pack(padx=15, fill=tk.X)
        ttk.Radiobutton(mode_frame, text="加/减", variable=mode_var, value="add").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="乘/除", variable=mode_var, value="multiply").pack(side=tk.LEFT, padx=(15, 0))
        ttk.Radiobutton(mode_frame, text="设为固定值", variable=mode_var, value="set").pack(side=tk.LEFT, padx=(15, 0))

        # 数值输入
        ttk.Label(dialog, text="数值：", font=("", 10)).pack(anchor=tk.W, padx=15, pady=(10, 5))
        value_var = tk.StringVar(value="0")
        value_entry = ttk.Entry(dialog, textvariable=value_var, width=20)
        value_entry.pack(padx=15, fill=tk.X)

        # 提示
        ttk.Label(dialog, text="提示：加/减模式输入正负数，乘/除模式输入倍率（如0.5=减半，2=翻倍）",
                  font=("", 8), foreground="gray", wraplength=400).pack(padx=15, pady=(5, 0), anchor=tk.W)

        # 英雄选择（checkbox 列表）
        ttk.Label(dialog, text="选择英雄：", font=("", 10)).pack(anchor=tk.W, padx=15, pady=(10, 2))

        hero_select_frame = ttk.Frame(dialog)
        hero_select_frame.pack(padx=15, fill=tk.BOTH, expand=True)

        # 搜索过滤框
        search_var = tk.StringVar()
        search_row = ttk.Frame(hero_select_frame)
        search_row.pack(fill=tk.X, pady=(0, 3))
        search_entry = ttk.Entry(search_row, textvariable=search_var, width=20)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(search_row, text="×", width=3,
                   command=lambda: search_var.set("")).pack(side=tk.LEFT, padx=(3, 0))

        # 全选/反选按钮
        select_btn_frame = ttk.Frame(hero_select_frame)
        select_btn_frame.pack(fill=tk.X, pady=(0, 3))

        hero_check_vars = {}  # hero_key → BooleanVar
        hero_check_widgets = {}  # hero_key → (checkbutton_widget, display_name, en_name)

        def update_selected_count():
            selected_count_var.set(f"已选 {sum(1 for v in hero_check_vars.values() if v.get())} 个")

        def select_all():
            for hero_key, (cb_w, _, _) in hero_check_widgets.items():
                if str(cb_w.winfo_manager()) != "forget":  # 只选可见的
                    hero_check_vars[hero_key].set(True)
            update_selected_count()

        def deselect_all():
            for hero_key, (cb_w, _, _) in hero_check_widgets.items():
                if str(cb_w.winfo_manager()) != "forget":
                    hero_check_vars[hero_key].set(False)
            update_selected_count()

        def invert_selection():
            for hero_key, (cb_w, _, _) in hero_check_widgets.items():
                if str(cb_w.winfo_manager()) != "forget":
                    hero_check_vars[hero_key].set(not hero_check_vars[hero_key].get())
            update_selected_count()

        ttk.Button(select_btn_frame, text="全选", width=6, command=select_all).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(select_btn_frame, text="全不选", width=6, command=deselect_all).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(select_btn_frame, text="反选", width=6, command=invert_selection).pack(side=tk.LEFT)

        selected_count_var = tk.StringVar(value="已选 0 个")
        ttk.Label(select_btn_frame, textvariable=selected_count_var,
                  font=("", 8), foreground="gray").pack(side=tk.RIGHT)

        # 可滚动的 checkbox 列表
        list_canvas = tk.Canvas(hero_select_frame, highlightthickness=0, height=180)
        list_scrollbar = ttk.Scrollbar(hero_select_frame, orient=tk.VERTICAL, command=list_canvas.yview)
        checkbox_frame = ttk.Frame(list_canvas)

        checkbox_frame.bind("<Configure>",
                            lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.create_window((0, 0), window=checkbox_frame, anchor=tk.NW)
        list_canvas.configure(yscrollcommand=list_scrollbar.set)

        list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 鼠标滚轮支持
        def _on_mousewheel(event):
            list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        list_canvas.bind("<Enter>", lambda e: list_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        list_canvas.bind("<Leave>", lambda e: list_canvas.unbind_all("<MouseWheel>"))

        # 填充 checkbox
        for hero_key in self.hero_keys:
            en_name = hero_key.replace("npc_dota_hero_", "")
            cn_name = EN_TO_CN.get(en_name, "")
            display = cn_name if cn_name else en_name
            var = tk.BooleanVar(value=True)
            hero_check_vars[hero_key] = var
            cb = ttk.Checkbutton(checkbox_frame, text=display, variable=var,
                                 command=update_selected_count)
            cb.pack(anchor=tk.W, padx=5, pady=1)
            hero_check_widgets[hero_key] = (cb, display, en_name)

        selected_count_var.set(f"已选 {len(self.hero_keys)} 个")

        # 搜索过滤逻辑
        def _on_filter_heroes(*args):
            filter_text = search_var.get().strip().lower()
            for hero_key, (cb_w, display, en_name) in hero_check_widgets.items():
                if not filter_text:
                    cb_w.pack(anchor=tk.W, padx=5, pady=1)
                elif filter_text in display.lower() or filter_text in en_name.lower():
                    cb_w.pack(anchor=tk.W, padx=5, pady=1)
                else:
                    cb_w.pack_forget()
            # 更新滚动区域
            list_canvas.configure(scrollregion=list_canvas.bbox("all"))
            update_selected_count()

        search_var.trace_add("write", _on_filter_heroes)

        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(10, 10))

        def do_batch():
            mode_text = {"add": "加/减", "multiply": "乘/除", "set": "设为"}[mode_var.get()]
            try:
                modify_value = float(value_var.get().strip())
            except ValueError:
                messagebox.showerror("错误", "请输入有效数字", parent=dialog)
                return

            # #16 从映射获取属性 key
            selected_label = attr_var.get()
            attr_key = attr_key_map.get(selected_label, "")
            if not attr_key:
                messagebox.showwarning("提示", "请选择一个属性", parent=dialog)
                return

            # 确定范围：从 checkbox 获取选中的英雄
            target_keys = [k for k, v in hero_check_vars.items() if v.get()]

            if not target_keys:
                messagebox.showwarning("提示", "请至少选择一个英雄", parent=dialog)
                return

            # #20 批量修改预览：计算改前→改后值，显示预览对话框
            preview_data = []
            dota_heroes_preview = self.heroes_data.get("DOTAHeroes", {})
            for hero_key in target_keys[:20]:  # 最多预览20个
                hero_data = dota_heroes_preview.get(hero_key, {})
                if not isinstance(hero_data, dict):
                    continue
                current_val = hero_data.get(attr_key, BASE_DEFAULTS.get(attr_key, "0"))
                try:
                    current = float(current_val)
                except (ValueError, TypeError):
                    continue

                if mode_var.get() == "add":
                    new_val = current + modify_value
                elif mode_var.get() == "multiply":
                    new_val = current * modify_value
                else:  # set
                    new_val = modify_value

                if new_val == int(new_val):
                    new_str = str(int(new_val))
                else:
                    new_str = f"{new_val:.6f}".rstrip("0").rstrip(".")

                en_name = hero_key.replace("npc_dota_hero_", "")
                cn_name = EN_TO_CN.get(en_name, en_name)
                preview_data.append((cn_name, str(current_val), new_str))

            # 显示预览对话框
            preview_dialog = tk.Toplevel(dialog)
            preview_dialog.title("批量修改预览")
            preview_dialog.resizable(False, False)
            preview_dialog.transient(dialog)
            preview_dialog.grab_set()
            pw, ph = 400, 350
            px = dialog.winfo_x() + (dialog.winfo_width() - pw) // 2
            py = dialog.winfo_y() + (dialog.winfo_height() - ph) // 2
            preview_dialog.geometry(f"{pw}x{ph}+{px}+{py}")

            ttk.Label(preview_dialog, text=f"将对 {len(target_keys)} 个英雄的「{selected_label}」执行{mode_text}操作",
                       font=("", 10)).pack(padx=10, pady=(10, 5))

            # Treeview 显示预览
            tree_frame = ttk.Frame(preview_dialog)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            tree = ttk.Treeview(tree_frame, columns=("hero", "before", "after"),
                                show="headings", height=10)
            tree.heading("hero", text="英雄")
            tree.heading("before", text="当前值")
            tree.heading("after", text="修改后")
            tree.column("hero", width=120)
            tree.column("before", width=80)
            tree.column("after", width=80)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview).pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=tree_frame.winfo_children()[-1].set)

            for cn_name, before, after in preview_data:
                tree.insert("", tk.END, values=(cn_name, before, after))

            if len(target_keys) > 20:
                ttk.Label(preview_dialog, text=f"（仅显示前20个，共{len(target_keys)}个英雄）",
                           font=("", 8), foreground="gray").pack()

            confirm_result = [False]
            def on_confirm():
                confirm_result[0] = True
                preview_dialog.destroy()
            def on_cancel():
                preview_dialog.destroy()

            btn_frame2 = ttk.Frame(preview_dialog)
            btn_frame2.pack(pady=(5, 10))
            ttk.Button(btn_frame2, text="确认执行", command=on_confirm).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame2, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)

            preview_dialog.wait_window()
            if not confirm_result[0]:
                return

            # 执行批量修改
            dota_heroes = self.heroes_data.get("DOTAHeroes", {})
            modified_count = 0
            for hero_key in target_keys:
                hero_data = dota_heroes.get(hero_key, {})
                if not isinstance(hero_data, dict):
                    continue
                current_val = hero_data.get(attr_key, BASE_DEFAULTS.get(attr_key, "0"))
                try:
                    current = float(current_val)
                except (ValueError, TypeError):
                    continue

                if mode_var.get() == "add":
                    new_val = current + modify_value
                elif mode_var.get() == "multiply":
                    new_val = current * modify_value
                else:  # set
                    new_val = modify_value

                # 保留合理精度
                if new_val == int(new_val):
                    hero_data[attr_key] = str(int(new_val))
                else:
                    hero_data[attr_key] = f"{new_val:.6f}".rstrip("0").rstrip(".")
                modified_count += 1

            # 写入文件
            npc_heroes_path = get_npc_heroes_path()
            try:
                with open(npc_heroes_path, "w", encoding="utf-8") as f:
                    vdf.dump(self.heroes_data, f, pretty=True)
            except Exception as e:
                messagebox.showerror("错误", f"写入文件失败：{e}", parent=dialog)
                return

            # 刷新当前英雄
            if self.current_hero_key:
                self._load_hero_data(self.current_hero_key)

            dialog.destroy()
            val_str = value_var.get().strip()
            self._add_log(f"批量修改：{modified_count} 个英雄的 \"{selected_label}\" {mode_text}{val_str}（已写入文件，尚未打包VPK）")
            self._set_status(f"批量修改完成：{modified_count} 个英雄已修改（已写入文件，尚未打包VPK）")

        ttk.Button(btn_frame, text="执行修改", command=do_batch).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
