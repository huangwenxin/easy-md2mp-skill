# easy-md2mp 排障手册

## 1) 公众号里看不到红黄绿圆点
- 确认使用的是最新脚本版本（代码头为真实 `span` 节点，不依赖伪元素）。
- 重新生成输出后再复制，不要复用旧 preview 文件。
- 优先在 Chrome 中打开 `*.preview.html` 后复制。

## 2) 公众号里看不到代码语言标签
- 语言标签应是代码头右侧真实文本节点（如 `python`）。
- 若代码块未标语言（``` 后没写语言），标签可能为空。

## 3) 代码块头部跟着横向滚动
- 当前逻辑应为“头部固定、代码区滚动”：
  - `pre`: `overflow:hidden`
  - `code`: `overflow:auto; white-space:pre`
- 若未生效，请确认不是旧文件。

## 4) 本地图片粘贴后不显示
- 公众号编辑器通常不能直接使用本地路径。
- 解决方式：先上传图床或微信图片接口，再替换为公网 URL。

## 5) 命令模板

```bash
python3 /Users/xin/1code/公众号/script/md_to_wechat.py \
  --input <markdown_path> \
  --output-dir /Users/xin/1code/公众号/script/out \
  --theme all \
  --code-mode night \
  --mac-style \
  --title "<文章标题>"
```

