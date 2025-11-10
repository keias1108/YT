# YouTube DOM 구조 참조 가이드

> **작성일**: 2025-01-11
> **목적**: Chrome 확장 프로그램 개발 시 YouTube DOM 구조 참조용
> **주의**: YouTube는 UI를 자주 업데이트하므로, 이 문서의 정보가 outdated될 수 있습니다.

---

## 📋 목차

1. [검색 결과 페이지](#1-검색-결과-페이지)
2. [영상 시청 페이지 (Watch Page)](#2-영상-시청-페이지-watch-page)
3. [채널 페이지](#3-채널-페이지)
4. [공통 요소](#4-공통-요소)

---

## 1. 검색 결과 페이지

**URL 패턴**: `https://www.youtube.com/results?search_query=...`

### 비디오 아이템 구조

```
ytd-video-renderer (각 검색 결과)
├── ytd-channel-name
│   └── #text (채널명 텍스트)
└── #channel-info (보이는 영역)
    └── ytd-channel-name (실제 표시되는 채널명)
```

### 셀렉터

| 용도 | 셀렉터 | 설명 |
|------|--------|------|
| 모든 검색 결과 | `ytd-video-renderer` | 검색 결과의 각 비디오 아이템 |
| 채널명 추출 | `ytd-channel-name #text` | 채널명 텍스트 추출용 |
| 채널 정보 영역 | `#channel-info` | 체크마크 삽입 대상 영역 |
| 체크마크 삽입 위치 | `#channel-info ytd-channel-name` | 이 요소 다음에 체크마크 삽입 |

### 구현 코드 참조

- **함수**: `markSearchResults()` (content.js:88-147)
- **초기화**: `initSearchPage()` (content.js:150-181)

### 무한 스크롤 감지

- **방법**: setInterval (2초마다 비디오 개수 체크)
- **이유**: 간단하고 안정적

```javascript
const currentVideoCount = document.querySelectorAll('ytd-video-renderer').length;
if (currentVideoCount > previousVideoCount) {
    // 새 비디오 로드됨
}
```

---

## 2. 영상 시청 페이지 (Watch Page)

**URL 패턴**: `https://www.youtube.com/watch?v=...`

### 관련 영상 목록 구조

```
#secondary (오른쪽 사이드바)
└── #related (관련 영상 섹션)
    └── ytd-watch-next-secondary-results-renderer
        └── #items
            └── ytd-item-section-renderer
                └── yt-lockup-view-model (각 관련 영상) ⭐
                    ├── .yt-lockup-view-model__metadata
                    │   └── yt-lockup-metadata-view-model
                    │       └── .yt-lockup-metadata-view-model__text-container
                    │           └── .yt-content-metadata-view-model__metadata-row (여러 개)
                    │               └── .yt-core-attributed-string (4개)
                    │                   ├── [0]: 영상 제목
                    │                   ├── [1]: 채널명 ⭐⭐⭐
                    │                   ├── [2]: 조회수
                    │                   └── [3]: 업로드 시간
```

### 셀렉터

| 용도 | 셀렉터 | 설명 |
|------|--------|------|
| 관련 영상 컨테이너 | `#related` | MutationObserver 감시 대상 |
| 모든 관련 영상 | `#related yt-lockup-view-model` | 각 관련 영상 아이템 |
| 채널명 추출 | `.yt-core-attributed-string` | 4개 중 **두 번째(인덱스 1)** |
| 체크마크 삽입 위치 | `textElements[1].parentElement` | 채널명의 부모 div |

### 채널명 추출 방법

```javascript
const lockup = document.querySelector('#related yt-lockup-view-model');
const textElements = lockup.querySelectorAll('.yt-core-attributed-string');
const channelName = textElements[1].textContent.trim(); // 인덱스 1 = 채널명
```

### 구현 코드 참조

- **함수**: `markRelatedVideos()` (content.js:189-235)
- **초기화**: `initWatchPage()` (content.js:260-271)
- **무한 스크롤 감지**: `setupRelatedVideosObserver()` (content.js:238-257)

### 무한 스크롤 감지

- **방법**: MutationObserver
- **이유**: 실시간 DOM 변경 감지, 더 정확하고 효율적

```javascript
const observer = new MutationObserver(() => {
    markRelatedVideos(); // 새 영상 로드 시 자동 실행
});

observer.observe(relatedSection, {
    childList: true,
    subtree: true
});
```

### 테스트 결과

- **초기 로드**: 18~20개
- **스크롤당 증가**: 15~20개씩
- **테스트 데이터**: 18 → 37 → 55 → 75 → 94 → 114 → 134 → ...

---

## 3. 채널 페이지

**URL 패턴**:
- `https://www.youtube.com/channel/UC...`
- `https://www.youtube.com/@username`

### 버튼 삽입 위치 셀렉터

```javascript
const selectors = [
    'ytd-c4-tabbed-header-renderer #buttons',
    '#page-header tp-yt-paper-button',
    'ytd-browse[page-subtype="channels"] #buttons',
    'ytd-c4-tabbed-header-renderer .page-header-view-model-wiz__page-header-headline',
    '#channel-header-container'
];
```

### 구현 코드 참조

- **함수**: `addButtonToChannelPage()` (content.js:378-422)

---

## 4. 공통 요소

### 체크마크 스타일

```javascript
const mark = document.createElement('span');
mark.className = 'senior-channel-mark';
mark.innerHTML = '✅';
mark.title = '시니어 채널로 등록됨';
mark.style.marginLeft = '6px'; // Watch 페이지용
```

**CSS**: `style.css`

### 채널명 정규화

```javascript
const channelName = rawChannelName.toLowerCase().trim();
```

- 모든 채널명을 **소문자 + trim**으로 통일
- `registeredChannelNames` Set에 저장하여 O(1) 검색

### 중복 처리 방지

```javascript
if (element.dataset.seniorChecked === 'true') return;
element.dataset.seniorChecked = 'true';
```

---

## 🛠️ 디버깅 팁

### 콘솔에서 DOM 구조 확인

#### 검색 페이지
```javascript
// 비디오 개수
document.querySelectorAll('ytd-video-renderer').length

// 첫 번째 비디오의 채널명
document.querySelector('ytd-video-renderer ytd-channel-name #text').textContent
```

#### Watch 페이지
```javascript
// 관련 영상 개수
document.querySelectorAll('#related yt-lockup-view-model').length

// 첫 번째 관련 영상의 모든 텍스트 요소
const lockup = document.querySelector('#related yt-lockup-view-model');
const texts = lockup.querySelectorAll('.yt-core-attributed-string');
Array.from(texts).map(t => t.textContent.trim());
// [0]: 제목, [1]: 채널명, [2]: 조회수, [3]: 시간

// MutationObserver 테스트
const observer = new MutationObserver((mutations) => {
    const count = document.querySelectorAll('#related yt-lockup-view-model').length;
    console.log('🔔 관련 영상 개수:', count);
});
observer.observe(document.querySelector('#related'), {
    childList: true,
    subtree: true
});
```

---

## ⚠️ 주의사항

1. **YouTube UI 변경**: YouTube는 자주 UI를 업데이트합니다. 셀렉터가 작동하지 않으면 이 문서를 업데이트하세요.

2. **새 UI 감지 방법**:
   ```javascript
   // 페이지의 모든 YTD 요소 타입 확인
   const allYtdElements = document.querySelectorAll('*');
   const ytdTypes = new Set();
   allYtdElements.forEach(el => {
       if (el.tagName.startsWith('YTD-')) {
           ytdTypes.add(el.tagName.toLowerCase());
       }
   });
   console.log('YTD 요소 타입들:', Array.from(ytdTypes).sort());
   ```

3. **로드 타이밍**: YouTube는 SPA이므로 요소가 동적으로 로드됩니다. 재시도 로직과 MutationObserver 사용이 필수입니다.

4. **버전 관리**: DOM 구조가 변경되면 이 문서의 작성일을 업데이트하고, 변경 이력을 기록하세요.

---

## 📝 변경 이력

| 날짜 | 변경 내용 | 작성자 |
|------|----------|--------|
| 2025-01-11 | 초기 문서 작성 (검색 페이지, Watch 페이지) | - |

---

## 🔗 관련 파일

- **content.js**: 메인 로직
- **style.css**: 체크마크 스타일
- **manifest.json**: 확장 프로그램 설정
