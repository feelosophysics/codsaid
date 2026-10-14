"""Append reproducible bonus analysis cells to the existing report notebook."""
from pathlib import Path
import nbformat

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / 'notebooks/analysis_report.ipynb'
    notebook = nbformat.read(path, as_version=4)
    notebook.cells = [c for c in notebook.cells if not c.id.startswith('a1-bonus-')]
    notebook.cells[0].source = notebook.cells[0].source.replace('`python -m src.run_analysis --generate-sample`', '`uv run python -m src.run_analysis --generate-sample`')
    for cell in notebook.cells:
        if cell.cell_type == 'markdown':
            cell.source = cell.source.replace('HTML 학습 자료와 선택 보너스 과제는 이번 구현 범위에 포함하지 않는다.',
                                              'HTML 학습 자료와 선택 보너스 3종을 함께 제공한다. 아래 셀에서 보너스 결과를 확인한다.')
    texts = [
        ('markdown', '## 보너스 1 — NumPy 이미지 피처\n\n8개 구간의 정규화 밝기 히스토그램, 이웃 픽셀 차이, 엔트로피를 직접 계산한다. 픽셀·이미지 순회 루프 없이 배열 연산을 쓴다. 합성 이미지의 수치 요약이며 상품 품질을 판단한 값이 아니다.'),
        ('code', "from src.bonus import write_bonus\nbonus_summary = write_bonus(analyzer, OUTPUT)\ndisplay(pd.read_csv(OUTPUT / 'bonus/image_features.csv').head())\ndisplay(Image(filename=str(OUTPUT / 'bonus/image_features.png')))"),
        ('markdown', '## 보너스 2 — 가입 월별 코호트\n\ncustomers.csv의 명시적 합성 가입일을 사용한다. 분모는 가입 고객 전체, 분자는 경과 월에 양수 구매한 고유 고객이다. 같은 고객의 여러 상품 행은 한 번만 센다. 가입 월은 반드시 100%가 아니며, 월말까지 관측하지 않은 칸은 미관측으로 남긴다.'),
        ('code', "display(pd.read_csv(DATA / 'customers.csv').head())\ndisplay(pd.read_csv(OUTPUT / 'bonus/cohort_sizes.csv'))\ndisplay(pd.read_csv(OUTPUT / 'bonus/cohort_retention.csv', index_col=0).map(lambda x: '미관측' if pd.isna(x) else f'{x:.0%}'))\ndisplay(Image(filename=str(OUTPUT / 'bonus/cohort_retention.png')))"),
        ('markdown', '## 보너스 3 — 인터랙티브 RFM\n\nPlotly는 이 선택 보너스에서만 사용한다. 아래 HTML은 라이브러리를 포함해 인터넷 없이 열 수 있다. 점 hover로 고객별 R/F/M을 확인하고 범례로 그룹을 선택하며 확대·PNG 저장을 할 수 있다.'),
        ('code', "from IPython.display import HTML\ndisplay(HTML((OUTPUT / 'bonus/rfm_interactive.html').read_text(encoding='utf-8')))\nprint(bonus_summary)"),
    ]
    for i, (kind, text) in enumerate(texts):
        cell = nbformat.v4.new_code_cell(text) if kind == 'code' else nbformat.v4.new_markdown_cell(text)
        cell.id = f'a1-bonus-{i:02d}'
        notebook.cells.append(cell)
    nbformat.write(notebook, path)


if __name__ == '__main__':
    main()
