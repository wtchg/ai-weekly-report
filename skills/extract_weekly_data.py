"""从每周周报 markdown 中提取结构化数据，追加到 output/weekly_data.json。

用法：
    from extract_weekly_data import extract_and_append
    success = extract_and_append(report_markdown)

独立运行（测试用）：
    python3 skills/extract_weekly_data.py < report_markdown.txt
"""

import os
import json
import re
import subprocess
import ssl
import uuid
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(SCRIPT_DIR, "..")
ENTITY_MAP_PATH = os.path.join(SCRIPT_DIR, "entity_map.json")
WEEKLY_DATA_PATH = os.path.join(REPO_ROOT, "output", "weekly_data.json")

# SSL 绕过（公司网络代理证书问题）
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

# 自动加载 .env
_ENV_PATH = os.path.join(SCRIPT_DIR, "..", ".env")
if os.path.exists(_ENV_PATH):
    with open(_ENV_PATH, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _val = _line.split('=', 1)
                if _key.strip() not in os.environ:
                    os.environ[_key.strip()] = _val.strip()


def _load_entity_map() -> dict:
    with open(ENTITY_MAP_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _build_extraction_prompt(report_markdown: str) -> str:
    entity_map = _load_entity_map()
    current_week = datetime.now().strftime("%Y-W%W")
    current_date = datetime.now().strftime("%Y-%m-%d")

    return f"""从以下AI与数据驱动周报正文中提取结构化信息。严格输出JSON，不含任何其他文字。

【周报正文】
{report_markdown}

【实体归一化映射表】
```json
{json.dumps(entity_map, ensure_ascii=False, indent=2)}
```

【JSON Schema — 严格按此结构输出】
{{
  "week": "{current_week}",
  "date": "{current_date}",
  "section_1_products": {{
    "headline_signal": "板块一句总结",
    "products": [
      {{
        "name": "产品名",
        "company": "标准化公司名（查映射表）",
        "action": "发生了什么",
        "metric": {{"name": "指标名", "value": "数值", "source": "数据来源"}},
        "relevance_to_ths": "对同花顺的启示"
      }}
    ],
    "growth_cases": [
      {{
        "mechanism": "AI增长机制",
        "industry": "所属行业",
        "claimed_lift": "声称的提升效果",
        "ths_applicability": "同花顺可复现性评估"
      }}
    ]
  }},
  "section_2_cases": {{
    "headline_signal": "板块一句总结",
    "cases": [
      {{
        "company": "标准化公司名",
        "method": "使用的方法",
        "method_category": "标准化方法类别（查映射表）",
        "scenario": "应用场景",
        "key_insight": "关键发现",
        "ths_takeaway": "对同花顺的借鉴价值"
      }}
    ],
    "model_releases": [
      {{
        "name": "模型/工具名",
        "company": "发布方",
        "date": "发布日期",
        "note": "关键信息"
      }}
    ]
  }},
  "section_3_jobs": {{
    "headline_signal": "板块一句总结",
    "positions": [
      {{
        "company": "标准化公司名",
        "title": "完整岗位名",
        "role_category": "标准化岗位类别（查映射表）",
        "source_quality": "招聘官网（本周发布）| 基于近期JD模式综合推演 | 待验证",
        "key_requirements": ["技能1", "技能2"],
        "actual_work": "日常工作的具体描述",
        "tools_mentioned": ["工具1", "工具2"]
      }}
    ],
    "skill_trends": [
      {{
        "skill": "标准化技能名",
        "direction": "up|down|stable",
        "evidence": "判断依据"
      }}
    ],
    "gaps_identified": [
      {{
        "dimension": "差距维度",
        "current": "当前状态",
        "target": "目标状态"
      }}
    ]
  }},
  "section_4_skills": {{
    "headline_signal": "板块一句总结",
    "method_topic": "本周方法主题",
    "method_category": "标准化方法类别",
    "industry_example": {{
      "company": "示例公司",
      "scenario": "应用场景",
      "method_used": "具体方法"
    }},
    "output_goal": {{
      "filename": "产出文件名",
      "deliverables": ["交付物1", "交付物2"],
      "tools_used": ["工具1"]
    }}
  }},
  "section_5_radar": {{
    "headline_signal": "板块一句总结",
    "readings": [
      {{
        "title": "标题",
        "source_team": "来源团队",
        "topic": "主题",
        "is_fresh": true
      }}
    ],
    "people": [
      {{
        "name": "人名/账号",
        "platform": "平台",
        "expertise": "专长领域"
      }}
    ],
    "tools": [
      {{
        "name": "工具名",
        "category": "类别",
        "source": "来源"
      }}
    ]
  }}
}}

【规则】
1. 公司名、方法类别、岗位类别必须使用映射表中的标准化名称
2. 原文没有对应内容时，数组字段输出 []，对象字段输出 null
3. source_quality 必须从原文提取，三选一："招聘官网（本周发布）""基于近期JD模式综合推演""待验证"
4. 只输出 JSON，不要 markdown 代码块包裹，不要任何解释文字"""


def _call_kimi_for_extraction(prompt: str) -> dict | None:
    """调用 Kimi API 做结构化提取（低成本，无联网搜索）。"""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("DEFAULT_MODEL", "kimi-k2.6")
    url = "https://api.moonshot.cn/v1/chat/completions"

    payload = {
        "model": model,
        "max_completion_tokens": 4096,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        result = subprocess.run([
            "curl", "-k", "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", json.dumps(payload, ensure_ascii=False),
            "--max-time", "300"
        ], capture_output=True, text=True, timeout=310)

        if result.returncode != 0:
            print(f"  [extract] curl 失败: {result.stderr}")
            return None

        resp = json.loads(result.stdout)
        if "error" in resp:
            print(f"  [extract] API 错误: {resp['error']}")
            return None

        content = resp["choices"][0]["message"].get("content", "")
        usage = resp.get("usage", {})
        total = usage.get("total_tokens", 0)
        cost = total / 1_000_000 * 1.0
        print(f"  [extract] Token: {total} (约 ¥{cost:.3f})")

        # 尝试从响应中提取 JSON
        return _parse_json_response(content)

    except subprocess.TimeoutExpired:
        print("  [extract] API 超时")
        return None
    except Exception as e:
        print(f"  [extract] 失败: {e}")
        return None


def _parse_json_response(text: str) -> dict | None:
    """从 LLM 响应中提取 JSON 对象。"""
    # 去掉可能的 markdown 代码块包裹
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找到第一个 { 和最后一个 }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        print(f"  [extract] JSON 解析失败，原始响应前200字符: {text[:200]}")
        return None


def _validate_and_clean(data: dict) -> dict | None:
    """基本校验：确保关键字段存在且类型正确。"""
    required_sections = [
        "section_1_products", "section_2_cases", "section_3_jobs",
        "section_4_skills", "section_5_radar"
    ]
    for sec in required_sections:
        if sec not in data:
            print(f"  [extract] 缺少字段: {sec}")
            return None
        val = data[sec]
        if val is not None and not isinstance(val, dict):
            print(f"  [extract] 字段类型错误: {sec} (expected dict or null)")
            return None

    # 确保 week 和 date 存在
    if "week" not in data:
        data["week"] = datetime.now().strftime("%Y-W%W")
    if "date" not in data:
        data["date"] = datetime.now().strftime("%Y-%m-%d")

    return data


def extract_structured_data(report_markdown: str) -> dict | None:
    """从周报 markdown 中提取结构化数据。"""
    print("  [extract] 开始结构化提取...")
    prompt = _build_extraction_prompt(report_markdown)
    data = _call_kimi_for_extraction(prompt)
    if data is None:
        return None
    data = _validate_and_clean(data)
    return data


def append_to_weekly_data(data: dict) -> bool:
    """将一期结构化数据追加到 weekly_data.json。"""
    os.makedirs(os.path.dirname(WEEKLY_DATA_PATH), exist_ok=True)

    existing = []
    if os.path.exists(WEEKLY_DATA_PATH):
        try:
            with open(WEEKLY_DATA_PATH, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            existing = []

    # 检查是否已有同周数据（覆盖）
    week = data.get("week", "")
    existing = [e for e in existing if e.get("week") != week]
    existing.append(data)
    existing.sort(key=lambda x: x.get("date", ""))

    with open(WEEKLY_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"  [extract] 已追加到 {WEEKLY_DATA_PATH} (共 {len(existing)} 期)")
    return True


def extract_and_append(report_markdown: str) -> bool:
    """完整流程：提取 + 校验 + 追加。"""
    data = extract_structured_data(report_markdown)
    if data is None:
        return False
    return append_to_weekly_data(data)


def load_weekly_data() -> list:
    """加载所有已积累的结构化数据。"""
    if not os.path.exists(WEEKLY_DATA_PATH):
        return []
    with open(WEEKLY_DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)
