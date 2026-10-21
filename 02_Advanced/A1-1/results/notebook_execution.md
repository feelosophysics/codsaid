# 분석 노트북 실행 기록

`tools/execute_notebook.py`가 실제 전체 실행에 성공한 뒤 생성한 기록이다. 실행 안내를 적은 문서와 구분하며, 기록 이후 파일 변경 시 다시 실행해야 한다.

- 재현 명령: A1-1 폴더에서 `uv run python tools/execute_notebook.py`
- 실행 노트북: [analysis_report.ipynb](../notebooks/analysis_report.ipynb)
- 시작: 2026-10-22 00:56:24 KST (UTC+09:00)
- 완료: 2026-10-22 00:56:30 KST (UTC+09:00)
- 소요 시간: 5.33초
- 실행 환경: Windows, Python 3.12.13
- 코드 셀: 32개, 실행 완료: 32개, 오류 출력: 0개
- PNG 출력: 8개
- 소스·입력·환경 파일의 실행 전후 해시: 모두 일치

## 라이브러리

| 라이브러리 | 실제 설치 버전 |
| --- | --- |
| numpy | 2.5.3 |
| pandas | 3.0.6 |
| matplotlib | 3.11.2 |
| seaborn | 0.13.2 |
| plotly | 6.9.0 |
| nbclient | 0.11.0 |
| nbformat | 5.11.1 |
| ipykernel | 7.4.0 |

## 코드 셀 실행 결과

| 코드 셀 | execution_count | 출력 수 | 오류 수 |
| ---: | ---: | ---: | ---: |
| 1 | 1 | 0 | 0 |
| 2 | 2 | 1 | 0 |
| 3 | 3 | 2 | 0 |
| 4 | 4 | 5 | 0 |
| 5 | 5 | 3 | 0 |
| 6 | 6 | 3 | 0 |
| 7 | 7 | 3 | 0 |
| 8 | 8 | 3 | 0 |
| 9 | 9 | 2 | 0 |
| 10 | 10 | 2 | 0 |
| 11 | 11 | 1 | 0 |
| 12 | 12 | 3 | 0 |
| 13 | 13 | 2 | 0 |
| 14 | 14 | 1 | 0 |
| 15 | 15 | 3 | 0 |
| 16 | 16 | 2 | 0 |
| 17 | 17 | 2 | 0 |
| 18 | 18 | 1 | 0 |
| 19 | 19 | 2 | 0 |
| 20 | 20 | 3 | 0 |
| 21 | 21 | 1 | 0 |
| 22 | 22 | 1 | 0 |
| 23 | 23 | 1 | 0 |
| 24 | 24 | 1 | 0 |
| 25 | 25 | 1 | 0 |
| 26 | 26 | 1 | 0 |
| 27 | 27 | 1 | 0 |
| 28 | 28 | 1 | 0 |
| 29 | 29 | 2 | 0 |
| 30 | 30 | 2 | 0 |
| 31 | 31 | 4 | 0 |
| 32 | 32 | 2 | 0 |

## 실행 대상 SHA-256

UTF-8 텍스트는 CRLF를 LF로 정규화하고 `.npy`는 원래 바이트를 해시한다. 소스·입력·환경 파일은 실행 전후에 대조했으며, 노트북 해시는 실행 결과를 저장한 뒤 계산했다. 해시는 기록과 파일의 대응을 확인하는 수단이며 독립 기관의 실행 인증은 아니다.

| 파일 | SHA-256 |
| --- | --- |
| `data/sample/customers.csv` | `c40b09df6cc8563c32279da3dad78359c908ecef9503db6706fb0c41c056b311` |
| `data/sample/images.npy` | `a46d01d25f598fdd5ab344fd6b5a25c676be492b3baa95b1a510122dd1263e0d` |
| `data/sample/metadata.json` | `5784068841d63e0422634f20aac45f1cf3f600081492aded8cafa424c8905838` |
| `data/sample/products.csv` | `c6244b515c15d5f911bca26425cc5187c01207b15d8426f5b8c5ca8dc37c2189` |
| `data/sample/transactions.csv` | `ede38d02ea9b4281a1adec27ccc3bb41a2ef22724bb99aaf4a27a7c091f8d995` |
| `pyproject.toml` | `3bde2c0a522611781ef4d1758b7d16656d69266e672b31897ad9f678b67ca3db` |
| `src/__init__.py` | `57cd1c69493c6861aaa044240fbd3f173060dedb103a2c76930c19b2c0c20a51` |
| `src/bonus.py` | `c5885c7a9de0db8d989eb094ea0e58341ffa736ad7feafe3c8d46a486116e559` |
| `src/pipeline.py` | `ddf7f72752b1b544a6ccd65b5c714eb291de4738b69c48554475c36c2bd9394a` |
| `src/report.py` | `9dd34a26353103801d5e0e4523bbb35a1b1a66065077aa207b1dceceeaf1eb04` |
| `src/run_analysis.py` | `9ee343dd3b2bb34feb527b92c8f79445849c7f4d6f5b96f3f076db82c12feab2` |
| `src/sample_data.py` | `833e500a8357bd6c161c9747adb24aa048d98f0cfaf453801287f693fdf5cec0` |
| `tools/execute_notebook.py` | `76cd01596ad045ab90c40b2edddc5ed00d33cd7a629024e5201544cc7bae830d` |
| `uv.lock` | `f69b2cbd5ca635e27927948e890a9ede9b9d71fece16f147bf136f86fc159b86` |
| `notebooks/analysis_report.ipynb` | `e72eb417e066bfeec8feab5f136ca7192d44bea6e4c3680a9f50060562d00f10` |

## 확인 범위

노트북의 모든 코드 셀을 순서대로 실행했고, 필수 분석·시각화·보너스 결과 생성까지 완료했다. 이 기록은 해당 입력·환경에서의 실행 성공 근거다. 통계 해석의 외부 타당성, 다른 데이터에서의 정확성, 브라우저 조작 성공을 증명하지 않는다.
