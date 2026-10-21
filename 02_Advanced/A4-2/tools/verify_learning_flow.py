"""노트북 원문·HTML 코드/JS 일치와 Python–JS 계산을 대조한다. Node.js가 필요하다."""
import ast
import json
import random
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import nbformat
    from build_learning_notebook import build
    from src import aspect, extract, sentiment
    from src.data import load_splits
    from src.eval_extraction import read_jsonl

    notebook = nbformat.read(ROOT / 'notebooks/rules_walkthrough.ipynb', as_version=4)
    nbformat.validate(notebook)
    assert [(c.cell_type, c.source, c.id) for c in notebook.cells] == [
        (c.cell_type, c.source, c.id) for c in build().cells]
    execution_count = 0
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            execution_count += 1
            assert cell.execution_count == execution_count
            assert all(o.output_type != 'error' for o in cell.outputs)
    html = (ROOT / 'study/a4-2.html').read_text(encoding='utf-8')
    data = json.loads(re.search(r'<script id="study-data"[^>]*>(.*?)</script>', html, re.S)[1])
    for name in ['engine', 'app']:
        embedded = re.search(r'<script id="' + name + r'">(.*?)</script>', html, re.S)[1]
        assert embedded.strip() == (ROOT / 'study' / (name + '.js')).read_text(encoding='utf-8').strip()
        # app.js의 DOM 처리는 실행하지 않고 JavaScript 문법만 검증한다.
        subprocess.run(['node', '--check', str(ROOT / 'study' / (name + '.js'))], check=True)
    for entry in data['code']:
        source = (ROOT / entry['file']).read_text(encoding='utf-8')
        nodes = ast.parse(source).body
        for part in entry['name'].split('.'):
            node = next(n for n in nodes if getattr(n, 'name', None) == part or (
                isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == part for t in n.targets)))
            nodes = getattr(node, 'body', [])
        assert entry['start'] == node.lineno
        assert entry['code'] == '\n'.join(source.splitlines()[node.lineno - 1:node.end_lineno])

    # Python은 코드 포인트, JavaScript는 UTF-16 코드 단위로 문자열 위치를 센다.
    def js_position(text, position):
        return len(text[:position].encode('utf-16-le')) // 2

    analyzer = sentiment.SentimentAnalyzer()
    splits = load_splits()
    handmade = ROOT / 'data/handmade'
    rows = splits['dev'] + splits['test'] + random.Random(42).sample(splits['pool'], 3000)
    texts = [r['text'] for r in rows] + [r['text'] for r in read_jsonl(handmade / 'sentiment_rules.jsonl')]
    texts += ['좋다 나쁘다', '문의만 남깁니다', '재미있지 않을 수 없다', '정말 맛있지 않았어요', '']
    expected = []
    for _, config in sentiment.ABLATION_STEPS:
        for text in texts:
            result = analyzer.analyze(text, config)
            values = result.to_dict()
            normalized = sentiment.normalize_text(text)
            for item in values['items'] + values['orphans']:
                item['start'] = js_position(normalized, item['start'])
            expected.append({'text': text, 'config': asdict(config), 'expected': values})
    extraction = []
    for row in read_jsonl(handmade / 'extraction_cases.jsonl'):
        text = row['text']
        values = [asdict(e) for e in extract.extract(text)]
        for e in values:
            e['start'], e['end'] = js_position(text, e['start']), js_position(text, e['end'])
        extraction.append({'text': text, 'expected': values})
    masking = [{'text': r['text'], 'expected': extract.mask(r['text'])[0]}
               for r in read_jsonl(handmade / 'masking_cases.jsonl')]
    aspects = []
    for mode in ['preceding', 'nearest']:
        aa = aspect.AspectAnalyzer(mode)
        for row in read_jsonl(handmade / 'aspect_cases.jsonl'):
            aspects.append({'text': row['text'], 'mode': mode,
                            'expected': sorted(aa.pairs(row['text']))})
    script = (ROOT / 'study/engine.js').read_text(encoding='utf-8') + r'''
    const fs=require('fs'), assert=require('assert');
    const input=JSON.parse(fs.readFileSync(0,'utf8'));
    const engine=A42.makeEngine(input.engine);
    let maxError=0;
    function same(actual,expected){
      if(typeof expected==='number'){
        const error=Math.abs(actual-expected);
        assert(Number.isFinite(actual) && error<1e-9);
        maxError=Math.max(maxError,error);
      } else if(Array.isArray(expected)){
        assert(Array.isArray(actual) && actual.length===expected.length);
        expected.forEach((v,i)=>same(actual[i],v));
      } else if(expected!==null && typeof expected==='object'){
        for(const [key,value] of Object.entries(expected))same(actual[key],value);
      } else assert.strictEqual(actual,expected);
    }
    for(const row of input.sentiment)same(engine.analyze(row.text,row.config),row.expected);
    for(const row of input.extraction)same(engine.extract(row.text),row.expected);
    for(const row of input.masking)same(engine.mask(row.text)[0],row.expected);
    for(const row of input.aspects)same(engine.aspectPairs(row.text,row.mode),row.expected);
    console.log(JSON.stringify({sentiment:input.sentiment.length,extraction:input.extraction.length,
      masking:input.masking.length,aspects:input.aspects.length,maxError}));
    '''
    payload = {'engine': data['engine'], 'sentiment': expected, 'extraction': extraction,
               'masking': masking, 'aspects': aspects}
    output = subprocess.run(['node', '-e', script], input=json.dumps(payload, ensure_ascii=False),
                            capture_output=True, text=True, encoding='utf-8')
    if output.returncode:
        raise RuntimeError(output.stderr[-3500:])
    print('Executed notebook/source IDs match; embedded scripts and 15 code excerpts match.')
    print(output.stdout.strip())


if __name__ == '__main__':
    main()
