import os
import json
import glob
import ssl
import urllib.request
import urllib.error
from datetime import datetime

# 公司网络 SSL 代理证书绕过（个人脚本，仅本地运行）
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

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
今天是 {current_date}。你正在为一位具体的同事撰写个性化的《AI与数据驱动周报》。请仔细阅读以下用户画像，让报告对这个人有真实价值。

【用户画像】
- 当前岗位：同花顺移动互联网事业部 · 平台新用户数据分析师（刚入职，校招生）
- 当前工作：承接平台新用户运营的数据需求，日常与运营团队协作。未来的核心 KPI 是两方面——扩大平台新用户规模，以及提升新用户的后续转化（开户、购买云软件产品），从而驱动收入增长
- 技术背景：安徽大学金融数学本科 + 上海财经大学金融硕士（计量方向）。SQL 熟练，Python 不熟练。统计学和计量经济学基础扎实，已掌握 DID（双重差分法）的基本应用。对机器学习停留在了解监督/无监督学习概念的层面，对大模型只会使用、不懂原理。随机过程、实变函数等纯数方向基础较弱
- 职业目标：未来希望进入纯互联网行业（字节跳动、小红书、阿里系、美团、腾讯等），关注数据类、策略产品类、AI产品类岗位
- 阅读习惯：希望早上能花 5 分钟快速扫到关键信息，也愿意周末花 30 分钟精读有深度的部分。信息密度比字数更重要

【能力发展策略——请在所有分析和建议中贯彻】
用户的能力成长遵循两层结构：
1. 核心壁垒层（不可替代性）：因果推断方法论。他的计量硕士背景是大多数 DA 不具备的稀缺优势。DID 已有基础，下一步推进到 RDD、IV、合成控制法。这是他真正的护城河——当 AI 把"取数+做表"的成本降到零以后，能设计识别策略、验证因果效应、推动业务决策的 DA 不会被替代。
2. 效率放大层（工具杠杆）：用 AI 武装工作流。比如用 AI 写 SQL、做数据清洗、生成分析报告初稿。AI 负责执行速度，他负责判断方向和方法。同时要系统性提升 Python 实操能力（pandas → statsmodels → DoWhy），方法论的深度必须配上工具的熟练度才能真正落地。
两层都要推进，但优先级不同——核心壁垒层的投入产出比更高，尤其在职业早期。

【内容约束】
1. 只写本周（{current_date}所在周）真实发生的行业动态。不确定或无法核实的消息不要写，宁可少写一条也不编造。
2. 涉及非公开的具体数据指标时（如"DAU提升22%"），必须标注来源（哪个媒体的报道、哪家公司的官方发布）或清楚说明"基于公开报道推算"。
3. 禁止使用"赋能""降维打击""破局""闭环""抓手""底层逻辑""颗粒度""组合拳"等套话。用日常中文写。
4. 每段不超过5句话。信息密度优先，不写大家都知道的基础概念。
5. 每条分析必须与用户画像关联——这对一个同花顺新用户 DA 意味着什么？他应该做什么？不要写放之四海而皆准的废话。

【各部分特别要求】

第一部分（C端AI产品落地观察）：
- 必须聚焦可以直接映射到"平台新用户增长与转化"的 AI 产品动态
- 分析时要落到：这个趋势对同花顺的新用户拉新、激活、留存、付费转化意味着什么

第二部分（互联网行业数据与AI动态）：
- 2.1 的标杆案例必须是字节/淘天/小红书/美团/腾讯中有据可查的数据实践，不是杜撰的
- 2.2 的 AI 基础设施必须覆盖本周实际的模型发布/开源动态/API 更新/监管政策，有具体版本的写版本号

第三部分（大厂社招岗位洞察）：
- 必须具体到公司名+岗位方向+有据可查的 JD 要求。至少覆盖 2 家公司
- 差距分析必须诚实面对用户的实际情况：他刚入职，Python 不熟，DID 是主要方法论工具，对 ML/LLM 理解较浅——在这样的起点上，要往目标岗位走，最优先补什么
- 要利用好他的优势：计量经济学背景在大多数 DA 中是稀缺的，他应该在因果推断这条线上继续深耕，而不是分散精力去学基础 Python 或 SQL

第四部分（本周技能精进）：
- 推荐的技能应建在他的已有基础上。他有 DID 基础+计量背景，下一步可以是 RDD（断点回归）、IV（工具变量）、合成控制法（SCM）等因果推断的进阶方法，也可以是 Python 在因果推断中的实操（statsmodels/DoWhy），或是 AB 实验中的 MDE 计算和分流设计
- 4.1 的大白话解释要举同花顺场景的例子——比如用 RDD 分析用户等级升级对活跃度的影响、用 IV 分析 push 频次对留存的因果效应
- 4.2 的真实用例必须给出公司名+场景+效果+来源
- 4.3 的学习路径必须具体到可检索的文章/课程标题、可下载的数据集、在同花顺工作中的真实应用场景

【职业发展参考框架】
{career_fw}

【篇幅要求】
每部分至少 1200 字，整份报告 8000-12000 字。深度展开每个案例的完整背景、数据细节和推导过程，每条 JD 分析要拆解具体岗位的核心能力要求和面试要点，方法论解释要配真实分析案例。

【链接原则——严格遵守】
- 可以链接到论文 DOI（如 https://doi.org/10.1257/xxx），这比链接到期刊主页更可靠
- 推荐书籍时只写《书名》第X章，不要编造不存在的书籍
- GitHub 仓库或在线教程只链接主流知名资源（如 "Causal Inference for the Brave and True"），不要链接你可能记错的小众博客或个人页面
- 绝不要编造任何链接。无法确认链接有效时，改用"搜索关键词：XXX"

【排版要求】
必须严格遵循以下 Markdown 模板结构（保持层级关系，禁止新增或合并章节，禁止添加 emoji，禁止使用 *斜体* 标记）：

{template}

【最终自查——请逐条确认】
- 读完第一部分，一个同花顺新用户 DA 能不能在周一晨会上提出一个具体的观点？如果没有，重写
- 第二部分有没有可检索验证的具体信息（产品名、版本号、政策文件标题）？如果没有，重写
- 第三部分有没有具体公司+具体岗位+具体技能要求？差距分析有没有尊重用户的起点（刚入职、DID熟练、Python弱）？如果没有，重写
- 第四部分的技能建议是不是"别人也建议的通用方向"？如果是因果推断的进阶（RDD/IV/SCM），这是正确的——他的计量背景是稀缺优势，应该深耕。如果建议的是"学SQL"或"学Python基础"，重写
- 每个链接你能确认它在互联网上真实存在吗？如果不能，删掉链接改用"搜索关键词：XXX"
"""

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("DEFAULT_MODEL", "kimi-k2.6")
    print(f"正在连接 Kimi ({model}) 撰写深度行业报告 (预计 60-120 秒)...")
    url = "https://api.moonshot.cn/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 24576
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=900, context=_SSL_CTX) as res:
            msg = json.loads(res.read().decode('utf-8'))["choices"][0]["message"]
            result = msg.get("content") or msg.get("reasoning_content", "")
            return result.replace("{current_date}", current_date)
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
        urllib.request.urlopen(req, timeout=30, context=_SSL_CTX)
        print("群聊通知发送成功！")
    except: pass

def auto_push_to_github():
    """生成报告后自动提交并推送到 GitHub。"""
    import subprocess
    current_date = datetime.now().strftime("%Y-%m-%d")
    try:
        subprocess.run(["git", "add", "-A"], cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Weekly report {current_date}"], cwd=REPO_ROOT, check=False, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True, capture_output=True)
        print("已推送到 GitHub")
    except Exception as e:
        print(f"GitHub 推送失败（可能是网络问题，请手动 git push）: {e}")

if __name__ == "__main__":
    print("\n====== AI与数据驱动周报 生成任务启动 ======")
    report_content = generate_report_content()
    if report_content:
        filepath = save_report(report_content)
        push_to_feishu_group(filepath)
        auto_push_to_github()
    print("====== 任务流结束 ======\n")
