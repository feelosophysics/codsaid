"""학습용 노트북을 새 로컬 커널에서 실행하고 출력 저장.

uv run --group dev python tools/execute_learning_notebook.py
"""
import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager


def execute(root, notebook_path):
    runtime = root / ".notebook-runtime" / "learning"
    runtime.mkdir(parents=True, exist_ok=True)
    os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime)
    os.environ["IPYTHONDIR"] = str(runtime / "ipython")
    os.environ["MPLCONFIGDIR"] = str(runtime / "matplotlib")
    os.environ["PYTHONUTF8"] = "1"
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    with TemporaryDirectory(dir=runtime, prefix="kernel-") as kernel_root:
        spec_dir = Path(kernel_root) / "learning"
        spec_dir.mkdir()
        spec = {
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "A5-1 Learning", "language": "python",
            "env": {"PYTHONUTF8": "1"},
        }
        (spec_dir / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
        client = NotebookClient(notebook, timeout=1800, kernel_name="learning",
                                resources={"metadata": {"path": str(root)}}, record_timing=False)
        client.km = client.create_kernel_manager()
        client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[kernel_root])

        def progress(cell, cell_index):
            if cell.cell_type == "code":
                print(f"Running cell {cell_index + 1}: {cell.source.splitlines()[0]}", flush=True)

        client.on_cell_start = progress
        client.execute()
    nbformat.validate(notebook)
    nbformat.write(notebook, notebook_path)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in code_cells)
    print(f"Executed {len(code_cells)} code cells without errors: {notebook_path}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--notebook", type=Path)
    args = parser.parse_args()
    path = args.notebook or args.root / "notebooks" / "learning_walkthrough.ipynb"
    execute(args.root.resolve(), path.resolve())
