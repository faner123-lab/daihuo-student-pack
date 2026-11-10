---
name: "h3-quanneng-cankao-zhongtu-chuxian"
description: "写 H3 全能参考（Ref2VA）提示词，让首帧里没有的产品/道具在镜头中途出现（如罐子从下方被抓起、从画外飞入）。带货视频产品后出场时用。"
---

# H3 全能参考：产品/道具“中途出现”

用法：带货视频里产品不在一开始的场景中，后面才出现。这时不要让 Codex 把产品画进首帧或尾帧，而是用 H3 全能参考把产品当“参考主体”传进去，在镜头进行中让它出现。写提示词时先按 h3-prompt-writing 的全参考六段结构，再按本技能的规则。

## 什么时候用
- 产品/盒子/罐子/药片在镜头前半段不存在，后半段从下方、侧面、画外、高处、金光里出现。
- 前后相邻的“憋/想 → 看到 → 抓起 → 抛/亮出”这类连续动作，合并成一条较长的镜头、一镜多动作，不要拆成多段硬切。
- 产品不在首帧里：默认镜头用普通首帧/首尾帧，只有“中途出现”这一段才用全能参考。

## 参考图怎么传（少而精）
1. 首帧（不含产品）：<Picture 1>。
2. 角色母图：标成 <Subject 1>。
3. 产品透明底抠图（以用户产品原图为准）：标成 <Subject 2>。
4. 最多再加一张真实药片/胶囊照片（只管颜色形状）。
- 不要堆参考图；不让 Codex 为这一段出关键帧、尾帧（尾帧里带产品的图不用）。
- 没有干净的透明底产品抠图时，先让 Codex 出一张（只写“透明背景”，不教方法）。

## 提示词写法（Ref2VA 六段，英文正文）
1. subject_definitions：定义 <Picture 1>（首帧）、<Subject 1>（人物）、<Subject 2>（产品）。在 Subject 2 的定义里写明：**它不在 Picture 1 里，镜头中途才首次出现**。
2. summary：方括号前缀用 [keyframe completion + reference generation]，一句话说清从首帧开始、产品从哪里出现。
3. retention_analysis：Picture 1 用 fully_preserved（场景、姿态、脸色）；Subject 1 用 fully_preserved（脸、发型、身材、衣服）；Subject 2 用 fully_preserved，写清“从约 X 秒起出现”、形状/颜色/包装布局/印刷文字保持参考原样，不改字、不新增文字。
4. detailed_description：一个 [Shot 1] 写完，按秒写清情绪/动作变化，和“产品在第几秒、从哪里、怎么出现”（例：右臂伸到画面下缘之外，把罐子从下方举进画面，带轻微金光和飘动的小叶子）。约 350–500 英文词。
5. overall_soundscape：同期声（呼吸、衣料、轻微“叨”声、飞过的 whoosh）；视频里的音效最终以用户音效库的真音效在剪辑里混入。
6. non_diegetic_music：N/A。

## 固定要点
- 不生成人声：不写 <d>、不写说话人 ID；写明人物从不说话、嘴巴闭合（或只是无声倒吸一口气）。
- 无字幕、文字、水印、BGM。
- 默认运镜：慢速小幅推近，抛出之后稳住；动作从第 0 秒就开始，幅度明显。
- 首帧里没有的东西，在提示词里只用于“产品”这一个主体，不额外加道具。
- H3 最短 4 秒、最长 15 秒；设计里不到 4 秒的段落，先出足时长，在剪辑里加速或截取。
- H3 画不准包装文字，产品飞向镜头如果糊或有字误，在剪辑里用产品原图叠加校正，在白闪处接后半。
- 输出给用户：每条一个代码块，旁边用中文写要传的参考图顺序、H3 时长、剪辑里用多少；不写任何出片方式或参数。

## 参考模板（罐子从下方被抓起、抛向镜头，6 秒）
```
subject_definitions:
<Picture 1> is the first frame of the target video: [首帧场景和人物姿态].
<Subject 1> is [人物外貌、发型、衣服] in the character reference image.
<Subject 2> is [产品外形、颜色、标签] in the product reference image. It does not exist in Picture 1 and first appears mid-shot.

summary:
[keyframe completion + reference generation] The target video starts from <Picture 1> ... then <Subject 2> appears from below the frame when he grabs it, and he throws it at the camera.

retention_analysis:
<Picture 1> ([Shot 1] first frame): fully_preserved - ...
<Subject 1> (appears in [Shot 1]): fully_preserved - ...
<Subject 2> (appears in [Shot 1] from about 3.20 seconds): fully_preserved - shape, colors, label layout and printed text stay exactly as in the reference with no new or altered text.

detailed_description:
[风格一句话]
[Shot 1] [起始构图=Picture 1] ... From 0.00 to 1.60 seconds [情绪/动作] ... At 3.20 seconds his right arm reaches down past the bottom edge of the frame and lifts <Subject 2> up into view ... At 4.50 seconds he throws it toward the camera ... ends in a bright white flash at 6.00 seconds. The camera pushes in with small amplitude at slow speed until the throw, then holds static. The man never speaks and his lips stay closed.

overall_soundscape:
...

non_diegetic_music:
N/A
```