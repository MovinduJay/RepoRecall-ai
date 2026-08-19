from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.evaluation.dataset import load_evaluation_dataset
from app.evaluation.runner import EvaluationReport, run_evaluation


async def run(
    repository_id: uuid.UUID,
    dataset_path: Path,
    *,
    k: int,
    output_path: Path | None,
) -> EvaluationReport:
    dataset = load_evaluation_dataset(dataset_path)
    report = await run_evaluation(repository_id, dataset, k=k)
    _print_summary(report)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report_to_dict(report), indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Report written to {output_path}")

    return report


def report_to_dict(report: EvaluationReport) -> dict[str, Any]:
    serialized = asdict(report)
    serialized["repository_id"] = str(report.repository_id)
    return serialized


def _print_summary(report: EvaluationReport) -> None:
    print(f"Repository: {report.dataset_repository} ({report.repository_id})")
    print(f"Queries: {next(iter(report.strategies.values())).aggregate.query_count}")
    print(f"Evaluation cutoff: {report.k}")
    print()
    print(
        f"{'Strategy':<20} {'Recall':>8} {'MRR':>8} "
        f"{'nDCG':>8} {'Hit rate':>10}"
    )
    for strategy in report.strategies.values():
        aggregate = strategy.aggregate
        print(
            f"{strategy.strategy:<20} "
            f"{aggregate.recall_at_k:>8.4f} "
            f"{aggregate.mean_reciprocal_rank:>8.4f} "
            f"{aggregate.ndcg_at_k:>8.4f} "
            f"{aggregate.linked_fix_hit_rate:>10.4f}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare RepoRecall retrieval strategies on a curated dataset."
    )
    parser.add_argument("repository_id", type=uuid.UUID)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    asyncio.run(
        run(
            arguments.repository_id,
            arguments.dataset,
            k=arguments.k,
            output_path=arguments.output,
        )
    )
