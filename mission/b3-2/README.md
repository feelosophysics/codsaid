# 🔧 Mini Git — CLI 기반 버전 관리 시스템

Git의 핵심 자료구조(DAG, 해시맵, 역색인)와 알고리즘(BFS, DFS, 위상 정렬, 정렬)을
직접 구현하여 만든 교육용 Mini Git CLI 프로그램입니다.

## 📋 목차

- [실행 방법](#-실행-방법)
- [명령어 목록](#-명령어-목록)
- [프로젝트 구조](#-프로젝트-구조)
- [구현된 알고리즘](#-구현된-알고리즘)
- [보너스 과제](#-보너스-과제)
- [사용 예시](#-사용-예시)

## 🚀 실행 방법

```bash
python main.py
```

> **요구 환경**: Python 3.10 이상  
> **외부 라이브러리**: 없음 (표준 라이브러리만 사용)

## 📝 명령어 목록

### 기본 명령어

| 명령어 | 설명 | 사용법 |
|--------|------|--------|
| `INIT` | 저장소 초기화 | `INIT <user_name>` |
| `COMMIT` | 새 커밋 생성 | `COMMIT <message>` |
| `BRANCH` | 새 브랜치 생성 | `BRANCH <branch_name>` |
| `SWITCH` | 브랜치 전환 | `SWITCH <branch_name>` |
| `LOG` | 커밋 로그 출력 (위상 정렬) | `LOG` |
| `LOG --sort-by` | 정렬 기준 지정 | `LOG --sort-by=date\|author` |
| `PATH` | 두 커밋 간 최단 경로 | `PATH <hash1> <hash2>` |
| `ANCESTORS` | 특정 커밋의 모든 조상 | `ANCESTORS <commit_hash>` |
| `SEARCH` | 키워드로 커밋 검색 | `SEARCH <keyword>` |
| `SEARCH --author` | 작성자로 커밋 검색 | `SEARCH --author=<name>` |
| `STATUS` | 저장소 상태 확인 | `STATUS` |
| `HELP` | 도움말 출력 | `HELP` |
| `EXIT` / `QUIT` | 프로그램 종료 | `EXIT` |

### 보너스 명령어

| 명령어 | 설명 | 사용법 |
|--------|------|--------|
| `MERGE` | 브랜치 병합 (머지 커밋 생성) | `MERGE <branch_name>` |
| `DIFF` | 두 파일 비교 (LCS 기반) | `DIFF <file1> <file2>` |
| `BENCHMARK` | 정렬 알고리즘 성능 비교 | `BENCHMARK` |

### CLI 규칙

- 명령어는 **대소문자를 구분하지 않습니다** (예: `INIT`, `init`, `Init` 모두 가능)
- 공백이 포함된 인자는 **따옴표로 감쌉니다** (예: `COMMIT "Add login feature"`)
- 잘못된 입력 시 표준 에러 메시지를 출력합니다

## 📁 프로젝트 구조

```
b3-2/
├── main.py        # CLI 진입점 (REPL 루프, 명령어 파싱/라우팅)
├── models.py      # 핵심 데이터 모델 (Commit, Repository 클래스)
├── graph.py       # 그래프 알고리즘 (위상 정렬, BFS, DFS)
├── sorting.py     # 정렬 알고리즘 (Merge Sort, Quick Sort)
├── index.py       # 역색인 (키워드/작성자 기반 검색)
├── diff.py        # Diff 기능 (LCS 기반 파일 비교)
├── README.md      # 이 문서
└── study_guide.md # 초상세 학습 가이드
```

## 🧠 구현된 알고리즘

### 자료구조

| 자료구조 | 용도 | 위치 |
|----------|------|------|
| **DAG (방향성 비순환 그래프)** | 커밋 히스토리 구조 | `models.py` |
| **해시맵 (dict)** | O(1) 커밋 조회 | `models.py` |
| **역색인 (Inverted Index)** | O(1) 키워드/작성자 검색 | `index.py` |

### 알고리즘

| 알고리즘 | 용도 | 시간복잡도 | 위치 |
|----------|------|-----------|------|
| **SHA-1 해싱** | 커밋 고유 식별자 생성 | O(1) | `models.py` |
| **Kahn's Algorithm** | LOG 위상 정렬 | O(V+E) | `graph.py` |
| **BFS (너비 우선 탐색)** | PATH 최단 경로 | O(V+E) | `graph.py` |
| **DFS (깊이 우선 탐색)** | ANCESTORS 조상 탐색 | O(V+E) | `graph.py` |
| **Merge Sort (머지 정렬)** | LOG --sort-by 안정 정렬 | O(n log n) | `sorting.py` |
| **Quick Sort (퀵 정렬)** | 벤치마크용 불안정 정렬 | O(n log n) avg | `sorting.py` |
| **LCS (최장 공통 부분수열)** | DIFF 파일 비교 | O(m×n) | `diff.py` |

## 🌟 보너스 과제

### 5.1 Diff (파일 비교)
- LCS(Longest Common Subsequence) 알고리즘을 직접 구현
- 동적 프로그래밍(DP) 기반 O(m×n) 시간복잡도
- 추가(`+`), 삭제(`-`), 공통(` `) 줄을 구분하여 출력

### 5.2 Merge (브랜치 병합)
- 부모가 2개인 머지 커밋을 생성
- DAG에서 "두 경로가 만나는 지점" 구현

### 5.3 정렬 알고리즘 성능 비교
- Merge Sort vs Quick Sort 벤치마크
- 다양한 입력 크기(10~5000)에서 실행 시간 측정
- 안정 정렬 vs 불안정 정렬 비교

## 💡 사용 예시

```
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice

mini-git> commit "Initial commit"
[main a1b2c3] Initial commit

mini-git> branch feature
Created branch: feature

mini-git> switch feature
Switched to branch: feature

mini-git> commit "Add login feature"
[feature d4e5f6] Add login feature

mini-git> switch main
Switched to branch: main

mini-git> commit "Add payment feature"
[main g7h8i9] Add payment feature

mini-git> log
commit a1b2c3 (Alice, 2026-05-24 07:30:00)
  Initial commit

commit g7h8i9 (Alice, 2026-05-24 07:30:02) [main] (HEAD)
  Add payment feature

commit d4e5f6 (Alice, 2026-05-24 07:30:01) [feature]
  Add login feature

mini-git> search "login"
Found 1 commit(s) for keyword 'login':

  - d4e5f6: Add login feature

mini-git> merge feature
Merged 'feature' into 'main'.
[main x1y2z3] Merge branch 'feature' into main

mini-git> exit
Goodbye!
```

## 🔑 제약 사항

- `sorted()`, `list.sort()` 등 Python 표준 정렬 API **사용 금지** → 직접 구현
- 그래프 전용 라이브러리 **사용 금지** → 인접 리스트 직접 구축
- 파일 내용 추적 **미구현** (커밋 메타데이터 중심)
- 네트워크 통신 **미구현**
- 데이터 영속성 **미구현** (메모리 상 동작)
