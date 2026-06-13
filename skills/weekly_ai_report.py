import os
import json
import glob
import urllib.request
import urllib.error
from datetime import datetime

# 自动加载 .env 文件中的环境变量（优先级低于系统已设的环境变量）
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _val = _line.split('=', 1)
                if _key.strip() not in os.environ:
                    os.environ[_key.strip()] = _val.strip()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
CAREER_FRAMEWORK = os.path.join(os.path.dirname(__file__), "career_framework.md")

def read_template() -> str:
    template_path = os.path.join(os.path.dirname(__file__), 'report_template.md')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

def read_career_framework() -> str:
    try:
        with open(CAREER_FRAMEWORK, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ""

def generate_report_content() -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    template = read_template()
    career_fw = read_career_framework()

    prompt = f"""
今天是 {current_date}。你是一名在同花顺（金融科技公司）移动互联网事业部工作的数据分析师，主要职责是移动端新用户增长分析与平台商业分析。

请撰写本周的《AI与数据驱动周报》。受众是你的同事（数据分析师和产品运营）。

【内容约束】
1. 只写本周（{current_date}所在周）真实发生的行业动态。不确定或无法核实的消息不要写。
2. 每条新闻必须回答三个问题：发生了什么、为什么重要、对我有什么启发。
3. 禁止使用"赋能""降维打击""破局""闭环""抓手""底层逻辑""颗粒度""组合拳"等套话。用日常中文写。
4. 每段不超过5句话。信息密度优先，不写大家都知道的基础概念。
5. 涉及产品名、厂商名、数据指标时必须具体，不能泛泛而谈。

【大厂社招分析部分特别要求】
6. 第三部分必须基于2026年6月前后字节跳动、淘天集团、阿里国际、小红书、腾讯的真实或高度可信的社招动态，分析数据类、策略产品类、AI产品类、运营类岗位的JD趋势。
7. 必须覆盖至少2家公司的具体岗位需求，给出核心技能的变化方向。
8. 差距分析必须与用户的当前岗位（新用户数据分析师 / 平台商业分析师）对齐，给出可操作的提升建议。

【技能精进部分特别要求】
9. 第四部分推荐的技能方向应是高阶方向，排除基础 SQL（SQL已是基线能力，不应出现）。建议方向：因果推断方法（DID/RDD/IV）、AB实验设计与MDE计算、Python数据管道自动化、LLM在数据分析工作流中的应用、推荐系统理解、时间序列异常检测、数据产品设计。
10. 学习路径必须具体：给出一篇可检索的文章标题或关键词、一个能在一周内完成的练习、一个在当前数据分析工作中直接可用的场景。

【职业发展参考框架】
以下是用户的稳定职业发展框架（不要在每个周报中大幅改动此框架，只可在第三部分做细微调整）：
{career_fw}

【排版要求】
必须严格遵循以下 Markdown 模板结构（保持层级关系，禁止新增或合并章节，禁止添加 emoji，禁止使用 *斜体* 标记）：

{template}

【最终自查】
- 是否有具体产品名、具体数据指标、具体方法论？如果没有，请补充。
- 每一条是否都能让读者在周一晨会上有新的观点可以分享？如果没有，请重写。
- 第三部分的岗位分析是否具体到了公司和岗位方向？如果没有，请补充。
"""

    api_key = os.getenv("OPENAI_API_KEY")
    print("正在连接 Kimi 撰写深度行业报告 (预计 60-90 秒)...")
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    data = {"model": os.getenv("DEFAULT_MODEL", "moonshot-v1-32k"), "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=180) as res:
            return json.loads(res.read().decode('utf-8'))["choices"][0]["message"]["content"].replace("{current_date}", current_date)
    except Exception as e:
        print(f"Kimi API 调用失败: {e}")
        return ""

def markdown_to_html(md: str) -> str:
    import re

    lines = md.split('\n')
    html = []
    in_list = False
    in_ordered_list = False
    in_quote = False

    def close_lists():
        nonlocal in_list, in_ordered_list
        if in_list:
            html.append('</ul>')
            in_list = False
        if in_ordered_list:
            html.append('</ol>')
            in_ordered_list = False

    def close_quote():
        nonlocal in_quote
        if in_quote:
            html.append('</blockquote>')
            in_quote = False

    def inline(text: str) -> str:
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = text.replace('*', '')
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', text)
        return text

    for line in lines:
        stripped = line.strip()

        if not stripped:
            close_lists()
            close_quote()
            continue

        if stripped == '---':
            close_lists()
            close_quote()
            html.append('<hr>')
            continue

        if stripped.startswith('# '):
            close_lists()
            close_quote()
            html.append(f'<h1>{inline(stripped[2:])}</h1>')
        elif stripped.startswith('## '):
            close_lists()
            close_quote()
            html.append(f'<h2>{inline(stripped[3:])}</h2>')
        elif stripped.startswith('### '):
            close_lists()
            close_quote()
            html.append(f'<h3>{inline(stripped[4:])}</h3>')
        elif stripped.startswith('> '):
            close_lists()
            if not in_quote:
                html.append('<blockquote>')
                in_quote = True
            html.append(f'<p>{inline(stripped[2:])}</p>')
        elif stripped.startswith('- ') or stripped.startswith('* '):
            close_quote()
            if not in_list:
                html.append('<ul>')
                in_list = True
            html.append(f'<li>{inline(stripped[2:])}</li>')
        elif stripped[0].isdigit() and '. ' in stripped[:4]:
            close_quote()
            if not in_ordered_list:
                html.append('<ol>')
                in_ordered_list = True
            dot_idx = stripped.index('. ')
            html.append(f'<li>{inline(stripped[dot_idx+2:])}</li>')
        else:
            close_lists()
            close_quote()
            html.append(f'<p>{inline(stripped)}</p>')

    close_lists()
    close_quote()
    return '\n'.join(html)

def scan_history() -> list:
    """扫描 output 目录，返回历史报告列表（按日期倒序）。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pattern = os.path.join(OUTPUT_DIR, "AI与数据驱动周报_*.html")
    files = sorted(glob.glob(pattern), reverse=True)
    history = []
    for f in files:
        basename = os.path.basename(f)
        # 提取日期部分
        date_str = basename.replace("AI与数据驱动周报_", "").replace(".html", "")
        history.append({"date": date_str, "filename": basename, "path": f})
    return history

def build_sidebar_html(history: list, current_date: str) -> str:
    """生成侧边栏 HTML。"""
    items = []
    for h in history:
        active = ' active' if h["date"] == current_date else ''
        items.append(f'      <a href="{h["filename"]}" class="history-link{active}">'
                     f'<span class="history-date">{h["date"]}</span></a>')
    return '\n'.join(items) if items else '<p style="color:var(--muted);font-size:0.8rem;padding:0 12px;">暂无历史报告</p>'

def build_html_page(body_html: str, current_date: str) -> str:
    history = scan_history()
    sidebar = build_sidebar_html(history, current_date)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI与数据驱动周报 ({current_date})</title>
<style>
  :root {{
    --bg: #faf8f5;
    --card: #ffffff;
    --text: #1a1a1a;
    --muted: #8c8c8c;
    --border: #e8e4dc;
    --accent: #b8753e;
    --accent-dim: #e8d5c4;
    --sidebar-w: 220px;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: "Songti SC", "Noto Serif SC", "Source Han Serif SC", "SimSun", "STSong", Georgia, serif;
    font-size: 16px;
    line-height: 1.8;
    color: var(--text);
    background: var(--bg);
    display: flex;
    min-height: 100vh;
  }}

  /* ---- 侧边栏 ---- */
  .sidebar {{
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: var(--sidebar-w);
    background: #f5f1eb;
    border-right: 1px solid var(--border);
    padding: 48px 0 32px;
    overflow-y: auto;
    z-index: 10;
  }}
  .sidebar-title {{
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
    padding: 0 24px 24px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  }}
  .history-link {{
    display: block;
    padding: 6px 24px;
    font-size: 0.8rem;
    color: var(--muted);
    text-decoration: none;
    transition: all 0.15s;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  }}
  .history-link:hover {{
    color: var(--text);
    background: var(--bg);
  }}
  .history-link.active {{
    color: var(--accent);
    font-weight: 600;
    background: var(--bg);
    border-right: 2px solid var(--accent);
  }}
  .history-date {{
    letter-spacing: 0.02em;
  }}

  /* ---- 主内容 ---- */
  .main {{
    margin-left: var(--sidebar-w);
    flex: 1;
    max-width: 760px;
    padding: 64px 64px 96px;
  }}

  h1 {{
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    line-height: 1.25;
    margin: 0 0 8px 0;
  }}
  h2 {{
    font-size: 1.25rem;
    font-weight: 700;
    margin: 56px 0 20px 0;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    letter-spacing: -0.005em;
  }}
  h3 {{
    font-size: 1rem;
    font-weight: 700;
    margin: 36px 0 12px 0;
    color: #2c2c2c;
  }}
  p {{
    margin: 0 0 14px 0;
  }}

  blockquote {{
    margin: 20px 0;
    padding: 14px 20px;
    background: #fdfaf5;
    border-left: 3px solid var(--accent);
    border-radius: 0 4px 4px 0;
    color: #4a4035;
  }}
  blockquote p {{ margin: 4px 0; }}

  ul, ol {{
    margin: 10px 0 20px 0;
    padding-left: 22px;
  }}
  li {{
    margin: 8px 0;
  }}
  li strong:first-child {{
    color: #111;
  }}

  hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 40px 0;
  }}

  a {{
    color: var(--accent);
    text-decoration: none;
    border-bottom: 1px solid var(--accent-dim);
    transition: border-color 0.15s;
  }}
  a:hover {{ border-bottom-color: var(--accent); }}

  strong {{ color: #111; font-weight: 700; }}


  .report-meta {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-bottom: 40px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  }}
  .report-footer {{
    margin-top: 56px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.75rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    letter-spacing: 0.02em;
  }}

  .career-note {{
    margin-top: 28px;
    padding: 16px 20px;
    background: #fdfaf5;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 0.85rem;
    color: var(--muted);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  }}
  .career-note a {{
    font-weight: 600;
  }}

  @media (max-width: 800px) {{
    .sidebar {{ display: none; }}
    .main {{
      margin-left: 0;
      padding: 40px 24px 64px;
      max-width: 100%;
    }}
    h1 {{ font-size: 1.5rem; }}
  }}
</style>
</head>
<body>

<aside class="sidebar">
  <div class="sidebar-title">历史周报</div>
{sidebar}
</aside>

<main class="main">
<h1>AI与数据驱动周报</h1>
<p class="report-meta">{current_date} · 由 Kimi (Moonshot-v1-32k) 自动生成</p>
{body_html}
<p class="report-footer">OpenClaw Agent · AI与数据驱动周报</p>
</main>

</body>
</html>'''

def save_report(content: str) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    filename = f"AI与数据驱动周报_{current_date}.html"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    body_html = markdown_to_html(content)
    full_html = build_html_page(body_html, current_date)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_html)

    # 同时写一份 index.html 到仓库根目录，用于 GitHub Pages 固定链接
    index_path = os.path.join(REPO_ROOT, "index.html")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f"报告已保存: {filepath}")
    print(f"首页已更新: {index_path}")
    return filepath

def push_to_feishu_group(report_path: str):
    url = os.getenv("FEISHU_WEBHOOK")
    if not url:
        return
    print("正在发送群聊通知...")
    payload = {
        "msg_type": "text",
        "content": {"text": f"本周 AI 与数据驱动周报已生成，请查收本地文件：\n{report_path}"}
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}, method='POST')
    try:
        urllib.request.urlopen(req, timeout=30)
        print("群聊通知发送成功！")
    except: pass

if __name__ == "__main__":
    print("\n====== AI与数据驱动周报 生成任务启动 ======")
    report_content = generate_report_content()
    if report_content:
        filepath = save_report(report_content)
        push_to_feishu_group(filepath)
    print("====== 任务流结束 ======\n")
