/**
 * 백그라운드 스크립트 - Flask API 통신
 */

// Flask 서버 URL (설정 가능)
const API_BASE_URL = 'http://localhost:5000';

// 메시지 리스너
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'addChannel') {
        addChannelToServer(request.channelId)
            .then(result => sendResponse(result))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // 비동기 응답
    }

    if (request.action === 'checkChannel') {
        checkChannelExists(request.channelId)
            .then(result => sendResponse(result))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // 비동기 응답
    }

    if (request.action === 'deleteChannel') {
        deleteChannelFromServer(request.channelId)
            .then(result => sendResponse(result))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // 비동기 응답
    }

    if (request.action === 'getChannelNames') {
        getChannelNames()
            .then(result => sendResponse(result))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // 비동기 응답
    }
});

/**
 * Flask API로 채널 추가 요청
 */
async function addChannelToServer(channelId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/channels/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                channel_id: channelId
            })
        });

        const result = await response.json();

        if (result.success) {
            return {
                success: true,
                channelTitle: result.data.channel_title,
                message: result.message
            };
        } else {
            return {
                success: false,
                error: result.error || '알 수 없는 오류'
            };
        }
    } catch (error) {
        console.error('API 요청 실패:', error);
        return {
            success: false,
            error: `서버 연결 실패: ${error.message}\n\nFlask 앱이 실행 중인지 확인하세요 (http://localhost:5000)`
        };
    }
}

/**
 * Flask API로 채널 존재 여부 확인
 */
async function checkChannelExists(channelId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/channels/check/${channelId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            return {
                success: true,
                exists: result.exists,
                channelTitle: result.channel_title || null
            };
        } else {
            return {
                success: false,
                error: result.error || '알 수 없는 오류'
            };
        }
    } catch (error) {
        console.error('채널 확인 실패:', error);
        // 에러 시 exists: false로 처리 (서버 꺼져있어도 버튼은 표시)
        return {
            success: true,
            exists: false
        };
    }
}

/**
 * Flask API로 채널 삭제 요청
 */
async function deleteChannelFromServer(channelId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/channels/${channelId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            return {
                success: true,
                message: result.message
            };
        } else {
            return {
                success: false,
                error: result.error || '알 수 없는 오류'
            };
        }
    } catch (error) {
        console.error('채널 삭제 실패:', error);
        return {
            success: false,
            error: `서버 연결 실패: ${error.message}`
        };
    }
}

/**
 * Flask API로 등록된 채널명 리스트 가져오기
 */
async function getChannelNames() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/channels/names`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            return {
                success: true,
                channelNames: result.data
            };
        } else {
            return {
                success: false,
                error: result.error || '알 수 없는 오류'
            };
        }
    } catch (error) {
        console.error('채널명 리스트 가져오기 실패:', error);
        // 에러 시 빈 배열 반환
        return {
            success: true,
            channelNames: []
        };
    }
}

// 확장 설치 시 초기 설정
chrome.runtime.onInstalled.addListener(() => {
    console.log('시니어 유튜브 트렌드 확장 프로그램이 설치되었습니다.');
});
