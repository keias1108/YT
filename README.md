# 시니어층 유튜브 트렌드 추적 시스템

한국 시니어층이 실제로 소비하는 유튜브 트렌딩 영상을 추적하고 분석하는 시스템입니다.

## 프로젝트 개요

YouTube Data API v3에는 연령별 필터가 없기 때문에, **프록시 특징(키워드, 장르, 댓글, 채널 등)을 조합한 SeniorScore**를 개발하여 시니어층 친화 콘텐츠를 추정합니다.

### 핵심 기능

- **데이터 수집**: 한국(KR) 기준 선택 카테고리의 인기 영상 수집
- **스냅샷 저장**: 날짜별 스냅샷 저장 (`data/YYYY-MM-DD/videos.jsonl`)
- **SeniorScore 계산**: 키워드, 장르, 댓글, 채널, 영상 길이 기반 점수 산출
- **Δviews 계산**: 최근 14일간 조회수 증가량 추적
- **웹 UI**: 수집, 조회, 필터링, 라벨링 인터페이스
- **라벨링 시스템**: 주간 50개 수동 검수로 모델 개선

### 시스템 아키텍처

```
수집층 → 특징층 → 분류층(SeniorScore) → 랭킹층
```

## 설치 및 실행

### 1. 요구사항

- Python 3.8+
- YouTube Data API v3 키

### 2. 설치

```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env` 파일에 YouTube API 키를 추가하세요:

```
YOUTUBE_API_KEY=your_api_key_here
```

API 키 발급: [Google Cloud Console](https://console.cloud.google.com/) → YouTube Data API v3 활성화

### 4. 데이터베이스 초기화

```bash
python database.py
```

### 5. Flask 앱 실행

```bash
python app.py
```

웹 브라우저에서 `http://localhost:5000` 접속

## 사용 방법

### 1. 데이터 수집

1. 메인 페이지에서 원하는 카테고리 선택 (기본: Music, People & Blogs 등 7개)
2. "수집 시작" 버튼 클릭
3. 수집 완료 후 통계 확인

**중복 방지**: 같은 날짜에 이미 수집된 영상은 자동으로 스킵됩니다.

### 2. 데이터 조회

1. 조회 날짜 선택 (기본: 오늘)
2. SeniorScore 최소값 설정 (기본: 5.0)
3. "조회" 버튼 클릭
4. 테이블에서 결과 확인

**중요**: 조회는 **DB에서만** 읽으므로 API 쿼터를 소비하지 않습니다.

### 3. 라벨링

1. "라벨링 페이지로 이동" 클릭
2. 각 비디오에 대해:
   - "✅ 시니어 콘텐츠 맞음" 또는
   - "❌ 시니어 콘텐츠 아님" 선택
3. 주간 목표: 50개 라벨링

## SeniorScore 계산 로직

### 1. 키워드 점수 (w=1.0)
- 건강, 관절, 무릎, 혈당, 연금, 노후, 트로트, 가요무대 등
- 제목: 가중치 1.0, 설명: 가중치 0.5

### 2. 장르 점수 (w=1.5)
- 트로트, 국악, 전통, 교양, 다큐, 시사
- 트로트 가수명: 임영웅, 영탁, 이찬원 등

### 3. 댓글 점수 (w=0.5)
- 연령 지표: 어머니, 아버지, 손주, 무릎, 관절
- 존대 표현: ~하십니다, ~하세요

### 4. 채널 점수 (w=1.0)
- 화이트리스트/블랙리스트
- 구독자 수 보정 (소규모 채널 가중)

### 5. 영상 길이 점수 (w=0.8)
- Shorts(60초 미만): -2.0
- 3~30분: +2.0 (이상적)
- 30~60분: +1.0

### 6. Z세대 밈 감점
- ㅋㅋ, 실화냐, 개꿀, 레전드 등: -0.5/건

**최종 점수**: `SeniorScore = Σ(특징 × 가중치)`

## 프로젝트 구조

```
youtube api/
├── .env                      # API 키 (gitignore)
├── .gitignore
├── requirements.txt
├── README.md
├── app.py                    # Flask 메인 앱
├── database.py               # SQLite 스키마
├── youtube_api.py            # YouTube API 연동
├── senior_classifier.py      # SeniorScore 계산
├── data_collector.py         # 데이터 수집 및 스냅샷
├── youtube_senior_trends.db  # SQLite DB (자동 생성)
├── data/                     # 스냅샷 저장 폴더
│   └── 2025-11-05/
│       └── videos.jsonl
├── templates/
│   ├── index.html            # 메인 페이지
│   └── labeling.html         # 라벨링 페이지
└── static/
    ├── style.css
    └── app.js
```

## API 엔드포인트

- `GET /`: 메인 페이지
- `GET /labeling`: 라벨링 페이지
- `GET /api/categories`: 카테고리 목록
- `POST /api/collect`: 데이터 수집
- `GET /api/videos`: 비디오 조회 (DB에서)
- `GET /api/video/<id>`: 비디오 상세
- `POST /api/label`: 라벨 저장
- `GET /api/labels/unlabeled`: 라벨링 안 된 비디오
- `GET /api/stats`: 통계

## 데이터베이스 스키마

### videos
- 비디오 기본 정보 (video_id, title, channel_id 등)

### snapshots
- 일별 스냅샷 (video_id, snapshot_date, view_count, rank_position)
- UNIQUE 제약: (video_id, snapshot_date, category_id)

### senior_scores
- SeniorScore 계산 결과 (score, keyword_score, highlights 등)

### labels
- 사람이 라벨링한 결과 (is_senior_content, labeled_by 등)

### channels
- 채널 정보 및 가중치 (senior_weight, is_whitelist 등)

## 향후 개선 계획

1. **댓글 수집**: API 쿼터 관리하며 댓글 점수 정확도 향상
2. **ML 모델**: 라벨링 데이터로 로지스틱 회귀/랜덤 포레스트 학습
3. **스케줄링**: 매일 자동 수집 (cron/APScheduler)
4. **대시보드**: 주간/월간 트렌드 시각화
5. **알림**: 급상승 시니어 콘텐츠 자동 알림

## 메타벡터

> "한국 시니어층이 실제로 소비하는 트렌딩 영상을, 빠르고 재현 가능하게 포착해 바로 제작/기획에 쓸 수 있는 목록으로 뽑아낸다."

### 성공 기준

- **데이터 신선도**: 어제~오늘 업로드 포함, 매일 1회 스냅샷
- **정확도**: 시니어 여부 Precision ≥ 0.8 (주간 라벨로 측정)
- **발견성**: 상위 N개 중 구독자 10만 이하 비율 ≥ 40% (새 발굴)
- **실행성**: 추천 카드에 "핵심 키워드 요약 + 왜 시니어로 분류됐는지 근거" 표기

## 라이선스

MIT License

## 기여

이슈 및 PR 환영합니다!
