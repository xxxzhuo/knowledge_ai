import json
from typing import List, Tuple

from app.agent.part_number_parser import PartNumberParser

parser = PartNumberParser()


def _format_part_table(result: dict) -> str:
    grade = result.get("chip_grade", "X")
    if grade == "X":
        grade = result.get("die_grade", "X")

    return (
        "|品牌名称|晶圆型号|晶圆容量|颗粒容量|位宽|制程|球位|良率|叠代|\n"
        "|----|----|----|----|----|----|----|----|----|\n"
        f"|{result.get('brand_cn', 'X')}|{result.get('die_model', 'X')}|{result.get('die_capacity', 'X')}|"
        f"{result.get('chip_capacity', 'X')}|{result.get('bit_width', 'X')}|{result.get('process_node', 'X')}|"
        f"{result.get('ball_count', 'X')}|{grade}|{result.get('stacking_layers', 'X')}|\n"
    )


def query_part_number(part_number: str) -> str:
    """解析存储芯片料号，返回表格格式结果。"""
    try:
        result = parser.parse(part_number)
        return _format_part_table(result)
    except Exception as e:
        return f"解析失败：{str(e)}"


def calculate_chip_parameters(payload: str) -> str:
    """参数计算工具。输入支持 JSON 字符串：{"part_number":"...","quantity":100}。"""
    try:
        data = _try_parse_json(payload)
        if isinstance(data, dict):
            part_number = str(data.get("part_number", "")).strip()
            quantity = int(data.get("quantity", 1))
        else:
            part_number = str(payload).strip()
            quantity = 1

        if not part_number:
            return "参数计算失败：缺少 part_number"

        result = parser.compute_parameters(part_number, quantity=quantity)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"参数计算失败：{str(e)}"


def compare_part_numbers(payload: str) -> str:
    """料号对比工具。输入支持 JSON：{"part_numbers":["A","B"]} 或逗号分隔字符串。"""
    try:
        part_numbers = _parse_part_number_list(payload)
        if len(part_numbers) < 2:
            return "对比失败：至少提供2个料号"

        rows = parser.compare(part_numbers)
        lines = [
            "|料号|品牌|类型|晶圆型号|晶圆容量|颗粒容量|位宽|球位|频率|良率|叠层|",
            "|----|----|----|----|----|----|----|----|----|----|----|",
        ]
        for idx, row in enumerate(rows):
            pn = part_numbers[idx]
            grade = row.get("chip_grade", "X")
            if grade == "X":
                grade = row.get("die_grade", "X")
            lines.append(
                f"|{pn}|{row.get('brand_cn', 'X')}|{row.get('product_type', 'X')}|{row.get('die_model', 'X')}|"
                f"{row.get('die_capacity', 'X')}|{row.get('chip_capacity', 'X')}|{row.get('bit_width', 'X')}|"
                f"{row.get('ball_count', 'X')}|{row.get('ddr_frequency', 'X')}|{grade}|{row.get('stacking_layers', 'X')}|"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"对比失败：{str(e)}"


def generate_bom(payload: str) -> str:
    """BOM生成工具。输入支持 JSON：{"items":[{"part_number":"...","quantity":100}]}。"""
    try:
        data = _try_parse_json(payload)
        items = _parse_bom_items(data if data is not None else payload)
        if not items:
            return "BOM生成失败：未提供有效 items"

        bom = parser.build_bom(items)
        lines = [
            "|料号|数量|品牌|类型|颗粒容量|单颗(GB)|总容量(GB)|良率|有效产出(GB)|",
            "|----|----|----|----|----|----|----|----|----|",
        ]

        for row in bom["rows"]:
            grade = row.get("chip_grade", "X")
            if grade == "X":
                grade = row.get("die_grade", "X")
            lines.append(
                f"|{row.get('brand_code', 'X')}:{row.get('die_model', 'X')}|{row.get('quantity', '0')}|{row.get('brand_cn', 'X')}|"
                f"{row.get('product_type', 'X')}|{row.get('chip_capacity', 'X')}|{row.get('capacity_per_piece_gb', 'X')}|"
                f"{row.get('total_capacity_gb', 'X')}|{grade}|{row.get('good_output_gb', 'X')}|"
            )

        summary = bom["summary"]
        lines.append("")
        lines.append("**BOM汇总**")
        lines.append(f"- 项目数: {summary['item_count']}")
        lines.append(f"- 总容量: {summary['total_capacity_gb']} GB ({summary['total_capacity_tb']} TB)")
        lines.append(
            f"- 有效产出: {summary['total_good_output_gb']} GB ({summary['total_good_output_tb']} TB)"
        )

        return "\n".join(lines)
    except Exception as e:
        return f"BOM生成失败：{str(e)}"


def search_chip_info(query: str) -> str:
    return f"搜索结果：{query}"


def search_chip_news(query: str) -> str:
    return f"新闻搜索结果：{query}"


def _try_parse_json(value: str):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    if not (value.startswith("{") or value.startswith("[")):
        return None
    return json.loads(value)


def _parse_part_number_list(payload: str) -> List[str]:
    parsed = _try_parse_json(payload)
    if isinstance(parsed, dict) and isinstance(parsed.get("part_numbers"), list):
        return [str(item).strip().upper() for item in parsed["part_numbers"] if str(item).strip()]
    if isinstance(parsed, list):
        return [str(item).strip().upper() for item in parsed if str(item).strip()]
    return [item.strip().upper() for item in str(payload).split(",") if item.strip()]


def _parse_bom_items(payload) -> List[Tuple[str, int]]:
    items: List[Tuple[str, int]] = []
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        for item in payload["items"]:
            if not isinstance(item, dict):
                continue
            pn = str(item.get("part_number", "")).strip().upper()
            qty = int(item.get("quantity", 0))
            if pn and qty > 0:
                items.append((pn, qty))
        return items

    if isinstance(payload, str):
        for token in payload.split(","):
            token = token.strip()
            if not token:
                continue
            if "*" in token:
                pn, qty = token.split("*", 1)
                pn = pn.strip().upper()
                qty_num = int(qty.strip())
            else:
                pn = token.strip().upper()
                qty_num = 1
            if pn and qty_num > 0:
                items.append((pn, qty_num))

    return items