from fastapi import APIRouter
from typing import Dict, Any
from app.evals.benchmark_runner import BenchmarkRunner

router = APIRouter(prefix="/evals", tags=["Evaluation & Benchmarks"])

@router.post("/run-benchmark")
async def run_eval_benchmark() -> Dict[str, Any]:
    return BenchmarkRunner.run_benchmark()
