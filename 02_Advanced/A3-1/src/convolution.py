"""보너스 1: 가우시안 블러를 OpenCV 없이 NumPy만으로 구현한다.

컨볼루션의 한 출력 픽셀 = 커널과 같은 크기의 이미지 조각과 커널의 내적(원소곱의 합)이다.
가우시안 커널은 좌우 대칭이라 커널을 뒤집는 컨볼루션과 뒤집지 않는 상관(correlation)의 결과가 같다.
경계는 OpenCV 기본값(BORDER_REFLECT_101: 가장자리 픽셀을 반복하지 않는 거울 반사)과 같게 채운다.

같은 계산을 네 방법으로 구현하고 실행 시간을 비교한다(run_all.convolution_bonus, 480×360 회색, 5×5 커널).
    convolve_loops       픽셀마다 for문           반복 172,800번(= 480 × 360)
    convolve_vectorized  커널 칸마다 for문         반복 25번(= 5 × 5), 매번 이미지 전체 배열 연산
    convolve_strided     반복 없음               (480, 360, 5, 5) 조각 뷰를 einsum으로 한 번에
    blur_separable       가로 1차원 → 세로 1차원   칸 수 25 → 10
작은 숫자 예제는 study/code-walkthrough.md 10장에 있다.
"""
import time

import numpy as np

# sigma를 정하지 않은 작은 커널은 OpenCV가 공식 대신 이 정수비 표를 쓴다 (이항계수와 비슷한 값).
# 예: 5 → [1, 4, 6, 4, 1] / 16. 키 9의 값은 리스트 컴프리헨션 [v / 256 for v in ...]으로 만든다.
SMALL_KERNELS = {
    1: [1.0],
    3: [0.25, 0.5, 0.25],
    5: [0.0625, 0.25, 0.375, 0.25, 0.0625],
    7: [0.03125, 0.109375, 0.21875, 0.28125, 0.21875, 0.109375, 0.03125],
    9: [v / 256 for v in (4, 13, 30, 51, 60, 51, 30, 13, 4)],
}


def gaussian_kernel_1d(ksize, sigma=0.0):
    """1차원 가우시안 가중치. sigma ≤ 0이면 OpenCV와 같은 규칙으로 커널 크기에서 정한다.

    큰 커널 예(설명용 계산): ksize=11이면 sigma = 0.3 × ((11 − 1) × 0.5 − 1) + 0.8 = 2.0.

    Args:
        ksize: 커널 길이. 양의 홀수.
        sigma: 표준편차. 0 이하면 자동.

    Returns:
        numpy.ndarray: (ksize,) 가중치. 합이 1이라 블러해도 전체 밝기가 유지된다.

    Raises:
        ValueError: ksize가 양의 홀수가 아닌 경우.
    """
    # 홀수여야 가운데 칸이 있어 출력 픽셀이 조각의 정중앙에 놓인다.
    if ksize < 1 or ksize % 2 == 0:
        raise ValueError("커널 크기는 양의 홀수여야 한다")
    if sigma <= 0 and ksize in SMALL_KERNELS:  # "in"은 dict의 키 중에 있는지 확인한다
        return np.array(SMALL_KERNELS[ksize])
    if sigma <= 0:
        sigma = 0.3 * ((ksize - 1) * 0.5 - 1) + 0.8
    # arange(5)는 [0, 1, 2, 3, 4]. 가운데 2를 빼면 [−2, −1, 0, 1, 2] = 중심에서의 거리.
    x = np.arange(ksize) - (ksize - 1) / 2
    k = np.exp(-(x ** 2) / (2 * sigma ** 2))  # **는 거듭제곱. exp는 원소마다 e^값
    return k / k.sum()  # 합으로 나눠 합을 1로 맞춘다(정규화)


def gaussian_kernel_2d(ksize, sigma=0.0):
    """2차원 커널 = 1차원 커널의 외적. 가우시안은 x·y로 분리되기 때문이다.

    예: [0.25, 0.5, 0.25]의 외적 → 가운데 0.25, 상하좌우 0.125, 네 귀퉁이 0.0625인 3×3.

    Args:
        ksize: 커널 크기. 양의 홀수.
        sigma: 표준편차. 0 이하면 자동.

    Returns:
        numpy.ndarray: (ksize, ksize) 커널. 합은 1.
    """
    k = gaussian_kernel_1d(ksize, sigma)
    return np.outer(k, k)  # outer(u, v)[i, j] = u[i] · v[j]. (k,)와 (k,) → (k, k)


def pad_reflect101(image, pad):
    """OpenCV BORDER_REFLECT_101과 같은 경계 채우기 (예: [a b c d] → c b | a b c d | c b).

    가장자리 픽셀도 온전한 k×k 조각을 갖게 하려고 바깥을 채운다. 0으로 채우면 가장자리가 어두워진다.
    NumPy의 mode="reflect"는 가장자리 값 자체를 반복하지 않으므로 REFLECT_101과 같다.
    설명용 예: [1, 2, 3, 4]를 양쪽 2칸 → [3, 2, 1, 2, 3, 4, 3, 2].

    Args:
        image: 2차원 배열 (H, W).
        pad: 축별 채울 칸 수. ((위, 아래), (왼쪽, 오른쪽)) 또는 정수 하나.

    Returns:
        numpy.ndarray: 테두리를 채운 새 배열. 커널 5면 (H + 4, W + 4).
    """
    return np.pad(image, pad, mode="reflect")


def convolve_loops(image, kernel):
    """이중 for문 버전: 출력 픽셀마다 이미지 조각과 커널의 내적을 계산한다.

    정의를 그대로 옮긴 가장 읽기 쉬운 버전이자 가장 느린 버전이다. 결과의 정답 기준으로 쓴다.

    Args:
        image: 2차원 회색 이미지 (H, W).
        kernel: 2차원 커널 (kh, kw). 홀수 크기.

    Returns:
        numpy.ndarray: (H, W) float64 새 배열. 입력과 크기가 같다.
    """
    img = np.asarray(image, dtype=np.float64)  # 실수로 바꿔 소수 가중합을 그대로 계산한다. uint8로 되돌리는 일은 gaussian_blur가 한다
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2  # //는 몫(정수 나눗셈). 커널 5 → 위아래 2칸씩 채운다
    padded = pad_reflect101(img, ((ph, ph), (pw, pw)))
    h, w = img.shape
    out = np.empty((h, w), dtype=np.float64)  # empty는 값을 초기화하지 않은 새 배열. 모든 칸을 아래에서 채운다
    for y in range(h):
        for x in range(w):
            # padded[y:y+kh, x:x+kw]는 (kh, kw) 조각. 채운 배열에서 y번째 줄부터 kh줄을 자르면
            # 원래 이미지의 (y, x)가 조각의 정중앙에 온다. 슬라이싱은 복사하지 않는 "뷰"다.
            patch = padded[y:y + kh, x:x + kw]
            out[y, x] = np.sum(patch * kernel)  # *는 같은 위치끼리 곱. 곱 25개를 모두 더하면 내적
    return out


def convolve_vectorized(image, kernel):
    """벡터화 버전: 커널의 각 칸만큼 이미지 전체를 밀어 가중합한다.

    for문은 픽셀 수(H·W)가 아니라 커널 칸 수(k²)만큼만 돈다. 각 반복은 이미지 전체에 대한 배열 연산이다.

    convolve_loops와 더하는 순서만 다르고 같은 곱들을 더한다. 출력 (y, x)에 kernel[dy, dx] × padded[y+dy, x+dx]가
    한 번씩 더해지는 것은 두 방법이 같다.

    Args:
        image: 2차원 회색 이미지 (H, W).
        kernel: 2차원 커널 (kh, kw). 1×k나 k×1처럼 한 방향 커널도 된다.

    Returns:
        numpy.ndarray: (H, W) float64 새 배열.
    """
    img = np.asarray(image, dtype=np.float64)
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = pad_reflect101(img, ((ph, ph), (pw, pw)))
    h, w = img.shape
    out = np.zeros((h, w), dtype=np.float64)
    for dy in range(kh):
        for dx in range(kw):
            # padded[dy:dy+h, dx:dx+w]는 (H, W) 크기이고, 그 (y, x) 칸은 원래 이미지의 (y+dy−ph, x+dx−pw) 픽셀이다.
            # 숫자 하나 × (H, W) 배열 → (H, W). +=로 out을 제자리에서 누적한다.
            out += kernel[dy, dx] * padded[dy:dy + h, dx:dx + w]
    return out


def convolve_strided(image, kernel):
    """sliding_window_view로 모든 조각을 (H, W, kh, kw) 뷰로 만든 뒤 einsum으로 한 번에 내적한다.

    Args:
        image: 2차원 회색 이미지 (H, W).
        kernel: 2차원 커널 (kh, kw).

    Returns:
        numpy.ndarray: (H, W) float64 새 배열.
    """
    img = np.asarray(image, dtype=np.float64)
    kh, kw = kernel.shape
    padded = pad_reflect101(img, ((kh // 2, kh // 2), (kw // 2, kw // 2)))
    # (H+4, W+4) → (H, W, 5, 5). windows[y, x]가 출력 (y, x)의 5×5 조각이다.
    # 데이터를 복사하지 않고 같은 메모리를 다르게 읽는 "뷰"라서, 25배 큰 배열을 실제로 만들지 않는다.
    windows = np.lib.stride_tricks.sliding_window_view(padded, (kh, kw))
    # einsum("ijkl,kl->ij"): 이름이 같은 축 k, l은 곱해서 더하고, 화살표 뒤에 남긴 i, j가 결과 축이다.
    # 즉 out[i, j] = Σₖ Σₗ windows[i, j, k, l] · kernel[k, l] → (H, W).
    return np.einsum("ijkl,kl->ij", windows, kernel)


def blur_separable(image, ksize, sigma=0.0):
    """분리 가능 버전: 가로 1차원 → 세로 1차원. 연산량이 k²에서 2k로 준다.

    2차원 가우시안 커널이 outer(k, k)라서, 가로로 k를 한 번 적용한 뒤 세로로 k를 한 번 적용하면 같은 결과다.

    Args:
        image: 2차원 회색 이미지 (H, W).
        ksize: 커널 크기. 양의 홀수.
        sigma: 표준편차. 0 이하면 자동.

    Returns:
        numpy.ndarray: (H, W) float64 새 배열.
    """
    k = gaussian_kernel_1d(ksize, sigma)
    # k[None, :]는 (k,)에 앞 축을 추가한 (1, k) = 가로 한 줄 커널. k[:, None]은 (k, 1) = 세로 한 줄 커널.
    tmp = convolve_vectorized(image, k[None, :])
    return convolve_vectorized(tmp, k[:, None])


def gaussian_blur(image, ksize, sigma=0.0, method="vectorized"):
    """uint8 이미지를 받아 블러한 uint8 이미지를 돌려준다 (컬러는 채널별로 처리).

    Args:
        image: (H, W) 회색 또는 (H, W, C) 컬러 uint8 이미지.
        ksize: 커널 크기. 양의 홀수.
        sigma: 표준편차. 0 이하면 자동.
        method: "loops", "vectorized", "strided", "separable" 중 하나.

    Returns:
        numpy.ndarray: 입력과 같은 shape의 uint8 새 이미지.
    """
    # dict 값으로 함수 자체를 넣어 두고 funcs[method]로 꺼내 부른다. if문 네 개를 대신한다.
    funcs = {"loops": convolve_loops, "vectorized": convolve_vectorized, "strided": convolve_strided}
    img = np.asarray(image)
    if img.ndim == 3:
        # img[..., c]는 "앞의 모든 축은 그대로, 마지막 축의 c번" = c번 채널 (H, W).
        # 함수가 자기 자신을 부른다(재귀). 채널마다 2차원 블러 → dstack으로 마지막 축에 다시 쌓아 (H, W, C).
        return np.dstack([gaussian_blur(img[..., c], ksize, sigma, method) for c in range(img.shape[2])])
    out = blur_separable(img, ksize, sigma) if method == "separable" else funcs[method](img, gaussian_kernel_2d(ksize, sigma))
    # rint는 가장 가까운 정수로 반올림, clip은 0~255 밖을 경계값으로 자른다. 그 뒤에야 uint8로 안전하게 바꿀 수 있다.
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def benchmark(image, ksize=5, repeats=3, methods=("loops", "vectorized", "strided", "separable")):
    """각 방법의 실행 시간(초, 반복 중 최솟값)과 결과를 돌려준다.

    최솟값을 쓰는 이유: 다른 프로그램이 CPU를 잠깐 쓰면 시간이 늘어날 뿐 줄지는 않는다. 가장 빠른 회가
    그 방법 자체의 시간에 가장 가깝다. 시간은 컴퓨터와 그때의 부하에 따라 매번 달라진다.

    Args:
        image: 2차원 회색 이미지.
        ksize: 커널 크기.
        repeats: 방법마다 반복할 횟수. 느린 loops는 1번만 돈다.
        methods: 비교할 방법 이름들.

    Returns:
        dict: {방법: {"seconds": 초, "output": (H, W) 결과}}.
    """
    img = np.asarray(image, dtype=np.float64)
    kernel = gaussian_kernel_2d(ksize)
    # lambda: 식 은 인자 없는 한 줄 함수. 지금 실행하지 않고 runners[name]()처럼 부를 때 실행된다.
    runners = {
        "loops": lambda: convolve_loops(img, kernel),
        "vectorized": lambda: convolve_vectorized(img, kernel),
        "strided": lambda: convolve_strided(img, kernel),
        "separable": lambda: blur_separable(img, ksize),
    }
    results = {}
    for name in methods:
        best, out = float("inf"), None  # 무한대에서 시작하면 첫 측정값이 반드시 더 작다
        for _ in range(1 if name == "loops" else repeats):  # 반복 번호를 쓰지 않으므로 _로 받는다
            t0 = time.perf_counter()
            out = runners[name]()
            best = min(best, time.perf_counter() - t0)
        results[name] = {"seconds": best, "output": out}
    return results
