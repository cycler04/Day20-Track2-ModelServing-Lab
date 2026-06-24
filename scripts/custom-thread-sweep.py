#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

try:
    from llama_cpp import Llama
except ImportError:
    print("ERROR: llama_cpp not installed.")
    sys.exit(1)

PROMPT = "Explain continuous batching in detail and why it improves serving throughput."

def load_active() -> str:
    p = Path("models/active.json")
    if not p.exists():
        print("ERROR: active.json missing.")
        sys.exit(1)
    return json.loads(p.read_text())["primary_model"]

def load_hardware() -> dict:
    p = Path("hardware.json")
    return json.loads(p.read_text()) if p.exists() else {}

def measure_one(llm: Llama, prompt: str, max_tokens: int = 64) -> float:
    start = time.perf_counter()
    first_token_at = None
    n_tokens = 0
    for chunk in llm.create_completion(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.7,
        stream=True,
    ):
        text = chunk["choices"][0].get("text", "")
        if text and first_token_at is None:
            first_token_at = time.perf_counter()
        if text:
            n_tokens += 1
    end = time.perf_counter()
    if first_token_at is None or n_tokens <= 1:
        return 0.0
    decode_ms = (end - first_token_at) * 1000.0
    tpot_ms = decode_ms / (n_tokens - 1)
    return 1000.0 / tpot_ms

def main():
    model_path = load_active()
    hw = load_hardware()
    physical_cores = hw.get("cpu", {}).get("cores_physical") or 4
    logical_cores = hw.get("cpu", {}).get("cores_logical") or 8
    
    # Grid of threads to sweep
    threads_to_test = sorted({1, 2, physical_cores // 2, physical_cores, logical_cores, logical_cores + 4})
    threads_to_test = [t for t in threads_to_test if t > 0]
    
    print(f"==> Custom Thread Sweep on {Path(model_path).name}")
    print(f"    Physical Cores: {physical_cores}, Logical Cores: {logical_cores}")
    print(f"    Sweeping threads: {threads_to_test}")
    
    results = []
    for t in threads_to_test:
        print(f"--- Testing t={t} ---")
        llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=t,
            n_gpu_layers=0,
            verbose=False
        )
        
        # Warmup
        _ = measure_one(llm, "Hello.", max_tokens=8)
        
        # Bench runs
        rates = []
        for _ in range(3):
            tok_s = measure_one(llm, PROMPT, max_tokens=64)
            if tok_s > 0:
                rates.append(tok_s)
        
        avg_rate = sum(rates) / len(rates) if rates else 0.0
        results.append({"threads": t, "tok_s": avg_rate})
        print(f"    t={t:2d} -> {avg_rate:.2f} tok/s")
        
        del llm # free memory
        
    out_dir = Path("benchmarks")
    out_dir.mkdir(exist_ok=True)
    
    best = max(results, key=lambda r: r["tok_s"])
    
    md = f"# Bonus — Thread sweep\n\n"
    md += f"Model: `{Path(model_path).name}`  ·  GPU layers: `0` (CPU Backend)\n\n"
    md += "| threads | tg128 (tok/s) |\n|---:|---:|\n"
    md += "\n".join(f"| {r['threads']} | {r['tok_s']:.1f} |" for r in results)
    md += f"\n\n**Best**: `-t {best['threads']}` at {best['tok_s']:.1f} tok/s.\n\n"
    md += (
        "Look at the curve. If it peaks around your **physical** core count and "
        "drops as you go higher, that's the memory-bandwidth ceiling: extra threads "
        "fight over the same memory channels and slow each other down.\n"
    )
    
    (out_dir / "bonus-thread-sweep.md").write_text(md)
    (out_dir / "bonus-thread-sweep.json").write_text(json.dumps(results, indent=2))
    
    print("\nWrote benchmarks/bonus-thread-sweep.md and .json")
    
if __name__ == "__main__":
    main()
