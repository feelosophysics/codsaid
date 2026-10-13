"""분석 노트북을 현재 Python 환경의 로컬 커널로 처음부터 실행하고 출력까지 저장한다.

전역·사용자 Jupyter 커널을 설치하지 않는다.

    uv run --group dev python tools/execute_notebook.py
"""
import json
import os
import sys
from pathlib import Path

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient


def main():
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".notebook-runtime"
    kernel_dir = runtime / "kernels" / "a5-1"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    spec = {"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "A5-1", "language": "python",
            "env": {"PYTHONUTF8": "1"}}
    (kernel_dir / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime)
    os.environ["IPYTHONDIR"] = str(runtime / "ipython")
    os.environ["MPLCONFIGDIR"] = str(runtime / "matplotlib")
    path = root / "notebooks" / "analysis_report.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    client = NotebookClient(notebook, timeout=1800, kernel_name="a5-1",
                            resources={"metadata": {"path": str(root)}}, record_timing=False)
    client.km = client.create_kernel_manager()
    client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[str(runtime / "kernels")])
    client.execute()
    # 다른 컴퓨터에서도 일반 Python 커널로 열 수 있게 저장한다.
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbformat.write(notebook, path)
    count = sum(cell.cell_type == "code" for cell in notebook.cells)
    print(f"Executed {count} code cells without errors: {path}")


if __name__ == "__main__":
    main()
