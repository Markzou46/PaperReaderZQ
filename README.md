# Paper Pipeline 中文批处理流水线

批量处理学术论文的端到端流水线，为每个PDF生成中文翻译和技术报告。

## 安装

将 `paper-pipeline-zh.skill` 放入 Claude Code 的 skills 目录：

```bash
cp paper-pipeline-zh.skill ~/.claude/skills/
```

## 使用方法

```bash
# 单篇论文
/paper-pipeline-zh /path/to/paper.pdf

# 批量处理
/paper-pipeline-zh /data6/dspapers
```

## 输出示例

**输入**: 117页OLMo 3论文

**输出**:
- 翻译: 972行, 78KB
- 报告: 321行, 包含技术脉络分析

## License

MIT
