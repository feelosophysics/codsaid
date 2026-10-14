"""Execute the report in the current Python environment, using a local kernel.

No installation of a global/user Jupyter kernel is needed.
"""
import json
import os
from pathlib import Path
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


def main():
    root = Path(__file__).resolve().parents[1]
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
    nbformat.write(notebook, path)
    count = sum(cell.cell_type == "code" for cell in notebook.cells)
    print(f"Executed {count} code cells without errors: {path}")


if __name__ == "__main__":
    main()
