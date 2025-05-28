import customtkinter as tk
from customtkinter import filedialog
from tkinter import messagebox

import unpack
from unpack import unpack_from_vpk
import math
import os
import json

file_path = ''
config_file_path = './dota2_modify_config.json'
key_file_path = 'file_path'


def select_file():
    """弹出文件选择窗口，并将选定文件的完整路径显示在 Text 组件中。"""
    select_file_path = filedialog.askopenfilename()
    if select_file_path:  # 如果用户选择了文件
        if not select_file_path.endswith("dota2.exe"):
            messagebox.showerror("错误", "请选择dota2.exe文件！")
            return None
        global file_path
        file_path = select_file_path
        if os.path.exists(config_file_path):
            os.remove(config_file_path)
        with open(config_file_path, 'w', encoding='utf-8') as file:
            json.dump({key_file_path: file_path}, file)
        update_view()
    return None


def update_view():
    global file_path
    if file_path:
        text_tips_widget.configure(text_color='black', text="当前已获取文件路径")
        extract_file_button.configure(state=tk.NORMAL)
    else:
        text_tips_widget.configure(text_color='red', text="请选择dota2.exe文件")
        extract_file_button.configure(state=tk.DISABLED)


def read_config() -> dict:
    """判断本地有没有 'dota2_modify_config.json' 文件，有就读取并返回 dict, 否则返回空。"""

    if os.path.exists(config_file_path):
        with open(config_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        return {}


def unpack_file():
    unpack_from_vpk(file_path)
    messagebox.showinfo("提示", "解压完成！")

def package_file():
    warning_str = unpack.pack_to_vpk(file_path)
    if warning_str:
        messagebox.showwarning("警告", warning_str)
    else:
        unpack.add_local_modify_to_gi(file_path)
        messagebox.showinfo("提示", "打包完成,享受游戏吧！")

def unpackage_file():
    unpack.remove_local_modify_from_gi(file_path)
    messagebox.showinfo("提示", "还原完成！")

if __name__ == '__main__':
    # 创建主窗口
    root = tk.CTk()
    root.title("dota2本地解包打包工具")

    # 获取屏幕宽度和高度
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # 计算窗口大小（屏幕的八分之一）
    window_width = math.ceil(screen_width / 3)
    window_height = math.ceil(screen_height / 3)

    # 计算窗口居中位置
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2

    # 设置窗口大小和位置
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    config_dict = read_config()
    file_path = config_dict.get(key_file_path)

    # 创建 Text 组件
    text_tips_widget = tk.CTkLabel(root, text='')
    text_tips_widget.pack(pady=10)  # 垂直方向上留出10像素的填充

    # 创建 Button 组件
    select_file_button = tk.CTkButton(root, text="选择文件", command=select_file)
    select_file_button.pack(pady=5)  # 垂直方向上留出5像素的填充

    extract_file_button = tk.CTkButton(root, text="解压文件", command=unpack_file)
    extract_file_button.pack(pady=5)  # 垂直方向上留出5像素的填充

    package_file_button = tk.CTkButton(root, text="打包文件", command=package_file)
    package_file_button.pack(pady=5)

    unpackage_file_button = tk.CTkButton(root, text="还原文件", command=unpackage_file)
    unpackage_file_button.pack(pady=5)
    update_view()
    # 运行主循环
    root.mainloop()
