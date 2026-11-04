# [도구상자 가져오기]
# json: 파이썬 데이터를 텍스트 파일(JSON 형식)로 저장하고 읽기 위해 필요합니다.
import json
# os: 컴퓨터의 운영체제(Operating System)와 소통하기 위해 필요합니다. (예: 파일이 진짜 있는지 확인)
import os

# =====================================================================
# [1] Quiz 클래스: "퀴즈 한 문제"를 만들어내는 붕어빵 틀 (설계도)
# =====================================================================
class Quiz:
    # __init__ (초기화 함수): 이 틀로 붕어빵(퀴즈)을 처음 구울 때, 어떤 재료가 필요한지 정합니다.
    # self는 '만들어진 나 자신'을 뜻합니다.
    def __init__(self, question, choices, answer):
        self.question = question  # 문제 내용 (예: "파이썬 창시자는?")
        self.choices = choices    # 선택지 4개가 들어있는 리스트 (예: ["가", "나", "다", "라"])
        self.answer = answer      # 정답 번호 (예: 1)

    # 파이썬의 '객체(붕어빵)' 상태로는 JSON 파일에 바로 저장할 수 없습니다.
    # 그래서 JSON이 이해할 수 있는 형태인 '딕셔너리(사전 형태, {키: 값})'로 변환해 주는 함수입니다.
    def to_dict(self):
        return {
            "question": self.question,
            "choices": self.choices,
            "answer": self.answer
        }

    # 사용자에게 이 퀴즈를 화면에 예쁘게 보여주는 함수입니다.
    def display(self, index):
        # index는 '몇 번 문제인지' 알려주는 숫자입니다.
        print(f"\n----------------------------------------")
        print(f"[문제 {index}] {self.question}")
        
        # enumerate(리스트, 1): 리스트 안의 내용물(choice)을 꺼낼 때, 숫자(i)를 1부터 매겨줍니다.
        for i, choice in enumerate(self.choices, 1):
            print(f"{i}. {choice}")


# =====================================================================
# [2] QuizGame 클래스: 게임 전체를 관리하는 '점장님' (관리자)
# =====================================================================
class QuizGame:
    # 점장님이 출근했을 때 처음 셋팅하는 것들입니다.
    def __init__(self):
        self.quizzes =[]        # 퀴즈들을 담아둘 빈 장바구니(리스트)
        self.best_score = 0      # 최고 점수는 0점으로 시작
        self.file_path = "state.json" # 데이터를 저장할 파일의 이름

    # 장바구니(quizzes)에 새로운 퀴즈 하나를 쏙 넣는 함수입니다.
    def add_quiz(self, quiz):
        self.quizzes.append(quiz)

    # -----------------------------------------------------------------
    #[데이터 저장 기능] 컴퓨터를 꺼도 데이터가 날아가지 않게 파일에 씁니다.
    # -----------------------------------------------------------------
    def save_data(self):
        try: # 에러가 날지도 모르니 일단 조심스럽게 시도해 봅니다.
            # 저장할 데이터를 딕셔너리로 크게 묶습니다.
            data = {
                "best_score": self.best_score,
                # 리스트 안에 있는 모든 퀴즈 객체를 to_dict() 함수를 써서 딕셔너리로 바꿉니다.
                # (파이썬의 '리스트 내포'라는 문법입니다. for문을 한 줄로 줄여 쓴 것!)
                "quizzes":[q.to_dict() for q in self.quizzes]
            }
            # open(파일이름, "w"): 파일을 쓰기(Write) 모드로 엽니다. (with를 쓰면 자동으로 닫아줘서 안전해요)
            # encoding="utf-8": 한글이 깨지지 않게 해주는 마법의 주문입니다.
            with open(self.file_path, "w", encoding="utf-8") as f:
                # json.dump: 파이썬 데이터를 JSON 파일에 밀어 넣습니다.
                # ensure_ascii=False: 역시 한글 깨짐 방지용. indent=4: 엔터를 쳐서 예쁘게 정렬해 줍니다.
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:

            # try 안에서 뭔가 에러가 나면 프로그램이 죽지 않고 이곳으로 와서 에러 이유(e)를 알려줍니다.
            print(f"\n⚠️ 저장 중 오류 발생: {e}")

    # -----------------------------------------------------------------
    # [데이터 불러오기 기능] 프로그램이 켜질 때 예전 기록을 가져옵니다.
    # -----------------------------------------------------------------
    def load_data(self):
        # os.path.exists: "이 경로에 파일이 진짜 존재해?" 라고 묻습니다.
        if not os.path.exists(self.file_path):
            print("\n📂 저장된 파일이 없어 기본 퀴즈를 로드합니다.")
            self.set_default_quizzes() # 파일이 없으면 기본 문제를 깔아줍니다.
            return # 볼일 끝났으니 함수 종료!

        try: # 파일이 있다면 조심스럽게 열어봅니다.
            with open(self.file_path, "r", encoding="utf-8") as f: # "r"은 읽기(Read) 모드입니다.
                data = json.load(f) # JSON 파일의 글자들을 파이썬 데이터로 변환해서 가져옵니다.
                
                # 데이터에서 최고 점수를 가져오고, 혹시 내용이 없으면 0으로 셋팅합니다.
                self.best_score = data.get("best_score", 0)
                
                # 퀴즈 목록을 비운 다음, 파일에 있던 퀴즈 내용들을 다시 'Quiz 클래스(붕어빵)'로 만들어서 넣습니다.
                self.quizzes =[]
                for q_data in data.get("quizzes",[]):
                    # 파일에 있던 질문, 선택지, 정답을 꺼내서 새로운 Quiz를 만듭니다.
                    self.quizzes.append(Quiz(q_data["question"], q_data["choices"], q_data["answer"]))
            print(f"\n✅ 데이터를 불러왔습니다. (퀴즈 {len(self.quizzes)}개, 최고점수 {self.best_score}점)")
            
        except (json.JSONDecodeError, KeyError):
            # 파일 내용이 누군가 건드려서 망가졌을 때(글자가 깨졌을 때 등) 대처하는 곳입니다.
            print("\n⚠️ 파일이 손상되어 초기화합니다.")
            self.set_default_quizzes()
        except Exception as e:
            print(f"\n⚠️ 불러오기 중 오류 발생: {e}")

    # 파일이 없거나 망가졌을 때, 프로그램이 텅 비어있지 않게 5문제를 기본으로 채워줍니다.
    def set_default_quizzes(self):
        self.quizzes = [
            Quiz("파이썬의 창시자는 누구일까요?",["귀도 반 로섬", "제임스 고슬링", "빌 일론 머스크", "스티브 잡스"], 1),
            Quiz("리스트에 요소를 추가하는 메서드는?",["add()", "append()", "push()", "insert_end()"], 2),
            Quiz("다음 중 기본 자료형이 아닌 것은?", ["int", "str", "boolean", "dictionary"], 4),
            Quiz("반복문을 중단할 때 사용하는 키워드는?", ["stop", "exit", "break", "continue"], 3),
            Quiz("출력을 위해 사용하는 함수는?",["input()", "print()", "show()", "write()"], 2)
        ]
        self.save_data() # 채워 넣은 다음, 나중을 위해 바로 파일로 저장해 둡니다.

    # -----------------------------------------------------------------
    #[메뉴 1번: 퀴즈 풀기]
    # -----------------------------------------------------------------
    def play(self):
        if not self.quizzes: return # 퀴즈가 0개면 풀 수 없으니 그냥 돌아갑니다.
        
        score = 0 # 현재 내 점수
        # 등록된 퀴즈들을 1번부터 순서대로 하나씩 꺼내옵니다.
        for i, quiz in enumerate(self.quizzes, 1):
            quiz.display(i) # 아까 만든 퀴즈 화면에 보여주기 기능 실행!
            
            # 올바른 정답을 입력할 때까지 사용자를 무한 루프(while True)에 가둡니다.
            while True:
                # strip(): 사용자가 실수로 스페이스바를 누른 걸 없애줍니다. (예: " 1 " -> "1")
                user_input = input("정답 입력 (1-4): ").strip()
                # 1, 2, 3, 4 중 하나를 쳤으면 반복문을 탈출(break)합니다.
                if user_input in['1', '2', '3', '4']: 
                    break
                # 이상한 걸 쳤으면 이 경고문을 띄우고 다시 위로 올라가서 입력을 요구합니다.
                print("⚠️ 1~4 사이 숫자만 입력하세요.")
            
            # 입력한 글자("1")를 숫자(1)로 바꿔서 진짜 정답과 비교합니다.
            if int(user_input) == quiz.answer:
                print("✅ 정답입니다!")
                score += 1 # 점수 1점 획득!
            else:
                print(f"❌ 오답입니다. (정답: {quiz.answer}번)")
        
        # 반복문이 끝나면(퀴즈를 다 풀면) 최종 결과를 보여줍니다.
        print(f"\n🏆 결과: {len(self.quizzes)}개 중 {score}개 정답!")
        
        # 방금 얻은 점수가 내 역대 최고 점수보다 높다면?
        if score > self.best_score:
            self.best_score = score # 최고 점수 갈아치우기
            print("🎉 새로운 최고 점수입니다!")
            self.save_data() # 최고 점수가 바뀌었으니 파일에 저장합니다.

    # -----------------------------------------------------------------
    # [메뉴 2번: 퀴즈 추가]
    # -----------------------------------------------------------------
    def add_new_quiz_menu(self):
        print("\n📌 새로운 퀴즈 추가")
        q = input("문제: ").strip()
        
        # 선택지 4개를 입력받아 바로 리스트로 만듭니다. (for문을 한 줄로 압축한 것)
        c =[input(f"선택지 {i}: ").strip() for i in range(1, 5)]
        
        # 정답도 1~4 사이의 숫자가 들어올 때까지 무한 루프로 검사합니다.
        while True:
            ans = input("정답 (1-4): ").strip()
            if ans in['1', '2', '3', '4']: 
                break
                
        # 완벽한 재료가 다 모였으니, 새로운 Quiz 붕어빵을 구워서 장바구니에 넣습니다.
        self.add_quiz(Quiz(q, c, int(ans)))
        self.save_data() # 퀴즈가 추가되었으니 즉시 저장합니다.
        print("✅ 추가 완료!")

    # -----------------------------------------------------------------
    # [메뉴 3번: 퀴즈 목록 보기]
    # -----------------------------------------------------------------
    def list_quizzes(self):
        print(f"\n📋 퀴즈 목록 ({len(self.quizzes)}개)")
        # 퀴즈들을 순서대로 꺼내서 '문제 내용(question)'만 쭉 출력합니다.
        for i, quiz in enumerate(self.quizzes, 1):
            print(f"[{i}] {quiz.question}")


# =====================================================================
# [3] 메인 실행부: 프로그램이 시작되는 곳
# =====================================================================
def main():
    game = QuizGame() # 점장님 출근!
    game.load_data()  # 출근하자마자 예전 서류(json 파일)부터 챙겨서 읽습니다.

    try:
        # 영원히 돌아가는 메인 메뉴판입니다. (사용자가 5를 누르기 전까지)
        while True:
            print("\n" + "="*40)
            print("        🎯 나만의 퀴즈 게임 🎯")
            print("="*40)
            print("1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n5. 종료")
            print("="*40)
            choice = input("선택: ").strip()

            # 사용자의 선택에 따라 점장님(game)에게 일을 시킵니다.
            if choice == '1': game.play()
            elif choice == '2': game.add_new_quiz_menu()
            elif choice == '3': game.list_quizzes()
            elif choice == '4': print(f"\n🏆 최고 점수: {game.best_score}점")
            elif choice == '5': 
                print("👋 종료합니다.")
                break # break를 만나면 while 무한 루프가 깨지고 프로그램이 끝납니다.
            else: 
                print(f"⚠️ '{choice}'은(는) 잘못된 입력입니다.")

    # 사용자가 강제로 Ctrl+C를 눌러서 끄려고 할 때, 빨간 에러 대신 이걸 실행합니다.
    except (KeyboardInterrupt, EOFError):
        game.save_data() # 끄기 전에 지금까지의 상황을 안전하게 저장해 둡니다.
        print("\n\n🛑 안전하게 종료되었습니다.")

# 이 파이썬 파일이 "직접 실행"되었을 때만 main() 함수를 작동시키라는 파이썬의 규칙입니다.
if __name__ == "__main__":
    main()