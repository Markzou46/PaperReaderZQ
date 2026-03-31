#!/usr/bin/env python3
"""
合并分块翻译结果

用法:
    python merge_chunks.py <chunks_dir> <output_file> [--structure <structure.json>]
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Optional


def load_chunk_index(chunks_dir: str) -> Dict:
    """加载分块索引"""
    index_file = os.path.join(os.path.dirname(chunks_dir), "chunk_index.json")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"total_chunks": 0, "chunks": []}


def merge_chunks(chunks_dir: str, output_file: str, structure_file: Optional[str] = None) -> None:
    """合并所有分块翻译"""
    chunk_index = load_chunk_index(chunks_dir)

    # 按索引顺序读取所有分块
    merged_content = []

    for chunk_info in chunk_index.get("chunks", []):
        chunk_file = os.path.join(chunks_dir, chunk_info["file"])
        if not os.path.exists(chunk_file):
            # 尝试查找翻译后的文件
            translated_file = chunk_file.replace(".md", "_翻译.md")
            if os.path.exists(translated_file):
                chunk_file = translated_file
            else:
                print(f"Warning: Chunk file not found: {chunk_file}")
                continue

        with open(chunk_file, "r", encoding="utf-8") as f:
            content = f.read()
            merged_content.append(content)

    # 合并内容
    final_content = "\n\n---\n\n".join(merged_content)

    # 清理重复的章节标题
    final_content = clean_duplicate_headers(final_content)

    # 写入输出文件
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"Merged {len(chunk_index.get('chunks', []))} chunks -> {output_file}")
    print(f"Total lines: {len(final_content.splitlines())}")


def clean_duplicate_headers(content: str) -> str:
    """清理重复的章节标题"""
    lines = content.split("\n")
    cleaned_lines = []
    prev_header = None

    for line in lines:
        # 检测章节标题
        header_match = re.match(r'^#{1,3}\s+(.+?)(?:\s*\(续\))?$', line)
        if header_match:
            current_header = header_match.group(1).strip()
            # 如果与前一个标题相同，跳过
            if current_header == prev_header:
                continue
            prev_header = current_header
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def merge_with_structure(chunks_dir: str, output_file: str, structure_file: str) -> None:
    """按结构信息合并分块"""
    with open(structure_file, "r", encoding="utf-8") as f:
        structure = json.load(f)

    chunk_index = load_chunk_index(chunks_dir)

    # 构建分块映射
    chunk_map = {}
    for chunk_info in chunk_index.get("chunks", []):
        chunk_map[chunk_info["file"]] = chunk_info

    merged_sections = []

    # 按章节顺序合并
    for section in structure.get("sections", []):
        section_content = []

        # 添加章节标题
        section_title = section.get("title", "")
        section_content.append(f"\n## {section_title}\n")

        # 查找对应的分块
        chunk_file = section.get("chunk_file")
        if chunk_file:
            chunk_path = os.path.join(chunks_dir, chunk_file)
            if os.path.exists(chunk_path):
                with open(chunk_path, "r", encoding="utf-8") as f:
                    section_content.append(f.read())

        # 处理子章节
        for subsection in section.get("subsections", []):
            sub_chunk_file = subsection.get("chunk_file")
            if sub_chunk_file:
                sub_chunk_path = os.path.join(chunks_dir, sub_chunk_file)
                if os.path.exists(sub_chunk_path):
                    with open(sub_chunk_path, "r", encoding="utf-8") as f:
                        section_content.append(f.read())

        merged_sections.append("\n".join(section_content))

    # 最终合并
    final_content = "\n\n---\n\n".join(merged_sections)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"Merged with structure: {output_file}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    chunks_dir = sys.argv[1]
    output_file = sys.argv[2]

    structure_file = None
    if len(sys.argv) >= 5 and sys.argv[3] == "--structure":
        structure_file = sys.argv[4]

    if structure_file:
        merge_with_structure(chunks_dir, output_file, structure_file)
    else:
        merge_chunks(chunks_dir, output_file)


if __name__ == "__main__":
    main()
