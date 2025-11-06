# 시니어 유튜브 트렌드 - 크롬 확장 프로그램

유튜브 채널을 시니어 트렌드 추적 시스템에 바로 등록할 수 있는 크롬 확장 프로그램입니다.

## 설치 방법

### 1. 아이콘 이미지 준비

`icons/` 폴더에 다음 크기의 아이콘을 추가하세요:
- `icon16.png` (16x16)
- `icon48.png` (48x48)
- `icon128.png` (128x128)

**임시로 사용하기**: 온라인 아이콘 생성기(예: favicon.io)에서 간단한 아이콘을 만들 수 있습니다.
텍스트를 "📺" 또는 "S"로 입력하고 다운로드하세요.

### 2. 크롬에 로드

1. 크롬 브라우저에서 `chrome://extensions` 접속
2. 우측 상단 **개발자 모드** 활성화
3. **압축해제된 확장 프로그램을 로드합니다** 클릭
4. 이 폴더(`chrome-extension`) 선택
5. 완료!

## 사용 방법

### 방법 1: 유튜브에서 직접 등록

1. 유튜브 채널 페이지 방문 (예: https://www.youtube.com/channel/UCxxxxxx)
2. 페이지 상단에 **"⭐ 시니어 채널로 등록"** 버튼이 나타남
3. 버튼 클릭 → 자동으로 시스템에 등록됨

### 방법 2: 확장 아이콘 클릭

1. 크롬 우측 상단 확장 아이콘 클릭
2. **"📋 채널 관리"** 클릭
3. 채널 관리 페이지에서 수동 등록

## 주의사항

### Flask 서버 실행 필수

확장 프로그램은 `http://localhost:5000`에서 실행 중인 Flask 서버와 통신합니다.

Flask 서버가 실행 중이지 않으면:
```bash
cd "C:\Users\82103\Desktop\py\youtube api"
.\venv\Scripts\Activate.ps1
python app.py
```

### CORS 설정

만약 CORS 오류가 발생하면 `app.py`에 다음 추가:

```python
from flask_cors import CORS
CORS(app)
```

그리고 requirements.txt에 추가:
```
flask-cors==4.0.0
```

## 문제 해결

### 버튼이 나타나지 않음

1. 채널 페이지인지 확인 (`/channel/UCxxxx` 형식)
2. 페이지 새로고침 (F5)
3. 개발자 콘솔 확인 (F12 → Console 탭)

### "서버 연결 실패" 오류

1. Flask 서버 실행 여부 확인
2. `http://localhost:5000` 접속 테스트
3. 방화벽 설정 확인

### 채널 ID를 찾을 수 없음

- `/@handle` 형식 URL은 자동 추출이 어려울 수 있음
- URL을 `/channel/UCxxxx` 형식으로 변경 후 재시도
- 또는 웹 페이지(`/channels`)에서 수동 등록

## 파일 구조

```
chrome-extension/
├── manifest.json          # 확장 설정
├── content.js            # 유튜브 페이지에 버튼 삽입
├── background.js         # Flask API 통신
├── popup.html            # 확장 팝업 UI
├── popup.js              # 팝업 로직
├── style.css             # 버튼 스타일
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md
```

## 작동 원리

1. **content.js**: 유튜브 채널 페이지에서 실행, 채널 ID 추출 및 버튼 추가
2. **background.js**: 버튼 클릭 시 Flask API로 POST 요청 전송
3. **Flask API**: `/api/channels/add` 엔드포인트로 채널 정보 저장
4. **결과**: 성공/실패 알림 표시

## 개발자 모드

개발 시 유용한 팁:

- 코드 수정 후 `chrome://extensions`에서 새로고침 버튼 클릭
- 콘솔 로그: F12 → Console 탭
- background.js 디버깅: 확장 상세 페이지 → "서비스 워커" 클릭
