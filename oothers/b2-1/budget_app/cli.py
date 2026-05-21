"""
cli.py
이 모듈은 사용자와 직접 소통하는 '표현(Presentation) 계층'인 CLI 컨트롤러입니다.
파이썬 표준 라이브러리인 `argparse`를 활용하여 명령행 매개변수와 도움말(--help)을 자동으로 다듬고,
동시에 사용자의 입력을 자연스럽게 유도하는 '대화형 입력 흐름(Interactive UI Loop)'을 설계했습니다.

[핵심 사용성 설계]
- 사용자가 잘못된 형식을 입력했을 경우 바로 프로그램이 꺼지지 않고, 무엇이 틀렸는지 '힌트'를 주며
  올바른 값을 입력할 때까지 재입력을 친절하게 안내합니다.
- 'update' 기능은 약속된 '대화형(안 B)'으로 완벽히 고정하여 동작시킵니다.
"""

import sys
import argparse
from typing import List, Optional, Callable, Any
from budget_app.models import Transaction
from budget_app.service import BudgetService
from budget_app.utils import (
    validate_date,
    validate_type,
    validate_amount,
    validate_month,
    print_table
)
from budget_app.decorators import handle_errors_gracefully


def prompt_interactive(
    prompt_text: str,
    validator: Callable[[str], Any],
    optional: bool = False,
    default_val: str = ""
) -> Any:
    """
    대화형 입력을 유도하는 만능 도우미 함수입니다.
    - 사용자가 값을 올바르게 입력할 때까지 반복해서 입력받으며,
    - 잘못된 형식 입력 시 예외를 가리켜 주어 올바른 입력을 도와줍니다.
    - optional=True 이면 엔터(빈 값)를 쳤을 때 default_val을 그대로 승인합니다.
    """
    while True:
        try:
            user_input = input(prompt_text).strip()
            
            # 입력값이 비어 있고, 생략 가능한 항목인 경우
            if not user_input and optional:
                if default_val:
                    # 기본값을 검증기로 검사 후 전달
                    return validator(default_val)
                return ""
                
            # 필수 항목인데 빈 값을 넣은 경우 에러 유발
            if not user_input and not optional:
                raise ValueError("이 항목은 비워둘 수 없는 필수 항목입니다.")
                
            # 검증기를 통과하면 반환
            return validator(user_input)
            
        except ValueError as e:
            # 검증 실패 시 친절하게 한글 에러 문구와 힌트 가이드를 보여주고 입력을 다시 받습니다.
            print(f"  └ [오류] {e}")
            print("  └ [힌트] 입력 형식을 다시 확인하시고 올바른 값을 적어주세요.\n")


@handle_errors_gracefully # 예기치 못한 전체 프로세스 에러를 깔끔하게 다듬는 데코레이터 적용!
def run_cli() -> None:
    """
    명령어 인자를 파싱하고 가계부 비즈니스 서비스로 연결해 주는 진입로 함수입니다.
    """
    service = BudgetService()
    
    # 1. 메인 파서 정의 (명령어 도움말 설계)
    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="★ 스마트 가계부 콘솔 서비스 (Antigravity 설계) ★",
        epilog="상세 명령에 대한 도움말은 '명령어 --help'를 입력하세요."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="실행할 명령어를 선택해 주세요.")

    # -------------------------------------------------------------
    # 2. 서브커맨드 설정
    # -------------------------------------------------------------

    # [add] 거래 추가
    subparsers.add_parser("add", help="대화형으로 새로운 지출/수입 내역을 추가합니다.")

    # [list] 거래 목록 조회
    list_parser = subparsers.add_parser("list", help="최신순 가계부 거래 리스트를 한눈에 조회합니다.")
    list_parser.add_argument("--limit", type=int, default=None, help="출력할 최대 거래 건수를 한정합니다.")

    # [search] 거래 상세 검색
    search_parser = subparsers.add_parser("search", help="다양한 필터로 가계부 거래를 정밀 검색합니다.")
    search_parser.add_argument("--from", dest="from_date", help="시작 날짜 지정 (YYYY-MM-DD)")
    search_parser.add_argument("--to", dest="to_date", help="종료 날짜 지정 (YYYY-MM-DD)")
    search_parser.add_argument("--category", help="카테고리 필터 지정")
    search_parser.add_argument("--type", help="거래 분류 지정 (income / expense)")
    search_parser.add_argument("--q", dest="keyword", help="메모에 들어갈 키워드 검색")
    search_parser.add_argument("--tag", help="지정된 해시태그 검색")

    # [summary] 월별 통계 분석 및 요약
    summary_parser = subparsers.add_parser("summary", help="해당 월의 예산, 수입/지출 통계 및 지출 랭킹을 산출합니다.")
    summary_parser.add_argument("--month", required=True, help="조회할 년월 지정 (YYYY-MM)")
    summary_parser.add_argument("--top", type=int, default=3, help="출력할 최고 지출 카테고리 개수 (기본값: 3)")

    # [budget] 월별 예산 관리
    budget_parser = subparsers.add_parser("budget", help="월별 예산을 설정하거나 파악합니다.")
    budget_sub = budget_parser.add_subparsers(dest="budget_command")
    set_parser = budget_sub.add_parser("set", help="해당 년월에 대한 한도 예산을 저장합니다.")
    set_parser.add_argument("--month", required=True, help="예산을 설정할 년월 (YYYY-MM)")
    set_parser.add_argument("--amount", required=True, help="설정할 총 예산액 (양의 정수)")

    # [category] 카테고리 사전 정의 관리
    category_parser = subparsers.add_parser("category", help="가계부 카테고리(분류) 항목을 조율합니다.")
    cat_sub = category_parser.add_subparsers(dest="category_command")
    cat_sub.add_parser("add", help="새로운 카테고리를 사전에 추가합니다.")
    cat_sub.add_parser("list", help="사용 가능한 모든 카테고리 목록을 살펴봅니다.")
    cat_remove = cat_sub.add_parser("remove", help="특정 카테고리를 목록에서 삭제합니다.")
    cat_remove.add_argument("--fallback", help="기존 연관 거래를 이관해 줄 대체 카테고리명")

    # [update] 거래 정보 수정 (안 B: 대화형 흐름 고정)
    subparsers.add_parser("update", help="특정 거래의 내용을 대화형(안 B)으로 안전하게 수정합니다.")

    # [delete] 거래 삭제
    delete_parser = subparsers.add_parser("delete", help="선택한 거래 내역을 삭제합니다.")
    delete_parser.add_argument("--id", required=True, help="삭제하려는 거래의 고유 ID (예: TX-000001)")

    # [backup] 보너스 백업 실행
    subparsers.add_parser("backup", help="[보너스] 현재 저장된 가계부 파일 전체를 ZIP 압축 파일로 보관합니다.")

    # [recurring] 보너스 정기 반복 등록 관리
    rec_parser = subparsers.add_parser("recurring", help="[보너스] 매달 정기적으로 나가는 고정 수입/지출을 제어합니다.")
    rec_sub = rec_parser.add_subparsers(dest="rec_command")
    rec_sub.add_parser("add", help="매월 지정된 일자에 자동 발생할 반복 거래 규칙을 추가합니다.")
    rec_sub.add_parser("list", help="등록된 정기 반복 거래 규칙 목록을 표시합니다.")
    rec_remove = rec_sub.add_parser("remove", help="정기 반복 규칙을 제거합니다.")
    rec_remove.add_argument("--id", required=True, help="삭제할 규칙 고유 ID (예: REC-000001)")
    rec_gen = rec_sub.add_parser("generate", help="선택한 월에 아직 실행되지 않은 반복 규칙 데이터를 일괄 자동 생성합니다.")
    rec_gen.add_argument("--month", required=True, help="자동 생성 대상 년월 (YYYY-MM)")

    # [import] CSV 파일 일괄 가져오기
    import_parser = subparsers.add_parser("import", help="외부 CSV 파일을 분석하여 가계부에 거래 데이터를 넣습니다.")
    import_parser.add_argument("--from", dest="csv_path", required=True, help="가져올 원본 CSV 파일의 경로")

    # [export] 조건부 CSV 백업 내보내기
    export_parser = subparsers.add_parser("export", help="검색 조건에 맞는 거래 데이터를 CSV 파일로 안전하게 백업합니다.")
    export_parser.add_argument("--out", required=True, help="저장할 대상 CSV 파일명")
    export_parser.add_argument("--month", help="내보낼 특정 월 (YYYY-MM)")
    export_parser.add_argument("--from", dest="from_date", help="시작 기간 지정 (YYYY-MM-DD)")
    export_parser.add_argument("--to", dest="to_date", help="종료 기간 지정 (YYYY-MM-DD)")

    # -------------------------------------------------------------
    # 3. 매개변수 바인딩 및 분기 처리
    # -------------------------------------------------------------
    args = parser.parse_args()

    # 아무 명령어도 없이 그냥 실행한 경우 가이드 도움말 보여주기
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # -------------------------------------------------------------
    # 3.1 거래 추가 (add) - 대화형
    # -------------------------------------------------------------
    if args.command == "add":
        print("\n=== [거래 추가 진행] 대화형 가이드를 시작합니다 ===")
        date = prompt_interactive("1. 날짜(YYYY-MM-DD): ", validate_date)
        type_str = prompt_interactive("2. 타입(income/expense): ", validate_type)
        
        # 가독성을 위해 카테고리 힌트를 출력해 줍니다.
        cats = [c.name for c in service.list_categories()]
        print(f"  * 현재 선택 가능 카테고리: {cats}")
        
        # 카테고리 검증용 람다
        def cat_validator(x: str) -> str:
            if not service.cat_repo.exists(x):
                raise ValueError(f"'{x}' 카테고리는 존재하지 않습니다. 카테고리 목록에 있는 값을 입력하세요.")
            return x
            
        category = prompt_interactive("3. 카테고리: ", cat_validator)
        amount = prompt_interactive("4. 금액(양수): ", validate_amount)
        memo = prompt_interactive("5. 메모(선택 - 없을 시 그냥 엔터): ", lambda x: x, optional=True)
        tags_raw = prompt_interactive("6. 태그(쉼표 구분 선택 - 없을 시 그냥 엔터): ", lambda x: x, optional=True)
        
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        
        tx_id = service.add_transaction(
            date=date,
            type_str=type_str,
            category=category,
            amount=amount,
            memo=memo,
            tags=tags
        )
        print(f"\n[저장 완료] 성공적으로 추가되었습니다. 고유 발급 ID = {tx_id}")

    # -------------------------------------------------------------
    # 3.2 거래 목록 조회 (list)
    # -------------------------------------------------------------
    elif args.command == "list":
        # 제너레이터를 받아와 뷰 테이블로 예쁘게 렌더링
        tx_generator = service.list_transactions(limit=args.limit)
        
        headers = ["거래 ID", "날짜", "종류", "카테고리", "금액", "메모", "해시태그"]
        rows = []
        for tx in tx_generator:
            rows.append([
                tx.id,
                tx.date,
                "수입" if tx.type == "income" else "지출",
                tx.category,
                f"{tx.amount:,}원",
                tx.memo,
                ", ".join(tx.tags)
            ])
            
        alignments = ["center", "center", "center", "center", "right", "left", "left"]
        print(f"\n=== [거래 목록 전체 보기] (출력 제한: {args.limit if args.limit else '없음'}) ===")
        print_table(headers, rows, alignments)

    # -------------------------------------------------------------
    # 3.3 거래 검색 (search)
    # -------------------------------------------------------------
    elif args.command == "search":
        # 날짜 인자 유효성 임시 검사
        if args.from_date:
            validate_date(args.from_date)
        if args.to_date:
            validate_date(args.to_date)
            
        tx_generator = service.search_transactions(
            from_date=args.from_date,
            to_date=args.to_date,
            category=args.category,
            type_str=args.type,
            keyword=args.keyword,
            tag=args.tag
        )
        
        headers = ["거래 ID", "날짜", "종류", "카테고리", "금액", "메모", "해시태그"]
        rows = []
        for tx in tx_generator:
            rows.append([
                tx.id,
                tx.date,
                "수입" if tx.type == "income" else "지출",
                tx.category,
                f"{tx.amount:,}원",
                tx.memo,
                ", ".join(tx.tags)
            ])
            
        alignments = ["center", "center", "center", "center", "right", "left", "left"]
        print(f"\n=== [거래 검색 결과] ===")
        print_table(headers, rows, alignments)

    # -------------------------------------------------------------
    # 3.4 월별 통계 및 예산 대조 (summary)
    # -------------------------------------------------------------
    elif args.command == "summary":
        validate_month(args.month)
        summary = service.get_monthly_summary(args.month, top_n=args.top)
        
        if not summary["has_data"]:
            print(f"\n[안내] {args.month}에 입력된 가계부 거래 데이터가 존재하지 않습니다.")
            sys.exit(0)
            
        print(f"\n==========================================")
        print(f"       💰  {args.month} 재정 분석 리포트        ")
        print(f"==========================================")
        print(f" · 총 수입:  {summary['total_income']:,}원")
        print(f" · 총 지출:  {summary['total_expense']:,}원")
        print(f" · 순 잔액:  {summary['balance']:,}원")
        
        if summary["budget_amount"] is not None:
            print(f"------------------------------------------")
            print(f" · 설정 예산: {summary['budget_amount']:,}원")
            print(f" · 사용률:    {summary['usage_percent']:.1f}%")
            if summary["is_over_budget"]:
                print(f" ⚠️  [경고] 이번 달 설정한 총 예산을 초과하셨습니다!")
            else:
                print(f" ✅  안정적인 예산 범위 내 지출을 유지하고 계십니다.")
        else:
            print(f"------------------------------------------")
            print(f" · [알림] 해당 월에 설정된 예산 정보가 없습니다.")
            print(f"   (힌트: budget set --month {args.month} --amount [금액])")
            
        print(f"==========================================")
        print(f"       🔥 지출 TOP {args.top} 카테고리 랭킹      ")
        print(f"==========================================")
        for idx, (cat_name, amt) in enumerate(summary["top_categories"], start=1):
            print(f"  {idx}위) {cat_name} : {amt:,}원")
        if not summary["top_categories"]:
            print("  - 지출 항목이 전혀 존재하지 않습니다.")
        print(f"==========================================\n")

    # -------------------------------------------------------------
    # 3.5 예산 등록 (budget set)
    # -------------------------------------------------------------
    elif args.command == "budget":
        if args.budget_command == "set":
            val_month = validate_month(args.month)
            val_amount = validate_amount(args.amount)
            service.set_budget(val_month, val_amount)
            print(f"\n[저장 완료] {val_month} 예산 한도가 {val_amount:,}원으로 책정되어 저장되었습니다.")
        else:
            print("[안내] 상세한 사용을 위해 'python -m budget_app budget set --help'를 참고하세요.")

    # -------------------------------------------------------------
    # 3.6 카테고리 관리 (category add/list/remove)
    # -------------------------------------------------------------
    elif args.command == "category":
        if args.category_command == "add":
            print("\n=== [신규 카테고리 추가] ===")
            cat_name = prompt_interactive("새 카테고리명: ", lambda x: x)
            added = service.add_category(cat_name)
            if added:
                print(f"[저장 완료] 카테고리 '{cat_name}'이(가) 신규 등록되었습니다.")
            else:
                print(f"[경고] '{cat_name}'은(는) 이미 카테고리 사전에 존재합니다.")
                
        elif args.category_command == "list":
            print("\n=== [사용 가능 카테고리 일람] ===")
            for c in service.list_categories():
                print(f" - {c.name}")
                
        elif args.category_command == "remove":
            print("\n=== [카테고리 삭제 진행] ===")
            # 삭제할 이름을 사용자에게 직접 유도합니다.
            cat_name = prompt_interactive("삭제할 카테고리명: ", lambda x: x)
            
            # CLI에서 직접 제거 시도
            success, message = service.remove_category(cat_name, fallback_category=args.fallback)
            if success:
                print(f"\n[성공] {message}")
            else:
                print(f"\n[실패] {message}")
                # 대체 카테고리가 비어 있어서 실패했을 경우 대화형으로 한 번 더 대안 제공
                if "대체할 카테고리" in message:
                    print("\n[대화형 구조 복구]")
                    fallback = prompt_interactive("거래를 이관해 줄 대체 카테고리명: ", lambda x: x)
                    success_sec, msg_sec = service.remove_category(cat_name, fallback_category=fallback)
                    if success_sec:
                        print(f"[성공] {msg_sec}")
                    else:
                        print(f"[실패] {msg_sec}")
        else:
            print("[안내] 상세 명령은 'python -m budget_app category {add|list|remove} --help'를 참고하세요.")

    # -------------------------------------------------------------
    # 3.7 거래 수정 (update) - 대화형 고정 (안 B)
    # -------------------------------------------------------------
    elif args.command == "update":
        print("\n=== [거래 내역 대화형 수정] (안 B 방식 작동) ===")
        tx_id = prompt_interactive("수정할 거래 고유 ID를 입력해 주세요: ", lambda x: x)
        
        # 기존 거래를 검색합니다.
        existing_tx = None
        for tx in service.tx_repo.find_all_stream():
            if tx.id == tx_id:
                existing_tx = tx
                break
                
        if not existing_tx:
            print(f"[오류] 입력하신 ID '{tx_id}'에 해당하는 거래를 데이터에서 검색할 수 없습니다.")
            sys.exit(1)
            
        print(f"\n거래 검색 성공! 내용을 수정하려면 값을 새로 적으시고, 그대로 유지하려면 [엔터]를 치세요.\n")
        
        # 1. 날짜 수정 유도
        new_date = prompt_interactive(
            f"날짜 [현재값: {existing_tx.date}] 수정할 값 입력 (형식: YYYY-MM-DD): ",
            validate_date,
            optional=True,
            default_val=existing_tx.date
        )
        
        # 2. 거래 타입 수정 유도
        new_type = prompt_interactive(
            f"타입 [현재값: {existing_tx.type}] 수정할 값 입력 (income / expense): ",
            validate_type,
            optional=True,
            default_val=existing_tx.type
        )
        
        # 3. 카테고리 수정 유도 (등록 카테고리 중 선택 유도)
        cats = [c.name for c in service.list_categories()]
        print(f"  * 현재 선택 가능 카테고리: {cats}")
        
        def cat_validator(x: str) -> str:
            if not service.cat_repo.exists(x):
                raise ValueError(f"'{x}' 카테고리는 존재하지 않습니다. 목록에 등록된 분류를 기입하세요.")
            return x
            
        new_category = prompt_interactive(
            f"카테고리 [현재값: {existing_tx.category}] 수정할 값 입력: ",
            cat_validator,
            optional=True,
            default_val=existing_tx.category
        )
        
        # 4. 금액 수정 유도
        new_amount = prompt_interactive(
            f"금액 [현재값: {existing_tx.amount:,}원] 수정할 값 입력 (양수 숫자): ",
            validate_amount,
            optional=True,
            default_val=str(existing_tx.amount)
        )
        
        # 5. 메모 수정 유도
        new_memo = prompt_interactive(
            f"메모 [현재값: '{existing_tx.memo}'] 수정할 값 입력 (없애려면 '-' 입력): ",
            lambda x: "" if x == "-" else x,
            optional=True,
            default_val=existing_tx.memo
        )
        
        # 6. 해시태그 수정 유도
        current_tags_str = ", ".join(existing_tx.tags)
        new_tags_raw = prompt_interactive(
            f"태그 [현재값: {current_tags_str}] 수정할 값 입력 (쉼표로 구분, 없애려면 '-' 입력): ",
            lambda x: [] if x == "-" else x,
            optional=True,
            default_val=current_tags_str
        )
        
        if isinstance(new_tags_raw, str):
            new_tags = [t.strip() for t in new_tags_raw.split(",") if t.strip()]
        else:
            new_tags = []
            
        # 수정 객체 조립 후 영구 변경 호출
        updated = Transaction(
            id=existing_tx.id,
            date=new_date,
            type=new_type,
            category=new_category,
            amount=new_amount,
            memo=new_memo,
            tags=new_tags
        )
        
        success = service.update_transaction(updated)
        if success:
            print(f"\n[수정 완료] 거래 '{tx_id}' 정보가 무결하게 변경되어 안전하게 기록되었습니다!")
        else:
            print(f"\n[실패] 데이터베이스 수정 중 동기화 문제가 나타났습니다.")

    # -------------------------------------------------------------
    # 3.8 거래 삭제 (delete)
    # -------------------------------------------------------------
    elif args.command == "delete":
        deleted = service.delete_transaction(args.id)
        if deleted:
            print(f"\n[삭제 완료] 요청하신 거래 ID '{args.id}' 가 안전하게 제거되었습니다.")
        else:
            print(f"\n[오류] 요청하신 거래 ID '{args.id}' 는 존재하지 않는 데이터이거나 이미 삭제되었습니다.")
            sys.exit(1)

    # -------------------------------------------------------------
    # 3.9 [보너스] 백업 (backup)
    # -------------------------------------------------------------
    elif args.command == "backup":
        print("\n=== [가계부 백업 데이터 압축 파일 생성 시작] ===")
        backup_path = service.backup_data()
        print(f"[완료] 데이터가 완벽히 압축 저장되었습니다: {backup_path}")

    # -------------------------------------------------------------
    # 3.10 [보너스] 정기 반복 설정 (recurring)
    # -------------------------------------------------------------
    elif args.command == "recurring":
        if args.rec_command == "add":
            print("\n=== [매달 고정 반복 규칙 등록] ===")
            day = prompt_interactive("1. 매달 발생할 일자 (1~31일): ", lambda x: int(x) if 1 <= int(x) <= 31 else ValueError("일자는 1에서 31 사이여야 합니다."))
            type_str = prompt_interactive("2. 타입 (income / expense): ", validate_type)
            
            # 카테고리 검사
            cats = [c.name for c in service.list_categories()]
            print(f"  * 현재 선택 가능 카테고리: {cats}")
            def cat_validator(x: str) -> str:
                if not service.cat_repo.exists(x):
                    raise ValueError(f"'{x}' 카테고리는 존재하지 않습니다.")
                return x
            category = prompt_interactive("3. 카테고리: ", cat_validator)
            amount = prompt_interactive("4. 금액: ", validate_amount)
            memo = prompt_interactive("5. 메모(선택): ", lambda x: x, optional=True)
            tags_raw = prompt_interactive("6. 태그(쉼표 구분 선택): ", lambda x: x, optional=True)
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
            
            rule_id = service.add_recurring_rule(
                day_of_month=day,
                type_str=type_str,
                category=category,
                amount=amount,
                memo=memo,
                tags=tags
            )
            print(f"\n[저장 완료] 정기 반복 거래 규칙이 생성되었습니다. 규칙 ID = {rule_id}")
            
        elif args.rec_command == "list":
            rules = service.list_recurring_rules()
            headers = ["규칙 ID", "발생일", "종류", "카테고리", "금액", "메모"]
            rows = []
            for r in rules:
                rows.append([
                    r.id,
                    f"매달 {r.day_of_month}일",
                    "수입" if r.type == "income" else "지출",
                    r.category,
                    f"{r.amount:,}원",
                    r.memo
                ])
            alignments = ["center", "center", "center", "center", "right", "left"]
            print("\n=== [등록된 정기 반복 거래 규칙 일람] ===")
            print_table(headers, rows, alignments)
            
        elif args.rec_command == "remove":
            success = service.remove_recurring_rule(args.id)
            if success:
                print(f"\n[삭제 완료] 정기 반복 규칙 '{args.id}' 가 제거되었습니다.")
            else:
                print(f"\n[실패] 존재하지 않는 정기 반복 규칙 ID 입니다.")
                sys.exit(1)
                
        elif args.rec_command == "generate":
            validate_month(args.month)
            print(f"\n=== [{args.month} 정기 반복 거래 자동 일괄 대조 및 생성 작동] ===")
            succ, skip = service.generate_recurring_transactions(args.month)
            print(f"[완료] 자동 생성 완료 = {succ}건, 기 생성 건너뜀(중복 방어) = {skip}건")
        else:
            print("[안내] 상세 명령은 'python -m budget_app recurring {add|list|remove|generate} --help'를 참고하세요.")

    # -------------------------------------------------------------
    # 3.11 가져오기 (import)
    # -------------------------------------------------------------
    elif args.command == "import":
        print(f"\n=== [외부 CSV 가계부 일괄 불러오기 시작] ===")
        print(f" 분석 파일: {args.csv_path}")
        
        success, skipped, reports = service.import_from_csv(args.csv_path)
        
        print(f"\n[가져오기 종료]")
        print(f" · 성공적으로 저장 완료된 데이터: {success}건")
        print(f" · 스킵(데이터 정밀 검사 탈락)된 데이터: {skipped}건")
        
        if reports:
            print("\n🚨 [스킵 데이터 상세 리포트]")
            for rep in reports:
                print(f"  {rep}")
            print("\n[힌트] 스킵된 줄의 데이터를 확인하신 후 올바르게 교정하여 CSV를 다시 불러오시길 권장합니다.")

    # -------------------------------------------------------------
    # 3.12 내보내기 (export)
    # -------------------------------------------------------------
    elif args.command == "export":
        # 날짜 포맷 임시 검증
        if args.month:
            validate_month(args.month)
        if args.from_date:
            validate_date(args.from_date)
        if args.to_date:
            validate_date(args.to_date)
            
        print(f"\n=== [조건별 가계부 CSV 내보내기 시작] ===")
        count = service.export_to_csv(
            out_filepath=args.out,
            month=args.month,
            from_date=args.from_date,
            to_date=args.to_date
        )
        print(f"[완료] '{args.out}' 경로에 안전하게 저장되었습니다. (추출 건수: {count}건)")
