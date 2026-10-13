"""두 노트북을 현재 Python 환경에서 처음부터 실행하고 출력과 함께 저장한다.

전역/사용자 Jupyter 커널을 설치하지 않고 저장소 안의 임시 커널 설정을 사용한다.
실행 위치는 notebooks/ 폴더로, Jupyter에서 직접 열었을 때와 같다.
"""
import json
import os
from pathlib import Path
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager

NOTEBOOKS = ("backprop_derivation.ipynb", "probability_loss.ipynb")


def main():
    """노트북을 순서대로 실행하고 오류가 있으면 중단한다."""
    root = Path(__file__).resolve().parents[1]
    runtime = root / ".notebook-runtime"
    kernel_dir = runtime / "kernels" / "a2-1"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    spec = {"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "A2-1", "language": "python"}
    (kernel_dir / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime)
    os.environ["IPYTHONDIR"] = str(runtime / "ipython")
    os.environ["MPLCONFIGDIR"] = str(runtime / "matplotlib")
    for name in NOTEBOOKS:
        path = root / "notebooks" / name
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        client = NotebookClient(notebook, timeout=180, kernel_name="a2-1",
                                resources={"metadata": {"path": str(path.parent)}},
                                record_timing=False)
        client.km = client.create_kernel_manager()
        client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[str(runtime / "kernels")])
        client.execute()
        # 다른 컴퓨터에서도 일반 Python 커널로 열 수 있게 저장한다.
        notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
        nbformat.write(notebook, path)
        count = sum(cell.cell_type == "code" for cell in notebook.cells)
        print(f"Executed {count} code cells without errors: notebooks/{name}")


if __name__ == "__main__":
    main()
