"""미니배치 로더와 작은 합성 데이터셋. torch.utils.data 없이 NumPy 인덱싱만 쓴다."""
import numpy as np


class DataLoader:
    """for X, y in DataLoader(...)로 미니배치를 돌려준다. shuffle이면 epoch마다 순서를 섞는다."""

    def __init__(self, X, y, batch_size=64, shuffle=True, drop_last=False, rng=None):
        if len(X) != len(y):
            raise ValueError("X와 y의 샘플 수가 다르다")
        self.X, self.y = np.asarray(X), np.asarray(y)
        self.batch_size, self.shuffle, self.drop_last = batch_size, shuffle, drop_last
        self.rng = np.random.default_rng() if rng is None else rng

    def __len__(self):
        n = len(self.X)
        return n // self.batch_size if self.drop_last else -(-n // self.batch_size)

    def __iter__(self):
        order = self.rng.permutation(len(self.X)) if self.shuffle else np.arange(len(self.X))
        for start in range(0, len(order), self.batch_size):
            index = order[start:start + self.batch_size]
            if self.drop_last and len(index) < self.batch_size:
                break
            yield self.X[index], self.y[index]


def xor_dataset():
    X = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
    y = np.array([[0.0], [1.0], [1.0], [0.0]])
    return X, y


def make_moons(n_samples=400, noise=0.15, rng=None):
    """두 개의 반달 모양 클래스. sklearn.datasets.make_moons와 같은 모양을 NumPy로 만든다."""
    rng = np.random.default_rng() if rng is None else rng
    n_out = n_samples // 2
    n_in = n_samples - n_out
    t_out = np.linspace(0, np.pi, n_out)
    t_in = np.linspace(0, np.pi, n_in)
    X = np.vstack([
        np.column_stack([np.cos(t_out), np.sin(t_out)]),
        np.column_stack([1 - np.cos(t_in), 1 - np.sin(t_in) - 0.5]),
    ])
    y = np.concatenate([np.zeros(n_out, dtype=np.int64), np.ones(n_in, dtype=np.int64)])
    X = X + rng.normal(scale=noise, size=X.shape)
    order = rng.permutation(n_samples)
    return X[order], y[order]
