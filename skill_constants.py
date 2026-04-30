"""技能数据提取辅助函数"""

from hero_constants import SKILL_EDITABLE_FIELDS


def get_hero_abilities(hero_data: dict) -> list:
    """从英雄数据中提取技能列表（排除 generic_hidden 和 special_bonus_*）

    返回: [(编号, ability_key), ...]，如 [(1, "axe_berserkers_call"), ...]
    """
    abilities = []
    for i in range(1, 9):
        key = f"Ability{i}"
        ability_name = hero_data.get(key, "")
        if not ability_name:
            continue
        if ability_name == "generic_hidden":
            continue
        if ability_name.startswith("special_bonus"):
            continue
        abilities.append((len(abilities) + 1, ability_name))
    return abilities


def extract_skill_field(skill_data: dict, field_name: str):
    """从技能数据中提取指定字段的值和天赋信息

    字段可能存在于两个位置：
    1. 顶层字符串：如 "AbilityCastPoint" "0.3"
    2. AbilityValues 内的 dict：如 "AbilityCooldown" { "value" "18 16 14 12" "special_bonus_xxx" "-3" }

    返回: {
        "found": bool,
        "values": str,           # 原始值字符串，如 "18 16 14 12"
        "location": "top" | "ability_values" | None,  # 字段所在位置
        "ability_values_key": str | None,  # 如果在 AbilityValues 内，对应的 key
        "talents": list,         # [{"key": "special_bonus_xxx", "value": "-3"}, ...]
    }
    """
    result = {
        "found": False,
        "values": "",
        "location": None,
        "ability_values_key": None,
        "talents": [],
    }

    # 1. 检查顶层
    top_value = skill_data.get(field_name)
    if top_value is not None and not isinstance(top_value, dict):
        result["found"] = True
        result["values"] = str(top_value)
        result["location"] = "top"
        return result

    # 2. 检查 AbilityValues 内
    ability_values = skill_data.get("AbilityValues", {})
    if isinstance(ability_values, dict):
        # 字段名可能在 AbilityValues 中作为 key 直接存在
        # 如 "AbilityCooldown" { "value" "18 16 14 12" }
        av_entry = ability_values.get(field_name)
        if av_entry is not None:
            if isinstance(av_entry, dict):
                # dict 形式：{ "value" "18 16 14 12", "special_bonus_xxx" "-3" }
                result["found"] = True
                result["values"] = str(av_entry.get("value", ""))
                result["location"] = "ability_values"
                result["ability_values_key"] = field_name
                # 提取天赋信息
                for k, v in av_entry.items():
                    if k.startswith("special_bonus"):
                        result["talents"].append({"key": k, "value": str(v)})
                return result
            else:
                # 简单字符串形式：如 "AbilityCastPoint" "0.3 0.3 0.3 0.3"
                result["found"] = True
                result["values"] = str(av_entry)
                result["location"] = "ability_values"
                result["ability_values_key"] = field_name
                return result

    # 3. 未找到
    return result


def parse_level_values(value_str: str) -> list:
    """将空格分隔的多级值字符串拆分为列表

    "18 16 14 12" → ["18", "16", "14", "12"]
    "0.3" → ["0.3"]
    "" → []
    """
    if not value_str or not value_str.strip():
        return []
    return value_str.strip().split()


def join_level_values(values: list) -> str:
    """将多级值列表拼接回空格分隔的字符串

    ["18", "16", "14", "12"] → "18 16 14 12"
    """
    return " ".join(values)
