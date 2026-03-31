#!/usr/bin/env python3
"""
格式检查脚本

用法:
    python format_check.py <file> [--type translation|report]
"""

import os
import sys
import re
import json
from typing import Dict, List, Tuple


def check_translation(file_path: str) -> Dict:
    """检查翻译文件格式"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    results = {
        "file": file_path,
        "type": "translation",
        "passed": True,
        "issues": [],
        "stats": {}
    }

    # 统计
    lines = content.split("\n")
    results["stats"]["total_lines"] = len(lines)
    results["stats"]["total_chars"] = len(content)

    # 检查标题
    title_count = len(re.findall(r'^# .+', content, re.MULTILINE))
    if title_count == 0:
        results["issues"].append("缺少主标题")
        results["passed"] = False

    # 检查摘要
    if "摘要" not in content and "abstract" not in content.lower():
        results["issues"].append("缺少摘要部分")
        results["passed"] = False

    # 检查章节结构
    h2_count = len(re.findall(r'^## .+', content, re.MULTILINE))
    results["stats"]["h2_count"] = h2_count
    if h2_count < 3:
        results["issues"].append(f"章节过少: {h2_count}个")
        results["passed"] = False

    # 检查公式格式
    formula_issues = check_formulas(content)
    results["issues"].extend(formula_issues)
    if formula_issues:
        results["passed"] = False

    # 检查表格格式
    table_issues = check_tables(content)
    results["issues"].extend(table_issues)

    # 检查未翻译内容（大段英文）
    english_blocks = find_english_blocks(content)
    if english_blocks:
        results["issues"].append(f"发现{len(english_blocks)}处疑似未翻译内容")
        results["stats"]["untranslated_blocks"] = english_blocks[:5]  # 只记录前5个

    return results


def check_report(file_path: str) -> Dict:
    """检查报告文件格式"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    results = {
        "file": file_path,
        "type": "report",
        "passed": True,
        "issues": [],
        "stats": {}
    }

    lines = content.split("\n")
    results["stats"]["total_lines"] = len(lines)
    results["stats"]["total_chars"] = len(content)

    # 检查必需部分
    required_sections = [
        ("论文信息", ["论文信息", "paper information"]),
        ("核心贡献", ["核心贡献", "core contribution", "贡献"]),
        ("技术方案", ["技术方案", "technical", "方案"]),
        ("实验结果", ["实验结果", "experiment", "结果"]),
        ("技术脉络", ["技术脉络", "脉络", "演进", "定位"])
    ]

    for section_name, keywords in required_sections:
        found = any(kw in content for kw in keywords)
        if not found:
            results["issues"].append(f"缺少部分: {section_name}")
            results["passed"] = False

    # 检查一句话总结
    if "一句话总结" not in content:
        results["issues"].append("缺少'一句话总结'")

    # 检查表格数量
    table_count = len(re.findall(r'\|.*\|.*\|', content))
    results["stats"]["table_rows"] = table_count
    if table_count < 10:
        results["issues"].append(f"表格数据偏少: {table_count}行")

    # 检查具体数字（数字密度）
    number_count = len(re.findall(r'\d+\.?\d*%?', content))
    results["stats"]["number_count"] = number_count
    if number_count < 20:
        results["issues"].append(f"具体数字偏少: {number_count}个")

    return results


def check_formulas(content: str) -> List[str]:
    """检查公式格式"""
    issues = []

    # 检查行内公式是否过长
    inline_formulas = re.findall(r'\$([^\$]+)\$', content)
    for formula in inline_formulas:
        if len(formula) > 50:
            issues.append(f"行内公式过长（建议转为行间）: ${formula[:30]}...")

    # 检查公式是否闭合
    dollar_count = content.count('$')
    if dollar_count % 2 != 0:
        issues.append("公式符号$未正确闭合")

    # 检查$$是否成对
    double_dollar_count = content.count('$$')
    if double_dollar_count % 2 != 0:
        issues.append("公式符号$$未正确闭合")

    return issues


def check_tables(content: str) -> List[str]:
    """检查表格格式"""
    issues = []

    # 查找表格
    tables = re.findall(r'(\|[^\n]+\|\n)+', content)

    for i, table in enumerate(tables):
        lines = table.strip().split("\n")
        if len(lines) < 2:
            issues.append(f"表格{i+1}不完整")
            continue

        # 检查分隔行
        if not re.match(r'^\|[-:\s|]+\|$', lines[1]):
            issues.append(f"表格{i+1}缺少正确的分隔行")

    return issues


def find_english_blocks(content: str, min_length: int = 100) -> List[str]:
    """查找疑似未翻译的英文块"""
    # 查找连续英文文本块
    pattern = r'[A-Za-z][A-Za-z\s,\.\:\;\-\(\)\[\]]{' + str(min_length) + r',}'
    matches = re.findall(pattern, content)

    # 过滤掉公式中的英文
    filtered = []
    for match in matches:
        # 排除常见的专有名词和术语
        if not any(skip in match for skip in ['Figure', 'Table', 'Section', 'Equation', 'Algorithm']):
            filtered.append(match[:50] + "..." if len(match) > 50 else match)

    return filtered


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    file_path = sys.argv[1]
    file_type = "translation"

    if len(sys.argv) >= 4 and sys.argv[2] == "--type":
        file_type = sys.argv[3]

    if file_type == "report":
        results = check_report(file_path)
    else:
        results = check_translation(file_path)

    # 输出结果
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # 返回状态码
    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
