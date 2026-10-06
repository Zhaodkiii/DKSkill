# 生图提示词模板

每张图单独生成。根据正文内容替换变量，不要把多张图拼在一起。

```text
Generate one standalone 16:9 horizontal Chinese article illustration.

Visual DNA:
Pure white background. Clean rounded 2D animation character illustration. Lots of empty white space. Sparse handwritten Chinese annotations in red/orange/deep blue. Soft baby-blue color palette, gentle highlights, clean edges, friendly but not childish. No paper texture, no complex background, no commercial poster look, no PPT infographic look, no sticker sheet, no realistic UI.

Recurring IP character required:
小鲸, an anthropomorphic baby-blue whale character with a rounded body, white vertically-striped belly, blush cheeks, short rounded arms, short legs with cute feet, small tail fin, expressive friendly face, and a water spout on top of the head. 小鲸 must perform the core conceptual action, not decorate the scene.

IP recognition word:
喷泉. The water spout is the one-word identity anchor and must be visible in every image. Also keep the white belly stripes, short arms and legs, and tail fin.

IP appearance keywords:
小鲸 / 蓝鲸宝宝 / 喷泉 / 白肚纹 / 粉腮 / 短手短脚 / 尾鳍 / 圆润 / Q 弹 / 动画人物 / 清爽白底

Style keywords:
cute anthropomorphic blue whale character / rounded mascot character / baby-blue glossy body / white striped belly / water spout on head / blush cheeks / short arms and legs / small tail fin / clean 2D animation concept art / soft highlights / friendly expressive face

Theme:
{正文配图主题}

Structure type:
{结构类型：Workflow / 系统局部 / 前后对比 / 角色状态 / 概念隐喻 / 方法分层 / 地图路线 / 小漫画分镜}

Core idea:
{这张图要表达的核心意思}

Composition:
{具体画面：小鲸在哪里、正在做什么、喷泉如何参与识别或动作、主要物件是什么、信息如何流动}

Suggested elements:
{元素1} / {元素2} / {元素3} / {元素4}

Chinese handwritten labels:
{标注词1} / {标注词2} / {标注词3} / {标注词4} / {可选标注词5}

Color use:
Baby blue and light blue for 小鲸, water, feedback, and system state. White for background and belly. Deep blue for eyes, outlines, and short text. Orange for main flow/path/arrows. Red only for key warnings/problems/results. Pink only for blush or small emotional accents.

Negative prompt / 禁忌词:
小黑, black monster, black bean creature, shadow person, realistic whale, dolphin, shark, fish, seal, generic blue blob, missing water spout, missing striped belly, missing arms, missing legs, missing tail fin, crawling animal pose, sticker sheet, children's poster, cheap emoji, complex costume, realistic ocean animal texture, dark background, busy underwater scene, full model sheet, color palette chart, top-left title, PPT infographic, formal flowchart, dense architecture diagram, realistic app screenshot.

Constraints:
One image explains only one core structure. Keep the main subject around 40%-60% of the canvas. Preserve at least 35% blank white space. Use at most 5-8 short handwritten Chinese labels. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not make it a formal diagram, course slide, dense explainer, sticker pack, or character model sheet. Do not copy prior examples or reuse known case compositions unless explicitly requested; invent a fresh visual metaphor for this specific article. It should be clear but not instructional, friendly but not childish, polished but clean.
```

## 图像编辑提示

## 文章封面提示词补充

当用户要求生成文章封面时，在单张提示词开头明确替换为：

```text
Generate one standalone 3:4 vertical Chinese article cover.
```

封面仍沿用正文配图的 Visual DNA、Recurring IP character、IP recognition word、Color use 和 Negative prompt。封面可以更强调文章主题气质和第一眼识别，但不要做成商业海报、PPT 封面或复杂信息图。封面不计入正文配图数量；正文配图默认仍生成 2-5 张。

去掉左上角标题：

```text
Edit the provided image. Remove only the handwritten title "{要删除的文字}" and its underline from the top-left corner. Fill that area with the same clean white background, matching the surrounding blank paper. Preserve everything else exactly: characters, labels, paths, line style, composition, aspect ratio, and image quality. Do not add any new text or objects.
```

增强怪诞感：

```text
Regenerate this illustration with the same core meaning and simple layout, but make 小鲸 more central to the conceptual action. 小鲸 should be doing the work that explains the idea, not standing beside the diagram. Keep the water spout identity anchor visible, along with the white striped belly, short arms and legs, and tail fin. Keep it clean, sparse, rounded, and not childish.
```
