
import csv
import json
import os
import traceback
from pathlib import Path

import fitz

# 移除对外部 utils 和 constants 模块的依赖
# 定义本地 parse_range 函数
def parse_range(page_range: str, page_count: int) -> list:
    """解析页面范围字符串为页面索引列表"""
    if page_range == "all":
        return list(range(page_count))
    
    indices = []
    for part in page_range.split(","):
        if "-" in part:
            start, end = part.split("-")
            start = int(start) - 1  # 转换为 0-based 索引
            end = int(end) - 1
            indices.extend(range(start, min(end + 1, page_count)))
        else:
            idx = int(part) - 1
            if 0 <= idx < page_count:
                indices.append(idx)
    return indices

# 定义本地 dump_json 函数
def dump_json(path, data):
    """将数据写入 JSON 文件"""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 定义本地转换函数
def convert_length(value, from_unit, to_unit):
    """转换长度单位"""
    # 简单实现，仅支持 pt 到 cm 的转换
    if from_unit == "pt" and to_unit == "cm":
        return value * 0.0352778
    return value

def human_readable_size(size):
    """将文件大小转换为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

# 模拟 cmd_output_path
cmd_output_path = "/tmp/cmd_output.json"


class PdfExtractor:
    """统一 PDF 提取器。

    聚合当前项目中与 PDF 提取相关的能力：
    - 文本提取
    - 图片提取
    - 目录（书签）提取
    - 元数据提取
    - 资产组合提取（图片+文本+表格）
    """

    @staticmethod
    def _ensure_dir(path: Path) -> Path:
        """确保目录存在。"""
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def extract_text(**kwargs):
        """提取 PDF 文本到文件目录。"""
        try:
            doc_path = kwargs["doc_path"]
            page_range = kwargs.get("page_range", "all")
            output_path = kwargs.get("output_path")

            doc: fitz.Document = fitz.open(doc_path)
            roi_indices = parse_range(page_range, doc.page_count)
            if output_path is None:
                p = Path(doc_path)
                output_dir = Path(p.parent / f"{p.stem}-文本")
            else:
                output_dir = Path(output_path)
            PdfExtractor._ensure_dir(output_dir)

            for page_index in roi_indices:
                page = doc[page_index]
                text = page.get_text()
                savepath = output_dir / f"{page_index + 1}.txt"
                savepath.write_text(text, encoding="utf-8")

            dump_json(cmd_output_path, {"status": "success", "message": ""})
        except Exception:
            dump_json(cmd_output_path, {"status": "error", "message": traceback.format_exc()})

    @staticmethod
    def extract_images(**kwargs):
        """提取 PDF 图片到文件目录。"""
        try:
            doc_path = kwargs["doc_path"]
            page_range = kwargs.get("page_range", "all")
            output_path = kwargs.get("output_path")

            doc: fitz.Document = fitz.open(doc_path)
            roi_indices = parse_range(page_range, doc.page_count)
            if output_path is None:
                p = Path(doc_path)
                output_dir = Path(p.parent / f"{p.stem}-图片")
            else:
                output_dir = Path(output_path)
            PdfExtractor._ensure_dir(output_dir)

            for page_index in roi_indices:
                page = doc[page_index]
                image_list = page.get_images()
                for i, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n - pix.alpha > 3:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    savepath = output_dir / f"{page_index + 1}-{i + 1}.png"
                    pix.save(str(savepath))
                    pix = None

            dump_json(cmd_output_path, {"status": "success", "message": ""})
        except Exception:
            dump_json(cmd_output_path, {"status": "error", "message": traceback.format_exc()})

    @staticmethod
    def extract_toc(**kwargs):
        """提取 PDF 目录（书签）。"""
        try:
            doc_path = kwargs["doc_path"]
            format_type = kwargs.get("format", "txt")
            output_path = kwargs.get("output_path")

            doc: fitz.Document = fitz.open(doc_path)
            p = Path(doc_path)
            toc_data = doc.get_toc(simple=False)
            if not toc_data:
                dump_json(cmd_output_path, {"status": "error", "message": "该文件没有书签!"})
                return

            if format_type == "txt":
                if output_path is None:
                    output_path = str(p.parent / f"{p.stem}-书签.txt")
                with open(output_path, "w", encoding="utf-8") as f:
                    for line in toc_data:
                        indent = (line[0] - 1) * "\t"
                        f.writelines(f"{indent}{line[1]} {line[2]}\n")
            elif format_type == "json":
                if output_path is None:
                    output_path = str(p.parent / f"{p.stem}-书签.json")
                for i in range(len(toc_data)):
                    try:
                        toc_data[i][-1] = toc_data[i][-1]["to"].y
                    except Exception:
                        toc_data[i][-1] = 0
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(toc_data, f)

            dump_json(cmd_output_path, {"status": "success", "message": ""})
        except Exception:
            dump_json(cmd_output_path, {"status": "error", "message": traceback.format_exc()})

    @staticmethod
    def extract_metadata(**kwargs):
        """提取 PDF 元数据。"""
        try:
            doc_path = kwargs["doc_path"]
            doc: fitz.Document = fitz.open(doc_path)

            metadata = {}
            what, value = doc.xref_get_key(-1, "Info")
            if what == "xref":
                xref = int(value.replace("0 R", ""))
                for key in doc.xref_get_keys(xref):
                    metadata[key] = doc.xref_get_key(xref, key)[1]

            metadata["page_count"] = doc.page_count
            page_size = doc[-1].rect
            metadata["page_size"] = (
                convert_length(page_size.width, "pt", "cm"),
                convert_length(page_size.height, "pt", "cm"),
            )
            file_size = os.path.getsize(doc_path)
            metadata["file_size"] = human_readable_size(file_size)

            dump_json(cmd_output_path, {"status": "success", "message": ""})
            return metadata
        except Exception:
            dump_json(cmd_output_path, {"status": "error", "message": traceback.format_exc()})
            return None

    @staticmethod
    def extract_assets(input_pdf: str, page_range: str = "all", output: str | None = None):
        """组合提取 PDF 资产（图片、文本、表格），并返回汇总字典。"""
        try:
            input_path = Path(input_pdf)
            if not input_path.exists():
                raise FileNotFoundError(f"文件不存在: {input_pdf}")

            doc = fitz.open(str(input_path))
            page_indices = parse_range(page_range, doc.page_count)

            if output is None:
                output_dir = input_path.parent / f"{input_path.stem}-提取结果"
            else:
                output_dir = Path(output)
            PdfExtractor._ensure_dir(output_dir)

            images_dir = PdfExtractor._ensure_dir(output_dir / "images")
            text_dir = PdfExtractor._ensure_dir(output_dir / "text")
            datasheet_dir = PdfExtractor._ensure_dir(output_dir / "datasheet")

            image_items = []
            text_items = []
            datasheet_items = []
            jsonl_path = datasheet_dir / "tables.jsonl"

            with jsonl_path.open("w", encoding="utf-8") as jf:
                for page_index in page_indices:
                    page = doc[page_index]

                    # 图片提取
                    image_list = page.get_images(full=True)
                    for i, img in enumerate(image_list, start=1):
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        if pix.n - pix.alpha > 3:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        file_name = f"page-{page_index + 1}-image-{i}.png"
                        save_path = images_dir / file_name
                        pix.save(str(save_path))
                        image_items.append({"page": page_index + 1, "file": str(save_path)})

                    # 文本提取
                    text = page.get_text("text")
                    text_name = f"page-{page_index + 1}.txt"
                    text_path = text_dir / text_name
                    text_path.write_text(text, encoding="utf-8")
                    text_items.append({"page": page_index + 1, "file": str(text_path)})

                    # 表格提取
                    tables = []
                    if hasattr(page, "find_tables"):
                        found = page.find_tables()
                        tables = found.tables if found else []

                    for table_index, table in enumerate(tables, start=1):
                        rows = table.extract()
                        csv_name = f"page-{page_index + 1}-table-{table_index}.csv"
                        csv_path = datasheet_dir / csv_name
                        with csv_path.open("w", encoding="utf-8", newline="") as cf:
                            writer = csv.writer(cf)
                            for row in rows:
                                writer.writerow(row if row else [])

                        item = {
                            "page": page_index + 1,
                            "table_index": table_index,
                            "rows": len(rows),
                            "csv_file": str(csv_path),
                            "data": rows,
                        }
                        jf.write(json.dumps(item, ensure_ascii=False) + "\n")
                        datasheet_items.append(item)

            summary = {
                "input_pdf": str(input_path),
                "page_range": page_range,
                "page_count": len(page_indices),
                "output_dir": str(output_dir),
                "images": {"count": len(image_items), "items": image_items},
                "text": {"count": len(text_items), "items": text_items},
                "datasheet": {"count": len(datasheet_items), "items": datasheet_items},
            }

            summary_path = output_dir / "summary.json"
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            return summary
        except Exception:
            print(traceback.format_exc())
            return None

