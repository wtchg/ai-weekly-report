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

def is_monday() -> bool:
    return datetime.now().weekday() == 0

def current_week_key() -> str:
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]}"

def check_monday_guard() -> bool:
    """周一专属守卫：非周一运行直接退出，本周已有报告也退出。"""
    if not is_monday():
        print("周报仅在周一自动生成。今天是周"
              + ["一","二","三","四","五","六","日"][datetime.now().weekday()]
              + "，跳过生成。")
        return True
    week_key = current_week_key()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if not f.endswith('.html'):
            continue
        fpath = os.path.join(OUTPUT_DIR, f)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            f_week = f"{mtime.year}-W{mtime.isocalendar()[1]}"
            if f_week == week_key:
                print(f"本周已有正式报告（{f}），跳过生成。")
                return True
        except:
            pass
    return False

def extract_morning_scan_lines(content: str) -> list:
    """从报告内容中提取5个板块的一句信号。基于结构匹配：每个## 标题后的第一个>引用块。"""
    import re
    section_info = [
        ('一', 'C端AI产品落地观察'),
        ('二', '互联网行业数据与AI动态'),
        ('三', '大厂社招岗位洞察'),
        ('四', '本周技能精进'),
        ('五', '本周信息雷达'),
    ]
    lines = []
    for num, title in section_info:
        # 匹配 "## 一、..." 或 "## 一、 ..." 标题，之后找到第一个 > 引用块
        pattern = rf'##\s+{re.escape(num)}[、,]\s*\S+.*?\n\n>\s*(.+?)(?:\n|$)'
        m = re.search(pattern, content)
        if not m:
            # fallback: 标题后可能有空格
            pattern = rf'##\s+{re.escape(num)}[、,]\s*\S+.*?\n>\s*(.+?)(?:\n|$)'
            m = re.search(pattern, content)
        if m:
            text = m.group(1).strip().rstrip('。')
            # 去除可能残留的 ** 标记和旧版标签
            text = re.sub(r'\*{1,2}', '', text)
            text = re.sub(r'^本周一句话[：:]?\s*', '', text)
        else:
            text = ''
        lines.append({'num': num, 'title': title, 'text': text})
    return lines

def read_last_week_output_goal() -> str | None:
    """读取上周报告的4.3节产出目标，用于本周prompt注入。"""
    import html as html_mod
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted(
        [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.html')],
        reverse=True
    )
    if not files:
        return None
    try:
        with open(os.path.join(OUTPUT_DIR, files[0]), 'r', encoding='utf-8') as f:
            html_text = f.read()
        # 找 <h3>4.3 本周产出目标</h3> 和下一个 <h3> 或 <hr> 之间的内容
        import re
        m = re.search(
            r'<h3>4\.\d\s*本周产出目标</h3>(.+?)(?:<h[23]|<hr)',
            html_text, re.DOTALL
        )
        if not m:
            return None
        raw = m.group(1)
        # 去除HTML标签
        raw = re.sub(r'<[^>]+>', '', raw)
        raw = html_mod.unescape(raw).strip()
        if len(raw) > 600:
            raw = raw[:600] + '...'
        return raw
    except:
        return None

def estimate_reading_time(content: str) -> int:
    """估算阅读时间（分钟），按中文250字/分钟。"""
    import re
    text = re.sub(r'[^一-鿿]', '', content)
    char_count = len(text)
    return max(1, round(char_count / 250))

def _inject_last_week_review() -> str:
    goal = read_last_week_output_goal()
    if not goal:
        return ""
    return f"""
【上周回顾】
上周报告的"本周产出目标"内容如下：
```
{goal}
```

在生成本周报告时，请在第四部分的4.3节开头用1句话回应上周目标：
- 假设用户已完成：基于上周成果进阶到下一步
- 假设用户未完成：建议聚焦同一目标，不急于推进新内容
"""

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

{_inject_last_week_review()}

【约束】
1. 只写本周（{current_date}所在周）真实动态。不确定的宁可不写，绝不编造。尤其注意：不要编造具体的发布日期、版本号、MAU数字——除非你通过联网搜索确认了这些细节。如果你不确定一个数字是否准确，用"据报道""据公开信息"等措辞，或不写具体数字
2. 非公开数据指标必须标注来源。禁止"赋能、降维打击、破局、闭环、抓手、底层逻辑、颗粒度"等套话
3. 每段≤5句。每条分析必须回答：这对同花顺新用户 DA 意味着什么？他该做什么？
4. 链接只写确认存在的 DOI 或主流知名资源（如 Causal Inference for the Brave and True），不确定就改用"搜索关键词：XXX"
5. 标题只允许 # ## ### 三级，禁止 #### 及以上。需要四级子标题时用 - **加粗列表项**
6. 不要在文中出现以下表述模式及其变体："正是X的稀缺价值所在""这正是X的核心机会窗口""而非会跑SQL取数""计量背景""因果推断背景""与用户的X背景直接相关"。用户画像是让你内化后校准建议用的，不是让你在文中反复朗诵的。给你一个测试：把报告读给你不认识的人听——如果他听完能说出"这个读者好像是学计量的、刚毕业"，那就重写
7. 优先使用联网搜索获取本周真实动态。搜索到的信息要给出具体事实，但绝不要为了"看起来信息量大"而编造日期、版本号或事件。如果某子节确实搜不到值得写的新信息，写一句诚实说明（如"本周该方向无重大更新"）即可——诚实的简短比虚构的丰富更有价值

{career_fw}

【模板】
{template}

各部分要点：
- 每个板块标题下方用 > 引用块写一句完整结论——仅一句，加粗。这句话会被提取到页面顶部的"今日速览"面板，也是读者早上10秒扫读的内容。正文是下方展开的分析层
- 第一部分：聚焦新用户增长与转化的 AI 产品动态
- 第二部分：2.1 案例必须是字节/淘天/小红书/美团/腾讯的真实实践，2.2 覆盖本周模型发布/开源/API/监管
- 第三部分：具体到公司+岗位+JD要求（≥2家公司）。3.1 的"实际工作中怎么做"不要写成面试回答——要写这个岗位的人日常用什么工具、和谁协作、做什么类型的分析项目、产出什么文档。差距分析实事求是，不回避短板，直接列出具体差距和行动建议。**每个岗位必须标注信息来源**：来自招聘官网的标注"来源：XX招聘官网（本周发布）"，基于行业趋势推演的标注"来源：基于近期JD模式综合推演"，不确定的一律标注"来源：待验证，建议搜索关键词XX自行确认"
- 第四部分：建在已有基础上推因果推断进阶（RDD/IV/SCM）或 Python 因果推断实操。4.1 用同花顺场景大白话解释。4.2 给公司名+场景+效果+来源。4.3 是"本周产出目标"——不是学什么，是产出一份什么。必须具体到文件名和内容描述，这份产出下周就能放进面试作品集
- 第五部分（信息雷达）：推荐本周值得看的技术博客/分析报告（来自字节/小红书/美团等团队的真实分享），值得关注的人（即刻/公众号等真实可检索的），值得一试的新工具。**硬约束：至少1条是本周内（{current_date}所在周）发布或发现的内容。第五部分的板块总结句（> 引用块）必须包含一个具体名称或事件，不能写成"X生态持续完善"这种模糊概括。如确实无新信息，写明"本周无新发现"并跳过该板块。宁可少列一条也绝不编造**
- **宁可简短，不可编造**：如果一个 ### 子节本周确实搜索不到值得写的新内容，用 1-2 句诚实说明即可。例如"本周该方向无重大发布"——这是诚实，不是敷衍。诚实的信息简报胜过虚构的深度分析
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
                usage = resp.get("usage", {})
                if usage:
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    cost_est = total_tokens / 1_000_000 * 1.0
                    print(f"  Token用量: {total_tokens} (输入{prompt_tokens} + 输出{completion_tokens})，预估成本 ¥{cost_est:.2f}")
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
    # 去掉第一个 # 一级标题（HTML 页面另有 h1），保留其后的所有内容
    text = re.sub(r'^#\s.+\n+', '', text, count=1, flags=re.MULTILINE)
    # #### 四级标题 → 加粗列表项
    text = re.sub(r'^####\s+(.+)', r'- **\1**', text, flags=re.MULTILINE)
    # ##### 五级标题同上
    text = re.sub(r'^#####\s+(.+)', r'- **\1**', text, flags=re.MULTILINE)
    # DOI/URL 后粘连的中文：在 URL 和中文字符之间插入空格
    text = re.sub(r'(https?://\S+?)([（(][一-鿿])', r'\1 \2', text)
    return text

def markdown_to_html(md: str) -> str:
    import re

    # 预处理：提取并替换 pipe table，避免被后续逐行解析误处理
    md, table_placeholders = _extract_tables(md)

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

        # Table placeholder — emit directly, no wrapping
        if stripped.startswith('<!-- TABLE_'):
            close_lists()
            close_quote()
            html.append(stripped)
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
    result = '\n'.join(html)
    # 回填表格 HTML
    for idx, table_html in enumerate(table_placeholders):
        result = result.replace(f'<!-- TABLE_{idx} -->', table_html)
    return result


def _extract_tables(md: str) -> tuple:
    """从 markdown 中提取 pipe table 块，返回(替换后的md, [table_html列表])。"""
    import re
    lines = md.split('\n')
    result_lines = []
    table_html_list = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('|') and not stripped.startswith('|---') and i + 1 < len(lines):
            next_stripped = lines[i + 1].strip()
            if next_stripped.startswith('|') and '---' in next_stripped:
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1

                if len(table_lines) >= 3:
                    header_cells = [c.strip() for c in table_lines[0].split('|')[1:-1]]
                    body_rows = []
                    for tl in table_lines[2:]:
                        cells = [c.strip() for c in tl.split('|')[1:-1]]
                        body_rows.append(cells)

                    th_html = ''.join(f'<th>{c}</th>' for c in header_cells)
                    thead = f'<thead><tr>{th_html}</tr></thead>'
                    tbody_parts = []
                    for row in body_rows:
                        td_html = ''.join(
                            f'<td>{row[j] if j < len(row) else ""}</td>'
                            for j in range(len(header_cells))
                        )
                        tbody_parts.append(f'<tr>{td_html}</tr>')
                    tbody = f'<tbody>{"".join(tbody_parts)}</tbody>'
                    table_html = f'<table>{thead}{tbody}</table>'

                    result_lines.append(f'<!-- TABLE_{len(table_html_list)} -->')
                    table_html_list.append(table_html)
                    continue

        result_lines.append(line)
        i += 1

    return '\n'.join(result_lines), table_html_list

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

def build_html_page(body_html: str, current_date: str, morning_scan: list | None = None, reading_minutes: int = 5) -> str:
    history = scan_history()
    sidebar = build_sidebar_html(history, current_date)

    morning_brief_html = ""
    if morning_scan:
        items = []
        for item in morning_scan:
            items.append(f"""      <div class="brief-item">
        <span class="brief-num">{item['num']}</span>
        <div class="brief-content">
          <p>{item['text']}</p>
        </div>
      </div>""")
        morning_brief_html = f"""    <section class="morning-brief">
      <div class="brief-title">今日速览</div>
{"".join(items)}
    </section>
"""

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI与数据驱动周报 ({current_date})</title>
<meta property="og:title" content="AI与数据驱动周报 ({current_date})">
<meta property="og:description" content="个性化行业周报">
<meta property="og:type" content="article">
<meta name="twitter:card" content="summary">
<style>
  :root {{
    --bg: #fbfaf7;
    --text: #1d1d1d;
    --muted: #6e6e6e;
    --faint: #9e9e9e;
    --border: #e8e4df;
    --rule: #d6d0c4;
    --accent: #c2925a;
    --accent-hover: #a87740;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    --serif: "Songti SC", "Noto Serif SC", "Source Han Serif SC", "SimSun", STSong, Georgia, serif;
    --sidebar-w: 160px;
    --content-w: 700px;
    --gap: 64px;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: var(--serif);
    font-size: 17px;
    line-height: 1.85;
    color: var(--text);
    background: var(--bg);
  }}

  /* ---- 侧边栏 ---- */
  .sidebar {{
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: var(--sidebar-w);
    padding: 56px 0 32px;
    overflow-y: auto;
    z-index: 10;
  }}
  .sidebar-title {{
    font-family: var(--sans);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--faint);
    margin-bottom: 28px;
  }}
  .history-link {{
    display: block;
    font-family: var(--sans);
    font-size: 0.76rem;
    color: var(--muted);
    text-decoration: none;
    padding: 3px 0;
  }}
  .history-link:hover {{
    color: var(--text);
  }}
  .history-link.active {{
    color: var(--text);
    font-weight: 600;
  }}
  .history-date {{
    letter-spacing: 0.02em;
  }}

  /* ---- 主内容 ---- */
  .main {{
    margin-left: var(--sidebar-w);
    max-width: var(--content-w);
    padding: 68px 0 120px var(--gap);
  }}

  h1 {{
    font-size: 1.7rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    line-height: 1.3;
    margin: 0 0 4px 0;
  }}
  h2 {{
    font-size: 1.05rem;
    font-weight: 600;
    margin: 52px 0 12px 0;
    padding-bottom: 10px;
    border-bottom: 0.5px solid var(--rule);
    letter-spacing: 0.03em;
  }}
  h3 {{
    font-size: 0.92rem;
    font-weight: 600;
    margin: 32px 0 8px 0;
    color: #222;
  }}
  p {{
    margin: 0 0 14px 0;
  }}

  blockquote {{
    margin: 10px 0 18px;
    padding: 0;
    border: none;
    color: #4a4a4a;
    font-weight: 500;
    font-size: 0.94rem;
    line-height: 1.65;
  }}
  blockquote strong {{
    color: #3a3a3a;
    font-weight: 600;
  }}
  blockquote p {{ margin: 4px 0; }}

  ul, ol {{
    margin: 10px 0 20px 0;
    padding-left: 22px;
  }}
  li {{
    margin: 7px 0;
  }}
  li strong:first-child {{
    color: #111;
  }}

  hr {{
    border: none;
    border-top: 0.5px solid var(--rule);
    margin: 44px 0;
  }}

  a {{
    color: var(--accent);
    text-decoration: none;
  }}
  a:hover {{ color: var(--accent-hover); text-decoration: underline; }}

  strong {{ color: #111; font-weight: 700; }}

  /* ---- 表格 (booktabs) ---- */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 28px 0;
    font-size: 0.84rem;
    font-family: var(--sans);
    border-top: 0.5px solid var(--rule);
  }}
  th {{
    padding: 10px 28px 8px 0;
    text-align: left;
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 0.5px solid var(--rule);
  }}
  td {{
    padding: 8px 28px 8px 0;
    border: none;
    vertical-align: baseline;
    line-height: 1.5;
  }}

  /* ---- 今日速览面板 ---- */
  .morning-brief {{
    margin: 16px 0 36px;
    padding: 24px 0;
    border-top: 0.5px solid var(--rule);
    border-bottom: 0.5px solid var(--rule);
  }}
  .brief-title {{
    font-family: var(--sans);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--faint);
    margin-bottom: 20px;
  }}
  .brief-item {{
    display: flex;
    gap: 24px;
    margin-bottom: 10px;
  }}
  .brief-item:last-child {{
    margin-bottom: 0;
  }}
  .brief-num {{
    flex-shrink: 0;
    font-family: var(--serif);
    font-size: 2.4rem;
    font-weight: 700;
    line-height: 1;
    color: var(--rule);
    min-width: 36px;
    text-align: center;
  }}
  .brief-content p {{
    font-size: 0.88rem;
    font-weight: 600;
    line-height: 1.55;
    margin: 0;
    padding-top: 6px;
    color: var(--text);
  }}

  .report-meta {{
    font-family: var(--sans);
    color: var(--faint);
    font-size: 0.72rem;
    margin-bottom: 4px;
  }}
  .report-footer {{
    margin-top: 60px;
    padding-top: 20px;
    border-top: 0.5px solid var(--rule);
    font-family: var(--sans);
    color: var(--faint);
    font-size: 0.68rem;
    letter-spacing: 0.04em;
  }}

  /* ---- 暗色模式 ---- */
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1b1b1b;
      --text: #d6d1c8;
      --muted: #888;
      --faint: #6a6a6a;
      --border: #333;
      --rule: #3a3a3a;
      --accent: #d4a56a;
      --accent-hover: #e0b878;
    }}
    blockquote {{
      color: #b0a99e;
    }}
    blockquote strong {{
      color: #c8c0b4;
    }}
    h3 {{ color: #c8c0b4; }}
    li strong:first-child,
    strong {{ color: #e0dcd5; }}
  }}

  /* ---- 打印样式 ---- */
  @media print {{
    .sidebar {{ display: none !important; }}
    .main {{
      margin-left: 0;
      max-width: 100%;
      padding: 0;
    }}
    body {{
      font-size: 11pt;
      line-height: 1.65;
      background: #fff;
      color: #000;
    }}
    h1 {{ font-size: 1.5rem; }}
    h2 {{ font-size: 1.1rem; margin-top: 32px; }}
    h3 {{ font-size: 0.95rem; margin-top: 18px; }}
    .report-meta, .report-footer, .morning-brief {{ color: #666; }}
    a {{ color: #000; text-decoration: underline; }}
    a[href]::after {{ content: " (" attr(href) ")"; font-size: 0.8em; color: #666; }}
    @page {{ margin: 2.2cm; }}
  }}

  /* ---- 响应式 ---- */
  @media (max-width: 900px) {{
    .sidebar {{
      position: static;
      width: 100%;
      padding: 24px 20px 0;
    }}
    .sidebar-title {{
      margin-bottom: 12px;
    }}
    .history-link {{
      display: inline-block;
      padding: 4px 12px 4px 0;
      font-size: 0.74rem;
    }}
    .main {{
      margin-left: 0;
      max-width: 100%;
      padding: 28px 20px 72px;
    }}
    h1 {{ font-size: 1.4rem; }}
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
    <p class="report-meta">{current_date} · 预计阅读 {reading_minutes} 分钟</p>
    {morning_brief_html}{body_html}
    <p class="report-footer">OpenClaw Agent · AI与数据驱动周报</p>
  </main>

</body>
</html>'''

def save_report(content: str) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    filename = f"AI与数据驱动周报_{current_date}.html"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    morning_scan = extract_morning_scan_lines(content)
    reading_minutes = estimate_reading_time(content)
    body_html = markdown_to_html(content)
    full_html = build_html_page(body_html, current_date, morning_scan, reading_minutes)

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

def deepseek_audit(report_markdown: str) -> str | None:
    """DeepSeek V4 Pro 事实核查审计。返回 null（跳过核查）或一段审计标记文本。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("  未配置 DEEPSEEK_API_KEY，跳过核查")
        return None

    print("  DeepSeek V4 Pro 启动事实核查...")
    url = "https://api.deepseek.com/v1/chat/completions"

    prompt = f"""你是事实核查审计员。当前日期是{current_date}。以下是一份AI生成的行业周报。请逐板块审查其中每条声称的事实——发布日期、版本号、公司动态、数据指标——标记出可信度并指出问题项。控制输出在300字以内。

【审计规则】
- 如果一句话引用来源或标注"据报道""据悉"，标记为可信
- 如果一句话因搜索不到具体信息而诚实说明（如"本周无重大""搜索关键词"），标记为诚实，不扣分
- 如果一句话包含极其具体的日期/版本号/数字但无任何来源引述，标记为存疑

【报告正文】
{report_markdown}

【输出格式】
每个板块一行：`板块名 | 可信/诚实/存疑 | 一句话原因`
最后给一句整体建议。"""

    import subprocess
    import uuid

    payload = {
        "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        "max_completion_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        result = subprocess.run([
            "curl", "-k", "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", json.dumps(payload, ensure_ascii=False),
            "--max-time", "120"
        ], capture_output=True, text=True, timeout=130)

        if result.returncode != 0:
            print(f"  DeepSeek 核查失败: {result.stderr}")
            return None

        resp = json.loads(result.stdout)
        if "error" in resp:
            print(f"  DeepSeek API 错误: {resp['error']}")
            return None

        content = resp["choices"][0]["message"].get("content", "")
        usage = resp.get("usage", {})
        total = usage.get("total_tokens", 0)
        print(f"  DeepSeek 核查完成 ({total} tokens, 约 ¥{(total/1000000)*1.0:.3f})")
        return content

    except Exception as e:
        print(f"  DeepSeek 核查异常: {e}")
        return None

if __name__ == "__main__":
    print("\n====== AI与数据驱动周报 生成任务启动 ======")
    if check_monday_guard():
        print("====== 任务流结束 ======\n")
        exit(0)
    report_content = cleanup_markdown(generate_report_content())
    if report_content:
        # DeepSeek 事实核查（仅输出到控制台，不追加到报告）
        audit_result = deepseek_audit(report_content)
        if audit_result:
            print(f"\n  === DeepSeek 核查结果（仅供参考，未加入报告） ===\n{audit_result}\n  ================\n")

        filepath = save_report(report_content)
        auto_push_to_github()

        try:
            from extract_weekly_data import extract_and_append
            extract_and_append(report_content)
        except Exception as e:
            print(f"结构化提取失败（不影响报告发布）: {e}")
    print("====== 任务流结束 ======\n")
