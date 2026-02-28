"""RAG Prompt 模板定义。"""

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.prompts.chat import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)


# ============== 系统提示词 ==============

SYSTEM_PROMPT = """你是一个专业的半导体知识助手，专门回答关于半导体技术、芯片设计、制造工艺等方面的问题。

你的任务是根据提供的上下文信息，准确、专业地回答用户的问题。

回答要求：
1. 基于上下文：优先使用提供的上下文信息回答
2. 专业准确：使用准确的技术术语和概念
3. 结构清晰：分点阐述，逻辑清晰
4. 引用来源：在回答中注明信息来源（如果有）
5. 诚实谦逊：如果上下文中没有相关信息，明确说明
6. 中文回答：使用简体中文回答

上下文信息：
{context}

如果上下文信息不足以回答问题，请说明"根据提供的信息无法完全回答该问题"。
"""


# ============== 问答模板 ==============

QA_PROMPT_TEMPLATE = """基于以下上下文信息，回答用户的问题。

上下文信息：
{context}

用户问题：
{question}

请提供准确、专业的回答：
"""

QA_PROMPT = PromptTemplate(
    template=QA_PROMPT_TEMPLATE,
    input_variables=["context", "question"]
)


# ============== Chat 模板 ==============

CHAT_SYSTEM_MESSAGE = SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT)

CHAT_HUMAN_MESSAGE = HumanMessagePromptTemplate.from_template(
    "问题：{question}"
)

CHAT_PROMPT = ChatPromptTemplate.from_messages([
    CHAT_SYSTEM_MESSAGE,
    CHAT_HUMAN_MESSAGE
])


# ============== 多轮对话模板 ==============

CONVERSATIONAL_PROMPT_TEMPLATE = """你是一个专业的半导体知识助手。根据对话历史和上下文信息，回答用户的问题。

对话历史：
{chat_history}

上下文信息：
{context}

当前问题：
{question}

请提供准确、专业的回答：
"""

CONVERSATIONAL_PROMPT = PromptTemplate(
    template=CONVERSATIONAL_PROMPT_TEMPLATE,
    input_variables=["chat_history", "context", "question"]
)


# ============== 条件生成模板 ==============

CONDENSE_QUESTION_TEMPLATE = """给定以下对话历史和后续问题，将后续问题改写为一个独立的问题。

对话历史：
{chat_history}

后续问题：{question}

独立问题："""

CONDENSE_QUESTION_PROMPT = PromptTemplate(
    template=CONDENSE_QUESTION_TEMPLATE,
    input_variables=["chat_history", "question"]
)


# ============== 半导体专用模板 ==============

SEMICONDUCTOR_QA_TEMPLATE = """你是一位半导体领域的技术专家。请基于以下技术文档片段，回答用户关于半导体技术的问题。

技术文档：
{context}

问题：{question}

回答要求：
- 使用准确的半导体术语
- 包含技术规格和参数（如果有）
- 说明应用场景或使用限制
- 如果涉及多个厂商或产品，进行对比说明

专业回答：
"""

SEMICONDUCTOR_QA_PROMPT = PromptTemplate(
    template=SEMICONDUCTOR_QA_TEMPLATE,
    input_variables=["context", "question"]
)


# ============== Datasheet 查询模板 ==============

DATASHEET_QUERY_TEMPLATE = """你是一位芯片数据手册分析专家。请基于以下数据手册内容，回答用户的问题。

数据手册内容：
{context}

用户问题：{question}

请提供详细的技术参数和说明：
- 关键参数值及其单位
- 工作条件和限制条件
- 引脚定义或封装信息（如适用）
- 应用建议或注意事项

详细回答：
"""

DATASHEET_QUERY_PROMPT = PromptTemplate(
    template=DATASHEET_QUERY_TEMPLATE,
    input_variables=["context", "question"]
)


# ============== 工艺技术模板 ==============

PROCESS_TECH_TEMPLATE = """你是半导体制造工艺专家。请基于以下工艺技术文档，回答用户的问题。

工艺文档：
{context}

问题：{question}

回答要求：
- 解释工艺节点和技术特点
- 说明性能优势和局限性
- 对比不同厂商的工艺差异（如适用）
- 提供应用场景建议

专业分析：
"""

PROCESS_TECH_PROMPT = PromptTemplate(
    template=PROCESS_TECH_TEMPLATE,
    input_variables=["context", "question"]
)


# ============== 带来源引用的模板 ==============

QA_WITH_SOURCES_TEMPLATE = """基于以下文档片段回答问题，并在回答中引用来源。

文档片段：
{context}

问题：{question}

请按以下格式回答：
1. 详细回答
2. 引用来源（注明来源文档）

回答：
"""

QA_WITH_SOURCES_PROMPT = PromptTemplate(
    template=QA_WITH_SOURCES_TEMPLATE,
    input_variables=["context", "question"]
)


# ============== 帮助函数 ==============

def format_docs(docs: list) -> str:
    """
    格式化文档列表为字符串
    
    Args:
        docs: 文档列表，每个文档是 (score, text, metadata) 的元组
        
    Returns:
        格式化的文档字符串
    """
    if not docs:
        return "没有找到相关文档。"
    
    formatted = []
    for i, (score, text, metadata) in enumerate(docs, 1):
        source = metadata.get("source", "未知来源")
        formatted.append(f"[文档 {i}] (来源: {source}, 相关度: {score:.3f})\n{text}\n")
    
    return "\n".join(formatted)


def format_chat_history(messages: list) -> str:
    """
    格式化对话历史
    
    Args:
        messages: 消息列表，每个消息是 (role, content) 的元组
        
    Returns:
        格式化的对话历史字符串
    """
    if not messages:
        return "暂无对话历史。"
    
    formatted = []
    for role, content in messages:
        if role == "user":
            formatted.append(f"用户: {content}")
        elif role == "assistant":
            formatted.append(f"助手: {content}")
    
    return "\n".join(formatted)


def get_prompt_by_type(prompt_type: str = "default") -> PromptTemplate:
    """
    根据类型获取 prompt 模板
    
    Args:
        prompt_type: prompt 类型
            - default: 默认 QA
            - semiconductor: 半导体专用
            - datasheet: 数据手册查询
            - process: 工艺技术
            - conversational: 多轮对话
            - with_sources: 带来源引用
        
    Returns:
        PromptTemplate 实例
    """
    prompts = {
        "default": QA_PROMPT,
        "semiconductor": SEMICONDUCTOR_QA_PROMPT,
        "datasheet": DATASHEET_QUERY_PROMPT,
        "process": PROCESS_TECH_PROMPT,
        "conversational": CONVERSATIONAL_PROMPT,
        "with_sources": QA_WITH_SOURCES_PROMPT
    }
    
    return prompts.get(prompt_type, QA_PROMPT)
