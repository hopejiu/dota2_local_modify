import os
import shutil
import sys

import vdf
import vpk


def get_app_dir() -> str:
    """获取应用程序所在目录（兼容 PyInstaller 打包和直接运行）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def create_directory(directory_path: str):
    """创建目录，失败时抛出异常由调用方处理"""
    os.makedirs(directory_path, exist_ok=True)


def get_game_root_dir(dota2_path: str) -> str:
    """从 dota2.exe 路径获取游戏根目录 (game 文件夹)

    例: E:/SteamLibrary/steamapps/common/dota 2 beta/game/bin/win64/dota2.exe
        -> E:/SteamLibrary/steamapps/common/dota 2 beta/game
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(dota2_path)))


def preprocess_vdf_content(content: str) -> str:
    """预处理 VDF 文本内容，修复 vdf 库无法解析的问题

    处理内容：
    1. 同行双闭合括号（如 "}\\t\\t}"）拆为两行
    2. 移除整行注释（含引号的注释会干扰 vdf 解析）
    3. 移除行内注释（引号外的 // 注释）
    """
    # 修复同行双闭合括号
    content = content.replace("}\t\t}", "}\n\t\t}")
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        # 移除行内注释
        in_quote = False
        result = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"':
                in_quote = not in_quote
                result.append(ch)
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/" and not in_quote:
                break
            else:
                result.append(ch)
            i += 1
        cleaned.append("".join(result))
    return "\n".join(cleaned)


def unpack_from_vpk(dota2_path: str, progress_callback=None):
    """从 VPK 文件中解压 scripts/npc/ 下的文件

    Args:
        dota2_path: dota2.exe 路径
        progress_callback: 可选进度回调函数，签名为 callback(current, total, filename)
    """
    extract_path = os.path.join(get_app_dir(), "pak01_dir")
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    parent = get_game_root_dir(dota2_path)
    vpk_file_path = os.path.join(parent, "dota", "pak01_dir.vpk")
    if not os.path.exists(vpk_file_path):
        raise FileNotFoundError(f"VPK 文件不存在: {vpk_file_path}\n请检查 Dota 2 游戏路径是否正确")

    try:
        pak1 = vpk.open(vpk_file_path)
    except Exception as e:
        raise RuntimeError(f"无法打开 VPK 文件: {e}")

    need_save = []
    need_create_dir = set()
    for filepath in pak1:
        if filepath.startswith("scripts/npc/"):
            split_list = filepath.split("/")[0:-1]
            new_dir = os.path.join(extract_path, *split_list)
            need_create_dir.add(new_dir)
            need_save.append(filepath)

    for dir_path in need_create_dir:
        create_directory(dir_path)

    total = len(need_save)
    for current, filepath in enumerate(need_save, 1):
        try:
            pak_file = pak1.get_file(filepath)
            pak_file.save(os.path.join(extract_path, filepath.replace("/", os.sep)))
        except Exception as e:
            raise RuntimeError(f"解压文件 {filepath} 时出错: {e}")
        if progress_callback:
            progress_callback(current, total, filepath)


modify_dir_name = "local_modify"
gi_file_name = "gameinfo.gi"


def get_gi_path(dota2_path: str) -> str:
    parent = get_game_root_dir(dota2_path)
    return os.path.join(parent, "dota", "gameinfo.gi")


def mv_2_update_dir(dota2_path: str, vpk_path: str):
    parent = get_game_root_dir(dota2_path)
    target_dir_path = os.path.join(parent, modify_dir_name)
    if os.path.exists(target_dir_path):
        shutil.rmtree(target_dir_path)
    create_directory(target_dir_path)
    shutil.move(vpk_path, target_dir_path)


def pack_to_vpk(dota2_path: str) -> str:
    """将 pak01_dir 目录打包为 VPK 并移动到游戏目录

    Returns:
        空字符串表示成功，非空字符串为错误提示信息
    """
    app_dir = get_app_dir()
    target_path = os.path.join(app_dir, "pak01_dir")
    if not os.path.exists(target_path):
        return "请先解压文件后再打包"
    try:
        newpak = vpk.new(target_path)
        vpk_output_path = os.path.join(app_dir, "pak01_dir.vpk")
        if os.path.exists(vpk_output_path):
            os.remove(vpk_output_path)
        newpak.save(vpk_output_path)
        mv_2_update_dir(dota2_path, vpk_output_path)
    except Exception as e:
        raise RuntimeError(f"打包 VPK 文件时出错: {e}")
    return ""


def is_unpacked() -> bool:
    """检查是否已解压（pak01_dir 目录存在且包含内容）"""
    extract_path = os.path.join(get_app_dir(), "pak01_dir")
    if not os.path.exists(extract_path):
        return False
    return bool(os.listdir(extract_path))


def is_modified(dota2_path: str) -> bool:
    """检查 gameinfo.gi 中是否已包含 local_modify"""
    gi_path = get_gi_path(dota2_path)
    if not os.path.exists(gi_path):
        return False
    try:
        with open(gi_path, "r", encoding="utf-8") as f:
            data_dict = vdf.load(f, mapper=vdf.VDFDict)
    except Exception:
        return False
    items = data_dict["GameInfo"]["FileSystem"]["SearchPaths"].get_all_for("Game")
    return "local_modify" in items


def add_local_modify_to_gi(dota2_path: str):
    gi_path = get_gi_path(dota2_path)
    try:
        with open(gi_path, "r", encoding="utf-8") as f:
            data_dict = vdf.load(f, mapper=vdf.VDFDict)
    except PermissionError:
        raise PermissionError(f"无法读取 {gi_path}\n请确保游戏未运行，且以管理员身份运行本程序")
    items = data_dict["GameInfo"]["FileSystem"]["SearchPaths"].get_all_for("Game")
    if "local_modify" in items:
        return
    new_vdf_dict = vdf.VDFDict({"Game": "local_modify"})
    for (k, v) in data_dict["GameInfo"]["FileSystem"]["SearchPaths"].items():
        new_vdf_dict[k] = v
    del data_dict["GameInfo"]["FileSystem"]["SearchPaths"]
    data_dict["GameInfo"]["FileSystem"].update({"SearchPaths": new_vdf_dict})
    try:
        with open(gi_path, "w", encoding="utf-8") as f:
            vdf.dump(data_dict, f, pretty=True)
    except PermissionError:
        raise PermissionError(f"无法写入 {gi_path}\n请确保游戏未运行，且以管理员身份运行本程序")


def remove_local_modify_from_gi(dota2_path: str):
    gi_path = get_gi_path(dota2_path)
    try:
        with open(gi_path, "r", encoding="utf-8") as f:
            data_dict = vdf.load(f, mapper=vdf.VDFDict)
    except PermissionError:
        raise PermissionError(f"无法读取 {gi_path}\n请确保游戏未运行，且以管理员身份运行本程序")
    items = data_dict["GameInfo"]["FileSystem"]["SearchPaths"].get_all_for("Game")
    if "local_modify" not in items:
        return
    new_vdf_dict = vdf.VDFDict()
    for (k, v) in data_dict["GameInfo"]["FileSystem"]["SearchPaths"].items():
        if k == "Game" and v == "local_modify":
            continue
        new_vdf_dict[k] = v
    del data_dict["GameInfo"]["FileSystem"]["SearchPaths"]
    data_dict["GameInfo"]["FileSystem"].update({"SearchPaths": new_vdf_dict})
    try:
        with open(gi_path, "w", encoding="utf-8") as f:
            vdf.dump(data_dict, f, pretty=True)
    except PermissionError:
        raise PermissionError(f"无法写入 {gi_path}\n请确保游戏未运行，且以管理员身份运行本程序")
