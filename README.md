# 집중모드 (Focus Mode) - macOS App Blocker

macOS용 앱 차단 프로그램입니다. 집중이 필요할 때 방해가 되는 앱들을 일시적으로 차단할 수 있습니다.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 주요 기능

- **앱 차단**: 설정한 시간 동안 선택한 앱들을 자동으로 종료
- **슈퍼 감시 모드**: 한번 시작하면 설정한 시간이 끝날 때까지 중지 불가
- **시간 설정**: 버튼(+5분, +10분 등)으로 간편하게 설정하거나 직접 입력
- **설정 저장**: 차단 앱 목록이 자동으로 저장되어 다음 실행 시 유지
- **단일 인스턴스**: 앱을 중복 실행해도 하나의 창만 유지

## 스크린샷

```
┌─────────────────────────────────────┐
│         맥북 집중 모드               │
├─────────────────────────────────────┤
│  차단할 앱  [+ 추가] [초기화]        │
│  ┌─────────────────────────────┐   │
│  │ Chrome ✕  Slack ✕  KakaoTalk ✕│  │
│  └─────────────────────────────┘   │
│                                     │
│  현재 시간: 14:30:25               │
│                                     │
│  [+5분] [+10분] [+30분] [+1시간]   │
│  [-5분] [-10분] [-30분] [초기화]   │
│                                     │
│  총 집중시간: 30분                  │
│  종료 시간: 15:00:25               │
│                                     │
│  ☑ 슈퍼 감시 (중지 불가)           │
│                                     │
│  [감시 시작]  [감시 중지]           │
└─────────────────────────────────────┘
```

## 설치 방법

### 방법 1: 빌드된 앱 사용 (권장)
1. `dist/집중모드.app`을 Applications 폴더로 복사
2. 앱 실행

### 방법 2: 소스에서 직접 실행
```bash
# 의존성 설치
pip3 install psutil

# 실행
python3 app_blocker_gui.py
```

### 방법 3: 직접 빌드
```bash
# 의존성 설치
pip3 install psutil pyinstaller

# 빌드
pyinstaller --onefile --windowed --name "집중모드" \
  --icon=icon.icns \
  --hidden-import=psutil \
  app_blocker_gui.py

# 앱 서명 (선택사항)
codesign --force --deep --sign - dist/집중모드.app
```

## 사용 방법

1. **앱 선택**: `+ 추가` 버튼을 눌러 차단할 앱 선택
2. **시간 설정**: 버튼으로 집중 시간 설정 (누적 방식)
3. **슈퍼 감시** (선택): 체크하면 중지 불가 모드 활성화
4. **시작**: `감시 시작` 버튼 클릭

## 기술 스택

- **언어**: Python 3.8+
- **GUI**: tkinter
- **프로세스 관리**: psutil
- **빌드**: PyInstaller

## 파일 구조

```
PythonProject/
├── app_blocker_gui.py    # 메인 애플리케이션
├── icon.png              # 앱 아이콘 원본
├── icon.icns             # macOS 아이콘
├── 집중모드.spec         # PyInstaller 설정
├── dist/                 # 빌드된 앱
│   └── 집중모드.app
└── README.md
```

## 설정 파일

앱 설정은 `~/.focus_mode_config.json`에 저장됩니다.

```json
{
  "blocked_apps": ["Chrome", "Slack", "KakaoTalk"]
}
```

## 시스템 요구사항

- macOS 10.14 이상
- Python 3.8+ (소스 실행 시)

## 알려진 제한사항

- macOS 전용 (Windows/Linux 미지원)
- 일부 시스템 앱은 차단 불가
- 접근성 권한 필요 (시스템 환경설정에서 허용)

## 라이선스

MIT License
