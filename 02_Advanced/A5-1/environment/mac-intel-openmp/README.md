# Intel Mac 시연용 OpenMP 런타임

`libomp.dylib`는 conda-forge의 `llvm-openmp 23.1.3 h8c1e6b9_0` 패키지에서 그대로 추출했다. Intel x86_64, macOS 11 이상용이다. Conda·Homebrew 설치 없이 `tools/mac_demo.py`가 이번 실행의 `DYLD_LIBRARY_PATH`에 이 폴더를 추가한다.

- 다운로드 URL과 패키지·추출 파일 SHA-256: `provenance.json`
- 재배포 라이선스 원문: `LICENSE.TXT`
- 아카이브: ZIP 형식의 `.conda` 안 `pkg-*.tar.zst`의 `lib/libomp.dylib`
- 라이선스: 같은 아카이브 안 `info-*.tar.zst`의 `info/licenses/openmp/LICENSE.TXT`

원본 패키지 해시를 확인한 뒤 추출했으며, Mach-O의 Intel 아키텍처, 최소 macOS 11.0, 외부 참조 `/usr/lib/libSystem.B.dylib`, 정의된 외부 심벌 `___kmpc_dispatch_deinit`를 확인했다. Windows에서 정적으로 검사했으며 실제 Mac 로딩 성공을 주장하는 기록은 아니다. 실행 시에는 SHA-256 검사 후 scikit-learn과 XGBoost의 작은 학습·예측을 별도 프로세스에서 확인한다.

이 파일은 `.venv` 안에 복사하거나 시스템에 설치하지 않는다. `libomp`가 없거나 해시가 다르면 Intel 시연을 중단한다. 사용자 원본·시스템 폴더·scikit-learn의 라이브러리를 덮어쓰지 않는다.
