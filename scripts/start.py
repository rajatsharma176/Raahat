#!/usr/bin/env python3
"""
RAAHAT Startup Script

Runs:
1. Knowledge base ingestion (if needed)
2. FastAPI backend server

Usage:
    cd backend
    python ../scripts/start.py
"""
import subprocess
import sys
import os
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"


def check_rag_index():
    index_path = BACKEND / "data" / "faiss_index"
    if not (index_path / "index.faiss").exists():
        print("📚 Building RAG knowledge base index...")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "ingest_knowledge.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode == 0:
            print("✅ Knowledge base indexed successfully")
        else:
            print(f"⚠️  RAG indexing failed: {result.stderr[:200]}")
            print("   (System will continue with mock retrieval)")
    else:
        print("✅ RAG index found")


def start_backend():
    print("\n🚀 Starting RAAHAT Backend...")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    env["PYTHONIOENCODING"] = "utf-8"

    subprocess.run(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ],
        cwd=str(BACKEND),
        env=env,
    )


if __name__ == "__main__":
    check_rag_index()
    start_backend()
