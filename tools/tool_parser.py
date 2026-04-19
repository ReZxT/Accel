import json
import re
import time
from typing import Any


def _safe_json(text: str, fallback: Any = None) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return fallback


def parse_xml_tool_calls(content: str) -> list[dict]:
    """Parse XML-style tool calls from model content. Handles 3 variants."""
    results = []
    counter = [0]

    def make_id():
        i = counter[0]
        counter[0] += 1
        return f"call_{int(time.time())}_{i:02d}"

    # Variant B: <tool_call><tool>Name</tool><input>{...}</input></tool_call>
    variant_b = re.compile(
        r"<tool_call>\s*<tool>([\s\S]*?)</tool>\s*<input>([\s\S]*?)</input>\s*</tool_call>"
    )
    for m in variant_b.finditer(content):
        name = m.group(1).strip()
        args = _safe_json(m.group(2).strip(), {})
        results.append({"name": name, "args": args, "id": make_id()})
    if results:
        return results

    # Variant A: <tool_call><function=name>...<parameter=p>v</parameter>...</function></tool_call>
    variant_a = re.compile(
        r"<tool_call>\s*<function=([\w.:-]+)>([\s\S]*?)</function>\s*</tool_call>"
    )
    param_re = re.compile(r"<parameter=(\w+)>([\s\S]*?)</parameter>")
    for m in variant_a.finditer(content):
        name = m.group(1).strip()
        args: dict[str, Any] = {}
        for pm in param_re.finditer(m.group(2)):
            val = pm.group(2).strip()
            args[pm.group(1)] = _safe_json(val, val)
        results.append({"name": name, "args": args, "id": make_id()})
    if results:
        return results

    # Anthropic original: <function_calls><invoke name="..."><parameter name="p">v</parameter></invoke></function_calls>
    invoke_re = re.compile(r'<invoke\s+name="([\w.:-]+)">([\s\S]*?)</invoke>')
    param_re2 = re.compile(r'<parameter\s+name="(\w+)">([\s\S]*?)</parameter>')
    for m in invoke_re.finditer(content):
        name = m.group(1).strip()
        args = {}
        for pm in param_re2.finditer(m.group(2)):
            val = pm.group(2).strip()
            args[pm.group(1)] = _safe_json(val, val)
        results.append({"name": name, "args": args, "id": make_id()})

    return results


def strip_tool_calls(content: str) -> str:
    """Remove all XML tool call blocks from text."""
    content = re.sub(r"<tool_call>[\s\S]*?</tool_call>", "", content)
    content = re.sub(r"<function_calls>[\s\S]*?</function_calls>", "", content)
    return content.strip()
