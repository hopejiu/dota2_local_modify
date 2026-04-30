import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
import os
import json
import data
import unpack


CONFIG_FILE_PATH = "./dota2_modify_config.json"
KEY_FILE_PATH = "file_path"

# 自动搜索 dota2.exe 的候选路径
STEAM_CANDIDATE_DIRS = [
    r"{drive}:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\bin\win64",
    r"{drive}:\Program Files\Steam\steamapps\common\dota 2 beta\game\bin\win64",
    r"{drive}:\SteamLibrary\steamapps\common\dota 2 beta\game\bin\win64",
    r"{drive}:\Steam\steamapps\common\dota 2 beta\game\bin\win64",
    r"{drive}:\Games\Steam\steamapps\common\dota 2 beta\game\bin\win64",
    r"{drive}:\Game\Steam\steamapps\common\dota 2 beta\game\bin\win64",
]

# 构建 英文名→中文名 反向映射，用于英文搜索
hero_map_en_to_cn = {v: k for k, v in data.hero_map.items()}


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dota2 本地修改工具")
        self.root.resizable(False, False)

        self.file_path = ""
        self.dropdown_widget = None
        self.value_text_widget = None
        self.text_tips_widget = None
        self.copy_button = None
        self.path_label = None

        self._setup_style()
        self._setup_window()
        self._create_widgets()

        config_dict = self._read_config()
        self.file_path = config_dict.get(KEY_FILE_PATH, "")
        # 配置中没有路径时，自动搜索
        if not self.file_path:
            self.file_path = self._auto_find_dota2()
            if self.file_path:
                self._save_config()
        self._update_view()

    def _setup_style(self):
        self.style = ttk.Style()
        # Windows 上 vista 主题效果最好
        available = self.style.theme_names()
        if "vista" in available:
            self.style.theme_use("vista")
        elif "clam" in available:
            self.style.theme_use("clam")

        # 统一按钮宽度
        self.style.configure("Action.TButton", width=18)
        self.style.configure("Small.TButton", width=5)

    def _setup_window(self):
        window_width = 480
        window_height = 520
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 设置窗口图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

    def _create_widgets(self):
        # ---- 顶部状态提示 ----
        self.text_tips_widget = ttk.Label(self.root, text="", font=("", 10))
        self.text_tips_widget.pack(pady=(15, 5))

        # ---- 文件路径显示 ----
        self.path_label = ttk.Label(self.root, text="", font=("", 8), foreground="gray")
        self.path_label.pack(pady=(0, 5))

        # ---- 文件操作区 ----
        file_frame = ttk.LabelFrame(self.root, text="文件操作", padding=10)
        file_frame.pack(padx=20, pady=5, fill=tk.X)

        ttk.Button(file_frame, text="选择文件", style="Action.TButton",
                   command=self._select_file).pack(pady=3)
        self.extract_file_button = ttk.Button(file_frame, text="解压文件", style="Action.TButton",
                                              command=self._unpack_file)
        self.extract_file_button.pack(pady=3)
        self.open_unpack_dir_button = ttk.Button(file_frame, text="打开解包目录", style="Action.TButton",
                                                 command=self._open_unpack_dir)
        self.open_unpack_dir_button.pack(pady=3)
        self.package_file_button = ttk.Button(file_frame, text="打包文件", style="Action.TButton",
                                              command=self._package_file)
        self.package_file_button.pack(pady=3)
        self.unpackage_file_button = ttk.Button(file_frame, text="还原文件", style="Action.TButton",
                                                command=self._unpackage_file)
        self.unpackage_file_button.pack(pady=3)

        # ---- 启动游戏 ----
        self.start_game_button = ttk.Button(self.root, text="启动游戏", style="Action.TButton",
                                            command=self._start_game)
        self.start_game_button.pack(pady=8)

        # ---- 分隔线 ----
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=5)

        # ---- 英雄查询区 ----
        hero_frame = ttk.LabelFrame(self.root, text="英雄查询", padding=10)
        hero_frame.pack(padx=20, pady=5, fill=tk.X)

        dropdown_row = ttk.Frame(hero_frame)
        dropdown_row.pack(fill=tk.X, pady=3)

        ttk.Label(dropdown_row, text="选择英雄:").pack(side=tk.LEFT, padx=(0, 5))

        self.dropdown_widget = ttk.Combobox(dropdown_row, values=list(data.hero_map.keys()), width=20)
        self.dropdown_widget.pack(side=tk.LEFT, padx=(0, 5))
        self.dropdown_widget.bind("<<ComboboxSelected>>", self._on_dropdown_select)
        self.dropdown_widget.bind("<KeyRelease>", self._on_dropdown_key_release)

        ttk.Button(dropdown_row, text="×", style="Small.TButton",
                   command=self._clear_dropdown_input).pack(side=tk.LEFT)

        value_row = ttk.Frame(hero_frame)
        value_row.pack(fill=tk.X, pady=3)

        self.value_text_widget = ttk.Entry(value_row, width=28, state="readonly")
        self.value_text_widget.pack(side=tk.LEFT, padx=(0, 5))

        self.copy_button = ttk.Button(value_row, text="复制", style="Small.TButton",
                                      command=self._copy_to_clipboard)
        self.copy_button.pack(side=tk.LEFT)

    def run(self):
        self.root.mainloop()

    def _select_file(self):
        select_file_path = filedialog.askopenfilename()
        if select_file_path:
            if not select_file_path.endswith("dota2.exe"):
                messagebox.showerror("错误", "请选择dota2.exe文件！")
                return
            self.file_path = select_file_path
            self._save_config()
            self._update_view()

    def _update_view(self):
        if self.file_path:
            self.text_tips_widget.configure(foreground="green", text="✓ 当前已获取文件路径")
            self.path_label.configure(text=self.file_path)
            self.extract_file_button.configure(state=tk.NORMAL)
            self.start_game_button.configure(state=tk.NORMAL)
            self.open_unpack_dir_button.configure(state=tk.NORMAL)
            self.package_file_button.configure(state=tk.NORMAL)
            self.unpackage_file_button.configure(state=tk.NORMAL)
        else:
            self.text_tips_widget.configure(foreground="red", text="✗ 请选择dota2.exe文件")
            self.path_label.configure(text="")
            self.extract_file_button.configure(state=tk.DISABLED)
            self.start_game_button.configure(state=tk.DISABLED)
            self.open_unpack_dir_button.configure(state=tk.DISABLED)
            self.package_file_button.configure(state=tk.DISABLED)
            self.unpackage_file_button.configure(state=tk.DISABLED)

    @staticmethod
    def _read_config() -> dict:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_config(self):
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({KEY_FILE_PATH: self.file_path}, f)

    @staticmethod
    def _auto_find_dota2() -> str:
        """在 C~E 盘常见 Steam 路径下自动查找 dota2.exe"""
        for drive in "CDEFG":
            for template in STEAM_CANDIDATE_DIRS:
                candidate = template.format(drive=drive)
                exe_path = os.path.join(candidate, "dota2.exe")
                if os.path.isfile(exe_path):
                    return exe_path
        return ""

    def _unpack_file(self):
        unpack.unpack_from_vpk(self.file_path)
        messagebox.showinfo("提示", "解压完成！")

    def _package_file(self):
        if not messagebox.askyesno("确认", "确定要打包文件吗？此操作会修改游戏文件。"):
            return
        warning_str = unpack.pack_to_vpk(self.file_path)
        if warning_str:
            messagebox.showwarning("警告", warning_str)
        else:
            unpack.add_local_modify_to_gi(self.file_path)
            messagebox.showinfo("提示", "打包完成,享受游戏吧！")

    def _unpackage_file(self):
        if not messagebox.askyesno("确认", "确定要还原文件吗？此操作会撤销所有本地修改。"):
            return
        unpack.remove_local_modify_from_gi(self.file_path)
        messagebox.showinfo("提示", "还原完成！")

    def _open_unpack_dir(self):
        unpack_dir_path = os.path.join(os.path.abspath("."), "pak01_dir")
        if not os.path.isdir(unpack_dir_path):
            messagebox.showwarning("警告", "路径不存在")
        else:
            os.startfile(unpack_dir_path)

    def _start_game(self):
        webbrowser.open("steam://run/570")

    def _on_dropdown_select(self, event):
        selected_key = self.dropdown_widget.get()
        if selected_key in data.hero_map:
            self.value_text_widget.configure(state=tk.NORMAL)
            self.value_text_widget.delete(0, tk.END)
            self.value_text_widget.insert(0, data.hero_map[selected_key])
            self.value_text_widget.configure(state="readonly")

    def _on_dropdown_key_release(self, event):
        input_text = self.dropdown_widget.get()
        if input_text:
            # 同时支持中文名和英文名搜索
            filtered_keys = [
                key for key in data.hero_map.keys()
                if input_text in key or input_text in data.hero_map[key]
            ]
            self.dropdown_widget["values"] = filtered_keys
        else:
            self.dropdown_widget["values"] = list(data.hero_map.keys())

    def _clear_dropdown_input(self):
        self.dropdown_widget.delete(0, tk.END)
        self.dropdown_widget["values"] = list(data.hero_map.keys())
        self.value_text_widget.configure(state=tk.NORMAL)
        self.value_text_widget.delete(0, tk.END)
        self.value_text_widget.configure(state="readonly")

    def _copy_to_clipboard(self):
        value = self.value_text_widget.get()
        if value:
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.copy_button.configure(text="已复制!")
            self.root.after(1500, lambda: self.copy_button.configure(text="复制"))


if __name__ == "__main__":
    App().run()
