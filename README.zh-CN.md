# skillspector-open — 技能供应链安全扫描器

[English](README.md) | 简体中文

你的智能体正在加载外部技能（skills）。技能是以你的 API 密钥权限运行的未签名代码。本仓库致力于构建一个开源、确定性、纯静态的扫描器来对其进行安全评级——**并发布自身的误报审计报告**，因为一个不敢承认自身误报的扫描器绝不值得信任。

## 状态：pre-v1，如实披露

当前已交付的模块：

1. **`slop-scan.py`** — 首个检测模块。启发式规则、纯标准库、确定性、CI 就绪：检测近似重复代码块、遗留调试钩子、作为正式代码交付的未实现桩（stub）、TODO 密度、占位省略号、超大文件。存在任何 HIGH 严重级别发现时退出码为 `1`，否则为 `0`。
2. **`docs/methodology.md`** — 针对真实技能库的完整已判决安全评估报告（134 个扫描器发现经过人工审查裁定为 0 个真正例，并附带按分类细分的误报分析）。这是本扫描器完整实现所遵循的方法论文档与报告模板。

尚待实现的功能：完整的多检测项扫描器、报告卡（report card）输出格式、每周排行榜。这是我们的路线图——详见标记为 `help wanted` 的 Issue。我们坚持先交付严谨的审计追踪，再交付自动化扫描器。

## 60 秒快速演示

```bash
curl -o slop-scan.py https://raw.githubusercontent.com/empire-mind/skillspector-open/main/slop-scan.py
python3 slop-scan.py examples/sample-project   # 在专门构建的示例上触发 HIGH 级别告警
python3 slop-scan.py --json path/to/skill-repo
```

示例项目上的预期输出已在 [examples/README.md](examples/README.md) 中详细记录——欢迎验证扫描器输出与描述一致，或提出 Issue。

## 设计原则（不可动摇）

- **默认纯静态。** 无需 LLM 介入，无需 API 密钥，在 CI 中数秒内完成。需要输入 OpenAI 密钥的扫描器无法进入严谨的研究机构和实验室。
- **完全确定性。** 相同的代码库 + 相同的扫描器版本 = 每次输出完全相同的报告。版本锁定，评级 100% 可复现。
- **误报审计随代码一同发布。** 每个检测类别都紧跟其已知误报案例分析文档，遵循 `docs/methodology.md` 标准。

## 开发

```bash
python3 -m pytest tests/    # 离线运行，仅依赖标准库 + pytest
```

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 贡献指南

**每个 Issue 和外部 PR 都会在 7 个自然日内获得首次回复。** `good first issue` 任务设计为一个晚上即可完成——特别欢迎新的检测项建议（请务必将检测项与其误报分析一并提交）。完整流程参见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题报告：请阅读组织的 [SECURITY.md](https://github.com/empire-mind/.github/blob/main/SECURITY.md)。

## 致谢

启发式设计思想灵感来自 [garrytan/gstack](https://github.com/garrytan/gstack) (MIT © 2026 Garry Tan) 的评估逻辑；实现完全原创。评估方法论参考了 NVIDIA SkillSpector v2.12.0 进行验证。

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
