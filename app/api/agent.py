"""Agent相关API接口"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.agent import StorageChipAgent
from app.agent.part_number_parser import PartNumberParser
from app.agent.tools import (
    query_part_number,
    calculate_chip_parameters,
    compare_part_numbers,
    generate_bom,
)

_parser = PartNumberParser()

router = APIRouter(prefix="/agent", tags=["agent"])

class PartNumberRequest(BaseModel):
    """料号请求模型"""
    part_number: str

class AgentRequest(BaseModel):
    """Agent请求模型"""
    query: str

class AgentResponse(BaseModel):
    """Agent响应模型"""
    result: str


class ParameterRequest(BaseModel):
    part_number: str
    quantity: int = 1


class CompareRequest(BaseModel):
    part_numbers: List[str]


class BomItem(BaseModel):
    part_number: str
    quantity: int


class BomRequest(BaseModel):
    items: List[BomItem]

@router.post("/parse", response_model=AgentResponse)
async def parse_part_number(request: PartNumberRequest):
    """解析存储芯片料号"""
    try:
        result = query_part_number(request.part_number)
        return AgentResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")


@router.post("/calculate", response_model=AgentResponse)
async def calculate_parameters(request: ParameterRequest):
    """计算料号参数与容量汇总"""
    try:
        payload = request.model_dump_json()
        result = calculate_chip_parameters(payload)
        return AgentResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"参数计算失败: {str(e)}")


@router.post("/compare", response_model=AgentResponse)
async def compare_parts(request: CompareRequest):
    """对比多个料号"""
    try:
        payload = request.model_dump_json()
        result = compare_part_numbers(payload)
        return AgentResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"对比失败: {str(e)}")


@router.post("/bom", response_model=AgentResponse)
async def build_bom(request: BomRequest):
    """生成BOM统计表"""
    try:
        payload = request.model_dump_json()
        result = generate_bom(payload)
        return AgentResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"BOM生成失败: {str(e)}")

@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(request: AgentRequest):
    """与存储芯片专家Agent交互"""
    try:
        agent = StorageChipAgent()
        result = agent.run(request.query)
        return AgentResponse(result=result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Agent处理失败: {str(e)}")


# ==================== JSON API (供前端使用) ====================

@router.post("/parse_json")
async def parse_part_number_json(request: PartNumberRequest) -> Dict[str, Any]:
    """解析料号, 返回结构化 JSON"""
    try:
        return _parser.parse(request.part_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculate_json")
async def calculate_parameters_json(request: ParameterRequest) -> Dict[str, Any]:
    """计算料号参数, 返回结构化 JSON"""
    try:
        return _parser.compute_parameters(request.part_number, quantity=request.quantity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/compare_json")
async def compare_parts_json(request: CompareRequest) -> List[Dict[str, Any]]:
    """对比多个料号, 返回结构化 JSON"""
    try:
        if len(request.part_numbers) < 2:
            raise HTTPException(status_code=400, detail="至少提供2个料号")
        results = _parser.compare(request.part_numbers)
        for i, r in enumerate(results):
            r["part_number"] = request.part_numbers[i]
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bom_json")
async def build_bom_json(request: BomRequest) -> Dict[str, Any]:
    """生成 BOM, 返回结构化 JSON"""
    try:
        items = [(item.part_number, item.quantity) for item in request.items]
        if not items:
            raise HTTPException(status_code=400, detail="未提供有效 items")
        result = _parser.build_bom(items)
        for i, row in enumerate(result["rows"]):
            row["part_number"] = items[i][0]
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))