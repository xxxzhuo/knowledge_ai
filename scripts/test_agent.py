#!/usr/bin/env python3
"""测试存储芯片专家Agent功能"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.agent.part_number_parser import PartNumberParser
from app.agent.tools import (
    query_part_number,
    calculate_chip_parameters,
    compare_part_numbers,
    generate_bom,
)


def test_part_number_parser():
    """测试料号解析器"""
    print("测试料号解析器...")
    parser = PartNumberParser()
    
    # 测试示例料号
    test_cases = [
        "SUM1G16Z42BD8TB-PG",  # SpecTek DDR颗粒
        "MT29F4G08ABADAWP-IT:E",  # Micron NAND颗粒
        "M321R8GA3BB0-CRC",  # Samsung DDR5
        "FBM2G8A16MCB-ABWT",  # SpecTek NAND颗粒
        "SUM2G8Z32BD8TB-TP",  # SpecTek DDR颗粒
        "SUM4G16Y32BD8TB-PG",  # SpecTek DDR颗粒
    ]
    
    for part_number in test_cases:
        print(f"\n解析料号: {part_number}")
        result = parser.parse(part_number)
        print("解析结果:")
        for key, value in result.items():
            print(f"  {key}: {value}")


def test_query_part_number():
    """测试query_part_number工具"""
    print("\n测试query_part_number工具...")
    
    test_part_numbers = [
        "SUM1G16Z42BD8TB-PG",
        "MT29F4G08ABADAWP-IT:E",
    ]
    
    for part_number in test_part_numbers:
        print(f"\n解析料号: {part_number}")
        result = query_part_number(part_number)
        print("解析结果:")
        print(result)


def test_parameter_compare_bom_tools():
    """测试参数计算/对比/BOM工具"""
    print("\n测试参数计算工具...")
    payload = '{"part_number":"SUM1G16Z42BD8TB-PG","quantity":120}'
    print(calculate_chip_parameters(payload))

    print("\n测试料号对比工具...")
    compare_payload = '{"part_numbers":["SUM1G16Z42BD8TB-PG","SUM2G8Z32BD8TB-TP","MT29F4G08ABADAWP-IT:E"]}'
    print(compare_part_numbers(compare_payload))

    print("\n测试BOM工具...")
    bom_payload = (
        '{"items":['
        '{"part_number":"SUM1G16Z42BD8TB-PG","quantity":200},'
        '{"part_number":"SUM2G8Z32BD8TB-TP","quantity":150},'
        '{"part_number":"MT29F4G08ABADAWP-IT:E","quantity":80}'
        ']}'
    )
    print(generate_bom(bom_payload))


if __name__ == "__main__":
    test_part_number_parser()
    test_query_part_number()
    test_parameter_compare_bom_tools()