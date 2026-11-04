"""XOR 학습: 2-32-32-1 ReLU MLP + Sigmoid 출력 + BCE, Adam(lr=0.01).

XOR은 4개 샘플뿐이므로 1 epoch = 전체 배치 1 스텝이다.
기준: He 초기화로 100 epoch 안에 Loss < 0.1 또는 정확도 95% 이상.

실행: uv run python scripts/train_xor.py [--init he] [--seed 0] [--epochs 100]
"""
import argparse
import sys

import numpy as np

from _common import REPORTS, Tee
from minigrad import Tensor, nn, no_grad, optim
from minigrad.data import xor_dataset

HIDDEN = (32, 32)
LR = 0.01


def build_model(init, seed, hidden=HIDDEN, sigmoid_output=True):
    rng = np.random.default_rng(seed)
    return nn.mlp([2, *hidden, 1], activation=nn.ReLU, init=init,
                  output=nn.Sigmoid if sigmoid_output else None, rng=rng)


def xor_loss(output, y, loss):
    """loss="bce": Sigmoid 레이어 출력(확률)에 BCE.  loss="logits": 마지막 Linear 출력에 안정형 BCE."""
    if loss == "bce":
        return nn.binary_cross_entropy(output, y), output.data
    with no_grad():
        prob = output.sigmoid().data
    return nn.binary_cross_entropy_with_logits(output, y), prob


def make_optimizer(name, params, lr):
    if name == "adam":
        return optim.Adam(params, lr=lr)
    if name == "sgd":
        return optim.SGD(params, lr=lr)
    raise ValueError(name)


def train_xor(init="he", seed=0, epochs=100, hidden=HIDDEN, optimizer="adam", lr=LR, loss="bce",
              verbose=False):
    """epoch 0(학습 전)부터 epoch `epochs`까지의 loss·정확도와 학습된 모델을 돌려준다.

    losses[e]는 e번 갱신한 뒤의 손실이다. losses[0]은 초기화 직후의 손실이다.
    """
    X, y = xor_dataset()
    X = Tensor(X)
    model = build_model(init, seed, hidden, sigmoid_output=(loss == "bce"))
    opt = make_optimizer(optimizer, model.parameters(), lr)
    losses, accuracies = [], []
    loss_name = loss

    def evaluate():
        with no_grad():
            value, prob = xor_loss(model(X), y, loss_name)
        return value.item(), float(((prob > 0.5) == y).mean())

    loss, acc = evaluate()
    losses.append(loss), accuracies.append(acc)
    for epoch in range(1, epochs + 1):
        loss, _ = xor_loss(model(X), y, loss_name)
        opt.zero_grad()
        loss.backward()
        opt.step()
        loss, acc = evaluate()
        losses.append(loss), accuracies.append(acc)
        if verbose and (epoch <= 5 or epoch % 10 == 0):
            print(f"epoch {epoch:3d}  loss {loss:.4f}  acc {acc:.0%}")
    return np.array(losses), np.array(accuracies), model


def first_epoch_below(losses, threshold=0.1):
    hits = np.flatnonzero(losses < threshold)
    return int(hits[0]) if hits.size else None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--init", default="he", choices=nn.init.METHODS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()

    with Tee(REPORTS / f"train_xor_{args.init}.log"):
        print(f"XOR  model=2-{'-'.join(map(str, HIDDEN))}-1 ReLU/Sigmoid  init={args.init}  "
              f"Adam(lr={LR})  seed={args.seed}")
        losses, accs, model = train_xor(args.init, args.seed, args.epochs, verbose=True)
        with no_grad():
            prob = model(Tensor(xor_dataset()[0])).data.ravel()
        print("\n입력    정답  예측 확률")
        for x, t, p in zip(xor_dataset()[0], xor_dataset()[1].ravel(), prob):
            print(f"{x.astype(int)}   {int(t)}    {p:.4f}")
        hit = first_epoch_below(losses)
        ok = hit is not None or accs.max() >= 0.95
        print(f"\nLoss < 0.1 도달: {'epoch ' + str(hit) if hit is not None else '없음'}  "
              f"최종 loss {losses[-1]:.4f}, 정확도 {accs[-1]:.0%}")
        print(f"판정 ({args.epochs} epoch 내 Loss < 0.1 또는 정확도 ≥ 95%): {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
