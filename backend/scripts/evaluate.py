"""RAG 准确率评测脚本。

评测集：每条包含 question / expected_doc_title（应命中的文献）/ expected_keywords（答案应包含的关键词）
指标：
  - 检索命中率 HitRate@k：top-k 召回中包含正确文献的比例
  - MRR：正确文献在召回列表中排名倒数的均值
  - 答案关键词覆盖率：标准关键词在生成答案中的命中比例（忠实度的粗粒度代理）
输出：控制台报告 + backend/data/eval_report.md

运行：cd backend && venv/Scripts/python.exe scripts/evaluate.py
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.services.rag import recall_chunks, rerank_chunks, rewrite_question

# ---------------- 评测集（基于 6 篇真实馆藏文献构造）----------------
# expected_doc 为文献标题的子串，用于匹配检索命中的 chunk
EVAL_SET = [
    # 《从"互联网+"到"人工智能+"》
    {
        "question": "《关于深入实施“人工智能+”行动的意见》是哪一年印发的？",
        "expected_doc": "互联网",
        "keywords": ["2025", "国务院"],
    },
    {
        "question": "“互联网+”行动的指导意见是哪一年颁布的？",
        "expected_doc": "互联网",
        "keywords": ["2015"],
    },
    {
        "question": "人工智能的社会着陆有哪三大着陆点？",
        "expected_doc": "互联网",
        "keywords": ["生产", "服务", "协同"],
    },
    {
        "question": "这篇文献的作者是谁？",
        "expected_doc": "互联网",
        "keywords": ["曾巍", "姜帆"],
    },
    # 《SWEWT-Picker 地震初至拾取》
    {
        "question": "SWEWT-Picker 模型用于解决什么问题？",
        "expected_doc": "SWEWT",
        "keywords": ["地震", "初至", "拾取"],
    },
    {
        "question": "SWEWT-Picker 模型的第一作者是谁？",
        "expected_doc": "SWEWT",
        "keywords": ["原健龙"],
    },
    # 《强震动记录滤波》
    {
        "question": "强震动记录滤波截止频率研究的第一作者是谁？",
        "expected_doc": "强震动",
        "keywords": ["郭文轩"],
    },
    {
        "question": "强震动记录滤波研究发表在哪个期刊？",
        "expected_doc": "强震动",
        "keywords": ["地球物理学报"],
    },
    # 《非晶碳原子建模》
    {
        "question": "非晶碳原子建模综述发表在哪个期刊？",
        "expected_doc": "非晶碳",
        "keywords": ["新型炭材料"],
    },
    {
        "question": "非晶碳原子建模综述的作者是谁？",
        "expected_doc": "非晶碳",
        "keywords": ["张圣斌"],
    },
    # 《区域供热》
    {
        "question": "人工智能赋能区域供热研究的核心主题是什么？",
        "expected_doc": "区域供热",
        "keywords": ["供热", "全生命周期"],
    },
    # 《化学反应机理》
    {
        "question": "人工智能驱动的化学反应机理研究发表在哪个期刊？",
        "expected_doc": "化学反应",
        "keywords": ["有机化学"],
    },
]


def eval_retrieval(query: str, expected: str, chunks: list[dict]) -> tuple[bool, int]:
    """返回 (是否命中, 正确文献的排名；未命中记 0)。"""
    for rank, c in enumerate(chunks, start=1):
        if expected in c["title"]:
            return True, rank
    return False, 0


def eval_keywords(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    hit = sum(1 for k in keywords if k.lower() in answer.lower())
    return hit / len(keywords)


async def run_eval(k_values=(1, 3, 5)) -> str:
    lines = []
    lines.append("# RAG 检索准确率评测报告")
    lines.append("")
    lines.append(f"- 评测时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 召回模型：{settings.embedding_model}（top-{settings.recall_top_k}）")
    lines.append(f"- 重排模型：{settings.rerank_model}（top-{settings.rerank_top_n}）")
    lines.append(f"- 评测集规模：{len(EVAL_SET)} 条")
    lines.append("")

    hit_counts = {k: 0 for k in k_values}
    mrr_sum, keyword_scores = 0.0, []

    lines.append("## 明细")
    lines.append("")
    lines.append("| # | 问题 | 期望文献 | 命中排名 | 关键词覆盖 |")
    lines.append("|---|------|----------|----------|------------|")

    for i, item in enumerate(EVAL_SET, start=1):
        query = await rewrite_question(item["question"], history=[])
        chunks = recall_chunks(query)
        chunks = await rerank_chunks(query, chunks)
        ok, rank = eval_retrieval(query, item["expected_doc"], chunks)
        for k in k_values:
            if ok and rank <= k:
                hit_counts[k] += 1
        if ok:
            mrr_sum += 1.0 / rank
        lines.append(
            f"| {i} | {item['question'][:20]} | {item['expected_doc']} "
            f"| {'#' + str(rank) if ok else '未命中'} | - |"
        )

    n = len(EVAL_SET)
    lines.append("")
    lines.append("## 汇总指标")
    lines.append("")
    for k in k_values:
        lines.append(f"- **HitRate@{k}**：{hit_counts[k]}/{n} = {hit_counts[k] / n:.1%}")
    lines.append(f"- **MRR**：{mrr_sum / n:.4f}")
    lines.append("")
    lines.append("> 注：答案忠实度需接入生成端后在完整链路上评测（关键词覆盖率列）。")
    lines.append("> 评测集与脚本位于 backend/scripts/evaluate.py，可直接扩充作为论文实验素材。")

    report = "\n".join(lines)
    return report


if __name__ == "__main__":
    if not settings.llm_api_key or settings.llm_api_key.startswith("sk-xxxx"):
        print("[error] 请先在 backend/.env 中配置 LLM_API_KEY")
        sys.exit(1)
    report = asyncio.run(run_eval())
    print(report)
    out = Path(__file__).resolve().parents[1] / "data" / "eval_report.md"
    out.write_text(report, encoding="utf-8")
    print(f"\n报告已保存：{out}")
