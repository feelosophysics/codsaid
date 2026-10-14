"""시계열 예측 모델: LSTM·GRU, Attention을 붙인 LSTM(보너스), 작은 Transformer(보너스)."""
import math

import torch
from torch import nn


class RNNForecaster(nn.Module):
    """(batch, window, features) → 다음 시점 값 1개.

    attention=False: 마지막 은닉 상태 h_T 하나로 예측한다.
    attention=True : 모든 시점의 은닉 상태 h_1…h_T에 가중치 a_i를 매겨 문맥 c = Σ a_i·h_i를 만들고,
                     [c; h_T]로 예측한다 (Bahdanau식 additive attention, 질의는 h_T).
    """

    def __init__(self, n_features, cell="lstm", hidden=32, layers=1, dropout=0.0, attention=False):
        super().__init__()
        rnn_cls = {"lstm": nn.LSTM, "gru": nn.GRU}[cell]
        self.rnn = rnn_cls(n_features, hidden, num_layers=layers, batch_first=True,
                           dropout=dropout if layers > 1 else 0.0)
        self.dropout = nn.Dropout(dropout)
        self.attention = attention
        if attention:
            self.key = nn.Linear(hidden, hidden, bias=False)
            self.query = nn.Linear(hidden, hidden)
            self.score = nn.Linear(hidden, 1, bias=False)
        self.head = nn.Linear(hidden * (2 if attention else 1), 1)
        self.last_attention = None

    def forward(self, x):
        out, _ = self.rnn(x)                          # (B, T, H)
        last = out[:, -1]
        if self.attention:
            energy = torch.tanh(self.key(out) + self.query(last)[:, None, :])
            weights = torch.softmax(self.score(energy).squeeze(-1), dim=1)   # (B, T)
            context = (weights[:, :, None] * out).sum(dim=1)
            self.last_attention = weights.detach()
            last = torch.cat([context, last], dim=1)
        return self.head(self.dropout(last)).squeeze(-1)


class TransformerForecaster(nn.Module):
    """입력 사영 → 사인 위치 인코딩 → Transformer 인코더 2층 → 마지막 시점 토큰으로 예측."""

    def __init__(self, n_features, d_model=32, heads=4, layers=2, dropout=0.1, max_len=256):
        super().__init__()
        self.embed = nn.Linear(n_features, d_model)
        position = torch.arange(max_len)[:, None]
        div = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2], pe[:, 1::2] = torch.sin(position * div), torch.cos(position * div)
        self.register_buffer("pe", pe)
        layer = nn.TransformerEncoderLayer(d_model, heads, dim_feedforward=d_model * 2, dropout=dropout,
                                           batch_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.head = nn.Linear(d_model, 1)

    def forward(self, x):
        h = self.embed(x) + self.pe[: x.shape[1]]
        return self.head(self.encoder(h)[:, -1]).squeeze(-1)


def build_model(n_features, arch="lstm", **kwargs):
    if arch in ("lstm", "gru"):
        return RNNForecaster(n_features, cell=arch, **kwargs)
    if arch == "lstm_attention":
        return RNNForecaster(n_features, cell="lstm", attention=True, **kwargs)
    if arch == "transformer":
        return TransformerForecaster(n_features, **kwargs)
    raise ValueError(arch)


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
