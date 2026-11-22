# 墨线健身 · 渲染模板

横屏 1920×1080、30fps。你只要准备人物图、逐句配音和 `project.json`，用两条命令出片。需要：Python 3、ffmpeg、numpy、Pillow、scipy、中文粗体字体（Noto Sans CJK SC Black；找不到时设环境变量 `FONT_PATH`）。

## 先自检
```
python3 selftest.py
```
它会自己生成示例人物图、配音和音乐，跑一遍渲染和混音。看到「自检通过」才往下；报错就把提示发给 Claude。（`PACK` 环境变量指向学员素材包位置；不设就用本文件往上三级的文件夹。）

## 项目文件夹
```
我的项目/
  project.json        台词、镜头、元素（见 风格/墨线健身/风格说明.md）
  imgs/               你自己 IP 的人物图（黑底墨线 PNG/JPG，或透明底 PNG）
  vo/01.wav 02.wav…   逐句配音（裁掉两端静音），vo/dur.txt 每行「句号 秒数」
  bgm/bgm.mp3         可选，自己有授权的音乐
```

## 出片
```
python3 render.py 我的项目 --dur vo/dur.txt     # 画面：out/video_noaudio.mp4 + out/marks.json
python3 mix.py 我的项目 成片_v1.mp4            # 配音 + 音效 + BGM + -14 LUFS，合成成片
python3 render.py 我的项目 --quick S02,S03      # 只渲染指定镜头，快速看效果
```
先出前 30 秒样片（`--quick`）确认风格，再渲染全片。渲染较慢时分两次跑：先 `--quick` 渲染前半镜头确认，再整片。

## 注意
- 人物图固定画在画面左侧约 3/4 区域，右侧留给标签列、特写章和记忆组件。
- 字幕按子句切换，子句时间按字数比例分配；你有真实的子句时间码时，把 `render.py` 里的 `clause_times` 换成读你的 `segs.json`。
- 这是学员版精简引擎：没有粒子、冲击波、光扫等复杂特效。要更多特效，让 Claude 在 `render.py` 里按需加。
