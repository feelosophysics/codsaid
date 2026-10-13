"""보너스 1: 가우시안 블러를 OpenCV 없이 NumPy만으로 구현한다.

컨볼루션의 한 출력 픽셀 = 커널과 같은 크기의 이미지 조각과 커널의 내적(원소곱의 합)이다.
가우시안 커널은 좌우 대칭이라 커널을 뒤집는 컨볼루션과 뒤집지 않는 상관(correlation)의 결과가 같다.
경계는 OpenCV 기본값(BORDER_REFLECT_101: 가장자리 픽셀을 반복하지 않는 거울 반사)과 같게 채운다.
"""
import time

import numpy as np

# sigma를 정하지 않은 작은 커널은 OpenCV가 공식 대신 이 정수비 표를 쓴다 (이항계수와 비슷한 값).
SMALL_KERNELS = {
    1: [1.0],
    3: [0.25, 0.5, 0.25],
    5: [0.0625, 0.25, 0.375, 0.25, 0.0625],
    7: [0.03125, 0.109375, 0.21875, 0.28125, 0.21875, 0.109375, 0.03125],
    9: [v / 256 for v in (4, 13, 30, 51, 60, 51, 30, 13, 4)],
}


def gaussian_kernel_1d(ksize, sigma=0.0):
    """1차원 가우시안 가중치. sigma ≤ 0이면 OpenCV와 같은 규칙으로 커널 크기에서 정한다."""
    if ksize < 1 or ksize % 2 == 0:
        raise ValueError("커널 크기는 양의 홀수여야 한다")
    if sigma <= 0 and ksize in SMALL_KERNELS:
        return np.array(SMALL_KERNELS[ksize])
    if sigma <= 0:
        sigma = 0.3 * ((ksize - 1) * 0.5 - 1) + 0.8
    x = np.arange(ksize) - (ksize - 1) / 2
    k = np.exp(-(x ** 2) / (2 * sigma ** 2))
    return k / k.sum()


def gaussian_kernel_2d(ksize, sigma=0.0):
    """2차원 커널 = 1차원 커널의 외적. 가우시안은 x·y로 분리되기 때문이다."""
    k = gaussian_kernel_1d(ksize, sigma)
    return np.outer(k, k)


def pad_reflect101(image, pad):
    """OpenCV BORDER_REFLECT_101과 같은 경계 채우기 (예: [a b c d] → c b | a b c d | c b)."""
    return np.pad(image, pad, mode="reflect")


def convolve_loops(image, kernel):
    """이중 for문 버전: 출력 픽셀마다 이미지 조각과 커널의 내적을 계산한다."""
    img = np.asarray(image, dtype=np.float64)
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = pad_reflect101(img, ((ph, ph), (pw, pw)))
    h, w = img.shape
    out = np.empty((h, w), dtype=np.float64)
    for y in range(h):
        for x in range(w):
            patch = padded[y:y + kh, x:x + kw]
            out[y, x] = np.sum(patch * kernel)
    return out


def convolve_vectorized(image, kernel):
    """벡터화 버전: 커널의 각 칸만큼 이미지 전체를 밀어 가중합한다.

    for문은 픽셀 수(H·W)가 아니라 커널 칸 수(k²)만큼만 돈다. 각 반복은 이미지 전체에 대한 배열 연산이다.
    """
    img = np.asarray(image, dtype=np.float64)
    kh, kw = kernel.shape
    ph, pw = kh // 2, kw // 2
    padded = pad_reflect101(img, ((ph, ph), (pw, pw)))
    h, w = img.shape
    out = np.zeros((h, w), dtype=np.float64)
    for dy in range(kh):
        for dx in range(kw):
            out += kernel[dy, dx] * padded[dy:dy + h, dx:dx + w]
    return out


def convolve_strided(image, kernel):
    """sliding_window_view로 모든 조각을 (H, W, kh, kw) 뷰로 만든 뒤 einsum으로 한 번에 내적한다."""
    img = np.asarray(image, dtype=np.float64)
    kh, kw = kernel.shape
    padded = pad_reflect101(img, ((kh // 2, kh // 2), (kw // 2, kw // 2)))
    windows = np.lib.stride_tricks.sliding_window_view(padded, (kh, kw))
    return np.einsum("ijkl,kl->ij", windows, kernel)


def blur_separable(image, ksize, sigma=0.0):
    """분리 가능 버전: 가로 1차원 → 세로 1차원. 연산량이 k²에서 2k로 준다."""
    k = gaussian_kernel_1d(ksize, sigma)
    tmp = convolve_vectorized(image, k[None, :])
    return convolve_vectorized(tmp, k[:, None])


def gaussian_blur(image, ksize, sigma=0.0, method="vectorized"):
    """uint8 이미지를 받아 블러한 uint8 이미지를 돌려준다 (컬러는 채널별로 처리)."""
    funcs = {"loops": convolve_loops, "vectorized": convolve_vectorized, "strided": convolve_strided}
    img = np.asarray(image)
    if img.ndim == 3:
        return np.dstack([gaussian_blur(img[..., c], ksize, sigma, method) for c in range(img.shape[2])])
    out = blur_separable(img, ksize, sigma) if method == "separable" else funcs[method](img, gaussian_kernel_2d(ksize, sigma))
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def benchmark(image, ksize=5, repeats=3, methods=("loops", "vectorized", "strided", "separable")):
    """각 방법의 실행 시간(초, 반복 중 최솟값)과 결과를 돌려준다."""
    img = np.asarray(image, dtype=np.float64)
    kernel = gaussian_kernel_2d(ksize)
    runners = {
        "loops": lambda: convolve_loops(img, kernel),
        "vectorized": lambda: convolve_vectorized(img, kernel),
        "strided": lambda: convolve_strided(img, kernel),
        "separable": lambda: blur_separable(img, ksize),
    }
    results = {}
    for name in methods:
        best, out = float("inf"), None
        for _ in range(1 if name == "loops" else repeats):
            t0 = time.perf_counter()
            out = runners[name]()
            best = min(best, time.perf_counter() - t0)
        results[name] = {"seconds": best, "output": out}
    return results
