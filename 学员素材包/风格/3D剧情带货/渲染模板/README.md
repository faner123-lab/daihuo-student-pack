# 渲染模板（3D 剧情带货 / 3D 干货科普共用）

把「分镜 + 配音 + H3 片段」自动剪成竖屏成片：画面、白字黑边字幕、贴卡、设计字、转场、真实音效、BGM、-14 LUFS 响度，一条命令出片。带货用 `project.example.json` 改，干货科普用 `project.example.fitness.json` 改。

## 先自检

```
python3 selftest.py
```

先检查素材包的「音效库」是否完整（缺哪个文件会直接列出来），再用合成的假素材把带货和干货两种示例都渲染、混音一遍，约 2–3 分钟。通过就说明你的电脑环境（Python、ffmpeg、numpy、Pillow、scipy、中文字体）和音效、转场都没问题。报错就把报错发给 Claude，它会告诉你缺什么。

## 项目文件夹里放什么

```
我的项目/
  project.json      ← 复制 project.example.json 改（文案、镜头表、贴卡、设计字、BGM）
  clips/            ← H3 片段，命名 S01.mp4、S02.mp4…
  cards/            ← 贴卡用的原图（产品详情、检测报告等）
  vo/               ← 处理后的逐句配音 01.wav、02.wav…，和 dur.txt（每行「序号 秒数」）
  bgm/              ← 背景音乐文件
```

## 三步出片

```
# 1) 渲染画面（没有配音时先出无配音预览：去掉 --dur 即可）
python3 render.py 我的项目 --dur vo/dur.txt

# 想只看某几镜的效果：
python3 render.py 我的项目 --dur vo/dur.txt --quick S05,S06

# 2) 混音并合成成片
python3 mix.py 我的项目 成片_v1.mp4
```

成片在 `我的项目/out/`。每次改版换新的文件名（成片_v2.mp4…），不要覆盖旧的。

## project.json 怎么写

- `lines`：每句旁白原文（也是字幕，一字不改）。
- `shots`：每个镜头一条。
  - `name`：镜号，对应 `clips/镜号.mp4`；`line`：对应第几句（从 0 开始）；
  - `enter`：进场转场，选 `hard`（硬切）、`zoom`（放大冲击）、`push`（推近模糊）、`hwhip`（甩镜）、`white`（白闪）、`longwhite`（长白闪，产品登场）、`black`（黑场亮起）、`open`（开场）；
  - `ss`：从片段第几秒开始取；`frac`：本镜从这句的哪个比例开始（A/B 半镜用）；
  - `card`：贴卡 `{"img":"cards/xx.jpg","delay":0.15,"width":820}`，出现在画面上部；
  - `design`：设计字，只给 3–5 个重点，类型见下；
  - `arrow`：true 时加红色向下箭头；
  - `sfx`：自定义音效 `[{"file":"砰_拳击.wav","at":0.2,"gain":0.5}]`，文件取自素材包音效库。
- 设计字 `type`：`scale` 体重秤读数屏（`number`、`unit`）、`gold` 金色大数字加小签（`text`、`label`）、`coupon` 红色优惠券（`label`、`number`）、`timejump` 时间跳转标题（`title`、`subtitle`）。只写文案里有的字。
- `bgm`：`file` 音乐文件；`bar` 一小节多少秒；`drop` 爆点在音乐第几秒；`drop_shot` 爆点要对到哪个镜头（产品登场的镜头）。量不出 bar 和 drop 时可以只写 `file`，BGM 就从头铺到尾，不对爆点。

## 干货科普用的可选项（不写就是原来的带货效果）

顶层：

- `style`：`{"accent":[255,90,40], "highlight":["核心","腹肌"]}`，强调色，和字幕里要染成强调色的重点词。
- `lines_en`：英文句子，和 `lines` 一一对应，有就出中英双语字幕。
- `progress`：`{"total":6,"label":"ROUND"}`，配合镜头里的 `step` 显示进度条。
- `transition_scale`：转场速度倍率，默认 1.0；干货建议 1.8（单个转场约 0.35–0.4 秒）。

镜头里：

- `title`：钩子标题（只用在第一镜）。
- `step`：第几组/第几轮（显示进度条）。
- `numcard`：`{"text":"30","label":"秒 / 组","delay":0.4,"y":760}` 数字卡。
- `keywords`：`[{"text":"核心","at":0.6,"dur":1.3,"y":560,"sound":true}]` 关键词弹出；`sound` 写 false 就不配音效。

标题、数字卡、关键词出现时会自动配音效（咻、嘭），都来自音效库。

## 做了什么、没做什么

- 做了：每镜 6% 缓推、字幕只用一行（超长自动拆段）、转场和音效成对、说话时压低音效和 BGM、整体 -14 LUFS、导出 1080×1920 / H.264 约 4 Mbps。
- 没做：不画数字和小字（要用原图就放进 `cards/` 当贴卡）；不生成配音（见技能第 4 步）；不检查画面内容对不对，成片要你自己看。
- 单句配音重录：只重生成那一句，处理后覆盖 `vo/NN.wav`，更新 `dur.txt` 里那一行，重新运行 `render.py` 和 `mix.py`。

## 常见问题

- 提示找不到字体：安装 Noto Sans CJK SC（粗体），或设置环境变量 `FONT_PATH` 指向一个中文粗体字体文件。
- 提示音效文件不存在：确认素材包的 `音效库/` 在原位置，或设置环境变量 `PACK` 指向 `学员素材包` 文件夹。
- 画面偏软：H3 片段分辨率较低，放大到 1080×1920 会偏软，属正常。
- 质检：`ffmpeg -i 成片.mp4 -af ebur128 -f null -` 查响度，抽帧拼联系表看开头、转场和结尾，并逐句对字幕和配音。
