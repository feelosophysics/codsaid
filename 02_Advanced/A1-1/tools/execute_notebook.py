"""Execute the report in the current Python environment, using a local kernel.

No installation of a global/user Jupyter kernel is needed.
"""
from datetime import datetime, timedelta, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client.kernelspec import KernelSpecManager


def portable_outputs(value, root):
    """Keep machine-specific checkout paths out of published notebook outputs."""
    if isinstance(value, str):
        for prefix in (str(root), root.as_posix(), str(root).replace('\\', '\\\\')):
            value = value.replace(prefix, '.')
        return value
    if isinstance(value, list):
        return [portable_outputs(item, root) for item in value]
    if isinstance(value, dict):
        return value.__class__({key: portable_outputs(item, root) for key, item in value.items()})
    return value


def file_digest(path):
    """Normalize text line endings so Git checkout does not invalidate a receipt."""
    data = path.read_bytes()
    if path.suffix != ".npy":
        data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    kst = timezone(timedelta(hours=9))
    started = datetime.now(kst)
    evidence_files = sorted([
        *root.glob("src/*.py"), *root.glob("data/sample/*"),
        root / "pyproject.toml", root / "uv.lock", Path(__file__).resolve(),
    ])
    before = {file.relative_to(root).as_posix(): file_digest(file) for file in evidence_files}
    runtime = root / ".notebook-runtime"
    kernel_dir = runtime / "kernels" / "a1-check"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    spec = {"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "A1 check", "language": "python"}
    (kernel_dir / "kernel.json").write_text(json.dumps(spec), encoding="utf-8")
    os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime)
    os.environ["IPYTHONDIR"] = str(runtime / "ipython")
    os.environ["MPLCONFIGDIR"] = str(runtime / "matplotlib")
    path = root / "notebooks" / "analysis_report.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    client = NotebookClient(notebook, timeout=180, kernel_name="a1-check",
                            resources={"metadata": {"path": str(root)}},
                            record_timing=False)
    client.km = client.create_kernel_manager()
    client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[str(runtime / "kernels")])
    client.execute()
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            cell.outputs = portable_outputs(cell.outputs, root)
    # Keep the saved notebook usable with the normal Python kernel on other machines.
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if any(cell.execution_count is None for cell in code) or any(
            output.output_type == "error" for cell in code for output in cell.outputs):
        raise RuntimeError("Notebook execution evidence contains an unexecuted cell or error")
    after = {file.relative_to(root).as_posix(): file_digest(file) for file in evidence_files}
    if before != after:
        raise RuntimeError("Source or input changed during execution; rerun on stable files")
    nbformat.write(notebook, path)
    finished = datetime.now(kst)
    lines = [
        "# 분석 노트북 실행 기록", "",
        "`tools/execute_notebook.py`가 실제 전체 실행에 성공한 뒤 생성한 기록이다. "
        "실행 안내를 적은 문서와 구분하며, 기록 이후 파일 변경 시 다시 실행해야 한다.", "",
        "- 재현 명령: A1-1 폴더에서 `uv run python tools/execute_notebook.py`",
        "- 실행 노트북: [analysis_report.ipynb](../notebooks/analysis_report.ipynb)",
        f"- 시작: {started:%Y-%m-%d %H:%M:%S} KST (UTC+09:00)",
        f"- 완료: {finished:%Y-%m-%d %H:%M:%S} KST (UTC+09:00)",
        f"- 소요 시간: {(finished - started).total_seconds():.2f}초",
        f"- 실행 환경: {platform.system()}, Python {platform.python_version()}",
        f"- 코드 셀: {len(code)}개, 실행 완료: {len(code)}개, 오류 출력: 0개",
        f"- PNG 출력: {sum('image/png' in output.get('data', {}) for cell in code for output in cell.outputs)}개",
        "- 소스·입력·환경 파일의 실행 전후 해시: 모두 일치", "",
        "## 라이브러리", "", "| 라이브러리 | 실제 설치 버전 |", "| --- | --- |",
    ]
    for package in ("numpy", "pandas", "matplotlib", "seaborn", "plotly", "nbclient", "nbformat", "ipykernel"):
        lines.append(f"| {package} | {version(package)} |")
    lines += ["", "## 코드 셀 실행 결과", "",
              "| 코드 셀 | execution_count | 출력 수 | 오류 수 |", "| ---: | ---: | ---: | ---: |"]
    for index, cell in enumerate(code, 1):
        lines.append(f"| {index} | {cell.execution_count} | {len(cell.outputs)} | 0 |")
    lines += ["", "## 실행 대상 SHA-256", "",
              "UTF-8 텍스트는 CRLF를 LF로 정규화하고 `.npy`는 원래 바이트를 해시한다. "
              "소스·입력·환경 파일은 실행 전후에 대조했으며, 노트북 해시는 실행 결과를 저장한 뒤 계산했다. "
              "해시는 기록과 파일의 대응을 확인하는 수단이며 독립 기관의 실행 인증은 아니다.", "",
              "| 파일 | SHA-256 |", "| --- | --- |"]
    for name, digest in {**after, path.relative_to(root).as_posix(): file_digest(path)}.items():
        lines.append(f"| `{name}` | `{digest}` |")
    lines += ["", "## 확인 범위", "",
              "노트북의 모든 코드 셀을 순서대로 실행했고, 필수 분석·시각화·보너스 결과 생성까지 완료했다. "
              "이 기록은 해당 입력·환경에서의 실행 성공 근거다. 통계 해석의 외부 타당성, "
              "다른 데이터에서의 정확성, 브라우저 조작 성공을 증명하지 않는다.", ""]
    receipt = root / "results" / "notebook_execution.md"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("\n".join(lines), encoding="utf-8")
    print(f"Executed {len(code)} code cells without errors: {path.relative_to(root).as_posix()}")
    print(f"Saved execution evidence: {receipt.relative_to(root).as_posix()}")


if __name__ == "__main__":
    main()
