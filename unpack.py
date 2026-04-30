import os
import shutil

import vdf
import vpk


def create_directory(directory_path: str):
    try:
        os.makedirs(directory_path, exist_ok=True)
    except Exception as e:
        print(f"创建目录时发生错误: {e}")


def get_game_root_dir(dota2_path: str) -> str:
    """从 dota2.exe 路径获取游戏根目录 (game 文件夹)

    例: E:/SteamLibrary/steamapps/common/dota 2 beta/game/bin/win64/dota2.exe
        -> E:/SteamLibrary/steamapps/common/dota 2 beta/game
    """
    return os.path.dirname(os.path.dirname(os.path.dirname(dota2_path)))


def unpack_from_vpk(dota2_path: str):
    extract_path = os.path.join(os.path.abspath("."), "pak01_dir")
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    parent = get_game_root_dir(dota2_path)
    vpk_file_path = os.path.join(parent, "dota", "pak01_dir.vpk")
    pak1 = vpk.open(vpk_file_path)
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
    for filepath in need_save:
        pak_file = pak1.get_file(filepath)
        pak_file.save(os.path.join(extract_path, filepath.replace("/", os.sep)))


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
    target_path = os.path.join(os.path.abspath("."), "pak01_dir")
    if not os.path.exists(target_path):
        return "文件夹不存在"
    newpak = vpk.new(target_path)
    if os.path.exists("pak01_dir.vpk"):
        os.remove("pak01_dir.vpk")
    newpak.save("pak01_dir.vpk")
    mv_2_update_dir(dota2_path, os.path.join(os.path.abspath("."), "pak01_dir.vpk"))
    return ""


def add_local_modify_to_gi(dota2_path: str):
    gi_path = get_gi_path(dota2_path)
    with open(gi_path, "r", encoding="utf-8") as f:
        data_dict = vdf.load(f, mapper=vdf.VDFDict)
    items = data_dict["GameInfo"]["FileSystem"]["SearchPaths"].get_all_for("Game")
    if "local_modify" in items:
        return
    new_vdf_dict = vdf.VDFDict({"Game": "local_modify"})
    for (k, v) in data_dict["GameInfo"]["FileSystem"]["SearchPaths"].items():
        new_vdf_dict[k] = v
    del data_dict["GameInfo"]["FileSystem"]["SearchPaths"]
    data_dict["GameInfo"]["FileSystem"].update({"SearchPaths": new_vdf_dict})
    with open(gi_path, "w", encoding="utf-8") as f:
        vdf.dump(data_dict, f, pretty=True)


def remove_local_modify_from_gi(dota2_path: str):
    gi_path = get_gi_path(dota2_path)
    with open(gi_path, "r", encoding="utf-8") as f:
        data_dict = vdf.load(f, mapper=vdf.VDFDict)
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
    with open(gi_path, "w", encoding="utf-8") as f:
        vdf.dump(data_dict, f, pretty=True)
