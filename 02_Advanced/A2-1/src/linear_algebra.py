"""선형대수: 행렬 변환, Power Iteration, SVD 이미지 압축.

모든 점 집합은 shape (2, N)으로 다룬다. 열 하나가 점 하나이므로
변환은 ``A @ points`` 한 번의 행렬 곱으로 끝난다.
"""
import numpy as np
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# 1. 행렬 변환
# ---------------------------------------------------------------------------

def unit_circle(n_points=100):
    """단위 원 위의 점을 만든다.

    x = cos(θ), y = sin(θ),  θ = linspace(0, 2π, n_points)

    Returns:
        np.ndarray: shape (2, n_points). 첫 점과 마지막 점이 같아 닫힌 곡선이 된다.
    """
    theta = np.linspace(0, 2 * np.pi, n_points)
    return np.vstack([np.cos(theta), np.sin(theta)])


def rotation_matrix(theta):
    """반시계 방향 회전 행렬 R(θ) = [[cos θ, -sin θ], [sin θ, cos θ]]."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]])


def scaling_matrix(sx, sy):
    """축 방향 스케일링 행렬 S(sx, sy) = [[sx, 0], [0, sy]]."""
    return np.array([[sx, 0.0], [0.0, sy]])


def shear_matrix(k):
    """x축 방향 전단 행렬 Sh(k) = [[1, k], [0, 1]].

    (x, y) → (x + k·y, y). 높이 y에 비례해 옆으로 밀린다.
    """
    return np.array([[1.0, k], [0.0, 1.0]])


def transform_points(matrix, points):
    """점 집합에 선형 변환을 적용한다: P' = A @ P.

    Args:
        matrix: shape (2, 2) 변환 행렬 A.
        points: shape (2, N) 점 집합 P.

    Returns:
        np.ndarray: shape (2, N) 변환된 점 집합.
    """
    return np.asarray(matrix) @ np.asarray(points)


def determinant_2x2(matrix):
    """2x2 행렬식 det([[a, b], [c, d]]) = ad − bc.

    |det(A)|는 변환 A가 모든 도형의 면적을 몇 배로 바꾸는지를 뜻한다.
    부호가 음수이면 방향(시계/반시계)이 뒤집힌다.
    """
    (a, b), (c, d) = np.asarray(matrix, dtype=float)
    return float(a * d - b * c)


def polygon_area(points):
    """신발끈(Shoelace) 공식으로 닫힌 다각형의 면적을 구한다.

    Area = ½ |Σ (x_i · y_{i+1} − x_{i+1} · y_i)|

    Args:
        points: shape (2, N) 꼭짓점. 순서대로 이어진 닫힌 곡선이어야 한다.
    """
    x, y = np.asarray(points, dtype=float)
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)))


def area_ratio_check(matrix, points=None):
    """변환 전후 면적비와 |det(A)|를 비교한다.

    Returns:
        dict: det, 변환 전·후 면적, 면적비, 상대 오차(%).
    """
    if points is None:
        points = unit_circle()
    det = determinant_2x2(matrix)
    before = polygon_area(points)
    after = polygon_area(transform_points(matrix, points))
    ratio = after / before
    error_pct = abs(ratio - abs(det)) / abs(det) * 100 if det != 0 else float("nan")
    return {"det": det, "area_before": before, "area_after": after,
            "area_ratio": ratio, "error_pct": error_pct}


def _grid_lines(limit=1.5, n_lines=7, n_samples=50):
    """meshgrid로 만든 격자의 가로·세로 선 목록. 각 선은 shape (2, n_samples)."""
    ticks = np.linspace(-limit, limit, n_lines)
    samples = np.linspace(-limit, limit, n_samples)
    xs, ys = np.meshgrid(ticks, samples)
    vertical = [np.vstack([xs[:, i], ys[:, i]]) for i in range(n_lines)]
    horizontal = [np.vstack([ys[:, i], xs[:, i]]) for i in range(n_lines)]
    return vertical + horizontal


def plot_transformation(matrix, title, ax=None, points=None):
    """단위 원과 격자에 변환을 적용해 전(파랑)·후(빨강)를 겹쳐 그린다.

    기저 벡터 e1=(1,0), e2=(0,1)이 각각 A의 1열·2열로 옮겨지는 모습도 표시한다.
    """
    if points is None:
        points = unit_circle()
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    for line in _grid_lines():
        ax.plot(*line, color="#9db4d8", lw=0.6, alpha=0.6)
        ax.plot(*transform_points(matrix, line), color="#e8a39b", lw=0.6, alpha=0.6)
    after = transform_points(matrix, points)
    ax.plot(*points, color="tab:blue", lw=2, label="before: unit circle")
    ax.plot(*after, color="tab:red", lw=2, label="after: A @ circle")
    for col, name in ((0, "Ae1"), (1, "Ae2")):
        vec = np.asarray(matrix)[:, col]
        ax.annotate("", xy=vec, xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.5))
        ax.text(vec[0] * 1.08, vec[1] * 1.08, name, fontsize=9)
    check = area_ratio_check(matrix, points)
    ax.set_title(f"{title}\ndet={check['det']:.4f}, area ratio={check['area_ratio']:.4f}")
    ax.set_aspect("equal")
    ax.set_xlim(-2.6, 2.6)
    ax.set_ylim(-2.6, 2.6)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.legend(loc="lower right", fontsize=8)
    return ax


# ---------------------------------------------------------------------------
# 2. 고유값: Power Iteration
# ---------------------------------------------------------------------------

def power_iteration(matrix, num_iters=1000, tol=1e-6, seed=42, x0=None):
    """Power Iteration으로 절댓값이 가장 큰 고유값과 고유벡터를 구한다.

    반복식:  b_{t+1} = A b_t / ‖A b_t‖
    고유값 추정(Rayleigh quotient):  λ = bᵀ A b / bᵀ b

    A를 반복해서 곱하면 가장 큰 |λ|를 가진 고유벡터 성분만 상대적으로 커지고
    나머지는 (|λ₂|/|λ₁|)^t 비율로 사라진다.

    Args:
        matrix: shape (n, n) 정사각 행렬.
        num_iters: 최대 반복 횟수.
        tol: 연속한 두 단위 벡터의 차이 노름이 tol보다 작으면 수렴으로 본다.
        seed: x0가 없을 때 시작 벡터를 만드는 난수 시드.
        x0: 시작 벡터. 지배 고유벡터와 직교하지 않아야 한다.

    Returns:
        dict: eigenvalue, eigenvector(단위 벡터, 가장 큰 성분이 양수),
        iterations, converged, history(반복별 고유값 추정).
    """
    A = np.asarray(matrix, dtype=float)
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("power_iteration은 정사각 행렬만 받는다")
    if x0 is None:
        x0 = np.random.default_rng(seed).standard_normal(A.shape[0])
    b = np.asarray(x0, dtype=float)
    b = b / np.linalg.norm(b)
    history = []
    converged = False
    iterations = num_iters
    for t in range(1, num_iters + 1):
        Ab = A @ b
        norm = np.linalg.norm(Ab)
        if norm == 0:
            raise ValueError("A @ b가 0 벡터가 되어 반복할 수 없다")
        b_next = Ab / norm
        # 음수 고유값이면 매 반복 부호가 뒤집히므로 부호를 맞춘 뒤 비교한다.
        if np.dot(b_next, b) < 0:
            diff = np.linalg.norm(b_next + b)
        else:
            diff = np.linalg.norm(b_next - b)
        b = b_next
        history.append(float(b @ A @ b))
        if diff < tol:
            converged = True
            iterations = t
            break
    eigenvalue = float(b @ A @ b)
    if b[np.argmax(np.abs(b))] < 0:
        b = -b
    return {"eigenvalue": eigenvalue, "eigenvector": b, "iterations": iterations,
            "converged": converged, "history": history}


def compare_with_numpy_eig(matrix, result):
    """Power Iteration 결과를 np.linalg.eig와 비교한다 (검증 전용).

    eig는 여기서 정답 확인에만 쓰고 고유값 계산 자체에는 쓰지 않는다.

    Returns:
        dict: numpy 기준 고유값·고유벡터, 고유값 상대 오차(%), 고유벡터 각도 차(도).
    """
    values, vectors = np.linalg.eig(np.asarray(matrix, dtype=float))
    idx = int(np.argmax(np.abs(values)))
    ref_value = float(np.real(values[idx]))
    ref_vector = np.real(vectors[:, idx])
    if ref_vector[np.argmax(np.abs(ref_vector))] < 0:
        ref_vector = -ref_vector
    error_pct = abs(result["eigenvalue"] - ref_value) / abs(ref_value) * 100
    cos = abs(float(np.dot(ref_vector, result["eigenvector"])))
    angle = float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))
    return {"eigenvalue": ref_value, "eigenvector": ref_vector,
            "error_pct": error_pct, "vector_angle_deg": angle}


# ---------------------------------------------------------------------------
# 3. SVD 이미지 압축
# ---------------------------------------------------------------------------

def svd_compress(image, k):
    """상위 k개 특이값으로 이미지를 근사한다.

    A = U Σ Vᵀ = Σ_i σ_i u_i v_iᵀ  →  A_k = Σ_{i<k} σ_i u_i v_iᵀ

    Eckart–Young 정리에 따라 A_k는 rank-k 행렬 중 Frobenius 오차가 가장 작다.

    Args:
        image: shape (m, n) 흑백 이미지, 값 범위 [0, 1].
        k: 사용할 특이값 수. rank보다 크면 rank로 줄인다.

    Returns:
        dict: reconstruction(0~1로 자른 이미지), k(실제 사용 수), 저장 비율,
        상대 Frobenius 오차, 에너지 보존율, PSNR(dB).
    """
    A = np.asarray(image, dtype=float)
    if A.ndim != 2:
        raise ValueError("svd_compress는 2차원 흑백 이미지만 받는다")
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    k_used = int(min(k, S.size))
    approx = (U[:, :k_used] * S[:k_used]) @ Vt[:k_used, :]
    recon = np.clip(approx, 0.0, 1.0)
    m, n = A.shape
    mse = float(np.mean((A - recon) ** 2))
    psnr = float("inf") if mse == 0 else float(10 * np.log10(1.0 / mse))
    return {
        "reconstruction": recon,
        "k": k_used,
        # 원본 m·n개 값 대신 U_k(m·k) + σ(k) + V_k(n·k)를 저장한다.
        "storage_ratio": k_used * (m + n + 1) / (m * n),
        "relative_error": float(np.linalg.norm(A - approx) / np.linalg.norm(A)),
        "energy_retained": float(np.sum(S[:k_used] ** 2) / np.sum(S ** 2)),
        "psnr_db": psnr,
    }


def plot_svd_compression(image, ks=(10, 50, 100), axes=None):
    """원본과 k별 복원 결과를 한 Figure에 나란히 그린다."""
    if axes is None:
        _, axes = plt.subplots(1, len(ks) + 1, figsize=(4 * (len(ks) + 1), 4.4))
    m, n = image.shape
    axes[0].imshow(image, cmap="gray", vmin=0, vmax=1)
    axes[0].set_title(f"original {m}x{n}\n{m * n} values")
    results = []
    for ax, k in zip(axes[1:], ks):
        res = svd_compress(image, k)
        results.append(res)
        ax.imshow(res["reconstruction"], cmap="gray", vmin=0, vmax=1)
        ax.set_title(f"k={res['k']}  PSNR={res['psnr_db']:.1f} dB\n"
                     f"storage={res['storage_ratio']:.2f}x, energy={res['energy_retained']:.4f}")
    for ax in axes:
        ax.axis("off")
    return results


def plot_singular_values(image, ks=(10, 50, 100), ax=None):
    """특이값 크기와 누적 에너지 비율을 그린다."""
    S = np.linalg.svd(np.asarray(image, dtype=float), compute_uv=False)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(np.arange(1, S.size + 1), S, color="tab:blue", label="singular value σ_i")
    ax.set_xlabel("index i")
    ax.set_ylabel("σ_i (log scale)")
    twin = ax.twinx()
    twin.plot(np.arange(1, S.size + 1), np.cumsum(S ** 2) / np.sum(S ** 2),
              color="tab:orange", label="cumulative energy")
    twin.set_ylabel("cumulative energy Σσ²")
    twin.set_ylim(0, 1.02)
    for k in ks:
        ax.axvline(k, color="gray", ls="--", lw=0.8)
    ax.set_title("Singular value spectrum")
    return S
