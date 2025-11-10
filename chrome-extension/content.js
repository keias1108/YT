/**
 * 유튜브 페이지에서 채널 ID 추출 및 등록 버튼 추가
 *
 * 📌 YouTube DOM 구조 참조: YOUTUBE_DOM_STRUCTURE.md
 *    - 검색 페이지 셀렉터
 *    - Watch 페이지 관련 영상 셀렉터
 *    - 채널 페이지 버튼 위치
 *    - 디버깅 팁 및 예제 코드
 */

// 현재 페이지의 채널 ID 추출
function extractChannelId() {
    // 방법 1: URL에서 추출 (/channel/UCxxxx)
    const urlMatch = window.location.href.match(/\/channel\/(UC[\w-]+)/);
    if (urlMatch) {
        return urlMatch[1];
    }

    // 방법 2: 페이지 HTML에서 추출
    const linkElement = document.querySelector('link[rel="canonical"]');
    if (linkElement) {
        const canonicalMatch = linkElement.href.match(/\/channel\/(UC[\w-]+)/);
        if (canonicalMatch) {
            return canonicalMatch[1];
        }
    }

    // 방법 3: ytInitialData에서 추출
    try {
        const scripts = document.querySelectorAll('script');
        for (const script of scripts) {
            const content = script.textContent;
            if (content.includes('ytInitialData')) {
                const channelIdMatch = content.match(/"channelId":"(UC[\w-]+)"/);
                if (channelIdMatch) {
                    return channelIdMatch[1];
                }
            }
        }
    } catch (e) {
        console.error('채널 ID 추출 실패:', e);
    }

    return null;
}

// 채널 페이지인지 확인
function isChannelPage() {
    const path = window.location.pathname;
    // 채널 페이지만 감지 (동영상 페이지 제외)
    return (path.includes('/channel/') || path.includes('/@')) &&
           !path.includes('/watch');
}

// 동영상 시청 페이지인지 확인
function isVideoPage() {
    return window.location.pathname === '/watch' &&
           window.location.search.includes('v=');
}

// 검색 결과 페이지인지 확인
function isSearchPage() {
    return window.location.pathname === '/results' &&
           window.location.search.includes('search_query=');
}

// 등록된 채널명 캐시 (소문자로 정규화)
let registeredChannelNames = new Set();
let channelNamesLoaded = false;

// 등록된 채널명 로드
function loadRegisteredChannels() {
    if (channelNamesLoaded) return Promise.resolve();

    return new Promise((resolve) => {
        chrome.runtime.sendMessage(
            { action: 'getChannelNames' },
            (response) => {
                if (response && response.success && response.channelNames) {
                    // 소문자로 정규화하여 저장
                    registeredChannelNames = new Set(
                        response.channelNames.map(name => name.toLowerCase().trim())
                    );
                    channelNamesLoaded = true;
                    console.log('[시니어 채널] 등록된 채널:', registeredChannelNames.size, '개');
                }
                resolve();
            }
        );
    });
}

// 검색 결과의 비디오 항목에 마크 추가
// DOM 구조: YOUTUBE_DOM_STRUCTURE.md > "1. 검색 결과 페이지" 참조
function markSearchResults() {
    const videoRenderers = document.querySelectorAll('ytd-video-renderer');
    console.log('[시니어 채널] 검색 결과 비디오 수:', videoRenderers.length);

    let markedCount = 0;

    videoRenderers.forEach((video, index) => {
        // 이미 처리된 항목은 스킵
        if (video.dataset.seniorChecked === 'true') return;
        video.dataset.seniorChecked = 'true';

        // ytd-channel-name 요소 찾기
        const channelNameContainer = video.querySelector('ytd-channel-name');
        if (!channelNameContainer) {
            console.warn('[시니어 채널] ytd-channel-name을 찾을 수 없음:', index);
            return;
        }

        // 채널명 텍스트 추출
        const channelNameElement = channelNameContainer.querySelector('#text');
        if (!channelNameElement) {
            console.warn('[시니어 채널] #text를 찾을 수 없음:', index);
            return;
        }

        const channelName = channelNameElement.textContent.trim().toLowerCase();

        // 첫 3개만 로그 (디버깅)
        if (index < 3) {
            console.log(`[시니어 채널] 비디오 ${index}: "${channelName}"`);
        }

        // 등록된 채널인지 확인
        if (registeredChannelNames.has(channelName)) {
            // #channel-info 안에서 확인 (보이는 영역)
            const channelInfo = video.querySelector('#channel-info');
            if (!channelInfo) return;

            // 이미 마크가 있으면 스킵
            if (channelInfo.querySelector('.senior-channel-mark')) return;

            // #channel-info 안의 ytd-channel-name 찾기
            const visibleChannelName = channelInfo.querySelector('ytd-channel-name');
            if (!visibleChannelName) return;

            // 체크 마크 추가
            const mark = document.createElement('span');
            mark.className = 'senior-channel-mark';
            mark.innerHTML = '✅';
            mark.title = '시니어 채널로 등록됨';

            // ytd-channel-name 바로 다음에 추가 (#channel-info 안)
            channelInfo.insertBefore(mark, visibleChannelName.nextSibling);
            markedCount++;
            console.log('[시니어 채널] 마크 추가:', channelName);
        }
    });

    console.log(`[시니어 채널] 총 ${markedCount}개 채널에 마크 추가됨`);
}

// 검색 결과 페이지 초기화
async function initSearchPage() {
    console.log('[시니어 채널] 검색 결과 페이지 초기화');

    // 채널명 로드
    await loadRegisteredChannels();

    // 현재 결과에 마크 추가
    markSearchResults();

    // 비디오 개수 체크로 무한 스크롤 감지
    let previousVideoCount = 0;

    const checkForNewVideos = () => {
        const currentVideoCount = document.querySelectorAll('ytd-video-renderer').length;

        if (currentVideoCount > previousVideoCount) {
            console.log(`[시니어 채널] 새 비디오 감지 (${previousVideoCount} → ${currentVideoCount})`);
            previousVideoCount = currentVideoCount;
            markSearchResults();
        }
    };

    // 2초마다 체크
    const intervalId = setInterval(checkForNewVideos, 2000);

    // 페이지 이탈 시 interval 정리
    window.addEventListener('beforeunload', () => {
        clearInterval(intervalId);
    });

    console.log('[시니어 채널] 무한 스크롤 감지 시작 (2초마다 비디오 개수 체크)');
}

// Watch 페이지인지 확인 (관련 영상 마킹용)
function isWatchPage() {
    return window.location.pathname === '/watch';
}

// 관련 영상에 마크 추가
// DOM 구조: YOUTUBE_DOM_STRUCTURE.md > "2. 영상 시청 페이지 (Watch Page)" 참조
function markRelatedVideos() {
    const lockups = document.querySelectorAll('#related yt-lockup-view-model');
    console.log('[시니어 채널] 관련 영상 수:', lockups.length);

    let markedCount = 0;

    lockups.forEach((lockup, index) => {
        // 이미 처리된 항목은 스킵
        if (lockup.dataset.seniorChecked === 'true') return;
        lockup.dataset.seniorChecked = 'true';

        // 채널명 추출 (.yt-core-attributed-string의 두 번째 요소)
        const textElements = lockup.querySelectorAll('.yt-core-attributed-string');
        if (textElements.length < 2) {
            console.warn('[시니어 채널] 채널명을 찾을 수 없음:', index);
            return;
        }

        const channelName = textElements[1].textContent.trim().toLowerCase();

        // 첫 3개만 로그 (디버깅)
        if (index < 3) {
            console.log(`[시니어 채널] 관련 영상 ${index}: "${channelName}"`);
        }

        // 등록된 채널인지 확인
        if (registeredChannelNames.has(channelName)) {
            const channelNameRow = textElements[1].parentElement;

            // 이미 마크가 있으면 스킵
            if (channelNameRow.querySelector('.senior-channel-mark')) return;

            // 체크 마크 추가
            const mark = document.createElement('span');
            mark.className = 'senior-channel-mark';
            mark.innerHTML = '✅';
            mark.title = '시니어 채널로 등록됨';
            mark.style.marginLeft = '6px';

            channelNameRow.appendChild(mark);
            markedCount++;
            console.log('[시니어 채널] 관련 영상 마크 추가:', channelName);
        }
    });

    console.log(`[시니어 채널] 총 ${markedCount}개 관련 영상에 마크 추가됨`);
}

// 관련 영상 무한 스크롤 감지 (MutationObserver)
function setupRelatedVideosObserver() {
    const relatedSection = document.querySelector('#related');
    if (!relatedSection) {
        console.warn('[시니어 채널] #related 섹션을 찾을 수 없음');
        return;
    }

    console.log('[시니어 채널] MutationObserver 설정 시작');

    const observer = new MutationObserver(() => {
        markRelatedVideos();
    });

    observer.observe(relatedSection, {
        childList: true,
        subtree: true
    });

    console.log('[시니어 채널] 관련 영상 무한 스크롤 감지 시작 (MutationObserver)');
}

// Watch 페이지 초기화
async function initWatchPage() {
    console.log('[시니어 채널] Watch 페이지 초기화');

    // 채널명 로드
    await loadRegisteredChannels();

    // 현재 관련 영상에 마크 추가
    markRelatedVideos();

    // MutationObserver 설정
    setupRelatedVideosObserver();
}

// 버튼 생성 (공통 함수) - 채널 확인 후 적절한 버튼 생성
function createButton(channelId) {
    const button = document.createElement('button');
    button.id = 'senior-channel-btn';
    button.className = 'senior-channel-button';
    button.innerHTML = '확인 중...';
    button.disabled = true;
    button.title = `채널 ID: ${channelId}`;

    // 채널 존재 여부 확인
    chrome.runtime.sendMessage(
        { action: 'checkChannel', channelId: channelId },
        (response) => {
            if (response && response.success && response.exists) {
                // 이미 등록된 채널
                setupRegisteredButton(button, channelId, response.channelTitle);
            } else {
                // 등록 안된 채널
                setupUnregisteredButton(button, channelId);
            }
        }
    );

    return button;
}

// 등록 안된 채널 버튼 설정
function setupUnregisteredButton(button, channelId) {
    button.innerHTML = '⭐ 시니어 채널 등록';
    button.disabled = false;
    button.classList.remove('registered');

    button.onclick = () => {
        button.disabled = true;
        button.innerHTML = '등록 중...';

        chrome.runtime.sendMessage(
            { action: 'addChannel', channelId: channelId },
            (response) => {
                if (response && response.success) {
                    button.innerHTML = '✅ 등록 완료!';
                    alert(`채널이 등록되었습니다:\n${response.channelTitle}`);

                    // 2초 후 "등록된 채널" 버튼으로 변경
                    setTimeout(() => {
                        setupRegisteredButton(button, channelId, response.channelTitle);
                    }, 2000);
                } else {
                    button.innerHTML = '❌ 등록 실패';
                    alert(`등록 실패: ${response ? response.error : '알 수 없는 오류'}`);

                    setTimeout(() => {
                        setupUnregisteredButton(button, channelId);
                    }, 3000);
                }
            }
        );
    };
}

// 등록된 채널 버튼 설정
function setupRegisteredButton(button, channelId, channelTitle) {
    button.innerHTML = '✅ 등록된 채널';
    button.disabled = false;
    button.classList.add('registered');
    button.title = `${channelTitle || '채널'} - 클릭하여 삭제`;

    button.onclick = () => {
        // 삭제 확인창
        const confirmed = confirm(
            `"${channelTitle || '이 채널'}"을(를) 시니어 채널 목록에서 삭제하시겠습니까?`
        );

        if (!confirmed) {
            return;
        }

        button.disabled = true;
        button.innerHTML = '삭제 중...';

        chrome.runtime.sendMessage(
            { action: 'deleteChannel', channelId: channelId },
            (response) => {
                if (response && response.success) {
                    button.innerHTML = '🗑️ 삭제 완료';
                    alert('채널이 삭제되었습니다.');

                    // 2초 후 "등록" 버튼으로 변경
                    setTimeout(() => {
                        setupUnregisteredButton(button, channelId);
                    }, 2000);
                } else {
                    button.innerHTML = '❌ 삭제 실패';
                    alert(`삭제 실패: ${response ? response.error : '알 수 없는 오류'}`);

                    setTimeout(() => {
                        setupRegisteredButton(button, channelId, channelTitle);
                    }, 3000);
                }
            }
        );
    };
}

// 채널 페이지에 버튼 추가
function addButtonToChannelPage() {
    if (document.getElementById('senior-channel-btn')) {
        return;
    }

    const channelId = extractChannelId();
    console.log('[시니어 채널] 채널 페이지 - 채널 ID:', channelId);

    if (!channelId) {
        console.warn('[시니어 채널] 채널 ID를 찾을 수 없습니다.');
        return;
    }

    // 채널 페이지의 구독 버튼 또는 헤더 영역 찾기
    const selectors = [
        'ytd-c4-tabbed-header-renderer #buttons',
        '#page-header tp-yt-paper-button',
        'ytd-browse[page-subtype="channels"] #buttons',
        'ytd-c4-tabbed-header-renderer .page-header-view-model-wiz__page-header-headline',
        '#channel-header-container'
    ];

    let targetElement = null;
    for (const selector of selectors) {
        targetElement = document.querySelector(selector);
        if (targetElement) {
            console.log(`[시니어 채널] 채널 페이지 버튼 위치: ${selector}`);
            break;
        }
    }

    if (!targetElement) {
        console.warn('[시니어 채널] 채널 페이지에서 버튼 위치를 찾을 수 없습니다.');
        return;
    }

    const button = createButton(channelId);
    button.style.cssText = `
        margin: 0 12px !important;
        padding: 10px 20px !important;
    `;

    targetElement.appendChild(button);
    console.log(`[시니어 채널] ✓ 채널 페이지 버튼 추가 완료`);
}

// 스크립트 추출 및 클립보드 복사 함수
async function copyTranscriptToClipboard() {
    console.log('[스크립트 복사] 시작');

    const button = document.getElementById('transcript-copy-btn');
    const originalText = button ? button.innerHTML : '';

    try {
        // 버튼 상태 변경
        if (button) {
            button.innerHTML = '⏳ 로딩 중...';
            button.disabled = true;
        }

        // 스크립트 패널 찾기
        let transcriptPanel = document.querySelector('ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-searchable-transcript"]');

        // 패널의 visibility 확인
        const isHidden = !transcriptPanel ||
                        transcriptPanel.getAttribute('visibility') === 'ENGAGEMENT_PANEL_VISIBILITY_HIDDEN';

        // 세그먼트 개수 확인
        let segments = transcriptPanel ? transcriptPanel.querySelectorAll('ytd-transcript-segment-renderer') : [];
        const needsLoad = isHidden || segments.length === 0;

        // 스크립트 패널이 없거나 숨겨져 있으면 자동으로 열기
        if (needsLoad) {
            console.log('[스크립트 복사] 스크립트 패널이 없음 - 자동 로드 시작');

            // 1. 더보기 버튼 클릭 (필요시)
            const expandButton = document.querySelector('tp-yt-paper-button#expand');
            if (expandButton && expandButton.getAttribute('aria-expanded') === 'false') {
                console.log('[스크립트 복사] 더보기 버튼 클릭');
                expandButton.click();
                await new Promise(resolve => setTimeout(resolve, 500));
            }

            // 2. 스크립트 표시 버튼 찾기 및 클릭
            const transcriptButton = document.querySelector('button[aria-label*="스크립트"]');
            if (!transcriptButton) {
                throw new Error('이 동영상에는 스크립트가 없습니다.');
            }

            console.log('[스크립트 복사] 스크립트 표시 버튼 클릭');
            transcriptButton.click();

            // 3. 스크립트 패널이 로드될 때까지 대기 (최대 3초)
            let attempts = 0;
            while (attempts < 30) {
                await new Promise(resolve => setTimeout(resolve, 100));
                transcriptPanel = document.querySelector('ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-searchable-transcript"]');
                if (transcriptPanel) {
                    // 패널의 visibility 확인
                    const visibility = transcriptPanel.getAttribute('visibility');
                    if (visibility !== 'ENGAGEMENT_PANEL_VISIBILITY_HIDDEN') {
                        console.log('[스크립트 복사] 스크립트 패널 로드 완료');
                        break;
                    }
                }
                attempts++;
            }

            if (!transcriptPanel) {
                throw new Error('스크립트 로딩 시간 초과');
            }

            // 스크립트 세그먼트가 실제로 로드될 때까지 대기 (최대 5초)
            console.log('[스크립트 복사] 세그먼트 로딩 대기 중...');
            let segmentAttempts = 0;
            while (segmentAttempts < 50) {
                await new Promise(resolve => setTimeout(resolve, 100));
                segments = transcriptPanel.querySelectorAll('ytd-transcript-segment-renderer');
                if (segments.length > 0) {
                    console.log(`[스크립트 복사] 세그먼트 로드 완료 (${segments.length}개)`);
                    break;
                }
                segmentAttempts++;
            }

            if (segments.length === 0) {
                throw new Error('스크립트 세그먼트 로딩 시간 초과');
            }
        }

        // 모든 스크립트 세그먼트 가져오기 (다시 확인)
        segments = transcriptPanel.querySelectorAll('ytd-transcript-segment-renderer');

        if (segments.length === 0) {
            throw new Error('스크립트가 비어있습니다.');
        }

        console.log(`[스크립트 복사] ${segments.length}개 세그먼트 발견`);

        // 타임스탬프 제거하고 텍스트만 추출
        const textOnly = Array.from(segments)
            .map(segment => {
                const textElement = segment.querySelector('.segment-text');
                return textElement ? textElement.textContent.trim() : '';
            })
            .filter(text => text.length > 0)
            .join(' ');

        if (!textOnly) {
            throw new Error('추출할 텍스트가 없습니다.');
        }

        // 클립보드에 복사
        try {
            await navigator.clipboard.writeText(textOnly);
            alert(`스크립트가 클립보드에 복사되었습니다!\n\n길이: ${textOnly.length}자`);
            console.log('[스크립트 복사] 성공:', textOnly.length, '자');
        } catch (err) {
            console.error('[스크립트 복사] clipboard API 실패, fallback 시도:', err);
            // Fallback: textarea 사용
            const textarea = document.createElement('textarea');
            textarea.value = textOnly;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            alert(`스크립트가 클립보드에 복사되었습니다!\n\n길이: ${textOnly.length}자`);
            console.log('[스크립트 복사] Fallback 성공');
        }

    } catch (error) {
        console.error('[스크립트 복사] 오류:', error);
        alert(`스크립트 복사 실패:\n${error.message}`);
    } finally {
        // 버튼 상태 복원
        if (button) {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }
}

// 동영상 페이지에 버튼 추가
function addButtonToVideoPage() {
    // 이미 버튼이 추가되어 있으면 리턴
    if (document.getElementById('senior-channel-btn') || document.getElementById('transcript-copy-btn')) {
        return;
    }

    const channelId = extractChannelId();
    console.log('[시니어 채널] 동영상 페이지 - 채널 ID:', channelId);

    if (!channelId) {
        console.warn('[시니어 채널] 채널 ID를 찾을 수 없습니다.');
        return;
    }

    // 동영상 페이지의 구독 버튼 영역 찾기
    const subscribeContainer = document.querySelector('#owner');
    if (!subscribeContainer) {
        console.warn('[시니어 채널] 구독 버튼 영역을 찾을 수 없습니다.');
        return;
    }

    // 채널 등록 버튼
    const button = createButton(channelId);
    button.style.cssText = `
        margin-left: 12px !important;
        padding: 8px 16px !important;
        font-size: 13px !important;
        height: 36px !important;
    `;

    subscribeContainer.appendChild(button);
    console.log(`[시니어 채널] ✓ 동영상 페이지 버튼 추가 완료`);

    // 스크립트 복사 버튼
    const transcriptButton = document.createElement('button');
    transcriptButton.id = 'transcript-copy-btn';
    transcriptButton.className = 'transcript-copy-button';
    transcriptButton.innerHTML = '📝 스크립트 복사';
    transcriptButton.title = '동영상 스크립트를 타임스탬프 없이 클립보드에 복사';
    transcriptButton.style.cssText = `
        margin-left: 12px !important;
        padding: 8px 16px !important;
        font-size: 13px !important;
        height: 36px !important;
    `;

    transcriptButton.onclick = copyTranscriptToClipboard;

    subscribeContainer.appendChild(transcriptButton);
    console.log(`[스크립트 복사] ✓ 스크립트 복사 버튼 추가 완료`);
}

// 페이지 로드 및 변경 감지
function init() {
    const isChannel = isChannelPage();
    const isVideo = isVideoPage();
    const isSearch = isSearchPage();
    const isWatch = isWatchPage();

    console.log('[시니어 채널] 페이지 타입:', {
        채널: isChannel,
        동영상: isVideo,
        검색: isSearch,
        Watch: isWatch,
        URL: window.location.href
    });

    // 검색 결과 페이지
    if (isSearch) {
        initSearchPage();
        return;
    }

    // Watch 페이지 (관련 영상 마킹)
    if (isWatch) {
        initWatchPage();
        // Watch 페이지에서도 버튼 추가는 계속 진행
    }

    // 채널 또는 동영상 페이지 (버튼 추가)
    if (!isChannel && !isVideo) {
        console.log('[시니어 채널] 지원하지 않는 페이지입니다.');
        return;
    }

    // 이전 버튼 제거
    const oldButton = document.getElementById('senior-channel-btn');
    if (oldButton) {
        oldButton.remove();
    }

    // 페이지 타입에 따라 다른 함수 호출
    const addButtonFunction = isChannel ? addButtonToChannelPage : addButtonToVideoPage;

    // 즉시 시도
    addButtonFunction();

    // 재시도 메커니즘
    let retryCount = 0;
    const maxRetries = 5;
    const retryInterval = setInterval(() => {
        retryCount++;
        const buttonExists = document.getElementById('senior-channel-btn');

        if (buttonExists) {
            console.log('[시니어 채널] 버튼 추가 성공');
            clearInterval(retryInterval);
        } else if (retryCount >= maxRetries) {
            console.warn('[시니어 채널] 버튼 추가 실패 (최대 재시도 도달)');
            clearInterval(retryInterval);
        } else {
            console.log(`[시니어 채널] 재시도 ${retryCount}/${maxRetries}`);
            addButtonFunction();
        }
    }, 1000);
}

// 초기 실행
console.log('[시니어 채널] 확장 프로그램 시작');
setTimeout(() => init(), 1000); // 페이지 로딩 대기

// SPA이므로 URL 변경 감지
let lastUrl = location.href;
new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
        lastUrl = url;
        console.log('[시니어 채널] URL 변경 감지:', url);

        // 새 페이지에서 다시 시도
        setTimeout(() => init(), 800);
    }
}).observe(document, { subtree: true, childList: true });
