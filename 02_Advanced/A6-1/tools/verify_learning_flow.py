"""노트북 실행·공개 범위와 HTML 코드 발췌를 검사한다. --refresh-html로 발췌만 갱신한다."""
import argparse
import ast
import json
import re
from pathlib import Path

import nbformat

from build_learning_notebook import ROOT, TARGET, build


def html_code(refresh=False):
    path = ROOT/'study/a6-1.html'
    html = path.read_text(encoding='utf-8')
    marker = '<script>const DATA = '
    start = html.index(marker) + len(marker)
    end = html.index(';</script>', start)
    data = json.loads(html[start:end])
    for key, snippet in data['code'].items():
        source = (ROOT/snippet['file']).read_text(encoding='utf-8')
        node = ast.parse(source)
        for part in snippet['name'].split('.'):
            node = next(n for n in node.body if getattr(n, 'name', '') == part)
        expected = '\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])
        if refresh:
            snippet.update(start=node.lineno, end=node.end_lineno, text=expected)
        else:
            assert snippet['text'] == expected, f'HTML 코드 불일치: {key}'
            assert (snippet['start'], snippet['end']) == (node.lineno, node.end_lineno), key
    if refresh:
        path.write_text(html[:start] + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + html[end:],
                        encoding='utf-8')
    print(f"HTML source excerpts: {len(data['code'])} matched")


def notebook_check():
    saved = nbformat.read(TARGET, as_version=4)
    expected = build()
    nbformat.validate(saved)
    assert [(c.cell_type, c.source, c.id) for c in saved.cells] == [
        (c.cell_type, c.source, c.id) for c in expected.cells]
    executed, figures = 0, 0
    for cell in saved.cells:
        assert not cell.get('attachments'), '불필요한 첨부'
        if cell.cell_type == 'code':
            executed += 1
            assert cell.execution_count is not None, cell.id
        for output in cell.get('outputs', []):
            assert output.output_type != 'error', cell.id
            if 'image/png' in output.get('data', {}):
                figures += 1
    assert figures == 1, 'XOR 곡선 한 개가 출력돼야 한다'
    checked = [TARGET, Path(__file__), ROOT/'tools/build_learning_notebook.py']
    for path in checked:
        text = path.read_text(encoding='utf-8')
        # 패턴 자체의 문자열이 검사 파일에 들어 있으므로 이 파일은 정규식 검사에서 제외한다.
        if path != Path(__file__):
            assert not re.search(r'[A-Za-z]:\\\\|/Users/|/home/|sk-[A-Za-z0-9]{20,}', text), path.name
            assert not any(word in text for word in ['source-manifest', '평가표', 'A6-1.json']), path.name
    print(f'Notebook: {executed} executed code cells, {figures} figure, source/privacy checks passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-html', action='store_true')
    args = parser.parse_args()
    html_code(args.refresh_html)
    notebook_check()
