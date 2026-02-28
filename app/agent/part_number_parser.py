import re
from typing import Dict, List, Tuple


class PartNumberParser:
    def __init__(self):
        self._die_capacity_map = {
            "1": "1GB",
            "2": "2GB",
            "3": "4GB",
            "4": "8GB",
            "5": "16GB",
            "6": "32GB",
            "7": "64GB",
            "8": "128GB",
        }

    def parse(self, part_number: str) -> Dict[str, str]:
        code = part_number.strip().upper()
        result = {
            "brand_cn": "X",
            "brand_en": "X",
            "product_type": "X",
            "brand_code": "X",
            "capacity_string": "X",
            "die_model": "X",
            "die_capacity": "X",
            "chip_capacity": "X",
            "stacking_layers": "X",
            "process_node": "X",
            "bit_width": "X",
            "ball_count": "X",
            "die_grade": "X",
            "chip_grade": "X",
            "ddr_frequency": "X",
            "technology_type": "X",
            "confidence": "high",
        }

        self._identify_brand(code, result)
        self._identify_product_type(code, result)

        if result["capacity_string"] != "X":
            self._parse_capacity(result)

        self._identify_die_model(code, result)
        self._parse_bit_width(code, result)
        self._parse_ball_count(code, result)
        self._parse_grade(code, result)
        self._parse_frequency(code, result)
        self._calculate_stacking_layers(result)
        self._update_confidence(result)
        return result

    def parse_many(self, part_numbers: List[str]) -> List[Dict[str, str]]:
        return [self.parse(part_number) for part_number in part_numbers]

    def compute_parameters(self, part_number: str, quantity: int = 1) -> Dict[str, str]:
        parsed = self.parse(part_number)
        chip_gb = self._capacity_to_gb(parsed.get("chip_capacity", "X"))
        die_gb = self._capacity_to_gb(parsed.get("die_capacity", "X"))

        per_piece_gb = chip_gb if chip_gb is not None else 0.0
        total_gb = per_piece_gb * max(quantity, 0)
        total_tb = total_gb / 1024 if total_gb > 0 else 0.0

        utilization = self._extract_percent(parsed.get("chip_grade", "X"))
        if utilization is None:
            utilization = self._extract_percent(parsed.get("die_grade", "X"))

        good_output_gb = total_gb * utilization / 100 if utilization is not None else None
        stacking_layers = parsed.get("stacking_layers", "X")

        return {
            **parsed,
            "quantity": str(max(quantity, 0)),
            "capacity_per_piece_gb": f"{per_piece_gb:.3f}" if chip_gb is not None else "X",
            "total_capacity_gb": f"{total_gb:.3f}" if chip_gb is not None else "X",
            "total_capacity_tb": f"{total_tb:.3f}" if chip_gb is not None else "X",
            "yield_percent": f"{utilization:.1f}%" if utilization is not None else "X",
            "good_output_gb": f"{good_output_gb:.3f}" if good_output_gb is not None else "X",
            "stacking_layers": stacking_layers,
        }

    def compare(self, part_numbers: List[str]) -> List[Dict[str, str]]:
        return [self.compute_parameters(part_number, quantity=1) for part_number in part_numbers]

    def build_bom(self, items: List[Tuple[str, int]]) -> Dict[str, object]:
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

    def _identify_brand(self, code: str, result: Dict[str, str]) -> None:
        if "MT29" in code or code.startswith("MT"):
            result["brand_cn"] = "镁光"
            result["brand_en"] = "Micron"
            result["brand_code"] = "MT29"
            return

        spectek_prefixes = [
            "FBM", "FBN", "FBC", "SUN", "SUU", "XCB", "PRM", "PRN", "WBU", "WY3", "W1U", "W3U", "SUM",
        ]
        for prefix in spectek_prefixes:
            if code.startswith(prefix):
                result["brand_cn"] = "SPECTEK"
                result["brand_en"] = "SpecTek"
                result["brand_code"] = "SP"
                return

        if len(code) >= 16 and (code.startswith("M321") or code.startswith("M393")):
            result["brand_cn"] = "三星"
            result["brand_en"] = "Samsung"
            result["product_type"] = "服务器内存模组"

    def _identify_product_type(self, code: str, result: Dict[str, str]) -> None:
        if result.get("product_type") == "服务器内存模组":
            return

        if code.startswith(("FBM", "FBN", "FBC")):
            result["product_type"] = "NAND颗粒"
        elif code.startswith(("SUN", "SUU", "XCB", "PRM", "PRN", "SUM")):
            result["product_type"] = "DDR颗粒"
        elif code.startswith(("WBU", "WY3", "W1U", "W3U")):
            result["product_type"] = "NAND晶圆"

        if result["brand_cn"] == "镁光":
            if re.search(r"(\d+[GMK]\d+)", code):
                result["product_type"] = "NAND颗粒"
            else:
                result["product_type"] = "NAND晶圆"
            match = re.search(r"(\d+[GMK]\d+)", code)
            if match:
                result["capacity_string"] = match.group(1)
            return

        match = re.search(r"(\d+[GMK]\d+)", code)
        if not match:
            if result["product_type"] == "X":
                result["product_type"] = "NAND晶圆"
            return

        capacity_string = match.group(1)
        result["capacity_string"] = capacity_string
        start = match.start(1)

        if result["product_type"] == "X":
            if start <= len(code) // 2:
                result["product_type"] = "DDR颗粒"
            else:
                result["product_type"] = "NAND颗粒"

    def _parse_capacity(self, result: Dict[str, str]) -> None:
        match = re.match(r"(\d+)([GMK])(\d+)", result["capacity_string"])
        if not match:
            return

        left = int(match.group(1))
        unit = match.group(2)
        right_raw = int(match.group(3))
        right = right_raw if right_raw != 0 else 1
        value = left * right / 8
        result["chip_capacity"] = self._format_capacity(value, unit)

    def _identify_die_model(self, code: str, result: Dict[str, str]) -> None:
        product_type = result["product_type"]

        if product_type == "NAND晶圆":
            if len(code) >= 8:
                candidate = code[3:8]
                if re.match(r"^[A-Z]\d\d[A-Z].?$", candidate):
                    result["die_model"] = candidate
                    digit = candidate[2]
                    result["die_capacity"] = self._die_capacity_map.get(digit, "X")
            return

        if product_type in {"DDR颗粒", "服务器内存模组"}:
            match = re.search(r"([VZY]\d{2}[A-Z]?)", code)
            if not match:
                return

            die_model = match.group(1)
            result["die_model"] = die_model
            tech = {"V": "DDR3", "Z": "DDR4", "Y": "DDR5"}.get(die_model[0], "X")
            result["technology_type"] = tech
            result["die_capacity"] = self._die_capacity_map.get(die_model[2], "X")

    def _parse_bit_width(self, code: str, result: Dict[str, str]) -> None:
        product_type = result["product_type"]

        if product_type == "NAND颗粒":
            segment = code[10:14] if len(code) >= 14 else ""
            if "H" in segment:
                result["bit_width"] = "X1"
            elif "K" in segment:
                result["bit_width"] = "X8"
            elif "L" in segment:
                result["bit_width"] = "X16"
            return

        if product_type in {"DDR颗粒", "服务器内存模组"} and result["capacity_string"] != "X":
            match = re.search(r"[GMK](\d+)", result["capacity_string"])
            if match:
                result["bit_width"] = {"4": "X4", "8": "X8", "16": "X16"}.get(match.group(1), "X")

        if product_type == "服务器内存模组" and result["bit_width"] == "X":
            width_match = re.search(r"R(\d)", code)
            if width_match:
                width_code = width_match.group(1)
                result["bit_width"] = {"4": "X4", "8": "X8", "1": "X16"}.get(width_code, "X")

    def _parse_ball_count(self, code: str, result: Dict[str, str]) -> None:
        product_type = result["product_type"]

        if product_type == "NAND颗粒" and "-" in code:
            index = code.index("-")
            if index >= 2:
                ball_code = code[index - 2:index]
                ball_map = {
                    "G1": "272", "G2": "272", "G3": "272", "G5": "272", "G6": "272",
                    "M9": "252", "G4": "252", "G7": "252", "G8": "252",
                    "J7": "152", "M4": "132", "M5": "132",
                }
                if re.match(r"J[1-6]", ball_code):
                    result["ball_count"] = "132"
                else:
                    result["ball_count"] = ball_map.get(ball_code, "X")
            return

        if product_type in {"DDR颗粒", "服务器内存模组"}:
            tech = result["technology_type"]
            width = result["bit_width"]
            ball_map = {
                "DDR3": {"X4": "78", "X8": "78", "X16": "96"},
                "DDR4": {"X4": "78", "X8": "78", "X16": "96"},
                "DDR5": {"X4": "82", "X8": "82", "X16": "102"},
            }
            result["ball_count"] = ball_map.get(tech, {}).get(width, "X")

    def _parse_grade(self, code: str, result: Dict[str, str]) -> None:
        product_type = result["product_type"]

        if product_type == "NAND晶圆" and "-" in code:
            idx = code.index("-")
            if idx + 4 <= len(code):
                pair = code[idx + 2:idx + 4]
                if len(pair) == 2 and pair[0] == "E":
                    if pair[1] == "0":
                        result["die_grade"] = "100%"
                    elif pair[1].isdigit():
                        result["die_grade"] = f"{100 - int(pair[1]) * 10}%"
                    elif pair[1] == "X":
                        result["die_grade"] = "2%"
            return

        if product_type == "NAND颗粒":
            grade_map = {
                "AS": "96%", "AF": "96%", "AL": "96%", "AR": "88%", "UT": "80%", "CB": "70%", "PG": "45%",
            }
            if "-" in code:
                suffix = code.split("-", 1)[1]
                for k, v in grade_map.items():
                    if suffix.startswith(k):
                        result["chip_grade"] = v
                        break
            return

        if product_type in {"DDR颗粒", "服务器内存模组"}:
            if "-PG" in code:
                result["chip_grade"] = "50%"
            elif "-TP" in code:
                result["chip_grade"] = "90%"
            elif code.startswith("XCB"):
                result["chip_grade"] = "75%"
            elif code.startswith("PRN") or code.startswith("PRM"):
                result["chip_grade"] = "98%"

    def _parse_frequency(self, code: str, result: Dict[str, str]) -> None:
        if result["product_type"] == "服务器内存模组":
            module_freq_map = {
                "RC": "2400",
                "TD": "2666",
                "WE": "3200",
                "QK": "4800",
                "WM": "5600",
                "CP": "6400",
            }
            for key, value in module_freq_map.items():
                if key in code:
                    result["ddr_frequency"] = value
                    break

            module_cap_map = {
                "2": "16G",
                "4": "32G",
                "6": "48G",
                "8": "64G",
                "Y": "96G",
                "A": "128G",
                "B": "256G",
            }
            for ch in code[3:10]:
                if ch in module_cap_map:
                    result["chip_capacity"] = module_cap_map[ch]
                    break

            if code.startswith("M321"):
                result["technology_type"] = "DDR5"
            elif code.startswith("M393"):
                result["technology_type"] = "DDR4"

        model = result["die_model"]
        model_map = {
            "V88": "1600",
            "V89": "3200",
            "Z32": "3200",
            "Z42": "3200",
            "Y32": "4800",
        }
        for key, value in model_map.items():
            if key in model:
                result["ddr_frequency"] = value
                return

        if "-" in code:
            suffix3 = code.split("-", 1)[1][:3]
            if suffix3 == "12K":
                result["ddr_frequency"] = "1600"

    def _calculate_stacking_layers(self, result: Dict[str, str]) -> None:
        chip_gb = self._capacity_to_gb(result.get("chip_capacity", "X"))
        die_gb = self._capacity_to_gb(result.get("die_capacity", "X"))

        if chip_gb is None or die_gb is None or die_gb <= 0:
            return

        layers = int(chip_gb // die_gb)
        result["stacking_layers"] = str(max(layers, 1))

    def _update_confidence(self, result: Dict[str, str]) -> None:
        unknown_count = sum(1 for k, v in result.items() if k != "confidence" and v == "X")
        if unknown_count <= 4:
            result["confidence"] = "high"
        elif unknown_count <= 8:
            result["confidence"] = "medium"
        else:
            result["confidence"] = "low"

    def _format_capacity(self, value: float, unit: str) -> str:
        if abs(value - int(value)) < 1e-9:
            return f"{int(value)}{unit}"
        return f"{value:.3f}".rstrip("0").rstrip(".") + unit

    def _capacity_to_gb(self, text: str):
        if text == "X":
            return None
        match = re.match(r"([0-9]+(?:\.[0-9]+)?)([GMK])", text.upper())
        if not match:
            return None
        value = float(match.group(1))
        unit = match.group(2)
        unit_to_gb = {"G": 1.0, "M": 1 / 1024, "K": 1 / (1024 * 1024)}
        return value * unit_to_gb[unit]

    def _extract_percent(self, text: str):
        if text == "X":
            return None
        match = re.match(r"([0-9]+(?:\.[0-9]+)?)%", text)
        if not match:
            return None
        return float(match.group(1))