"""현재 캐시·배열과 저장 결과를 대조하고 노트북을 새 커널에서 검증한다."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from dataclasses import asdict

import nbformat
import numpy as np

from build_learning_notebook import ROOT, TARGET, build
from perfdiag.common import FLOWERS, RESULTS
from perfdiag.metrics import regression_metrics
from perfdiag.timeseries.baselines import all_baselines
from perfdiag.timeseries.data import prepare
from perfdiag.vision.data import class_names, load_manifest
from perfdiag.vision.train import scores


def stored_results():
    sys.path.insert(0, str(ROOT / "scripts"))
    from ts_baselines import split_fingerprint
    from ts_deep import EXPERIMENTS
    from perfdiag.timeseries.train import TrainConfig
    from vision_transfer import EPOCHS, LR_HEAD
    from perfdiag.vision.train import VisionConfig
    for name in ("aapl", "seoul"):
        prep = prepare(name)
        base = json.loads((RESULTS / f"ts_baselines_{name}.json").read_text(encoding="utf-8"))
        deep = json.loads((RESULTS / f"ts_deep_{name}.json").read_text(encoding="utf-8"))
        assert base["test_fingerprint"] == deep["test_fingerprint"] == split_fingerprint(prep)
        assert base["split_info"] == prep.info
        assert deep["feature_names"] == prep.feature_names
        t = prep.splits["test"]
        assert deep["test_dates"] == [str(date) for date in prep.dates[t]]
        np.testing.assert_array_equal(deep["test_actual"], prep.y[t])
        predictions, _ = all_baselines(prep.y, prep.splits)
        for model, splits in predictions.items():
            for split, predicted in splits.items():
                current = regression_metrics(prep.y[prep.splits[split]], predicted, prep.cfg.with_mape)
                for metric, value in current.items():
                    if value is not None:
                        np.testing.assert_allclose(value, base["metrics"][model][split][metric], rtol=1e-10)
            np.testing.assert_allclose(splits["test"], base["test_predictions"][model], atol=5.1e-7)
        for key, _, mode, arch, kwargs, train_kwargs, role in EXPERIMENTS:
            item = deep["experiments"][key]
            assert item["mode"] == mode and item["arch"] == arch and item["model_kwargs"] == kwargs
            assert item["window"] == deep["window"] == 30 and item["role"] == role
            assert item["train_config"] == asdict(TrainConfig(**train_kwargs))
            expected_seeds = deep["seeds"][:1] if role == "probe" else deep["seeds"]
            assert [run["seed"] for run in item["seeds"]] == expected_seeds
        selected = deep["experiments"][deep["final"]]
        current = regression_metrics(prep.y[t], np.asarray(selected["test_prediction"]), prep.cfg.with_mape)
        for metric, value in current.items():
            if value is not None:
                np.testing.assert_allclose(value, deep["final_test"][metric], rtol=1e-10)
        print(name, "9 baselines x 3 splits and saved final predictions matched; CSV SHA256",
              hashlib.sha256(prep.cfg.csv.read_bytes()).hexdigest())
    vision = json.loads((RESULTS / "vision_transfer.json").read_text(encoding="utf-8"))
    manifest = load_manifest()
    test = manifest[manifest["split"] == "test"].sort_values(["target", "order"])
    assert vision["classes"] == class_names()
    assert vision["test_files"] == test["file"].tolist()
    np.testing.assert_array_equal(vision["test_targets"], test["target"].to_numpy())
    assert all((FLOWERS / file).is_file() for file in test["file"])
    for run in vision["runs"]:
        strategy, shots = run["strategy"], run["shots"]
        assert run["config"] == asdict(VisionConfig(strategy=strategy, epochs=EPOCHS[strategy][shots],
                                                   lr_head=LR_HEAD[strategy]))
        probability = np.asarray(run["test_proba"])
        # vision_transfer.py는 확률을 소수 4자리로 저장한다. 합의 오차 한계는 8×0.00005다.
        np.testing.assert_allclose(probability.sum(1), 1., atol=8 * 5.01e-5)
        np.testing.assert_array_equal(probability.argmax(1), run["test_pred"])
        loss, error = scores(probability, test["target"].to_numpy())
        true_probability = probability[np.arange(len(test)), test["target"].to_numpy()]
        lower_loss = -np.log(np.minimum(1., true_probability + 5.01e-5) + 1e-12).mean()
        upper_loss = -np.log(np.maximum(0., true_probability - 5.01e-5) + 1e-12).mean()
        assert lower_loss <= run["test"]["loss"] <= upper_loss
        np.testing.assert_allclose(1 - error, run["test"]["accuracy"])
    print("vision:", len(vision["runs"]), "stored runs, file/target/prediction order and scores matched")


def html_code(refresh=False):
    path = ROOT / "study/a6-2.html"
    html = path.read_text(encoding="utf-8")
    marker = '<script>const DATA = '
    start = html.index(marker) + len(marker)
    end = html.index(';</script>', start)
    data = json.loads(html[start:end])
    for key, snippet in data["code"].items():
        source = (ROOT / snippet["file"]).read_text(encoding="utf-8")
        node = ast.parse(source)
        for part in snippet["name"].split("."):
            node = next(n for n in node.body if getattr(n, "name", "") == part or
                        isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == part for t in n.targets))
        expected = "\n".join(source.splitlines()[node.lineno-1:node.end_lineno])
        if refresh:
            snippet.update(start=node.lineno, end=node.end_lineno, text=expected)
        else:
            assert snippet["text"] == expected, key
            assert (snippet["start"], snippet["end"]) == (node.lineno, node.end_lineno), key
    if refresh:
        path.write_text(html[:start] + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + html[end:],
                        encoding="utf-8")
    print("HTML excerpts matched:", len(data["code"]))


def execute():
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    notebook = build()
    with tempfile.TemporaryDirectory(prefix="perfdiag-kernel-") as folder:
        spec = Path(folder) / "perfdiag-check"
        spec.mkdir()
        (spec / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "perfdiag check", "language": "python"}), encoding="utf-8")
        manager = KernelManager(kernel_name="perfdiag-check", kernel_spec_manager=KernelSpecManager(kernel_dirs=[folder]))
        old = os.environ.get("JUPYTER_RUNTIME_DIR")
        os.environ["JUPYTER_RUNTIME_DIR"] = folder
        try:
            NotebookClient(notebook, km=manager, timeout=300, resources={"metadata": {"path": str(ROOT)}}).execute(cleanup_kc=True)
        finally:
            if old is None:
                os.environ.pop("JUPYTER_RUNTIME_DIR", None)
            else:
                os.environ["JUPYTER_RUNTIME_DIR"] = old
    # 로컬 커널 실행 경로를 공개 메타데이터에 남기지 않는다.
    notebook.metadata = build().metadata
    nbformat.write(notebook, TARGET)
    print("Fresh kernel execution completed")


def notebook_check():
    saved = nbformat.read(TARGET, as_version=4)
    nbformat.validate(saved)
    assert [(c.cell_type, c.id, c.source) for c in saved.cells] == [
        (c.cell_type, c.id, c.source) for c in build().cells]
    code_count, figures = 0, 0
    for cell in saved.cells:
        assert not cell.get("attachments")
        if cell.cell_type == "code":
            code_count += 1
            assert cell.execution_count is not None, cell.id
        for output in cell.get("outputs", []):
            assert output.output_type != "error", cell.id
            figures += "image/png" in output.get("data", {})
    assert figures == 2
    for path in (TARGET, ROOT / "tools/build_learning_notebook.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"[A-Za-z]:\\\\|/Users/|/home/|sk-[A-Za-z0-9]{20,}", text), path.name
        assert not any(token in text for token in ("source-manifest", "A6-2.json", "평가표"))
    print("Notebook source/output/privacy checks:", code_count, "code cells,", figures, "figures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--refresh-html", action="store_true")
    args = parser.parse_args()
    stored_results()
    html_code(args.refresh_html)
    if args.execute:
        execute()
    notebook_check()
