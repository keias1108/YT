/**
 * 팝업 UI 스크립트
 */

const BASE_URL = 'http://localhost:5000';

// 기본 설정값
const DEFAULT_SETTINGS = {
    days: 14,
    minViews: 100000
};

document.addEventListener('DOMContentLoaded', () => {
    // 대시보드 열기
    document.getElementById('btn-open-dashboard').addEventListener('click', () => {
        chrome.tabs.create({ url: BASE_URL });
    });

    // 채널 관리 페이지 열기
    document.getElementById('btn-open-channels').addEventListener('click', () => {
        chrome.tabs.create({ url: `${BASE_URL}/channels` });
    });

    // 설정 로드
    loadSettings();

    // 설정 저장 버튼
    document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
});

// 설정 로드
function loadSettings() {
    chrome.storage.local.get(['trendingSettings'], (result) => {
        const settings = result.trendingSettings || DEFAULT_SETTINGS;

        // 드롭다운에 값 설정
        document.getElementById('period-select').value = settings.days;
        document.getElementById('views-select').value = settings.minViews;

        console.log('[팝업] 설정 로드:', settings);
    });
}

// 설정 저장
function saveSettings() {
    const days = parseInt(document.getElementById('period-select').value);
    const minViews = parseInt(document.getElementById('views-select').value);

    const settings = { days, minViews };

    chrome.storage.local.set({ trendingSettings: settings }, () => {
        console.log('[팝업] 설정 저장:', settings);

        // 상태 메시지 표시
        const statusDiv = document.getElementById('status');
        statusDiv.className = 'status success';
        statusDiv.textContent = '✓ 설정이 저장되었습니다!';

        // 2초 후 메시지 제거
        setTimeout(() => {
            statusDiv.textContent = '';
            statusDiv.className = '';
        }, 2000);

        // 현재 열려있는 YouTube 탭들에 설정 변경 알림
        chrome.tabs.query({ url: '*://*.youtube.com/*' }, (tabs) => {
            tabs.forEach(tab => {
                chrome.tabs.sendMessage(tab.id, {
                    action: 'updateTrendingSettings',
                    settings: settings
                }).catch(() => {
                    // 일부 탭에서 메시지 수신 실패는 무시
                });
            });
        });
    });
}
