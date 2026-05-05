"""英雄编辑器共享常量和工具函数"""

import os

import data
import unpack


# ---- 路径工具函数 ----

def get_pak01_dir():
    return os.path.join(unpack.get_app_dir(), "pak01_dir")


def get_npc_heroes_path():
    return os.path.join(get_pak01_dir(), "scripts", "npc", "npc_heroes.txt")


def get_hero_skill_file_path(hero_key: str):
    """获取英雄技能文件路径"""
    return os.path.join(get_pak01_dir(), "scripts", "npc", "heroes", f"{hero_key}.txt")


# ---- 英雄属性定义 ----

# 可编辑属性定义（分组）
HERO_ATTRIBUTES = {
    "基础属性": [
        ("AttributeBaseStrength", "初始力量"),
        ("AttributeStrengthGain", "力量成长"),
        ("AttributeBaseAgility", "初始敏捷"),
        ("AttributeAgilityGain", "敏捷成长"),
        ("AttributeBaseIntelligence", "初始智力"),
        ("AttributeIntelligenceGain", "智力成长"),
    ],
    "战斗属性": [
        ("MovementSpeed", "移动速度"),
        ("BaseAttackSpeed", "基础攻击速度"),
        ("AttackRate", "攻击间隔"),
        ("ArmorPhysical", "基础护甲"),
        ("AttackRange", "攻击范围"),
        ("AttackDamageMin", "最小攻击力"),
        ("AttackDamageMax", "最大攻击力"),
    ],
    "状态属性": [
        ("StatusHealth", "初始生命值"),
        ("StatusMana", "初始魔法值"),
        ("StatusHealthRegen", "生命回复"),
        ("StatusManaRegen", "魔法回复"),
        ("MagicalResistance", "魔法抗性"),
    ],
    "视野": [
        ("VisionDaytimeRange", "白天视野"),
        ("VisionNighttimeRange", "夜间视野"),
    ],
}

# base 英雄的默认属性值（用于合并显示）
BASE_DEFAULTS = {
    "AttributeBaseStrength": "0", "AttributeStrengthGain": "0",
    "AttributeBaseAgility": "0", "AttributeAgilityGain": "0",
    "AttributeBaseIntelligence": "0", "AttributeIntelligenceGain": "0",
    "MovementSpeed": "300", "BaseAttackSpeed": "100",
    "AttackRate": "1.700000", "ArmorPhysical": "-1",
    "AttackRange": "600", "AttackDamageMin": "1", "AttackDamageMax": "1",
    "StatusHealth": "120", "StatusMana": "75",
    "StatusHealthRegen": "0.25", "StatusManaRegen": "0",
    "MagicalResistance": "25",
    "VisionDaytimeRange": "1800", "VisionNighttimeRange": "800",
}

# 构建 英文名→中文名 映射
EN_TO_CN = {v: k for k, v in data.hero_map.items()}

# ---- 技能可编辑字段定义 ----

SKILL_EDITABLE_FIELDS = [
    ("AbilityCastPoint", "施法前摇"),
    ("AbilityCooldown", "冷却时间"),
    ("AbilityManaCost", "魔耗"),
    ("AbilityCastRange", "施法距离"),
    ("AbilityDuration", "持续时间"),
    ("damage", "伤害"),
]
