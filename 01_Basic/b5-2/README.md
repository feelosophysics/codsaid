# Mini Git

커밋의 **메타데이터**를 메모리에 보관하는 학습용 명령줄 프로그램입니다. 커밋 그래프, 브랜치, 역색인, BFS/DFS, 위상 정렬, 직접 구현한 정렬을 작은 코드로 살펴볼 수 있습니다. 선택 과제인 병합, 줄 단위 파일 비교, 정렬 시간 비교도 포함합니다.

처음 배우는 중이라면 **[실습 중심 학습 가이드](study/study_guide.md)**를 먼저 읽으세요. 명령을 실행한 다음 실제 코드와 저장소 상태를 연결해 설명합니다.

## 실행

Python 3.10 이상이 필요하며 추가 패키지는 없습니다. 이 README가 있는 폴더에서 실행합니다.

```text
python -m minigit
```

Windows에서 `python` 명령이 Microsoft Store 별칭으로 연결되어 실행되지 않으면 설치된 Python 실행 파일 또는 `py -3.12 -m minigit`을 사용하세요. `mini-git>` 프롬프트에서 명령을 입력하고 `EXIT` 또는 `QUIT`으로 종료합니다. 종료하면 저장소의 커밋도 사라집니다.

## 명령

| 명령 | 역할 |
| --- | --- |
| `INIT <user_name>` | 저장소를 새로 초기화하고 `main`과 현재 작성자를 설정 |
| `USER <user_name>` | 이후 커밋의 작성자를 변경하는 학습용 추가 명령 |
| `COMMIT <message>` | 현재 브랜치 끝을 부모로 하는 커밋 생성 |
| `BRANCH <branch_name>` | 현재 커밋을 가리키는 브랜치 생성 |
| `SWITCH <branch_name>` | 현재 브랜치 변경 |
| `LOG` | 전체 커밋을 부모가 자식보다 먼저 나오도록 출력 |
| `LOG --sort-by=date`, `LOG --sort-by=author` | 시간 또는 작성자로 정렬 |
| `PATH <hash1> <hash2>` | 부모 연결을 양방향으로 본 최단 경로; 없으면 `No path` |
| `ANCESTORS <hash>` | 해당 커밋의 모든 조상 |
| `SEARCH <keyword>` | 메시지에서 단어 또는 연속 구절 검색 |
| `SEARCH --author=<name>` | 작성자 이름 검색 |
| `MERGE <branch_name>` | 현재 끝과 대상 끝을 부모로 하는 병합 커밋 생성 |
| `DIFF <file1> <file2>` | UTF-8 파일 두 개를 줄 단위로 비교 |
| `BENCHMARK` | 직접 구현한 머지 정렬과 퀵 정렬의 실행 시간 비교 |
| `STATUS`, `HELP` | 현재 상태, 명령 도움말 |

명령 이름은 대소문자를 구분하지 않습니다. **공백이 있는 인자는 따옴표로 하나로 묶습니다.** 예를 들어 `INIT "Alice Lee"`, `COMMIT "Add login feature"`, `SEARCH "login feature"`, `SEARCH --author="Alice Lee"`입니다. `DIFF "C:\my files\old.txt" "C:\my files\new.txt"`처럼 Windows 경로도 사용할 수 있습니다. 따옴표가 닫히지 않거나 인자가 더 있으면 입력 오류를 출력합니다.

검색은 `split()`으로 나눈 **완전한 단어**를 소문자로 비교합니다. `SEARCH login`은 `login`을 찾지만 `login,`은 다른 단어입니다. 공백 검색어는 연속된 단어를 뜻하므로 `SEARCH "login feature"`는 `login new feature`를 찾지 않습니다. 작성자 검색은 이름 전체를 대소문자 구분 없이 비교합니다.

## 따라 해보기

```text
mini-git> INIT "Alice Lee"
mini-git> COMMIT "Start project"
mini-git> BRANCH feature
mini-git> SWITCH feature
mini-git> USER "Bob Smith"
mini-git> COMMIT "Add login feature"
mini-git> SEARCH "login feature"
mini-git> SEARCH --author="Bob Smith"
mini-git> SWITCH main
mini-git> COMMIT "Update main"
mini-git> MERGE feature
mini-git> LOG
```

각 `COMMIT`과 `MERGE`가 출력한 ID를 `PATH <ID1> <ID2>`와 `ANCESTORS <ID>`에 넣어 보세요. ID와 시간은 실행할 때마다 달라집니다. `INIT`을 다시 실행하면 커밋과 역색인은 비워지지만, 한 프로그램 실행 안에서 ID 번호는 재사용되지 않습니다.

## 코드와 알고리즘

| 위치 | 핵심 내용 |
| --- | --- |
| `minigit/__main__.py` | 입력 파싱, 명령 검증, 결과 출력 |
| `minigit/models.py` | `Commit`, `Repository`, 브랜치·HEAD·커밋 생성 |
| `minigit/index.py` | 단어·작성자 역색인과 연속 구절 후보 검색 |
| `minigit/graph.py` | 부모 우선 위상 정렬, BFS 최단 경로, DFS 조상 |
| `minigit/sorting.py` | 머지 정렬, 퀵 정렬, 시간 비교 |
| `minigit/diff.py` | LCS 표를 이용한 줄 단위 차이 |
| `minigit/constants.py` | 공통 설정과 화면 문구 |

- 커밋은 0개 이상의 부모 ID를 가집니다. 생성 시 이미 있는 커밋만 부모가 되므로 DAG를 이룹니다. `dict[ID] = Commit`으로 ID 조회는 평균 O(1)입니다.
- 커밋 ID는 SHA-1 지문의 앞 6자리와 증가 번호를 합칩니다(예: `a1b2c3-4`). 번호가 한 세션에서 반복되지 않아 전체 ID가 유일합니다. 실제 Git 객체 ID와는 다릅니다.
- `LOG`는 Kahn 위상 정렬로 부모를 먼저 출력합니다(O(V+E)). `PATH`는 무방향 인접 목록에서 BFS를 수행하고, 이웃 ID 뒤에 `->`를 붙인 값을 직접 구현한 정렬로 비교해 동률 경로 문자열의 사전순을 맞춥니다. ID 내부에는 `->`를 허용하지 않습니다. `ANCESTORS`는 부모 방향 DFS입니다.
- 검색은 단어·작성자에서 커밋 ID 집합으로 가는 역색인을 사용합니다. 연속 구절은 첫 단어로 후보를 좁힌 뒤 그 후보의 메시지만 확인합니다. 검색 결과 후보는 머지 정렬로 일정한 순서로 출력합니다.
- `LOG --sort-by`는 안정적인 머지 정렬을 사용합니다(평균·최악 O(n log n)). 이 프로젝트의 퀵 정렬도 순서를 보존하는 세 그룹 분할 방식이므로 **안정 정렬**입니다(평균 O(n log n), 최악 O(n²)). 제자리 퀵 정렬과는 구현 및 공간 사용이 다릅니다.
- `DIFF`는 두 파일의 공통 줄 순서를 찾는 LCS 동적 계획법을 사용합니다(시간·공간 O(mn)). `BENCHMARK` 수치는 컴퓨터와 실행 시점에 따라 달라집니다.

이 프로그램은 파일 상태 추적, 네트워크, 저장을 구현하지 않습니다. 여기의 `LOG`는 미션의 **부모 우선** 규칙을 따르며 실제 `git log`의 기본 표시 순서와 같다고 가정하면 안 됩니다. `MERGE`도 파일 내용을 합치지 않고 부모가 두 개인 커밋만 만듭니다. Python 표준 정렬 API인 `sorted()`와 `list.sort()`는 사용하지 않습니다.

## 입력과 출력의 제한

`shlex`는 따옴표 안의 공백과 Windows 경로를 읽는 표준 토큰 분리 도구로 유지합니다. 입력을 셸 명령으로 실행하지 않습니다. 인자 하나를 받는 저장소 명령 여섯 개는 `execute()`의 작은 명령 표와 공통 인자 검사로 연결하며, 다른 문법의 명령은 개별 처리 함수를 사용합니다.

REPL은 결과를 화면에 출력할 때 ESC 등 C0/C1 제어문자를 `\x1b` 같은 보이는 표기로 바꿉니다. 줄바꿈과 탭은 유지하고 저장된 커밋 메시지는 바꾸지 않습니다. `execute()`와 `diff_files()`는 원래 결과 문자열을 반환하므로 다른 프로그램이 직접 사용한다면 출력 경계에서 같은 처리가 필요합니다.

DIFF의 학습용 상한은 **파일 하나당 1,048,576바이트(1 MiB)**, **LCS 표 1,000,000칸**입니다. 표 크기는 `(첫 파일 줄 수 + 1) × (둘째 파일 줄 수 + 1)`로 계산합니다. 파일은 상한보다 한 바이트만 더 읽어 초과 여부를 판단하고, 표는 할당 전에 검사합니다. 경로·UTF-8 오류와 상한 초과는 이유를 안내하고 REPL을 계속 실행합니다. 알고리즘은 여전히 O(mn)이며, 모든 파일 IO의 대기 시간을 제한하는 기능은 없습니다.

## 테스트

```text
python -m unittest discover -s tests -v
```

초기화·브랜치·병합, 부모 우선 로그, 동률 최단 경로, 조상, 검색·정렬, 입력 오류, 파일 비교, 작은 벤치마크를 확인합니다.

추가 회귀 테스트는 잘못된 명령 후 상태 보존, NUL 경로 이후 REPL 계속 실행, 제어문자의 화면 출력, DIFF 상한 경계와 초과, 그리고 4노드 DAG 64개에서 모든 출발·도착점 조합의 최단 경로를 독립적으로 열거한 결과와 대조합니다.
