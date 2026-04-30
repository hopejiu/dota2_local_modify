# Dota2 本地修改工具

> ⚠️ 本修改方法仅适用于单机娱乐，在多人模式中无效。

## 功能

- 解包 Dota2 的 VPK 配置文件
- 修改英雄属性、技能、物品等游戏数据
- 重新打包并部署到游戏目录
- 一键还原游戏原始文件
- 英雄中英文名查询（支持中英文搜索）

## 使用方法

1. 运行程序，首次打开会提示"请选择dota2.exe文件"
2. 点击 **选择文件**，选择 Dota2 安装目录下的 `dota2.exe`
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
pyinstaller -F -i "icon.ico" -w --name "dota2_local_change" main.py
```

## 项目结构

```
├── main.py          # GUI 主程序（tkinter）
├── unpack.py        # VPK 解包/打包/游戏配置修改
├── data.py          # 英雄中英文名映射
├── icon.ico         # 窗口图标
├── requirement.txt  # Python 依赖
└── run.bat          # Windows 启动脚本
```

## 依赖

- Python 3.11+
- vpk
- vdf
