## 注意
本修改方法仅适用于单机娱乐,在多人模式中无效.
## 软件使用方法
1. 打开main.exe
2. 第一次打开会提示红色报错(请选择dota2.exe文件),点击"选择文件"按钮,选择dota2.exe文件
3. 点击"解压文件"按钮
4. 程序会自动在软件的目录生成"pak01_dir"文件夹, 其中重要的文件有
    - pak01_dir\scripts\npc\npc_heros.txt 记录所有英雄的属性和拥有的技能
    - pak01_dir\scripts\npc\items.txt  记录所有物品的技能效果和购买价格
    - pak01_dir\scripts\npc\heroes\
    该文件夹下面每个文件代表一个英雄的具体技能配置 
5. 按照自己喜好用记事本/vscode(推荐) 等文本编辑工具修改后, 点击"打包文件"按钮
6. 打开dota2, 在主界面(没有点击开始DOTA) 可以预览英雄的技能和属性, 如果修改生效,可以看到属性变化.如攻击间隔, 移动速度等.
7. 点击开始DOTA-创建房间-编辑-服务器地点改成本地主机. 开始比赛后修改生效.


## 打包方式
1. 安装pyinstaller
2. 执行命令
```pyinstaller -F -i "icon.ico" -w main.py```

## 英雄 英文名对应
整理了一份dota2 英雄中英文名对应的名单,方便修改
- 不朽尸王 , undying
- 伐木机 , shredder
- 全能骑士 , omniknight
- 军团指挥官 , legion_commander
- 冥魂大帝 , skeleton_king
- 凤凰 , phoenix
- 半人马战行者 , centaur
- 发条技师 , rattletrap
- 哈斯卡 , huskar
- 噬魂鬼 , life_stealer
- 大地之灵 , earth_spirit
- 孽主 , abyssal_underlord
- 小小 , tiny
- 巨牙海民 , tusk
- 帕吉 , pudge
- 撼地者 , earthshaker
- 斧王 , axe
- 斯拉达 , slardar
- 斯温 , sven
- 昆卡 , kunkka
- 暗夜魔王 , night_stalker
- 末日使者 , doom_bringer
- 树精卫士 , treant
- 混沌骑士 , chaos_knight
- 潮汐猎人 , tidehunter
- 炼金术士 , alchemist
- 狼人 , lycan
- 獸 , primal_beast
- 玛尔斯 , mars
- 破晓辰星 , dawnbreaker
- 裂魂人 , spirit_breaker
- 钢背兽 , bristleback
- 食人魔魔法师 , ogre_magi
- 龙骑士 , dragon_knight
- 上古巨神 , elder_titan
- 主宰 , juggernaut
- 亚巴顿 , abaddon
- 修补匠 , tinker
- 光之守卫 , keeper_of_the_light
- 克林克兹 , clinkz
- 兽王 , beastmaster
- 冥界亚龙 , viper
- 凯 , kez
- 剧毒术士 , venomancer
- 力丸 , riki
- 卓尔游侠 , drow_ranger
- 变体精灵 , morphling
- 司夜刺客 , nyx_assassin
- 圣堂刺客 , templar_assassin
- 复仇之魂 , vengefulspirit
- 天怒法师 , skywrath_mage
- 天涯墨客 , grimstroke
- 天穹守望者 , arc_warden
- 娜迦海妖 , naga_siren
- 宙斯 , zuus
- 寒冬飞龙 , winter_wyvern
- 工程师 , techies
- 巨魔战将 , troll_warlord
- 巫医 , witch_doctor
- 巫妖 , lich
- 帕克 , puck
- 帕格纳 , pugna
- 干扰者 , disruptor
- 幻影刺客 , phantom_assassin
- 幻影长矛手 , phantom_lancer
- 幽鬼 , spectre
- 影魔 , nevermore
- 恐怖利刃 , terrorblade
- 戴泽 , dazzle
- 拉席克 , leshrac
- 拉比克 , rubick
- 敌法师 , antimage
- 斯拉克 , slark
- 暗影恶魔 , shadow_demon
- 暗影萨满 , shadow_shaman
- 术士 , warlock
- 杰奇洛 , jakiro
- 森海飞霞 , hoodwink
- 死亡先知 , death_prophet
- 殁境神蚀者 , obsidian_destroyer
- 水晶室女 , crystal_maiden
- 沉默术士 , silencer
- 沙王 , sand_king
- 灰烬之灵 , ember_spirit
- 熊战士 , ursa
- 狙击手 , sniper
- 独行德鲁伊 , lone_druid
- 玛西 , marci
- 琼英碧灵 , muerta
- 电炎绝手 , snapfire
- 痛苦女王 , queenofpain
- 瘟疫法师 , necrolyte
- 百戏大王 , ringmaster
- 矮人直升机 , gyrocopter
- 石鳞剑士 , pangolier
- 祈求者 , invoker
- 神谕者 , oracle
- 祸乱之源 , bane
- 米拉娜 , mirana
- 米波 , meepo
- 维萨吉 , visage
- 编织者 , weaver
- 美杜莎 , medusa
- 育母蜘蛛 , broodmother
- 自然先知 , furion
- 艾欧 , wisp
- 莉娜 , lina
- 莱恩 , lion
- 虚无之灵 , void_spirit
- 虚空假面 , faceless_void
- 蝙蝠骑士 , batrider
- 血魔 , bloodseeker
- 谜团 , enigma
- 赏金猎人 , bounty_hunter
- 远古冰魄 , ancient_apparition
- 邪影芳灵 , dark_willow
- 酒仙 , brewmaster
- 陈 , chen
- 雷泽 , razor
- 露娜 , luna
- 风暴之灵 , storm_spirit
- 风行者 , windrunner
- 马格纳斯 , magnataur
- 魅惑魔女 , enchantress
- 黑暗贤者 , dark_seer
- 齐天大圣 , monkey_king