import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
import os
import json
import threading
import unpack
import hero_editor


VERSION = "1.2.0"

# 配置文件路径（基于应用程序目录）
APP_DIR = unpack.get_app_dir()
CONFIG_FILE_PATH = os.path.join(APP_DIR, "dota2_modify_config.json")
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


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Dota2 本地修改工具 v{VERSION}")
        self.root.resizable(False, False)

        self.file_path: str = ""
        self.text_tips_widget: ttk.Label
        self.path_label: ttk.Label
        self.status_var: tk.StringVar
        self.guide_label: ttk.Label
        self.extract_file_button: ttk.Button
        self.open_unpack_dir_button: ttk.Button
        self.package_file_button: ttk.Button
        self.unpackage_file_button: ttk.Button
        self.edit_hero_button: ttk.Button
        self.start_game_button: ttk.Button
        self._busy: bool = False

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
        self.style.configure("Status.TLabel", font=("", 9), foreground="gray")

    def _setup_window(self):
        window_width = 500
        window_height = 420
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 设置窗口图标
        icon_path = os.path.join(APP_DIR, "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

    def _create_widgets(self):
        # ---- 顶部状态提示 ----
        self.text_tips_widget = ttk.Label(self.root, text="", font=("", 10))
        self.text_tips_widget.pack(pady=(15, 5))

        # ---- 文件路径显示 ----
        self.path_label = ttk.Label(self.root, text="", font=("", 8), foreground="gray")
        self.path_label.pack(pady=(0, 5))

        # ---- 操作引导提示（步骤标签）----
        self.guide_frame = ttk.Frame(self.root)
        self.guide_frame.pack(pady=(0, 5))
        self._step_labels = []
        steps = ["① 选择文件", "② 解压文件", "③ 修改配置", "④ 打包文件", "⑤ 启动游戏"]
        for i, step_text in enumerate(steps):
            lbl = ttk.Label(self.guide_frame, text=step_text, font=("", 9), foreground="#999999")
            lbl.pack(side=tk.LEFT, padx=4)
            self._step_labels.append(lbl)
            if i < len(steps) - 1:
                ttk.Label(self.guide_frame, text="→", font=("", 9),
                          foreground="#CCCCCC").pack(side=tk.LEFT, padx=2)

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

        # ---- 修改英雄 ----
        self.edit_hero_button = ttk.Button(self.root, text="修改英雄", style="Action.TButton",
                                            command=self._open_hero_editor)
        self.edit_hero_button.pack(pady=8)

        # ---- 启动游戏 ----
        self.start_game_button = ttk.Button(self.root, text="启动游戏", style="Action.TButton",
                                            command=self._start_game)
        self.start_game_button.pack(pady=8)

        # ---- 底部状态栏 ----
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 5))
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var,
                  style="Status.TLabel").pack(side=tk.LEFT)

    def _set_status(self, text: str):
        """更新状态栏"""
        if self.status_var:
            self.status_var.set(text)

    def _update_step_indicator(self, is_unpacked: bool, is_modified: bool):
        """根据当前状态更新步骤标签颜色"""
        # 步骤状态：0=选择文件 1=解压 2=修改 3=打包 4=启动
        colors = ["#999999"] * 5  # 默认灰色
        if self.file_path:
            colors[0] = "#4CAF50"  # 绿色=已完成
            if is_unpacked:
                colors[1] = "#4CAF50"
                colors[2] = "#2196F3"  # 蓝色=可操作
                if is_modified:
                    colors[2] = "#4CAF50"
                    colors[3] = "#4CAF50"
                    colors[4] = "#2196F3"
                else:
                    colors[3] = "#2196F3"
            else:
                colors[1] = "#2196F3"
        else:
            colors[0] = "#2196F3"  # 蓝色=当前步骤

        for i, lbl in enumerate(self._step_labels):
            lbl.configure(foreground=colors[i])

    def _set_busy(self, busy: bool):
        """设置忙碌状态，禁用/启用所有操作按钮"""
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for btn in [self.extract_file_button, self.open_unpack_dir_button,
                    self.package_file_button, self.unpackage_file_button,
                    self.edit_hero_button, self.start_game_button]:
            btn.configure(state=state)
        # 忙碌时也禁用选择文件按钮
        if busy:
            for child in self.root.winfo_children():
                if isinstance(child, ttk.LabelFrame) and child.cget("text") == "文件操作":
                    for btn in child.winfo_children():
                        if isinstance(btn, ttk.Button) and btn.cget("text") == "选择文件":
                            btn.configure(state=state)

    def run(self):
        self.root.mainloop()

    def _select_file(self):
        select_file_path = filedialog.askopenfilename(
            title="选择 dota2.exe 文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if select_file_path:
            if not select_file_path.lower().endswith("dota2.exe"):
                messagebox.showerror("文件选择错误", "请选择 Dota2 安装目录下的 dota2.exe 文件！\n\n"
                                     "通常位于：Steam\\steamapps\\common\\dota 2 beta\\game\\bin\\win64\\dota2.exe")
                return
            self.file_path = select_file_path
            self._save_config()
            self._update_view()
            self._set_status("已选择 dota2.exe 路径")

    def _update_view(self):
        is_unpacked = unpack.is_unpacked()
        is_modified = unpack.is_modified(self.file_path) if self.file_path else False

        # 更新步骤标签颜色
        self._update_step_indicator(is_unpacked, is_modified)

        if self.file_path:
            # 根据解压和修改状态显示不同提示
            if is_modified:
                self.text_tips_widget.configure(
                    foreground="blue",
                    text="✓ 已应用本地修改（打包状态）"
                )
            elif is_unpacked:
                self.text_tips_widget.configure(
                    foreground="green",
                    text="✓ 已解压（修改后请打包）"
                )
            else:
                self.text_tips_widget.configure(
                    foreground="green",
                    text="✓ 当前已获取文件路径"
                )
            self.path_label.configure(text=self.file_path)

            # 基本按钮：有路径就可用
            self.extract_file_button.configure(state=tk.NORMAL)
            self.start_game_button.configure(state=tk.NORMAL)
            self.unpackage_file_button.configure(state=tk.NORMAL)

            # 依赖解压的按钮
            unpack_state = tk.NORMAL if is_unpacked else tk.DISABLED
            self.open_unpack_dir_button.configure(state=unpack_state)
            self.package_file_button.configure(state=unpack_state)
            self.edit_hero_button.configure(state=unpack_state)
        else:
            self.text_tips_widget.configure(foreground="red", text="✗ 请选择 dota2.exe 文件")
            self.path_label.configure(text="")
            self.extract_file_button.configure(state=tk.DISABLED)
            self.start_game_button.configure(state=tk.DISABLED)
            self.open_unpack_dir_button.configure(state=tk.DISABLED)
            self.package_file_button.configure(state=tk.DISABLED)
            self.unpackage_file_button.configure(state=tk.DISABLED)
            self.edit_hero_button.configure(state=tk.DISABLED)

    @staticmethod
    def _read_config() -> dict[str, str]:
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    result: dict[str, str] = json.load(f)
                    return result
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_config(self):
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump({KEY_FILE_PATH: self.file_path}, f)
        except IOError as e:
            self._set_status(f"保存配置失败: {e}")

    @staticmethod
    def _auto_find_dota2() -> str:
        """自动查找 dota2.exe：先解析 Steam 库文件，再搜索常见路径"""
        # 1. 尝试从 Steam 库文件解析
        steam_install_path = _find_steam_install_path()
        if steam_install_path:
            library_path = os.path.join(steam_install_path, "steamapps", "libraryfolders.vdf")
            dota2_path = _search_steam_libraries(library_path)
            if dota2_path:
                return dota2_path
            # 也检查默认路径
            default_path = os.path.join(
                steam_install_path, "steamapps", "common",
                "dota 2 beta", "game", "bin", "win64", "dota2.exe"
            )
            if os.path.isfile(default_path):
                return default_path

        # 2. 搜索常见路径
        for drive in "CDEFG":
            for template in STEAM_CANDIDATE_DIRS:
                candidate = template.format(drive=drive)
                exe_path = os.path.join(candidate, "dota2.exe")
                if os.path.isfile(exe_path):
                    return exe_path
        return ""

    def _unpack_file(self):
        """解压 VPK 文件（在子线程中执行，避免界面卡死）"""
        if self._busy:
            return

        # 检查是否已解压，提示覆盖风险
        if unpack.is_unpacked():
            if not messagebox.askyesno(
                "确认解压",
                "已存在解压文件，重新解压会覆盖之前的修改！\n\n是否继续？"
            ):
                return

        self._set_busy(True)
        self._set_status("正在解压文件，请稍候...")

        def do_unpack():
            try:
                # 先检查 VPK 文件是否存在
                parent = unpack.get_game_root_dir(self.file_path)
                vpk_file_path = os.path.join(parent, "dota", "pak01_dir.vpk")
                if not os.path.isfile(vpk_file_path):
                    self.root.after(0, lambda: self._on_unpack_error(
                        FileNotFoundError(f"找不到 VPK 文件:\n{vpk_file_path}\n\n请确认 dota2.exe 路径是否正确。")
                    ))
                    return

                def progress_callback(current: int, total: int, filename: str):
                    if total > 0:
                        pct = int(current / total * 100)
                        self.root.after(0, lambda p=pct: self._set_status(f"正在解压... {p}%"))

                unpack.unpack_from_vpk(self.file_path, progress_callback=progress_callback)
                self.root.after(0, self._on_unpack_success)
            except Exception as e:
                self.root.after(0, lambda: self._on_unpack_error(e))

        thread = threading.Thread(target=do_unpack, daemon=True)
        thread.start()

    def _on_unpack_success(self):
        self._set_busy(False)
        self._set_status("解压完成")
        self._update_view()
        messagebox.showinfo("解压完成", "文件解压成功！\n\n"
                            "你可以：\n"
                            "• 点击「打开解包目录」查看和编辑配置文件\n"
                            "• 点击「修改英雄」使用英雄属性编辑器\n"
                            "• 修改完成后点击「打包文件」应用修改")

    def _on_unpack_error(self, error: Exception):
        self._set_busy(False)
        self._set_status("解压失败")
        if isinstance(error, FileNotFoundError):
            messagebox.showerror("解压失败", str(error))
        elif isinstance(error, PermissionError):
            messagebox.showerror("解压失败",
                                 f"权限不足，无法访问文件。\n\n"
                                 f"请尝试以管理员身份运行本程序。\n\n"
                                 f"详细信息: {error}")
        else:
            messagebox.showerror("解压失败",
                                 f"解压过程中发生错误:\n{error}\n\n"
                                 f"请确认 dota2.exe 路径正确，且游戏未在运行。")

    def _package_file(self):
        if self._busy:
            return

        # 检测游戏是否运行
        if unpack.is_dota2_running():
            messagebox.showwarning("无法打包",
                                   "检测到 Dota2 正在运行！\n\n"
                                   "请先关闭游戏再进行打包操作。")
            return

        if not unpack.is_unpacked():
            messagebox.showwarning("无法打包", "请先解压文件后再打包！")
            return

        if not messagebox.askyesno(
            "确认打包",
            "确定要打包文件吗？\n\n"
            "此操作会将修改后的配置文件部署到游戏目录，修改将在游戏中生效。\n"
            "（仅对本地主机房间有效）"
        ):
            return

        self._set_busy(True)
        self._set_status("正在打包文件，请稍候...")

        def do_pack():
            try:
                warning_str = unpack.pack_to_vpk(self.file_path)
                if warning_str:
                    self.root.after(0, lambda: self._on_pack_warning(warning_str))
                else:
                    unpack.add_local_modify_to_gi(self.file_path)
                    self.root.after(0, self._on_pack_success)
            except PermissionError as e:
                self.root.after(0, lambda: self._on_pack_error(
                    PermissionError(f"权限不足，无法写入游戏文件。\n\n"
                                    f"请确保游戏未运行，且以管理员身份运行本程序。\n\n"
                                    f"详细信息: {e}")
                ))
            except Exception as e:
                self.root.after(0, lambda: self._on_pack_error(e))

        thread = threading.Thread(target=do_pack, daemon=True)
        thread.start()

    def _on_pack_success(self):
        self._set_busy(False)
        self._set_status("打包完成")
        self._update_view()
        if messagebox.askyesno("打包完成",
                               "文件打包成功！修改已部署到游戏目录。\n\n"
                               "是否立即启动游戏？\n"
                               "（请记得在游戏中选择「本地主机」房间）"):
            self._start_game()

    def _on_pack_warning(self, warning_str: str):
        self._set_busy(False)
        self._set_status("打包警告")
        messagebox.showwarning("打包警告", warning_str)

    def _on_pack_error(self, error: Exception):
        self._set_busy(False)
        self._set_status("打包失败")
        messagebox.showerror("打包失败", str(error))

    def _unpackage_file(self):
        if self._busy:
            return

        if not messagebox.askyesno(
            "确认还原",
            "确定要还原文件吗？\n\n"
            "此操作会撤销所有本地修改，恢复游戏原始配置。\n"
            "（解压的文件不会被删除，只是游戏不再加载修改）"
        ):
            return

        try:
            unpack.remove_local_modify_from_gi(self.file_path)
            self._set_status("还原完成")
            self._update_view()
            messagebox.showinfo("还原完成", "已成功还原游戏原始文件！\n\n所有本地修改已撤销。")
        except PermissionError as e:
            messagebox.showerror("还原失败",
                                 f"权限不足，无法修改游戏配置文件。\n\n"
                                 f"请确保游戏未运行，且以管理员身份运行本程序。\n\n"
                                 f"详细信息: {e}")
        except Exception as e:
            messagebox.showerror("还原失败",
                                 f"还原过程中发生错误:\n{e}\n\n"
                                 f"请确保游戏未运行，且 dota2.exe 路径正确。")

    def _open_unpack_dir(self):
        unpack_dir_path = os.path.join(APP_DIR, "pak01_dir")
        if not os.path.isdir(unpack_dir_path):
            messagebox.showwarning("目录不存在",
                                   "解包目录不存在。\n\n请先点击「解压文件」进行解压。")
        else:
            os.startfile(unpack_dir_path)
            self._set_status("已打开解包目录")

    def _start_game(self):
        try:
            webbrowser.open("steam://run/570")
            self._set_status("正在启动 Dota2...")
        except Exception as e:
            messagebox.showerror("启动失败", f"无法启动游戏:\n{e}\n\n你也可以手动在 Steam 中启动 Dota2。")

    def _open_hero_editor(self):
        if not self.file_path:
            messagebox.showwarning("提示", "请先选择 dota2.exe 文件路径！")
            return
        if not unpack.is_unpacked():
            if not messagebox.askyesno(
                "提示",
                "尚未解压文件，英雄编辑器需要先解压游戏数据。\n\n是否现在解压？"
            ):
                return
            # 先解压
            self._unpack_file()
            return
        hero_editor.HeroEditorWindow(self.root, self.file_path)


def _find_steam_install_path() -> str:
    """查找 Steam 安装路径（从注册表或常见路径）"""
    # 尝试从注册表读取
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\WOW6432Node\Valve\Steam")
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        if path and os.path.isdir(path):
            return path
    except (OSError, ImportError):
        pass

    # 尝试常见路径
    for drive in "CDEFG":
        for candidate in [
            f"{drive}:\\Program Files (x86)\\Steam",
            f"{drive}:\\Program Files\\Steam",
            f"{drive}:\\Steam",
        ]:
            if os.path.isdir(candidate):
                return candidate
    return ""


def _search_steam_libraries(library_vdf_path: str) -> str:
    """解析 Steam libraryfolders.vdf 查找 dota2.exe"""
    if not os.path.isfile(library_vdf_path):
        return ""

    try:
        import vdf as vdf_lib
        with open(library_vdf_path, "r", encoding="utf-8") as f:
            lib_data = vdf_lib.load(f)

        paths = lib_data.get("libraryfolders", {})
        for lib_info in paths.values():
            if isinstance(lib_info, dict):
                lib_path = lib_info.get("path", "")
                if lib_path:
                    dota2_exe = os.path.join(
                        lib_path, "steamapps", "common",
                        "dota 2 beta", "game", "bin", "win64", "dota2.exe"
                    )
                    if os.path.isfile(dota2_exe):
                        return dota2_exe
    except Exception:
        pass

    return ""


if __name__ == "__main__":
    App().run()
