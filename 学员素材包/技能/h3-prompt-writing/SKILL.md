---
name: "h3-prompt-writing"
description: "Write MiniMax H3 (海螺 H3) video prompts in the official structured format for T2VA, I2VA, FL2VA, L2VA and full-reference Ref2VA; use when writing or rewriting H3 video prompts."
---

# H3 Prompt Writing（来源：MiniMax-AI/MiniMax-H3 官方 skills/h3-prompt-writing）

## Workflow
1. 先判断输入模式：T2VA（纯文字）、I2VA（首帧）、FL2VA（首尾帧）、L2VA（尾帧）、Ref2VA（多参考图/视频/音频，全参考）。
2. 前四种用「基础结构」；有多个参考素材（角色图、产品图、首帧等一起传）用「全参考结构」。
3. 严格保留字段名、段落顺序、标签和时间写法。
4. 描述正文用英文写；对白/歌词（`<d>`）和画面里真实出现的文字保留原语言。总时长必须和要求的视频时长（4–15 秒）一致。
5. 用具体的画面和声音细节，不用 “cinematic / beautiful” 这类空词。

## 一、基础结构（T2VA / I2VA / FL2VA / L2VA）

### 第一部分：对齐指令（T2VA 没有）
- I2VA 第一行固定：`For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`
- FL2VA：`How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.`
- L2VA：`How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.`
- N 是实际最后一镜编号，S.SS 是有效时长（保留两位小数）。指令放第一行，后面空一行。

### 第二部分：三个核心字段（按顺序）
```
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```
- integrated_multimodal_description：按时间线写画面、动作、镜头、说话人、对白、同期声。
- overall_soundscape：1–4 句英文，概括全片环境声、物理动作声、非语言人声（风、脚步、衣料摩擦、撞击、呼吸等）；对白和歌唱不重复写在这里；只有用户明确要求全程静音才写 N/A。
- non_diegetic_music：1–3 句，只有观众能听到的配乐，写乐器、速度、节奏、力度变化，不写抽象情绪词；没有配乐写 N/A。

### 时间线与镜头
- `[Shot 1]` 不加时间；之后 `[Shot 2] At 00:03.500, the camera cuts to ...`，切点严格递增且在时长内。
- 普通切镜用：the camera cuts to / the shot cuts to / transitions to / changes to / switches to；用户明确要求时才用 cross-dissolve / fade / wipe。
- 只需要改距离或小角度时优先用运镜而不是切镜。
- [Shot 1] 开头先写整体风格和起始构图（如 Live-action, 3D CG, claymation, 2D-animated；有首帧时风格从首帧推出）。
- 首帧（I2VA）：先写首帧里的风格、主体、构图、场景锚点，再写动作：首帧锚点 → 动作开始 → 持续发展 → 结果/反应。人物外观、服装、颜色、关键物体、空间关系保持一致。
- 首尾帧（FL2VA）：描述从首帧到尾帧的连续路径，通常一镜到底，最后一镜末尾落在尾帧。
- 尾帧（L2VA）：先推断合理的前序状态，再逐步收敛到尾帧；尾帧属于最后一镜。

### 运镜：类型 + 幅度 + 速度
类型：Zoom In/Out（变焦）、Push In/Pull Out（推/拉）、Pan Left/Right（摇）、Truck Left/Right（横移）、Tilt Up/Down、Pedestal Up/Down、Arc Shot（环绕）、Tracking Shot（跟拍）、Static Shot（固定）、Shake Slightly/Strongly、POV、Roll Clockwise/Counterclockwise。
幅度：with small amplitude / with large amplitude；速度：at slow speed / at fast speed（中等幅度、正常速度通常省略）。
写成自然英文动作，如：`The camera pushes in with small amplitude at slow speed toward the folded letter.` `The camera holds a static shot as the runner exits the frame.`

### 说话人、对白与歌唱
- 会说话/唱歌/画外音的主体用稳定 ID：(S1)(S2)，多人同时 (S1,S2)；不发声的角色不加 ID。
- 首次出现时给出足够的身份与声音信息（类型、年龄、性别、是否在画面内、音高、音色、语速、口音）。说话人描述、ID、动作、语气写在 `<d>` 外，`<d>` 内只放语言标签和用户给的原文：`<d>[English] ...</d>`，逐字保留，不翻译不改写。
- 画外音用固定短语 `says in an off-screen voiceover`，并在 `<d>` 后紧跟 `while his lips remain completely closed.`
- 同一句话跨切镜用 `<scenetrans>` 连接并说明声音延续；被视频结尾截断用 `<cutoff>`。
- 画面中真实出现的招牌/字幕/标签文字，用英文双引号包住，保持原文：`A red neon sign reading "营业中" glows above the doorway.`

## 二、全参考结构（Ref2VA）
六段按顺序输出：
1. `subject_definitions`：给每个需要单独追踪的参考内容定义标签，一行一个，写清标签指代什么、参考作用、要跟随的关键特征（来源图可在定义里指明）。
2. `summary`：一小段英文，开头方括号任务类型前缀，如 `[reference generation]`、`[keyframe completion]`、`[reference generation + audio reference]`；多个关系用 ` + ` 连接且不重复。可用类型：keyframe completion（图片作首帧/关键帧/尾帧）、reference generation（图/视频/音频只提供角色、场景、风格、动作、运镜等生成指导）、video editing、video continuation、audio reuse、audio reference。summary 里不引入新标签。
3. `retention_analysis`：每个标签一行，说明保留程度。可见内容用 fully_preserved / partially_preserved / attribute_transfer / weak_reference；音频用 fully_copy / partially_copy / reference / weak_reference。格式例：`<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - ...`；`<Picture 2> ([Shot 1] first frame): fully_preserved - ...`。
4. `detailed_description`：全参考的主体字段。先用一两句英文交代整体风格，再写 `[Shot 1]`、`[Shot 2] At MM:SS.mmm, ...`。要尽可能详细：每镜写清构图、主体外观与位置、环境与光线、动作与状态变化、运镜、同期声，以及参考内容在哪一刻出现/起作用。生成类任务通常 350–500 英文词。
5. `overall_soundscape`
6. `non_diegetic_music`

### 标签
- `<Subject N>`：从参考素材抽象出来、可复用的可见内容（人物、动物、物体、场景、服装、道具、风格、动作、表情等），是目标视频里实际使用的内容单元，不是文件本身；一个主体可以来自多个素材。
- `<Picture N>`：当参考图本身作为某一镜的首帧、关键帧、尾帧、编辑后的关键帧或构图锚点时单独定义；如果图只用来定义角色/场景/服装/风格，就写进对应的 Subject 定义里，不单独建 Picture。
- `<Video N>`：整段视频关系（编辑原视频、续写、参考其运镜/剪辑/节奏结构）；视频里复用的人物/物体仍然用 Subject。
- `<Audio N>`：独立音频素材或启用的视频音轨（复制、参考音乐风格、音色、对白、节奏等）；对应说话人时沿用其全局 (Sx)。
- 标签一旦指派，在六段里含义保持一致。
- 说话人：参考主体说话时同时保留标签和 ID：`<Subject 2> (S1) turns and says, <d>[English] ...</d>`；ID 按目标视频中实际发声事件顺序一次性分配，不要写在 retention_analysis 里。

### 例子（节选）
```
subject_definitions:
<Subject 1> is the coffee-shop environment in <Picture 1>, featuring an exposed brick wall and an orange tufted sofa.
<Subject 2> is the fluffy white Samoyed in <Picture 2>, with thick white fur and pointed ears.

summary:
[reference generation] The target video shows <Subject 3> eating a cookie in <Subject 1> while <Subject 2> lunges toward the cookie.

retention_analysis:
<Subject 1> (appears in [Shot 1]): fully_preserved - the brick wall and sofa are retained.
<Subject 2> (appears in [Shot 1]): fully_preserved - the Samoyed's fur, ears and tail are retained.

detailed_description:
The target video uses a realistic multi-camera sitcom style with warm indoor lighting.
[Shot 1] A medium shot establishes <Subject 1> ... <Subject 3> (S1) says, <d>[English] Hey! Watch your dog!</d> She closes her lips ...

overall_soundscape:
Soft indoor room tone continues throughout the scene.

non_diegetic_music:
N/A
```

## 三、给用户的工作台适配（小灰人带货等项目）
- 用户常用的是「首帧 + 角色母图 + 产品原图」一起传的参考生：用全参考结构。首帧用 `<Picture 1>`（[Shot 1] 的首帧），角色/产品作为 `<Subject N>`。
- 视频不生成人声：不写 `<d>`、不写说话人 ID；写明人物嘴巴闭合、不说话；配音由用户另外用 TTS 生成。
- 小灰人是无五官光滑脸的雕塑质感角色：必须在 retention_analysis 里强调保持无五官、体型、服饰、材质；产品瓶身字标和小字保持首帧原样，不改字、不新增文字。
- 默认固定镜头 + 轻微缓慢推近（Static Shot / Push In with small amplitude at slow speed）；动作从第 0 秒开始、幅度明显；结尾稳住，不循环。
- 一镜约 4.96 秒、单镜一条；时间标注与 4–15 秒的时长要求保持一致。
- 输出给用户时，每镜一个代码块，旁边用中文写镜号、对应旁白和要传的参考图顺序；对用户的说明用中文，提示词正文按本技能用英文。
- 写 H3 提示词时严格按本技能的要求（全能参考结构、细节程度）写，不要自己另编宽松格式。H3 出片由用户自己完成，出片方式、地址、参数不用管，只负责把提示词写好交给用户。