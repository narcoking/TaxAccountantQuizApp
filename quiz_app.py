import customtkinter as ctk
import tkinter.messagebox as tkmb
import json
import os
import random
import time

# ==============================================================================
# CustomTkinter 기반 세무사 시험 퀴즈 프로그램 (홈 화면 및 과목 선택, 경과 시간 타이머 기능 추가)
# - 시작 시 과목 선택 화면 표시
# - 각 과목 버튼 클릭 시 해당 퀴즈 페이지로 전환
# - 문제와 보기가 잘리지 않고 스크롤 가능하도록 UI 개선.
# - 문제 무작위 출제 및 동일 세션 내 중복 출제 방지.
# - 선택지 글자색 검정으로 변경.
# - 퀴즈 통계 (총 풀이, 맞은 문제, 틀린 문제) 표시.
# - 오답 노트 기능 (틀린 문제만 다시 풀기).
# - '퀴즈 끝내기' 버튼을 통해 언제든지 퀴즈 종료 및 오답 노트 접근 가능.
# - 퀴즈 종료 후 '홈 화면으로' 돌아가는 버튼 추가.
# - **문제 풀이 경과 시간 타이머 추가.**
# - **메인 화면에 '1. 문제 풀기', '2. 모의고사' 메뉴 추가.**
# - **'2. 모의고사' 선택 시 '1교시', '2교시' 버튼 화면으로 전환.**
# - **[수정] 하위 프레임에 QuizApp 컨트롤러 인스턴스 올바르게 전달.**
# - **[추가] 모의고사 기능 (1교시/2교시, 80문제, 최종 결과, 오답 노트, 점수 환산).**
# - **[수정] MockQuizPage에 is_review_mode 속성 초기화.**
# - **[수정] 보기 텍스트가 길 경우 40글자마다 줄바꿈 되도록 텍스트 처리 로직 추가.**
# ==============================================================================


class QuizApp(ctk.CTk):
    """
    메인 애플리케이션 클래스.
    여러 페이지(프레임)를 관리하고 페이지 전환을 제어합니다.
    """

    def __init__(self):
        super().__init__()
        self.title("세무사 시험 대비 퀴즈")
        self.geometry("900x880")
        self.resizable(False, False)

        # 메인 윈도우의 그리드 구성: 페이지 프레임이 전체 공간을 차지하도록 설정
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.frames = {}  # 각 페이지(프레임) 인스턴스를 저장할 딕셔너리
        self._create_frames()  # 페이지 프레임 생성
        self._show_frame("StartPage")  # 초기 화면으로 StartPage 표시

    def _create_frames(self):
        """
        애플리케이션의 모든 페이지 프레임을 생성하고 딕셔너리에 저장합니다.
        """
        # StartPage 생성 및 그리드에 배치 (일단 숨겨진 상태로)
        self.start_page = StartPage(parent=self, controller=self)
        self.frames["StartPage"] = self.start_page
        self.start_page.grid(
            row=0, column=0, sticky="nsew", padx=20, pady=20
        )  # StartPage가 중앙에 오도록 padx/pady 추가

        # QuizPage와 MockQuizPage는 과목/세션 선택 시 동적으로 생성되므로, 여기서는 초기화하지 않습니다.
        self.quiz_page = None
        self.mock_quiz_page = None

    def _show_frame(
        self, page_name, subject_file=None, subject_title=None, session_type=None
    ):
        """
        지정된 페이지(프레임)를 표시하고 다른 페이지를 숨깁니다.
        QuizPage나 MockQuizPage로 전환할 경우 새로운 인스턴스를 생성합니다.
        """
        # 모든 프레임을 숨깁니다.
        for frame in self.frames.values():
            # 기존 QuizPage나 MockQuizPage가 남아있다면 타이머를 멈추도록 요청
            if isinstance(frame, (QuizPage, MockQuizPage)) and hasattr(
                frame, "_stop_timer"
            ):
                frame._stop_timer()
            frame.grid_remove()

        # QuizPage로 전환하는 경우
        if page_name == "QuizPage":
            if "QuizPage" in self.frames:
                self.frames["QuizPage"].destroy()
                del self.frames["QuizPage"]

            self.quiz_page = QuizPage(
                parent=self,
                controller=self,
                subject_file=subject_file,
                subject_title=subject_title,
            )
            self.frames["QuizPage"] = self.quiz_page
            self.quiz_page.grid(row=0, column=0, sticky="nsew")

        # MockQuizPage로 전환하는 경우
        elif page_name == "MockQuizPage":
            if "MockQuizPage" in self.frames:
                self.frames["MockQuizPage"].destroy()
                del self.frames["MockQuizPage"]

            self.mock_quiz_page = MockQuizPage(
                parent=self,
                controller=self,
                session_type=session_type,
            )
            self.frames["MockQuizPage"] = self.mock_quiz_page
            self.mock_quiz_page.grid(row=0, column=0, sticky="nsew")

        # 요청된 프레임을 표시하고 맨 앞으로 가져옵니다.
        frame = self.frames[page_name]
        frame.grid()
        frame.tkraise()


class StartPage(ctk.CTkFrame):
    """
    퀴즈 시작 시 과목을 선택할 수 있는 홈 화면 프레임입니다.
    메인 메뉴(문제 풀기, 모의고사)와 그에 따른 하위 메뉴를 관리합니다.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")  # 투명 배경 설정
        self.controller = controller  # QuizApp 인스턴스 (메인 컨트롤러)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=1)  # Main menu buttons / Sub frames
        self.grid_rowconfigure(2, weight=1)  # Spacer for layout

        # 초기 제목 레이블
        self.title_label = ctk.CTkLabel(
            self,
            text="메뉴를 선택하세요",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#2C3E50",
        )
        self.title_label.grid(row=0, column=0, pady=40)

        # 메인 메뉴 버튼들을 담을 프레임
        self.main_menu_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_menu_frame.grid(row=1, column=0, sticky="nsew")
        self.main_menu_frame.grid_columnconfigure(0, weight=1)
        self.main_menu_frame.grid_rowconfigure(0, weight=1)
        self.main_menu_frame.grid_rowconfigure(1, weight=1)

        # '1. 문제 풀기' 버튼
        self.problem_solving_btn = ctk.CTkButton(
            self.main_menu_frame,
            text="1. 문제 풀기",
            command=self._show_problem_solving_menu,
            font=ctk.CTkFont(size=25, weight="bold"),
            height=70,
            corner_radius=12,
            fg_color="#3498DB",
            hover_color="#2980B9",
        )
        self.problem_solving_btn.grid(row=0, column=0, pady=15, padx=50, sticky="ew")

        # '2. 모의고사' 버튼
        self.mock_exam_btn = ctk.CTkButton(
            self.main_menu_frame,
            text="2. 모의고사",
            command=self._show_mock_exam_menu,
            font=ctk.CTkFont(size=25, weight="bold"),
            height=70,
            corner_radius=12,
            fg_color="#E67E22",  # Orange color
            hover_color="#D35400",
        )
        self.mock_exam_btn.grid(row=1, column=0, pady=15, padx=50, sticky="ew")

        # 하위 메뉴 프레임 (문제 풀기, 모의고사) 생성 및 숨기기
        # 중요 수정: controller에 메인 QuizApp 인스턴스 (self.controller) 전달
        self.problem_solving_sub_frame = ProblemSolvingSubFrame(
            parent=self, controller=self.controller
        )
        self.problem_solving_sub_frame.grid(
            row=1, column=0, sticky="nsew", padx=20, pady=20
        )
        self.problem_solving_sub_frame.grid_remove()  # 초기에는 숨김

        self.mock_exam_sub_frame = MockExamSubFrame(
            parent=self, controller=self.controller
        )
        self.mock_exam_sub_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.mock_exam_sub_frame.grid_remove()  # 초기에는 숨김

        self._show_main_menu()  # 시작 시 메인 메뉴 표시

    def _hide_all_sub_frames(self):
        """모든 하위 메뉴 프레임을 숨깁니다."""
        self.problem_solving_sub_frame.grid_remove()
        self.mock_exam_sub_frame.grid_remove()
        self.main_menu_frame.grid_remove()

    def _show_main_menu(self):
        """메인 메뉴 버튼들을 표시합니다."""
        self._hide_all_sub_frames()
        self.title_label.configure(text="메뉴를 선택하세요")
        self.main_menu_frame.grid()
        self.main_menu_frame.tkraise()

    def _show_problem_solving_menu(self):
        """문제 풀기 하위 메뉴를 표시합니다."""
        self._hide_all_sub_frames()
        self.title_label.configure(text="과목을 선택하세요 (문제 풀기)")
        self.problem_solving_sub_frame.grid()
        self.problem_solving_sub_frame.tkraise()

    def _show_mock_exam_menu(self):
        """모의고사 하위 메뉴를 표시합니다."""
        self._hide_all_sub_frames()
        self.title_label.configure(text="모의고사를 선택하세요")
        self.mock_exam_sub_frame.grid()
        self.mock_exam_sub_frame.tkraise()


class ProblemSolvingSubFrame(ctk.CTkFrame):
    """
    '문제 풀기'를 선택했을 때 나타나는 과목 선택 프레임입니다.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller  # 이제 QuizApp 인스턴스
        self.master_start_page = parent  # StartPage 인스턴스

        self.grid_columnconfigure(0, weight=1)
        for i in range(
            5
        ):  # For subject buttons and back button (4 subjects + 1 back button)
            self.grid_rowconfigure(i, weight=1)

        # 과목 버튼 데이터 (JSON 파일명과 과목명을 매핑)
        subjects = {
            "재정학": "questions_finance.json",
            "세법학개론": "questions_taxlaw.json",
            "회계학개론": "questions_accounting.json",
            "상법": "questions_commerciallaw.json",
        }

        # 각 과목 버튼 생성 및 배치
        for i, (subject_name, file_name) in enumerate(subjects.items()):
            button = ctk.CTkButton(
                self,
                text=subject_name,
                command=lambda sf=file_name, sn=subject_name: self._start_subject_quiz(
                    sf, sn
                ),
                font=ctk.CTkFont(size=25, weight="bold"),
                height=70,
                corner_radius=12,
                fg_color="#3498DB",  # 파란색 계열 버튼
                hover_color="#2980B9",
            )
            button.grid(
                row=i, column=0, pady=15, padx=50, sticky="ew"
            )  # 수직 여백 및 좌우 패딩 추가

        # 뒤로가기 버튼
        back_button = ctk.CTkButton(
            self,
            text="뒤로가기",
            command=self.master_start_page._show_main_menu,
            font=ctk.CTkFont(size=20, weight="bold"),
            height=50,
            corner_radius=12,
            fg_color="#7F8C8D",  # Grey
            hover_color="#6C7A89",
        )
        back_button.grid(row=len(subjects), column=0, pady=20, padx=50, sticky="ew")

    def _start_subject_quiz(self, subject_file, subject_name):
        """
        과목 버튼 클릭 시 해당 퀴즈를 시작합니다.
        """
        # self.controller는 이제 QuizApp 인스턴스이므로 _show_frame 호출 가능
        self.controller._show_frame(
            "QuizPage", subject_file=subject_file, subject_title=subject_name
        )


class MockExamSubFrame(ctk.CTkFrame):
    """
    '모의고사'를 선택했을 때 나타나는 하위 메뉴 프레임입니다.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller  # QuizApp 인스턴스
        self.master_start_page = parent  # StartPage 인스턴스

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)  # For back button

        # '1교시' 버튼
        session1_btn = ctk.CTkButton(
            self,
            text="1교시",
            command=lambda: self._start_mock_exam("session1"),  # 모의고사 시작 호출
            font=ctk.CTkFont(size=25, weight="bold"),
            height=70,
            corner_radius=12,
            fg_color="#1ABC9C",  # Teal color
            hover_color="#16A085",
        )
        session1_btn.grid(row=0, column=0, pady=15, padx=50, sticky="ew")

        # '2교시' 버튼
        session2_btn = ctk.CTkButton(
            self,
            text="2교시",
            command=lambda: self._start_mock_exam("session2"),  # 모의고사 시작 호출
            font=ctk.CTkFont(size=25, weight="bold"),
            height=70,
            corner_radius=12,
            fg_color="#9B59B6",  # Purple color
            hover_color="#8E44AD",
        )
        session2_btn.grid(row=1, column=0, pady=15, padx=50, sticky="ew")

        # 뒤로가기 버튼
        back_button = ctk.CTkButton(
            self,
            text="뒤로가기",
            command=self.master_start_page._show_main_menu,
            font=ctk.CTkFont(size=20, weight="bold"),
            height=50,
            corner_radius=12,
            fg_color="#7F8C8D",  # Grey
            hover_color="#6C7A89",
        )
        back_button.grid(row=2, column=0, pady=20, padx=50, sticky="ew")

    def _start_mock_exam(self, session_type):
        """
        선택된 모의고사 세션을 시작합니다.
        """
        self.controller._show_frame("MockQuizPage", session_type=session_type)


class QuizPage(ctk.CTkFrame):
    """
    실제 퀴즈가 진행되는 페이지 프레임입니다. (일반 과목 학습용)
    문제 표시, 답 확인, 통계, 오답 노트 기능 등을 포함합니다.
    """

    def __init__(self, parent, controller, subject_file, subject_title):
        super().__init__(parent)
        self.controller = controller
        self.subject_file = subject_file  # 선택된 과목의 JSON 파일 경로
        self.subject_title = subject_title  # 선택된 과목명

        # QuizPage의 그리드 구성
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=0)  # Stats Frame
        self.grid_rowconfigure(
            2, weight=2
        )  # Scrollable frame for Question & Choices (더 많은 공간 할당)
        self.grid_rowconfigure(
            3, weight=0
        )  # Control Buttons Frame (Check/Next & End Early)
        self.grid_rowconfigure(4, weight=1)  # Scrollable frame for Result & Explanation
        self.grid_rowconfigure(5, weight=0)  # End Quiz Buttons
        self.grid_columnconfigure(0, weight=1)

        self.questions = []  # 전체 문제 목록
        self.incorrectly_answered_questions_data = (
            []
        )  # 틀린 문제 데이터를 저장할 리스트
        self.current_question_index = 0  # 전체 문제 리스트용 인덱스
        self.current_review_question_index = 0  # 오답 노트 리스트용 인덱스
        self.selected_choice = -1  # 현재 선택된 보기 (초기값 -1: 선택 없음)
        self.is_review_mode = False  # 오답 노트 모드 여부

        # 퀴즈 통계 변수 초기화
        self.total_attempted = 0
        self.correct_count = 0
        self.incorrect_count = 0

        # 타이머 관련 변수 초기화
        self.elapsed_seconds = 0
        self.timer_running = False
        self.timer_job = None  # after() 메서드의 ID를 저장할 변수

        self._load_questions_from_json(self.subject_file)  # JSON에서 문제 로드
        self._shuffle_questions()  # 문제 로드 후 즉시 섞기
        self._setup_ui()  # UI 구성 요소 초기화
        self._restart_quiz()  # 퀴즈 시작 (타이머도 여기서 시작)

    def _load_questions_from_json(self, json_file_path):
        """
        지정된 JSON 파일 경로에서 문제를 로드합니다.
        """
        if not os.path.exists(json_file_path):
            tkmb.showerror(
                "파일 오류",
                f"'{json_file_path}' 파일을 찾을 수 없습니다.\n"
                "1. 'quiz_app.py' 파일과 같은 폴더에 해당 과목의 JSON 파일을 생성해주세요.\n"
                "2. JSON 파일에 문제 데이터를 복사해서 붙여넣어주세요.",
            )
            # QuizApp의 destroy 대신 StartPage로 돌아가도록 수정
            self.controller._show_frame("StartPage")
            return []  # 빈 리스트 반환하여 오류 후에도 앱이 유지되도록 함

        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                questions_data = json.load(f)
            if not questions_data:
                tkmb.showwarning(
                    "데이터 경고",
                    f"{self.subject_title} 문제 파일에 문제가 없습니다. 문제가 비어 있습니다. 문제를 추가해 주세요.",
                )
                self.controller._show_frame("StartPage")
                return []
            self.questions = questions_data  # 정상 로드 시 self.questions 업데이트
            return questions_data  # MockQuizPage에서 사용하기 위해 반환
        except json.JSONDecodeError as e:
            tkmb.showerror(
                "JSON 오류",
                f"{self.subject_title} 문제 파일을 읽는 중 오류가 발생했습니다.\n"
                f"JSON 형식이 올바른지 확인해주세요: {e}",
            )
            self.controller._show_frame("StartPage")
            return []
        except Exception as e:
            tkmb.showerror(
                "오류", f"문제를 로드하는 중 알 수 없는 오류가 발생했습니다: {e}"
            )
            self.controller._show_frame("StartPage")
            return []

    def _shuffle_questions(self):
        """문제 목록을 무작위로 섞습니다."""
        random.shuffle(self.questions)

    def _setup_ui(self):
        """UI 구성 요소를 초기화하고 배치합니다."""

        # 퀴즈 제목 (과목명 포함)
        self.title_label = ctk.CTkLabel(
            self,
            text=f"{self.subject_title} 퀴즈",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#3498DB",
        )
        self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="n")

        # 퀴즈 통계 표시 프레임
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.stats_frame.grid_columnconfigure(0, weight=1)  # 총 풀이
        self.stats_frame.grid_columnconfigure(1, weight=1)  # 정답
        self.stats_frame.grid_columnconfigure(2, weight=1)  # 오답
        self.stats_frame.grid_columnconfigure(3, weight=1)  # 경과 시간 (새로 추가)

        self.total_label = ctk.CTkLabel(
            self.stats_frame,
            text="총 풀이: 0",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.total_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.correct_label = ctk.CTkLabel(
            self.stats_frame,
            text="정답: 0",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2ECC71",
        )
        self.correct_label.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.incorrect_label = ctk.CTkLabel(
            self.stats_frame,
            text="오답: 0",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#E74C3C",
        )
        self.incorrect_label.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        # 경과 시간 표시 레이블 추가
        self.time_label = ctk.CTkLabel(
            self.stats_frame,
            text="시간: 00:00",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50",
        )
        self.time_label.grid(row=0, column=3, padx=5, pady=5, sticky="e")

        # 문제와 선택지를 포함할 스크롤 가능한 프레임
        self.question_choices_scroll_frame = ctk.CTkScrollableFrame(
            self,
            label_text="문제 및 선택지",
            label_font=ctk.CTkFont(size=18, weight="bold"),
            width=850,
            height=350,
        )
        self.question_choices_scroll_frame.grid(
            row=2, column=0, padx=20, pady=10, sticky="nsew"
        )
        self.question_choices_scroll_frame.grid_rowconfigure(0, weight=1)
        self.question_choices_scroll_frame.grid_rowconfigure(1, weight=0)
        self.question_choices_scroll_frame.grid_columnconfigure(0, weight=1)

        # 문제 표시 레이블 (스크롤 프레임 안에 배치)
        self.question_label = ctk.CTkLabel(
            self.question_choices_scroll_frame,
            text="",
            font=ctk.CTkFont(size=18, weight="bold"),
            wraplength=800,
            justify="left",
        )
        self.question_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # 선택지 버튼들을 포함할 프레임 (스크롤 프레임 안에 배치)
        self.choice_buttons_frame = ctk.CTkFrame(
            self.question_choices_scroll_frame, fg_color="transparent"
        )
        self.choice_buttons_frame.grid(row=1, column=0, padx=0, pady=10, sticky="ew")
        self.choice_buttons_frame.grid_columnconfigure(0, weight=1)

        self.choice_buttons = []
        for i in range(5):
            button = ctk.CTkButton(
                self.choice_buttons_frame,
                text=f"{i+1}. ",
                command=lambda idx=i: self._select_choice(idx),
                font=ctk.CTkFont(size=16),
                height=40,
                corner_radius=8,
                fg_color=("gray75", "gray25"),
                hover_color=("gray60", "gray35"),
                text_color="black",  # 글자색을 검은색으로 변경
                anchor="w",
                # wraplength=780,  # 텍스트 줄바꿈을 위한 wraplength 추가 - 제거
            )
            button.grid(row=i, column=0, padx=0, pady=5, sticky="ew")
            self.choice_buttons.append(button)

        # --- 컨트롤 버튼들을 담을 컨테이너 프레임 ---
        self.control_buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        self.control_buttons_container.grid(
            row=3, column=0, pady=20, padx=20, sticky="ew"
        )
        self.control_buttons_container.grid_columnconfigure(
            0, weight=1
        )  # 정답 확인 버튼용 컬럼
        self.control_buttons_container.grid_columnconfigure(
            1, weight=1
        )  # 퀴즈 끝내기 버튼용 컬럼

        # 정답 확인 / 다음 문제 버튼 (control_buttons_container 안에 배치됨)
        self.check_next_button = ctk.CTkButton(
            self.control_buttons_container,  # 부모 위젯 변경
            text="정답 확인",
            command=self._check_or_next_question,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#4CAF50",
            hover_color="#45a049",
            height=50,
            corner_radius=8,
        )
        self.check_next_button.grid(
            row=0, column=0, padx=(0, 10), sticky="ew"
        )  # container 내의 위치

        # 퀴즈 끝내기 버튼 추가 (control_buttons_container 안에 배치됨)
        self.end_early_button = ctk.CTkButton(
            self.control_buttons_container,  # 부모 위젯 변경
            text="퀴즈 끝내기",
            command=self._end_quiz_early,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#D35400",  # Orange/Red color
            hover_color="#C0392B",
            height=50,
            corner_radius=8,
        )
        self.end_early_button.grid(
            row=0, column=1, padx=(10, 0), sticky="ew"
        )  # container 내의 위치
        # --- 컨트롤 버튼 프레임 끝 ---

        # 결과 및 해설 표시 스크롤 가능한 프레임
        self.result_explanation_frame = ctk.CTkScrollableFrame(
            self,
            label_text="결과 및 해설",
            label_font=ctk.CTkFont(size=18, weight="bold"),
            width=850,
            height=200,
        )
        self.result_explanation_frame.grid(
            row=4, column=0, padx=20, pady=10, sticky="nsew"
        )
        self.result_explanation_frame.grid_rowconfigure(0, weight=1)
        self.result_explanation_frame.grid_columnconfigure(0, weight=1)

        self.feedback_label = ctk.CTkLabel(
            self.result_explanation_frame,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#333333",
        )
        self.feedback_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.explanation_label = ctk.CTkLabel(
            self.result_explanation_frame,
            text="",
            font=ctk.CTkFont(size=15),
            wraplength=830,
            justify="left",
        )
        self.explanation_label.grid(
            row=1, column=0, padx=10, pady=(0, 10), sticky="nsew"
        )

        # 퀴즈 종료 시 버튼들 (오답노트, 처음으로, 홈 화면으로)을 담을 프레임
        self.end_quiz_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.end_quiz_buttons_frame.grid(
            row=5, column=0, pady=(10, 20), padx=20, sticky="ew"
        )
        self.end_quiz_buttons_frame.grid_columnconfigure(0, weight=1)
        self.end_quiz_buttons_frame.grid_columnconfigure(1, weight=1)
        self.end_quiz_buttons_frame.grid_rowconfigure(
            0, weight=1
        )  # Restart / Review buttons
        self.end_quiz_buttons_frame.grid_rowconfigure(1, weight=1)  # Go to Home button

        self.restart_full_quiz_button = ctk.CTkButton(
            self.end_quiz_buttons_frame,
            text="처음으로 (전체 퀴즈 다시 풀기)",
            command=self._restart_quiz,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#3498DB",
            hover_color="#2980B9",
            height=50,
            corner_radius=8,
        )
        self.restart_full_quiz_button.grid(row=0, column=0, padx=10, sticky="ew")

        self.review_incorrect_button = ctk.CTkButton(
            self.end_quiz_buttons_frame,
            text="오답 노트 풀기",
            command=self._start_review_mode,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#E67E22",
            hover_color="#D35400",
            height=50,
            corner_radius=8,
        )
        self.review_incorrect_button.grid(row=0, column=1, padx=10, sticky="ew")

        self.go_to_home_button = ctk.CTkButton(
            self.end_quiz_buttons_frame,
            text="홈 화면으로",
            command=lambda: self.controller._show_frame(
                "StartPage"
            ),  # 홈 화면으로 돌아가는 버튼
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#7F8C8D",  # Grey color
            hover_color="#6C7A89",
            height=50,
            corner_radius=8,
        )
        self.go_to_home_button.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew"
        )  # 새로운 행에 배치

        # 처음 시작 시 퀴즈 종료 버튼 프레임 숨김
        self.end_quiz_buttons_frame.grid_remove()
        self._update_stats_display()  # 초기 통계 업데이트

    def _update_stats_display(self):
        """퀴즈 통계를 UI에 업데이트합니다."""
        self.total_label.configure(text=f"총 풀이: {self.total_attempted}")
        self.correct_label.configure(text=f"정답: {self.correct_count}")
        self.incorrect_label.configure(text=f"오답: {self.incorrect_count}")

    def _update_time_display(self):
        """경과 시간을 계산하고 UI에 업데이트합니다."""
        if not self.timer_running:
            return

        self.elapsed_seconds += 1
        minutes = self.elapsed_seconds // 60
        seconds = self.elapsed_seconds % 60
        self.time_label.configure(text=f"시간: {minutes:02}:{seconds:02}")

        # 1초 후에 다시 이 함수를 호출하도록 스케줄링
        self.timer_job = self.after(1000, self._update_time_display)

    def _start_timer(self):
        """타이머를 시작합니다."""
        if not self.timer_running:
            self.timer_running = True
            self.elapsed_seconds = 0  # 시간 초기화
            self._update_time_display()  # 즉시 업데이트 및 이후 스케줄링

    def _stop_timer(self):
        """타이머를 정지합니다."""
        if self.timer_running and self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self.timer_running = False
        self.time_label.configure(text="시간: 00:00")  # 타이머 정지 시 시간 초기화 표시

    def _format_choice_text(self, text, char_limit_per_line=40):
        """
        주어진 텍스트를 지정된 글자 수마다 줄바꿈 문자를 삽입하여 포맷합니다.
        한글은 1글자로 계산합니다.
        """
        formatted_text = ""
        current_line_length = 0
        for char in text:
            # 한글은 유니코드 범위 CJK 통합 한자 (U+4E00 - U+9FFF)와 한글 음절 (U+AC00 - U+D7AF)에 해당
            # 또는 기타 아시아 문자 포함 여부는 필요에 따라 확장 가능
            if (
                "가" <= char <= "힣" or "\u4e00" <= char <= "\u9fff"
            ):  # 대략적인 한글/한자 범위
                char_width = 2  # 한글/한자는 2글자 너비로 간주
            else:
                char_width = 1  # 영문, 숫자, 특수문자는 1글자 너비로 간주

            if current_line_length + char_width > char_limit_per_line:
                formatted_text += "\n"
                current_line_length = char_width
            else:
                current_line_length += char_width
            formatted_text += char
        return formatted_text

    def _load_question(self):
        """현재 인덱스에 해당하는 문제를 로드하고 UI를 업데이트합니다."""
        target_questions_list = (
            self.incorrectly_answered_questions_data
            if self.is_review_mode
            else self.questions
        )
        current_idx_for_list = (
            self.current_review_question_index
            if self.is_review_mode
            else self.current_question_index
        )

        # 모든 문제 (또는 오답 노트)를 다 풀었을 때
        if (
            current_idx_for_list >= len(target_questions_list)
            or not target_questions_list
        ):
            self._transition_to_quiz_end_state()  # 퀴즈 종료 상태로 전환
            return

        # 문제 로드 및 UI 업데이트
        question_data = target_questions_list[current_idx_for_list]

        # 문제 번호 접두사 설정
        q_prefix_num = current_idx_for_list + 1
        q_prefix = f"Q{q_prefix_num}."
        if self.is_review_mode:
            q_prefix = f"오답 Q{q_prefix_num}."  # 오답 노트 모드에서는 접두사 변경

        self.question_label.configure(text=f"{q_prefix} {question_data['question']}")

        for i, button in enumerate(self.choice_buttons):
            if i < len(question_data["choices"]):
                # 보기를 포맷하여 줄바꿈 적용
                formatted_choice = self._format_choice_text(
                    question_data["choices"][i], 40
                )
                button.configure(
                    text=f"{i+1}. {formatted_choice}",
                    fg_color=("gray75", "gray25"),
                    state="normal",
                    text_color="black",
                )
                button.grid()  # 버튼 보이기
            else:
                button.grid_remove()  # 사용하지 않는 버튼 숨기기

        self.feedback_label.configure(text="")
        self.explanation_label.configure(text="")
        self.selected_choice = -1  # 선택 초기화

        # '정답 확인' / '다음 문제' 버튼 텍스트 업데이트
        button_text = "정답 확인"
        if self.is_review_mode:
            button_text = "정답 확인 (오답 노트)"
        self.check_next_button.configure(
            text=button_text,
            command=self._check_or_next_question,
            fg_color="#4CAF50",
            hover_color="#45a049",
            state="normal",  # 버튼 활성화
        )
        # 컨트롤 버튼 컨테이너를 보이게 함 (그 안에 있는 버튼들도 자동으로 보임)
        self.control_buttons_container.grid(
            row=3, column=0, pady=20, padx=20, sticky="ew"
        )

        self.end_quiz_buttons_frame.grid_remove()  # 퀴즈 진행 중에는 종료 버튼 프레임 숨김

        # 문제와 보기를 담는 스크롤 프레임의 스크롤을 맨 위로 올립니다.
        self.question_choices_scroll_frame._parent_canvas.yview_moveto(0)

    def _select_choice(self, index):
        """사용자가 선택지를 클릭했을 때 호출됩니다."""
        self.selected_choice = index
        for i, button in enumerate(self.choice_buttons):
            if i == index:
                button.configure(fg_color="#5DADE2")  # 선택된 버튼 색상 변경
            else:
                button.configure(
                    fg_color=("gray75", "gray25")
                )  # 나머지 버튼 원래 색상으로 복원

    def _check_or_next_question(self):
        """'정답 확인' 또는 '다음 문제' 버튼 클릭 시 호출됩니다."""
        # 선택지가 선택되지 않은 상태에서 '정답 확인' 버튼을 누르면 경고 메시지 표시
        if self.selected_choice == -1 and self.check_next_button.cget(
            "text"
        ).startswith("정답 확인"):
            tkmb.showwarning("선택 오류", "답을 먼저 선택해주세요!")
            return

        if self.check_next_button.cget("text").startswith("정답 확인"):
            self._check_answer()  # 정답 확인
        else:  # '다음 문제' 버튼일 때
            if self.is_review_mode:
                self.current_review_question_index += 1
            else:
                self.current_question_index += 1
            self._load_question()  # 다음 문제 로드

    def _check_answer(self):
        """선택된 답을 확인하고 피드백 및 해설을 표시합니다."""
        target_questions_list = (
            self.incorrectly_answered_questions_data
            if self.is_review_mode
            else self.questions
        )
        current_idx_for_list = (
            self.current_review_question_index
            if self.is_review_mode
            else self.current_question_index
        )

        # 현재 문제가 없는 상태일 경우 (퀴즈가 이미 끝난 경우 등)
        if current_idx_for_list >= len(target_questions_list):
            return

        current_question_data = target_questions_list[current_idx_for_list]
        correct_index = current_question_data["correct_answer_index"]
        explanation = current_question_data["explanation"]

        # 모든 선택지 버튼 비활성화
        for button in self.choice_buttons:
            button.configure(state="disabled")

        # 퀴즈 통계 업데이트 (오답 노트 모드에서는 통계 업데이트하지 않음)
        if not self.is_review_mode:
            self.total_attempted += 1
            if self.selected_choice == correct_index:
                self.correct_count += 1
            else:
                self.incorrect_count += 1
                # 중복 추가 방지 (오답 노트에 이미 있는 문제인지 확인)
                if (
                    current_question_data
                    not in self.incorrectly_answered_questions_data
                ):
                    self.incorrectly_answered_questions_data.append(
                        current_question_data
                    )

        self._update_stats_display()  # 통계 UI 업데이트

        # 정답/오답 피드백 및 버튼 색상 변경
        if self.selected_choice == correct_index:
            self.feedback_label.configure(text="정답입니다!", text_color="#2ECC71")
            self.choice_buttons[correct_index].configure(
                fg_color=("#2ECC71")
            )  # 정답은 녹색
        else:
            self.feedback_label.configure(text="오답입니다.", text_color="#E74C3C")
            # 선택한 답이 유효한 범위 내일 경우에만 오답 색상 변경
            if 0 <= self.selected_choice < len(self.choice_buttons):
                self.choice_buttons[self.selected_choice].configure(
                    fg_color=("#E74C3C")
                )  # 오답은 빨간색
            self.choice_buttons[correct_index].configure(
                fg_color=("#2ECC71")
            )  # 정답은 녹색으로 표시

        self.explanation_label.configure(text=explanation)  # 해설 표시

        # '다음 문제' 버튼 텍스트 변경 및 활성화
        button_text = "다음 문제"
        if self.is_review_mode:
            button_text = "다음 오답"
        self.check_next_button.configure(
            text=button_text, fg_color="#2980B9", hover_color="#2471A3"
        )

    def _restart_quiz(self):
        """퀴즈를 처음부터 다시 시작합니다 (전체 문제)."""
        self._stop_timer()  # 타이머 정지
        self.current_question_index = 0
        self.current_review_question_index = 0
        self.is_review_mode = False
        self.incorrectly_answered_questions_data = []  # 틀린 문제 목록 초기화

        # 통계 초기화
        self.total_attempted = 0
        self.correct_count = 0
        self.incorrect_count = 0
        self._update_stats_display()

        self._shuffle_questions()  # 문제 다시 섞기
        self._load_question()  # 첫 문제 로드
        self._start_timer()  # 타이머 다시 시작

        # UI 상태를 퀴즈 진행 상태로 전환
        self.end_quiz_buttons_frame.grid_remove()  # 퀴즈 종료 버튼 프레임 숨김
        self.control_buttons_container.grid(
            row=3, column=0, pady=20, padx=20, sticky="ew"
        )  # 컨트롤 버튼 프레임 다시 보이기

    def _start_review_mode(self):
        """오답 노트 모드로 퀴즈를 시작합니다."""
        if not self.incorrectly_answered_questions_data:
            tkmb.showinfo(
                "오답 없음", "현재 틀린 문제가 없습니다. 전체 퀴즈를 다시 시작합니다."
            )
            self._restart_quiz()  # 오답이 없으면 전체 퀴즈로 리스타트
            return

        self._stop_timer()  # 타이머 정지
        self.is_review_mode = True
        self.current_review_question_index = 0

        random.shuffle(
            self.incorrectly_answered_questions_data
        )  # 오답 문제를 다시 섞어서 풀어볼 수 있습니다.

        self._load_question()  # 오답 노트 첫 문제 로드
        self._start_timer()  # 타이머 다시 시작

        # UI 상태를 오답 노트 진행 상태로 전환
        self.end_quiz_buttons_frame.grid_remove()  # 퀴즈 종료 버튼 프레임 숨김
        self.control_buttons_container.grid(
            row=3, column=0, pady=20, padx=20, sticky="ew"
        )  # 컨트롤 버튼 프레임 다시 보이기

    def _end_quiz_early(self):
        """현재 퀴즈를 강제로 종료하고 결과 화면으로 전환합니다."""
        tkmb.showinfo(
            "퀴즈 종료",
            "현재 퀴즈가 종료되었습니다. 결과를 확인하고 오답 노트를 이용할 수 있습니다.",
        )

        self._transition_to_quiz_end_state()  # UI 상태를 퀴즈 종료 상태로 전환

    def _transition_to_quiz_end_state(self):
        """퀴즈 종료 시 UI 상태를 관리하는 헬퍼 함수."""
        self._stop_timer()  # 타이머 정지

        self.control_buttons_container.grid_remove()  # 정답 확인/끝내기 버튼이 있는 프레임 숨김

        # 최종 통계 메시지 표시
        self.question_label.configure(
            text=f"퀴즈가 종료되었습니다! 총 {self.total_attempted}문제 중 {self.correct_count}개 정답, {self.incorrect_count}개 오답입니다. 수고하셨습니다."
        )
        # 모든 선택지 버튼 숨김
        for button in self.choice_buttons:
            button.grid_remove()

        self.feedback_label.configure(text="")  # 피드백 초기화
        self.explanation_label.configure(text="")  # 해설 초기화

        # 퀴즈 종료 후 버튼 프레임 활성화
        self.end_quiz_buttons_frame.grid()
        self.restart_full_quiz_button.grid(row=0, column=0, padx=10, sticky="ew")
        if self.incorrect_count > 0:  # 틀린 문제가 있을 경우에만 오답 노트 버튼 표시
            self.review_incorrect_button.grid(row=0, column=1, padx=10, sticky="ew")
        else:
            self.review_incorrect_button.grid_remove()  # 틀린 문제 없으면 버튼 숨김

        self.go_to_home_button.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew"
        )  # 홈 버튼 표시

        # 내부 상태를 퀴즈 종료 상태로 설정하여 _load_question이 다음 문제를 로드하려 하지 않도록 함
        self.current_question_index = len(self.questions)
        self.current_review_question_index = len(
            self.incorrectly_answered_questions_data
        )
        self.is_review_mode = False  # 일반 퀴즈 종료 상태로 간주 (오답 노트 모드 아님)


class MockQuizPage(ctk.CTkFrame):
    """
    모의고사가 진행되는 페이지 프레임입니다.
    문제 표시, 답 선택, 최종 결과 및 오답 노트 기능을 포함합니다.
    """

    def __init__(self, parent, controller, session_type):
        super().__init__(parent)
        self.controller = controller
        self.session_type = session_type
        self.subject_map = {
            "session1": {
                "title": "1교시 모의고사",
                "subjects": {
                    "재정학": "questions_finance.json",
                    "세법학개론": "questions_taxlaw.json",
                },
            },
            "session2": {
                "title": "2교시 모의고사",
                "subjects": {
                    "회계학개론": "questions_accounting.json",
                    "상법": "questions_commerciallaw.json",
                },
            },
        }
        self.session_info = self.subject_map[self.session_type]

        self.all_questions_for_mock_exam = []  # 모의고사에 출제될 80문제 전체
        self.user_answers = []  # 사용자의 답을 저장 (index, choice_index)
        self.current_mock_question_index = 0
        self.incorrectly_answered_questions_data = []  # 모의고사 중 틀린 문제
        self.is_review_mode = False  # MockQuizPage에 is_review_mode 속성 추가

        self.elapsed_seconds = 0
        self.timer_running = False
        self.timer_job = None

        self._setup_ui()
        self._load_mock_questions()
        self._load_question()  # 첫 문제 로드
        self._start_timer()

    def _load_questions_from_json(self, json_file_path):
        """
        주어진 JSON 파일 경로에서 문제를 로드합니다.
        파일이 없거나 비어있을 경우 경고 메시지를 표시하고 빈 리스트를 반환합니다.
        """
        if not os.path.exists(json_file_path):
            tkmb.showerror(
                "파일 오류",
                f"'{json_file_path}' 파일을 찾을 수 없습니다.\n"
                "JSON 파일이 올바르게 위치하는지 확인해주세요.",
            )
            return []
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                questions_data = json.load(f)
            if not questions_data:
                tkmb.showwarning(
                    "데이터 경고",
                    f"'{json_file_path}' 파일에 문제가 없습니다. 문제가 비어 있습니다.",
                )
                return []
            return questions_data
        except json.JSONDecodeError as e:
            tkmb.showerror(
                "JSON 오류",
                f"'{json_file_path}' 파일을 읽는 중 오류가 발생했습니다.\n"
                f"JSON 형식이 올바른지 확인해주세요: {e}",
            )
            return []
        except Exception as e:
            tkmb.showerror(
                "오류", f"문제를 로드하는 중 알 수 없는 오류가 발생했습니다: {e}"
            )
            return []

    def _load_mock_questions(self):
        """
        모의고사에 필요한 문제들을 각 과목에서 40문제씩 랜덤으로 로드합니다.
        """
        self.all_questions_for_mock_exam = []
        for subject_name, file_name in self.session_info["subjects"].items():
            subject_questions = self._load_questions_from_json(file_name)

            if not subject_questions:
                # 파일 로드 실패 시 모의고사 중단 및 홈 화면으로 복귀
                tkmb.showerror(
                    "모의고사 로드 오류",
                    f"{subject_name} 문제 로드에 실패했습니다. 모의고사를 시작할 수 없습니다.",
                )
                self.controller._show_frame("StartPage")
                return

            # 각 과목에서 40문제씩 랜덤 선택
            # 과목별 문제 수가 40개 미만일 경우 가능한 모든 문제 사용
            num_questions_to_select = min(40, len(subject_questions))
            selected_questions = random.sample(
                subject_questions, num_questions_to_select
            )

            # 문제에 원본 과목 정보 추가
            for q in selected_questions:
                q["subject_origin"] = subject_name
            self.all_questions_for_mock_exam.extend(selected_questions)

        # 전체 모의고사 문제를 섞습니다.
        random.shuffle(self.all_questions_for_mock_exam)

        # 사용자 답변 저장 공간 초기화 (80문제에 대한 공간 확보)
        self.user_answers = [-1] * len(self.all_questions_for_mock_exam)

        if not self.all_questions_for_mock_exam:
            tkmb.showwarning(
                "문제 부족",
                "모의고사를 위한 충분한 문제가 로드되지 않았습니다. 다른 파일을 확인하거나 문제를 추가해주세요.",
            )
            self.controller._show_frame("StartPage")

    def _setup_ui(self):
        """모의고사 UI 구성 요소를 초기화하고 배치합니다."""
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=0)  # Time/Question count
        self.grid_rowconfigure(2, weight=2)  # Scrollable frame for Question & Choices
        self.grid_rowconfigure(3, weight=0)  # Control Buttons Frame (Next & End Early)
        self.grid_rowconfigure(4, weight=1)  # Scrollable frame for Results
        self.grid_rowconfigure(5, weight=0)  # End Quiz Buttons
        self.grid_columnconfigure(0, weight=1)

        # 퀴즈 제목 (세션명 포함)
        self.title_label = ctk.CTkLabel(
            self,
            text=self.session_info["title"],
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#3498DB",
        )
        self.title_label.grid(row=0, column=0, pady=(20, 10), sticky="n")

        # 시간 및 문제 카운트 표시 프레임
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)  # 문제 번호
        self.info_frame.grid_columnconfigure(1, weight=1)  # 경과 시간

        self.question_count_label = ctk.CTkLabel(
            self.info_frame,
            text="문제: 0/80",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50",
        )
        self.question_count_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.time_label = ctk.CTkLabel(
            self.info_frame,
            text="시간: 00:00",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50",
        )
        self.time_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        # 문제와 선택지를 포함할 스크롤 가능한 프레임 (QuizPage와 동일)
        self.question_choices_scroll_frame = ctk.CTkScrollableFrame(
            self,
            label_text="문제 및 선택지",
            label_font=ctk.CTkFont(size=18, weight="bold"),
            width=850,
            height=350,
        )
        self.question_choices_scroll_frame.grid(
            row=2, column=0, padx=20, pady=10, sticky="nsew"
        )
        self.question_choices_scroll_frame.grid_rowconfigure(0, weight=1)
        self.question_choices_scroll_frame.grid_rowconfigure(1, weight=0)
        self.question_choices_scroll_frame.grid_columnconfigure(0, weight=1)

        self.question_label = ctk.CTkLabel(
            self.question_choices_scroll_frame,
            text="",
            font=ctk.CTkFont(size=18, weight="bold"),
            wraplength=800,
            justify="left",
        )
        self.question_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.choice_buttons_frame = ctk.CTkFrame(
            self.question_choices_scroll_frame, fg_color="transparent"
        )
        self.choice_buttons_frame.grid(row=1, column=0, padx=0, pady=10, sticky="ew")
        self.choice_buttons_frame.grid_columnconfigure(0, weight=1)

        self.choice_buttons = []
        for i in range(5):
            button = ctk.CTkButton(
                self.choice_buttons_frame,
                text=f"{i+1}. ",
                command=lambda idx=i: self._select_choice(idx),
                font=ctk.CTkFont(size=16),
                height=40,
                corner_radius=8,
                fg_color=("gray75", "gray25"),
                hover_color=("gray60", "gray35"),
                text_color="black",
                anchor="w",
                # wraplength=780,  # 텍스트 줄바꿈을 위한 wraplength 추가 - 제거
            )
            button.grid(row=i, column=0, padx=0, pady=5, sticky="ew")
            self.choice_buttons.append(button)

        # --- 컨트롤 버튼들을 담을 컨테이너 프레임 ---
        self.control_buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        self.control_buttons_container.grid(
            row=3, column=0, pady=20, padx=20, sticky="ew"
        )
        self.control_buttons_container.grid_columnconfigure(0, weight=1)
        self.control_buttons_container.grid_columnconfigure(1, weight=1)

        # 다음 문제 / 결과 보기 버튼
        self.next_question_button = ctk.CTkButton(
            self.control_buttons_container,
            text="다음 문제",
            command=self._next_question_or_show_results,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#3498DB",
            hover_color="#2980B9",
            height=50,
            corner_radius=8,
        )
        self.next_question_button.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        # 모의고사 끝내기 버튼 (언제든지 모의고사를 종료할 수 있음)
        self.end_mock_early_button = ctk.CTkButton(
            self.control_buttons_container,
            text="모의고사 끝내기",
            command=self._end_mock_exam_early,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color="#D35400",
            hover_color="#C0392B",
            height=50,
            corner_radius=8,
        )
        self.end_mock_early_button.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        # --- 컨트롤 버튼 프레임 끝 ---

        # 결과 표시 스크롤 가능한 프레임 (모의고사 종료 후 사용)
        self.result_display_frame = ctk.CTkScrollableFrame(
            self,
            label_text="모의고사 결과",
            label_font=ctk.CTkFont(size=18, weight="bold"),
            width=850,
            height=200,
        )
        self.result_display_frame.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        self.result_display_frame.grid_rowconfigure(0, weight=0)  # 총평
        self.result_display_frame.grid_rowconfigure(1, weight=1)  # 과목별 상세
        self.result_display_frame.grid_columnconfigure(0, weight=1)
        self.result_display_frame.grid_remove()  # 초기에는 숨김

        self.overall_result_label = ctk.CTkLabel(
            self.result_display_frame,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#333333",
            wraplength=830,
            justify="left",
        )
        self.overall_result_label.grid(
            row=0, column=0, padx=10, pady=(5, 0), sticky="w"
        )

        self.subject_results_label = ctk.CTkLabel(
            self.result_display_frame,
            text="",
            font=ctk.CTkFont(size=16),
            wraplength=830,
            justify="left",
        )
        self.subject_results_label.grid(
            row=1, column=0, padx=10, pady=(0, 10), sticky="nsew"
        )

        # 모의고사 종료 시 버튼들 (오답노트, 처음으로, 홈 화면으로)
        self.end_mock_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.end_mock_buttons_frame.grid(
            row=5, column=0, pady=(10, 20), padx=20, sticky="ew"
        )
        self.end_mock_buttons_frame.grid_columnconfigure(0, weight=1)
        self.end_mock_buttons_frame.grid_columnconfigure(1, weight=1)
        self.end_mock_buttons_frame.grid_rowconfigure(0, weight=1)
        self.end_mock_buttons_frame.grid_rowconfigure(1, weight=1)
        self.end_mock_buttons_frame.grid_remove()  # 초기에는 숨김

        self.restart_mock_button = ctk.CTkButton(
            self.end_mock_buttons_frame,
            text="다시 풀기 (새 모의고사)",
            command=self._restart_mock_exam,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#3498DB",
            hover_color="#2980B9",
            height=50,
            corner_radius=8,
        )
        self.restart_mock_button.grid(row=0, column=0, padx=10, sticky="ew")

        self.review_mock_incorrect_button = ctk.CTkButton(
            self.end_mock_buttons_frame,
            text="오답 노트 풀기",
            command=self._start_review_mode,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#E67E22",
            hover_color="#D35400",
            height=50,
            corner_radius=8,
        )
        self.review_mock_incorrect_button.grid(row=0, column=1, padx=10, sticky="ew")

        self.go_to_home_button = ctk.CTkButton(
            self.end_mock_buttons_frame,
            text="홈 화면으로",
            command=lambda: self.controller._show_frame("StartPage"),
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="#7F8C8D",
            hover_color="#6C7A89",
            height=50,
            corner_radius=8,
        )
        self.go_to_home_button.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew"
        )

    def _update_time_display(self):
        """경과 시간을 계산하고 UI에 업데이트합니다."""
        if not self.timer_running:
            return

        self.elapsed_seconds += 1
        minutes = self.elapsed_seconds // 60
        seconds = self.elapsed_seconds % 60
        self.time_label.configure(text=f"시간: {minutes:02}:{seconds:02}")

        self.timer_job = self.after(1000, self._update_time_display)

    def _start_timer(self):
        """타이머를 시작합니다."""
        if not self.timer_running:
            self.timer_running = True
            self.elapsed_seconds = 0
            self._update_time_display()

    def _stop_timer(self):
        """타이머를 정지합니다."""
        if self.timer_running and self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self.timer_running = False
        self.time_label.configure(text="시간: 00:00")

    def _format_choice_text(self, text, char_limit_per_line=40):
        """
        주어진 텍스트를 지정된 글자 수마다 줄바꿈 문자를 삽입하여 포맷합니다.
        한글은 1글자로 계산합니다.
        """
        formatted_text = ""
        current_line_length = 0
        for char in text:
            # 한글은 유니코드 범위 CJK 통합 한자 (U+4E00 - U+9FFF)와 한글 음절 (U+AC00 - U+D7AF)에 해당
            # 또는 기타 아시아 문자 포함 여부는 필요에 따라 확장 가능
            if (
                "가" <= char <= "힣" or "\u4e00" <= char <= "\u9fff"
            ):  # 대략적인 한글/한자 범위
                char_width = 2  # 한글/한자는 2글자 너비로 간주
            else:
                char_width = 1  # 영문, 숫자, 특수문자는 1글자 너비로 간주

            if current_line_length + char_width > char_limit_per_line:
                formatted_text += "\n"
                current_line_length = char_width
            else:
                current_line_length += char_width
            formatted_text += char
        return formatted_text

    def _load_question(self):
        """현재 인덱스에 해당하는 모의고사 문제를 로드하고 UI를 업데이트합니다."""
        target_questions_list = (
            self.incorrectly_answered_questions_data
            if self.is_review_mode
            else self.all_questions_for_mock_exam
        )
        current_idx_for_list = (
            self.current_review_question_index
            if self.is_review_mode
            else self.current_mock_question_index
        )

        if (
            current_idx_for_list >= len(target_questions_list)
            or not target_questions_list
        ):
            if self.is_review_mode:
                tkmb.showinfo("오답 노트", "오답 노트 풀이를 완료했습니다.")
                self._transition_to_mock_exam_end_state()  # 오답 노트 끝나면 결과 화면으로
            else:
                self._end_mock_exam_and_show_results()  # 모의고사 끝나면 결과 화면으로
            return

        question_data = target_questions_list[current_idx_for_list]

        # 문제 번호 설정 (모의고사는 1부터 80번)
        if self.is_review_mode:
            q_prefix = f"오답 Q{current_idx_for_list + 1}."
        else:
            q_prefix = f"Q{current_idx_for_list + 1}."
            self.question_count_label.configure(
                text=f"문제: {current_idx_for_list + 1}/{len(self.all_questions_for_mock_exam)}"
            )

        self.question_label.configure(text=f"{q_prefix} {question_data['question']}")

        # 선택지 버튼 업데이트
        for i, button in enumerate(self.choice_buttons):
            if i < len(question_data["choices"]):
                # 보기를 포맷하여 줄바꿈 적용
                formatted_choice = self._format_choice_text(
                    question_data["choices"][i], 40
                )
                button.configure(
                    text=f"{i+1}. {formatted_choice}",
                    fg_color=("gray75", "gray25"),
                    state="normal",
                    text_color="black",
                )
                button.grid()
                # 사용자가 이전에 선택한 답이 있다면 다시 하이라이트
                if (
                    not self.is_review_mode
                    and self.user_answers[self.current_mock_question_index] == i
                ):
                    button.configure(fg_color="#5DADE2")
            else:
                button.grid_remove()

        self.selected_choice = -1  # 현재 문제의 선택 초기화
        self.result_display_frame.grid_remove()  # 결과 프레임 숨김 (문제 풀이 중)

        # 오답 노트 모드에서는 피드백/해설이 즉시 보일 수 있도록
        if self.is_review_mode:
            self.overall_result_label.configure(
                text=""
            )  # 기존 overall_result_label 사용
            self.subject_results_label.configure(
                text=""
            )  # 기존 subject_results_label 사용
            # 오답 노트에서는 '정답 확인 (오답 노트)' 버튼을 사용하여 해설을 먼저 보고 다음 문제로 넘어갈 수 있도록
            # QuizPage의 check_next_button과 동일한 로직으로 동작
            self.next_question_button.configure(
                text="정답 확인 (오답 노트)", command=self._check_answer_in_review_mode
            )
            self.next_question_button.grid(row=0, column=0, padx=(0, 10), sticky="ew")
            self.end_mock_early_button.grid_remove()  # 오답 노트 중에는 끝내기 버튼 숨김

            # 오답 노트 결과/해설 UI 활성화
            # MockQuizPage의 result_display_frame의 label들을 사용하도록 변경
            self.result_display_frame.grid()  # 결과/해설 프레임 보이게
        else:
            # 모의고사 진행 중
            self.next_question_button.configure(
                text="다음 문제",
                fg_color="#3498DB",
                hover_color="#2980B9",
                state="normal",
            )
            self.end_mock_early_button.grid()  # 모의고사 중에는 끝내기 버튼 표시
            self.control_buttons_container.grid(
                row=3, column=0, pady=20, padx=20, sticky="ew"
            )
            self.next_question_button.grid(
                row=0, column=0, padx=(0, 10), sticky="ew"
            )  # 다음 문제 버튼
            # 모의고사 진행 중에는 해설 관련 UI를 숨김 (피드백, 해설 레이블)
            self.overall_result_label.configure(
                text=""
            )  # 결과 프레임의 총평 레이블을 해설로 사용
            self.subject_results_label.configure(
                text=""
            )  # 결과 프레임의 과목별 상세 레이블을 해설로 사용
            self.result_display_frame.grid_remove()  # 해설 프레임 숨김

        self.question_choices_scroll_frame._parent_canvas.yview_moveto(0)

    def _select_choice(self, index):
        """사용자가 선택지를 클릭했을 때 호출됩니다."""
        self.selected_choice = index
        for i, button in enumerate(self.choice_buttons):
            # 이전 선택 상태를 리셋하기 위해 모든 버튼의 배경색을 기본값으로 설정
            button.configure(fg_color=("gray75", "gray25"))
            if i == index:
                button.configure(fg_color="#5DADE2")  # 선택된 버튼 색상 변경

        # 모의고사 모드에서만 사용자 선택 저장 (오답 노트 모드에서는 저장하지 않음)
        if not self.is_review_mode:
            self.user_answers[self.current_mock_question_index] = self.selected_choice

    def _next_question_or_show_results(self):
        """'다음 문제' 버튼 클릭 시 다음 문제 로드 또는 결과 표시."""
        if self.selected_choice == -1:
            tkmb.showwarning("선택 오류", "답을 먼저 선택해주세요!")
            return

        # 현재 문제에 대한 사용자 선택 저장
        if not self.is_review_mode:
            self.user_answers[self.current_mock_question_index] = self.selected_choice

        self.current_mock_question_index += 1

        if self.current_mock_question_index < len(self.all_questions_for_mock_exam):
            self._load_question()
        else:
            self._end_mock_exam_and_show_results()

    def _check_answer_in_review_mode(self):
        """오답 노트 모드에서 정답 확인."""
        if self.selected_choice == -1:
            tkmb.showwarning("선택 오류", "답을 먼저 선택해주세요!")
            return

        current_question_data = self.incorrectly_answered_questions_data[
            self.current_review_question_index
        ]
        correct_index = current_question_data["correct_answer_index"]
        explanation = current_question_data["explanation"]

        # 모든 선택지 버튼 비활성화
        for button in self.choice_buttons:
            button.configure(state="disabled")

        # 정답/오답 피드백 및 버튼 색상 변경
        if self.selected_choice == correct_index:
            self.overall_result_label.configure(
                text="정답입니다!", text_color="#2ECC71"
            )  # 기존 overall_result_label 사용
            self.choice_buttons[correct_index].configure(
                fg_color=("#2ECC71")
            )  # 정답은 녹색
        else:
            self.overall_result_label.configure(
                text="오답입니다.", text_color="#E74C3C"
            )  # 기존 overall_result_label 사용
            if 0 <= self.selected_choice < len(self.choice_buttons):
                self.choice_buttons[self.selected_choice].configure(
                    fg_color=("#E74C3C")
                )  # 오답은 빨간색
            self.choice_buttons[correct_index].configure(
                fg_color=("#2ECC71")
            )  # 정답은 녹색으로 표시

        self.subject_results_label.configure(
            text=explanation
        )  # 기존 subject_results_label 사용

        # '다음 오답' 버튼으로 변경
        self.next_question_button.configure(
            text="다음 오답",
            fg_color="#2980B9",
            hover_color="#2471A3",
            command=self._next_review_question,
        )
        self.next_question_button.grid()  # 이 버튼이 보이도록 함

    def _next_review_question(self):
        """오답 노트 다음 문제 로드."""
        self.current_review_question_index += 1
        self._load_question()

    def _end_mock_exam_and_show_results(self):
        """모의고사 종료 후 결과 화면을 표시하고 점수를 계산합니다."""
        self._stop_timer()

        self.control_buttons_container.grid_remove()  # 문제 풀이 버튼 숨김
        for button in self.choice_buttons:  # 선택지 버튼 숨김
            button.grid_remove()

        # 결과 계산
        subject_correct_counts = {
            sub_name: 0 for sub_name in self.session_info["subjects"].keys()
        }
        # 모의고사 종료 시에만 incorrectly_answered_questions_data를 새로 생성
        # 오답 노트 풀이 후에는 이 리스트를 다시 비우지 않음.
        if not self.is_review_mode:
            self.incorrectly_answered_questions_data = []

        total_correct_overall = 0
        total_questions_overall = len(self.all_questions_for_mock_exam)

        for i, question_data in enumerate(self.all_questions_for_mock_exam):
            user_choice = self.user_answers[i]
            correct_index = question_data["correct_answer_index"]
            subject_origin = question_data["subject_origin"]

            if user_choice == correct_index:
                subject_correct_counts[subject_origin] += 1
                total_correct_overall += 1
            else:
                # 틀린 문제 오답 노트에 추가 (중복 방지)
                if question_data not in self.incorrectly_answered_questions_data:
                    self.incorrectly_answered_questions_data.append(question_data)

        # 결과 텍스트 구성
        overall_feedback = f"모의고사 종료! 총 {total_questions_overall}문제 중 {total_correct_overall}개 정답입니다.\n"
        overall_feedback += f"경과 시간: {self.elapsed_seconds // 60:02}:{self.elapsed_seconds % 60:02}\n"

        subject_results_text = ""
        for subject_name, correct_count in subject_correct_counts.items():
            # 40문제 중 맞춘 개수를 100점 만점으로 환산
            # 모의고사당 각 과목은 40문제로 고정되어 있다고 가정
            score = (correct_count / 40) * 100 if 40 > 0 else 0
            subject_results_text += f"- {subject_name}: {correct_count}개 정답 (총 40문제 중), 점수: {score:.1f}점\n"

        self.overall_result_label.configure(text=overall_feedback)
        self.subject_results_label.configure(text=subject_results_text)
        self.result_display_frame.grid()  # 결과 프레임 보이게

        # 퀴즈 종료 후 버튼 프레임 활성화
        self.end_mock_buttons_frame.grid()
        self.restart_mock_button.grid(row=0, column=0, padx=10, sticky="ew")
        if (
            self.incorrectly_answered_questions_data
        ):  # 틀린 문제가 있을 경우에만 오답 노트 버튼 표시
            self.review_mock_incorrect_button.grid(
                row=0, column=1, padx=10, sticky="ew"
            )
        else:
            self.review_mock_incorrect_button.grid_remove()
        self.go_to_home_button.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew"
        )

        # UI 상태 변경
        self.question_label.configure(
            text="모의고사가 종료되었습니다. 결과를 확인하세요."
        )
        self.question_count_label.configure(text="")  # 문제 카운트 숨김
        self.time_label.configure(text="")  # 시간 숨김

    def _end_mock_exam_early(self):
        """사용자가 모의고사를 중간에 끝내기로 선택했을 때 호출."""
        if tkmb.askyesno(
            "모의고사 종료",
            "모의고사를 중간에 종료하시겠습니까?\n진행 상황은 저장되지 않습니다.",
        ):
            self._transition_to_mock_exam_end_state(early_exit=True)

    def _transition_to_mock_exam_end_state(self, early_exit=False):
        """모의고사 종료 시 UI 상태를 관리하는 헬퍼 함수 (조기 종료 포함)."""
        self._stop_timer()

        self.control_buttons_container.grid_remove()  # 문제 풀이 버튼 숨김
        for button in self.choice_buttons:  # 선택지 버튼 숨김
            button.grid_remove()

        if early_exit:
            self.overall_result_label.configure(
                text="모의고사를 중도 종료했습니다.\n다음에 다시 도전해주세요!"
            )
            self.subject_results_label.configure(text="")
        else:
            # 이 경우는 _end_mock_exam_and_show_results에서 이미 처리되므로 여기서는 빈 상태로 둠
            pass

        self.result_display_frame.grid()  # 결과 프레임 보이게
        self.question_label.configure(
            text="모의고사가 종료되었습니다. 결과를 확인하세요."
        )
        self.question_count_label.configure(text="")
        self.time_label.configure(text="")

        # 퀴즈 종료 후 버튼 프레임 활성화
        self.end_mock_buttons_frame.grid()
        self.restart_mock_button.grid(row=0, column=0, padx=10, sticky="ew")
        if (
            self.incorrectly_answered_questions_data and not early_exit
        ):  # 조기 종료 시에는 오답 노트 버튼 숨김
            self.review_mock_incorrect_button.grid(
                row=0, column=1, padx=10, sticky="ew"
            )
        else:
            self.review_mock_incorrect_button.grid_remove()
        self.go_to_home_button.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew"
        )

        # 내부 상태를 퀴즈 종료 상태로 설정
        self.current_mock_question_index = len(self.all_questions_for_mock_exam)
        self.current_review_question_index = len(
            self.incorrectly_answered_questions_data
        )
        self.is_review_mode = False

    def _restart_mock_exam(self):
        """새로운 모의고사를 시작합니다 (문제 재로드 및 셔플)."""
        self._stop_timer()
        self.current_mock_question_index = 0
        self.incorrectly_answered_questions_data = []
        self.user_answers = []
        self.is_review_mode = False  # 초기화 시 is_review_mode도 False로 설정

        self._load_mock_questions()  # 문제 다시 로드 및 섞기
        self._load_question()  # 첫 문제 로드
        self._start_timer()

        # UI 상태를 모의고사 진행 상태로 전환
        self.end_mock_buttons_frame.grid_remove()
        self.result_display_frame.grid_remove()
        self.control_buttons_container.grid()
        self.next_question_button.configure(
            text="다음 문제", command=self._next_question_or_show_results
        )
        self.end_mock_early_button.grid()  # 끝내기 버튼 다시 보이게

    def _start_review_mode(self):
        """모의고사 후 오답 노트 모드로 전환합니다."""
        if not self.incorrectly_answered_questions_data:
            tkmb.showinfo(
                "오답 없음", "현재 틀린 문제가 없습니다. 새로운 모의고사를 시작합니다."
            )
            self._restart_mock_exam()
            return

        self._stop_timer()
        self.is_review_mode = True
        self.current_review_question_index = 0
        random.shuffle(self.incorrectly_answered_questions_data)  # 오답 문제 다시 섞기

        self._load_question()  # 오답 노트 첫 문제 로드
        self._start_timer()

        # UI 상태를 오답 노트 진행 상태로 전환
        self.end_mock_buttons_frame.grid_remove()
        self.result_display_frame.grid()  # 결과/해설 표시 프레임을 다시 사용
        self.overall_result_label.configure(text="오답 노트", text_color="#E67E22")
        self.subject_results_label.configure(text="틀린 문제를 다시 풀어보세요.")

        self.control_buttons_container.grid()  # 정답 확인/다음 오답 버튼 표시
        self.next_question_button.configure(
            text="정답 확인 (오답 노트)", command=self._check_answer_in_review_mode
        )
        self.end_mock_early_button.grid_remove()  # 오답 노트 중에는 '모의고사 끝내기' 숨김 (대신 홈으로 가기)


if __name__ == "__main__":
    ctk.set_appearance_mode("System")  # 시스템 테마 사용 (Light/Dark)
    ctk.set_default_color_theme("blue")  # 기본 색상 테마 설정

    app = QuizApp()
    app.mainloop()
