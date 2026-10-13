"""옵티마이저 공통 부분: 매개변수 목록, 기울기 초기화, L2 정규화."""


class Optimizer:
    def __init__(self, params, lr, weight_decay=0.0):
        self.params = list(params)
        if not self.params:
            raise ValueError("최적화할 매개변수가 없다")
        self.lr = lr
        self.weight_decay = weight_decay
        self.step_count = 0

    def zero_grad(self):
        for p in self.params:
            p.grad = None

    def step(self):
        self.step_count += 1
        for i, p in enumerate(self.params):
            if p.grad is None:
                continue
            grad = p.grad
            if self.weight_decay:
                # L2 정규화: 손실에 (λ/2)‖w‖²를 더한 것과 같다. 미분하면 λw.
                grad = grad + self.weight_decay * p.data
            self._update(i, p, grad)

    def _update(self, index, param, grad):
        raise NotImplementedError
