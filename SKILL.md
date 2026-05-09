---
name: easy-md2mp
description: 将 Markdown 一键转换为微信公众号可粘贴排版（多主题、代码块亮色/黑夜、Mac 风格代码头、预览页一键复制）。当用户提到“公众号排版”“md 转公众号”“生成可复制到微信公众号编辑器的 html”“需要预览页和复制按钮”“修复公众号粘贴样式丢失”时，务必优先使用本技能。
---

# 公众号快捷排版（easy-md2mp）

> 本技能是给不同智能体安装调用的通用技能文档。  
> 执行时禁止写死某一台机器的绝对路径，必须先在当前环境中定位脚本与主题文件，再运行命令。

## 技能目标
把用户的 `.md` 文件转换为微信公众号友好的 HTML 排版，并生成本地预览页，支持：

- 多主题样式
- 代码块 `normal/night` 模式
- Mac 风格代码头（三色圆点 + 语言标签）
- 预览页一键复制富文本

## 适用场景
- 用户有 Markdown 草稿，想快速发布到公众号
- 用户要求“可直接粘贴到公众号编辑器”的排版
- 用户要求“预览页 + 一键复制”
- 用户反馈粘贴到公众号后样式丢失，需要提高兼容

## 执行前检查
1. 优先使用技能内置脚本：`<skill_root>/scripts/md_to_wechat.py`。
2. 确认同目录存在：`<skill_root>/scripts/themes.json` 与 `requirements.txt`。
3. 仅当内置脚本缺失时，才回退到工作区里的同名脚本。
4. 如首次运行，先安装依赖：

```bash
python3 -m pip install -r <skill_root>/scripts/requirements.txt
```

## 标准执行流程
1. 询问或确认输入 Markdown 路径（`.md`）。
2. 询问输出目录（默认可用 `<workspace>/out`）。
3. 执行转换命令（优先全主题）：

```bash
python3 <skill_root>/scripts/md_to_wechat.py \
  --input <markdown_path> \
  --output-dir <output_dir> \
  --theme all \
  --code-mode night \
  --mac-style \
  --title "<文章标题>"
```

4. 返回生成产物路径，重点给出 `*.preview.html`。
5. 提醒用户在预览页中切主题、切代码块模式后点击“一键复制富文本”。

## 路径约定（面向通用智能体）
- `<skill_root>`：当前技能目录（包含 `SKILL.md`）。
- `<markdown_path>`：用户输入 Markdown 绝对路径。
- `<output_dir>`：输出目录，推荐 `<workspace>/out` 或用户指定目录。
- 不要假设操作系统、用户名、磁盘目录结构固定。

## 参数决策规则
- `--theme`
  - 追求对比试样：用 `all`
  - 用户指定风格：用单主题，如 `minimal`
- `--code-mode`
  - 技术文档默认 `night`
  - 偏阅读类可选 `normal`
- `--mac-style`
  - 默认开启
  - 用户不需要代码头时用 `--no-mac-style`

## 输出规范
完成后必须明确给出：
- 主题 HTML 文件列表：`*.{theme}.wechat.html`
- 预览页：`*.preview.html`
- 清单文件：`*.manifest.json`
- 建议下一步：打开预览页 -> 复制 -> 粘贴公众号编辑器

## 智能体调用约束
- 优先保证“可运行”和“可复制到公众号”两件事。
- 如用户未指定主题，默认 `--theme all`。
- 如用户未指定代码模式，技术文默认 `--code-mode night`。
- 若执行失败，先回传报错摘要，再给出最小修复步骤，不要沉默重试过多次。

## 公众号兼容关键点
- 代码头中的三色圆点与语言标签使用真实节点（非伪元素），提升粘贴保留率。
- 图片若是本地路径，公众号通常无法直接加载，需上传后替换 URL。
- 若用户粘贴后样式缺失，优先建议使用 Chrome 复制，并从预览页复制“内容区域”。

## 故障排查
参考：`references/troubleshooting.md`

## 一键自测
可使用技能自带示例文件快速验证安装是否正常：

```bash
python3 <skill_root>/scripts/md_to_wechat.py \
  --input <skill_root>/assets/example.md \
  --output-dir <workspace>/out \
  --theme all \
  --code-mode night \
  --mac-style \
  --title "easy-md2mp 自测"
```

预期输出：
- `<workspace>/out/example.preview.html`
- `<workspace>/out/example.<theme>.wechat.html`
