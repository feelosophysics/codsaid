"""
repository.py
이 모듈은 데이터의 영구 저장을 책임지는 '저장소(Repository) 계층'입니다.
우리는 미션에서 제시한 제약 사항에 따라 외부 라이브러리(SQL 등) 없이 오직 파일 입출력으로만 데이터를 저장합니다.

여기서 아주 중요한 핵심 기술 2가지를 학습하게 됩니다:
1. **제너레이터(Generator, yield)**: 대량의 가계부 데이터를 한 번에 메모리에 올리지 않고,
   파일에서 한 줄씩 읽어가며 필요할 때마다 실시간으로 전달(스트리밍)하여 메모리를 효율적으로 씁니다.
2. **[보너스 과제 5.4] 원자적 쓰기(Atomic Write)**: 데이터를 수정/삭제할 때 기존 파일을 직접 덮어쓰지 않고,
   안전하게 임시 파일(.tmp)을 만든 후 쓰기가 완료되면 '원자적으로(한 번에)' 교체하여 정전 등의 비상 상황에서도 데이터가 절대 유실되지 않게 방어합니다.
"""

import os
import json
import shutil
from typing import Generator, List, Optional
from budget_app.models import Transaction, Category, Budget, RecurringRule


class BaseRepository:
    """
    모든 저장소 클래스가 공통으로 사용하는 원자적 쓰기 및 기본 경로 관리 로직을 품은 부모 클래스입니다.
    """
    def __init__(self, data_dir: str = "data", filename: str = ""):
        self.data_dir = data_dir
        self.filename = filename
        self.file_path = os.path.join(data_dir, filename)
        
        # 저장 폴더가 존재하지 않으면 자동으로 폴더를 생성합니다.
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 저장할 데이터 파일이 없으면 빈 파일을 만들어 초기화해 줍니다.
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                pass # 그냥 비어 있는 상태로 파일을 생성만 해 둡니다.

    def _atomic_write_lines(self, lines: List[str]) -> None:
        """
        [보너스 과제 5.4] 원자적 쓰기(Atomic Write) 구현
        - 데이터를 영구 파일에 안전하게 기록하는 역할을 합니다.
        - 메커니즘:
          1) 대상 파일과 같은 폴더에 임시 파일(예: 파일명.tmp)을 생성합니다.
          2) 임시 파일에 모든 데이터를 기록하고 정상적으로 닫습니다(Close).
          3) `os.replace` 함수를 통해 임시 파일을 원본 파일 경로로 원자적 교체합니다.
             (OS 커널 레벨에서 즉시 이름이 변경되므로 파일 쓰기 중 오류가 나도 기존 원본 파일은 완벽히 안전합니다!)
        """
        tmp_file_path = self.file_path + ".tmp"
        try:
            # 1단계: 임시 파일에 한 줄씩 쓰기
            with open(tmp_file_path, "w", encoding="utf-8") as tmp_file:
                for line in lines:
                    tmp_file.write(line + "\n")
            
            # 2단계: 쓰기가 정상 완료되면 OS 수준에서 안전하게 덮어쓰기 교체
            os.replace(tmp_file_path, self.file_path)
        except Exception as e:
            # 만약 쓰는 도중 에러가 나면, 생성되었던 임시 파일만 안전하게 지우고 에러를 상위로 던집니다.
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
            raise IOError(f"파일을 안전하게 쓰는 도중 오류가 발생했습니다: {e}")


class TransactionRepository(BaseRepository):
    """
    거래 내역(Transaction)의 영구 저장을 담당하는 클래스입니다. (JSONL 형식 사용)
    """
    def __init__(self, data_dir: str = "data"):
        super().__init__(data_dir=data_dir, filename="transactions.jsonl")

    def save(self, transaction: Transaction) -> None:
        """
        새로운 거래 내역을 파일 끝에 덧붙여(Append) 저장합니다.
        """
        # JSON 형식을 한 줄 문자열로 인코딩합니다.
        json_line = json.dumps(transaction.to_dict(), ensure_ascii=False)
        
        # 파일 끝에 'a'(append) 모드로 추가합니다.
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json_line + "\n")

    def find_all_stream(self) -> Generator[Transaction, None, None]:
        """
        [핵심 미션] 제너레이터 기반 스트리밍 조회
        - 파일 전체를 한 번에 리스트로 읽지 않고(메모리 낭비 방지),
          한 줄(거래 1건)씩 읽을 때마다 yield를 호출해 호출처에 즉시 전달합니다.
        """
        if not os.path.exists(self.file_path):
            return
            
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                # 한 줄의 JSON 텍스트를 파이썬 딕셔너리로 바꾼 뒤 객체로 복원합니다.
                data_dict = json.loads(stripped_line)
                yield Transaction.from_dict(data_dict)

    def find_all(self) -> List[Transaction]:
        """
        내부 분석이나 가공을 위해 제너레이터 전체를 리스트로 받아옵니다.
        """
        return list(self.find_all_stream())

    def update(self, updated_tx: Transaction) -> bool:
        """
        [원자적 수정] 특정 ID를 가진 거래 내역을 안전하게 변경합니다.
        """
        found = False
        new_lines = []
        
        # 모든 거래를 돌면서 수정 대상 ID는 변경된 데이터로, 나머지는 그대로 유지합니다.
        for tx in self.find_all_stream():
            if tx.id == updated_tx.id:
                new_lines.append(json.dumps(updated_tx.to_dict(), ensure_ascii=False))
                found = True
            else:
                new_lines.append(json.dumps(tx.to_dict(), ensure_ascii=False))
                
        if found:
            # 임시 파일에 적어 덮어씌우는 원자적 쓰기 작동!
            self._atomic_write_lines(new_lines)
            
        return found

    def delete(self, tx_id: str) -> bool:
        """
        [원자적 삭제] 특정 ID를 가진 거래 내역을 안전하게 삭제합니다.
        """
        found = False
        new_lines = []
        
        # 삭제할 ID를 제외한 모든 거래만 모읍니다.
        for tx in self.find_all_stream():
            if tx.id == tx_id:
                found = True
            else:
                new_lines.append(json.dumps(tx.to_dict(), ensure_ascii=False))
                
        if found:
            # 임시 파일에 적어 덮어씌우는 원자적 쓰기 작동!
            self._atomic_write_lines(new_lines)
            
        return found


class CategoryRepository(BaseRepository):
    """
    카테고리 목록(Category)의 영구 저장을 담당하는 클래스입니다. (JSONL 형식 사용)
    """
    def __init__(self, data_dir: str = "data"):
        super().__init__(data_dir=data_dir, filename="categories.jsonl")
        self._ensure_initial_categories()

    def _ensure_initial_categories(self) -> None:
        """
        파일이 비어 있을 때, 사용의 편의를 위해 대표적인 초기 기본 카테고리를 자동 생성합니다. (안 A 방식)
        """
        if os.path.getsize(self.file_path) == 0:
            default_categories = ["식비", "교통", "주거", "수입", "기타"]
            for cat_name in default_categories:
                self.save(Category(name=cat_name))

    def save(self, category: Category) -> None:
        """
        새로운 카테고리를 저장합니다. (이미 존재하면 중복 저장 안 함)
        """
        # 중복 방지를 위해 전체 목록 확인
        if self.exists(category.name):
            return
            
        json_line = json.dumps(category.to_dict(), ensure_ascii=False)
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json_line + "\n")

    def find_all(self) -> List[Category]:
        """
        전체 카테고리 목록을 불러옵니다.
        """
        categories = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    categories.append(Category.from_dict(json.loads(stripped)))
        return categories

    def exists(self, category_name: str) -> bool:
        """
        특정 이름의 카테고리가 등록되어 있는지 확인합니다.
        """
        for cat in self.find_all():
            if cat.name == category_name:
                return True
        return False

    def delete(self, category_name: str) -> bool:
        """
        카테고리를 안전하게 제거합니다.
        """
        found = False
        new_lines = []
        for cat in self.find_all():
            if cat.name == category_name:
                found = True
            else:
                new_lines.append(json.dumps(cat.to_dict(), ensure_ascii=False))
                
        if found:
            self._atomic_write_lines(new_lines)
        return found


class BudgetRepository(BaseRepository):
    """
    월별 예산(Budget) 정보를 영구 저장을 담당하는 클래스입니다. (JSONL 형식 사용)
    """
    def __init__(self, data_dir: str = "data"):
        super().__init__(data_dir=data_dir, filename="budgets.jsonl")

    def save_or_update(self, budget: Budget) -> None:
        """
        예산을 저장합니다. 이미 해당 년월(YYYY-MM)의 예산 설정이 존재한다면,
        기존 금액을 수정(업데이트)합니다.
        """
        found = False
        new_lines = []
        for bg in self.find_all():
            if bg.month == budget.month:
                new_lines.append(json.dumps(budget.to_dict(), ensure_ascii=False))
                found = True
            else:
                new_lines.append(json.dumps(bg.to_dict(), ensure_ascii=False))
                
        if not found:
            # 기존에 없던 달이면 파일 끝에 덧붙여 씁니다.
            json_line = json.dumps(budget.to_dict(), ensure_ascii=False)
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")
        else:
            # 기존 예산을 고쳤다면 전체 라인을 원자적으로 덮어씁니다.
            self._atomic_write_lines(new_lines)

    def find_all(self) -> List[Budget]:
        budgets = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    budgets.append(Budget.from_dict(json.loads(stripped)))
        return budgets

    def find_by_month(self, month: str) -> Optional[Budget]:
        """
        특정 년월(YYYY-MM)의 예산 설정을 찾아 반환합니다. (없으면 None)
        """
        for bg in self.find_all():
            if bg.month == month:
                return bg
        return None


class RecurringRepository(BaseRepository):
    """
    [보너스 과제 5.2]
    매달 고정으로 나가는 비용이나 수입인 '반복 거래 규칙'을 저장하는 클래스입니다. (JSONL 형식 사용)
    """
    def __init__(self, data_dir: str = "data"):
        super().__init__(data_dir=data_dir, filename="recurring.jsonl")

    def save(self, rule: RecurringRule) -> None:
        json_line = json.dumps(rule.to_dict(), ensure_ascii=False)
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json_line + "\n")

    def find_all(self) -> List[RecurringRule]:
        rules = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    rules.append(RecurringRule.from_dict(json.loads(stripped)))
        return rules

    def delete(self, rule_id: str) -> bool:
        found = False
        new_lines = []
        for rule in self.find_all():
            if rule.id == rule_id:
                found = True
            else:
                new_lines.append(json.dumps(rule.to_dict(), ensure_ascii=False))
                
        if found:
            self._atomic_write_lines(new_lines)
        return found
