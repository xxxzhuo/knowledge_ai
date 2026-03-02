"""
存储芯片料号解析器 - 严格按照料号公式规则实现

支持品牌: 镁光 SPECTEK 三星 海力士 长江存储 英特尔 闪迪
支持类型: NAND颗粒 DDR颗粒 NAND晶圆 服务器内存模组
"""

import re
from typing import Dict, List, Tuple


class PartNumberParser:

    def __init__(self):
        # 规则三(通用): 晶圆容量映射 - 晶圆型号第三位数字 -> 容量
        self._die_capacity_map = {
            "1": "1GB", "2": "2GB", "3": "4GB", "4": "8GB",
            "5": "16GB", "6": "32GB", "7": "64GB", "8": "128GB",
        }
        # 规则三(DDR3 V开头型号): 容量单位为 MB
        self._ddr3_die_capacity_map = {
            "0": "512MB", "8": "128MB", "9": "256MB",
        }
        # 容量字符串正则: 容量数字 + 单位(M/G/T) + 数字
        self._capacity_re = re.compile(r"(\d+)([MGT])(\d+)")

    # ==================== 公开 API ====================

    def parse(self, part_number: str) -> Dict[str, str]:
        """解析单个料号, 返回所有解析字段"""
        code = part_number.strip().upper()
        result: Dict[str, str] = {
            "brand_cn": "X", "brand_en": "X", "product_type": "X",
            "brand_code": "X", "capacity_string": "X",
            "die_model": "X", "die_capacity": "X",
            "chip_capacity": "X", "stacking_layers": "X",
            "process_node": "X", "bit_width": "X", "ball_count": "X",
            "die_grade": "X", "chip_grade": "X",
            "ddr_frequency": "X", "technology_type": "X",
            "confidence": "high",
        }
        # 1. 品牌 + 产品类型
        self._identify_brand_and_type(code, result)
        # 2. 容量字符串
        self._extract_capacity_string(code, result)
        # 3. MT29 歧义类型判断
        self._resolve_ambiguous_type(code, result)
        # 4. 晶圆型号 + 晶圆容量
        self._identify_die_model(code, result)
        # 5. 制程(晶圆型号首字母)
        self._parse_process_node(result)
        # 6. 颗粒容量
        if result["capacity_string"] != "X":
            self._parse_chip_capacity(result)
        # 7. 位宽
        self._parse_bit_width(code, result)
        # 8. 球位
        self._parse_ball_count(code, result)
        # 9. 良率/等级
        self._parse_grade(code, result)
        # 10. 频率
        self._parse_frequency(code, result)
        # 11. 叠层数
        self._calculate_stacking_layers(result)
        # 12. 置信度
        self._update_confidence(result)
        return result

    def parse_many(self, part_numbers: List[str]) -> List[Dict[str, str]]:
        """批量解析多个料号"""
        return [self.parse(pn) for pn in part_numbers]

    def compute_parameters(self, part_number: str, quantity: int = 1) -> Dict[str, str]:
        """解析料号并计算扩展参数(总容量/良品产出等)"""
        parsed = self.parse(part_number)
        chip_gb = self._capacity_to_gb(parsed.get("chip_capacity", "X"))
        per_piece_gb = chip_gb if chip_gb is not None else 0.0
        total_gb = per_piece_gb * max(quantity, 0)
        total_tb = total_gb / 1024 if total_gb > 0 else 0.0
        utilization = self._extract_percent(parsed.get("chip_grade", "X"))
        if utilization is None:
            utilization = self._extract_percent(parsed.get("die_grade", "X"))
        good_output_gb = total_gb * utilization / 100 if utilization is not None else None
        return {
            **parsed,
            "quantity": str(max(quantity, 0)),
            "capacity_per_piece_gb": f"{per_piece_gb:.3f}" if chip_gb is not None else "X",
            "total_capacity_gb": f"{total_gb:.3f}" if chip_gb is not None else "X",
            "total_capacity_tb": f"{total_tb:.3f}" if chip_gb is not None else "X",
            "yield_percent": f"{utilization:.1f}%" if utilization is not None else "X",
            "good_output_gb": f"{good_output_gb:.3f}" if good_output_gb is not None else "X",
        }

    def compare(self, part_numbers: List[str]) -> List[Dict[str, str]]:
        """对比多个料号参数"""
        return [self.compute_parameters(pn, quantity=1) for pn in part_numbers]

    def build_bom(self, items: List[Tuple[str, int]]) -> Dict[str, object]:
        """构建BOM清单"""
        rows: List[Dict[str, str]] = []
        total_capacity_gb = 0.0
        total_good_output_gb = 0.0
        for part_number, qty in items:
            data = self.compute_parameters(part_number, quantity=qty)
            rows.append(data)
            if data["total_capacity_gb"] != "X":
                total_capacity_gb += float(data["total_capacity_gb"])
            if data["good_output_gb"] != "X":
                total_good_output_gb += float(data["good_output_gb"])
        return {
            "rows": rows,
            "summary": {
                "item_count": len(rows),
                "total_capacity_gb": f"{total_capacity_gb:.3f}",
                "total_capacity_tb": f"{(total_capacity_gb / 1024):.3f}",
                "total_good_output_gb": f"{total_good_output_gb:.3f}",
                "total_good_output_tb": f"{(total_good_output_gb / 1024):.3f}",
            },
        }

    # ==================== 规则一: 品牌名称 + 产品类型 ====================

    def _identify_brand_and_type(self, code: str, result: Dict[str, str]) -> None:
        """通过料号开头字符识别品牌和产品类型"""
        # ---- 镁光 (Micron) ----
        if code.startswith("FBM"):
            result.update(brand_cn="镁光", brand_en="Micron",
                          brand_code="FBM", product_type="NAND颗粒")
            return
        if code.startswith("SUM"):
            result.update(brand_cn="镁光", brand_en="Micron",
                          brand_code="SUM", product_type="DDR颗粒")
            return
        if code.startswith("MT29"):
            result.update(brand_cn="镁光", brand_en="Micron", brand_code="MT29")
            # MT29 可能是 DDR颗粒 或 NAND晶圆, 在 _resolve_ambiguous_type 中判断
            return

        # ---- SPECTEK ----
        if code.startswith(("FBN", "FBC")):
            result.update(brand_cn="SPECTEK", brand_en="SpecTek",
                          brand_code=code[:3], product_type="NAND颗粒")
            return
        if code.startswith(("SUN", "SUU", "XCB", "PRM", "PRN")):
            result.update(brand_cn="SPECTEK", brand_en="SpecTek",
                          brand_code=code[:3], product_type="DDR颗粒")
            return
        # SPECTEK NAND晶圆: W开头且料号总字符数超过6位
        if code.startswith("W") and len(code) > 6:
            result.update(brand_cn="SPECTEK", brand_en="SpecTek",
                          brand_code=code[:3], product_type="NAND晶圆")
            return

        # ---- 三星 (Samsung) ----
        if len(code) >= 4 and code[0] == "M" and code[1:4] in ("321", "393"):
            result.update(brand_cn="三星", brand_en="Samsung",
                          brand_code=code[:4], product_type="服务器内存模组")
            result["technology_type"] = "DDR5" if code[1:4] == "321" else "DDR4"
            return
        if code.startswith("K9"):
            result.update(brand_cn="三星", brand_en="Samsung",
                          brand_code="K9", product_type="NAND晶圆")
            return

        # ---- 其他晶圆品牌 ----
        _other = [
            ("H25", "海力士", "SK Hynix", "NAND晶圆"),
            ("YMN", "长江存储", "YMTC", "NAND晶圆"),
            ("X29", "英特尔", "Intel", "NAND晶圆"),
            ("SD", "闪迪", "SanDisk", "NAND晶圆"),
        ]
        for prefix, cn, en, ptype in _other:
            if code.startswith(prefix):
                result.update(brand_cn=cn, brand_en=en,
                              brand_code=prefix, product_type=ptype)
                return

    def _resolve_ambiguous_type(self, code: str, result: Dict[str, str]) -> None:
        """MT29 可能是 DDR颗粒 或 NAND晶圆, 通过晶圆型号进一步判断"""
        if result["brand_cn"] != "镁光" or result["product_type"] != "X":
            return
        # 在第7-14位查找DDR晶圆型号(V/Z/Y开头)
        ddr_segment = code[6:14] if len(code) >= 7 else ""
        if re.search(r"[VZY]\d{2}", ddr_segment):
            result["product_type"] = "DDR颗粒"
            return
        # 有容量字符串 -> NAND颗粒; 无 -> NAND晶圆
        if self._capacity_re.search(code):
            result["product_type"] = "NAND颗粒"
        else:
            result["product_type"] = "NAND晶圆"

    # ==================== 容量字符串提取 ====================

    def _extract_capacity_string(self, code: str, result: Dict[str, str]) -> None:
        """提取容量字符串: 容量数字 + 单位(M/G/T) + 数字"""
        match = self._capacity_re.search(code)
        if match:
            result["capacity_string"] = match.group(0)

    # ==================== 规则二/三: 晶圆型号 + 晶圆容量 ====================

    def _identify_die_model(self, code: str, result: Dict[str, str]) -> None:
        """
        FLASH晶圆: 4字符(字母+数字+数字+字母), 位于料号第4至第8位之间
        DDR颗粒: 位于料号第7至第14位之间, 型号以V/Z/Y开头
        """
        product_type = result["product_type"]

        # FLASH晶圆 / NAND颗粒 - 晶圆型号在第4-8位 (0-indexed: code[3:8])
        if product_type in ("NAND晶圆", "NAND颗粒"):
            segment = code[3:8] if len(code) >= 8 else code[3:]
            match = re.search(r"([A-Z]\d\d[A-Z])", segment)
            if match:
                die_model = match.group(1)
                result["die_model"] = die_model
                digit = die_model[2]  # 型号第三位数字
                result["die_capacity"] = self._die_capacity_map.get(digit, "X")
            return

        # DDR颗粒 / 服务器内存模组 - 型号在第7-14位 (0-indexed: code[6:14])
        if product_type in ("DDR颗粒", "服务器内存模组"):
            segment = code[6:14] if len(code) >= 7 else ""
            match = re.search(r"([VZY]\d{2}[A-Z]?)", segment)
            if match:
                die_model = match.group(1)
                result["die_model"] = die_model
                first_letter = die_model[0]
                digit = die_model[2]  # 型号第三位数字

                tech = {"V": "DDR3", "Z": "DDR4", "Y": "DDR5"}.get(first_letter, "X")
                result["technology_type"] = tech

                # V开头(DDR3)使用MB单位的容量映射
                if first_letter == "V":
                    result["die_capacity"] = self._ddr3_die_capacity_map.get(digit, "X")
                else:
                    result["die_capacity"] = self._die_capacity_map.get(digit, "X")

    # ==================== 规则六: 制程 ====================

    def _parse_process_node(self, result: Dict[str, str]) -> None:
        """晶圆型号第一个字母: M->SLC, L->MLC, B->TLC, N->QLC"""
        die_model = result["die_model"]
        if die_model == "X" or not die_model:
            return
        process_map = {"M": "SLC", "L": "MLC", "B": "TLC", "N": "QLC"}
        result["process_node"] = process_map.get(die_model[0], "X")

    # ==================== 规则四: 颗粒容量 ====================

    def _parse_chip_capacity(self, result: Dict[str, str]) -> None:
        """
        NAND FLASH颗粒: 容量数字 / 8
        DDR颗粒: 容量数字 * 数字 / 8
        """
        match = self._capacity_re.match(result["capacity_string"])
        if not match:
            return

        left = int(match.group(1))        # 容量数字
        unit = match.group(2)             # M / G / T
        right_raw = int(match.group(3))   # 后面的数字
        right = right_raw if right_raw != 0 else 1  # 0按1计算

        product_type = result["product_type"]

        if product_type == "NAND颗粒":
            value = left / 8
        elif product_type in ("DDR颗粒", "服务器内存模组"):
            value = left * right / 8
        else:
            # NAND晶圆无颗粒容量概念
            return

        result["chip_capacity"] = self._format_capacity(value, unit)

    # ==================== 规则五: 位宽 ====================

    def _parse_bit_width(self, code: str, result: Dict[str, str]) -> None:
        """
        FLASH颗粒: 料号第11-14位中 H=X1, K=X8, L=X16 (以左边第一个为准)
        DDR颗粒: 容量字符串单位后面的数字 4/8/16/32/64
        """
        product_type = result["product_type"]

        if product_type == "NAND颗粒":
            segment = code[10:14] if len(code) >= 14 else ""
            for ch in segment:  # 以左边第一个为准
                if ch == "H":
                    result["bit_width"] = "X1"
                    return
                if ch == "K":
                    result["bit_width"] = "X8"
                    return
                if ch == "L":
                    result["bit_width"] = "X16"
                    return
            return

        if product_type in ("DDR颗粒", "服务器内存模组") and result["capacity_string"] != "X":
            match = re.search(r"[MGT](\d+)", result["capacity_string"])
            if match:
                bw_map = {"4": "X4", "8": "X8", "16": "X16", "32": "X32", "64": "X64"}
                result["bit_width"] = bw_map.get(match.group(1), "X")

    # ==================== 规则七: 球位 ====================

    def _parse_ball_count(self, code: str, result: Dict[str, str]) -> None:
        """
        FLASH颗粒: '-' 符号左边两位字符
        DDR颗粒: 根据DDR代数 + 位宽组合
        """
        product_type = result["product_type"]

        if product_type == "NAND颗粒" and "-" in code:
            idx = code.index("-")
            if idx >= 2:
                ball_code = code[idx - 2:idx]
                _ball_272 = {"G1", "G2", "G3", "G5", "G6"}
                _ball_252 = {"M9", "G4", "G7", "G8"}
                _ball_132 = {"M4", "M5", "J1", "J2", "J3", "J4", "J5", "J6"}

                if ball_code in _ball_272:
                    result["ball_count"] = "272"
                elif ball_code in _ball_252:
                    result["ball_count"] = "252"
                elif ball_code == "J7":
                    result["ball_count"] = "152"
                elif ball_code in _ball_132:
                    result["ball_count"] = "132"
            return

        if product_type in ("DDR颗粒", "服务器内存模组"):
            tech = result["technology_type"]
            width = result["bit_width"]
            ddr_ball_map = {
                "DDR3": {"X4": "78", "X8": "78", "X16": "96"},
                "DDR4": {"X4": "78", "X8": "78", "X16": "96"},
                "DDR5": {"X8": "82", "X16": "102"},
            }
            result["ball_count"] = ddr_ball_map.get(tech, {}).get(width, "X")

    # ==================== 规则八: 良率/等级 ====================

    def _parse_grade(self, code: str, result: Dict[str, str]) -> None:
        """
        FLASH晶圆: '-'右边查找 E+数字/X 模式
        FLASH颗粒: '-'右边的字母组合
        DDR颗粒: '-'右边 或 料号开头
        """
        product_type = result["product_type"]

        # ---- NAND晶圆 ----
        if product_type == "NAND晶圆" and "-" in code:
            suffix = code.split("-", 1)[1]
            match = re.search(r"E([0-9X])", suffix)
            if match:
                ch = match.group(1)
                if ch == "0":
                    result["die_grade"] = "100%"
                elif ch == "X":
                    result["die_grade"] = "2%"
                elif ch.isdigit():
                    result["die_grade"] = f"{int(ch) * 10}%"
            return

        # ---- NAND颗粒 ----
        if product_type == "NAND颗粒" and "-" in code:
            suffix = code.split("-", 1)[1]
            _nand_grade = {
                "AS": "96%", "AF": "96%", "AL": "96%",
                "AR": "88%", "UT": "80%", "CB": "70%", "PG": "45%",
            }
            for k, v in _nand_grade.items():
                if suffix.startswith(k):
                    result["chip_grade"] = v
                    return
            return

        # ---- DDR颗粒 / 服务器模组 ----
        if product_type in ("DDR颗粒", "服务器内存模组"):
            if "-" in code:
                suffix = code.split("-", 1)[1]
                if suffix.startswith("XCBB"):
                    result["chip_grade"] = "75%"
                    return
                if suffix.startswith("PG"):
                    result["chip_grade"] = "50%"
                    return
                if suffix.startswith("TP"):
                    result["chip_grade"] = "90%"
                    return
            # 规则2: 看料号开头
            if code.startswith("XCB"):
                result["chip_grade"] = "75%"
            elif code.startswith(("PRN", "PRM")):
                result["chip_grade"] = "98%"

    # ==================== 频率 ====================

    def _parse_frequency(self, code: str, result: Dict[str, str]) -> None:
        """三星服务器模组频率/容量 + DDR颗粒晶圆型号频率"""
        if result["product_type"] == "服务器内存模组":
            _freq = {
                "RC": "2400", "TD": "2666", "WE": "3200",
                "QK": "4800", "WM": "5600", "CP": "6400",
            }
            for key, value in _freq.items():
                if key in code:
                    result["ddr_frequency"] = value
                    break
            _cap = {
                "2": "16G", "4": "32G", "6": "48G", "8": "64G",
                "Y": "96G", "A": "128G", "B": "256G",
            }
            for ch in code[3:10]:
                if ch in _cap:
                    result["chip_capacity"] = _cap[ch]
                    break

        # DDR颗粒晶圆型号频率推断
        model = result["die_model"]
        if model != "X":
            _model_freq = {
                "V88": "1600", "V89": "3200",
                "Z32": "3200", "Z42": "3200",
                "Y32": "4800",
            }
            for key, value in _model_freq.items():
                if model.startswith(key):
                    result["ddr_frequency"] = value
                    return

        # '-'后缀频率
        if "-" in code:
            suffix3 = code.split("-", 1)[1][:3]
            if suffix3 == "12K":
                result["ddr_frequency"] = "1600"

    # ==================== 叠层数 ====================

    def _calculate_stacking_layers(self, result: Dict[str, str]) -> None:
        """叠层数 = 颗粒容量 / 晶圆容量"""
        chip_gb = self._capacity_to_gb(result.get("chip_capacity", "X"))
        die_gb = self._capacity_to_gb(result.get("die_capacity", "X"))
        if chip_gb is None or die_gb is None or die_gb <= 0:
            return
        layers = int(chip_gb // die_gb)
        result["stacking_layers"] = str(max(layers, 1))

    # ==================== 置信度 ====================

    def _update_confidence(self, result: Dict[str, str]) -> None:
        unknown = sum(1 for k, v in result.items() if k != "confidence" and v == "X")
        if unknown <= 4:
            result["confidence"] = "high"
        elif unknown <= 8:
            result["confidence"] = "medium"
        else:
            result["confidence"] = "low"

    # ==================== 工具方法 ====================

    def _format_capacity(self, value: float, unit: str) -> str:
        if abs(value - int(value)) < 1e-9:
            return f"{int(value)}{unit}"
        return f"{value:.3f}".rstrip("0").rstrip(".") + unit

    def _capacity_to_gb(self, text: str):
        if not text or text == "X":
            return None
        match = re.match(r"([0-9]+(?:\.[0-9]+)?)([GMTK])", text.upper())
        if not match:
            return None
        value = float(match.group(1))
        unit = match.group(2)
        unit_to_gb = {"G": 1.0, "M": 1 / 1024, "T": 1024.0, "K": 1 / (1024 * 1024)}
        return value * unit_to_gb.get(unit, 0)

    def _extract_percent(self, text: str):
        if not text or text == "X":
            return None
        match = re.match(r"([0-9]+(?:\.[0-9]+)?)%", text)
        if not match:
            return None
        return float(match.group(1))
