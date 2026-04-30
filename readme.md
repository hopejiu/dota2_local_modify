# Dota2 本地修改工具 v1.2.0

> ⚠️ 本修改方法仅适用于单机娱乐，在多人模式中无效。

## 功能

- 解包 Dota2 的 VPK 配置文件
- 修改英雄属性、技能、物品等游戏数据
- 重新打包并部署到游戏目录
- 一键还原游戏原始文件
- 英雄中英文名查询（支持中英文搜索）
- 英雄属性可视化编辑器
- 技能参数可视化编辑器（支持天赋加成）
- PermissionError 友好提示（游戏运行时保护）
- UPX 压缩打包，减小 exe 体积

## 使用方法

1. 运行程序，首次打开会自动搜索 dota2.exe 路径
2. 如未自动找到，点击 **选择文件**，选择 Dota2 安装目录下的 `dota2.exe`
3. 点击 **解压文件**，程序会在当前目录生成 `pak01_dir` 文件夹
4. 用文本编辑器（推荐 VSCode）修改配置文件，重要文件如下：

   | 文件 | 说明 |
   |------|------|
   | `pak01_dir/scripts/npc/npc_heros.txt` | 所有英雄的属性和技能 |
   | `pak01_dir/scripts/npc/items.txt` | 所有物品的效果和价格 |
   | `pak01_dir/scripts/npc/heroes/` | 每个英雄的具体技能配置 |

5. 修改完成后点击 **打包文件**，程序会自动打包并部署
6. 启动游戏 → 创建房间 → 服务器地点改 **本地主机** → 开始比赛，修改生效
7. 如需还原，点击 **还原文件** 即可撤销所有本地修改

## 运行

### 直接运行

```bash
pip install -r requirement.txt
python main.py
```

### 打包为 exe

双击 `build.bat`，自动完成环境搭建和打包。生成的 `dota2_local_change.exe` 在 `dist/` 目录下。

或手动执行：

```bash
pip install -r requirement.txt
pip install pyinstaller
pyinstaller dota2_local_change.spec
```

## 项目结构

```
├── main.py              # GUI 主程序（tkinter）
├── unpack.py            # VPK 解包/打包/游戏配置修改
├── hero_editor.py       # 英雄编辑器主窗口（协调属性+技能）
├── attribute_editor.py  # 英雄属性编辑 Tab
├── skill_editor.py      # 技能参数编辑 Tab
├── skill_constants.py   # 技能数据提取辅助函数
├── hero_constants.py    # 英雄编辑器共享常量和工具函数
├── data.py              # 英雄中英文名映射
├── icon.ico             # 窗口图标
├── requirement.txt      # Python 依赖
├── build.bat            # 打包脚本（含 UPX 压缩）
└── run.bat              # Windows 启动脚本
```

## 依赖

- Python 3.11+
- vpk
- vdf
