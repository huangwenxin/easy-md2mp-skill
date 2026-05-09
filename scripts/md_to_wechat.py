#!/usr/bin/env python3
"""
Markdown -> 微信公众号排版 HTML 转换器

功能：
1) 将 .md 转成微信友好的 HTML（内联样式）
2) 支持多主题批量输出
3) 生成可预览的 HTML 页面，包含一键复制富文本按钮
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Dict, List

import markdown
from bs4 import BeautifulSoup, Tag


FORBIDDEN_TAGS = {
    "script",
    "style",
    "iframe",
    "frame",
    "frameset",
    "form",
    "input",
    "textarea",
    "button",
    "select",
    "option",
    "canvas",
    "svg",
    "video",
    "audio",
    "object",
    "embed",
    "meta",
    "link",
}

REQUIRED_THEME_FIELDS = {
    "name",
    "font",
    "text",
    "muted",
    "primary",
    "border",
    "quote_bg",
    "code_bg",
    "code_text",
    "code_border",
    "code_dark_bg",
    "code_dark_text",
    "code_dark_border",
    "table_head_bg",
}


def load_themes(theme_file: Path) -> Dict[str, Dict[str, str]]:
    if not theme_file.exists():
        raise FileNotFoundError(f"主题文件不存在: {theme_file}")
    data = json.loads(theme_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("主题文件格式错误：顶层必须是非空对象")

    themes: Dict[str, Dict[str, str]] = {}
    for theme_key, theme_conf in data.items():
        if not isinstance(theme_conf, dict):
            raise ValueError(f"主题 `{theme_key}` 配置错误：必须是对象")
        missing = REQUIRED_THEME_FIELDS - set(theme_conf.keys())
        if missing:
            raise ValueError(
                f"主题 `{theme_key}` 缺少字段: {', '.join(sorted(missing))}"
            )
        themes[theme_key] = {k: str(v) for k, v in theme_conf.items()}

    return themes


THEME_FILE = Path(__file__).with_name("themes.json")
THEMES = load_themes(THEME_FILE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将 Markdown 转换为微信公众号排版 HTML，并生成预览页。"
    )
    parser.add_argument("-i", "--input", required=True, help="Markdown 文件路径")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./dist",
        help="输出目录（默认: ./dist）",
    )
    parser.add_argument(
        "-t",
        "--theme",
        default="all",
        choices=["all", *THEMES.keys()],
        help="主题名称，默认 all 输出全部主题",
    )
    parser.add_argument(
        "--code-mode",
        default="normal",
        choices=["normal", "night"],
        help="代码块模式：normal 或 night（默认 normal）",
    )
    parser.add_argument(
        "--mac-style",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="代码块是否显示 Mac 风格头部（默认开启）",
    )
    parser.add_argument("--title", default="", help="文章标题（可选）")
    return parser.parse_args()


def preprocess_markdown(md_text: str) -> str:
    # 将任务列表转为 emoji，避免微信过滤 checkbox/input
    text = re.sub(r"^(\s*[-*]\s*)\[(x|X)\]\s+", r"\1✅ ", md_text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*[-*]\s*)\[\s\]\s+", r"\1⬜ ", text, flags=re.MULTILINE)
    return text


def merge_style(tag: Tag, style: str) -> None:
    current = (tag.get("style") or "").strip()
    if current and not current.endswith(";"):
        current += ";"
    tag["style"] = f"{current}{style}"


def markdown_to_html(md_text: str) -> str:
    md = markdown.Markdown(
        extensions=[
            "extra",
            "fenced_code",
            "tables",
            "sane_lists",
            "nl2br",
        ]
    )
    return md.convert(preprocess_markdown(md_text))


def clean_html(html_fragment: str) -> BeautifulSoup:
    soup = BeautifulSoup(html_fragment, "html.parser")

    for tag_name in FORBIDDEN_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 清除事件属性和 JS URL
    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)
        for attr, value in attrs.items():
            if attr.lower().startswith("on"):
                del tag.attrs[attr]
                continue
            if isinstance(value, str) and "javascript:" in value.lower():
                tag.attrs[attr] = "#"

    return soup


def apply_wechat_inline_styles(
    soup: BeautifulSoup,
    theme: Dict[str, str],
    code_mode: str = "normal",
    mac_style: bool = True,
) -> None:
    article_style = (
        f"font-family:{theme['font']};"
        f"color:{theme['text']};"
        "font-size:16px;"
        "line-height:1.8;"
        "word-break:break-word;"
        "letter-spacing:0.2px;"
    )

    root = soup.new_tag("section")
    root["class"] = ["wechat-article"]
    root["style"] = article_style

    for node in list(soup.contents):
        root.append(node.extract())
    soup.append(root)

    block_map = {
        "p": f"margin:0 0 18px;color:{theme['text']};line-height:1.85;",
        "blockquote": (
            f"margin:18px 0;padding:12px 14px;"
            f"border-left:4px solid {theme['primary']};"
            f"background:{theme['quote_bg']};"
            f"color:{theme['muted']};border-radius:4px;"
        ),
        "ul": "margin:0 0 18px 22px;padding:0;line-height:1.85;",
        "ol": "margin:0 0 18px 22px;padding:0;line-height:1.85;",
        "li": "margin:6px 0;",
        "hr": f"border:none;border-top:1px solid {theme['border']};margin:24px 0;",
        "table": (
            f"border-collapse:collapse;width:100%;margin:18px 0;"
            f"font-size:14px;border:1px solid {theme['border']};"
        ),
        "thead": f"background:{theme['table_head_bg']};",
        "th": f"border:1px solid {theme['border']};padding:8px 10px;text-align:left;",
        "td": f"border:1px solid {theme['border']};padding:8px 10px;text-align:left;",
    }

    heading_map = {
        "h1": (
            f"margin:0 0 24px;padding-bottom:10px;font-size:30px;"
            f"line-height:1.4;color:{theme['text']};border-bottom:2px solid {theme['border']};"
        ),
        "h2": (
            f"margin:28px 0 14px;font-size:24px;line-height:1.5;color:{theme['text']};"
            f"padding-left:10px;border-left:4px solid {theme['primary']};"
        ),
        "h3": f"margin:24px 0 12px;font-size:20px;line-height:1.55;color:{theme['text']};",
        "h4": f"margin:20px 0 10px;font-size:18px;line-height:1.6;color:{theme['text']};",
        "h5": f"margin:18px 0 8px;font-size:16px;line-height:1.65;color:{theme['text']};",
        "h6": f"margin:16px 0 8px;font-size:15px;line-height:1.65;color:{theme['muted']};",
    }

    inline_map = {
        "a": f"color:{theme['primary']};text-decoration:none;border-bottom:1px solid {theme['primary']};",
        "strong": "font-weight:700;",
        "em": "font-style:italic;",
        "code": (
            f"font-family:'JetBrains Mono','Menlo','Consolas',monospace;"
            f"background:{theme['code_bg']};border-radius:4px;padding:2px 6px;font-size:0.92em;"
        ),
    }

    for tag, style in heading_map.items():
        for el in root.find_all(tag):
            merge_style(el, style)

    for tag, style in block_map.items():
        for el in root.find_all(tag):
            merge_style(el, style)

    for tag, style in inline_map.items():
        for el in root.find_all(tag):
            merge_style(el, style)

    for pre in root.find_all("pre"):
        pre["class"] = list(set([*pre.get("class", []), "hljs", "code__pre"]))

        is_night = code_mode == "night"
        code_bg = theme["code_dark_bg"] if is_night else theme["code_bg"]
        code_text = theme["code_dark_text"] if is_night else theme["code_text"]
        code_border = theme["code_dark_border"] if is_night else theme["code_border"]

        merge_style(
            pre,
            (
                "position:relative;"
                "margin:18px 0;"
                f"padding:{'0 10px 14px' if mac_style else '14px 16px'};"
                "overflow:hidden;"
                "border-radius:8px;"
                f"border:1px solid {code_border};"
                f"background:{code_bg};"
                f"color:{code_text};"
                "line-height:1.7;font-size:13px;"
            ),
        )

        # 代码块内 code 不再加过多内边距，避免双层 padding
        code = pre.find("code")
        if code:
            language = ""
            for cls in code.get("class", []):
                if cls.startswith("language-"):
                    language = cls.replace("language-", "")
                    break
            if language:
                pre["data-lang"] = language

            if not pre.find(class_="code-head"):
                code_head = soup.new_tag("span")
                code_head["class"] = ["code-head"]
                code_head["style"] = (
                    "display:flex;align-items:center;justify-content:space-between;"
                    "padding:10px 5px 0 2px;margin-bottom:8px;"
                )

                if mac_style:
                    mac_sign = soup.new_tag("span")
                    mac_sign["class"] = ["mac-sign"]
                    mac_sign["style"] = "display:flex;align-items:center;"
                    dot_colors = ["#ed6c60", "#f7c151", "#64c856"]
                    for color in dot_colors:
                        dot = soup.new_tag("span")
                        dot["class"] = ["mac-dot"]
                        dot["style"] = (
                            "display:inline-block;font-size:18px;line-height:1;"
                            f"color:{color};margin-right:5px;"
                        )
                        dot.string = "●"
                        mac_sign.append(dot)
                    code_head.append(mac_sign)

                if language:
                    lang = soup.new_tag("span")
                    lang["class"] = ["code-lang"]
                    lang["style"] = (
                        "font-size:12px;line-height:1;color:#9ca3af;"
                        "font-family:'JetBrains Mono','Menlo','Consolas',monospace;"
                        "text-transform:lowercase;letter-spacing:0.3px;"
                    )
                    lang.string = language
                    code_head.append(lang)

                pre.insert(0, code_head)

            code["style"] = (
                "font-family:'JetBrains Mono','Menlo','Consolas',monospace;"
                "background:transparent;padding:0;border-radius:0;display:block;"
                "overflow:auto;white-space:pre;"
                f"color:{code_text};"
            )

    for img in root.find_all("img"):
        src = (img.get("src") or "").strip()
        merge_style(
            img,
            "display:block;max-width:100%;height:auto;margin:20px auto;border-radius:8px;",
        )
        if src and not src.startswith(("http://", "https://", "data:")):
            # 微信编辑器无法直接使用本地图片路径
            img["data-local-src"] = src

    for a in root.find_all("a"):
        if "href" in a.attrs:
            a["target"] = "_blank"
            a["rel"] = "noopener noreferrer"

    # 移除空白无内容标签（保留 img/br/hr）
    keep_empty = {"img", "br", "hr"}
    for el in root.find_all(True):
        class_names = set(el.get("class", []))
        if {"code-head", "code-lang", "mac-sign", "mac-dot"} & class_names:
            continue
        if el.name in keep_empty:
            continue
        if not el.text.strip() and not el.find(True):
            el.decompose()


def render_theme_article(
    markdown_text: str,
    theme_key: str,
    code_mode: str = "normal",
    mac_style: bool = True,
) -> str:
    html_fragment = markdown_to_html(markdown_text)
    soup = clean_html(html_fragment)
    apply_wechat_inline_styles(
        soup,
        THEMES[theme_key],
        code_mode=code_mode,
        mac_style=mac_style,
    )
    return str(soup)


def build_preview_page(
    preview_theme_html_map: Dict[str, Dict[str, str]],
    title: str,
    source_file: str,
) -> str:
    theme_options = [
        {"key": k, "label": v["name"]}
        for k, v in THEMES.items()
        if k in preview_theme_html_map
    ]
    default_theme = theme_options[0]["key"]
    default_mode = "normal"

    escaped_title = html.escape(title) if title else "未命名文章"
    escaped_source = html.escape(source_file)

    card_html = []
    for option in theme_options:
        theme_key = option["key"]
        for mode in ("normal", "night"):
            mode_html = preview_theme_html_map.get(theme_key, {}).get(mode, "")
            visible = (
                "block"
                if theme_key == default_theme and mode == default_mode
                else "none"
            )
            active_cls = (
                "active"
                if theme_key == default_theme and mode == default_mode
                else ""
            )
            card_html.append(
                f'<section class="wechat-canvas {active_cls}" data-theme="{theme_key}" data-code-mode="{mode}" style="display:{visible};">'
                f'<article class="js-article">{mode_html}</article>'
                "</section>"
            )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escaped_title} - 微信预览</title>
  <style>
    :root {{
      --bg: #f3f6fb;
      --panel: #ffffff;
      --text: #101828;
      --muted: #667085;
      --brand: #0f766e;
      --border: #d0d5dd;
      --shadow: 0 12px 28px rgba(16, 24, 40, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
      background: radial-gradient(1200px 600px at 20% -10%, #e6f7ff 0%, transparent 65%), var(--bg);
      color: var(--text);
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 26px 18px 40px;
    }}
    .toolbar {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 14px;
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
      box-shadow: var(--shadow);
    }}
    .meta {{
      flex: 1 1 280px;
      min-width: 220px;
    }}
    .title {{
      font-size: 18px;
      font-weight: 700;
      margin: 0 0 6px;
    }}
    .sub {{
      font-size: 13px;
      color: var(--muted);
      margin: 0;
    }}
    select, button {{
      border: 1px solid var(--border);
      background: #fff;
      border-radius: 10px;
      font-size: 14px;
      padding: 10px 12px;
      cursor: pointer;
    }}
    button.primary {{
      background: var(--brand);
      color: #fff;
      border-color: var(--brand);
      font-weight: 600;
    }}
    .status {{
      color: var(--muted);
      font-size: 13px;
      min-height: 20px;
      margin-top: 8px;
    }}
    .preview-wrap {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}
    .phone {{
      width: 390px;
      max-width: 100%;
      margin: 0 auto;
      background: #0f172a;
      border-radius: 26px;
      padding: 12px;
      box-shadow: var(--shadow);
    }}
    .phone-screen {{
      background: #fff;
      border-radius: 18px;
      min-height: 620px;
      overflow: auto;
      padding: 22px 16px;
    }}
    .wechat-canvas article {{
      width: 100%;
    }}
    .phone-screen .hljs.code__pre > .mac-sign {{
      display: flex;
    }}
    .phone-screen h2 strong {{
      color: inherit !important;
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="toolbar">
      <div class="meta">
        <h1 class="title">{escaped_title}</h1>
        <p class="sub">来源：{escaped_source} · 复制后可直接粘贴到公众号编辑器</p>
        <p id="status" class="status">请选择主题后，点击“一键复制富文本”。</p>
      </div>
      <label>
        <select id="themeSelect">
          {"".join([f'<option value="{opt["key"]}">{opt["label"]}</option>' for opt in theme_options])}
        </select>
      </label>
      <label>
        <select id="codeModeSelect">
          <option value="normal">代码块亮色</option>
          <option value="night">代码块黑夜</option>
        </select>
      </label>
      <button id="copyBtn" class="primary">一键复制富文本</button>
      <button id="copyHtmlBtn">复制当前 HTML 源码</button>
    </div>

    <div class="preview-wrap">
      <div class="phone">
        <div class="phone-screen" id="screen">
          {"".join(card_html)}
        </div>
      </div>
    </div>
  </div>

  <script>
    const statusEl = document.getElementById('status');
    const themeSelect = document.getElementById('themeSelect');
    const codeModeSelect = document.getElementById('codeModeSelect');
    const copyBtn = document.getElementById('copyBtn');
    const copyHtmlBtn = document.getElementById('copyHtmlBtn');

    function setStatus(msg, isError = false) {{
      statusEl.textContent = msg;
      statusEl.style.color = isError ? '#b42318' : '#667085';
    }}

    function activeArticle() {{
      return document.querySelector('.wechat-canvas.active .js-article');
    }}

    function switchCanvas(theme, codeMode) {{
      const cards = document.querySelectorAll('.wechat-canvas');
      cards.forEach((card) => {{
        const isActive = card.getAttribute('data-theme') === theme
          && card.getAttribute('data-code-mode') === codeMode;
        card.style.display = isActive ? 'block' : 'none';
        card.classList.toggle('active', isActive);
      }});
      const themeName = themeSelect.options[themeSelect.selectedIndex].text;
      const modeName = codeMode === 'night' ? '黑夜' : '亮色';
      setStatus(`已切换主题：${{themeName}} · 代码块：${{modeName}}`);
    }}

    async function copyRichText() {{
      const article = activeArticle();
      if (!article) {{
        setStatus('未找到可复制内容', true);
        return;
      }}
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(article);
      selection.removeAllRanges();
      selection.addRange(range);
      let copied = false;
      try {{
        copied = document.execCommand('copy');
      }} catch (err) {{
        copied = false;
      }}
      selection.removeAllRanges();
      if (!copied && navigator.clipboard) {{
        try {{
          await navigator.clipboard.writeText(article.innerText || article.textContent || '');
          copied = true;
          setStatus('浏览器限制导致已降级为纯文本复制，可尝试在 Chrome 中使用富文本复制。');
          return;
        }} catch (err) {{
          setStatus('复制失败：请手动全选预览区复制。', true);
          return;
        }}
      }}
      setStatus(copied ? '复制成功，可直接粘贴到公众号编辑器。' : '复制失败，请手动复制。', !copied);
    }}

    async function copyHtmlSource() {{
      const article = activeArticle();
      if (!article) {{
        setStatus('未找到可复制内容', true);
        return;
      }}
      const htmlText = article.innerHTML;
      if (!navigator.clipboard) {{
        setStatus('当前浏览器不支持剪贴板 API', true);
        return;
      }}
      try {{
        await navigator.clipboard.writeText(htmlText);
        setStatus('当前主题 HTML 源码已复制。');
      }} catch (err) {{
        setStatus('复制 HTML 源码失败。', true);
      }}
    }}

    themeSelect.addEventListener('change', () => switchCanvas(themeSelect.value, codeModeSelect.value));
    codeModeSelect.addEventListener('change', () => switchCanvas(themeSelect.value, codeModeSelect.value));
    copyBtn.addEventListener('click', copyRichText);
    copyHtmlBtn.addEventListener('click', copyHtmlSource);
    switchCanvas(themeSelect.value, codeModeSelect.value);
  </script>
</body>
</html>
"""


def write_outputs(
    output_dir: Path,
    source_file: Path,
    title: str,
    theme_html_map: Dict[str, str],
    preview_theme_html_map: Dict[str, Dict[str, str]],
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = source_file.stem
    generated: List[Path] = []

    for key, article_html in theme_html_map.items():
        target = output_dir / f"{stem}.{key}.wechat.html"
        target.write_text(article_html, encoding="utf-8")
        generated.append(target)

    preview_html = build_preview_page(
        preview_theme_html_map,
        title=title,
        source_file=source_file.name,
    )
    preview_target = output_dir / f"{stem}.preview.html"
    preview_target.write_text(preview_html, encoding="utf-8")
    generated.append(preview_target)

    meta = {
        "source_markdown": str(source_file),
        "themes": list(theme_html_map.keys()),
        "preview": str(preview_target),
    }
    manifest = output_dir / f"{stem}.manifest.json"
    manifest.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    generated.append(manifest)
    return generated


def main() -> None:
    args = parse_args()
    src = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not src.exists():
        raise FileNotFoundError(f"Markdown 文件不存在: {src}")
    if src.suffix.lower() != ".md":
        raise ValueError("输入文件必须是 .md")

    markdown_text = src.read_text(encoding="utf-8")
    title = args.title.strip()
    if not title:
        title = src.stem

    themes = list(THEMES.keys()) if args.theme == "all" else [args.theme]
    theme_html_map = {
        theme: render_theme_article(
            markdown_text,
            theme,
            code_mode=args.code_mode,
            mac_style=args.mac_style,
        )
        for theme in themes
    }
    preview_theme_html_map = {
        theme: {
            "normal": render_theme_article(markdown_text, theme, "normal", args.mac_style),
            "night": render_theme_article(markdown_text, theme, "night", args.mac_style),
        }
        for theme in themes
    }

    generated = write_outputs(
        output_dir,
        src,
        title,
        theme_html_map,
        preview_theme_html_map,
    )
    print("生成完成：")
    for path in generated:
        print(f"- {path}")


if __name__ == "__main__":
    main()
