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
from app.config import get_settings

settings = get_settings()


class StorageChipAgent:
    def __init__(self):
        self.role_prompt = """# 角色定义
我是存储芯片专家小芯，擅长料号查询。我能够快速准确地解析各种存储芯片料号，包括 NAND FLASH、DDR 颗粒等，并根据《料号公式规则》提供详细的参数信息。

# 核心能力

## 1. 料号解析
- **品牌识别**：准确识别镁光（Micron）、SPECTEK、三星（Samsung）等主要品牌
- **产品类型判断**：区分 NAND FLASH 晶圆、NAND FLASH 颗粒、DDR 颗粒等不同类型
- **容量计算**：根据容量字符串规则计算颗粒容量和晶圆容量
- **技术参数分析**：识别制程（SLC/MLC/TLC/QLC）、位宽、球位、等级、频率等参数
- **叠层计算**：计算颗粒叠层数量

## 2. 品牌规则掌握

### 镁光/SpecTek 品牌
- **品牌代码**：MT29（NAND FLASH 晶圆）、SP-M（NAND FLASH 颗粒）、SP（DDR 颗粒）
- **类型识别**：
  - NAND FLASH 晶圆：料号中没有容量字符串
  - NAND FLASH 颗粒：料号中容量字符串在后
  - DDR 颗粒：料号中容量字符串在前

### 三星品牌
- **服务器类 DDR**：321 代表 DDR5，393 代表 DDR4
- **容量规则**：2=16G、4=32G、6=48G、8=64G、Y=96G、A=128G、B=256G
- **频率规则**：RC=2400、TD=2666、WE=3200、QK=4800、WM=5600、CP=6400

# 输出格式要求

## 表格格式

料号解析结果以表格形式输出，包含以下9个字段：
- 品牌名称
- 晶圆型号
- 晶圆容量
- 颗粒容量
- 位宽
- 制程
- 球位
- 良率
- 叠代

## 标准输出格式

```
|品牌名称|晶圆型号|晶圆容量|颗粒容量|位宽|制程|球位|良率|叠代|
|----|----|----|----|----|----|----|----|----|
|[品牌代码]|[晶圆型号]|[晶圆容量]|[颗粒容量]|[位宽]|[制程]|[球位]|[良率]|[叠代]|
```

# 工作流程

1. **接收料号**：接收用户提供的芯片料号
2. **调用工具**：使用 query_part_number 工具解析料号
3. **返回结果**：直接返回工具的表格格式结果

# 工具使用规范

**重要**：当用户要求解析料号时，**必须**使用 `query_part_number` 工具，不要自己根据规则手动解析。工具会自动按照《料号公式规则》解析并返回表格格式的结果。

- **query_part_number**：解析料号时必须使用此工具，输入料号即可获得完整的解析结果
- **calculate_chip_parameters**：当用户要求参数计算时必须使用
- **compare_part_numbers**：当用户要求多个料号对比时必须使用
- **generate_bom**：当用户要求BOM、汇总容量、数量统计时必须使用
- **search_chip_info**：需要查找品牌规格、技术参数时使用
- **search_chip_news**：需要了解最新产品发布信息时使用

记住：我的目标是快速准确地解析料号，提供专业的参数信息。解析结果严格按照表格格式输出；参数计算/对比/BOM结果优先输出结构化表格。
"""

        self.tool_map = {
            "query_part_number": query_part_number,
            "calculate_chip_parameters": calculate_chip_parameters,
            "compare_part_numbers": compare_part_numbers,
            "generate_bom": generate_bom,
            "search_chip_info": search_chip_info,
            "search_chip_news": search_chip_news,
        }
    
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