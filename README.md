# Paper Pipeline 中文批处理流水线

批量处理学术论文的端到端流水线，为PDF论文生成中文翻译和技术报告。

## 安装

将 `paper-pipeline-zh` 目录放入 Claude Code 的 skills 目录：

```bash
cp -r paper-pipeline-zh ~/.claude/skills/
```

## 使用方法

### 批量处理文件夹（推荐）

```bash
/paper-pipeline-zh /data6/dspapers
```

**输入**：一个包含多个PDF的文件夹

**输出**：
```
/data6/dspapers/              # 原始PDF文件夹
├── paper1.pdf
├── paper2.pdf
└── ...

/data6/dspapers_translated/   # 中文翻译文件夹
├── paper1_翻译.md
├── paper2_翻译.md
└── ...

/data6/dspapers/reports/      # 技术报告文件夹
├── paper1_report.md
├── paper2_report.md
└── ...
```

### 单篇论文处理

```bash
/paper-pipeline-zh /path/to/paper.pdf
```

### 高级选项

```bash
# 指定并发数（默认3篇并行）
/paper-pipeline-zh /data6/dspapers --parallel 3

# 只处理特定论文
/paper-pipeline-zh /data6/dspapers --papers "paper1.pdf,paper2.pdf"

# 只翻译不生成报告
/paper-pipeline-zh /data6/dspapers --translation-only

# 恢复中断的批处理
/paper-pipeline-zh --resume /data6/dspapers/.progress.json
```

## 特性

- **批量并发处理**: 3篇论文并行，大幅提升吞吐
- **超长论文支持**: 智能分块策略，支持100+页论文
- **术语一致性**: 分块翻译时维护术语表
- **断点续传**: 进度持久化，中断后可恢复
- **质量检查**: 自动检测公式格式、表格语法等

## 输出示例

批量处理 `/data6/后续LLM范式论文/` 目录（10篇论文）：

```
输入: 10个PDF文件

输出:
├── 后续LLM范式论文_translated/   # 10个翻译文件
│   ├── 2503Gemma 3_翻译.md
│   ├── 2505Qwen3_翻译.md
│   └── ...
└── 后续LLM范式论文/reports/      # 10个报告文件
    ├── 2503Gemma 3_report.md
    ├── 2505Qwen3_report.md
    └── ...
```

单篇处理示例（OLMo 3, 117页）：
- 翻译: 972行, 78KB
- 报告: 321行, 包含技术脉络分析

## 文件结构

```
paper-pipeline-zh/
├── SKILL.md                    # 主入口文档
├── scripts/                    # 处理脚本
│   ├── preprocess.py           # PDF提取、分块
│   ├── format_check.py         # 格式检查
│   ├── read_pdf.py             # PDF解析
│   └── merge_chunks.py         # 分块合并
├── references/                 # 模板参考
│   ├── translation_template.md
│   ├── report_template.md
│   ├── quality_standards.md
│   └── style_anchor.md
├── subagents/                  # Agent指令
│   ├── translator.md
│   └── reporter.md
└── assets/
    └── progress_schema.json
```

## 版本历史

### v1.1.0 (2026-03-30)
- 新增单篇论文处理支持
- 优化超长论文（100+页）的分块策略
- 改进翻译Agent的术语一致性
- 增强报告生成的技术脉络分析

### v1.0.0 (2026-03-27)
- 初始版本发布
- 四阶段流水线架构
- 3篇并发翻译/报告

## License

MIT
