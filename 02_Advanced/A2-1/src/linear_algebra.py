"""선형대수: 행렬 변환, Power Iteration, SVD 이미지 압축.

모든 점 집합은 shape (2, N)으로 다룬다. 열 하나가 점 하나이므로
변환은 ``A @ points`` 한 번의 행렬 곱으로 끝난다.

예를 들어 점 (1, 0), (0, 1), (2, 3)을 담으면 다음 배열이 된다.
0행이 x 좌표들, 1행이 y 좌표들이고 열 하나가 점 하나다.

    [[1, 0, 2],     ← x 좌표
     [0, 1, 3]]     ← y 좌표   shape (2, 3)

미션에서 이 파일이 맡는 문제:
    1. 회전·스케일링·전단 행렬로 도형이 어떻게 바뀌는지 보이고, |det|가 면적비임을 확인한다.
    2. 고유값을 np.linalg.eig 없이 Power Iteration으로 직접 구한다.
    3. SVD로 이미지를 저랭크 근사해 압축률과 화질의 관계를 본다.

읽기 순서와 작은 숫자 예제는 study/code-walkthrough.md의 "1. 선형대수"에 있다.
"""
# import A as B: 라이브러리 A를 짧은 이름 B로 불러온다. 이후 np.xxx, plt.xxx로 쓴다.
# NumPy는 숫자 배열(ndarray) 계산, Matplotlib의 pyplot은 그림 그리기 도구다.
import numpy as np
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# 1. 행렬 변환
# ---------------------------------------------------------------------------

def unit_circle(n_points=100):
    """단위 원 위의 점을 만든다.

    x = cos(θ), y = sin(θ),  θ = linspace(0, 2π, n_points)

    Args:
        n_points: 만들 점의 개수. ``n_points=100``처럼 ``=`` 뒤의 값은 기본값이라
            호출할 때 생략하면 100이 쓰인다.

    Returns:
        np.ndarray: shape (2, n_points). 첫 점과 마지막 점이 같아 닫힌 곡선이 된다.
    """
    # linspace(시작, 끝, 개수)는 양 끝을 포함해 같은 간격의 숫자를 만든다.
    # n_points=5라면 θ = [0, π/2, π, 3π/2, 2π], shape (5,).
    # 0과 2π는 같은 방향이므로 첫 점과 마지막 점이 겹쳐 곡선이 닫힌다.
    theta = np.linspace(0, 2 * np.pi, n_points)
    # np.cos(theta)는 배열의 원소마다 cos를 계산해 같은 shape (n_points,)를 돌려준다.
    # vstack([행1, 행2])은 1차원 배열 두 개를 위아래로 쌓아 (2, n_points)를 만든다.
    # n_points=5의 결과: [[1, 0, −1, 0, 1], [0, 1, 0, −1, 0]] (0에 가까운 값은 반올림해 표기)
    return np.vstack([np.cos(theta), np.sin(theta)])


def rotation_matrix(theta):
    """반시계 방향 회전 행렬 R(θ) = [[cos θ, -sin θ], [sin θ, cos θ]].

    Args:
        theta: 회전 각도(라디안). 45°는 np.pi / 4이다.

    Returns:
        np.ndarray: shape (2, 2) 회전 행렬. 예: θ=90°이면 [[0, −1], [1, 0]]이고
        점 (1, 0)을 (0, 1)로 옮긴다.
    """
    # 쉼표로 두 값을 한 번에 만들고 두 변수에 나눠 담는다(튜플 언패킹).
    c, s = np.cos(theta), np.sin(theta)
    # 중첩 리스트 [[...], [...]]를 np.array로 바꾸면 바깥 리스트가 행, 안쪽이 열인 2x2 배열이 된다.
    return np.array([[c, -s], [s, c]])


def scaling_matrix(sx, sy):
    """축 방향 스케일링 행렬 S(sx, sy) = [[sx, 0], [0, sy]].

    Args:
        sx: x 방향 배율.
        sy: y 방향 배율.

    Returns:
        np.ndarray: shape (2, 2). (x, y)를 (sx·x, sy·y)로 옮긴다.
    """
    # 0.0처럼 소수점을 붙이면 배열 전체가 실수(float) 자료형으로 만들어진다.
    return np.array([[sx, 0.0], [0.0, sy]])


def shear_matrix(k):
    """x축 방향 전단 행렬 Sh(k) = [[1, k], [0, 1]].

    (x, y) → (x + k·y, y). 높이 y에 비례해 옆으로 밀린다.

    Args:
        k: 전단 계수. k=1이면 점 (0, 1)이 (1, 1)로, (0, 2)는 (2, 2)로 밀린다.

    Returns:
        np.ndarray: shape (2, 2) 전단 행렬.
    """
    return np.array([[1.0, k], [0.0, 1.0]])


def transform_points(matrix, points):
    """점 집합에 선형 변환을 적용한다: P' = A @ P.

    Args:
        matrix: shape (2, 2) 변환 행렬 A.
        points: shape (2, N) 점 집합 P.

    Returns:
        np.ndarray: shape (2, N) 변환된 점 집합. 입력 배열은 바뀌지 않고 새 배열이 만들어진다.
    """
    # np.asarray는 리스트를 배열로 바꾼다. 이미 배열이면 복사하지 않고 그대로 쓴다.
    # @는 행렬 곱이다. (2, 2) @ (2, N) → (2, N). 안쪽 크기 2가 맞아야 곱할 수 있다.
    # 열 하나 [x, y]에 대해 [[a, b], [c, d]] @ [x, y] = [a·x + b·y, c·x + d·y]를 N개 열에 한 번에 계산한다.
    # 예: 전단 [[1, 1], [0, 1]] @ [[0, 1], [1, 1]] = [[1, 2], [1, 1]] → 점 (0,1)→(1,1), (1,1)→(2,1).
    return np.asarray(matrix) @ np.asarray(points)


def determinant_2x2(matrix):
    """2x2 행렬식 det([[a, b], [c, d]]) = ad − bc.

    |det(A)|는 변환 A가 모든 도형의 면적을 몇 배로 바꾸는지를 뜻한다.
    부호가 음수이면 방향(시계/반시계)이 뒤집힌다.

    Args:
        matrix: shape (2, 2) 행렬 또는 같은 모양의 중첩 리스트.

    Returns:
        float: 행렬식. 예: [[2, 1], [1, 3]] → 2·3 − 1·1 = 5.
    """
    # 2x2 배열을 반복하면 행이 하나씩 나온다. (a, b), (c, d) = ...는
    # 첫 행을 a, b에, 둘째 행을 c, d에 나눠 담는 중첩 언패킹이다.
    (a, b), (c, d) = np.asarray(matrix, dtype=float)
    # float(...)는 NumPy 숫자를 파이썬 기본 실수로 바꾼다. 출력·JSON 저장이 단순해진다.
    return float(a * d - b * c)


def polygon_area(points):
    """신발끈(Shoelace) 공식으로 닫힌 다각형의 면적을 구한다.

    Area = ½ |Σ (x_i · y_{i+1} − x_{i+1} · y_i)|

    마지막 꼭짓점의 "다음 점"은 첫 꼭짓점이다. 단위 원처럼 첫 점과 끝 점이 같으면
    그 쌍의 항은 0이 되어 결과에 영향을 주지 않는다.

    Args:
        points: shape (2, N) 꼭짓점. 순서대로 이어진 닫힌 곡선이어야 한다.

    Returns:
        float: 면적(항상 0 이상).
    """
    # (2, N) 배열의 두 행을 x, y에 나눠 담는다. 각각 shape (N,).
    x, y = np.asarray(points, dtype=float)
    # np.roll(y, -1)은 원소를 왼쪽으로 한 칸 민다: [y0, y1, y2] → [y1, y2, y0].
    # 그래서 x와 짝지으면 x_i · y_{i+1}이 된다. np.dot(a, b)는 Σ a_i · b_i (곱의 합)이다.
    # 단위 정사각형 (0,0),(1,0),(1,1),(0,1): x=[0,1,1,0], y=[0,0,1,1]
    #   Σ x_i·y_{i+1} = [0,1,1,0]·[0,1,1,0] = 2,  Σ x_{i+1}·y_i = [1,1,0,0]·[0,0,1,1] = 0
    #   면적 = ½ |2 − 0| = 1
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)))


def area_ratio_check(matrix, points=None):
    """변환 전후 면적비와 |det(A)|를 비교한다.

    미션 요구사항 "행렬식과 면적 변화의 관계 확인"을 수치로 검증하는 함수다.
    선형 변환은 모든 도형의 면적을 같은 배율 |det|로 바꾸므로, 원을 100각형으로
    근사해도 면적비는 |det|와 (반올림 오차 범위에서) 정확히 같다.

    Args:
        matrix: shape (2, 2) 변환 행렬.
        points: shape (2, N) 닫힌 다각형. None이면 100점짜리 단위 원을 쓴다.

    Returns:
        dict: det, 변환 전·후 면적, 면적비, 상대 오차(%).
        det가 0이면 상대 오차를 나눗셈 없이 nan(정의되지 않은 수)으로 둔다.
    """
    # 기본값을 None으로 두고 함수 안에서 채우는 것은 파이썬의 흔한 관례다.
    # `is None`은 "값이 비어 있는가"를 확인한다.
    if points is None:
        points = unit_circle()
    det = determinant_2x2(matrix)
    before = polygon_area(points)
    after = polygon_area(transform_points(matrix, points))
    ratio = after / before
    # A if 조건 else B: 조건이 참이면 A, 거짓이면 B를 값으로 쓰는 한 줄 조건식이다.
    # det가 0이면 |det|로 나눌 수 없으므로 nan을 쓴다.
    error_pct = abs(ratio - abs(det)) / abs(det) * 100 if det != 0 else float("nan")
    # {"이름": 값, ...}은 사전(dict)이다. 결과를 이름으로 꺼내 쓸 수 있다: check["det"].
    return {"det": det, "area_before": before, "area_after": after,
            "area_ratio": ratio, "error_pct": error_pct}


def _grid_lines(limit=1.5, n_lines=7, n_samples=50):
    """그림 배경에 깔 격자의 가로·세로 선 목록을 만든다.

    이름 앞의 밑줄(_)은 "이 파일 안에서만 쓰는 보조 함수"라는 관례 표시다.

    Args:
        limit: 격자가 덮는 범위 [-limit, limit].
        n_lines: 방향마다 그을 선의 개수.
        n_samples: 선 하나를 이루는 점의 개수. 변환 후 선이 휘어 보일 일은 없지만
            점이 많아야 transform_points를 그대로 적용해 그릴 수 있다.

    Returns:
        list[np.ndarray]: 세로선 n_lines개 + 가로선 n_lines개. 각 선은 shape (2, n_samples).
    """
    ticks = np.linspace(-limit, limit, n_lines)        # 선이 지나가는 위치 (7,)
    samples = np.linspace(-limit, limit, n_samples)    # 선 위의 점 위치 (50,)
    # meshgrid(a, b)는 a를 열 방향, b를 행 방향으로 펼친 두 배열을 만든다.
    # xs[r, c] = ticks[c], ys[r, c] = samples[r]. 둘 다 shape (50, 7).
    xs, ys = np.meshgrid(ticks, samples)
    # xs[:, i]: 모든 행(:)의 i번 열 → (50,). 값이 모두 ticks[i]라서 x가 고정된 세로선이 된다.
    # [식 for i in range(n)]은 리스트 컴프리헨션: i=0..n-1마다 식을 계산해 리스트로 모은다.
    vertical = [np.vstack([xs[:, i], ys[:, i]]) for i in range(n_lines)]
    # x와 y 자리를 바꾸면 y가 고정된 가로선이 된다.
    horizontal = [np.vstack([ys[:, i], xs[:, i]]) for i in range(n_lines)]
    # 리스트끼리의 +는 이어 붙이기다: 7개 + 7개 = 14개.
    return vertical + horizontal


def plot_transformation(matrix, title, ax=None, points=None):
    """단위 원과 격자에 변환을 적용해 전(파랑)·후(빨강)를 겹쳐 그린다.

    기저 벡터 e1=(1,0), e2=(0,1)이 각각 A의 1열·2열로 옮겨지는 모습도 표시한다.

    Args:
        matrix: shape (2, 2) 변환 행렬.
        title: 그림 제목 첫 줄.
        ax: 그릴 Matplotlib 좌표축(Axes). None이면 새 Figure를 만든다.
        points: 변환할 도형. None이면 단위 원.

    Returns:
        matplotlib.axes.Axes: 그림을 그린 좌표축. 여러 그림을 한 Figure에 모을 때 쓴다.
    """
    if points is None:
        points = unit_circle()
    if ax is None:
        # plt.subplots()는 (Figure, Axes) 두 값을 돌려준다. Figure는 쓰지 않으므로 _에 버린다.
        _, ax = plt.subplots(figsize=(5, 5))
    for line in _grid_lines():
        # *line은 (2, 50) 배열을 두 행으로 풀어 ax.plot(line[0], line[1])처럼 넘긴다.
        ax.plot(*line, color="#9db4d8", lw=0.6, alpha=0.6)
        ax.plot(*transform_points(matrix, line), color="#e8a39b", lw=0.6, alpha=0.6)
    after = transform_points(matrix, points)
    ax.plot(*points, color="tab:blue", lw=2, label="before: unit circle")
    ax.plot(*after, color="tab:red", lw=2, label="after: A @ circle")
    # A @ e1 = A의 0번 열, A @ e2 = A의 1번 열이다. matrix[:, col]은 col번 열을 꺼낸다.
    # 열 두 개만 보면 변환 전체를 알 수 있다는 것이 "행렬의 열 = 기저 벡터의 도착점"이다.
    for col, name in ((0, "Ae1"), (1, "Ae2")):
        vec = np.asarray(matrix)[:, col]
        ax.annotate("", xy=vec, xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color="black", lw=1.5))
        ax.text(vec[0] * 1.08, vec[1] * 1.08, name, fontsize=9)
    check = area_ratio_check(matrix, points)
    # f"...{값:.4f}..."는 값을 소수점 4자리로 끼워 넣은 문자열이다. \n은 줄바꿈.
    ax.set_title(f"{title}\ndet={check['det']:.4f}, area ratio={check['area_ratio']:.4f}")
    # 가로·세로 축의 1 단위를 같은 길이로 맞춘다. 없으면 원이 타원처럼 보일 수 있다.
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

    A=[[4,1],[1,3]], b₀=[1,0]으로 한 번 따라가면
    A b₀ = [4, 1], ‖A b₀‖ = √17 ≈ 4.123, b₁ ≈ [0.970, 0.243]이다.
    정답 고유벡터 [0.851, 0.526] 쪽으로 반복마다 조금씩 회전한다.
    전체 반복 기록은 study/code-walkthrough.md에 있다.

    Args:
        matrix: shape (n, n) 정사각 행렬.
        num_iters: 최대 반복 횟수.
        tol: 연속한 두 단위 벡터의 차이 노름이 tol보다 작으면 수렴으로 본다.
        seed: x0가 없을 때 시작 벡터를 만드는 난수 시드. 같은 seed면 같은 시작 벡터가 나온다.
        x0: 시작 벡터. 지배 고유벡터와 직교하지 않아야 한다.

    Returns:
        dict: eigenvalue, eigenvector(단위 벡터, 가장 큰 성분이 양수),
        iterations, converged, history(반복별 고유값 추정).

    Raises:
        ValueError: 정사각 행렬이 아니거나, 반복 중 A @ b가 0 벡터가 된 경우.
    """
    # dtype=float: 정수 행렬이 들어와도 실수 배열로 바꿔 나눗셈 결과를 그대로 담게 한다.
    A = np.asarray(matrix, dtype=float)
    # ndim은 축의 개수(행렬이면 2), shape는 각 축의 길이 (행 수, 열 수)다.
    if A.ndim != 2 or A.shape[0] != A.shape[1]:
        # raise는 오류를 일으켜 함수를 즉시 멈춘다. 잘못된 입력으로 엉뚱한 답을 내지 않게 한다.
        raise ValueError("power_iteration은 정사각 행렬만 받는다")
    if x0 is None:
        # default_rng(seed)는 난수 생성기다. standard_normal(n)은 평균 0, 표준편차 1인 난수 n개 (n,).
        x0 = np.random.default_rng(seed).standard_normal(A.shape[0])
    b = np.asarray(x0, dtype=float)
    # np.linalg.norm(b)은 벡터 길이 √(Σ b_i²)다. 나누면 길이 1인 단위 벡터가 된다.
    b = b / np.linalg.norm(b)
    history = []           # 빈 리스트. 반복마다 .append로 값을 덧붙인다.
    converged = False
    iterations = num_iters  # 끝까지 수렴하지 못했을 때 남을 값
    # range(1, num_iters + 1)은 1, 2, ..., num_iters. t를 1부터 세어 "몇 번째 반복"과 맞춘다.
    for t in range(1, num_iters + 1):
        Ab = A @ b                 # (n, n) @ (n,) → (n,)
        norm = np.linalg.norm(Ab)
        if norm == 0:
            raise ValueError("A @ b가 0 벡터가 되어 반복할 수 없다")
        # 길이로 나누는 이유: 매번 A를 곱하면 길이가 λ₁^t배로 커져 overflow되거나 0으로 사라진다.
        # 방향만 필요하므로 길이를 1로 되돌린다.
        b_next = Ab / norm
        # 음수 고유값이면 매 반복 부호가 뒤집히므로 부호를 맞춘 뒤 비교한다.
        # 예: b=[1,0], b_next=[−1,0]은 같은 방향(축)이다. b_next − b는 길이 2지만 b_next + b는 0이다.
        if np.dot(b_next, b) < 0:
            diff = np.linalg.norm(b_next + b)
        else:
            diff = np.linalg.norm(b_next - b)
        b = b_next
        # b @ A @ b = bᵀ A b. b가 단위 벡터라 분모 bᵀb = 1을 생략했다. 결과는 숫자 하나(스칼라)다.
        history.append(float(b @ A @ b))
        if diff < tol:
            converged = True
            iterations = t
            break   # for 반복을 즉시 끝낸다.
    eigenvalue = float(b @ A @ b)
    # v와 −v는 둘 다 고유벡터다. 결과를 하나로 정하려고 "절댓값이 가장 큰 성분이 양수"가 되게 맞춘다.
    # np.argmax(np.abs(b))는 절댓값이 가장 큰 원소의 위치(인덱스)를 돌려준다.
    if b[np.argmax(np.abs(b))] < 0:
        b = -b
    return {"eigenvalue": eigenvalue, "eigenvector": b, "iterations": iterations,
            "converged": converged, "history": history}


def compare_with_numpy_eig(matrix, result):
    """Power Iteration 결과를 np.linalg.eig와 비교한다 (검증 전용).

    eig는 여기서 정답 확인에만 쓰고 고유값 계산 자체에는 쓰지 않는다.

    Args:
        matrix: power_iteration에 넣었던 정사각 행렬.
        result: power_iteration의 반환 dict.

    Returns:
        dict: numpy 기준 고유값·고유벡터, 고유값 상대 오차(%), 고유벡터 각도 차(도).
    """
    # eig는 고유값 배열 (n,)과 고유벡터 행렬 (n, n)을 돌려준다. 고유벡터는 "열"로 들어 있다.
    values, vectors = np.linalg.eig(np.asarray(matrix, dtype=float))
    idx = int(np.argmax(np.abs(values)))
    # eig는 일반 행렬에서 복소수를 줄 수 있어 실수부(np.real)만 취한다. 대칭 행렬이면 허수부는 0이다.
    ref_value = float(np.real(values[idx]))
    ref_vector = np.real(vectors[:, idx])
    if ref_vector[np.argmax(np.abs(ref_vector))] < 0:
        ref_vector = -ref_vector
    error_pct = abs(result["eigenvalue"] - ref_value) / abs(ref_value) * 100
    # 두 단위 벡터의 내적은 사잇각의 cos이다. abs로 부호 차이(v와 −v)를 무시한다.
    cos = abs(float(np.dot(ref_vector, result["eigenvector"])))
    # 반올림 때문에 cos가 1.0000000002처럼 1을 살짝 넘으면 arccos가 nan이 되므로 [−1, 1]로 자른다.
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

    작은 예: A = [[3, 0], [0, 1]]이면 σ = [3, 1]이다. k=1이면 A_1 = [[3, 0], [0, 0]]이고
    상대 오차 = ‖A − A_1‖ / ‖A‖ = 1 / √10 ≈ 0.316, 에너지 보존 = 3² / (3² + 1²) = 0.9.

    Args:
        image: shape (m, n) 흑백 이미지, 값 범위 [0, 1].
        k: 사용할 특이값 수. rank보다 크면 rank로 줄인다.

    Returns:
        dict: reconstruction(0~1로 자른 이미지), k(실제 사용 수), 저장 비율,
        상대 Frobenius 오차, 에너지 보존율, PSNR(dB).
        상대 오차와 에너지는 자르기 전 근사 A_k로, PSNR은 자른 뒤 이미지로 계산한다.

    Raises:
        ValueError: image가 2차원 배열이 아닌 경우 (예: RGB 3채널).
    """
    A = np.asarray(image, dtype=float)
    if A.ndim != 2:
        raise ValueError("svd_compress는 2차원 흑백 이미지만 받는다")
    # full_matrices=False("얇은 SVD"): r = min(m, n)일 때 U (m, r), S (r,), Vt (r, n).
    # S는 대각 행렬이 아니라 특이값만 큰 순서로 담은 1차원 배열이다. 128x128 이미지면 r = 128.
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    # S.size는 원소 개수. k=200처럼 rank보다 크게 요청해도 128개까지만 쓴다.
    k_used = int(min(k, S.size))
    # U[:, :k]는 모든 행, 앞 k개 열 → (m, k). S[:k]는 앞 k개 (k,). Vt[:k, :]는 앞 k개 행 → (k, n).
    # (m, k) * (k,)는 브로드캐스팅: U의 j번 열 전체에 S[j]를 곱한다. U_k @ diag(S_k)와 같지만
    # 대각 행렬을 만들지 않는다. 이어서 (m, k) @ (k, n) → (m, n), 원본과 같은 크기의 근사 이미지.
    approx = (U[:, :k_used] * S[:k_used]) @ Vt[:k_used, :]
    # 근사값은 0보다 작거나 1보다 클 수 있다. 화면에 보일 픽셀 범위로 자른 새 배열을 만든다.
    recon = np.clip(approx, 0.0, 1.0)
    m, n = A.shape
    # (A − recon) ** 2: 픽셀마다 차이를 제곱 → (m, n). np.mean은 m·n개 전체의 평균 → 숫자 하나.
    mse = float(np.mean((A - recon) ** 2))
    # PSNR = 10·log10(최댓값² / MSE). 픽셀 최댓값이 1이므로 1 / MSE. 클수록 원본과 가깝다.
    # 오차가 0이면 나눌 수 없으므로 무한대(inf)로 둔다.
    psnr = float("inf") if mse == 0 else float(10 * np.log10(1.0 / mse))
    return {
        "reconstruction": recon,
        "k": k_used,
        # 원본 m·n개 값 대신 U_k(m·k) + σ(k) + V_k(n·k)를 저장한다.
        # 128x128, k=10: 10·(128+128+1) / 16384 = 0.157. 1보다 크면 오히려 저장량이 늘어난다.
        "storage_ratio": k_used * (m + n + 1) / (m * n),
        # 행렬의 norm 기본값은 Frobenius 노름 √(Σ 모든 원소²)이다.
        "relative_error": float(np.linalg.norm(A - approx) / np.linalg.norm(A)),
        # σ_i²의 합은 이미지 전체 "에너지"(Σ 픽셀²)와 같다. 앞 k개가 그중 몇 %를 담는지 본다.
        "energy_retained": float(np.sum(S[:k_used] ** 2) / np.sum(S ** 2)),
        "psnr_db": psnr,
    }


def plot_svd_compression(image, ks=(10, 50, 100), axes=None):
    """원본과 k별 복원 결과를 한 Figure에 나란히 그린다.

    Args:
        image: shape (m, n) 흑백 이미지.
        ks: 비교할 k 값들. (10, 50, 100)처럼 괄호로 묶은 값은 바꿀 수 없는 튜플이다.
        axes: 좌표축 len(ks)+1개. 0번에 원본, 나머지에 복원 결과를 그린다.

    Returns:
        list[dict]: k마다 svd_compress의 결과.
    """
    if axes is None:
        _, axes = plt.subplots(1, len(ks) + 1, figsize=(4 * (len(ks) + 1), 4.4))
    m, n = image.shape
    # imshow는 2차원 배열을 이미지로 그린다. vmin=0, vmax=1로 밝기 기준을 고정해야 k마다 공정하게 비교된다.
    axes[0].imshow(image, cmap="gray", vmin=0, vmax=1)
    axes[0].set_title(f"original {m}x{n}\n{m * n} values")
    results = []
    # zip(a, b)는 두 묶음을 같은 순서끼리 짝지어 준다. axes[1:]은 1번부터 끝까지(슬라이싱).
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
    """특이값 크기와 누적 에너지 비율을 그린다.

    Args:
        image: shape (m, n) 흑백 이미지.
        ks: 점선으로 표시할 k 위치.
        ax: 그릴 좌표축. None이면 새로 만든다.

    Returns:
        np.ndarray: 큰 순서의 특이값 (min(m, n),).
    """
    # compute_uv=False: U, Vt 없이 특이값만 계산해 더 빠르다.
    S = np.linalg.svd(np.asarray(image, dtype=float), compute_uv=False)
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    # semilogy는 y축만 로그 눈금으로 그린다. 특이값은 수백 배 차이가 나서 일반 눈금이면 뒤쪽이 0처럼 보인다.
    # np.arange(1, S.size + 1)은 1, 2, ..., 128 (번호를 1부터 매기려고 +1).
    ax.semilogy(np.arange(1, S.size + 1), S, color="tab:blue", label="singular value σ_i")
    ax.set_xlabel("index i")
    ax.set_ylabel("σ_i (log scale)")
    # twinx는 같은 x축을 공유하고 오른쪽에 두 번째 y축을 만든다.
    twin = ax.twinx()
    # np.cumsum은 누적 합이다: [9, 1] → [9, 10]. 전체 합으로 나누면 [0.9, 1.0]인 누적 비율.
    twin.plot(np.arange(1, S.size + 1), np.cumsum(S ** 2) / np.sum(S ** 2),
              color="tab:orange", label="cumulative energy")
    twin.set_ylabel("cumulative energy Σσ²")
    twin.set_ylim(0, 1.02)
    for k in ks:
        ax.axvline(k, color="gray", ls="--", lw=0.8)
    ax.set_title("Singular value spectrum")
    return S
