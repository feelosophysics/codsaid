"""Verify the current project Python can run a real Jupyter kernel without training.

    uv run --group dev python tools/check_notebook_kernel.py
"""
import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--kernel", help="등록된 커널 이름 (Mac: a5-1-mac-demo)")
args = parser.parse_args()
runtime = ROOT / ".notebook-runtime"
runtime.mkdir(exist_ok=True)
os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime)
os.environ["IPYTHONDIR"] = str(runtime / "ipython")
os.environ["MPLCONFIGDIR"] = str(runtime / "matplotlib")

with TemporaryDirectory(prefix="kernel-check-", dir=runtime) as work:
    spec_dir = Path(work) / "a5-1-check"
    spec_dir.mkdir()
    (spec_dir / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "A5-1 kernel check", "language": "python",
        "env": {"PYTHONUTF8": "1"},
    }), encoding="utf-8")
    notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_code_cell("3 + 7"),
        nbformat.v4.new_code_cell(next(
            cell.source for cell in nbformat.read(
                ROOT / "notebooks/analysis_report.ipynb", as_version=4).cells
            if cell.cell_type == "code")),
        nbformat.v4.new_code_cell("""import json, sys
import ipykernel, numpy, pandas, sklearn
from src.data import load_data
print(json.dumps({"python": sys.version.split()[0], "executable": sys.executable,
                  "ipykernel": ipykernel.__version__, "rows": len(load_data())}))"""),
    ])
    client = NotebookClient(notebook, timeout=60, kernel_name=args.kernel or "a5-1-check",
                            resources={"metadata": {"path": str(ROOT / "notebooks")}})
    client.km = client.create_kernel_manager()
    if not args.kernel:
        client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[work])
    client.execute()
    assert notebook.cells[0].outputs[0].data["text/plain"] == "10"
    text = "".join(output.get("text", "") for output in notebook.cells[2].outputs)
    details = json.loads(text)
    assert details["rows"] == 10000
    assert Path(details["executable"]).resolve() == Path(sys.executable).resolve()
    print(json.dumps({"passed": True, "arithmetic": 10, **details}, ensure_ascii=False))
