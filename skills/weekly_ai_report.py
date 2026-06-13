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
今天是 {current_date}。你正在为一位具体的数据分析师同事撰写个性化周报。

【用户画像与能力策略】
- 同花顺移动互联网事业部 · 平台新用户数据分析师（刚入职校招生），日常与运营协作承接数据需求。核心 KPI：扩大新用户规模 + 提升新用户转化（开户、购买云软件），驱动收入增长
- 安徽大学金融数学本科 + 上海财经大学金融硕士（计量方向）。SQL 熟练，Python 不熟练，DID 已掌握。ML 仅了解概念，LLM 只会使用不懂原理
- 职业目标：未来进入字节/小红书/阿里系/美团/腾讯等纯互联网，关注数据类、策略产品类、AI产品类岗位
- 阅读习惯：早上 5 分钟扫关键信息，周末 30 分钟精读。信息密度优先
- 能力策略：因果推断是核心壁垒（计量硕士背景是稀缺优势，DID→RDD→IV→合成控制法）；AI+Python 是效率放大器（pandas→statsmodels→DoWhy）；壁垒层优先级高于效率层

【约束】
1. 只写本周（{current_date}所在周）真实动态。不确定的宁可不写，绝不编造
2. 非公开数据指标必须标注来源。禁止"赋能、降维打击、破局、闭环、抓手、底层逻辑、颗粒度"等套话
3. 每段≤5句。每条分析必须回答：这对同花顺新用户 DA 意味着什么？他该做什么？
4. 链接只写确认存在的 DOI 或主流知名资源（如 Causal Inference for the Brave and True），不确定就改用"搜索关键词：XXX"
5. 标题只允许 # ## ### 三级，禁止 #### 及以上。需要四级子标题时用 - **加粗列表项**

{career_fw}

【模板】
{template}

各部分要点：第一部分聚焦新用户增长与转化的 AI 产品动态。第二部分 2.1 案例必须是字节/淘天/小红书/美团/腾讯的真实实践，2.2 覆盖本周模型发布/开源/API/监管。第三部分具体到公司+岗位+JD要求（≥2家公司），差距分析诚实面对用户起点（刚入职/DID熟练/Python弱/ML浅）。第四部分建在已有基础上推因果推断进阶（RDD/IV/SCM）或 Python 因果推断实操（statsmodels/DoWhy），4.1 用同花顺场景大白话解释，4.2 给公司名+场景+效果+来源，4.3 给可检索资料+可下载数据集+同花顺真实应用场景。
"""

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("DEFAULT_MODEL", "kimi-k2.6")
    print(f"正在连接 Kimi ({model}) 撰写深度行业报告 (预计 3-5 分钟)...")
    url = "https://api.moonshot.cn/v1/chat/completions"

    # K2.6 web_search 要求关闭 thinking
    base_payload = {
        "model": model,
        "max_completion_tokens": 32768,
        "thinking": {"type": "disabled"},
        "tools": [{"type": "builtin_function", "function": {"name": "$web_search"}}]
    }

    import subprocess
    import uuid

    try:
        # 第 1 轮：初始请求，Kimi 可能触发搜索
        msgs = [{"role": "user", "content": prompt}]
        for iteration in range(5):  # 最多 5 轮 tool call
            req_payload = json.dumps({**base_payload, "messages": msgs})
            cmd_id = f"curl_req_{uuid.uuid4().hex[:6]}"
            print(f"  [第{iteration+1}轮] 发送请求...")

            result = subprocess.run([
                "curl", "-k", "-s", "-X", "POST", url,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {api_key}",
                "-d", req_payload,
                "--max-time", "900"
            ], capture_output=True, text=True, timeout=910)

            if result.returncode != 0:
                print(f"  curl 失败: {result.stderr}")
                return ""

            resp = json.loads(result.stdout)
            if "error" in resp:
                print(f"  API 错误: {resp['error']}")
                return ""

            choice = resp.get("choices", [{}])[0]
            msg = choice.get("message", {})
            finish = choice.get("finish_reason", "")

            # tool_calls：Kimi 要求联网搜索
            if finish == "tool_calls":
                tool_calls = msg.get("tool_calls", [])
                if not tool_calls:
                    print("  收到 tool_calls 但无具体调用，跳过")
                    # fallback: 直接取 content
                    content = msg.get("content") or msg.get("reasoning_content", "")
                    return content.replace("{current_date}", current_date)

                print(f"  Kimi 请求联网搜索（{len(tool_calls)} 次）...")

                # 构建 assistant 消息（含 tool_calls）
                assistant_msg = {
                    "role": "assistant",
                    "content": msg.get("content") or None,
                    "tool_calls": tool_calls
                }
                msgs.append(assistant_msg)

                # 为每个 tool_call 返回一个 tool 消息
                # Kimi 的 $web_search 是服务端工具，只需原样回传
                for tc in tool_calls:
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps({"status": "called"}, ensure_ascii=False)
                    }
                    msgs.append(tool_msg)

                print(f"  已回传搜索请求，等待 Kimi 生成...")
                continue

            # 正常完成
            if finish == "stop" or finish == "length" or msg.get("content"):
                content = msg.get("content") or msg.get("reasoning_content", "")
                return content.replace("{current_date}", current_date)

            # 未预期的 finish_reason
            content = msg.get("content") or msg.get("reasoning_content", "")
            if content:
                return content.replace("{current_date}", current_date)
            print(f"  未预期的 finish_reason: {finish}，内容为空")
            return ""

        print("  达到最大迭代次数，返回已有内容")
        return ""

    except subprocess.TimeoutExpired:
        print("Kimi API 调用超时（超过 15 分钟）")
        return ""
    except Exception as e:
        print(f"Kimi API 调用失败: {e}")
        return ""

def cleanup_markdown(text: str) -> str:
    """后处理：修复模型输出的格式违规，裁掉前置废话"""
    import re
    # 找到第一个 # 标题，裁掉之前的所有内容（K2.6 的内心独白）
    m = re.search(r'^#\s', text, re.MULTILINE)
    if m:
        text = text[m.start():]
    # #### 四级标题 → 加粗列表项
    text = re.sub(r'^####\s+(.+)', r'- **\1**', text, flags=re.MULTILINE)
    # ##### 五级标题同上
    text = re.sub(r'^#####\s+(.+)', r'- **\1**', text, flags=re.MULTILINE)
    # DOI/URL 后粘连的中文：在 URL 和中文字符之间插入空格
    text = re.sub(r'(https?://\S+?)([（(][一-鿿])', r'\1 \2', text)
    return text

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
<p class="report-meta">{current_date} · 由 Kimi K2.6 + 联网搜索 自动生成</p>
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
    report_content = cleanup_markdown(generate_report_content())
    if report_content:
        filepath = save_report(report_content)
        auto_push_to_github()
    print("====== 任务流结束 ======\n")
