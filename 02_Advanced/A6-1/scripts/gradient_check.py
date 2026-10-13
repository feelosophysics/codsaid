"""모든 연산·레이어·손실의 역전파를 수치 미분과 비교한다 (ε=1e-5, 상대 오차 < 1e-7).

레이어 하나를 검사할 때는 L = Σ(layer(x) ⊙ R)을 쓴다. R은 고정된 무작위 가중치라서
출력의 모든 원소가 서로 다른 기울기를 받는다 (단순 합이면 대칭 때문에 오류가 가려질 수 있다).

실행: uv run python scripts/gradient_check.py   → reports/gradient_check.log
"""
import sys

import numpy as np

from _common import REPORTS, Tee, save_json
from minigrad import Tensor, nn
from minigrad.gradcheck import EPSILON, THRESHOLD, check_gradients

rng = np.random.default_rng(2024)


def param(*shape, scale=1.0, away_from_zero=False):
    """기울기 검사용 float64 텐서. ReLU 계열은 꺾이는 점(0) 근처 값을 피한다.

    x가 0에서 ε 안에 있으면 x±ε가 꺾임을 넘나들어 수치 미분 자체가 틀린 값이 된다.
    """
    data = rng.standard_normal(shape) * scale
    if away_from_zero:
        data = np.where(np.abs(data) < 0.05, np.sign(data + 1e-12) * 0.05 + data, data)
    return Tensor(data, requires_grad=True)


def projected(fn, out_shape):
    weights = rng.standard_normal(out_shape)
    return lambda: (fn() * weights).sum()


def layer_case(name, layer, in_shape, away_from_zero=False):
    x = param(*in_shape, away_from_zero=away_from_zero)
    out_shape = layer(x).shape
    tensors = [x] + list(layer.parameters())
    names = [f"{name}.input"] + [p.name.replace("Linear", name) if p.name else name for p in layer.parameters()]
    return name, projected(lambda: layer(x), out_shape), tensors, names


def build_cases():
    cases = []

    # 1. 기본 연산 (브로드캐스팅 포함)
    a, b = param(4, 3), param(3)                # (4,3)과 (3,)이 브로드캐스팅된다
    c, d = param(4, 1), param(3, 5)
    pos = Tensor(rng.uniform(0.5, 2.0, (4, 3)), requires_grad=True)
    ops = [
        ("Add (broadcast)", lambda: a + b, [a, b], (4, 3)),
        ("Sub (broadcast)", lambda: a - c, [a, c], (4, 3)),
        ("Mul (broadcast)", lambda: a * b, [a, b], (4, 3)),
        ("Div (broadcast)", lambda: a / (pos + c * c), [a, pos, c], (4, 3)),
        ("MatMul", lambda: a @ d, [a, d], (4, 5)),
        ("Pow", lambda: pos ** 3, [pos], (4, 3)),
        ("Exp", lambda: a.exp(), [a], (4, 3)),
        ("Log", lambda: pos.log(), [pos], (4, 3)),
        ("Sum(axis=0)", lambda: a.sum(axis=0), [a], (3,)),
        ("Mean(axis=1, keepdims)", lambda: a.mean(axis=1, keepdims=True), [a], (4, 1)),
        ("Reshape+Transpose", lambda: a.reshape(3, 4).T, [a], (4, 3)),
        ("Getitem (fancy index)", lambda: a[[0, 2, 2], 1:], [a], (3, 2)),
        ("Reuse (x*x + x)", lambda: a * a + a, [a], (4, 3)),
    ]
    for name, fn, tensors, shape in ops:
        names = [f"{name}.{chr(ord('a') + i)}" for i in range(len(tensors))]
        cases.append((name, projected(fn, shape), tensors, names))

    # 2. 레이어
    cases.append(layer_case("Linear", nn.Linear(5, 3, init="he", rng=rng), (4, 5)))
    cases.append(layer_case("ReLU", nn.ReLU(), (4, 5), away_from_zero=True))
    cases.append(layer_case("Sigmoid", nn.Sigmoid(), (4, 5)))
    cases.append(layer_case("Softmax", nn.Softmax(), (4, 5)))
    cases.append(layer_case("Tanh", nn.Tanh(), (4, 5)))
    cases.append(layer_case("LeakyReLU", nn.LeakyReLU(0.1), (4, 5), away_from_zero=True))
    cases.append(layer_case("ELU", nn.ELU(1.0), (4, 5), away_from_zero=True))

    # Dropout: 수치 미분 중에도 같은 마스크가 나오도록 매번 같은 seed로 되돌린다.
    dropout, x_drop = nn.Dropout(0.3), param(4, 5)
    weights = rng.standard_normal((4, 5))

    def dropout_loss():
        dropout.rng = np.random.default_rng(7)
        return (dropout(x_drop) * weights).sum()
    cases.append(("Dropout", dropout_loss, [x_drop], ["Dropout.input"]))

    # 3. 손실 함수
    pred, target = param(6, 2), rng.standard_normal((6, 2))
    logit_bce, y_bce = param(6, 1), rng.integers(0, 2, (6, 1)).astype(float)
    logits, labels = param(6, 4), rng.integers(0, 4, 6)
    cases += [
        ("MSELoss", lambda: nn.mse_loss(pred, target), [pred], ["MSELoss.pred"]),
        ("BCELoss", lambda: nn.binary_cross_entropy(logit_bce.sigmoid(), y_bce), [logit_bce], ["BCELoss.logit"]),
        ("BCEWithLogitsLoss", lambda: nn.binary_cross_entropy_with_logits(logit_bce, y_bce), [logit_bce],
         ["BCEWithLogitsLoss.logit"]),
        ("CrossEntropyLoss", lambda: nn.cross_entropy(logits, labels), [logits], ["CrossEntropyLoss.logits"]),
        ("Softmax+NLLLoss", lambda: nn.nll_loss(logits.softmax(), labels), [logits], ["NLLLoss.logits"]),
    ]

    # 4. 전체 모델: 2층 MLP의 모든 매개변수를 한 손실로 검사한다.
    model = nn.Sequential(
        nn.Linear(4, 6, init="he", rng=rng, name="Linear_1"), nn.ReLU(),
        nn.Linear(6, 3, init="he", rng=rng, name="Linear_2"),
    )
    for p in model.parameters():
        p.data += rng.standard_normal(p.shape) * 0.1  # 0인 편향도 검사 대상이 되게 흔든다
    x_mlp, y_mlp = Tensor(rng.standard_normal((8, 4))), rng.integers(0, 3, 8)
    params = list(model.parameters())
    cases.append(("MLP (Linear_1→ReLU→Linear_2→CE)", lambda: nn.cross_entropy(model(x_mlp), y_mlp),
                  params, [p.name for p in params]))
    return cases


def main():
    REPORTS.mkdir(exist_ok=True)
    with Tee(REPORTS / "gradient_check.log"):
        print(f"Gradient Check  ε={EPSILON:g}, 통과 기준: 상대 오차 < {THRESHOLD:g} (float64)")
        print("상대 오차 = ‖analytic − numerical‖ / (‖analytic‖ + ‖numerical‖), 대표값은 |analytic| 최대 원소")
        results, summary = [], []
        for case, loss_fn, tensors, names in build_cases():
            print(f"\n## {case}")
            for r in check_gradients(loss_fn, tensors, names):
                print(r.line())
                results.append(r)
                summary.append({"case": case, "tensor": r.name, "analytic": r.analytic,
                                "numerical": r.numerical, "difference": r.difference, "passed": r.passed})
        worst = max(results, key=lambda r: r.difference)
        failed = [r for r in results if not r.passed]
        print()
        if failed:
            print(f"{len(failed)}/{len(results)} gradient checks FAILED. Maximum difference: "
                  f"{worst.difference:.1e} ({worst.name})")
        else:
            print(f"All {len(results)} gradient checks passed! Maximum difference: "
                  f"{worst.difference:.1e} < {THRESHOLD:g} ✓  ({worst.name})")
    save_json({"epsilon": EPSILON, "threshold": THRESHOLD, "max_difference": worst.difference,
               "passed": not failed, "checks": summary}, "gradient_check.json")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
