---
name: paper-pipeline-zh
version: 1.1.0
description: |
  批量处理学术论文的端到端流水线，为每个PDF生成中文翻译和技术报告。

  触发场景：
  - 用户需要对整个目录的PDF论文进行批量翻译和报告生成
  - 用户使用 /paper-pipeline-zh 命令
  - 用户提到"论文批处理"、"批量翻译论文"、"论文技术报告"等需求

  核心能力：
  1. 并发处理（3篇并行），大幅提升吞吐
  2. 智能分块（章节级），支持超长论文（100+页）
  3. 术语表机制，确保分块翻译一致性
  4. 进度持久化，支持断点续传
  5. 质量检查，防止输出缩水

  输出结构：
  - [input_dir]_translated/  中文翻译文件
  - [input_dir]/reports/     技术报告文件
  - [input_dir]/.cache/      中间缓存（可删除）

  更新日志：
  v1.1.0 (2026-03-30):
  - 新增单篇论文处理支持（直接指定PDF路径）
  - 优化超长论文（100+页）的分块策略
  - 改进翻译Agent的术语一致性
  - 增强报告生成的技术脉络分析
  - 格式检查更严格（行间/行内公式检测）

  v1.0.0 (2026-03-27):
  - 初始版本发布
  - 四阶段流水线架构
  - 3篇并发翻译/报告
---

# Paper Pipeline 中文批处理流水线（优化版）

## 快速开始

```bash
# 批量处理目录
/paper-pipeline-zh /data6/dspapers

# 单篇论文处理（直接指定PDF）
/paper-pipeline-zh /path/to/paper.pdf

# 指定并发数（默认3）
/paper-pipeline-zh /data6/dspapers --parallel 3

# 只处理特定论文
/paper-pipeline-zh /data6/dspapers --papers "paper1.pdf,paper2.pdf"

# 只翻译不生成报告
/paper-pipeline-zh /data6/dspapers --translation-only

# 恢复中断的批处理
/paper-pipeline-zh --resume /data6/dspapers/.progress.json
```

## 使用示例

**单篇论文处理**：
```
/paper-pipeline-zh /data6/后续LLM范式论文/2512olmo3.pdf
```
输出：
- `/data6/后续LLM范式论文_translated/2512olmo3_翻译.md` (972行)
- `/data6/后续LLM范式论文/reports/2512olmo3_report.md` (321行)

**批量处理**：
```
/paper-pipeline-zh /data6/dspapers
```
自动处理目录下所有PDF，3篇并行，支持断点续传。

## 核心工作流（四阶段流水线）

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 1: 预处理（脚本化，快速）                                  │
│  - PDF提取 → 缓存                                               │
│  - 结构检测 → 章节元数据                                        │
│  - 智能分块 → 章节级chunks                                      │
│  - 初始化manifest                                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 2: 并发翻译（3篇并行）                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   Paper 1   │ │   Paper 2   │ │   Paper 3   │               │
│  │  Task Agent │ │  Task Agent │ │  Task Agent │               │
│  │  独立上下文  │ │  独立上下文  │ │  独立上下文  │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│  每个Agent: 读取chunks → 逐块翻译(维护术语表) → 合并输出          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 3: 并发报告（3篇并行）                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   Paper 1   │ │   Paper 2   │ │   Paper 3   │               │
│  │  Task Agent │ │  Task Agent │ │  Task Agent │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│  每个Agent: 读取翻译 → 生成报告(按模板) → 输出                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Phase 4: 后处理（脚本化）                                        │
│  - 格式检查（公式、表格）                                         │
│  - 质量评分                                                      │
│  - 统计汇总                                                      │
│  - 更新manifest                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: 预处理

**目标**：将PDF转换为结构化的中间格式，避免后续重复读取。

### 执行步骤

1. **扫描PDF文件**
   ```bash
   ls <input_dir>/*.pdf
   ```

2. **创建目录结构**
   ```
   <input_dir>_translated/
   <input_dir>/reports/
   <input_dir>/.cache/
   <input_dir>/.cache/<paper_name>/
   <input_dir>/.cache/<paper_name>/raw.txt
   <input_dir>/.cache/<paper_name>/structure.json
   <input_dir>/.cache/<paper_name>/chunks/
   ```

3. **提取PDF文本**
   ```bash
   python3 scripts/preprocess.py extract <pdf_file> <cache_dir>
   ```

4. **检测结构并分块**
   ```bash
   python3 scripts/preprocess.py chunk <raw_text> <cache_dir>
   ```

### 分块策略（章节级优先）

```
优先级：
1. 章节级 - 每个Section作为独立块
2. 小节级 - 超大章节按Subsection切分
3. 段落块 - 仅在必要时使用

分块规则：
- MAX_CHUNK_SIZE = 8000 tokens (~12000字符)
- 表格、公式作为整体不分块
- 保留章节标题作为上下文
```

### structure.json 格式

```json
{
  "title": "DeepSeek LLM",
  "total_pages": 48,
  "sections": [
    {
      "id": "sec_1",
      "title": "Introduction",
      "level": 1,
      "start_page": 3,
      "chunk_file": "chunk_001.md"
    },
    {
      "id": "sec_2",
      "title": "Pre-Training",
      "level": 1,
      "start_page": 4,
      "subsections": [
        {"id": "sec_2_1", "title": "Data", "chunk_file": "chunk_002.md"},
        {"id": "sec_2_2", "title": "Architecture", "chunk_file": "chunk_003.md"}
      ]
    }
  ]
}
```

---

## Phase 2: 并发翻译

**核心原则**：3篇论文并行，每篇使用独立Task Agent，互不干扰。

### 单篇翻译流程

对每篇论文，启动独立Task Agent执行：

```
1. 读取缓存的结构和分块
2. 初始化术语表
3. 逐块翻译:
   - 读取chunk
   - 翻译（参考术语表）
   - 更新术语表
   - 写入翻译结果
4. 合并所有翻译块
5. 质量自检
6. 输出最终文件
```

### 并发控制

```python
# 伪代码
semaphore = Semaphore(3)  # 最多3个并发

for paper in pending_papers:
    semaphore.acquire()
    spawn_task_agent(paper)  # 异步启动
    semaphore.release()      # 完成后释放
```

### 术语表机制

每篇论文维护独立术语表，格式：

```json
{
  "Transformer": "Transformer",
  "attention": "注意力",
  "Multi-Head Attention": "多头注意力",
  "Grouped Query Attention": "分组查询注意力 (GQA)",
  "fine-tuning": "微调"
}
```

**使用方式**：
- 翻译每个chunk时注入当前术语表
- 发现新术语时更新术语表
- 确保全文术语一致

### 翻译模板

必须严格遵循：[translation_template.md](references/translation_template.md)

**公式渲染规范**（关键）：

```
行间公式：独立成行，前后空行
$$
\eta_{opt} = 0.3118 \cdot C^{-0.1250}
$$

行内公式：简短内容，单$符号
学习率 $\eta_{opt}$ 随计算预算增加而减小。

复杂公式：必须转为行间格式
❌ 错误：损失函数为 $\mathcal{L} = -\sum_{i=1}^{N} \log P(y_i|x_i)$
✅ 正确：
损失函数定义如下：
$$\mathcal{L} = -\sum_{i=1}^{N} \log P(y_i|x_i)$$
```

---

## Phase 3: 并发报告

**原则**：翻译完成后，立即开始报告生成，同样3篇并行。

### 单篇报告流程

```
1. 读取完整翻译文件
2. 读取结构元数据
3. 按模板生成报告:
   - 论文信息
   - 核心贡献（一句话总结）
   - 技术方案（具体参数）
   - 实验结果（表格展示）
   - 技术脉络（深度分析）
4. 格式美化
5. 输出报告文件
```

### 报告模板

必须严格遵循：[report_template.md](references/report_template.md)

**排版规范**：
- 标题层级清晰
- 表格对齐
- 关键数字加粗
- 使用引用块突出重要结论
- 技术脉络用ASCII图展示

---

## Phase 4: 后处理

**目标**：统一格式检查和质量汇总。

### 格式检查脚本

```bash
python3 scripts/format_check.py <translation_file>
python3 scripts/format_check.py <report_file> --type report
```

检查项：
- 公式格式正确性
- 表格语法正确性
- 标题层级完整性
- 文件编码UTF-8

### 质量评分

```
翻译质量 = 结构分(30%) + 长度分(30%) + 格式分(20%) + 抽检分(20%)

报告质量 = 结构分(25%) + 深度分(40%) + 格式分(20%) + 脉络分(15%)
```

### 统计汇总

生成批处理报告：
- 处理论文数量
- 平均质量分数
- 耗时统计
- 问题列表

---

## 进度文件格式

`.progress.json` 存储在输入目录：

```json
{
  "batch_id": "batch_20260327_001",
  "input_dir": "/data6/dspapers",
  "created_at": "2026-03-27T10:00:00Z",
  "config": {
    "parallel": 3,
    "translation_only": false
  },
  "papers": [
    {
      "pdf_file": "paper1.pdf",
      "status": "completed",
      "phases": {
        "preprocess": "completed",
        "translation": "completed",
        "report": "completed",
        "postprocess": "completed"
      },
      "cache_dir": ".cache/paper1",
      "translation_file": "paper1_翻译.md",
      "report_file": "paper1_report.md",
      "quality_score": 0.92,
      "processed_at": "2026-03-27T10:30:00Z"
    }
  ],
  "statistics": {
    "total": 10,
    "completed": 3,
    "in_progress": 3,
    "pending": 4,
    "failed": 0
  }
}
```

---

## 断点续传

支持从任意阶段恢复：

```bash
# 自动检测进度文件
/paper-pipeline-zh /data6/dspapers

# 或明确指定
/paper-pipeline-zh --resume /data6/dspapers/.progress.json
```

恢复逻辑：
- 读取progress.json
- 跳过已完成的论文
- 从in_progress状态继续
- 重新处理failed状态

---

## 防止质量衰减的机制

| 机制 | 实现方式 |
|------|----------|
| 上下文隔离 | 每篇论文独立Task Agent |
| 模板强制 | 每个Agent重新加载模板文件 |
| 术语一致性 | 分块翻译时维护术语表 |
| 并发隔离 | 每个Agent独立工作目录 |
| 质量检查 | 自动评分+人工抽检提示 |

---

## 文件说明

### scripts/
| 文件 | 功能 |
|------|------|
| `read_pdf.py` | PDF文本提取（复用现有） |
| `preprocess.py` | 预处理：提取、结构检测、分块 |
| `merge_chunks.py` | 合并分块输出 |
| `format_check.py` | 格式检查 |

### references/
| 文件 | 内容 |
|------|------|
| `translation_template.md` | 翻译模板+公式规范 |
| `report_template.md` | 报告模板+排版规范 |
| `quality_standards.md` | 质量标准 |
| `style_anchor.md` | 高质量样本参考 |

### subagents/
| 文件 | 用途 |
|------|------|
| `translator.md` | 翻译Task Agent指令 |
| `reporter.md` | 报告Task Agent指令 |

---

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| PDF读取失败 | 标记failed，继续处理其他 |
| 单块翻译失败 | 重试该块，超过3次标记failed |
| 合并失败 | 保留分块结果，提示手动合并 |
| 报告生成失败 | 标记failed，翻译结果保留 |

---

## 使用建议

1. **首次使用**：先用 `--papers` 测试1-2篇
2. **大批量**：建议分批，每批10-15篇
3. **缓存清理**：完成后可删除 `.cache/` 目录节省空间
4. **质量验证**：定期抽检输出质量
