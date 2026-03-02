"""Quick test for the rewritten PartNumberParser."""
import sys
sys.path.insert(0, ".")

from app.agent.part_number_parser import PartNumberParser
import json

p = PartNumberParser()

def show(label, result, keys):
    print(f"\n=== {label} ===")
    print(json.dumps({k: result[k] for k in keys}, ensure_ascii=False, indent=2))

errors = []

# Test 1: FBM -> Micron NAND
r1 = p.parse("FBMB47R128G8ABAEAWG5-AS")
show("FBM (Micron NAND)", r1, ["brand_cn", "product_type", "die_model", "die_capacity",
     "chip_capacity", "process_node", "bit_width", "ball_count", "chip_grade", "stacking_layers"])
if r1["brand_cn"] != "镁光": errors.append("FBM brand should be 镁光")
if r1["product_type"] != "NAND颗粒": errors.append("FBM type should be NAND颗粒")
if r1["chip_capacity"] != "16G": errors.append(f"NAND capacity should be 16G, got {r1['chip_capacity']}")
if r1["chip_grade"] != "96%": errors.append(f"Grade -AS should be 96%, got {r1['chip_grade']}")

# Test 2: SUM -> Micron DDR
r2 = p.parse("SUM123Z32512M8-TP")
show("SUM (Micron DDR)", r2, ["brand_cn", "product_type", "die_model", "die_capacity",
     "chip_capacity", "technology_type", "bit_width", "ball_count", "chip_grade"])
if r2["brand_cn"] != "镁光": errors.append("SUM brand should be 镁光")
if r2["product_type"] != "DDR颗粒": errors.append("SUM type should be DDR颗粒")
if r2["chip_grade"] != "90%": errors.append(f"Grade -TP should be 90%, got {r2['chip_grade']}")

# Test 3: MT29 NAND wafer with E9 grade
r3 = p.parse("MT29N48R-IT:E9")
show("MT29 (NAND wafer)", r3, ["brand_cn", "product_type", "die_model", "die_capacity",
     "process_node", "die_grade"])
if r3["product_type"] != "NAND晶圆": errors.append(f"MT29 no DDR should be NAND晶圆, got {r3['product_type']}")
if r3["die_grade"] != "90%": errors.append(f"E9 grade should be 90%, got {r3['die_grade']}")
if r3["die_model"] != "N48R": errors.append(f"Die model should be N48R, got {r3['die_model']}")
if r3["process_node"] != "QLC": errors.append(f"N->QLC, got {r3['process_node']}")

# Test 4: XCB (SPECTEK DDR)
r4 = p.parse("XCB123Z32512M8-PG")
show("XCB (SPECTEK DDR)", r4, ["brand_cn", "product_type", "die_model", "technology_type", "chip_grade"])
if r4["brand_cn"] != "SPECTEK": errors.append("XCB brand should be SPECTEK")
if r4["chip_grade"] != "50%": errors.append(f"XCB -PG should be 50%, got {r4['chip_grade']}")

# Test 5: Samsung RDIMM DDR5
r5 = p.parse("M321R8GA0BB0-CQKBY")
show("M321 (Samsung DDR5)", r5, ["brand_cn", "product_type", "technology_type", "ddr_frequency", "chip_capacity"])
if r5["brand_cn"] != "三星": errors.append("M321 brand should be 三星")
if r5["technology_type"] != "DDR5": errors.append("M321 tech should be DDR5")
if r5["ddr_frequency"] != "4800": errors.append(f"QK freq should be 4800, got {r5['ddr_frequency']}")

# Test 6: K9 Samsung NAND wafer
r6 = p.parse("K9ABCDEF-TEST")
show("K9 (Samsung NAND wafer)", r6, ["brand_cn", "product_type"])
if r6["brand_cn"] != "三星": errors.append("K9 brand should be 三星")
if r6["product_type"] != "NAND晶圆": errors.append("K9 type should be NAND晶圆")

# Test 7: SPECTEK W prefix NAND wafer
r7 = p.parse("WBUB47R-IT:E5")
show("W prefix (SPECTEK wafer)", r7, ["brand_cn", "product_type", "die_model", "die_grade"])
if r7["brand_cn"] != "SPECTEK": errors.append("W prefix should be SPECTEK")
if r7["product_type"] != "NAND晶圆": errors.append("W prefix should be NAND晶圆")

# Test 8: DDR V-prefix (DDR3) die capacity
r8 = p.parse("SUM123V88512M8-TP")
show("V88 DDR3", r8, ["die_model", "die_capacity", "technology_type"])
if r8["technology_type"] != "DDR3": errors.append("V prefix should be DDR3")
if r8["die_capacity"] != "128MB": errors.append(f"V88 die capacity should be 128MB, got {r8['die_capacity']}")

# Test 9: XCBB grade
r9 = p.parse("SUN123Z32512M8-XCBB")
show("XCBB grade", r9, ["brand_cn", "chip_grade"])
if r9["chip_grade"] != "75%": errors.append(f"XCBB grade should be 75%, got {r9['chip_grade']}")

# Test 10: PRN prefix grade
r10 = p.parse("PRN123Z32512M8-OK")
show("PRN prefix", r10, ["brand_cn", "chip_grade"])
if r10["chip_grade"] != "98%": errors.append(f"PRN prefix grade should be 98%, got {r10['chip_grade']}")

# Test 11: compute_parameters & build_bom API
cp = p.compute_parameters("FBMB47R128G8ABAEAWG5-AS", quantity=100)
assert "quantity" in cp and cp["quantity"] == "100"
assert "total_capacity_gb" in cp

bom = p.build_bom([("FBMB47R128G8ABAEAWG5-AS", 50)])
assert "rows" in bom and "summary" in bom
assert bom["summary"]["item_count"] == 1

print("\n" + "=" * 50)
if errors:
    print(f"FAILED: {len(errors)} errors")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED!")
