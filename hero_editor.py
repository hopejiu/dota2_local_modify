"""英雄编辑器主窗口 — 协调属性编辑和技能编辑"""

import os
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import vdf

from hero_constants import EN_TO_CN, get_pak01_dir, get_npc_heroes_path
from attribute_editor import AttributeEditor
from skill_editor import SkillEditor
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

        self._create_window()
        self._load_data()
        self._backup_heroes_file()
        self._build_ui()

        # 窗口关闭确认
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_window(self):
        self.win = tk.Toplevel(self.parent)
        self.win.title("英雄属性编辑")
        self.win.resizable(False, False)

        # 窗口大小和居中（加宽以容纳技能编辑区）
        w, h = 1050, 700
        sx = (self.win.winfo_screenwidth() - w) // 2
        sy = (self.win.winfo_screenheight() - h) // 2
        self.win.geometry(f"{w}x{h}+{sx}+{sy}")

        # 图标
        icon_path = os.path.join(unpack.get_app_dir(), "icon.ico")
        if os.path.exists(icon_path):
            self.win.iconbitmap(icon_path)

    def _backup_heroes_file(self):
        """备份 npc_heroes.txt（仅首次）"""
        npc_heroes_path = get_npc_heroes_path()
        self.heroes_backup_path = npc_heroes_path + ".bak"
        if os.path.exists(npc_heroes_path) and not os.path.exists(self.heroes_backup_path):
            shutil.copy2(npc_heroes_path, self.heroes_backup_path)

    def _load_data(self):
        """自动解压（如需要）并加载英雄数据"""
        pak01_dir = get_pak01_dir()
        npc_heroes_path = get_npc_heroes_path()

        # 检查是否需要解压
        if not os.path.exists(pak01_dir):
            try:
                unpack.unpack_from_vpk(self.file_path)
            except Exception as e:
                messagebox.showerror("错误", f"自动解压失败：{e}\n\n请确认 dota2.exe 路径正确，且游戏未在运行。")
                self.win.destroy()
                return

        # 检查 npc_heroes.txt 是否存在
        if not os.path.exists(npc_heroes_path):
            messagebox.showerror("错误", "找不到英雄数据文件。\n\n请先在主界面点击「解压文件」。")
            self.win.destroy()
            return

        # 加载 VDF 数据
        try:
            with open(npc_heroes_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = unpack.preprocess_vdf_content(content)
            self.heroes_data = vdf.loads(content)
        except Exception as e:
            messagebox.showerror("错误", f"加载英雄数据失败：{e}\n\n请尝试在主界面重新解压文件。")
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

        # 搜索框
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
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

        self.save_button = ttk.Button(btn_frame, text="保存并打包", width=14,
                                       command=self._save, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=(0, 5))

        self.open_skill_button = ttk.Button(btn_frame, text="打开技能文件", width=14,
                                             command=self._open_skill_file, state=tk.DISABLED)
        self.open_skill_button.pack(side=tk.LEFT)

        self.reset_button = ttk.Button(btn_frame, text="恢复初始", width=14,
                                        command=self._reset_to_original, state=tk.DISABLED)
        self.reset_button.pack(side=tk.RIGHT)

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
        self._populate_hero_list(self.search_var.get())

    def _clear_search(self):
        """清空搜索"""
        self.search_var.set("")

    def _on_hero_select(self, event):
        """选择英雄时加载属性和技能"""
        selection = self.hero_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        item_key = self.filtered_keys[idx]

        self.current_hero_key = item_key
        self._load_hero_data(item_key)
        self.save_button.configure(state=tk.NORMAL)
        self.open_skill_button.configure(state=tk.NORMAL)
        self.reset_button.configure(state=tk.NORMAL)

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

        # 加载属性
        self.attr_editor.load(hero_data)

        # 加载技能
        self.skill_editor.load(hero_key, self.heroes_data)

    def _on_edit_change(self):
        """编辑器内容变化时的回调"""
        pass  # 目前仅用于修改标记，关闭时检查

    def _has_any_unsaved_changes(self) -> bool:
        """检查是否有任何未保存的修改"""
        return self.attr_editor.has_changes() or self.skill_editor.has_changes()

    def _on_close(self):
        """窗口关闭时，如果有未保存的修改则提示确认"""
        if self._has_any_unsaved_changes():
            if not messagebox.askyesno("确认关闭", "有未保存的修改，确定要关闭吗？\n未保存的修改将会丢失。"):
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
            messagebox.showerror("错误", f"恢复英雄属性失败：{e}\n\n请尝试在主界面重新解压文件。")
            return

        # 2. 恢复技能文件：从 VPK 重新提取
        success, err_msg = self.skill_editor.restore_skill_file(self.current_hero_key)
        if not success:
            messagebox.showerror("错误", err_msg)
            return

        # 3. 刷新界面显示
        self._load_hero_data(self.current_hero_key)
        messagebox.showinfo("成功", f"{display} 已恢复到初始状态")

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
            messagebox.showerror("错误", f"写入文件失败：{e}\n\n请确认文件未被其他程序占用。")
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
            messagebox.showerror("错误", f"打包失败：{e}\n\n请确认游戏未在运行，且以管理员身份运行本程序。")
            return

        # 重置修改标记
        self.attr_editor.reset_changes_flag()
        self.skill_editor.reset_changes_flag()

        # 保存成功后提示启动游戏
        if messagebox.askyesno("成功", "修改已保存并打包成功！是否立即启动游戏？"):
            webbrowser.open("steam://run/570")
