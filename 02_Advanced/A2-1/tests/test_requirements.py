"""미션 요구사항의 수치 기준을 그대로 검증하는 테스트.

실행:  python -m unittest discover -s tests -v
"""
import unittest

import matplotlib
matplotlib.use("Agg")
import numpy as np  # noqa: E402

from src import calculus as calc  # noqa: E402
from src import information as info  # noqa: E402
from src import linear_algebra as la  # noqa: E402
from src import optimizer as opt  # noqa: E402
from src import probability as prob  # noqa: E402
from src.neural_net import TwoLayerNet, example_network  # noqa: E402
from src.run_all import load_grayscale_image  # noqa: E402


class LinearAlgebraTest(unittest.TestCase):
    """1. 선형대수: 행렬 변환과 분해."""

    def test_unit_circle_shape_and_radius(self):
        circle = la.unit_circle()
        self.assertEqual(circle.shape, (2, 100))
        np.testing.assert_allclose(np.linalg.norm(circle, axis=0), 1.0)

    def test_det_matches_area_ratio_within_1_percent(self):
        for A in (la.rotation_matrix(0.7), la.scaling_matrix(2, 0.5), la.shear_matrix(1.0),
                  np.array([[2.0, 1.0], [1.0, 3.0]]), np.array([[0.0, 2.0], [1.0, 0.0]])):
            check = la.area_ratio_check(A)
            self.assertAlmostEqual(check["det"], np.linalg.det(A), places=12)
            self.assertLess(check["error_pct"], 1.0)

    def test_transforms_change_shape_as_expected(self):
        circle = la.unit_circle()
        rotated = la.transform_points(la.rotation_matrix(np.pi / 3), circle)
        np.testing.assert_allclose(np.linalg.norm(rotated, axis=0), 1.0)    # 회전: 거리 보존
        ellipse = la.transform_points(la.scaling_matrix(2, 0.5), circle)
        self.assertAlmostEqual(ellipse[0].max(), 2.0)                       # 가로 2배
        self.assertAlmostEqual(ellipse[1].max(), 0.5, places=3)             # 세로 0.5배
        sheared = la.transform_points(la.shear_matrix(1.0), circle)
        np.testing.assert_allclose(sheared[1], circle[1])                  # 전단: y 유지
        np.testing.assert_allclose(sheared[0], circle[0] + circle[1])      # x += k·y

    def test_power_iteration_within_5_percent_of_eig(self):
        A = np.array([[4.0, 1.0], [1.0, 3.0]])
        result = la.power_iteration(A)
        ref = la.compare_with_numpy_eig(A, result)
        self.assertTrue(result["converged"])
        self.assertLess(ref["error_pct"], 5.0)
        self.assertAlmostEqual(result["eigenvalue"], (7 + np.sqrt(5)) / 2, places=6)
        np.testing.assert_allclose(A @ result["eigenvector"],
                                   result["eigenvalue"] * result["eigenvector"], atol=1e-5)

    def test_power_iteration_dominant_negative_eigenvalue(self):
        A = np.diag([-5.0, 2.0, 1.0])
        result = la.power_iteration(A, tol=1e-10)
        self.assertAlmostEqual(result["eigenvalue"], -5.0, places=6)

    def test_svd_compression_k_values(self):
        image = load_grayscale_image()
        self.assertEqual(image.shape, (128, 128))
        errors = [la.svd_compress(image, k)["relative_error"] for k in (10, 50, 100)]
        self.assertTrue(errors[0] > errors[1] > errors[2])                 # k가 클수록 정확
        full = la.svd_compress(image, 128)
        self.assertLess(full["relative_error"], 1e-10)                     # 전체 rank면 원본
        self.assertEqual(la.svd_compress(image, 500)["k"], 128)            # rank보다 큰 k는 제한

    def test_svd_matches_eckart_young_error(self):
        image = load_grayscale_image()
        S = np.linalg.svd(image, compute_uv=False)
        res = la.svd_compress(image, 50)
        expected = np.sqrt(np.sum(S[50:] ** 2)) / np.sqrt(np.sum(S ** 2))
        self.assertAlmostEqual(res["relative_error"], expected, places=10)


class CalculusTest(unittest.TestCase):
    """2. 미적분: 수치 미분과 Gradient."""

    def test_derivative_of_x_squared_at_3(self):
        self.assertLess(abs(calc.numerical_derivative(lambda x: x ** 2, 3.0) - 6.0), 1e-4)

    def test_numerical_gradient_matches_analytic(self):
        point = np.array([1.5, -2.0])
        np.testing.assert_allclose(calc.numerical_gradient(opt.quadratic, point),
                                   opt.quadratic_grad(point), atol=1e-8)
        np.testing.assert_allclose(calc.numerical_gradient(opt.rosenbrock, point),
                                   opt.rosenbrock_grad(point), rtol=1e-6)

    def test_gradient_perpendicular_to_contour(self):
        for f in (opt.quadratic, opt.elliptic):
            res = calc.gradient_contour_orthogonality(f, level=4.0, n_points=64)
            self.assertLess(res["max_abs_cos"], 1e-6)

    def test_numerical_hessian(self):
        np.testing.assert_allclose(calc.numerical_hessian(opt.elliptic, [1.0, 2.0]),
                                   np.diag([2.0, 20.0]), atol=1e-4)


class BackpropTest(unittest.TestCase):
    """3. 역전파: 손계산 값과 소수점 4자리 일치."""

    # 노트북의 손계산 결과(소수점 4자리 반올림)
    HAND = {
        "z1": [0.1, 0.3], "a1": [0.5250, 0.5744], "z2": 0.6072, "y_pred": 0.6473,
        "dL_dy_pred": -1.5449, "dL_dz2": -0.3527, "dL_dW2": [-0.1852, -0.2026],
        "dL_da1": [-0.1764, -0.2116], "dL_dz1": [-0.0440, -0.0517],
        "dL_dW1": [[-0.0440, 0.0], [-0.0517, 0.0]],
    }

    def setUp(self):
        self.net, self.x, self.y = example_network()
        self.cache = self.net.forward(self.x, self.y)
        self.grads = self.net.backward(self.cache, self.y)

    def test_forward_matches_hand_calculation(self):
        for key in ("z1", "a1", "z2", "y_pred"):
            np.testing.assert_array_equal(np.round(self.cache[key], 4), self.HAND[key])

    def test_backward_matches_hand_calculation(self):
        for key in ("dL_dy_pred", "dL_dz2", "dL_dW2", "dL_da1", "dL_dz1", "dL_dW1"):
            np.testing.assert_array_equal(np.round(self.grads[key], 4) + 0.0, self.HAND[key])

    def test_shapes(self):
        self.assertEqual(self.cache["z1"].shape, (2,))
        self.assertEqual(self.grads["dL_dW1"].shape, self.net.W1.shape)
        self.assertEqual(self.grads["dL_dW2"].shape, self.net.W2.shape)
        self.assertEqual(np.shape(self.cache["z2"]), ())

    def test_backward_matches_numerical_gradient(self):
        num_W1 = calc.numerical_gradient(lambda W: self.net.loss_with(self.x, self.y, W1=W), self.net.W1)
        num_b1 = calc.numerical_gradient(lambda b: self.net.loss_with(self.x, self.y, b1=b), self.net.b1)
        num_W2 = calc.numerical_gradient(lambda W: self.net.loss_with(self.x, self.y, W2=W), self.net.W2)
        np.testing.assert_allclose(num_W1, self.grads["dL_dW1"], atol=1e-9)
        np.testing.assert_allclose(num_b1, self.grads["dL_db1"], atol=1e-9)
        np.testing.assert_allclose(num_W2, self.grads["dL_dW2"], atol=1e-9)

    def test_random_network_gradient_check(self):
        rng = np.random.default_rng(42)
        net = TwoLayerNet(rng.normal(size=(2, 2)), rng.normal(size=2), rng.normal(size=2), 0.3)
        x = rng.normal(size=2)
        for y in (0.0, 1.0):
            grads = net.backward(net.forward(x, y), y)
            num = calc.numerical_gradient(lambda W: net.loss_with(x, y, W1=W), net.W1)
            np.testing.assert_allclose(num, grads["dL_dW1"], atol=1e-8)

    def test_sgd_step_reduces_loss(self):
        before = self.cache["loss"]
        self.net.sgd_step(self.grads, lr=0.5)
        self.assertLess(self.net.forward(self.x, self.y)["loss"], before)


class OptimizerTest(unittest.TestCase):
    """4. 최적화와 보너스(Adam, Newton)."""

    x0 = np.array([5.0, 5.0])

    def test_vanilla_gd_reaches_origin(self):
        path = opt.optimize(opt.VanillaGD(0.1), opt.quadratic_grad, self.x0, 100)
        self.assertEqual(len(path), 101)
        self.assertLess(np.linalg.norm(path[-1]), 0.1)

    def test_learning_rate_stability_boundary(self):
        def final(lr, grad=opt.quadratic_grad, n=100):
            return np.linalg.norm(opt.optimize(opt.VanillaGD(lr), grad, self.x0, n)[-1])
        self.assertLess(final(0.5), 1e-12)                       # 1 − 2·0.5 = 0 → 한 번에 도달
        self.assertAlmostEqual(final(1.0), np.linalg.norm(self.x0))  # |1 − 2| = 1 → 진동
        self.assertGreater(final(1.1), 1e6)                      # |1 − 2.2| > 1 → 발산
        self.assertGreater(final(0.5, opt.elliptic_grad, 20), 1e6)   # 타원: |1 − 20·0.5| = 9

    def test_momentum_reaches_origin_and_helps_on_ellipse(self):
        path = opt.optimize(opt.Momentum(0.1, 0.9), opt.quadratic_grad, self.x0, 100)
        self.assertLess(np.linalg.norm(path[-1]), 0.1)
        gd = opt.optimize(opt.VanillaGD(0.01), opt.elliptic_grad, self.x0, 100)
        mom = opt.optimize(opt.Momentum(0.01, 0.9), opt.elliptic_grad, self.x0, 100)
        self.assertLess(np.linalg.norm(mom[-1]), np.linalg.norm(gd[-1]) / 10)

    def test_momentum_first_step_equals_gd(self):
        gd = opt.VanillaGD(0.1).step(self.x0, opt.quadratic_grad(self.x0))
        mom = opt.Momentum(0.1, 0.9).step(self.x0, opt.quadratic_grad(self.x0))
        np.testing.assert_allclose(gd, mom)

    def test_adam_first_step_size_is_lr_per_coordinate(self):
        step = opt.Adam(0.1).step(self.x0, opt.elliptic_grad(self.x0))
        np.testing.assert_allclose(self.x0 - step, [0.1, 0.1], atol=1e-6)

    def test_adam_converges_on_ellipse_where_gd_oscillates(self):
        adam = opt.optimize(opt.Adam(0.1), opt.elliptic_grad, self.x0, 300)
        gd = opt.optimize(opt.VanillaGD(0.1), opt.elliptic_grad, self.x0, 300)
        self.assertLess(np.linalg.norm(adam[-1]), 1e-3)
        self.assertGreater(abs(gd[-1][1]), 4.9)

    def test_newton_one_step_on_quadratic(self):
        path = opt.optimize(opt.NewtonMethod(f=opt.elliptic), opt.elliptic_grad, self.x0, 1)
        np.testing.assert_allclose(path[-1], [0.0, 0.0], atol=1e-5)

    def test_newton_solves_rosenbrock(self):
        path = opt.optimize(opt.NewtonMethod(f=opt.rosenbrock), opt.rosenbrock_grad, [-1.5, 2.0], 50, stop_tol=1e-8)
        np.testing.assert_allclose(path[-1], [1.0, 1.0], atol=1e-6)
        self.assertLess(len(path), 20)


class ProbabilityTest(unittest.TestCase):
    """5. 확률/통계와 보너스(정보 이론)."""

    def test_normal_pdf_integrates_to_one_and_peak(self):
        x = np.linspace(-10, 12, 20001)
        for mu, var in ((0, 1), (2, 0.5)):
            pdf = prob.normal_pdf(x, mu, var)
            self.assertAlmostEqual(float(np.sum(pdf) * (x[1] - x[0])), 1.0, places=6)
            self.assertAlmostEqual(float(prob.normal_pdf(mu, mu, var)), 1 / np.sqrt(2 * np.pi * var))

    def test_bernoulli_pmf(self):
        np.testing.assert_allclose(prob.bernoulli_pmf([0, 1], 0.3), [0.7, 0.3])
        np.testing.assert_allclose(prob.bernoulli_pmf([0, 1], 0.7), [0.3, 0.7])
        with self.assertRaises(ValueError):
            prob.bernoulli_pmf([2], 0.5)

    def test_softmax_sums_to_one(self):
        np.random.seed(42)
        for z in (np.random.randn(10), np.array([1000.0, 1001.0, 1002.0]), np.random.randn(4, 6) * 50):
            s = prob.softmax(z)
            self.assertTrue(np.all(np.isfinite(s)))
            np.testing.assert_allclose(s.sum(axis=-1), 1.0, atol=1e-6)

    def test_mse_and_gaussian_nll_have_same_minimizer(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=40)
        y = 2 * x + rng.normal(scale=0.3, size=40)
        ws = np.linspace(0, 4, 4001)
        w_mse = ws[np.argmin([prob.mse(y, w * x) for w in ws])]
        w_nll = ws[np.argmin([prob.gaussian_nll(y, w * x, 0.09) for w in ws])]
        self.assertEqual(w_mse, w_nll)
        # NLL = n/(2σ²)·MSE + 상수 관계를 직접 확인한다.
        n, var = len(x), 0.09
        nll = prob.gaussian_nll(y, 1.7 * x, var)
        self.assertAlmostEqual(nll, n / (2 * var) * prob.mse(y, 1.7 * x) + n / 2 * np.log(2 * np.pi * var))

    def test_bce_is_bernoulli_nll(self):
        y = np.array([1, 0, 1, 1])
        p = np.array([0.9, 0.2, 0.6, 0.4])
        likelihood = np.prod(prob.bernoulli_pmf(y, p))
        self.assertAlmostEqual(prob.bernoulli_nll(y, p), -np.log(likelihood))

    def test_categorical_cross_entropy(self):
        logits = np.array([[2.0, 1.0, 0.1]])
        onehot = np.array([[1, 0, 0]])
        self.assertAlmostEqual(prob.categorical_cross_entropy(onehot, logits),
                               -np.log(prob.softmax(logits)[0, 0]))

    def test_information_identities(self):
        p, q = np.array([0.7, 0.2, 0.1]), np.array([0.4, 0.4, 0.2])
        self.assertAlmostEqual(info.cross_entropy(p, q), info.entropy(p) + info.kl_divergence(p, q))
        self.assertGreater(info.kl_divergence(p, q), 0)
        self.assertAlmostEqual(info.kl_divergence(p, p), 0.0)
        self.assertNotAlmostEqual(info.kl_divergence(p, q), info.kl_divergence(q, p))
        self.assertAlmostEqual(info.entropy([0.25] * 4), np.log(4))
        self.assertAlmostEqual(info.entropy([1.0, 0.0]), 0.0)
        self.assertEqual(info.cross_entropy([0.5, 0.5], [1.0, 0.0]), float("inf"))


if __name__ == "__main__":
    unittest.main()
