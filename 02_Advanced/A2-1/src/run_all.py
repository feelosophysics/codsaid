"""모든 실험을 실행하고 outputs/에 PNG와 summary.json을 저장한다.

실행:  python -m src.run_all
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import calculus as calc  # noqa: E402
from . import information as info  # noqa: E402
from . import linear_algebra as la  # noqa: E402
from . import optimizer as opt  # noqa: E402
from . import probability as prob  # noqa: E402
from .neural_net import EXAMPLE, example_network  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
IMAGE_PATH = ROOT / "data" / "grace_hopper_128.png"


def save(fig, name):
    """Figure를 outputs/name으로 저장하고 닫는다."""
    # suptitle이 있으면 위쪽 여백을 남겨 각 Axes 제목과 겹치지 않게 한다.
    fig.tight_layout(rect=(0, 0, 1, 0.93) if fig._suptitle is not None else None)
    fig.savefig(OUT / name, dpi=110)
    plt.close(fig)
    print(f"  saved outputs/{name}")


def load_grayscale_image(path=IMAGE_PATH):
    """PNG를 읽어 [0, 1] 범위의 2차원 흑백 배열로 반환한다."""
    img = plt.imread(path)
    if img.ndim == 3:
        img = img[..., :3] @ np.array([0.299, 0.587, 0.114])
    return np.asarray(img, dtype=float)


def to_list(x):
    """JSON 저장용으로 NumPy 값을 반올림한 파이썬 값으로 바꾼다."""
    return np.round(np.asarray(x, dtype=float), 6).tolist()


# ---------------------------------------------------------------------------

def run_linear_algebra(summary):
    """행렬 변환, Power Iteration, SVD 실험."""
    print("\n[1] 선형대수")
    transforms = {
        "rotation": ("Rotation R(45°)", la.rotation_matrix(np.pi / 4)),
        "scaling": ("Scaling S(2, 0.5)", la.scaling_matrix(2, 0.5)),
        "shear": ("Shear Sh(1.0)", la.shear_matrix(1.0)),
    }
    summary["transforms"] = {}
    for i, (key, (title, A)) in enumerate(transforms.items(), start=1):
        fig, ax = plt.subplots(figsize=(5.5, 5.5))
        la.plot_transformation(A, title, ax)
        save(fig, f"0{i}_{key}.png")
        check = la.area_ratio_check(A)
        summary["transforms"][key] = {"matrix": to_list(A), **{k: round(v, 6) for k, v in check.items()}}
        print(f"  {title:18s} det={check['det']:.4f}  면적비={check['area_ratio']:.4f}  "
              f"오차={check['error_pct']:.2e}%  ({'통과' if check['error_pct'] < 1 else '실패'}: 1% 이내)")
    # 요구된 세 변환은 모두 det=1(면적 보존)이므로 det≠1인 행렬로도 관계를 확인한다.
    extra = {"general [[2,1],[1,3]]": np.array([[2.0, 1.0], [1.0, 3.0]]),
             "reflection+scale [[0,2],[1,0]]": np.array([[0.0, 2.0], [1.0, 0.0]])}
    summary["transforms_extra"] = {}
    for name, A in extra.items():
        check = la.area_ratio_check(A)
        summary["transforms_extra"][name] = {k: round(v, 6) for k, v in check.items()}
        print(f"  {name:30s} det={check['det']:+.4f}  면적비={check['area_ratio']:.4f}  "
              f"|det|와 오차={check['error_pct']:.2e}%")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (title, A) in zip(axes, transforms.values()):
        la.plot_transformation(A, title, ax)
    save(fig, "04_transforms_overview.png")

    A = np.array([[4.0, 1.0], [1.0, 3.0]])
    result = la.power_iteration(A, tol=1e-6, seed=42)
    ref = la.compare_with_numpy_eig(A, result)
    print(f"  Power Iteration (수렴 {result['iterations']}회, tol=1e-6): "
          f"λ={result['eigenvalue']:.4f}, v={np.round(result['eigenvector'], 4)}")
    print(f"  np.linalg.eig: λ={ref['eigenvalue']:.4f}, v={np.round(ref['eigenvector'], 4)}")
    print(f"  고유값 오차: {ref['error_pct']:.2e}% (5% 이내), 벡터 각도 차: {ref['vector_angle_deg']:.2e}°")

    # 더 큰 대칭 행렬에서도 같은 함수가 동작하는지 확인한다.
    rng = np.random.default_rng(42)
    M = rng.standard_normal((6, 6))
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

    values = np.sort(np.abs(np.linalg.eigvals(A)))[::-1]  # 그래프의 이론선 비교용
    errors = np.abs(np.array(result["history"]) - ref["eigenvalue"])
    t = np.arange(1, len(errors) + 1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    axes[0].semilogy(t, np.maximum(errors, 1e-17), "o-", ms=3, label="|λ_t − λ_true|")
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
        print(f"  SVD k={res['k']:3d}: 저장 비율 {res['storage_ratio']:.3f}, 에너지 {res['energy_retained']:.4f}, "
              f"상대 오차 {res['relative_error']:.4f}, PSNR {res['psnr_db']:.2f} dB")
        summary["svd"]["results"].append({k: (round(v, 6) if isinstance(v, float) else v)
                                          for k, v in res.items() if k != "reconstruction"})
    return image


def run_calculus(summary):
    """수치 미분과 Gradient 시각화 실험."""
    print("\n[2] 미적분")
    numeric = calc.numerical_derivative(lambda x: x ** 2, 3.0)
    err = abs(numeric - 6.0)
    print(f"  f(x)=x², x=3: 수치 미분 {numeric:.10f}, 해석 6, 오차 {err:.2e} "
          f"({'통과' if err < 1e-4 else '실패'}: 1e-4 이내)")
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    checks = calc.plot_gradient_field(opt.quadratic, levels=(1, 4, 9), ax=ax)
    save(fig, "08_gradient_field.png")
    worst = max(c["max_abs_cos"] for c in checks)
    print(f"  등고선 접선·Gradient 최대 |cos| = {worst:.2e} (0이면 수직)")

    curve = calc.derivative_error_curve(np.sin, np.cos, 1.0)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    xs = np.linspace(0, 5, 200)
    axes[0].plot(xs, xs ** 2, label="f(x)=x²")
    axes[0].plot(xs, 9 + numeric * (xs - 3), "--", label=f"tangent at x=3, slope≈{numeric:.6f}")
    axes[0].plot([3], [9], "ro")
    axes[0].set_ylim(-2, 26)
    axes[0].set_title("Central difference slope at x=3")
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    axes[1].loglog(curve["hs"], np.maximum(curve["forward"], 1e-17), "o-", ms=3, label="forward (f(x+h)−f(x))/h")
    axes[1].loglog(curve["hs"], np.maximum(curve["central"], 1e-17), "s-", ms=3, label="central (f(x+h)−f(x−h))/2h")
    axes[1].set_xlabel("h")
    axes[1].set_ylabel("|error| for d/dx sin(x) at x=1")
    axes[1].set_title("Too large h: truncation error / too small h: rounding error")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3, which="both")
    save(fig, "09_derivative_error.png")
    best = int(np.argmin(curve["central"]))
    summary["calculus"] = {"numeric_derivative": numeric, "abs_error": err, "max_abs_cos": worst,
                           "central_best_h": float(curve["hs"][best]),
                           "central_best_error": float(curve["central"][best])}


def run_backprop(summary):
    """손계산 예제의 순전파·역전파와 수치 미분 검증."""
    print("\n[3] 역전파 (손계산 예제, y_true=1)")
    net, x, y = example_network()
    cache = net.forward(x, y)
    grads = net.backward(cache, y)
    for key in ("z1", "a1", "z2", "y_pred", "loss"):
        print(f"  {key:7s} = {np.round(cache[key], 4)}")
    for key in ("dL_dy_pred", "dL_dz2", "dL_dW2", "dL_da1", "dL_dz1", "dL_dW1"):
        print(f"  {key:10s} = {np.round(grads[key], 4).tolist()}")
    num_W1 = calc.numerical_gradient(lambda W: net.loss_with(x, y, W1=W), net.W1)
    num_W2 = calc.numerical_gradient(lambda W: net.loss_with(x, y, W2=W), net.W2)
    diff = max(np.max(np.abs(num_W1 - grads["dL_dW1"])), np.max(np.abs(num_W2 - grads["dL_dW2"])))
    print(f"  수치 미분과 최대 차이: {diff:.2e}")
    summary["backprop"] = {
        "example": EXAMPLE,
        "forward": {k: to_list(cache[k]) for k in ("z1", "a1", "z2", "y_pred", "loss")},
        "backward": {k: to_list(v) for k, v in grads.items()},
        "numerical_max_diff": float(diff),
    }


def run_optimizers(summary):
    """VanillaGD·Momentum 필수 실험과 Adam·Newton 보너스 실험."""
    print("\n[4] 최적화")
    x0 = np.array([5.0, 5.0])
    res = {}

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
    lrs = [0.1, 0.5, 0.9, 1.0, 1.1]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.4))
    lr_paths = {f"lr={lr}": opt.optimize(opt.VanillaGD(lr), opt.quadratic_grad, x0, 100) for lr in lrs}
    for (name, path), color in zip(lr_paths.items(), plt.cm.plasma(np.linspace(0, 0.85, len(lrs)))):
        axes[0].plot(np.arange(11), path[:11, 0], "--o", ms=4, color=color, label=name)
    axes[0].axhline(0, color="gray", lw=0.8)
    axes[0].set_xlabel("iteration")
    axes[0].set_ylabel("x_t (y_t is identical)")
    axes[0].set_title("x²+y², first 10 steps: x_{t+1} = (1−2·lr)·x_t")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    for (name, path), color in zip(lr_paths.items(), plt.cm.plasma(np.linspace(0, 0.85, len(lrs)))):
        axes[1].semilogy(np.maximum(np.linalg.norm(path, axis=1), 1e-17), color=color,
                         label=f"{name}  |1−2lr|={abs(1 - 2 * float(name[3:])):.1f}")
    axes[1].axhline(np.linalg.norm(x0), color="gray", ls=":", lw=1)
    axes[1].set_xlabel("iteration")
    axes[1].set_ylabel("‖θ_t‖ (log)")
    axes[1].set_title("x²+y²: converges for lr<1, oscillates at 1, diverges above 1")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
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
    for ax, lr in zip(axes[:2], (0.01, 0.09)):
        paths = {"VanillaGD": opt.optimize(opt.VanillaGD(lr), opt.elliptic_grad, x0, 100),
                 "Momentum": opt.optimize(opt.Momentum(lr, 0.9), opt.elliptic_grad, x0, 100)}
        opt.plot_convergence_paths(opt.elliptic, paths, ax, f"x²+10y², lr={lr}, β=0.9, 100 iterations",
                                   (-6, 6), (-6, 6))
        ell[lr] = paths
    sweep_lrs = [0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.07, 0.09]
    sweep = {"VanillaGD": [], "Momentum": []}
    for lr in sweep_lrs:
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
    print("  [보너스] Adam")
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.6))
    adam_res = {}
    for ax, (fname, f, g) in zip(axes[:2], (("x²+y²", opt.quadratic, opt.quadratic_grad),
                                           ("x²+10y²", opt.elliptic, opt.elliptic_grad))):
        paths = {"VanillaGD": opt.optimize(opt.VanillaGD(0.1), g, x0, 300),
                 "Momentum": opt.optimize(opt.Momentum(0.1, 0.9), g, x0, 300),
                 "Adam": opt.optimize(opt.Adam(0.1), g, x0, 300)}
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
    newton_ell = opt.optimize(opt.NewtonMethod(hess_fn=lambda p: np.diag([2.0, 20.0])),
                              opt.elliptic_grad, x0, 10, stop_tol=1e-10)
    gd_ell = opt.optimize(opt.VanillaGD(0.05), opt.elliptic_grad, x0, 100)
    opt.plot_convergence_paths(opt.elliptic, {"VanillaGD": gd_ell, "Newton": newton_ell}, axes[0],
                               "x²+10y²: Newton reaches minimum in 1 step", (-6, 6), (-6, 6))
    r0 = np.array([-1.5, 2.0])
    newton_rb = opt.optimize(opt.NewtonMethod(f=opt.rosenbrock), opt.rosenbrock_grad, r0, 50, stop_tol=1e-8)
    gd_rb = opt.optimize(opt.VanillaGD(0.001), opt.rosenbrock_grad, r0, 20000)
    opt.plot_convergence_paths(opt.rosenbrock, {"VanillaGD": gd_rb, "Newton": newton_rb}, axes[1],
                               "Rosenbrock: GD lr=0.001 (marker every 500) vs Newton", (-2, 2), (-1, 3),
                               target=(1, 1), log_levels=True, markevery={"VanillaGD": 500})
    s0 = np.array([1.0, 0.5])
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
    """분포 시각화, 소프트맥스, MLE 연결, 정보 이론(보너스)."""
    print("\n[5] 확률/통계")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    prob.plot_normal_pdfs(((0.0, 1.0), (2.0, 0.5)), ax)
    save(fig, "16_normal_pdf.png")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    prob.plot_bernoulli_pmfs((0.3, 0.7), ax)
    save(fig, "17_bernoulli_pmf.png")

    np.random.seed(42)
    logits = np.random.randn(5) * 3
    s = prob.softmax(logits)
    big = prob.softmax(np.array([1000.0, 1001.0, 1002.0]))
    print(f"  softmax({np.round(logits, 3)}) = {np.round(s, 4)}, 합-1 = {abs(s.sum() - 1):.1e}")
    print(f"  softmax([1000,1001,1002]) = {np.round(big, 4)} (overflow 없음)")

    # MSE ↔ 가우시안 MLE: 같은 데이터에서 두 목적 함수의 최소점이 같은지 본다.
    rng = np.random.default_rng(42)
    x = rng.uniform(-2, 2, 50)
    y = 1.5 * x + rng.normal(0, 0.5, 50)
    ws = np.linspace(0, 3, 601)
    mses = np.array([prob.mse(y, w * x) for w in ws])
    nlls = np.array([prob.gaussian_nll(y, w * x, 0.25) for w in ws])
    w_mse, w_nll = ws[np.argmin(mses)], ws[np.argmin(nlls)]
    w_closed = float(np.dot(x, y) / np.dot(x, x))
    # BCE ↔ 베르누이 MLE: 로지스틱 모델 p = σ(w x)
    yb = (rng.uniform(size=50) < 1 / (1 + np.exp(-2 * x))).astype(float)
    bces = np.array([prob.bernoulli_nll(yb, 1 / (1 + np.exp(-w * x))) for w in ws])
    lik = np.array([np.prod(prob.bernoulli_pmf(yb.astype(int), 1 / (1 + np.exp(-w * x)))) for w in ws])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    axes[0].plot(ws, mses, label="MSE(w)")
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
    """전체 실험을 순서대로 실행한다."""
    np.random.seed(42)
    OUT.mkdir(exist_ok=True)
    summary = {}
    run_linear_algebra(summary)
    run_calculus(summary)
    run_backprop(summary)
    run_optimizers(summary)
    run_probability(summary)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n  saved outputs/summary.json")


if __name__ == "__main__":
    main()
