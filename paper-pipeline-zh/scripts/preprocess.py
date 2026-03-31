#!/usr/bin/env python3
"""
PDF预处理脚本：提取文本、检测结构、智能分块

用法:
    python preprocess.py extract <pdf_file> <output_dir>
    python preprocess.py chunk <raw_text_file> <output_dir>
    python preprocess.py all <pdf_file> <output_dir>
"""

import os
import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# 配置
MAX_CHUNK_SIZE = 12000  # 字符数，约8000 tokens
MIN_CHUNK_SIZE = 2000   # 最小分块大小


def extract_pdf(pdf_path: str, output_dir: str) -> str:
    """提取PDF文本到文件"""
    try:
        import pdfplumber
    except ImportError:
        print("Error: pdfplumber not installed. Run: pip install pdfplumber")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    raw_file = os.path.join(output_dir, "raw.txt")

    with pdfplumber.open(pdf_path) as pdf:
        lines = []
        lines.append(f"PDF文件: {pdf_path}")
        lines.append(f"总页数: {len(pdf.pages)}")
        lines.append("=" * 80)

        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                lines.append(f"\n--- 第 {i} 页 ---\n")
                lines.append(text)

        content = "\n".join(lines)

    with open(raw_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Extracted: {pdf_path} -> {raw_file}")
    return raw_file


def detect_structure(raw_file: str) -> Dict:
    """检测论文结构"""
    with open(raw_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取标题（通常在第一页）
    lines = content.split("\n")
    title = ""
    for i, line in enumerate(lines[:30]):
        line = line.strip()
        if line and not line.startswith("---") and not line.startswith("PDF") and not line.startswith("总页数") and not line.startswith("="):
            # 跳过作者列表（通常包含很多逗号分隔的名字）
            if "," not in line or len(line) < 100:
                title = line
                break

    # 检测章节标题
    sections = []
    section_patterns = [
        # 标准编号格式: 1. Title, 2.1 Title, etc.
        r'^(\d+(?:\.\d+)?)\s*\.?\s+([A-Z][A-Za-z\s\-:]+)$',
        # 附录格式: A.1 Title
        r'^([A-Z]\.\d*)\s+([A-Z][A-Za-z\s\-:]+)$',
        # 中文编号: 一、二、三、
        r'^([一二三四五六七八九十]+)[、．.]\s*(.+)$',
    ]

    current_section = None
    current_subsections = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        for pattern in section_patterns:
            match = re.match(pattern, line)
            if match:
                num, title_text = match.groups()
                level = num.count('.') + 1 if '.' in num else 1

                section_info = {
                    "id": f"sec_{len(sections)+1:03d}",
                    "number": num,
                    "title": title_text.strip(),
                    "level": level,
                    "line_start": i
                }

                # 判断是主节还是子节
                if level == 1:
                    if current_section:
                        current_section["subsections"] = current_subsections
                        sections.append(current_section)
                    current_section = section_info
                    current_subsections = []
                else:
                    current_subsections.append(section_info)
                break

    # 添加最后一个章节
    if current_section:
        current_section["subsections"] = current_subsections
        sections.append(current_section)

    # 提取总页数
    total_pages = 0
    page_match = re.search(r'总页数:\s*(\d+)', content)
    if page_match:
        total_pages = int(page_match.group(1))

    structure = {
        "title": title,
        "total_pages": total_pages,
        "sections": sections
    }

    return structure


def chunk_by_sections(raw_file: str, output_dir: str, structure: Dict) -> List[Dict]:
    """按章节分块"""
    with open(raw_file, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    chunks_dir = os.path.join(output_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    chunks = []

    # 获取所有章节的行号范围
    section_ranges = []
    for sec in structure["sections"]:
        start_line = sec.get("line_start", 0)
        section_ranges.append((start_line, sec))

        for subsec in sec.get("subsections", []):
            sub_start = subsec.get("line_start", start_line + 1)
            section_ranges.append((sub_start, subsec))

    # 按行号排序
    section_ranges.sort(key=lambda x: x[0])

    # 生成分块
    for i, (start_line, sec_info) in enumerate(section_ranges):
        # 确定结束行
        if i + 1 < len(section_ranges):
            end_line = section_ranges[i + 1][0]
        else:
            end_line = len(lines)

        # 提取内容
        chunk_lines = lines[start_line:end_line]
        chunk_content = "\n".join(chunk_lines)

        # 如果内容过长，需要进一步分割
        if len(chunk_content) > MAX_CHUNK_SIZE:
            sub_chunks = split_large_chunk(chunk_content, sec_info, len(chunks))
            for sub in sub_chunks:
                chunk_file = os.path.join(chunks_dir, f"chunk_{sub['index']:03d}.md")
                with open(chunk_file, "w", encoding="utf-8") as f:
                    f.write(sub["content"])
                chunks.append({
                    "index": sub["index"],
                    "file": f"chunk_{sub['index']:03d}.md",
                    "section_id": sec_info.get("id", ""),
                    "section_title": sec_info.get("title", ""),
                    "size": len(sub["content"])
                })
        else:
            chunk_index = len(chunks)
            chunk_file = os.path.join(chunks_dir, f"chunk_{chunk_index:03d}.md")

            # 添加章节标题作为上下文
            header = f"## {sec_info.get('title', '')}\n\n"
            full_content = header + chunk_content

            with open(chunk_file, "w", encoding="utf-8") as f:
                f.write(full_content)

            chunks.append({
                "index": chunk_index,
                "file": f"chunk_{chunk_index:03d}.md",
                "section_id": sec_info.get("id", ""),
                "section_title": sec_info.get("title", ""),
                "size": len(full_content)
            })

    return chunks


def split_large_chunk(content: str, sec_info: Dict, start_index: int) -> List[Dict]:
    """分割过大的分块"""
    chunks = []

    # 按段落分割
    paragraphs = re.split(r'\n\s*\n', content)

    current_chunk = ""
    chunk_index = start_index

    for para in paragraphs:
        # 表格和公式作为整体
        is_table = "|" in para and para.count("|") >= 3
        is_formula = "$$" in para

        if is_table or is_formula:
            # 如果当前块不为空且加入后会超限，先保存当前块
            if current_chunk and len(current_chunk) + len(para) > MAX_CHUNK_SIZE:
                chunks.append({
                    "index": chunk_index,
                    "content": current_chunk.strip()
                })
                chunk_index += 1
                current_chunk = ""

            current_chunk += "\n\n" + para
        else:
            # 普通段落
            if len(current_chunk) + len(para) > MAX_CHUNK_SIZE and len(current_chunk) >= MIN_CHUNK_SIZE:
                chunks.append({
                    "index": chunk_index,
                    "content": current_chunk.strip()
                })
                chunk_index += 1
                current_chunk = para
            else:
                current_chunk += "\n\n" + para

    # 保存最后一块
    if current_chunk.strip():
        chunks.append({
            "index": chunk_index,
            "content": current_chunk.strip()
        })

    # 添加章节标题作为头部
    for chunk in chunks:
        header = f"## {sec_info.get('title', '')} (续)\n\n"
        chunk["content"] = header + chunk["content"]

    return chunks


def process_all(pdf_path: str, output_dir: str) -> Dict:
    """完整预处理流程"""
    os.makedirs(output_dir, exist_ok=True)

    # 1. 提取文本
    raw_file = extract_pdf(pdf_path, output_dir)

    # 2. 检测结构
    structure = detect_structure(raw_file)
    structure_file = os.path.join(output_dir, "structure.json")
    with open(structure_file, "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
    print(f"Structure: {structure_file}")

    # 3. 分块
    chunks = chunk_by_sections(raw_file, output_dir, structure)

    # 更新结构文件，添加分块信息
    for sec in structure["sections"]:
        for chunk in chunks:
            if chunk["section_id"] == sec.get("id"):
                sec["chunk_file"] = chunk["file"]
                break

    with open(structure_file, "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    # 4. 生成分块索引
    chunk_index = {
        "total_chunks": len(chunks),
        "chunks": chunks
    }
    index_file = os.path.join(output_dir, "chunk_index.json")
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(chunk_index, f, ensure_ascii=False, indent=2)

    print(f"Chunks: {len(chunks)} files in {output_dir}/chunks/")

    return {
        "raw_file": raw_file,
        "structure_file": structure_file,
        "chunk_index_file": index_file,
        "total_chunks": len(chunks)
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "extract":
        if len(sys.argv) != 4:
            print("Usage: python preprocess.py extract <pdf_file> <output_dir>")
            sys.exit(1)
        extract_pdf(sys.argv[2], sys.argv[3])

    elif command == "chunk":
        if len(sys.argv) != 4:
            print("Usage: python preprocess.py chunk <raw_text_file> <output_dir>")
            sys.exit(1)
        structure = detect_structure(sys.argv[2])
        chunks = chunk_by_sections(sys.argv[2], sys.argv[3], structure)
        print(f"Created {len(chunks)} chunks")

    elif command == "all":
        if len(sys.argv) != 4:
            print("Usage: python preprocess.py all <pdf_file> <output_dir>")
            sys.exit(1)
        result = process_all(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
