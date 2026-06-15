"""
service.py
이 모듈은 가계부의 핵심 로직과 규칙을 처리하는 '비즈니스 서비스(Service) 계층'입니다.
저장소(Repository)가 파일과 직접 대화하며 데이터를 읽고 쓴다면,
서비스(Service)는 그 데이터를 가지고 지출/수입을 계산하고, 정렬하고,
가져오기/내보내기 규칙을 집행하며, 백업을 수행하는 등의 브레인 역할을 합니다.

사용자님의 학습을 돕기 위해, 각 기능이 어떻게 흘러가는지 로직을 정말 세심하게 풀어서 주석으로 작성했습니다.
"""

import os
import csv
import zipfile
from datetime import datetime
from typing import Generator, List, Dict, Any, Tuple, Optional
from budget_app.models import Transaction, Category, Budget, RecurringRule
from budget_app.repository import (
    TransactionRepository,
    CategoryRepository,
    BudgetRepository,
    RecurringRepository
)
from budget_app.decorators import log_execution_time, log_activity


class BudgetService:
    """
    가계부 애플리케이션의 핵심 비즈니스 로직을 제공하는 서비스 클래스입니다.
    """
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.tx_repo = TransactionRepository(data_dir)
        self.cat_repo = CategoryRepository(data_dir)
        self.budget_repo = BudgetRepository(data_dir)
        self.rec_repo = RecurringRepository(data_dir)

    # -------------------------------------------------------------
    # 1. 거래(Transaction) CRUD 비즈니스 로직
    # -------------------------------------------------------------
    
    def _generate_new_id(self) -> str:
        """
        고유한 일련번호 형식의 거래 ID(예: TX-000001)를 자동으로 발급합니다.
        가장 큰 ID 숫자값을 찾아 1을 더해주는 방식으로 안전하게 발급합니다.
        """
        max_num = 0
        for tx in self.tx_repo.find_all_stream():
            if tx.id.startswith("TX-"):
                try:
                    num = int(tx.id.split("-")[1])
                    if num > max_num:
                        max_num = num
                except (ValueError, IndexError):
                    pass
        # 포맷팅을 통해 6자리의 숫자로 맞춥니다. 예: 1 -> TX-000001
        return f"TX-{max_num + 1:06d}"

    @log_activity() # 데코레이터 적용: 작업 내용을 로그 파일에 기록
    def add_transaction(self, date: str, type_str: str, category: str, amount: int, memo: str = "", tags: List[str] = None) -> str:
        """
        검증된 정보를 토대로 새로운 거래 내역을 등록합니다.
        """
        if tags is None:
            tags = []
            
        # 카테고리가 실제로 등록되어 있는지 검증합니다.
        if not self.cat_repo.exists(category):
            raise ValueError(f"'{category}' 카테고리는 등록되지 않은 카테고리입니다. 먼저 카테고리를 추가하세요.")
            
        tx_id = self._generate_new_id()
        tx = Transaction(
            id=tx_id,
            type=type_str,
            date=date,
            amount=amount,
            category=category,
            memo=memo,
            tags=tags
        )
        self.tx_repo.save(tx)
        return tx_id

    def list_transactions(self, limit: Optional[int] = None) -> Generator[Transaction, None, None]:
        """
        최신순(날짜 역순, ID 역순)으로 정렬된 거래 리스트를 제너레이터 스트리밍으로 출력합니다.
        - 파일은 기본적으로 순서대로 추가되므로 최신순 정렬을 위해 전체 목록을 정렬한 뒤 yield 해 줍니다.
        """
        all_tx = self.tx_repo.find_all()
        
        # 날짜 내림차순(최신순), 날짜가 같다면 ID 내림차순으로 정렬합니다.
        # 파이썬의 sort는 안정 정렬(Stable Sort)을 보장하므로 정렬 키를 튜플로 주어 다중 정렬합니다.
        all_tx.sort(key=lambda tx: (tx.date, tx.id), reverse=True)
        
        count = 0
        for tx in all_tx:
            if limit is not None and count >= limit:
                break
            yield tx
            count += 1

    def search_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        type_str: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Generator[Transaction, None, None]:
        """
        다양한 필터 조건을 조합하여 해당하는 거래들을 최신순으로 검색하고 yield로 스트리밍 반환합니다.
        """
        filtered = []
        for tx in self.tx_repo.find_all_stream():
            # 1. 시작 날짜 필터 (from)
            if from_date and tx.date < from_date:
                continue
            # 2. 종료 날짜 필터 (to)
            if to_date and tx.date > to_date:
                continue
            # 3. 카테고리 필터
            if category and tx.category != category:
                continue
            # 4. 수입/지출 종류 필터
            if type_str and tx.type != type_str:
                continue
            # 5. 메모 검색 키워드 필터 (대소문자 무시)
            if keyword and keyword.lower() not in tx.memo.lower():
                continue
            # 6. 태그 필터 (태그 리스트에 해당 태그가 포함되어 있는지)
            if tag and tag not in tx.tags:
                continue
                
            filtered.append(tx)
            
        # 최신순 정렬
        filtered.sort(key=lambda tx: (tx.date, tx.id), reverse=True)
        
        for tx in filtered:
            yield tx

    @log_activity()
    def update_transaction(self, updated_tx: Transaction) -> bool:
        """
        거래 내역 정보를 수정합니다. (카테고리 유효성 체크 포함)
        """
        if not self.cat_repo.exists(updated_tx.category):
            raise ValueError(f"'{updated_tx.category}' 카테고리는 존재하지 않습니다. 카테고리 등록 후 수정해 주세요.")
        return self.tx_repo.update(updated_tx)

    @log_activity()
    def delete_transaction(self, tx_id: str) -> bool:
        """
        특정 거래 내역을 삭제합니다.
        """
        return self.tx_repo.delete(tx_id)

    # -------------------------------------------------------------
    # 2. 요약(Summary) & 예산(Budget) 관리 비즈니스 로직
    # -------------------------------------------------------------
    
    def get_monthly_summary(self, month: str, top_n: int = 3) -> Dict[str, Any]:
        """
        특정 월(YYYY-MM)의 재정 요약 정보를 산출합니다.
        - 총 수입, 총 지출, 잔액
        - 지출 비중 카테고리 TOP N 목록
        - 설정한 월 예산과 비교한 사용률 및 예산 초과 경고 메시지
        """
        total_income = 0
        total_expense = 0
        category_expenses = {} # 카테고리별 지출 금액 합계
        
        # 특정 월에 해당하는 거래 데이터 수집
        has_data = False
        for tx in self.tx_repo.find_all_stream():
            if tx.date.startswith(month):
                has_data = True
                if tx.type == "income":
                    total_income += tx.amount
                elif tx.type == "expense":
                    total_expense += tx.amount
                    category_expenses[tx.category] = category_expenses.get(tx.category, 0) + tx.amount

        if not has_data:
            return {"has_data": False}

        # 카테고리별 지출 순위 정렬 (금액 기준 내림차순)
        sorted_cats = sorted(category_expenses.items(), key=lambda x: x[1], reverse=True)
        top_categories = sorted_cats[:top_n]
        
        # 예산 연동 처리
        budget_obj = self.budget_repo.find_by_month(month)
        budget_amount = budget_obj.amount if budget_obj else None
        
        usage_percent = 0.0
        is_over_budget = False
        if budget_amount and budget_amount > 0:
            usage_percent = (total_expense / budget_amount) * 100
            if total_expense > budget_amount:
                is_over_budget = True

        return {
            "has_data": True,
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "budget_amount": budget_amount,
            "usage_percent": usage_percent,
            "is_over_budget": is_over_budget,
            "top_categories": top_categories
        }

    def set_budget(self, month: str, amount: int) -> None:
        """
        특정 월의 예산을 저장 또는 수정합니다.
        """
        budget = Budget(month=month, amount=amount)
        self.budget_repo.save_or_update(budget)

    # -------------------------------------------------------------
    # 3. 카테고리 관리 기능 (무결성 규칙 적용)
    # -------------------------------------------------------------
    
    def add_category(self, name: str) -> bool:
        """
        새로운 카테고리를 등록합니다.
        """
        if self.cat_repo.exists(name):
            return False
        self.cat_repo.save(Category(name=name))
        return True

    def list_categories(self) -> List[Category]:
        return self.cat_repo.find_all()

    def remove_category(self, name: str, fallback_category: Optional[str] = None) -> Tuple[bool, str]:
        """
        카테고리를 삭제합니다.
        - 무결성 조건: 만약 삭제하려는 카테고리를 참조하는 기존 거래 내역이 존재할 경우,
          삭제를 그냥 허용하면 데이터의 일관성이 깨집니다.
          따라서, 1) 그냥 삭제를 차단하고 경고하거나, 2) 대체할 카테고리를 받아서 거래 데이터를 이관한 뒤 기존 카테고리를 삭제합니다.
        """
        if not self.cat_repo.exists(name):
            return False, "존재하지 않는 카테고리입니다."
            
        # 해당 카테고리를 쓰고 있는 거래 내역이 있는지 먼저 스캔해 둡니다.
        affected_count = 0
        for tx in self.tx_repo.find_all_stream():
            if tx.category == name:
                affected_count += 1
                
        # 만약 해당 카테고리를 쓰고 있는 거래가 있다면 대체 카테고리가 필수적입니다.
        if affected_count > 0:
            if not fallback_category:
                return False, f"'{name}' 카테고리를 사용하는 거래가 {affected_count}건 존재합니다. 안전을 위해 대체할 카테고리를 함께 지정해 주세요."
            if fallback_category == name:
                return False, "대체 카테고리는 삭제하려는 카테고리와 같을 수 없습니다."
            if not self.cat_repo.exists(fallback_category):
                return False, f"대체 지정된 '{fallback_category}' 카테고리가 등록되어 있지 않습니다. 먼저 등록해 주세요."
                
            # 기존 거래들의 카테고리를 대체 카테고리로 안전하게 전부 이관(수정)시킵니다.
            for tx in self.tx_repo.find_all():
                if tx.category == name:
                    tx.category = fallback_category
                    self.tx_repo.update(tx)
                    
        # 카테고리 저장소에서 안전하게 영구 제거
        self.cat_repo.delete(name)
        msg = f"'{name}' 카테고리를 삭제했습니다."
        if affected_count > 0:
            msg += f" (연관된 거래 {affected_count}건의 분류를 '{fallback_category}'(으)로 이관했습니다.)"
        return True, msg

    # -------------------------------------------------------------
    # 4. [보너스 과제 5.1] 백업 기능 (Backup)
    # -------------------------------------------------------------
    
    @log_execution_time # 데코레이터 적용: 백업이 완료될 때 소요 시간을 측정해 출력합니다.
    def backup_data(self) -> str:
        """
        가계부의 데이터 저장 디렉토리의 모든 파일(.jsonl)들을 모아
        타임스탬프 이름이 포함된 단일 ZIP 압축 백업 파일로 저장합니다.
        - 백업 저장소: `./backups/`
        - 반환값: 생성된 백업 파일의 경로
        """
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # 파일명 생성: backup_YYYYMMDD_HHMMSS.zip
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        backup_filepath = os.path.join(backup_dir, backup_filename)
        
        # zipfile 모듈을 사용해 가계부 원본 jsonl 파일들을 한곳에 압축해 담아냅니다.
        with zipfile.ZipFile(backup_filepath, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, _, files in os.walk(self.data_dir):
                for file in files:
                    if file.endswith(".jsonl"):
                        full_path = os.path.join(root, file)
                        # 압축 파일 내부에 들어갈 상대 경로를 지정해 줍니다.
                        archive_name = os.path.relpath(full_path, self.data_dir)
                        zip_file.write(full_path, archive_name)
                        
        return backup_filepath

    # -------------------------------------------------------------
    # 5. [보너스 과제 5.2] 반복 내역 생성 기능 (Recurring)
    # -------------------------------------------------------------
    
    def add_recurring_rule(self, day_of_month: int, type_str: str, category: str, amount: int, memo: str = "", tags: List[str] = None) -> str:
        """
        매달 고정적으로 발생할 지출/수입의 규칙을 새로 추가합니다.
        """
        if tags is None:
            tags = []
            
        if not self.cat_repo.exists(category):
            raise ValueError(f"'{category}' 카테고리는 존재하지 않습니다. 먼저 등록해 주세요.")
            
        # 고유 규칙 ID 발급 (예: REC-000001)
        max_num = 0
        for rule in self.rec_repo.find_all():
            if rule.id.startswith("REC-"):
                try:
                    num = int(rule.id.split("-")[1])
                    if num > max_num:
                        max_num = num
                except (ValueError, IndexError):
                    pass
        rule_id = f"REC-{max_num + 1:06d}"
        
        rule = RecurringRule(
            id=rule_id,
            day_of_month=day_of_month,
            type=type_str,
            amount=amount,
            category=category,
            memo=memo,
            tags=tags
        )
        self.rec_repo.save(rule)
        return rule_id

    def list_recurring_rules(self) -> List[RecurringRule]:
        return self.rec_repo.find_all()

    def remove_recurring_rule(self, rule_id: str) -> bool:
        return self.rec_repo.delete(rule_id)

    @log_execution_time
    def generate_recurring_transactions(self, month: str) -> Tuple[int, int]:
        """
        특정 월(YYYY-MM)의 반복 거래 내역을 규칙에 따라 일괄 자동 생성합니다.
        - 안전 장치(중복 방어):
          거래 메모나 태그 정보에 '[반복 규칙 적용: REC-XXXXXX]'와 같은 고유 표식을 심어둠으로써,
          이미 해당 월에 등록된 반복 항목이 재실행되어 중복 중복 생성되는 문제를 방지합니다.
        - 반환값: (성공 건수, 건너뛴 건수)
        """
        # 해당 년월이 유효한 형식인지 임시 검증
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise ValueError("년월 형식은 YYYY-MM 이어야 합니다. (예: 2026-05)")
            
        rules = self.list_recurring_rules()
        if not rules:
            return 0, 0
            
        # 이미 이달에 생성 완료된 반복 규칙 ID들의 목록을 기 생성된 거래 리스트를 흝어 수집합니다.
        already_generated_rule_ids = set()
        for tx in self.tx_repo.find_all_stream():
            if tx.date.startswith(month):
                # 태그 리스트나 메모 내용에서 규칙 ID 흔적을 찾습니다.
                for tag in tx.tags:
                    if tag.startswith("REC-"):
                        already_generated_rule_ids.add(tag)

        success_count = 0
        skip_count = 0
        
        for rule in rules:
            # 만약 이미 이달에 해당 규칙이 실행된 적이 있다면 건너뜁니다.
            if rule.id in already_generated_rule_ids:
                skip_count += 1
                continue
                
            # 해당 년월과 규칙에 적힌 일자를 결합해 정확한 날짜 생성
            # 단, 예: 2월 30일과 같이 날짜가 초과될 수 있으므로, 해당 달의 마지막 날짜를 넘지 않도록 보정합니다.
            year_int, month_int = map(int, month.split("-"))
            import calendar
            last_day = calendar.monthrange(year_int, month_int)[1]
            day = min(rule.day_of_month, last_day)
            
            date_str = f"{year_int:04d}-{month_int:02d}-{day:02d}"
            
            # 거래 생성 및 저장
            # 태그 리스트에 규칙 ID를 심어 두어 추후 중복 생성을 강력하게 막습니다.
            tx_tags = list(rule.tags)
            if rule.id not in tx_tags:
                tx_tags.append(rule.id)
                
            memo_with_mark = rule.memo
            if not memo_with_mark:
                memo_with_mark = f"[자동 생성] 매달 {rule.day_of_month}일 정기 발생"
                
            tx_id = self._generate_new_id()
            new_tx = Transaction(
                id=tx_id,
                type=rule.type,
                date=date_str,
                amount=rule.amount,
                category=rule.category,
                memo=memo_with_mark,
                tags=tx_tags
            )
            
            # 저장소 저장
            self.tx_repo.save(new_tx)
            success_count += 1
            
        return success_count, skip_count

    # -------------------------------------------------------------
    # 6. 가져오기 및 내보내기 기능 (Import / Export)
    # -------------------------------------------------------------
    
    @log_execution_time
    def export_to_csv(self, out_filepath: str, month: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None) -> int:
        """
        필터 조건에 부합하는 거래 내역을 표준 CSV 파일 형태로 내보냅니다.
        - UTF-8 인코딩, 헤더 포함 필수
        - 스키마: date, type, category, amount, memo, tags
        """
        # 적어도 하나 이상의 필터 조건이 주어졌는지 검증합니다.
        if not month and not from_date and not to_date:
            raise ValueError("내보내기(export) 시에는 반드시 --month 또는 --from/--to 조건이 한 개 이상 필요합니다.")
            
        # 내보낼 거래 필터링
        filtered_tx = []
        if month:
            for tx in self.tx_repo.find_all_stream():
                if tx.date.startswith(month):
                    filtered_tx.append(tx)
        else:
            for tx in self.tx_repo.find_all_stream():
                if from_date and tx.date < from_date:
                    continue
                if to_date and tx.date > to_date:
                    continue
                filtered_tx.append(tx)
                
        # 최신순 정렬
        filtered_tx.sort(key=lambda tx: (tx.date, tx.id), reverse=True)
        
        # CSV 파일 작성 시작
        with open(out_filepath, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            # 1. 헤더 줄 작성
            writer.writerow(["date", "type", "category", "amount", "memo", "tags"])
            
            # 2. 데이터 행 작성
            for tx in filtered_tx:
                # tags 리스트는 쉼표로 연결된 단일 문자열로 조인하여 저장합니다.
                tags_str = ",".join(tx.tags)
                writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo, tags_str])
                
        return len(filtered_tx)

    @log_execution_time
    def import_from_csv(self, csv_filepath: str) -> Tuple[int, int, List[str]]:
        """
        지정된 외부 CSV 파일로부터 거래 내역을 일괄 파싱하여 가계부에 등록합니다.
        
        [신뢰성과 무결성 보장 장치]
        - 일부 불량 행(날짜 포맷 에러, 음수 금액, 등록되지 않은 카테고리 등)이 섞여 있을 때
          전체 등록을 멈추는 대신(All-or-Nothing 방식의 가혹함 지양),
          잘못된 행만 조용히 스킵하고 스킵 사유와 행 번호를 기록하여 나중에 완벽하게 리포트합니다.
        - 이를 통해 사용자는 신뢰성 있는 정상 거래들만 안전하게 가져올 수 있습니다.
        
        - 반환값: (성공 등록 수, 스킵된 수, 스킵 안내 리포트 리스트)
        """
        if not os.path.exists(csv_filepath):
            raise FileNotFoundError(f"불러올 CSV 파일 '{csv_filepath}'을 찾을 수 없습니다.")
            
        success_count = 0
        skip_count = 0
        error_reports = []
        
        with open(csv_filepath, "r", encoding="utf-8") as csv_file:
            # 딕셔너리 리더를 사용하여 헤더 이름 기반으로 안전하게 컬럼을 가져옵니다.
            reader = csv.DictReader(csv_file)
            
            # 필수 헤더가 정상적으로 포함되어 있는지 체크
            required_cols = {"date", "type", "category", "amount"}
            if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
                raise ValueError("가져올 CSV 파일의 헤더(컬럼명) 구성이 올바르지 않습니다. (필수: date, type, category, amount)")
                
            # 1-indexed 행 번호를 매기기 위해 enumerate를 활용합니다.
            # DictReader는 내부적으로 첫 번째 라인(헤더)을 소비했으므로, 2번 행부터 데이터 행이 시작됩니다.
            for idx, row in enumerate(reader, start=2):
                try:
                    # 1) 개별 필드 데이터 무결성 검증 수행
                    raw_date = row.get("date", "").strip()
                    raw_type = row.get("type", "").strip()
                    raw_category = row.get("category", "").strip()
                    raw_amount = row.get("amount", "").strip()
                    memo = row.get("memo", "").strip()
                    tags_raw = row.get("tags", "").strip()
                    
                    # 헬퍼 함수를 통한 형식 검사 수행
                    from budget_app.utils import validate_date, validate_type, validate_amount
                    
                    date_val = validate_date(raw_date)
                    type_val = validate_type(raw_type)
                    amount_val = validate_amount(raw_amount)
                    
                    # 카테고리가 가계부에 등록되어 있는지 검증 (미션 무결성 지침)
                    if not self.cat_repo.exists(raw_category):
                        raise ValueError(f"'{raw_category}' 카테고리는 현재 가계부에 존재하지 않는 카테고리입니다.")
                        
                    # 태그 복원 (쉼표 구분 형태)
                    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
                    
                    # 2) 검증 완료된 거래 데이터를 저장소에 영구 추가
                    tx_id = self._generate_new_id()
                    tx = Transaction(
                        id=tx_id,
                        type=type_val,
                        date=date_val,
                        amount=amount_val,
                        category=raw_category,
                        memo=memo,
                        tags=tags
                    )
                    self.tx_repo.save(tx)
                    success_count += 1
                    
                except Exception as e:
                    # 행 파싱 중 검증 예외 등이 나면, 에러 메시지를 수집하고 해당 행을 안전하게 건너뜁니다.
                    skip_count += 1
                    error_reports.append(f"[{idx}번 행 스킵 이유] {e}")
                    
        return success_count, skip_count, error_reports
