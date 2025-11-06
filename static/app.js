// 전역 변수
let allCategories = [];
let currentSort = 'view_score';  // 기본 정렬: ViewScore
let currentOrder = 'desc';        // 기본 방향: 내림차순

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    initializeDateInputs();
    loadStats();
    loadCategories();
    initializeSortableHeaders();
    initializeWeightSliders();
    loadWeights();  // 저장된 가중치 복원
    restoreSectionStates();  // 섹션 토글 상태 복원

    // 이벤트 리스너 등록
    document.getElementById('btn-collect').addEventListener('click', collectData);
    document.getElementById('btn-load').addEventListener('click', loadVideos);
    document.getElementById('btn-recalculate').addEventListener('click', recalculateViewScores);
    document.getElementById('btn-save-weights').addEventListener('click', saveWeights);
});

/**
 * 날짜 입력 초기화 (오늘 날짜로)
 */
function initializeDateInputs() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('view-date').value = today;
}

/**
 * 통계 조회
 */
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const result = await response.json();

        if (result.success) {
            const data = result.data;
            document.getElementById('stat-videos').textContent = data.total_videos.toLocaleString();
            document.getElementById('stat-snapshots').textContent = data.total_snapshots.toLocaleString();
            document.getElementById('stat-labels').textContent = data.total_labels.toLocaleString();
            document.getElementById('stat-latest').textContent = data.latest_snapshot_date || '-';
        }
    } catch (error) {
        console.error('통계 조회 실패:', error);
    }
}

/**
 * 카테고리 목록 로드
 */
async function loadCategories() {
    const container = document.getElementById('categories-list');

    try {
        const response = await fetch('/api/categories');
        const result = await response.json();

        if (result.success) {
            allCategories = result.data;

            // 시니어층 관련 카테고리 우선 선택 (한국에서 인기 영상이 실제로 있는 것만)
            const seniorCategoryIds = ['10', '15', '17', '22', '23', '24', '25', '26', '28'];

            container.innerHTML = allCategories.map(cat => `
                <div class="checkbox-item">
                    <input type="checkbox"
                           id="cat-${cat.id}"
                           value="${cat.id}"
                           ${seniorCategoryIds.includes(cat.id) ? 'checked' : ''}>
                    <label for="cat-${cat.id}">${cat.title}</label>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="error">카테고리 로드 실패</p>';
        }
    } catch (error) {
        console.error('카테고리 로드 실패:', error);
        container.innerHTML = '<p class="error">카테고리 로드 실패</p>';
    }
}

/**
 * 데이터 수집
 */
async function collectData() {
    const btn = document.getElementById('btn-collect');
    const statusDiv = document.getElementById('collect-status');

    // 선택된 카테고리 가져오기
    const checkboxes = document.querySelectorAll('#categories-list input[type="checkbox"]:checked');
    const categoryIds = Array.from(checkboxes).map(cb => cb.value);

    if (categoryIds.length === 0) {
        showStatus(statusDiv, '카테고리를 하나 이상 선택해주세요.', 'error');
        return;
    }

    const maxResults = parseInt(document.getElementById('max-results').value);

    // 버튼 비활성화
    btn.disabled = true;
    btn.textContent = '수집 중...';
    showStatus(statusDiv, `${categoryIds.length}개 카테고리 수집 시작 (오늘 날짜로 저장)...`, 'info');

    try {
        const response = await fetch('/api/collect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                category_ids: categoryIds,
                max_results: maxResults
            })
        });

        const result = await response.json();

        if (result.success) {
            const stats = result.data;
            showStatus(
                statusDiv,
                `✅ 수집 완료: 총 ${stats.total_videos}개 중 신규 ${stats.new_videos}개, 중복 스킵 ${stats.duplicate_skipped}개`,
                'success'
            );

            // 통계 업데이트
            loadStats();
        } else {
            showStatus(statusDiv, `❌ 오류: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('수집 실패:', error);
        showStatus(statusDiv, `❌ 수집 실패: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '수집 시작';
    }
}

/**
 * 비디오 조회 (DB에서, API 호출 없음)
 */
async function loadVideos() {
    const viewDate = document.getElementById('view-date').value;
    const seniorThreshold = parseFloat(document.getElementById('senior-threshold').value);
    const dataSource = document.querySelector('input[name="data-source"]:checked').value;
    const tableBody = document.getElementById('video-table-body');
    const countDiv = document.getElementById('video-count');

    // 로딩 표시
    tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">로딩 중...</td></tr>';

    try {
        const response = await fetch(`/api/videos?snapshot_date=${viewDate}&senior_threshold=${seniorThreshold}&limit=100&sort_by=${currentSort}&order=${currentOrder}&data_source=${dataSource}`);
        const result = await response.json();

        if (result.success) {
            const videos = result.data;

            if (videos.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">조회 결과가 없습니다. 먼저 데이터를 수집하세요.</td></tr>';
                countDiv.textContent = '';
                return;
            }

            // 테이블 렌더링
            tableBody.innerHTML = videos.map((video, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>
                        <img src="${video.thumbnail_url}" alt="썸네일" class="thumbnail">
                    </td>
                    <td class="video-title">
                        <a href="https://www.youtube.com/watch?v=${video.video_id}" target="_blank">
                            ${video.title}
                        </a>
                    </td>
                    <td>${video.channel_title}</td>
                    <td>${(video.view_count || 0).toLocaleString()}</td>
                    <td>
                        <span class="score-badge ${getScoreClass(video.senior_score)}">
                            ${(video.senior_score || 0).toFixed(1)}
                        </span>
                    </td>
                    <td class="highlights">
                        ${renderHighlights(video.highlights)}
                    </td>
                    <td>${(video.delta_views_14d || 0).toLocaleString()}</td>
                </tr>
            `).join('');

            countDiv.textContent = `총 ${videos.length}개 비디오 (날짜: ${result.snapshot_date})`;
        } else {
            tableBody.innerHTML = `<tr><td colspan="8" class="empty-state">오류: ${result.error}</td></tr>`;
            countDiv.textContent = '';
        }
    } catch (error) {
        console.error('비디오 조회 실패:', error);
        tableBody.innerHTML = `<tr><td colspan="8" class="empty-state">조회 실패: ${error.message}</td></tr>`;
        countDiv.textContent = '';
    }
}

/**
 * SeniorScore 클래스 반환
 */
function getScoreClass(score) {
    if (score >= 10) return 'score-high';
    if (score >= 5) return 'score-medium';
    return 'score-low';
}

/**
 * Highlights 렌더링
 */
function renderHighlights(highlightsJson) {
    if (!highlightsJson) return '-';

    let highlights;
    if (typeof highlightsJson === 'string') {
        try {
            highlights = JSON.parse(highlightsJson);
        } catch (e) {
            return '-';
        }
    } else {
        highlights = highlightsJson;
    }

    const parts = [];

    // 키워드
    if (highlights.matched_keywords && highlights.matched_keywords.length > 0) {
        parts.push(...highlights.matched_keywords.slice(0, 3).map(kw =>
            `<span class="highlight-tag">🔑 ${kw}</span>`
        ));
    }

    // 장르
    if (highlights.matched_genres && highlights.matched_genres.length > 0) {
        parts.push(...highlights.matched_genres.map(g =>
            `<span class="highlight-tag">🎵 ${g}</span>`
        ));
    }

    // 댓글 지표
    if (highlights.comment_indicators && highlights.comment_indicators.length > 0) {
        parts.push(`<span class="highlight-tag">💬 댓글지표</span>`);
    }

    // 길이
    if (highlights.length_category) {
        parts.push(`<span class="highlight-tag">⏱️ ${highlights.length_category}</span>`);
    }

    return parts.length > 0 ? parts.join(' ') : '-';
}

/**
 * 상태 메시지 표시
 */
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
}

/**
 * 정렬 가능한 헤더 초기화
 */
function initializeSortableHeaders() {
    const sortableHeaders = document.querySelectorAll('th.sortable');

    sortableHeaders.forEach(header => {
        header.addEventListener('click', () => {
            handleSortClick(header);
        });
    });
}

/**
 * 정렬 클릭 처리
 */
function handleSortClick(header) {
    const sortBy = header.getAttribute('data-sort');

    // 같은 컬럼 클릭 시 방향 전환, 다른 컬럼 클릭 시 desc로 시작
    if (currentSort === sortBy) {
        currentOrder = (currentOrder === 'desc') ? 'asc' : 'desc';
    } else {
        currentSort = sortBy;
        currentOrder = 'desc';  // 새 컬럼은 항상 내림차순부터
    }

    // 화살표 업데이트
    updateSortArrows();

    // 데이터 다시 로드
    loadVideos();
}

/**
 * 정렬 화살표 업데이트
 */
function updateSortArrows() {
    const sortableHeaders = document.querySelectorAll('th.sortable');

    sortableHeaders.forEach(header => {
        const arrow = header.querySelector('.sort-arrow');
        const sortBy = header.getAttribute('data-sort');

        if (sortBy === currentSort) {
            header.classList.add('active');
            arrow.textContent = (currentOrder === 'desc') ? '▼' : '▲';
        } else {
            header.classList.remove('active');
            arrow.textContent = '';
        }
    });
}

/**
 * 가중치 슬라이더 초기화
 */
function initializeWeightSliders() {
    const sliders = [
        { id: 'view-weight', valId: 'view-weight-val' },
        { id: 'subscriber-weight', valId: 'subscriber-weight-val' },
        { id: 'recency-weight', valId: 'recency-weight-val' },
        { id: 'engagement-weight', valId: 'engagement-weight-val' }
    ];

    sliders.forEach(slider => {
        const element = document.getElementById(slider.id);
        const valueDisplay = document.getElementById(slider.valId);

        element.addEventListener('input', (e) => {
            valueDisplay.textContent = parseFloat(e.target.value).toFixed(1);
        });
    });
}

/**
 * ViewScore 재계산 (슬라이더 가중치 적용)
 */
async function recalculateViewScores() {
    const viewDate = document.getElementById('view-date').value;
    const dataSource = document.querySelector('input[name="data-source"]:checked').value;
    const tableBody = document.getElementById('video-table-body');
    const countDiv = document.getElementById('video-count');

    // 가중치 가져오기
    const weights = {
        view: parseFloat(document.getElementById('view-weight').value),
        subscriber: parseFloat(document.getElementById('subscriber-weight').value),
        recency: parseFloat(document.getElementById('recency-weight').value),
        engagement: parseFloat(document.getElementById('engagement-weight').value)
    };

    // 로딩 표시
    tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">재계산 중...</td></tr>';

    try {
        const response = await fetch('/api/videos/recalculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                snapshot_date: viewDate,
                data_source: dataSource,
                weights: weights
            })
        });

        const result = await response.json();

        if (result.success) {
            const videos = result.data;

            if (videos.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="8" class="empty-state">결과가 없습니다.</td></tr>';
                countDiv.textContent = '';
                return;
            }

            // 테이블 렌더링
            tableBody.innerHTML = videos.map((video, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>
                        <img src="${video.thumbnail_url}" alt="썸네일" class="thumbnail">
                    </td>
                    <td class="video-title">
                        <a href="https://www.youtube.com/watch?v=${video.video_id}" target="_blank">
                            ${video.title}
                        </a>
                    </td>
                    <td>${video.channel_title}</td>
                    <td>${(video.view_count || 0).toLocaleString()}</td>
                    <td>
                        <span class="score-badge ${getScoreClass(video.view_score)}">
                            ${(video.view_score || 0).toFixed(1)}
                        </span>
                    </td>
                    <td class="highlights">
                        ${renderBreakdown(video.metadata)}
                    </td>
                    <td>${(video.delta_views_14d || 0).toLocaleString()}</td>
                </tr>
            `).join('');

            countDiv.textContent = `총 ${videos.length}개 비디오 (가중치: 조회수=${weights.view}, 구독자=${weights.subscriber}, 최신성=${weights.recency}, 참여도=${weights.engagement})`;
        } else {
            tableBody.innerHTML = `<tr><td colspan="8" class="empty-state">오류: ${result.error}</td></tr>`;
            countDiv.textContent = '';
        }
    } catch (error) {
        console.error('재계산 실패:', error);
        tableBody.innerHTML = `<tr><td colspan="8" class="empty-state">재계산 실패: ${error.message}</td></tr>`;
        countDiv.textContent = '';
    }
}

/**
 * ViewScore Breakdown 렌더링
 */
function renderBreakdown(metadata) {
    if (!metadata) return '-';

    try {
        const meta = typeof metadata === 'string' ? JSON.parse(metadata) : metadata;

        const parts = [];
        parts.push(`<span class="factor-tag">👁️ ${(meta.raw_view_count || 0).toLocaleString()}</span>`);
        parts.push(`<span class="factor-tag">👥 ${(meta.raw_subscriber_count || 0).toLocaleString()}</span>`);

        if (meta.raw_published_at) {
            const daysAgo = Math.floor((new Date() - new Date(meta.raw_published_at)) / (1000 * 60 * 60 * 24));
            parts.push(`<span class="factor-tag">📅 ${daysAgo}일</span>`);
        }

        parts.push(`<span class="factor-tag">💬 ${(meta.raw_engagement || 0).toLocaleString()}</span>`);

        return parts.join(' ');
    } catch (e) {
        return '-';
    }
}

/**
 * 가중치 저장 (localStorage)
 */
function saveWeights() {
    const weights = {
        view: parseFloat(document.getElementById('view-weight').value),
        subscriber: parseFloat(document.getElementById('subscriber-weight').value),
        recency: parseFloat(document.getElementById('recency-weight').value),
        engagement: parseFloat(document.getElementById('engagement-weight').value)
    };

    localStorage.setItem('viewScoreWeights', JSON.stringify(weights));
    alert('가중치가 저장되었습니다!');
}

/**
 * 가중치 복원 (localStorage)
 */
function loadWeights() {
    const savedWeights = localStorage.getItem('viewScoreWeights');
    if (!savedWeights) return;

    try {
        const weights = JSON.parse(savedWeights);

        document.getElementById('view-weight').value = weights.view;
        document.getElementById('view-weight-val').textContent = weights.view.toFixed(1);

        document.getElementById('subscriber-weight').value = weights.subscriber;
        document.getElementById('subscriber-weight-val').textContent = weights.subscriber.toFixed(1);

        document.getElementById('recency-weight').value = weights.recency;
        document.getElementById('recency-weight-val').textContent = weights.recency.toFixed(1);

        document.getElementById('engagement-weight').value = weights.engagement;
        document.getElementById('engagement-weight-val').textContent = weights.engagement.toFixed(1);
    } catch (e) {
        console.error('가중치 복원 실패:', e);
    }
}

/**
 * 섹션 토글 (접기/펼치기)
 */
function toggleSection(sectionClass) {
    const section = document.querySelector(`.${sectionClass}`);
    const content = section.querySelector('.form-group, .weight-controls, .checkbox-group').parentElement;
    const toggleBtn = section.querySelector('.toggle-btn');

    section.classList.toggle('collapsed');

    // 화살표 방향 변경
    if (section.classList.contains('collapsed')) {
        toggleBtn.textContent = '▶';
    } else {
        toggleBtn.textContent = '▼';
    }

    // localStorage에 상태 저장
    const sectionStates = JSON.parse(localStorage.getItem('sectionStates') || '{}');
    sectionStates[sectionClass] = section.classList.contains('collapsed');
    localStorage.setItem('sectionStates', JSON.stringify(sectionStates));
}

/**
 * 섹션 토글 상태 복원
 */
function restoreSectionStates() {
    const sectionStates = JSON.parse(localStorage.getItem('sectionStates') || '{}');

    Object.keys(sectionStates).forEach(sectionClass => {
        if (sectionStates[sectionClass]) {
            const section = document.querySelector(`.${sectionClass}`);
            if (section) {
                section.classList.add('collapsed');
                const toggleBtn = section.querySelector('.toggle-btn');
                if (toggleBtn) {
                    toggleBtn.textContent = '▶';
                }
            }
        }
    });
}
