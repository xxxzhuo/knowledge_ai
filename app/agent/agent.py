import json
import re
from typing import List

from app.agent.tools import (
    query_part_number,
    calculate_chip_parameters,
    compare_part_numbers,
    generate_bom,
    search_chip_info,
    search_chip_news,
)


class StorageChipAgent:
    """存储芯片料号解析 Agent"""

    def run(self, query: str) -> str:
        """运行工具编排Agent处理查询。"""
        clean_query = query.strip()
        part_numbers = self._extract_part_numbers(clean_query)

        if self._is_bom_query(clean_query):
            payload = self._build_bom_payload(clean_query, part_numbers)
            return generate_bom(json.dumps(payload, ensure_ascii=False))

        if self._is_compare_query(clean_query):
            payload = {"part_numbers": part_numbers}
            return compare_part_numbers(json.dumps(payload, ensure_ascii=False))

        if self._is_calculate_query(clean_query):
            part_number = part_numbers[0] if part_numbers else ""
            qty = self._extract_quantity(clean_query)
            payload = {"part_number": part_number, "quantity": qty}
            return calculate_chip_parameters(json.dumps(payload, ensure_ascii=False))

        if part_numbers:
            return query_part_number(part_numbers[0])

        if "新闻" in clean_query or "发布" in clean_query:
            return search_chip_news(clean_query)

        return search_chip_info(clean_query)

    def parse_part_number(self, part_number: str) -> str:
        """直接解析料号并返回表格结果"""
        return query_part_number(part_number)

    def compare(self, payload: str) -> str:
        """直接调用料号对比工具"""
        return compare_part_numbers(payload)

    def bom(self, payload: str) -> str:
        """直接调用BOM工具"""
        return generate_bom(payload)

    def _extract_part_numbers(self, text: str) -> List[str]:
        candidates = re.findall(r"[A-Z0-9][A-Z0-9:-]{6,}", text.upper())
        return [item for item in candidates if any(ch.isdigit() for ch in item)]

    def _extract_quantity(self, text: str) -> int:
        match = re.search(r"(数量|QTY|qty|x|X)\s*[:：]?\s*(\d+)", text)
        if match:
            return max(int(match.group(2)), 1)
        return 1

    def _build_bom_payload(self, text: str, part_numbers: List[str]) -> dict:
        items = []
        pairs = re.findall(r"([A-Z0-9][A-Z0-9:-]{6,})\s*[*xX]\s*(\d+)", text.upper())
        for pn, qty in pairs:
            items.append({"part_number": pn, "quantity": int(qty)})

        if not items:
            qty = self._extract_quantity(text)
            for pn in part_numbers:
                items.append({"part_number": pn, "quantity": qty})

        return {"items": items}

    def _is_compare_query(self, text: str) -> bool:
        return any(keyword in text for keyword in ["对比", "比较", "差异", "compare"])

    def _is_bom_query(self, text: str) -> bool:
        return any(keyword in text for keyword in ["BOM", "bom", "清单", "用量", "汇总"])

    def _is_calculate_query(self, text: str) -> bool:
        return any(keyword in text for keyword in ["计算", "参数", "产出", "容量"])
