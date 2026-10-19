A5-1 Mac 시연: 기존 잠금 파일로 환경을 준비합니다.
Using CPython 3.12.13 interpreter at: /usr/local/opt/python@3.12/bin/python3.12
Creating virtual environment at: .venv
Resolved 63 packages in 10ms
Prepared 57 packages in 1.40s
Installed 57 packages in 253ms
 + appnope==1.0.0
 + asttokens==3.0.2
 + attrs==26.1.0
 + cloudpickle==3.1.2
 + comm==0.2.3
 + contourpy==1.4.0
 + cycler==0.12.1
 + debugpy==1.8.22
 + executing==2.3.0
 + fastjsonschema==2.22.2
 + fonttools==4.66.1
 + imbalanced-learn==0.14.2
 + ipykernel==7.4.0
 + ipython==9.17.1
 + ipython-pygments-lexers==1.1.1
 + jedi==0.20.1
 + joblib==1.6.0
 + jsonschema==4.26.0
 + jsonschema-specifications==2025.9.1
 + jupyter-client==8.10.0
 + jupyter-core==5.9.1
 + kiwisolver==1.5.1
 + matplotlib==3.11.2
 + matplotlib-inline==0.2.2
 + narwhals==2.27.1
 + nbclient==0.11.0
 + nbformat==5.11.1
 + nest-asyncio2==1.7.4
 + numpy==2.5.4
 + packaging==26.3
 + pandas==3.0.6
 + parso==0.8.7
 + pexpect==4.9.0
 + pillow==12.3.0
 + platformdirs==4.13.0
 + prompt-toolkit==3.0.53
 + psutil==7.2.2
 + ptyprocess==0.7.0
 + pure-eval==0.2.4
 + pygments==2.21.0
 + pyparsing==3.3.3
 + python-dateutil==2.9.0.post0
 + pyzmq==27.2.0
 + referencing==0.37.0
 + rpds-py==2026.9.1
 + scikit-learn==1.9.1
 + scipy==1.18.1
 + seaborn==0.13.2
 + six==1.17.0
 + sklearn-compat==0.1.6
 + stack-data==0.6.3
 + threadpoolctl==3.7.0
 + tornado==6.5.10
 + traitlets==5.16.1
 + typing-extensions==4.16.0
 + wcwidth==0.9.2
 + xgboost==3.4.1
Python: /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/bin/python
CPU: x86_64
libomp 검사: /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/sklearn/.dylibs/libomp.dylib
이 후보는 불러오지 못했습니다.
XGBoost 로딩에 실패했습니다. 아래 오류를 전달해 주세요.
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/xgboost/__init__.py", line 6, in <module>
    from . import (
  File "/Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/xgboost/collective.py", line 14, in <module>
    from .core import _LIB, _check_call, build_info, c_str, make_jcargs, py_str
  File "/Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/xgboost/core.py", line 42, in <module>
    from ._c_api import (
  File "/Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/xgboost/_c_api.py", line 184, in <module>
    _LIB = _load_lib()
           ^^^^^^^^^^^
  File "/Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/xgboost/_c_api.py", line 148, in _load_lib
    raise XGBoostError(f"""
xgboost._c_api.XGBoostError: 
XGBoost Library (libxgboost.dylib) could not be loaded.
Likely causes:
  * OpenMP runtime is not installed
    - vcomp140.dll or libgomp-1.dll for Windows
    - libomp.dylib for Mac OSX
    - libgomp.so for Linux and other UNIX-like OSes
    Mac OSX users: Run `brew install libomp` to install OpenMP runtime.

  * You are running 32-bit Python on a 64-bit OS

Error message(s): ['dlopen(/Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/xgboost/lib/libxgboost.dylib, 0x0006): Symbol not found: ___kmpc_dispatch_deinit\n  Referenced from: <77F13E08-27C4-30BB-B9B6-08064A31C57F> /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/xgboost/lib/libxgboost.dylib\n  Expected in:     <14BC387F-0237-327F-B68C-C42E478D2DCE> /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/lib/python3.12/site-packages/sklearn/.dylibs/libomp.dylib']



실행에 실패했습니다. 위 오류 내용을 확인해 주세요.

Enter를 누르면 창을 닫습니다. 

---

f22losophysics1091@c6r10s6 A5-1 % git pull          
remote: Enumerating objects: 25, done.
remote: Counting objects: 100% (25/25), done.
remote: Compressing objects: 100% (9/9), done.
remote: Total 16 (delta 7), reused 16 (delta 7), pack-reused 0 (from 0)
Unpacking objects: 100% (16/16), 332.08 KiB | 1024.00 KiB/s, done.
From https://github.com/feelosophysics/codsaid
   578247e..20569d9  main       -> origin/main
Updating 578247e..20569d9
Fast-forward
 02_Advanced/A5-1/MAC_DEMO.md                                  |  15 +++--
 02_Advanced/A5-1/README.md                                    |   2 +-
 02_Advanced/A5-1/environment/mac-intel-openmp/LICENSE.TXT     | 361 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 02_Advanced/A5-1/environment/mac-intel-openmp/README.md       |  12 ++++
 02_Advanced/A5-1/environment/mac-intel-openmp/libomp.dylib    | Bin 0 -> 852904 bytes
 02_Advanced/A5-1/environment/mac-intel-openmp/provenance.json |  19 ++++++
 02_Advanced/A5-1/tests/test_mac_demo.py                       |  88 ++++++++++++++++++++++++++
 02_Advanced/A5-1/tools/mac_demo.py                            |  68 +++++++++++++++++---
 8 files changed, 551 insertions(+), 14 deletions(-)
 create mode 100644 02_Advanced/A5-1/environment/mac-intel-openmp/LICENSE.TXT
 create mode 100644 02_Advanced/A5-1/environment/mac-intel-openmp/README.md
 create mode 100644 02_Advanced/A5-1/environment/mac-intel-openmp/libomp.dylib
 create mode 100644 02_Advanced/A5-1/environment/mac-intel-openmp/provenance.json
 create mode 100644 02_Advanced/A5-1/tests/test_mac_demo.py
f22losophysics1091@c6r10s6 A5-1 % bash run_mac_demo.command 
A5-1 Mac 시연: 기존 잠금 파일로 환경을 준비합니다.
Resolved 63 packages in 5ms
Checked 57 packages in 13ms
Python: /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/.venv/bin/python
CPU: x86_64
검증된 Intel Mac libomp 23.1.3 연결: /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/environment/mac-intel-openmp/libomp.dylib
XGBoost + scikit-learn 학습 검사 OK: 3.4.1
시연에 필요한 합성 데이터를 생성합니다.
데이터 생성 완료: finance_data.csv
전체 샘플 수: 10000
연체(1) 비율: 12.01% (불균형 데이터 확인)
분석을 시작합니다. 결과 저장 위치: /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/results/mac-demo
전체 모델 비교에는 시간이 걸립니다. 중단하려면 Ctrl+C를 누르세요.
Matplotlib is building the font cache; this may take a moment.
[   0.1s] 데이터 10,000행, Train 8,000 / Test 2,000
[   3.3s] 회귀 완료
[ 324.7s] 분류 완료, 최종 모델 RF + class_weight
[ 331.2s] 정책·그래프 완료
[ 373.1s] 진단 완료
[ 373.1s] 저장 완료: /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/results/mac-demo
시연 완료. 보고서: /Users/f22losophysics1091/Desktop/codsaid/02_Advanced/A5-1/results/mac-demo/report.md

Enter를 누르면 창을 닫습니다. ^C