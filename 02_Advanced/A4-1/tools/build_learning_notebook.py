"""문자열에서 검색·분류까지의 실습. --execute로 새 커널에서 실행한다."""
import argparse
import json
import os
import sys
import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'notebooks/search_walkthrough.ipynb'


def build():
    import nbformat as nbf
    cells = []

    def md(source):
        cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(source).strip()))

    def code(source):
        cells.append(nbf.v4.new_code_cell(textwrap.dedent(source).strip()))

    md('''
    # 문자열에서 검색 점수까지, 그리고 분류로

    **문서·질의 → 토큰·어휘 → TF·DF·IDF → TF-IDF·정규화 → 코사인·순위**를
    두 문서로 계산한 뒤 같은 모듈을 실제 게시글 검색과 분류에 연결한다.
    Python 변수·반복문·배열에서 출발한다. 먼저 숫자를 예상하고 실행 결과를 읽는다.

    A4-1에서 `uv sync --group dev` 후 `.venv`를 커널로 선택하고 위에서 아래로 실행한다.
    `uv run --group dev python tools/build_learning_notebook.py --execute`로 새 커널 실행도 가능하다.
    실제 데이터 캐시가 없으면 다운로드한다. C 후보 3개 × 5-fold 분류는 수 분 걸릴 수 있다.
    기존 `outputs/`를 읽어 이전 조건과 비교하며 덮어쓰지 않는다.

    [HTML](../study/a4-1.html)은 설정을 바꾸는 계산기·브라우저 시연에,
    이 노트북은 Python의 중간 배열과 학습 경계 확인에 쓴다.
    HTML의 분류 표는 이전 CV 조건의 저장 결과다. 새 CV 수치는 이 노트북에서 확인한다.
    ''')
    code('''
    from pathlib import Path
    import sys
    import json
    import platform
    import numpy as np
    import sklearn
    import matplotlib.pyplot as plt
    from IPython.display import display, Markdown
    from threadpoolctl import threadpool_limits

    root = Path.cwd()
    if root.name == 'notebooks':
        root = root.parent
    assert (root/'src/tfidf.py').is_file(), 'A4-1 또는 notebooks에서 실행하세요.'
    sys.path.insert(0, str(root))
    from src.preprocess import clean, tokenize, normalize, remove_stopwords, preprocess
    from src.tfidf import TfidfVectorizerNP, term_frequency
    from src.search import SearchEngine, cosine_similarity, top_k
    from src.data import Corpus, load_corpus, train_test_indices
    from src.classify import run_classification
    from src.experiments import verify_against_sklearn, verify_cosine, bow_limits, benchmark_index
    thread_limit = threadpool_limits(limits=2)
    np.set_printoptions(precision=6, suppress=True)
    print('Python', platform.python_version(), 'NumPy', np.__version__, 'sklearn', sklearn.__version__)

    def table(headers, rows):
        lines = ['| ' + ' | '.join(map(str, headers)) + ' |',
                 '| ' + ' | '.join(['---'] * len(headers)) + ' |']
        for row in rows:
            lines.append('| ' + ' | '.join(map(str, row)) + ' |')
        display(Markdown('\\n'.join(lines)))
    ''')
    md('''
    ## 1. 입력에서 토큰까지

    문서 d0은 `Space space orbit!`, d1은 `Goalie orbit.`, 질의는 `SPACE orbit unknown`이다.
    d0의 space는 두 번 등장한다. 빈도 TF와 출현 문서 수 DF가 어떻게 다른지 예상해 보자.
    정제 → 토큰화 → 표기 통합 → 불용어 제거는 영어 규칙이다. 한국어 형태소 분석은 지원하지 않는다.
    ''')
    code('''
    documents = ['Space space orbit!', 'Goalie orbit.']
    query = 'SPACE orbit unknown'
    tokens = []
    for i, text in enumerate(documents):
        cleaned = clean(text)
        pieces = tokenize(cleaned)
        normalized = normalize(pieces)
        kept = remove_stopwords(normalized)
        tokens.append(kept)
        print('d', i, ':', repr(text), '→', repr(cleaned), '→', pieces, '→', normalized, '→', kept)
    query_tokens = preprocess(query)
    print('질의:', repr(query), '→', query_tokens)
    ''')
    md('''
    ## 2. 같은 열에 같은 단어 놓기

    어휘는 알파벳순 `[goalie, orbit, space]`. 한 행은 문서, 한 열은 단어다.
    첫 예는 `min_df=1, max_df=1.0`으로 세 단어를 모두 남긴다.
    실제 검색 기본값 `min_df=5, max_df=0.5`와 다르다. 문서 두 개에 5를 쓰면 열이 사라진다.
    `max_df=1.0`은 전체 문서 비율이고 정수 `1`은 한 문서라는 차이도 주의한다.
    ''')
    code('''
    terms = sorted(set(tokens[0] + tokens[1]))
    vocabulary = {}
    for column, term in enumerate(terms):
        vocabulary[term] = column
    counts = np.zeros((len(tokens), len(terms)), dtype=np.float64)
    for row, document_tokens in enumerate(tokens):
        for term in document_tokens:
            counts[row, vocabulary[term]] += 1
    print('단어 → 열 번호:', vocabulary)
    print('빈도 행렬 shape / dtype:', counts.shape, counts.dtype)
    table(['문서'] + terms, [['d0'] + counts[0].tolist(), ['d1'] + counts[1].tolist()])
    ''')
    md('''
    ## 3. TF와 DF를 구별하고 IDF 곱하기

    기본 TF는 원래 빈도다. DF는 `(counts > 0)`을 문서 방향(axis=0)으로 합친다.
    space 빈도 합은 2지만 DF는 1이다. 기본 IDF는 자연로그 `ln((N+1)/(DF+1))+1`.
    orbit은 두 문서 모두에 있어 IDF=1, 나머지는 약 1.405465다.
    분수의 +1은 smoothing, 바깥 +1은 흔한 단어도 가중치 1을 남기는 역할이다.
    ''')
    code('''
    tf = counts.copy()
    presence = counts > 0
    df = presence.sum(axis=0)
    idf = np.log((len(tokens) + 1) / (df + 1)) + 1
    weighted = tf * idf
    print('출현 여부:\\n', presence)
    table(['단어', '총빈도', 'DF', 'IDF'],
          [[term, counts[:, j].sum(), df[j], round(idf[j], 6)] for j, term in enumerate(terms)])
    print('TF × IDF (2,3):\\n', weighted)
    ''')
    md('''
    ## 4. 행마다 L2 길이로 나누기

    `[0,1,2.810930]`의 길이는 `sqrt(1²+2.810930²)`다. 길이로 나누면
    `[0,0.335176,0.942156]` 부근이 된다. 0벡터는 그대로 0으로 둔다.
    라이브러리에는 첫 계산을 맡기지 않고 여기서 계산한 뒤 기존 구현 및 sklearn과 대조한다.
    ''')
    code('''
    lengths = np.sqrt((weighted ** 2).sum(axis=1))
    safe_lengths = np.where(lengths > 0, lengths, 1)
    document_vectors = weighted / safe_lengths[:, None]
    print('길이 shape:', lengths.shape, '→ 나눌 축:', safe_lengths[:, None].shape)
    print('L2 정규화:\\n', document_vectors)
    vec = TfidfVectorizerNP(min_df=1, max_df=1.0)
    module_vectors = vec.fit_transform(tokens)
    assert terms == vec.terms_
    np.testing.assert_allclose(counts, vec.counts(tokens))
    np.testing.assert_allclose(idf, vec.idf_)
    np.testing.assert_allclose(document_vectors, module_vectors)
    from sklearn.feature_extraction.text import TfidfVectorizer
    reference = TfidfVectorizer(analyzer=lambda document: document, dtype=np.float64)
    reference_vectors = reference.fit_transform(tokens).toarray()
    assert terms == list(reference.get_feature_names_out())
    np.testing.assert_allclose(document_vectors, reference_vectors)
    print('손계산 · 기존 모듈 · sklearn: 같은 토큰/어휘/설정에서 일치')
    ''')
    md('''
    ## 5. 질의는 fit 없이 transform → 점수 → 순위

    unknown은 열이 없어 무시한다. 질의로 IDF를 다시 만들면 문서와 좌표계가 달라진다.
    코사인은 같은 열끼리 곱한 합을 두 길이의 곱으로 나눈 값이다.
    L2 정규화된 양수 행에서는 내적과 같고, 값은 정답 확률이 아니다.
    ''')
    code('''
    query_counts = np.zeros(len(terms), dtype=np.float64)
    for term in query_tokens:
        if term in vocabulary:
            query_counts[vocabulary[term]] += 1
    query_weighted = query_counts * idf
    query_length = np.linalg.norm(query_weighted)
    query_vector = query_weighted / query_length if query_length > 0 else query_weighted
    contributions = document_vectors * query_vector
    dots = contributions.sum(axis=1)
    denominator = np.linalg.norm(document_vectors, axis=1) * np.linalg.norm(query_vector)
    scores = np.divide(dots, denominator, out=np.zeros_like(dots), where=denominator > 0)
    order = top_k(scores, 5)
    print('질의 빈도:', query_counts, '→ TF-IDF:', query_vector)
    table(['문서'] + terms + ['코사인'],
          [['d'+str(i)] + contributions[i].round(6).tolist() + [round(scores[i], 6)] for i in range(2)])
    print('양수 점수 순위(문서 위치):', order)
    np.testing.assert_allclose(query_vector, vec.transform([query_tokens])[0])
    np.testing.assert_allclose(scores, cosine_similarity(query_vector, module_vectors))
    print('질의도 기존 transform/코사인과 일치')
    ''')
    md('''
    ## 6. 경계와 정보 손실도 결과다

    빈 문서, 불용어만 있는 문서, 영어 규칙이 제거하는 한국어, 미등록 단어는 0벡터가 된다.
    아는 단어라도 상대 문서와 겹친 칸이 없으면 0이다. top-k는 0점을 제외하며
    동점은 작은 문서 위치 먼저다. 반환 개수가 k보다 적을 수 있다.
    ''')
    code('''
    for text in ['', 'the and of', 'zzzzunknown', '한국어 검색', 'goalie', 'space orbit', 'orbit space']:
        q = vec.transform([preprocess(text)])[0]
        s = cosine_similarity(q, module_vectors)
        print(repr(text), '→', preprocess(text), '→', q, '→ 점수', s, '→ 순위', top_k(s, 5))
    empty_vector = vec.transform([[]])[0]
    assert np.count_nonzero(empty_vector) == 0
    assert top_k(np.array([0.7, 0.7, 0.0]), 5).tolist() == [0, 1]
    for a, b in [('good team', 'not a good team'), ('space orbit', 'orbit space')]:
        print(repr(a), '/', repr(b), '같은 토큰 빈도?', sorted(preprocess(a)) == sorted(preprocess(b)))
    ''')
    md('''
    ## 7. 실제 검색: 원문 일부·토큰·공통 단어·기여도 연결

    헤더·서명·인용을 제거한 5개 범주의 자료에서 5토큰 미만을 제외한다.
    전체 색인은 검색 대상 모두로 어휘·IDF를 만든다. 이것은 분류 평가의 Train이 아니다.
    문서 위치 p, 원래 ID, 범주 번호를 같은 문서에 연결한다. 출력 원문은 짧은 발췌만 본다.
    ''')
    code('''
    corpus = load_corpus()
    engine = SearchEngine(corpus)
    print('필터 전/후:', corpus.n_raw, len(corpus))
    print('검색 문서 행렬:', engine.matrix.shape, engine.matrix.dtype)
    actual_query = 'space shuttle launch'
    hits = engine.search(actual_query, topk=5)
    table(['순위', '원래 ID', '범주', '코사인'],
          [[rank, h.doc_id, corpus.target_names[corpus.labels[engine.position(h.doc_id)]], round(h.score, 6)]
           for rank, h in enumerate(hits, 1)])
    first = hits[0]
    position = engine.position(first.doc_id)
    print('질의 토큰:', engine.query_tokens(actual_query))
    print('1위 원문 발췌:', first.snippet[:160])
    print('1위 토큰 앞 24개:', corpus.tokens[position][:24])
    ex = engine.explain(actual_query, first.doc_id)
    table(['단어', '질의값', '문서값', '곱'],
          [[t, round(q, 6), round(d, 6), round(v, 6)] for t, q, d, v in ex['shared']])
    print('곱 합:', ex['dot'], '길이:', ex['query_norm'], ex['doc_norm'], '코사인:', ex['cosine'])
    np.testing.assert_allclose(sum(item[3] for item in ex['shared']), ex['dot'])
    np.testing.assert_allclose(ex['cosine'], first.score)
    ''')
    code('''
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar([item[0] for item in ex['shared']], [item[3] for item in ex['shared']])
    ax.set(xlabel='Shared term', ylabel='q[j] * d[j]', title='Top document: contributions to cosine')
    fig.tight_layout()
    plt.show()
    plt.close(fig)
    print('실제 데이터 13설정 대조 시작')
    checks = verify_against_sklearn(corpus.tokens)
    table(['TF', 'smoothing', 'norm', '최대 오차', '어휘 일치', '통과'],
          [[r['ours']['tf'], r['ours']['smooth_idf'], r['ours']['norm'],
            format(r['max_error'], '.2e'), r['vocabulary_equal'], r['pass']] for r in checks])
    assert all(r['pass'] and r['vocabulary_equal'] for r in checks)
    print('코사인 sklearn 최대 오차:', verify_cosine(engine, [actual_query, 'the and of']))
    ''')
    md('''
    ## 8. 성공·실패를 같은 질의 조건에서 보기

    어순·부정어 손실은 위에서 직접 확인했다. 다음은 현재 어휘의 동의어·다의어 실험이다.
    결과가 다르다고 문서의 의미까지 다르다고 판단하지 않는다. 단어 하나가 여러 뜻을 갖거나
    같은 의미가 다른 표기로 나올 때, BoW는 문맥을 복원하지 못한다.
    실제 문서의 원인을 단정하지 않고 토큰과 공통 단어로 관찰 가능한 범위만 설명한다.
    ''')
    code('''
    limits = bow_limits(engine)
    table(['사례', '문장 A', '문장 B', '코사인'],
          [[key, limits[key]['a'], limits[key]['b'], round(limits[key]['cosine'], 6)]
           for key in ['word_order', 'negation', 'synonym']])
    print('goalie / goaltender 상위 10개 겹침:', limits['synonym']['top10_overlap'])
    print('한국어 예는 형태소를 손으로 나눈 별도 실험이다. 이 전처리기의 기능이 아니다.')
    for text in ['hockey playoff goalie', 'hockey playoff goaltender', 'save', 'zzzzunknown', 'the and of']:
        results = engine.search(text, topk=3)
        print(repr(text), '토큰', preprocess(text), '→',
              [(h.doc_id, round(h.score, 4), corpus.target_names[corpus.labels[engine.position(h.doc_id)]]) for h in results])
    ''')
    md('''
    ## 9. 분류: 표현 학습과 모델 학습을 나누기

    원본 공식 train/test 대신 전체 자료를 고정 난수 42의 층화 8:2로 새로 나눈 실험이다.
    `X`는 문서×단어, `y`는 문서의 범주 번호다. Test의 새 단어는 열을 추가하지 않는다.
    C 선택은 Train 내부 5-fold: 각 fold의 학습 토큰으로 어휘·IDF를 fit하고 검증 토큰은 transform.
    C를 고른 뒤 Train 전체로 표현과 모델을 학습하고 Test에서 평가한다.
    기존 outputs의 CV는 Train 전체 어휘·IDF를 공유했다. 비교 조건이 바뀌었으므로 별도로 읽는다.
    ''')
    code('''
    train_idx, test_idx = train_test_indices(corpus.labels)
    train_tokens = [corpus.tokens[i] for i in train_idx]
    test_tokens = [corpus.tokens[i] for i in test_idx]
    classification_vec = TfidfVectorizerNP(min_df=5, max_df=0.5)
    X_train = classification_vec.fit_transform(train_tokens)
    frozen_idf = classification_vec.idf_.copy()
    X_test = classification_vec.transform(test_tokens)
    y_train = corpus.labels[train_idx]
    y_test = corpus.labels[test_idx]
    print('X_train / y_train:', X_train.shape, y_train.shape)
    print('X_test / y_test:', X_test.shape, y_test.shape)
    print('검색 어휘 / 분류 어휘:', len(engine.vectorizer.terms_), len(classification_vec.terms_))
    np.testing.assert_array_equal(frozen_idf, classification_vec.idf_)
    assert not set(train_idx).intersection(test_idx)
    print('Test의 0벡터 수:', np.count_nonzero(np.linalg.norm(X_test, axis=1) == 0))
    # 메모리를 돌려주고 기존 분류 모듈로 같은 분할·설정을 실행한다.
    del X_train, X_test
    result = run_classification(corpus)
    print('fold마다 표현 재학습 CV:', result.cv_scores, '선택 C:', result.C)
    print('Test accuracy:', result.accuracy, 'macro F1:', result.f1_macro)
    previous = json.loads((root/'outputs/classification.json').read_text(encoding='utf-8'))
    print('이전 조건의 저장 결과:', {k: v for k, v in previous.items()
          if k in ['C', 'accuracy', 'f1_macro', 'cv_scores']})
    ''')
    md('''
    ## 10. 한 예측과 혼동 행렬 읽기

    분류 점수 `z = W @ x + b`를 softmax로 변환한 확률과 검색 코사인은 서로 다르다.
    확률의 최댓값이 커도 예측이 맞는다는 보장은 없다. 혼동 행렬은 행=실제, 열=예측, 단위=문서 건수다.
    ''')
    code('''
    mistakes = np.flatnonzero(result.y_pred != y_test)
    row = int(mistakes[0]) if len(mistakes) else 0
    x = result.X_test[row]
    logits = result.model.coef_ @ x + result.model.intercept_
    exp_values = np.exp(logits - logits.max())
    probabilities = exp_values / exp_values.sum()
    predicted = int(result.y_pred[row])
    actual = int(y_test[row])
    print('Test 행 / Corpus 위치 / 원래 ID:', row, result.test_idx[row], corpus.doc_ids[result.test_idx[row]])
    table(['범주', '선형 점수', '모델 확률'],
          [[name, round(z, 5), round(p, 5)] for name, z, p in zip(corpus.target_names, logits, probabilities)])
    np.testing.assert_allclose(probabilities, result.proba[row])
    print('실제 / 예측:', corpus.target_names[actual], corpus.target_names[predicted])
    push = x * (result.model.coef_[predicted] - result.model.coef_[actual])
    intercept_gap = result.model.intercept_[predicted] - result.model.intercept_[actual]
    np.testing.assert_allclose(push.sum() + intercept_gap, logits[predicted] - logits[actual], atol=1e-12)
    strongest = np.argsort(-np.abs(push))[:6]
    table(['단어', '예측−실제 선형 점수 기여'],
          [[result.vectorizer.terms_[j], round(push[j], 6)] for j in strongest if push[j] != 0])
    print('모든 단어 기여 합 / 절편 차이:', push.sum(), intercept_gap)
    print('산술적 점수 분해이며 현실의 오분류 원인을 증명하지 않는다.')
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(result.confusion, cmap='Blues')
    ax.set_xticks(range(5), corpus.target_names, rotation=30, ha='right')
    ax.set_yticks(range(5), corpus.target_names)
    ax.set(xlabel='Predicted category', ylabel='Actual category', title='Test confusion matrix (documents)')
    for i in range(5):
        for j in range(5):
            ax.text(j, i, str(result.confusion[i, j]), ha='center', va='center',
                    color='white' if result.confusion[i, j] > result.confusion.max()/2 else 'black')
    fig.colorbar(im, ax=ax, label='Documents')
    fig.tight_layout()
    plt.show()
    plt.close(fig)
    ''')
    md('''
    ## 11. 보너스: 점수 방식과 검색 경로는 서로 다른 선택

    TF raw/log/double/binary는 반복 단어의 보상을 바꾸고 BM25는 빈도 포화·문서 길이를 반영한다.
    역색인은 질의 단어가 있는 문서의 포스팅만 방문하는 경로다. 후보를 찾은 뒤 저장 가중치로
    점수를 더한다. TF-IDF와 BM25 점수의 절대 크기를 같은 척도로 비교하지 않는다.
    ''')
    code('''
    frequency = np.array([[4., 1., 0.]])
    for variant in ['raw', 'log', 'double', 'binary']:
        print(variant, term_frequency(frequency, variant))
    for method in ['tfidf', 'bm25']:
        full = engine.search(actual_query, method=method)
        indexed = engine.search(actual_query, method=method, use_index=True)
        assert [h.doc_id for h in full] == [h.doc_id for h in indexed]
        np.testing.assert_allclose([h.score for h in full], [h.score for h in indexed])
        print(method, [(h.doc_id, round(h.score, 6)) for h in full])
    q = engine.query_vector(actual_query)
    weights = {}
    for column in np.flatnonzero(q):
        weights[int(column)] = float(q[column])
    candidates, candidate_scores, visited = engine.index('tfidf').score(weights)
    print('전체 문서:', len(corpus), '후보:', len(candidates), '방문 포스팅:', visited)
    # 같은 질의·벡터·행 부분집합으로 측정. 구축/질의 벡터화 제외, 5회 중 최솟값.
    timings = benchmark_index(engine, [actual_query, 'hockey playoff goalie', 'save'], [500, len(corpus)])
    print(json.dumps(timings, indent=2))
    assert all(row['same_top_k'] for row in timings)
    ''')
    md('''
    ## 친구에게 5분 시연하기

    1. `space shuttle launch`의 1위와 겹치는 단어 세 개를 보여 준다. 곱의 합이 코사인임을 설명한다.
    2. `the and of`, 미등록 단어를 넣어 빈 결과를 보여 준다. 결과가 없는 이유를 토큰과 어휘에서 찾는다.
    3. `space orbit` / `orbit space`, `good team` / `not a good team`으로 잃어버리는 정보를 보인다.
    4. `save`를 TF-IDF·BM25로 비교한다. 다의어를 문맥 없이 센다는 한계와 두 점수의 척도 차이를 설명한다.
    5. 역색인을 켜도 같은 점수를 얻는지 확인하고, 분류는 정답 범주로 별도 모델을 학습한다는 경계를 짚는다.

    ```powershell
    uv run python main.py --query "space shuttle launch" --explain
    uv run python main.py --query "the and of"
    uv run python main.py --query "save" --method both --index --topk 3
    ```

    **자기 점검:** space TF=2인데 DF=1인 이유는? 질의에서 fit하면 무엇이 바뀌는가?
    0벡터 코사인은 어떻게 처리하는가? Test 단어로 어휘를 확장하면 왜 평가 경계가 흐려지는가?
    역색인의 후보 수와 방문 포스팅 수는 왜 다른가? 코사인 0.47을 47% 정답 확률로 읽을 수 있는가?
    ''')
    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata = {'kernelspec': {'display_name': 'Python (A4-1)', 'language': 'python', 'name': 'python3'},
                         'language_info': {'name': 'python', 'version': '3.12'}}
    for index, cell in enumerate(cells):
        cell.id = f'search-{index:02d}'
    return notebook


def execute(notebook):
    from nbclient import NotebookClient
    from jupyter_client.kernelspec import KernelSpecManager
    runtime = ROOT / '.notebook-runtime'
    runtime.mkdir(exist_ok=True)
    os.environ['JUPYTER_RUNTIME_DIR'] = str(runtime)
    os.environ['IPYTHONDIR'] = str(runtime / 'ipython')
    os.environ['MPLCONFIGDIR'] = str(runtime / 'matplotlib')
    with TemporaryDirectory(dir=runtime, prefix='kernel-') as folder:
        spec = Path(folder) / 'learning'
        spec.mkdir()
        (spec / 'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'A4-1 Learning', 'language': 'python', 'env': {'PYTHONUTF8': '1'}
        }), encoding='utf-8')
        client = NotebookClient(notebook, timeout=1800, kernel_name='learning',
                                resources={'metadata': {'path': str(ROOT)}}, record_timing=False)
        client.km = client.create_kernel_manager()
        client.km.kernel_spec_manager = KernelSpecManager(kernel_dirs=[folder])

        def progress(cell, cell_index):
            if cell.cell_type == 'code':
                print(f'Executing cell {cell_index + 1}', flush=True)
        client.on_cell_start = progress
        client.execute()


if __name__ == '__main__':
    import nbformat
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    notebook = build()
    if args.execute:
        execute(notebook)
    nbformat.validate(notebook)
    TARGET.parent.mkdir(exist_ok=True)
    nbformat.write(notebook, TARGET)
    print('Saved notebooks/search_walkthrough.ipynb')
