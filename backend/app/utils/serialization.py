"""通用序列化工具函数。"""
from __future__ import annotations

import json


def safe_json_dumps(obj) -> str | None:
    """安全地将对象序列化为 JSON 字符串，支持 Pydantic v2 模型、dict、list 等。"""
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if hasattr(obj, 'model_dump_json'):
        return obj.model_dump_json()
    if hasattr(obj, 'dict'):
        return json.dumps(obj.dict(), ensure_ascii=False)
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False)
    return str(obj)
