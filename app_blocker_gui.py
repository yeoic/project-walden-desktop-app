import tkinter as tk
from tkinter import messagebox, ttk
import psutil
import subprocess
import threading
import time
import os
import sys
import json
import socket
from datetime import datetime, timedelta

# macOS tkinter 경고 메시지 숨기기
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# TSM/IMK 에러 메시지 숨기기
if sys.platform == 'darwin':
    os.environ['TK_LIBRARY'] = '/System/Library/Frameworks/Tk.framework/Versions/Current/Resources'

# 단일 인스턴스 포트
SINGLE_INSTANCE_PORT = 47200


class AppBlockerGUI:
    # 설정 파일 경로
    CONFIG_FILE = os.path.expanduser("~/.focus_mode_config.json")

    def __init__(self, root):
        self.root = root
        self.root.title("맥북 집중 모드")

        # 창 크기는 내용에 맞게 자동, 사용자 조절 불가
        self.root.resizable(False, False)

        # 감시 상태 플래그
        self.is_running = False
        self.focus_duration = 0  # 총 집중 시간 (초)
        self.end_time = None  # 종료 시간 저장
        self.blocked_apps = []  # 차단할 앱 목록
        self.super_mode = False  # 슈퍼 감시 모드

        # 저장된 설정 불러오기
        self.load_config()

        # UI 구성
        self.create_widgets()

        # 블록 표시 업데이트 (저장된 앱 표시)
        self.update_blocks_display()

        # 화면 중앙 배치
        self.center_window()

        # 현재 시간 업데이트 시작
        self.update_current_time()

        # 창 닫을 때 설정 저장
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """창을 화면 중앙에 배치"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"+{x}+{y}")

    def load_config(self):
        """저장된 설정 불러오기"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.blocked_apps = config.get('blocked_apps', [])
        except Exception:
            self.blocked_apps = []

    def save_config(self):
        """설정 저장"""
        try:
            config = {
                'blocked_apps': self.blocked_apps
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def on_closing(self):
        """창 닫을 때 호출"""
        self.save_config()
        self.root.destroy()

    def create_widgets(self):
        # 1. 차단할 앱 선택
        header_frame = tk.Frame(self.root)
        header_frame.pack(pady=5)
        tk.Label(header_frame, text="차단할 앱", font=("", 11)).pack(side=tk.LEFT)
        self.select_btn = tk.Button(header_frame, text="+ 추가", command=self.open_app_selector)
        self.select_btn.pack(side=tk.LEFT, padx=5)
        self.clear_apps_btn = tk.Button(header_frame, text="초기화", command=self.clear_all_apps, fg="red")
        self.clear_apps_btn.pack(side=tk.LEFT, padx=5)

        # 블록 표시 영역
        self.block_container = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        self.block_container.pack(pady=5, padx=20, fill=tk.X)

        self.blocks_frame = tk.Frame(self.block_container)
        self.blocks_frame.pack(fill=tk.X, padx=5, pady=5)

        # 안내 레이블 (앱이 없을 때)
        self.no_app_label = tk.Label(self.blocks_frame, text="차단할 앱을 추가하세요", fg="gray")
        self.no_app_label.pack(pady=15)

        # 2. 현재 시간 표시
        time_frame = tk.Frame(self.root)
        time_frame.pack(pady=10)

        tk.Label(time_frame, text="현재 시간:", font=("", 14)).pack(side=tk.LEFT)
        self.current_time_label = tk.Label(time_frame, text="--:--:--", font=("", 24, "bold"), fg="#00FF00", bg="black", padx=10, pady=5)
        self.current_time_label.pack(side=tk.LEFT, padx=5)

        # 3. 빠른 시간 설정 버튼
        tk.Label(self.root, text="집중 시간 설정", font=("", 10)).pack(pady=(10, 5))

        # 플러스 버튼
        plus_btn_frame = tk.Frame(self.root)
        plus_btn_frame.pack(pady=3)

        tk.Button(plus_btn_frame, text="+5분", width=6,
                  command=lambda: self.set_duration(5)).pack(side=tk.LEFT, padx=3)
        tk.Button(plus_btn_frame, text="+10분", width=6,
                  command=lambda: self.set_duration(10)).pack(side=tk.LEFT, padx=3)
        tk.Button(plus_btn_frame, text="+30분", width=6,
                  command=lambda: self.set_duration(30)).pack(side=tk.LEFT, padx=3)
        tk.Button(plus_btn_frame, text="+1시간", width=6,
                  command=lambda: self.set_duration(60)).pack(side=tk.LEFT, padx=3)

        # 마이너스 버튼
        minus_btn_frame = tk.Frame(self.root)
        minus_btn_frame.pack(pady=3)

        tk.Button(minus_btn_frame, text="-5분", width=6,
                  command=lambda: self.set_duration(-5)).pack(side=tk.LEFT, padx=3)
        tk.Button(minus_btn_frame, text="-10분", width=6,
                  command=lambda: self.set_duration(-10)).pack(side=tk.LEFT, padx=3)
        tk.Button(minus_btn_frame, text="-30분", width=6,
                  command=lambda: self.set_duration(-30)).pack(side=tk.LEFT, padx=3)
        tk.Button(minus_btn_frame, text="초기화", width=6, fg="red",
                  command=self.reset_duration).pack(side=tk.LEFT, padx=3)

        # 직접 입력 (시, 분)
        direct_frame = tk.Frame(self.root)
        direct_frame.pack(pady=5)

        tk.Label(direct_frame, text="직접 입력:").pack(side=tk.LEFT)
        self.hour_entry = tk.Entry(direct_frame, width=4)
        self.hour_entry.insert(0, "0")
        self.hour_entry.pack(side=tk.LEFT, padx=2)
        tk.Label(direct_frame, text="시간").pack(side=tk.LEFT)
        self.min_entry = tk.Entry(direct_frame, width=4)
        self.min_entry.insert(0, "0")
        self.min_entry.pack(side=tk.LEFT, padx=2)
        tk.Label(direct_frame, text="분").pack(side=tk.LEFT)
        tk.Button(direct_frame, text="설정", command=self.set_manual_duration).pack(side=tk.LEFT, padx=5)

        # 4. 총 집중시간 표시
        duration_frame = tk.Frame(self.root)
        duration_frame.pack(pady=5)

        tk.Label(duration_frame, text="총 집중시간:", font=("", 11)).pack(side=tk.LEFT)
        self.duration_label = tk.Label(duration_frame, text="0분", font=("", 14, "bold"), fg="gray")
        self.duration_label.pack(side=tk.LEFT, padx=5)

        # 5. 종료 시간 표시
        end_frame = tk.Frame(self.root)
        end_frame.pack(pady=5)

        tk.Label(end_frame, text="종료 시간:", font=("", 11)).pack(side=tk.LEFT)
        self.end_time_label = tk.Label(end_frame, text="--:--:--", font=("", 14, "bold"), fg="gray")
        self.end_time_label.pack(side=tk.LEFT, padx=5)

        # 6. 상태 메시지
        self.status_label = tk.Label(self.root, text="대기 중...", fg="gray")
        self.status_label.pack(pady=20)

        # 7. 슈퍼 감시 모드 체크박스
        self.super_mode_var = tk.BooleanVar(value=False)
        super_frame = tk.Frame(self.root)
        super_frame.pack(pady=5)
        self.super_checkbox = tk.Checkbutton(
            super_frame,
            text="슈퍼 감시 (중지 불가)",
            variable=self.super_mode_var,
            command=self.toggle_super_mode,
            fg="#FF5555",
            font=("", 11, "bold")
        )
        self.super_checkbox.pack()

        # 8. 버튼 (시작/중지)
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=(10, 25))  # 하단 마진 추가

        # 시작 버튼 (초록 배경)
        self.start_frame = tk.Frame(self.btn_frame, bg="#4CAF50", padx=2, pady=2)
        self.start_frame.pack(side=tk.LEFT, padx=10)
        self.start_btn = tk.Label(self.start_frame, text="  감시 시작  ", bg="#4CAF50", fg="white",
                                   font=("", 12, "bold"), cursor="hand2")
        self.start_btn.pack()
        self.start_btn.bind("<Button-1>", lambda e: self.start_blocking())

        # 중지 버튼 (빨간 배경)
        stop_frame = tk.Frame(self.btn_frame, bg="#FF5555", padx=2, pady=2)
        stop_frame.pack(side=tk.LEFT, padx=10)
        self.stop_btn = tk.Label(stop_frame, text="  감시 중지  ", bg="#CCCCCC", fg="gray",
                                  font=("", 12, "bold"), cursor="hand2")
        self.stop_btn.pack()
        self.stop_frame = stop_frame

    def update_current_time(self):
        """현재 시간 업데이트 (1초마다)"""
        now = datetime.now().strftime("%H:%M:%S")
        self.current_time_label.config(text=now)

        # 감시 중이 아닐 때 종료 시간 실시간 업데이트
        if not self.is_running and self.focus_duration > 0:
            end_time = datetime.now() + timedelta(seconds=self.focus_duration)
            self.end_time_label.config(text=end_time.strftime("%H:%M:%S"), fg="green")

        # 남은 시간 업데이트 (감시 중일 때)
        if self.is_running and self.end_time:
            remaining = self.end_time - datetime.now()
            if remaining.total_seconds() > 0:
                mins, secs = divmod(int(remaining.total_seconds()), 60)
                hours, mins = divmod(mins, 60)
                if self.super_mode:
                    self.status_label.config(
                        text=f"슈퍼 감시 중! 남은 시간: {hours:02d}:{mins:02d}:{secs:02d}",
                        fg="#FF5555"
                    )
                else:
                    self.status_label.config(
                        text=f"감시 중! 남은 시간: {hours:02d}:{mins:02d}:{secs:02d}",
                        fg="red"
                    )

        self.root.after(1000, self.update_current_time)

    def set_duration(self, minutes):
        """빠른 시간 설정 (누적 방식)"""
        self.focus_duration += minutes * 60  # 초 단위로 누적

        # 0 이하면 초기화
        if self.focus_duration <= 0:
            self.reset_duration()
        else:
            self.update_duration_display()

    def update_duration_display(self):
        """총 집중시간과 종료 시간 표시 업데이트"""
        if self.focus_duration > 0:
            # 총 집중시간 표시
            hours = self.focus_duration // 3600
            mins = (self.focus_duration % 3600) // 60
            if hours > 0:
                self.duration_label.config(text=f"{hours}시간 {mins}분", fg="green")
            else:
                self.duration_label.config(text=f"{mins}분", fg="green")

            # 종료 시간 (현재 시간 + 집중 시간)
            end_time = datetime.now() + timedelta(seconds=self.focus_duration)
            self.end_time_label.config(text=end_time.strftime("%H:%M:%S"), fg="green")
        else:
            self.duration_label.config(text="0분", fg="gray")
            self.end_time_label.config(text="--:--:--", fg="gray")

    def reset_duration(self):
        """시간 초기화"""
        self.focus_duration = 0
        self.end_time = None
        self.duration_label.config(text="0분", fg="gray")
        self.end_time_label.config(text="--:--:--", fg="gray")

    def toggle_super_mode(self):
        """슈퍼 감시 모드 토글"""
        if self.super_mode_var.get():
            # 확인 대화상자 표시
            self.show_super_mode_confirm()
        else:
            self.super_mode = False

    def show_super_mode_confirm(self):
        """슈퍼 감시 모드 확인 대화상자"""
        dialog = tk.Toplevel(self.root)
        dialog.title("슈퍼 감시 모드")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 메시지
        msg_frame = tk.Frame(dialog, padx=20, pady=20)
        msg_frame.pack()

        tk.Label(
            msg_frame,
            text="슈퍼 감시를 체크하는 순간부터\n집중 시작 후, 중간에 중지하는게 불가능합니다.\n\n반드시 설정한 집중시간을 마무리해야\n다시 차단한 앱을 사용할 수 있습니다.",
            font=("", 12),
            justify=tk.CENTER
        ).pack()

        # 버튼 프레임
        btn_frame = tk.Frame(dialog, pady=15)
        btn_frame.pack()

        def on_confirm():
            self.super_mode = True
            dialog.destroy()

        def on_cancel():
            self.super_mode = False
            self.super_mode_var.set(False)
            dialog.destroy()

        # 예, 알겠습니다 버튼 (Label 기반)
        confirm_frame = tk.Frame(btn_frame, bg="#4CAF50", padx=2, pady=2)
        confirm_frame.pack(side=tk.LEFT, padx=5)
        confirm_btn = tk.Label(
            confirm_frame,
            text="  예, 알겠습니다  ",
            bg="#4CAF50",
            fg="white",
            font=("", 11),
            cursor="hand2"
        )
        confirm_btn.pack()
        confirm_btn.bind("<Button-1>", lambda e: on_confirm())

        # 취소 버튼 (Label 기반)
        cancel_frame = tk.Frame(btn_frame, bg="#888888", padx=2, pady=2)
        cancel_frame.pack(side=tk.LEFT, padx=5)
        cancel_btn = tk.Label(
            cancel_frame,
            text="  취소  ",
            bg="#888888",
            fg="white",
            font=("", 11),
            cursor="hand2"
        )
        cancel_btn.pack()
        cancel_btn.bind("<Button-1>", lambda e: on_cancel())

        # 대화상자 중앙 배치
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # X 버튼으로 닫을 때도 취소 처리
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    def update_blocks_display(self):
        """블록 UI 업데이트 (줄넘김 지원)"""
        # 기존 위젯 제거
        for widget in self.blocks_frame.winfo_children():
            widget.destroy()

        if not self.blocked_apps:
            self.no_app_label = tk.Label(self.blocks_frame, text="차단할 앱을 추가하세요", fg="gray")
            self.no_app_label.pack(pady=15)
            self.resize_window()
            return

        # 블록들을 줄넘김하며 배치
        max_width = 340  # 컨테이너 최대 너비
        current_row = tk.Frame(self.blocks_frame)
        current_row.pack(anchor="w", fill=tk.X, pady=2)
        current_width = 0

        for app_name in self.blocked_apps:
            # 블록 예상 너비 계산 (대략적)
            block_width = len(app_name) * 8 + 40

            # 줄넘김 필요시 새 행 생성
            if current_width + block_width > max_width and current_width > 0:
                current_row = tk.Frame(self.blocks_frame)
                current_row.pack(anchor="w", fill=tk.X, pady=2)
                current_width = 0

            block = tk.Frame(current_row, bg="#E3F2FD", relief=tk.RAISED, bd=1)
            block.pack(side=tk.LEFT, padx=2, pady=2)

            label = tk.Label(block, text=app_name, bg="#E3F2FD", fg="#1976D2",
                     font=("", 10), padx=5, pady=2)
            label.pack(side=tk.LEFT)

            # X 버튼
            close_btn = tk.Label(block, text="✕", bg="#E3F2FD", fg="#666",
                                  font=("", 9), cursor="hand2", padx=3)
            close_btn.pack(side=tk.LEFT)
            close_btn.bind("<Button-1>", lambda e, name=app_name: self.remove_blocked_app(name))

            current_width += block_width

        self.resize_window()

    def resize_window(self):
        """창 크기를 내용에 맞게 조절"""
        self.root.update_idletasks()

        # 위치 저장
        x = self.root.winfo_x()
        y = self.root.winfo_y()

        # geometry 초기화하여 자동 크기 계산
        self.root.geometry("")
        self.root.update_idletasks()

        # 위치 복원
        self.root.geometry(f"+{x}+{y}")

    def remove_blocked_app(self, app_name):
        """차단 앱 제거"""
        if app_name in self.blocked_apps:
            self.blocked_apps.remove(app_name)
            self.update_blocks_display()
            self.save_config()  # 자동 저장

    def clear_all_apps(self):
        """모든 차단 앱 초기화"""
        if self.blocked_apps:
            self.blocked_apps.clear()
            self.update_blocks_display()
            self.save_config()

    def set_manual_duration(self):
        """직접 입력한 시간 설정"""
        try:
            hours = int(self.hour_entry.get() or 0)
            mins = int(self.min_entry.get() or 0)
            total_minutes = hours * 60 + mins

            if total_minutes > 0:
                self.set_duration(total_minutes)
                self.hour_entry.delete(0, tk.END)
                self.hour_entry.insert(0, "0")
                self.min_entry.delete(0, tk.END)
                self.min_entry.insert(0, "0")
            else:
                messagebox.showwarning("경고", "1분 이상 입력해주세요.")
        except ValueError:
            messagebox.showerror("오류", "숫자를 입력해주세요.")

    def start_blocking(self):
        # 입력값 검증
        if not self.blocked_apps:
            messagebox.showwarning("경고", "차단할 앱을 추가해주세요.")
            return

        if self.focus_duration <= 0:
            messagebox.showwarning("경고", "종료 시간을 설정해주세요.\n(+5분, +10분 등 버튼을 눌러주세요)")
            return

        # 종료 시간 계산 (현재 시간 + 집중 시간)
        self.end_time = datetime.now() + timedelta(seconds=self.focus_duration)
        self.end_time_label.config(text=self.end_time.strftime("%H:%M:%S"), fg="red")

        self.target_apps = self.blocked_apps.copy()

        # UI 상태 변경
        self.is_running = True
        # 시작 버튼 비활성화
        self.start_btn.config(bg="#CCCCCC", fg="gray")
        self.start_frame.config(bg="#CCCCCC")
        self.start_btn.unbind("<Button-1>")
        # 슈퍼 감시 체크박스 비활성화
        self.super_checkbox.config(state=tk.DISABLED)

        # 중지 버튼 (슈퍼 모드면 비활성화 유지)
        if self.super_mode:
            self.stop_btn.config(bg="#CCCCCC", fg="gray")
            self.stop_frame.config(bg="#CCCCCC")
            self.status_label.config(text="슈퍼 감시 중! (중지 불가)", fg="#FF5555")
        else:
            self.stop_btn.config(bg="#FF5555", fg="white")
            self.stop_frame.config(bg="#FF5555")
            self.stop_btn.bind("<Button-1>", lambda e: self.stop_blocking())
        self.select_btn.config(state=tk.DISABLED)

        # 스레드 시작
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_blocking(self):
        self.is_running = False
        # 시작 버튼 활성화
        self.start_btn.config(bg="#4CAF50", fg="white")
        self.start_frame.config(bg="#4CAF50")
        self.start_btn.bind("<Button-1>", lambda e: self.start_blocking())
        # 중지 버튼 비활성화
        self.stop_btn.config(bg="#CCCCCC", fg="gray")
        self.stop_frame.config(bg="#CCCCCC")
        self.stop_btn.unbind("<Button-1>")
        self.select_btn.config(state=tk.NORMAL)
        # 슈퍼 감시 모드 초기화
        self.super_mode = False
        self.super_mode_var.set(False)
        self.super_checkbox.config(state=tk.NORMAL)
        # 종료 시간만 초기화 (설정한 집중시간은 유지)
        self.end_time = None
        self.status_label.config(text="대기 중...", fg="gray")
        # 종료 시간은 현재시간 기준으로 다시 표시
        if self.focus_duration > 0:
            end_time = datetime.now() + timedelta(seconds=self.focus_duration)
            self.end_time_label.config(text=end_time.strftime("%H:%M:%S"), fg="green")

    def open_app_selector(self):
        """프로그램 선택 팝업 창 열기"""
        # 새 팝업 창 생성
        self.selector_window = tk.Toplevel(self.root)
        self.selector_window.title("프로그램 선택")
        self.selector_window.geometry("400x500")
        self.selector_window.resizable(False, False)  # 크기 고정
        self.selector_window.transient(self.root)  # 부모 창 위에 표시
        self.selector_window.grab_set()  # 모달 창으로 설정

        # 상단 영역 (제목 + 검색) - 고정
        top_frame = tk.Frame(self.selector_window)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="차단할 프로그램을 선택하세요",
                 font=("", 12, "bold")).pack(pady=10)

        search_frame = tk.Frame(top_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="검색:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_app_list)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        # 하단 버튼 영역 - 먼저 pack (항상 보이게)
        btn_frame = tk.Frame(self.selector_window)
        btn_frame.pack(side=tk.BOTTOM, pady=10)

        # 선택 완료 버튼 (Label로 구현)
        confirm_frame = tk.Frame(btn_frame, bg="#4CAF50", padx=2, pady=2)
        confirm_frame.pack(side=tk.LEFT, padx=5)
        confirm_btn = tk.Label(confirm_frame, text="  선택 완료  ", bg="#4CAF50", fg="white",
                               font=("", 11), cursor="hand2")
        confirm_btn.pack()
        confirm_btn.bind("<Button-1>", lambda e: self.confirm_selection())

        # 취소 버튼
        cancel_frame = tk.Frame(btn_frame, bg="#888888", padx=2, pady=2)
        cancel_frame.pack(side=tk.LEFT, padx=5)
        cancel_btn = tk.Label(cancel_frame, text="  취소  ", bg="#888888", fg="white",
                              font=("", 11), cursor="hand2")
        cancel_btn.pack()
        cancel_btn.bind("<Button-1>", lambda e: self.selector_window.destroy())

        # 중간 영역 (스크롤 가능한 앱 목록) - 나머지 공간 차지
        container = tk.Frame(self.selector_window)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(container)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 마우스 휠 스크롤 바인딩
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)

        # 현재 실행 중인 응용프로그램 목록 가져오기
        self.running_apps = self.get_running_apps()
        self.app_checkboxes = {}
        self.checkbox_widgets = {}

        # 이미 선택된 앱들 체크 상태로 초기화
        for app_name in self.running_apps:
            self.app_checkboxes[app_name] = tk.BooleanVar(value=(app_name in self.blocked_apps))

        self.display_app_list(self.running_apps)

    def display_app_list(self, apps):
        """앱 목록을 체크박스로 표시"""
        # 기존 위젯 제거
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.checkbox_widgets = {}

        for app_name in apps:
            # 기존 체크 상태 유지
            if app_name not in self.app_checkboxes:
                self.app_checkboxes[app_name] = tk.BooleanVar(value=(app_name in self.blocked_apps))

            var = self.app_checkboxes[app_name]
            cb = tk.Checkbutton(self.scrollable_frame, text=app_name, variable=var, anchor="w")
            cb.pack(fill=tk.X, padx=5, pady=2)
            cb.bind("<MouseWheel>", self._on_mousewheel)  # 휠 스크롤 바인딩
            self.checkbox_widgets[app_name] = cb

        # 스크롤 맨 위로
        self.canvas.yview_moveto(0)

        # 스크롤 필요 여부에 따라 활성화/비활성화
        self.scrollable_frame.update_idletasks()
        if len(apps) <= 12:  # 약 12개 이하면 스크롤 불필요
            self.scroll_enabled = False
        else:
            self.scroll_enabled = True

    def _on_mousewheel(self, event):
        """마우스 휠 스크롤 처리 (macOS)"""
        # 스크롤 비활성화 상태면 무시
        if not getattr(self, 'scroll_enabled', True):
            return

        # macOS에서는 delta 값이 다름
        if sys.platform == 'darwin':
            self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def filter_app_list(self, *args):
        """검색어로 앱 목록 필터링"""
        search_text = self.search_var.get().lower()

        if search_text:
            filtered_apps = [app for app in self.running_apps if search_text in app.lower()]
        else:
            filtered_apps = self.running_apps

        self.display_app_list(filtered_apps)

    def get_running_apps(self):
        """설치된 앱 + 실행 중인 앱 반환 (macOS)"""
        apps = set()

        # 시스템 앱 및 자기 자신 제외
        exclude = {'Automator', 'Boot Camp Assistant', 'Bluetooth File Exchange',
                   'ColorSync Utility', 'Console', 'Digital Color Meter', 'Disk Utility',
                   'DVD Player', 'Font Book', 'Grapher', 'Keychain Access',
                   'Migration Assistant', 'Screenshot', 'Stickies', 'System Preferences',
                   'System Information', 'Terminal', 'VoiceOver Utility', 'AirPort Utility',
                   'Audio MIDI Setup', 'Directory Utility', 'Wireless Diagnostics',
                   'loginwindow', 'WindowServer', 'Dock', 'SystemUIServer', 'Finder',
                   'ControlCenter', 'NotificationCenter', 'Siri',
                   '집중모드', 'Python', 'python3'}

        # 1. /Applications 폴더에서 설치된 앱 가져오기
        app_dirs = ['/Applications', os.path.expanduser('~/Applications')]
        for app_dir in app_dirs:
            try:
                if os.path.exists(app_dir):
                    for item in os.listdir(app_dir):
                        if item.endswith('.app'):
                            app_name = item[:-4]  # .app 제거
                            apps.add(app_name)
            except Exception:
                pass

        # 2. 실행 중인 GUI 앱도 추가
        try:
            result = subprocess.run(
                ['osascript', '-e',
                 'tell application "System Events" to get name of every process whose background only is false'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                app_list = result.stdout.strip().split(', ')
                for app in app_list:
                    app = app.strip()
                    if app and app not in exclude:
                        apps.add(app)
        except Exception:
            pass

        # 제외 목록 적용
        apps = {app for app in apps if app not in exclude}

        return sorted(apps)

    def confirm_selection(self):
        """선택한 앱들을 블록 리스트에 추가/제거"""
        selected_apps = [name for name, var in self.app_checkboxes.items() if var.get()]
        unselected_apps = [name for name, var in self.app_checkboxes.items() if not var.get()]

        # 새로 선택한 앱 추가 (중복 제거)
        for app in selected_apps:
            if app not in self.blocked_apps:
                self.blocked_apps.append(app)

        # 체크 해제한 앱 제거
        for app in unselected_apps:
            if app in self.blocked_apps:
                self.blocked_apps.remove(app)

        # 블록 UI 업데이트
        self.update_blocks_display()
        self.save_config()  # 자동 저장

        self.selector_window.destroy()

    def monitor_loop(self):
        """실제 감시 로직이 돌아가는 백그라운드 스레드"""
        while self.is_running:
            # 종료 시간 체크
            if self.end_time and datetime.now() >= self.end_time:
                # 메인 스레드에서 stop_blocking 호출
                self.root.after(0, self.stop_blocking)
                break

            # 앱 차단
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in self.target_apps:
                        app_name = proc.info['name']
                        proc.kill()
                        print(f"차단됨: {app_name}")
                        # 알림 표시
                        self.show_block_notification(app_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            time.sleep(1)  # CPU 과부하 방지

    def show_block_notification(self, app_name):
        """차단 알림 표시"""
        message = f"[{app_name}] 차단됨!\\n\\n1분 1초가 아깝다!\\n하던 일을 마무리 하세요!"
        subprocess.run([
            'osascript', '-e',
            f'display dialog "{message}" with title "집중 모드" buttons {{"확인"}} default button "확인" with icon caution'
        ], capture_output=True)


def check_single_instance():
    """단일 인스턴스 체크 - 이미 실행 중이면 기존 창을 앞으로"""
    try:
        # 소켓 생성 시도
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('localhost', SINGLE_INSTANCE_PORT))
        server_socket.listen(1)
        return server_socket  # 첫 번째 인스턴스
    except OSError:
        # 이미 실행 중 - 기존 인스턴스에 신호 보내기
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('localhost', SINGLE_INSTANCE_PORT))
            client.send(b'RAISE')
            client.close()
        except:
            pass
        return None  # 두 번째 인스턴스 (종료해야 함)


def listen_for_raise(server_socket, root):
    """다른 인스턴스의 요청을 듣고 창을 앞으로 가져옴"""
    while True:
        try:
            client, addr = server_socket.accept()
            data = client.recv(1024)
            if data == b'RAISE':
                # 메인 스레드에서 창을 앞으로 가져옴
                root.after(0, bring_to_front, root)
            client.close()
        except:
            break


def bring_to_front(root):
    """창을 최상위로 가져옴"""
    root.deiconify()  # 최소화되어 있으면 복원
    root.lift()  # 창을 위로
    root.focus_force()  # 포커스
    # macOS에서 확실히 앞으로 가져오기
    if sys.platform == 'darwin':
        subprocess.run([
            'osascript', '-e',
            'tell application "System Events" to set frontmost of process "Python" to true'
        ], capture_output=True)


# 메인 실행부
if __name__ == "__main__":
    # 단일 인스턴스 체크
    server_socket = check_single_instance()

    if server_socket is None:
        # 이미 실행 중 - 종료
        sys.exit(0)

    # 첫 번째 인스턴스 - 정상 실행
    root = tk.Tk()
    app = AppBlockerGUI(root)

    # 다른 인스턴스 요청 리스너 시작
    listener_thread = threading.Thread(target=listen_for_raise, args=(server_socket, root), daemon=True)
    listener_thread.start()

    root.mainloop()

    # 종료 시 소켓 정리
    server_socket.close()
