"""技能编辑 Tab 组件"""

import os
import shutil

import tkinter as tk
from tkinter import ttk
import vdf
import vpk

from hero_constants import SKILL_EDITABLE_FIELDS, get_pak01_dir, get_hero_skill_file_path
from skill_constants import get_hero_abilities, extract_skill_field, parse_level_values, join_level_values
from undo_manager import UndoManager
import unpack


class SkillEditor:
    """封装技能 Tab 的 UI 构建、数据加载、修改检测、校验、保存"""

    def __init__(self, file_path: str, on_change_callback=None):
        self.file_path = file_path  # dota2.exe 路径
        self._on_change_callback = on_change_callback

        # 技能数据缓存：hero_key → vdf 解析后的技能数据 dict
        self._skill_data_cache = {}
        # 技能文件备份路径缓存：hero_key → .bak 路径
        self._backup_paths = {}

        # 当前编辑状态
        self._current_hero_key = None
        self._current_abilities = []  # [(编号, ability_key), ...]
        self._field_entries = {}  # (ability_key, field_name) → [Entry, Entry, ...]
        self._field_info = {}    # (ability_key, field_name) → extract_skill_field 返回的 dict
        self._has_changes = False

        # 撤销/重做
        self.undo_manager = UndoManager()

        # UI 引用
        self.scrollable_frame = None
        self.canvas = None
        self.canvas_window = None
        self._skill_content_frame = None  # 技能内容容器，切换英雄时清空重建

    def build(self, parent: ttk.Frame):
        """构建技能编辑 Tab 的 UI"""
        # 可滚动区域
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

        # 快捷操作按钮栏
        self._quick_btn_frame = ttk.Frame(self.scrollable_frame)
        self._quick_btn_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        quick_actions = [
            ("冷却减半", "AbilityCooldown", 0.5),
            ("魔耗减半", "AbilityManaCost", 0.5),
            ("前摇减半", "AbilityCastPoint", 0.5),
            ("施法距离×2", "AbilityCastRange", 2),
            ("持续时间×2", "AbilityDuration", 2),
        ]
        for label, field, multiplier in quick_actions:
            btn = ttk.Button(self._quick_btn_frame, text=label,
                             command=lambda f=field, m=multiplier: self._apply_quick_action(f, m))
            btn.pack(side=tk.LEFT, padx=(0, 5))

        self._reset_quick_btn = ttk.Button(self._quick_btn_frame, text="重置修改",
                                            command=self._reset_all_fields)
        self._reset_quick_btn.pack(side=tk.RIGHT)

        # 技能内容容器
        self._skill_content_frame = ttk.Frame(self.scrollable_frame)
        self._skill_content_frame.pack(fill=tk.BOTH, expand=True)

        # 占位提示
        ttk.Label(self._skill_content_frame, text="请选择英雄",
                  font=("Microsoft YaHei UI", 12), foreground="gray").pack(pady=50)

    def load(self, hero_key: str, heroes_data: dict):
        """加载指定英雄的技能数据到编辑区"""
        self._current_hero_key = hero_key
        self._current_abilities = []
        self._field_entries = {}
        self._field_info = {}
        self._has_changes = False
        self.undo_manager.clear()

        # 清空现有内容
        for widget in self._skill_content_frame.winfo_children():
            widget.destroy()

        # 获取英雄的技能列表
        dota_heroes = heroes_data.get("DOTAHeroes", {})
        hero_data = dota_heroes.get(hero_key, {})
        abilities = get_hero_abilities(hero_data)

        if not abilities:
            ttk.Label(self._skill_content_frame, text="该英雄无可用技能",
                      font=("Microsoft YaHei UI", 12), foreground="gray").pack(pady=50)
            return

        self._current_abilities = abilities

        # 加载技能文件数据
        skill_data = self._load_skill_file(hero_key)
        if skill_data is None:
            ttk.Label(self._skill_content_frame, text="技能文件不存在或无法解析",
                      font=("Microsoft YaHei UI", 12), foreground="gray").pack(pady=50)
            return

        # 为每个技能构建编辑区
        dota_abilities = skill_data.get("DOTAAbilities", {})

        for idx, (num, ability_key) in enumerate(abilities):
            ability_data = dota_abilities.get(ability_key, {})
            if not ability_data or not isinstance(ability_data, dict):
                continue

            self._build_ability_section(num, ability_key, ability_data)

    def validate(self) -> tuple:
        """校验所有输入值

        返回: (is_valid, error_message)
        """
        for (ability_key, field_name), entries in self._field_entries.items():
            for i, entry in enumerate(entries):
                val = entry.get().strip()
                if not val:
                    continue
                try:
                    float(val)
                except ValueError:
                    cn_name = self._get_field_cn_name(field_name)
                    return False, f"技能 {ability_key} 的 \"{cn_name}\" 第{i+1}级值 \"{val}\" 不是有效数字"
        return True, ""

    def save_changes(self):
        """将修改保存到技能文件

        返回: (success, error_message)
        """
        if not self._current_hero_key:
            return True, ""

        hero_key = self._current_hero_key
        skill_data = self._load_skill_file(hero_key)
        if skill_data is None:
            return False, "无法加载技能文件"

        dota_abilities = skill_data.get("DOTAAbilities", {})

        # 备份技能文件
        self._backup_skill_file(hero_key)

        # 应用修改到技能数据
        for (ability_key, field_name), entries in self._field_entries.items():
            ability_data = dota_abilities.get(ability_key)
            if not ability_data or not isinstance(ability_data, dict):
                continue

            info = self._field_info.get((ability_key, field_name))
            if not info or not info["found"]:
                continue

            # 拼接新值
            new_values = [e.get().strip() for e in entries]
            new_value_str = join_level_values(new_values)

            # 根据字段位置写回
            if info["location"] == "top":
                ability_data[field_name] = new_value_str
            elif info["location"] == "ability_values":
                av_key = info["ability_values_key"]
                ability_values = ability_data.get("AbilityValues", {})
                if av_key in ability_values:
                    if isinstance(ability_values[av_key], dict):
                        ability_values[av_key]["value"] = new_value_str
                    else:
                        # 简单字符串形式，直接替换
                        ability_values[av_key] = new_value_str

        # 写回文件
        skill_file_path = get_hero_skill_file_path(hero_key)
        try:
            os.makedirs(os.path.dirname(skill_file_path), exist_ok=True)
            with open(skill_file_path, "w", encoding="utf-8") as f:
                vdf.dump(skill_data, f, pretty=True)
        except Exception as e:
            return False, f"写入技能文件失败：{e}"

        self._has_changes = False
        return True, ""

    def save_changes_to_file(self):
        """将修改写入技能文件（自动保存用，不重置修改标记，静默失败）

        返回: True 成功, False 失败
        """
        if not self._current_hero_key:
            return True

        hero_key = self._current_hero_key
        skill_data = self._load_skill_file(hero_key)
        if skill_data is None:
            return False

        dota_abilities = skill_data.get("DOTAAbilities", {})

        # 备份技能文件
        self._backup_skill_file(hero_key)

        # 应用修改到技能数据
        for (ability_key, field_name), entries in self._field_entries.items():
            ability_data = dota_abilities.get(ability_key)
            if not ability_data or not isinstance(ability_data, dict):
                continue

            info = self._field_info.get((ability_key, field_name))
            if not info or not info["found"]:
                continue

            # 拼接新值
            new_values = [e.get().strip() for e in entries]
            new_value_str = join_level_values(new_values)

            # 根据字段位置写回
            if info["location"] == "top":
                ability_data[field_name] = new_value_str
            elif info["location"] == "ability_values":
                av_key = info["ability_values_key"]
                ability_values = ability_data.get("AbilityValues", {})
                if av_key in ability_values:
                    if isinstance(ability_values[av_key], dict):
                        ability_values[av_key]["value"] = new_value_str
                    else:
                        ability_values[av_key] = new_value_str

        # 写回文件
        skill_file_path = get_hero_skill_file_path(hero_key)
        try:
            os.makedirs(os.path.dirname(skill_file_path), exist_ok=True)
            with open(skill_file_path, "w", encoding="utf-8") as f:
                vdf.dump(skill_data, f, pretty=True)
        except Exception:
            return False

        # 更新缓存
        self._skill_data_cache[hero_key] = skill_data
        return True

    def has_changes(self) -> bool:
        """是否有未保存的修改"""
        return self._has_changes

    def reset_changes_flag(self):
        """重置修改标记"""
        self._has_changes = False

    def restore_skill_file(self, hero_key: str, pak=None) -> tuple:
        """从 VPK 重新提取技能文件，恢复到初始状态

        Args:
            hero_key: 英雄键名
            pak: 可选的已打开的 VPK 对象，传入则复用，不传则自行打开

        返回: (success, error_message)
        """
        skill_file_path = get_hero_skill_file_path(hero_key)
        should_close = pak is None
        try:
            if pak is None:
                parent = unpack.get_game_root_dir(self.file_path)
                vpk_file_path = os.path.join(parent, "dota", "pak01_dir.vpk")
                pak = vpk.open(vpk_file_path)
            vpk_skill_path = f"scripts/npc/heroes/{hero_key}.txt"
            if vpk_skill_path in pak:
                pak_file = pak.get_file(vpk_skill_path)
                os.makedirs(os.path.dirname(skill_file_path), exist_ok=True)
                pak_file.save(skill_file_path)
            elif os.path.exists(skill_file_path):
                os.remove(skill_file_path)

            # 清除缓存，强制下次重新加载
            self._skill_data_cache.pop(hero_key, None)
            self._backup_paths.pop(hero_key, None)
            # 删除备份文件
            bak_path = skill_file_path + ".bak"
            if os.path.exists(bak_path):
                os.remove(bak_path)

        except Exception as e:
            return False, f"恢复技能文件失败：{e}"
        finally:
            if should_close and pak is not None:
                try:
                    pak.close()
                except Exception:
                    pass

        return True, ""

    def restore_all_skill_files(self, hero_keys: list) -> tuple:
        """批量从 VPK 重新提取所有技能文件（只打开一次 VPK）

        返回: (restored_count, error_messages)
        """
        try:
            parent = unpack.get_game_root_dir(self.file_path)
            vpk_file_path = os.path.join(parent, "dota", "pak01_dir.vpk")
            pak = vpk.open(vpk_file_path)
        except Exception as e:
            return 0, [f"打开VPK失败：{e}"]

        restored_count = 0
        errors = []
        try:
            for hero_key in hero_keys:
                success, err_msg = self.restore_skill_file(hero_key, pak=pak)
                if success:
                    restored_count += 1
                else:
                    errors.append(err_msg)
        finally:
            try:
                pak.close()
            except Exception:
                pass

        return restored_count, errors

    # ---- 内部方法 ----

    def _load_skill_file(self, hero_key: str):
        """加载技能文件数据（带缓存）"""
        if hero_key in self._skill_data_cache:
            return self._skill_data_cache[hero_key]

        skill_file_path = get_hero_skill_file_path(hero_key)
        if not os.path.exists(skill_file_path):
            return None

        try:
            with open(skill_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = unpack.preprocess_vdf_content(content)
            data = vdf.loads(content)
            self._skill_data_cache[hero_key] = data
            return data
        except Exception:
            return None

    def _backup_skill_file(self, hero_key: str):
        """备份技能文件（仅首次）"""
        if hero_key in self._backup_paths:
            return

        skill_file_path = get_hero_skill_file_path(hero_key)
        if not os.path.exists(skill_file_path):
            return

        bak_path = skill_file_path + ".bak"
        if not os.path.exists(bak_path):
            shutil.copy2(skill_file_path, bak_path)
        self._backup_paths[hero_key] = bak_path

    def _build_ability_section(self, num: int, ability_key: str, ability_data: dict):
        """构建单个技能的编辑区"""
        # 技能标题
        title_frame = ttk.Frame(self._skill_content_frame)
        title_frame.pack(fill=tk.X, pady=(10, 2), padx=5)

        ttk.Label(title_frame, text=f"{num}: {ability_key}",
                  font=("Microsoft YaHei UI", 10, "bold")).pack(anchor=tk.W)

        # 字段编辑区（带边框）
        fields_frame = ttk.LabelFrame(self._skill_content_frame, padding=5)
        fields_frame.pack(fill=tk.X, padx=15, pady=(0, 5))

        for field_name, cn_name in SKILL_EDITABLE_FIELDS:
            info = extract_skill_field(ability_data, field_name)
            self._field_info[(ability_key, field_name)] = info

            row_frame = ttk.Frame(fields_frame)
            row_frame.pack(fill=tk.X, pady=2)

            # 字段中文名标签
            ttk.Label(row_frame, text=cn_name, width=8,
                      font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(0, 5))

            if not info["found"]:
                # 无此属性，显示灰色 --
                ttk.Label(row_frame, text="--", foreground="gray",
                          font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
                continue

            # 解析多级值
            level_values = parse_level_values(info["values"])
            entries = []

            for i, val in enumerate(level_values):
                # 等级标签（仅第一行显示）
                if i == 0:
                    lv_label = ttk.Label(row_frame, text=f"Lv{i+1}",
                                         font=("Microsoft YaHei UI", 8), width=3)
                    lv_label.pack(side=tk.LEFT, padx=(0, 1))
                else:
                    ttk.Label(row_frame, text=f"Lv{i+1}",
                              font=("Microsoft YaHei UI", 8), width=3).pack(side=tk.LEFT, padx=(0, 1))

                entry = tk.Entry(row_frame, width=7, font=("Microsoft YaHei UI", 9))
                entry.insert(0, val)
                entry.pack(side=tk.LEFT, padx=(0, 5))

                # 绑定修改检测
                entry.bind("<KeyRelease>",
                           lambda e, ak=ability_key, fn=field_name: self._on_value_change(ak, fn))

                entries.append(entry)

            self._field_entries[(ability_key, field_name)] = entries

            # 天赋信息展示
            if info["talents"]:
                talent_texts = []
                for t in info["talents"]:
                    talent_texts.append(f"{t['value']} ({t['key']})")
                talent_str = "天赋: " + ", ".join(talent_texts)
                ttk.Label(row_frame, text=talent_str, foreground="#8B4513",
                          font=("Microsoft YaHei UI", 8)).pack(side=tk.LEFT, padx=(10, 0))

    def _on_value_change(self, ability_key: str, field_name: str):
        """技能值变化时检测修改"""
        entries = self._field_entries.get((ability_key, field_name))
        info = self._field_info.get((ability_key, field_name))
        if not entries or not info:
            return

        # 比较当前值与原始值
        current_values = [e.get().strip() for e in entries]
        original_values = parse_level_values(info["values"])

        # 记录撤销操作（仅当值确实改变时，且不是撤销/重做触发的）
        changed = current_values != original_values
        if changed and not hasattr(self, '_undoing'):
            cn_name = self._get_field_cn_name(field_name)
            old_vals = list(original_values)
            new_vals = list(current_values)
            self.undo_manager.push(
                desc=f"修改{ability_key}的{cn_name}",
                undo_fn=lambda es=entries, ak=ability_key, fn=field_name, ov=old_vals: self._set_entries_values(es, ak, fn, ov),
                redo_fn=lambda es=entries, ak=ability_key, fn=field_name, nv=new_vals: self._set_entries_values(es, ak, fn, nv),
            )

        for entry in entries:
            entry.configure(bg="#FFFACD" if changed else "white")

        if changed:
            self._has_changes = True
        else:
            self._check_unsaved_changes()

        if self._on_change_callback:
            self._on_change_callback()

    def _set_entries_values(self, entries, ability_key: str, field_name: str, values: list):
        """设置多个 Entry 的值（撤销/重做用）"""
        self._undoing = True
        for entry, val in zip(entries, values):
            entry.delete(0, tk.END)
            entry.insert(0, val)
        del self._undoing
        self._on_value_change(ability_key, field_name)

    def undo(self) -> str:
        """撤销最近一次技能修改"""
        return self.undo_manager.undo()

    def redo(self) -> str:
        """重做最近一次技能修改"""
        return self.undo_manager.redo()

    def _check_unsaved_changes(self):
        """检查所有字段是否与原始值相同"""
        for (ability_key, field_name), entries in self._field_entries.items():
            info = self._field_info.get((ability_key, field_name))
            if not info or not info["found"]:
                continue
            current_values = [e.get().strip() for e in entries]
            original_values = parse_level_values(info["values"])
            if current_values != original_values:
                self._has_changes = True
                return
        self._has_changes = False

    def _get_field_cn_name(self, field_name: str) -> str:
        """获取字段中文名"""
        for fn, cn in SKILL_EDITABLE_FIELDS:
            if fn == field_name:
                return cn
        return field_name

    def _apply_quick_action(self, field_name: str, multiplier: float):
        """对所有技能的指定字段执行乘法快捷操作"""
        cn_name = self._get_field_cn_name(field_name)
        count = 0
        for (ak, fn), entries in self._field_entries.items():
            if fn != field_name:
                continue
            info = self._field_info.get((ak, fn))
            if not info or not info["found"]:
                continue

            for entry in entries:
                val = entry.get().strip()
                if not val:
                    continue
                try:
                    new_val = float(val) * multiplier
                    # 保留合理精度：整数不带小数，否则最多4位
                    if new_val == int(new_val):
                        new_str = str(int(new_val))
                    else:
                        new_str = f"{new_val:.4f}".rstrip("0").rstrip(".")
                    entry.delete(0, tk.END)
                    entry.insert(0, new_str)
                    count += 1
                except ValueError:
                    continue

            # 触发修改检测
            self._on_value_change(ak, fn)

        # 反馈
        if self._on_change_callback and count > 0:
            op = "×" if multiplier >= 1 else "÷"
            factor = multiplier if multiplier >= 1 else 1 / multiplier
            self._on_change_callback(f"已将所有技能{cn_name}{op}{factor:.1f}（{count}个值）")

    def _reset_all_fields(self):
        """将所有字段恢复到原始值"""
        for (ak, fn), entries in self._field_entries.items():
            info = self._field_info.get((ak, fn))
            if not info or not info["found"]:
                continue
            original_values = parse_level_values(info["values"])
            for entry, orig_val in zip(entries, original_values):
                entry.delete(0, tk.END)
                entry.insert(0, orig_val)
                entry.configure(bg="white")
            # 更新 field_info 中的原始值（因为快捷操作可能已修改过）
            # 不需要更新，原始值始终是文件中的值

        self._has_changes = False
        if self._on_change_callback:
            self._on_change_callback("已重置所有技能字段到原始值")

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
