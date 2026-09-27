from typing import Any

from fastapi import APIRouter

from app.evals.benchmark_runner import BenchmarkRunner
from app.evals.retrieval_metrics import run_evaluation

router = APIRouter(prefix="/evals", tags=["Evaluation & Benchmarks"])

@router.post("/run-benchmark")
def run_eval_benchmark() -> dict[str, Any]:
    return BenchmarkRunner.run_benchmark()

@router.get("/retrieval-metrics")
def run_retrieval_metrics(limit: int | None = None) -> dict[str, Any]:
    """Recall@5/10, Precision@5/10, MRR and citation accuracy over the benchmark set."""
    return run_evaluation(limit=limit)
