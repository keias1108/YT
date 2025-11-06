/**
 * 팝업 UI 스크립트
 */

const BASE_URL = 'http://localhost:5000';

document.addEventListener('DOMContentLoaded', () => {
    // 대시보드 열기
    document.getElementById('btn-open-dashboard').addEventListener('click', () => {
        chrome.tabs.create({ url: BASE_URL });
    });

    // 채널 관리 페이지 열기
    document.getElementById('btn-open-channels').addEventListener('click', () => {
        chrome.tabs.create({ url: `${BASE_URL}/channels` });
    });
});
