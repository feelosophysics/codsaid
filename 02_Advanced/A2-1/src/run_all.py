"""모든 실험을 실행하고 outputs/에 PNG와 summary.json을 저장한다.

실행:  python -m src.run_all

-m src.run_all은 "src 패키지 안의 run_all 모듈을 실행"한다는 뜻이다. 그래서 이 파일은
``from . import calculus``처럼 같은 패키지의 모듈을 상대 경로로 불러올 수 있다.

흐름: main() → run_linear_algebra → run_calculus → run_backprop → run_optimizers → run_probability
각 run_* 함수는 그림을 outputs/에 저장하고, 수치 결과를 summary라는 dict에 직접 채운다
(반환값이 아니라 인자로 받은 dict를 수정하는 부수 효과). 마지막에 main()이 summary를 JSON으로 저장한다.

이 파일은 계산 방법을 새로 정의하지 않는다. src의 다른 모듈을 미션 조건(시작점, 학습률,
반복 횟수 등)으로 호출하고 결과를 그림·숫자로 남기는 "실험 대본"이다.
"""
import json
from pathlib import Path

import matplotlib
# "Agg"는 화면 창을 띄우지 않고 파일로만 그리는 방식이다. 서버나 터미널에서도 실행되게 한다.
# pyplot을 import하기 전에 정해야 해서 import 사이에 들어 있고, noqa: E402는 그 순서를 허용하라는 린터 표시다.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import calculus as calc  # noqa: E402
from . import information as info  # noqa: E402
from . import linear_algebra as la  # noqa: E402
from . import optimizer as opt  # noqa: E402
from . import probability as prob  # noqa: E402
from .neural_net import EXAMPLE, example_network  # noqa: E402

# __file__은 이 파일의 경로. resolve()로 절대 경로로 바꾸고 parents[1]로 두 단계 위(A2-1 폴더)를 얻는다.
# Path끼리 /로 이으면 운영체제에 맞는 경로가 된다: A2-1/outputs.
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
IMAGE_PATH = ROOT / "data" / "grace_hopper_128.png"


def save(fig, name):
    """Figure를 outputs/name으로 저장하고 닫는다.

    Args:
        fig: 저장할 Matplotlib Figure.
        name: 파일 이름 (예: "01_rotation.png").
    """
    # suptitle이 있으면 위쪽 여백을 남겨 각 Axes 제목과 겹치지 않게 한다.
    # fig._suptitle은 Figure 전체 제목 객체(없으면 None). 밑줄로 시작하는 내부 속성을 읽기만 한다.
    fig.tight_layout(rect=(0, 0, 1, 0.93) if fig._suptitle is not None else None)
    fig.savefig(OUT / name, dpi=110)
    # 닫지 않으면 그림 19개가 메모리에 계속 쌓인다.
    plt.close(fig)
    print(f"  saved outputs/{name}")


def load_grayscale_image(path=IMAGE_PATH):
    """PNG를 읽어 [0, 1] 범위의 2차원 흑백 배열로 반환한다.

    Args:
        path: 이미지 경로. 기본값은 data/grace_hopper_128.png.

    Returns:
        np.ndarray: shape (높이, 너비), 값 0~1. SVD는 2차원 행렬에만 적용되므로 색 채널을 없앤다.
    """
    # plt.imread는 PNG를 0~1 실수 배열로 읽는다. 흑백 PNG도 (128, 128, 4)처럼 RGBA 채널이 붙을 수 있다.
    img = plt.imread(path)
    if img.ndim == 3:
        # img[..., :3]: 앞의 모든 축(...)은 그대로, 마지막 축에서 R, G, B 세 채널만 → (128, 128, 3).
        # @ [0.299, 0.587, 0.114]: 마지막 축(3)과 내적 → (128, 128). 사람 눈의 밝기 가중치(BT.601)다.
        img = img[..., :3] @ np.array([0.299, 0.587, 0.114])
    return np.asarray(img, dtype=float)


def to_list(x):
    """JSON 저장용으로 NumPy 값을 반올림한 파이썬 값으로 바꾼다.

    Args:
        x: 숫자 또는 배열.

    Returns:
        float 또는 (중첩) list. json 모듈은 NumPy 배열을 직접 저장하지 못한다.
    """
    return np.round(np.asarray(x, dtype=float), 6).tolist()


# ---------------------------------------------------------------------------

def run_linear_algebra(summary):
    """행렬 변환, Power Iteration, SVD 실험.

    Args:
        summary: 결과를 채울 dict. "transforms", "transforms_extra", "power_iteration", "svd" 키가 추가된다.

    Returns:
        np.ndarray: 실험에 쓴 흑백 이미지 (128, 128).
    """
    print("\n[1] 선형대수")
    # {이름: (제목, 행렬)} 사전. 값 자리에 튜플을 넣어 두 정보를 함께 보관한다.
    transforms = {
        "rotation": ("Rotation R(45°)", la.rotation_matrix(np.pi / 4)),
        "scaling": ("Scaling S(2, 0.5)", la.scaling_matrix(2, 0.5)),
        "shear": ("Shear Sh(1.0)", la.shear_matrix(1.0)),
    }
    summary["transforms"] = {}
    # enumerate(..., start=1)은 번호를 1부터 센다. 꺼내는 값이 (key, (title, A)) 모양이라 같은 모양으로 풀어 받는다.
    for i, (key, (title, A)) in enumerate(transforms.items(), start=1):
        fig, ax = plt.subplots(figsize=(5.5, 5.5))
        la.plot_transformation(A, title, ax)
        save(fig, f"0{i}_{key}.png")
        check = la.area_ratio_check(A)
        # {k: round(v, 6) for k, v in check.items()}는 dict 컴프리헨션: 모든 값을 6자리로 반올림한 새 dict.
        # {"matrix": ..., **다른dict}는 두 dict를 합친 새 dict를 만든다.
        summary["transforms"][key] = {"matrix": to_list(A), **{k: round(v, 6) for k, v in check.items()}}
        # :18s는 문자열을 18칸 폭으로 맞춘다(출력 정렬용). :.2e는 1.23e-05 같은 지수 표기.
        print(f"  {title:18s} det={check['det']:.4f}  면적비={check['area_ratio']:.4f}  "
              f"오차={check['error_pct']:.2e}%  ({'통과' if check['error_pct'] < 1 else '실패'}: 1% 이내)")
    # 요구된 세 변환은 모두 det=1(면적 보존)이므로 det≠1인 행렬로도 관계를 확인한다.
    # det=1만으로는 "면적비 = |det|"와 "면적비 = 1"을 구별할 수 없기 때문이다.
    extra = {"general [[2,1],[1,3]]": np.array([[2.0, 1.0], [1.0, 3.0]]),
             "reflection+scale [[0,2],[1,0]]": np.array([[0.0, 2.0], [1.0, 0.0]])}
    summary["transforms_extra"] = {}
    for name, A in extra.items():
        check = la.area_ratio_check(A)
        summary["transforms_extra"][name] = {k: round(v, 6) for k, v in check.items()}
        # :+.4f는 양수에도 + 부호를 붙인다. det=−2처럼 부호가 의미 있는 값을 비교하기 쉽다.
        print(f"  {name:30s} det={check['det']:+.4f}  면적비={check['area_ratio']:.4f}  "
              f"|det|와 오차={check['error_pct']:.2e}%")
    # 1행 3열 좌표축. axes는 Axes 3개가 든 배열이고 zip으로 변환 3개와 짝짓는다.
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (title, A) in zip(axes, transforms.values()):
        la.plot_transformation(A, title, ax)
    save(fig, "04_transforms_overview.png")

    A = np.array([[4.0, 1.0], [1.0, 3.0]])
    result = la.power_iteration(A, tol=1e-6, seed=42)
    # eig는 결과 비교에만 쓴다. 고유값 자체는 위의 power_iteration이 직접 구했다.
    ref = la.compare_with_numpy_eig(A, result)
    print(f"  Power Iteration (수렴 {result['iterations']}회, tol=1e-6): "
          f"λ={result['eigenvalue']:.4f}, v={np.round(result['eigenvector'], 4)}")
    print(f"  np.linalg.eig: λ={ref['eigenvalue']:.4f}, v={np.round(ref['eigenvector'], 4)}")
    print(f"  고유값 오차: {ref['error_pct']:.2e}% (5% 이내), 벡터 각도 차: {ref['vector_angle_deg']:.2e}°")

    # 더 큰 대칭 행렬에서도 같은 함수가 동작하는지 확인한다.
    rng = np.random.default_rng(42)
    M = rng.standard_normal((6, 6))
    # M @ M.T는 항상 대칭이고 고유값이 0 이상이다. 그래서 가장 큰 고유값이 하나로 분명해 검증에 알맞다.
    B = M @ M.T
    big = la.power_iteration(B, tol=1e-10, num_iters=5000, seed=42)
    big_ref = la.compare_with_numpy_eig(B, big)
    print(f"  6x6 무작위 대칭 행렬: λ={big['eigenvalue']:.4f} vs eig {big_ref['eigenvalue']:.4f} "
          f"(오차 {big_ref['error_pct']:.2e}%, {big['iterations']}회)")
    summary["power_iteration"] = {
        "matrix": to_list(A), "eigenvalue": round(result["eigenvalue"], 6),
        "eigenvector": to_list(result["eigenvector"]), "iterations": result["iterations"],
        "numpy_eigenvalue": round(ref["eigenvalue"], 6), "numpy_eigenvector": to_list(ref["eigenvector"]),
        "error_pct": ref["error_pct"], "vector_angle_deg": ref["vector_angle_deg"],
        "random_6x6": {"eigenvalue": round(big["eigenvalue"], 6), "numpy": round(big_ref["eigenvalue"], 6),
                       "error_pct": big_ref["error_pct"], "iterations": big["iterations"]},
    }

    # [::-1]은 배열을 거꾸로 뒤집는 슬라이싱이다. 오름차순 정렬을 내림차순으로 바꿔 values[0]이 λ₁이 된다.
    values = np.sort(np.abs(np.linalg.eigvals(A)))[::-1]  # 그래프의 이론선 비교용
    # 반복마다 추정한 고유값과 정답의 차이. history는 리스트라 np.array로 바꿔 한 번에 뺀다.
    errors = np.abs(np.array(result["history"]) - ref["eigenvalue"])
    t = np.arange(1, len(errors) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    # np.maximum(errors, 1e-17): 오차가 정확히 0이면 로그 축에 그릴 수 없어 아주 작은 값으로 바꾼다(표시용).
    axes[0].semilogy(t, np.maximum(errors, 1e-17), "o-", ms=3, label="|λ_t − λ_true|")
    # 이론선: 첫 오차에서 시작해 매 반복 (λ₂/λ₁)²배씩 줄어드는 선. 실제 점들이 이 기울기를 따라가는지 비교한다.
    axes[0].semilogy(t, errors[0] * (values[1] / values[0]) ** (2 * (t - 1)), "--",
                     label="theory ∝ (λ2/λ1)^(2t)")
    axes[0].set_xlabel("iteration")
    axes[0].set_ylabel("eigenvalue error (log)")
    axes[0].set_title(f"Power iteration on A=[[4,1],[1,3]]: {result['iterations']} iterations")
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    la.plot_transformation(A, "A maps circle → ellipse; v1 is the long axis", axes[1])
    v = result["eigenvector"] * result["eigenvalue"]
    axes[1].plot([-v[0], v[0]], [-v[1], v[1]], color="tab:green", lw=2.5, label="λ1·v1 (power iteration)")
    axes[1].set_xlim(-5, 5)
    axes[1].set_ylim(-5, 5)
    axes[1].legend(loc="lower right", fontsize=8)
    save(fig, "05_power_iteration.png")

    image = load_grayscale_image()
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.8))
    svd_results = la.plot_svd_compression(image, (10, 50, 100), axes)
    fig.suptitle("SVD compression: A_k = Σ_{i≤k} σ_i u_i v_iᵀ  (storage>1 means no real saving)")
    save(fig, "06_svd_compression.png")
    fig, ax = plt.subplots(figsize=(7, 4.2))
    la.plot_singular_values(image, (10, 50, 100), ax)
    save(fig, "07_singular_values.png")
    summary["svd"] = {"shape": list(image.shape), "results": []}
    for res in svd_results:
        # :3d는 정수를 3칸 폭으로 맞춘다.
        print(f"  SVD k={res['k']:3d}: 저장 비율 {res['storage_ratio']:.3f}, 에너지 {res['energy_retained']:.4f}, "
              f"상대 오차 {res['relative_error']:.4f}, PSNR {res['psnr_db']:.2f} dB")
        # 이미지 배열(reconstruction)은 JSON에 넣기에 너무 크므로 if 조건으로 빼고,
        # 실수 값만 반올림한다. isinstance(v, float)는 "v가 실수인가"를 확인한다.
        summary["svd"]["results"].append({k: (round(v, 6) if isinstance(v, float) else v)
                                          for k, v in res.items() if k != "reconstruction"})
    return image


def run_calculus(summary):
    """수치 미분과 Gradient 시각화 실험.

    Args:
        summary: 결과를 채울 dict. "calculus" 키가 추가된다.
    """
    print("\n[2] 미적분")
    # lambda x: x ** 2는 f(x) = x²을 즉석에서 만든 함수다. 정답 f'(3) = 6과 비교한다.
    numeric = calc.numerical_derivative(lambda x: x ** 2, 3.0)
    err = abs(numeric - 6.0)
    print(f"  f(x)=x², x=3: 수치 미분 {numeric:.10f}, 해석 6, 오차 {err:.2e} "
          f"({'통과' if err < 1e-4 else '실패'}: 1e-4 이내)")
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    # opt.quadratic(x² + y²)의 등고선은 원이고 Gradient (2x, 2y)는 원점에서 바깥을 향한다.
    checks = calc.plot_gradient_field(opt.quadratic, levels=(1, 4, 9), ax=ax)
    save(fig, "08_gradient_field.png")
    worst = max(c["max_abs_cos"] for c in checks)
    print(f"  등고선 접선·Gradient 최대 |cos| = {worst:.2e} (0이면 수직)")

    # h에 따른 오차 실험은 sin을 쓴다. x²은 중심차분 절단 오차가 정확히 0이라 h의 영향이 드러나지 않는다.
    # np.sin, np.cos처럼 이미 있는 함수도 이름만 넘기면 된다(괄호를 붙이지 않는다).
    curve = calc.derivative_error_curve(np.sin, np.cos, 1.0)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    xs = np.linspace(0, 5, 200)
    axes[0].plot(xs, xs ** 2, label="f(x)=x²")
    # 접선의 방정식 y = f(3) + f'(3)(x − 3) = 9 + numeric·(x − 3).
    axes[0].plot(xs, 9 + numeric * (xs - 3), "--", label=f"tangent at x=3, slope≈{numeric:.6f}")
    axes[0].plot([3], [9], "ro")
    axes[0].set_ylim(-2, 26)
    axes[0].set_title("Central difference slope at x=3")
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    # loglog는 x, y 모두 로그 축. h가 1e-12~1까지 12자리에 걸쳐 있어 일반 축으로는 보이지 않는다.
    axes[1].loglog(curve["hs"], np.maximum(curve["forward"], 1e-17), "o-", ms=3, label="forward (f(x+h)−f(x))/h")
    axes[1].loglog(curve["hs"], np.maximum(curve["central"], 1e-17), "s-", ms=3, label="central (f(x+h)−f(x−h))/2h")
    axes[1].set_xlabel("h")
    axes[1].set_ylabel("|error| for d/dx sin(x) at x=1")
    axes[1].set_title("Too large h: truncation error / too small h: rounding error")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3, which="both")
    save(fig, "09_derivative_error.png")
    # argmin은 가장 작은 값의 위치. 그 위치의 h가 중심차분에 가장 좋은 간격이다.
    best = int(np.argmin(curve["central"]))
    summary["calculus"] = {"numeric_derivative": numeric, "abs_error": err, "max_abs_cos": worst,
                           "central_best_h": float(curve["hs"][best]),
                           "central_best_error": float(curve["central"][best])}


def run_backprop(summary):
    """손계산 예제의 순전파·역전파와 수치 미분 검증.

    Args:
        summary: 결과를 채울 dict. "backprop" 키가 추가된다.
    """
    print("\n[3] 역전파 (손계산 예제, y_true=1)")
    net, x, y = example_network()
    cache = net.forward(x, y)
    grads = net.backward(cache, y)
    for key in ("z1", "a1", "z2", "y_pred", "loss"):
        # :7s로 이름을 7칸에 맞추고, np.round(..., 4)로 손계산 표와 같은 4자리로 보여 준다.
        print(f"  {key:7s} = {np.round(cache[key], 4)}")
    for key in ("dL_dy_pred", "dL_dz2", "dL_dW2", "dL_da1", "dL_dz1", "dL_dW1"):
        print(f"  {key:10s} = {np.round(grads[key], 4).tolist()}")
    # 역전파와 독립적인 확인: W1의 원소를 하나씩 ±h 움직여 손실 변화로 기울기를 잰다.
    # lambda W: net.loss_with(x, y, W1=W)는 "W1만 W로 바꾼 손실"을 돌려주는 함수다.
    num_W1 = calc.numerical_gradient(lambda W: net.loss_with(x, y, W1=W), net.W1)
    num_W2 = calc.numerical_gradient(lambda W: net.loss_with(x, y, W2=W), net.W2)
    # 두 방법의 차이 중 가장 큰 값. 1e-11 수준이면 역전파 식이 맞다는 근거가 된다.
    diff = max(np.max(np.abs(num_W1 - grads["dL_dW1"])), np.max(np.abs(num_W2 - grads["dL_dW2"])))
    print(f"  수치 미분과 최대 차이: {diff:.2e}")
    summary["backprop"] = {
        "example": EXAMPLE,
        "forward": {k: to_list(cache[k]) for k in ("z1", "a1", "z2", "y_pred", "loss")},
        "backward": {k: to_list(v) for k, v in grads.items()},
        "numerical_max_diff": float(diff),
    }


def run_optimizers(summary):
    """VanillaGD·Momentum 필수 실험과 Adam·Newton 보너스 실험.

    모든 실험은 같은 시작점 (5, 5)에서 출발해 옵티마이저·학습률·함수만 바꿔 비교한다.

    Args:
        summary: 결과를 채울 dict. "optimizers" 키가 추가된다.
    """
    print("\n[4] 최적화")
    x0 = np.array([5.0, 5.0])
    res = {}

    # 필수 실험: x² + y², lr=0.1, 100회. 경로 배열 shape은 (101, 2)이고 gd[-1]은 마지막 위치다.
    gd = opt.optimize(opt.VanillaGD(0.1), opt.quadratic_grad, x0, 100)
    mom = opt.optimize(opt.Momentum(0.1, 0.9), opt.quadratic_grad, x0, 100)
    print(f"  f=x²+y², 시작 (5,5), lr=0.1, 100회: VanillaGD {gd[-1]}, |θ|={np.linalg.norm(gd[-1]):.2e} "
          f"({'반경 0.1 이내' if np.linalg.norm(gd[-1]) < 0.1 else '실패'})")
    print(f"  Momentum(β=0.9): {np.round(mom[-1], 4)}, |θ|={np.linalg.norm(mom[-1]):.2e}")
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    opt.plot_convergence_paths(opt.quadratic, {"VanillaGD": gd}, ax,
                               "VanillaGD on x²+y², lr=0.1, 100 iterations")
    save(fig, "10_gd_quadratic.png")
    res["quadratic_lr0.1"] = {
        "VanillaGD_final": to_list(gd[-1]), "Momentum_final": to_list(mom[-1]),
        "VanillaGD_iters_to_1e-3": opt.iterations_to_reach(gd, (0, 0), 1e-3),
        "Momentum_iters_to_1e-3": opt.iterations_to_reach(
            opt.optimize(opt.Momentum(0.1, 0.9), opt.quadratic_grad, x0, 1000), (0, 0), 1e-3),
    }

    # 학습률과 발산: x²+y²에서는 θ_{t+1} = (1 − 2η)θ_t 이므로 η > 1에서 발산한다.
    # lr=0.1 → 0.8배(수렴), 0.5 → 0배(한 번에 도착), 0.9 → −0.8배(부호가 바뀌며 수렴),
    # 1.0 → −1배(같은 크기로 진동), 1.1 → −1.2배(발산).
    lrs = [0.1, 0.5, 0.9, 1.0, 1.1]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))
    # dict 컴프리헨션으로 {"lr=0.1": 경로, "lr=0.5": 경로, ...}를 만든다.
    lr_paths = {f"lr={lr}": opt.optimize(opt.VanillaGD(lr), opt.quadratic_grad, x0, 100) for lr in lrs}
    # plt.cm.plasma(...)는 0~0.85 사이 위치의 색 5개. 학습률이 커질수록 색이 바뀌게 한다.
    for (name, path), color in zip(lr_paths.items(), plt.cm.plasma(np.linspace(0, 0.85, len(lrs)))):
        # path[:11, 0]: 앞 11행(0~10번 반복)의 x 좌표.
        axes[0].plot(np.arange(11), path[:11, 0], "--o", ms=4, color=color, label=name)
    axes[0].axhline(0, color="gray", lw=0.8)
    axes[0].set_xlabel("iteration")
    axes[0].set_ylabel("x_t (y_t is identical)")
    axes[0].set_title("x²+y², first 10 steps: x_{t+1} = (1−2·lr)·x_t")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    for (name, path), color in zip(lr_paths.items(), plt.cm.plasma(np.linspace(0, 0.85, len(lrs)))):
        # norm(path, axis=1): 행(반복)마다 원점까지 거리 (101,).
        # name[3:]은 "lr=0.1"의 3번째 글자부터 → "0.1". float로 바꿔 |1 − 2·lr|을 범례에 적는다.
        axes[1].semilogy(np.maximum(np.linalg.norm(path, axis=1), 1e-17), color=color,
                         label=f"{name}  |1−2lr|={abs(1 - 2 * float(name[3:])):.1f}")
    axes[1].axhline(np.linalg.norm(x0), color="gray", ls=":", lw=1)
    axes[1].set_xlabel("iteration")
    axes[1].set_ylabel("‖θ_t‖ (log)")
    axes[1].set_title("x²+y²: converges for lr<1, oscillates at 1, diverges above 1")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
    # 타원 x² + 10y²에서는 y 방향 배율이 1 − 20·lr이다. lr=0.5면 −9배라 몇 번 만에 그림 밖으로 튄다.
    ell_paths = {f"lr={lr}": opt.optimize(opt.VanillaGD(lr), opt.elliptic_grad, x0, 6) for lr in (0.05, 0.5)}
    opt.plot_contour(opt.elliptic, axes[2], (-60, 60), (-60, 60), log_levels=True)
    for (name, path), color in zip(ell_paths.items(), ("tab:blue", "tab:red")):
        axes[2].plot(path[:4, 0], path[:4, 1], "--o", ms=4, color=color, label=name)
    axes[2].set_title("x²+10y², lr=0.5: |1−20·lr|=9 → diverges")
    axes[2].legend(fontsize=8)
    fig.suptitle("Learning rate vs. divergence (stable only if lr < 2 / largest curvature)")
    save(fig, "11_lr_divergence.png")
    res["lr_divergence"] = {}
    for name, path in lr_paths.items():
        norm = float(np.linalg.norm(path[-1]))
        res["lr_divergence"][name] = norm
        # 조건식을 겹쳐 쓴 판정: 시작 거리보다 1% 넘게 커지면 발산, 1보다 크면 진동, 그 외 수렴.
        status = "발산" if norm > np.linalg.norm(x0) * 1.01 else ("진동(유지)" if norm > 1 else "수렴")
        print(f"  x²+y² {name:7s}: 100회 후 ‖θ‖ = {norm:.3e} → {status}")
    ell_norm = float(np.linalg.norm(opt.optimize(opt.VanillaGD(0.5), opt.elliptic_grad, x0, 20)[-1]))
    res["elliptic_lr0.5_norm_after_20"] = ell_norm
    print(f"  x²+10y² lr=0.5: 20회 후 ‖θ‖ = {ell_norm:.3e} → 발산")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    opt.plot_convergence_paths(opt.quadratic, {"VanillaGD": gd, "Momentum": mom}, axes[0],
                               "x²+y², lr=0.1, β=0.9, 100 iterations", (-6, 6), (-6, 6))
    opt.plot_distance_curves({"VanillaGD": gd, "Momentum": mom}, axes[1],
                             title="distance to minimum")
    save(fig, "12_gd_vs_momentum_quadratic.png")

    # 타원형 함수: 작은 lr에서 GD는 완만한 x 방향을 기어가고 Momentum은 가속한다.
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.6))
    ell = {}
    # axes[:2]는 앞의 두 좌표축. 세 번째는 아래 학습률 비교 그래프에 쓴다.
    for ax, lr in zip(axes[:2], (0.01, 0.09)):
        paths = {"VanillaGD": opt.optimize(opt.VanillaGD(lr), opt.elliptic_grad, x0, 100),
                 "Momentum": opt.optimize(opt.Momentum(lr, 0.9), opt.elliptic_grad, x0, 100)}
        opt.plot_convergence_paths(opt.elliptic, paths, ax, f"x²+10y², lr={lr}, β=0.9, 100 iterations",
                                   (-6, 6), (-6, 6))
        ell[lr] = paths
    # 학습률 하나만 보면 결론이 뒤집힐 수 있어 여러 학습률에서 "1e-3까지 몇 번"을 잰다.
    sweep_lrs = [0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.09]
    sweep = {"VanillaGD": [], "Momentum": []}
    for lr in sweep_lrs:
        # 클래스도 값처럼 튜플에 넣었다가 cls(lr)로 객체를 만들 수 있다.
        for name, cls in (("VanillaGD", opt.VanillaGD), ("Momentum", opt.Momentum)):
            o = cls(lr) if name == "VanillaGD" else cls(lr, 0.9)
            path = opt.optimize(o, opt.elliptic_grad, x0, 5000)
            sweep[name].append(opt.iterations_to_reach(path, (0, 0), 1e-3))
    for name, its in sweep.items():
        axes[2].loglog(sweep_lrs, its, "o-", color=opt.STYLES[name]["color"], label=name)
    axes[2].set_xlabel("learning rate")
    axes[2].set_ylabel("iterations to ‖θ‖ < 1e-3 (log)")
    axes[2].set_title("x²+10y²: Momentum(β=0.9) helps at small lr")
    axes[2].legend()
    axes[2].grid(alpha=0.3, which="both")
    save(fig, "13_gd_vs_momentum_elliptic.png")
    # 중첩 dict 컴프리헨션: {"0.01": {"VanillaGD": {...}, "Momentum": {...}}, "0.09": {...}}.
    # JSON 키는 문자열이어야 해서 str(lr)로 바꾼다.
    res["elliptic"] = {
        str(lr): {name: {"final": to_list(p[-1]), "norm": float(np.linalg.norm(p[-1]))} for name, p in paths.items()}
        for lr, paths in ell.items()}
    res["elliptic_sweep"] = {"lrs": sweep_lrs, **sweep}
    for lr, paths in ell.items():
        print(f"  x²+10y² lr={lr}: VanillaGD ‖θ‖={np.linalg.norm(paths['VanillaGD'][-1]):.3e}, "
              f"Momentum ‖θ‖={np.linalg.norm(paths['Momentum'][-1]):.3e}")
    print(f"  1e-3 도달 반복 수 (lr {sweep_lrs}):")
    print(f"    VanillaGD {sweep['VanillaGD']}")
    print(f"    Momentum  {sweep['Momentum']}")

    # 보너스 1: Adam
    # 세 옵티마이저에 같은 lr=0.1을 주고 비교한다. x²+10y²에서 GD는 y 배율이 1 − 20·0.1 = −1이라 영원히 진동한다.
    print("  [보너스] Adam")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.6))
    adam_res = {}
    # (이름, 함수, 기울기 함수) 튜플 두 개를 차례로 꺼낸다. 함수도 값처럼 튜플에 담을 수 있다.
    for ax, (fname, f, g) in zip(axes[:2], (("x²+y²", opt.quadratic, opt.quadratic_grad),
                                           ("x²+10y²", opt.elliptic, opt.elliptic_grad))):
        paths = {"VanillaGD": opt.optimize(opt.VanillaGD(0.1), g, x0, 300),
                 "Momentum": opt.optimize(opt.Momentum(0.1, 0.9), g, x0, 300),
                 "Adam": opt.optimize(opt.Adam(0.1), g, x0, 300)}
        # v[:101]: 그림에는 앞 100 step(101개 위치)만 그린다. 도달 횟수는 300 step 전체에서 센다.
        opt.plot_convergence_paths(f, {k: v[:101] for k, v in paths.items()}, ax,
                                   f"{fname}, lr=0.1 for all, first 100 steps", (-6, 6), (-6, 6))
        adam_res[fname] = {k: opt.iterations_to_reach(v, (0, 0), 1e-3) for k, v in paths.items()}
        if fname == "x²+10y²":
            opt.plot_distance_curves(paths, axes[2], title="x²+10y², lr=0.1: distance to minimum")
        print(f"    {fname}: 1e-3 도달 반복 수 {adam_res[fname]}")
    save(fig, "14_adam_comparison.png")
    res["adam"] = adam_res

    # 보너스 2: Newton Method
    print("  [보너스] Newton Method")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.6))
    # 이차 함수의 Hessian은 위치와 무관한 상수 [[2, 0], [0, 20]]이다. np.diag는 대각 행렬을 만든다.
    # lambda p: ...는 p를 받지만 쓰지 않고 항상 같은 행렬을 돌려준다.
    newton_ell = opt.optimize(opt.NewtonMethod(hess_fn=lambda p: np.diag([2.0, 20.0])),
                              opt.elliptic_grad, x0, 10, stop_tol=1e-10)
    gd_ell = opt.optimize(opt.VanillaGD(0.05), opt.elliptic_grad, x0, 100)
    opt.plot_convergence_paths(opt.elliptic, {"VanillaGD": gd_ell, "Newton": newton_ell}, axes[0],
                               "x²+10y²: Newton reaches minimum in 1 step", (-6, 6), (-6, 6))
    r0 = np.array([-1.5, 2.0])
    # Rosenbrock은 Hessian이 위치마다 달라 hess_fn 대신 f를 넘기고 수치 Hessian을 쓴다.
    newton_rb = opt.optimize(opt.NewtonMethod(f=opt.rosenbrock), opt.rosenbrock_grad, r0, 50, stop_tol=1e-8)
    gd_rb = opt.optimize(opt.VanillaGD(0.001), opt.rosenbrock_grad, r0, 20000)
    opt.plot_convergence_paths(opt.rosenbrock, {"VanillaGD": gd_rb, "Newton": newton_rb}, axes[1],
                               "Rosenbrock: GD lr=0.001 (marker every 500) vs Newton", (-2, 2), (-1, 3),
                               target=(1, 1), log_levels=True, markevery={"VanillaGD": 500})
    s0 = np.array([1.0, 0.5])
    # 안장점 x² − y²: Hessian [[2, 0], [0, −2]]은 음수 곡률이 있어 Newton이 원점(안장점)으로 곧장 간다.
    newton_sd = opt.optimize(opt.NewtonMethod(hess_fn=lambda p: np.diag([2.0, -2.0])),
                             opt.saddle_grad, s0, 5, stop_tol=1e-10)
    gd_sd = opt.optimize(opt.VanillaGD(0.1), opt.saddle_grad, s0, 12)
    opt.plot_convergence_paths(opt.saddle, {"VanillaGD": gd_sd, "Newton": newton_sd}, axes[2],
                               "x²−y²: Newton jumps INTO the saddle point", (-3, 3), (-3, 3),
                               target_label="saddle point (not a minimum)")
    save(fig, "15_newton_method.png")
    rb_gd_iters = opt.iterations_to_reach(gd_rb, (1, 1), 1e-3)
    res["newton"] = {
        "elliptic_steps": len(newton_ell) - 1, "elliptic_final": to_list(newton_ell[-1]),
        "rosenbrock_newton_iters": opt.iterations_to_reach(newton_rb, (1, 1), 1e-3),
        "rosenbrock_gd_iters": rb_gd_iters, "rosenbrock_gd_final": to_list(gd_rb[-1]),
        "saddle_newton_final": to_list(newton_sd[-1]), "saddle_gd_final": to_list(gd_sd[-1]),
    }
    print(f"    x²+10y²: Newton {len(newton_ell) - 1}회 만에 {np.round(newton_ell[-1], 6)}")
    print(f"    Rosenbrock (1e-3 도달): Newton {res['newton']['rosenbrock_newton_iters']}회, "
          f"GD(lr=0.001) {rb_gd_iters}회")
    print(f"    x²−y² 시작 (1, 0.5): Newton → {np.round(newton_sd[-1], 4)} (안장점), "
          f"GD 12회 → {np.round(gd_sd[-1], 3)} (탈출)")
    summary["optimizers"] = res


def run_probability(summary):
    """분포 시각화, 소프트맥스, MLE 연결, 정보 이론(보너스).

    Args:
        summary: 결과를 채울 dict. "probability" 키가 추가된다.
    """
    print("\n[5] 확률/통계")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    prob.plot_normal_pdfs(((0.0, 1.0), (2.0, 0.5)), ax)
    save(fig, "16_normal_pdf.png")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    prob.plot_bernoulli_pmfs((0.3, 0.7), ax)
    save(fig, "17_bernoulli_pmf.png")

    # np.random.seed(42)는 NumPy의 전역 난수 상태를 고정한다. 아래 randn이 매번 같은 값을 내게 한다.
    np.random.seed(42)
    # randn(5)는 표준정규 난수 5개, × 3으로 점수 차이를 키운다. shape (5,).
    logits = np.random.randn(5) * 3
    s = prob.softmax(logits)
    big = prob.softmax(np.array([1000.0, 1001.0, 1002.0]))
    print(f"  softmax({np.round(logits, 3)}) = {np.round(s, 4)}, 합-1 = {abs(s.sum() - 1):.1e}")
    print(f"  softmax([1000,1001,1002]) = {np.round(big, 4)} (overflow 없음)")

    # MSE ↔ 가우시안 MLE: 같은 데이터에서 두 목적 함수의 최소점이 같은지 본다.
    # 설명용 합성 데이터: 실제 기울기 1.5인 직선에 표준편차 0.5인 정규 잡음을 더한 50개 점.
    rng = np.random.default_rng(42)
    x = rng.uniform(-2, 2, 50)
    y = 1.5 * x + rng.normal(0, 0.5, 50)
    # 후보 w를 0~3에서 0.005 간격 601개로 모두 대입해 보는 격자 탐색이다(경사하강법을 쓰지 않는다).
    ws = np.linspace(0, 3, 601)
    mses = np.array([prob.mse(y, w * x) for w in ws])
    # σ² = 0.25는 잡음 표준편차 0.5를 제곱한 값이다.
    nlls = np.array([prob.gaussian_nll(y, w * x, 0.25) for w in ws])
    # ws[np.argmin(mses)]: MSE가 가장 작은 위치의 w.
    w_mse, w_nll = ws[np.argmin(mses)], ws[np.argmin(nlls)]
    # 모델 ŷ = w·x의 MSE를 미분해 0으로 두면 w = Σxy / Σx²이다. 격자 탐색 결과를 확인하는 정답.
    w_closed = float(np.dot(x, y) / np.dot(x, x))
    # BCE ↔ 베르누이 MLE: 로지스틱 모델 p = σ(w x)
    # 실제 w=2인 확률 σ(2x)로 0/1 정답을 뽑는다. (난수 < 확률)은 참/거짓, astype(float)로 1.0/0.0.
    yb = (rng.uniform(size=50) < 1 / (1 + np.exp(-2 * x))).astype(float)
    bces = np.array([prob.bernoulli_nll(yb, 1 / (1 + np.exp(-w * x))) for w in ws])
    # 우도 = 샘플별 확률의 곱(np.prod). BCE는 이 곱에 −log를 씌운 값이라 최소·최대 위치가 같아야 한다.
    lik = np.array([np.prod(prob.bernoulli_pmf(yb.astype(int), 1 / (1 + np.exp(-w * x)))) for w in ws])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    axes[0].plot(ws, mses, label="MSE(w)")
    # 두 곡선은 값의 크기가 달라 오른쪽에 별도 y축(twinx)을 두고 모양과 최소 위치만 비교한다.
    ax2 = axes[0].twinx()
    ax2.plot(ws, nlls, color="tab:orange", ls="--", label="Gaussian NLL(w), σ²=0.25")
    axes[0].axvline(w_mse, color="tab:blue", ls=":")
    ax2.axvline(w_nll, color="tab:orange", ls=":")
    axes[0].set_xlabel("w  (model ŷ = w·x)")
    axes[0].set_ylabel("MSE")
    ax2.set_ylabel("negative log-likelihood")
    axes[0].set_title(f"argmin MSE = {w_mse:.3f}, argmin NLL = {w_nll:.3f}")
    axes[0].legend([axes[0].lines[0], ax2.lines[0]], ["MSE(w)", "Gaussian NLL(w)"], loc="upper center")
    axes[1].plot(ws, bces, label="BCE sum = Bernoulli NLL")
    ax3 = axes[1].twinx()
    ax3.plot(ws, lik, color="tab:green", ls="--")
    w_bce, w_lik = ws[np.argmin(bces)], ws[np.argmax(lik)]
    axes[1].axvline(w_bce, color="tab:blue", ls=":")
    axes[1].set_xlabel("w  (model p = σ(w·x))")
    axes[1].set_ylabel("BCE (sum)")
    ax3.set_ylabel("likelihood Π p(y|x)")
    axes[1].set_title(f"argmin BCE = {w_bce:.3f}, argmax likelihood = {w_lik:.3f}")
    axes[1].legend([axes[1].lines[0], ax3.lines[0]], ["BCE = −log likelihood", "likelihood"], loc="upper center")
    save(fig, "18_loss_mle.png")
    print(f"  MSE 최소 w={w_mse:.3f}, 가우시안 NLL 최소 w={w_nll:.3f}, 닫힌 해 w={w_closed:.3f}")
    print(f"  BCE 최소 w={w_bce:.3f}, 베르누이 우도 최대 w={w_lik:.3f}")

    print("  [보너스] 정보 이론")
    p = np.array([0.7, 0.2, 0.1])
    q = np.array([0.4, 0.4, 0.2])
    H, CE, KL, KLr = info.entropy(p), info.cross_entropy(p, q), info.kl_divergence(p, q), info.kl_divergence(q, p)
    print(f"  p={p}, q={q}: H(p)={H:.4f}, H(p,q)={CE:.4f}, KL(p‖q)={KL:.4f}, KL(q‖p)={KLr:.4f}, "
          f"H(p)+KL={H + KL:.4f}")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    ps = np.linspace(0, 1, 201)
    axes[0].plot(ps, info.binary_entropy(ps), label="H(Bernoulli(p))")
    axes[0].axhline(np.log(2), color="gray", ls=":", label="max = log 2")
    axes[0].set_xlabel("p")
    axes[0].set_ylabel("entropy (nats)")
    axes[0].set_title("Binary entropy: most uncertain at p=0.5")
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    labels = ["H(p)", "KL(p‖q)", "H(p,q)", "KL(q‖p)"]
    # H(p,q) 자리는 일단 높이 0인 흰 막대로 자리만 잡고, 아래 두 줄에서 H(p)와 KL을 쌓아 다시 그린다.
    axes[1].bar(labels, [H, KL, 0, KLr], color=["tab:blue", "tab:orange", "white", "tab:gray"])
    axes[1].bar(["H(p,q)"], [H], color="tab:blue")                  # H(p,q)를 H(p) + KL로 쌓는다
    axes[1].bar(["H(p,q)"], [KL], bottom=[H], color="tab:orange")
    for i, v in enumerate([H, KL, CE, KLr]):
        axes[1].text(i, v + 0.01, f"{v:.4f}", ha="center")
    axes[1].set_title("H(p,q) = H(p) + KL(p‖q);  KL is not symmetric")
    axes[1].set_ylabel("nats")
    save(fig, "19_information_theory.png")
    summary["probability"] = {
        "softmax_logits": to_list(logits), "softmax": to_list(s), "softmax_sum_error": float(abs(s.sum() - 1)),
        "mse_argmin": float(w_mse), "nll_argmin": float(w_nll), "closed_form_w": w_closed,
        "bce_argmin": float(w_bce), "likelihood_argmax": float(w_lik),
        "information": {"p": p.tolist(), "q": q.tolist(), "H_p": H, "H_pq": CE, "KL_pq": KL, "KL_qp": KLr},
    }


def main():
    """전체 실험을 순서대로 실행한다.

    부수 효과: outputs/ 폴더를 만들고(이미 있으면 그대로) PNG 19개와 summary.json을 덮어쓴다.
    """
    # 전역 난수 고정. 각 실험이 쓰는 default_rng(42)와 별개로, np.random.* 함수를 쓰는 부분을 재현 가능하게 한다.
    np.random.seed(42)
    # exist_ok=True: 폴더가 이미 있어도 오류를 내지 않는다.
    OUT.mkdir(exist_ok=True)
    summary = {}
    # 같은 summary dict를 차례로 넘겨 각 함수가 자기 결과 칸을 채운다.
    run_linear_algebra(summary)
    run_calculus(summary)
    run_backprop(summary)
    run_optimizers(summary)
    run_probability(summary)
    # ensure_ascii=False: 한글·기호를 \uXXXX로 바꾸지 않고 그대로 저장한다. indent=2는 사람이 읽기 좋게 들여쓰기.
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n  saved outputs/summary.json")


# 이 파일을 직접 실행할 때(python -m src.run_all)만 main()을 부른다.
# 테스트처럼 다른 파일이 import할 때는 실험이 자동으로 돌지 않는다.
if __name__ == "__main__":
    main()
