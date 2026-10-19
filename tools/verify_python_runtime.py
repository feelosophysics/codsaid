"""Run project code after a Python environment migration without replacing reports.

Run from a mission directory with its own Python; outputs go to the given temp path.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path.cwd()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert sys.version_info[:3] == (3, 12, 13)
    result = {"project": args.project, "python": sys.version.split()[0]}

    def cli(*command):
        subprocess.run([sys.executable, "-B", *map(str, command)], check=True)

    if args.project == "A1-1":
        cli("-m", "src.run_analysis", "--output-dir", out / "commerce")
        assert len(list((out / "commerce").rglob("*.png"))) >= 6
        result["execution"] = "Full commerce analysis, including bonus outputs"
    elif args.project == "A2-1":
        import src.run_all as app
        app.OUT = out / "math"
        app.main()
        summary = json.loads((app.OUT / "summary.json").read_text(encoding="utf-8"))
        assert summary and len(list(app.OUT.glob("*.png"))) >= 10
        result["execution"] = "Full linear algebra, calculus, backprop, optimizer and probability experiments"
    elif args.project == "A3-1":
        cli("-m", "src.app", "data/synthetic/E01.jpg", "--no-gui", "--out", out / "scan")
        assert list((out / "scan").rglob("*.png"))
        result["execution"] = "Document scanning CLI on the existing E01 image"
    elif args.project == "A3-2":
        cli("-m", "src.app", "--no-gui", "--no-realtime", "--max-frames", "60", "--out", out / "video")
        assert any(p.stat().st_size > 0 for p in (out / "video").rglob("*.mp4"))
        result["execution"] = "Headless tracking of 60 frames from the existing demo video"
    elif args.project == "A4-1":
        cli("main.py", "--query", "space shuttle launch", "--topk", "3", "--method", "both")
        result["execution"] = "TF-IDF and BM25 CLI search on the cached 20 Newsgroups corpus"
    elif args.project == "A4-2":
        cli("main.py", "--text", "문의 support@company.co.kr, 전화 02-1234-5678, 참가비 50,000원. 음식은 맛있는데 가격이 비싸요.", "--aspect", "--mask", "--json")
        result["execution"] = "Extraction, sentiment, aspect and masking CLI"
    elif args.project == "A5-1":
        import numpy as np
        from sklearn.linear_model import LogisticRegression, Ridge
        from xgboost import XGBClassifier
        from src.data import load_data, split_data
        from src.classification import make_pipeline
        from src.regression import make_pipeline as regression_pipeline
        split = split_data(load_data())
        X, y = split.X_train.iloc[:1000], split.y_clf_train.iloc[:1000]
        models = [make_pipeline(LogisticRegression(max_iter=2000), "smote"),
                  make_pipeline(XGBClassifier(n_estimators=5, max_depth=2, n_jobs=2))]
        for model in models:
            model.fit(X, y)
            pred = model.predict_proba(split.X_test.iloc[:64])
            assert pred.shape == (64, 2) and np.isfinite(pred).all()
        reg = regression_pipeline(Ridge())
        reg.fit(X, split.y_reg_train.iloc[:1000])
        assert np.isfinite(reg.predict(split.X_test.iloc[:64])).all()
        result["execution"] = "Real credit data: Ridge, SMOTE/LogReg and XGBoost training and predictions (1000 train / 64 test)"
    elif args.project == "A5-2":
        import numpy as np
        from src import clustering, explain, model
        from src.data import load_data, features_only, split_data
        df = load_data()
        X = features_only(df).iloc[:1000]
        Z = clustering.fit_scaler(X).transform(X)
        scan = clustering.scan_k(Z, k_range=range(2, 5), seeds=range(2))
        assert len(scan) == 3
        split = split_data(df)
        clf = model.build_model(n_estimators=10, n_jobs=2)
        clf.fit(split.X_train.iloc[:1000], split.y_train.iloc[:1000])
        Xtest = split.X_test.iloc[:16]
        sv = explain.explain(clf, Xtest)
        error = explain.additivity_error(sv, clf.predict_proba(Xtest)[:, 1])
        assert np.isfinite(sv.values).all() and error < 1e-6
        result.update(execution="Real customer data: KMeans scan, RF training and TreeSHAP explanations", shap_additivity_error=error)
    elif args.project == "A6-1":
        sys.path.insert(0, str(Path.cwd() / "scripts"))
        from train_xor import train_xor
        loss, accuracy, _ = train_xor(epochs=100)
        assert loss[-1] < 0.1 and accuracy[-1] >= 0.95
        result.update(execution="MiniGrad XOR training for 100 epochs", final_loss=float(loss[-1]), accuracy=float(accuracy[-1]))
    elif args.project == "A6-2":
        import numpy as np
        import torch
        from perfdiag.timeseries.data import prepare, make_dataset
        from perfdiag.timeseries.models import build_model
        from perfdiag.vision.models import TransferNet
        torch.set_num_threads(2)
        torch.manual_seed(42)
        ds = make_dataset(prepare("aapl"), "delta", 30)
        train = ds.sets["train"]
        X, y = torch.from_numpy(train.X[:16]), torch.from_numpy(train.target[:16])
        for arch in ("lstm", "gru", "lstm_attention", "transformer"):
            model = build_model(ds.n_features, arch)
            opt = torch.optim.Adam(model.parameters(), lr=0.001)
            for _ in range(3):
                opt.zero_grad()
                loss = torch.nn.functional.mse_loss(model(X), y)
                loss.backward()
                opt.step()
            assert torch.isfinite(loss)
            model.eval()
            with torch.no_grad():
                pred = model(torch.from_numpy(ds.sets["test"].X[:16]))
            assert pred.shape == (16,) and torch.isfinite(pred).all()
        vision = TransferNet(8, "linear_probe").train()
        opt = torch.optim.SGD([p for p in vision.parameters() if p.requires_grad], lr=0.01)
        opt.zero_grad()
        logits = vision(torch.randn(2, 3, 64, 64))
        loss = torch.nn.functional.cross_entropy(logits, torch.tensor([0, 1]))
        loss.backward()
        opt.step()
        assert logits.shape == (2, 8) and torch.isfinite(loss)
        result.update(execution="Real AAPL windows: four forecast architectures trained for 3 steps each; cached pretrained ResNet18 forward/backward and FC update", torch=torch.__version__)
    else:
        raise ValueError(args.project)

    # Validate an actual kernel using this interpreter, without global kernel registration.
    if args.project in ("A1-1", "A2-1", "A5-1", "A5-2"):
        from jupyter_client import KernelManager
        os.environ["JUPYTER_RUNTIME_DIR"] = str(out / "jupyter")
        Path(os.environ["JUPYTER_RUNTIME_DIR"]).mkdir(exist_ok=True)
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        client = None
        try:
            manager.start_kernel(cwd=str(Path.cwd()))
            client = manager.client()
            client.start_channels()
            client.wait_for_ready(timeout=30)
            reply = client.execute_interactive("import sys, numpy as np; assert sys.version_info[:3] == (3,12,13); assert 3+7 == 10; print(sys.executable)", timeout=30)
            assert reply["content"]["status"] == "ok", reply
            result["jupyter_kernel"] = "passed"
        finally:
            if client is not None:
                client.stop_channels()
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
