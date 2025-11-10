"""
ViewScore 계산기

영상의 조회수 잠재력을 평가하는 점수 시스템
- 조회수: 높을수록 좋음
- 구독자수: 조회수 대비 구독자가 적을수록 좋음 (언더독 보너스)
- 최신성: 최근일수록 좋음
- 참여도: 좋아요+댓글 많을수록 좋음
"""
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional


# 기본 가중치
DEFAULT_WEIGHTS = {
    'view': 1.0,
    'subscriber': 1.0,
    'recency': 1.0,
    'engagement': 1.0
}


def normalize_view_count(view_count: int) -> float:
    """
    조회수 정규화 (0-100점)
    로그 스케일 사용: 1만 = 50점, 100만 = 75점, 1억 = 100점
    """
    if view_count <= 0:
        return 0.0

    # 로그 스케일: log10(view_count) / 8 * 100
    # 10^0 = 1 → 0점
    # 10^4 = 10,000 → 50점
    # 10^6 = 1,000,000 → 75점
    # 10^8 = 100,000,000 → 100점
    score = (math.log10(view_count) / 8.0) * 100
    return min(100.0, max(0.0, score))


def normalize_subscriber_count_inverse(subscriber_count: int, view_count: int = 0) -> float:
    """
    구독자수 역정규화 (0-100점)
    조회수 대비 구독자수 비율로 언더독 보너스 계산
    - 높은 조회수 대비 낮은 구독자수 = 높은 점수 (진정한 언더독)
    """
    if subscriber_count is None or subscriber_count <= 0:
        return 100.0  # 구독자 정보 없으면 최대 보너스

    if view_count <= 0:
        return 50.0  # 조회수 없으면 중간 점수

    # 조회수/구독자 비율 계산
    ratio = view_count / subscriber_count

    # 비율 기반 점수
    # ratio >= 100 (조회수가 구독자의 100배) = 100점
    # ratio >= 50 = 90점
    # ratio >= 20 = 80점
    # ratio >= 10 = 70점
    # ratio >= 5 = 60점
    # ratio >= 2 = 50점
    # ratio >= 1 = 40점
    # ratio >= 0.5 = 30점
    # ratio >= 0.1 = 20점
    # ratio < 0.1 = 10점

    if ratio >= 100:
        return 100.0
    elif ratio >= 50:
        return 90.0
    elif ratio >= 20:
        return 80.0
    elif ratio >= 10:
        return 70.0
    elif ratio >= 5:
        return 60.0
    elif ratio >= 2:
        return 50.0
    elif ratio >= 1:
        return 40.0
    elif ratio >= 0.5:
        return 30.0
    elif ratio >= 0.1:
        return 20.0
    else:
        return 10.0


def normalize_recency(published_at: str) -> float:
    """
    최신성 정규화 (0-100점)
    지수 감쇠: 오늘 = 100점, 30일 = 50점, 90일 = ~0점
    """
    try:
        # ISO 8601 날짜 파싱
        if 'T' in published_at:
            published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        else:
            published_date = datetime.strptime(published_at, '%Y-%m-%d')

        # 며칠 전인지 계산 (UTC 기준으로 통일)
        days_old = (datetime.now(timezone.utc) - published_date).days

        # 지수 감쇠: 30일 반감기
        # score = 100 * exp(-days_old / 30)
        score = 100.0 * math.exp(-days_old / 30.0)
        return max(0.0, min(100.0, score))

    except Exception as e:
        print(f"⚠️  날짜 파싱 오류: {published_at} - {e}")
        return 50.0  # 파싱 실패 시 중간 점수


def normalize_engagement(like_count: int, comment_count: int) -> float:
    """
    참여도 정규화 (0-100점)
    좋아요 + 댓글 합산, 로그 스케일
    """
    total_engagement = (like_count or 0) + (comment_count or 0)

    if total_engagement <= 0:
        return 0.0

    # 로그 스케일: log10(engagement) / 6 * 100
    # 10^0 = 1 → 0점
    # 10^3 = 1,000 → 50점
    # 10^6 = 1,000,000 → 100점
    score = (math.log10(total_engagement) / 6.0) * 100
    return min(100.0, max(0.0, score))


def calculate_view_score(
    video_data: Dict[str, Any],
    snapshot_data: Dict[str, Any],
    channel_data: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    ViewScore 계산

    Args:
        video_data: 비디오 정보 (published_at 포함)
        snapshot_data: 스냅샷 정보 (view_count, like_count, comment_count 포함)
        channel_data: 채널 정보 (subscriber_count 포함)
        weights: 가중치 딕셔너리 (기본값: DEFAULT_WEIGHTS)

    Returns:
        {
            'video_id': str,
            'snapshot_id': int,
            'score': float (0-100),
            'view_score': float,
            'subscriber_score': float,
            'recency_score': float,
            'engagement_score': float,
            'view_weight': float,
            'subscriber_weight': float,
            'recency_weight': float,
            'engagement_weight': float,
            'metadata': {...}  # 디버깅용 원본 데이터
        }
    """
    # 가중치 기본값 설정
    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()

    # 각 요소 점수 계산 (0-100점)
    view_count = snapshot_data.get('view_count', 0)
    view_score = normalize_view_count(view_count)

    subscriber_count = channel_data.get('subscriber_count', 0) if channel_data else 0
    subscriber_score = normalize_subscriber_count_inverse(subscriber_count, view_count)

    recency_score = normalize_recency(video_data.get('published_at', ''))

    engagement_score = normalize_engagement(
        snapshot_data.get('like_count', 0),
        snapshot_data.get('comment_count', 0)
    )

    # 가중 합산
    total_weight = sum([
        weights.get('view', 1.0),
        weights.get('subscriber', 1.0),
        weights.get('recency', 1.0),
        weights.get('engagement', 1.0)
    ])

    if total_weight == 0:
        final_score = 0.0
    else:
        final_score = (
            view_score * weights.get('view', 1.0) +
            subscriber_score * weights.get('subscriber', 1.0) +
            recency_score * weights.get('recency', 1.0) +
            engagement_score * weights.get('engagement', 1.0)
        ) / total_weight

    # 메타데이터 (디버깅 및 UI 표시용)
    metadata = {
        'raw_view_count': snapshot_data.get('view_count', 0),
        'raw_subscriber_count': subscriber_count,
        'raw_published_at': video_data.get('published_at', ''),
        'raw_like_count': snapshot_data.get('like_count', 0),
        'raw_comment_count': snapshot_data.get('comment_count', 0),
        'raw_engagement': snapshot_data.get('like_count', 0) + snapshot_data.get('comment_count', 0)
    }

    return {
        'video_id': video_data.get('video_id'),
        'snapshot_id': snapshot_data.get('id'),
        'score': round(final_score, 2),

        # 각 요소별 점수
        'view_score': round(view_score, 2),
        'subscriber_score': round(subscriber_score, 2),
        'recency_score': round(recency_score, 2),
        'engagement_score': round(engagement_score, 2),

        # 사용된 가중치
        'view_weight': weights.get('view', 1.0),
        'subscriber_weight': weights.get('subscriber', 1.0),
        'recency_weight': weights.get('recency', 1.0),
        'engagement_weight': weights.get('engagement', 1.0),

        # 메타데이터
        'metadata': metadata
    }


def batch_calculate_view_scores(
    videos_with_snapshots: list,
    channels_dict: Dict[str, Dict],
    weights: Optional[Dict[str, float]] = None
) -> list:
    """
    여러 비디오의 ViewScore를 일괄 계산

    Args:
        videos_with_snapshots: 비디오+스냅샷 데이터 리스트
        channels_dict: channel_id를 키로 하는 채널 정보 딕셔너리
        weights: 가중치

    Returns:
        ViewScore 결과 리스트
    """
    results = []

    for video in videos_with_snapshots:
        channel_id = video.get('channel_id')
        channel_data = channels_dict.get(channel_id, {})

        try:
            score_result = calculate_view_score(
                video_data=video,
                snapshot_data=video,
                channel_data=channel_data,
                weights=weights
            )
            results.append(score_result)
        except Exception as e:
            print(f"⚠️  ViewScore 계산 실패 ({video.get('video_id')}): {e}")
            continue

    return results


if __name__ == '__main__':
    # 테스트
    print("🧪 ViewScore Calculator 테스트\n")

    test_video = {
        'video_id': 'test123',
        'published_at': '2025-11-05T10:00:00Z'
    }

    test_snapshot = {
        'id': 1,
        'view_count': 50000,
        'like_count': 1200,
        'comment_count': 300
    }

    test_channel = {
        'subscriber_count': 5000  # 작은 채널
    }

    result = calculate_view_score(test_video, test_snapshot, test_channel)

    print(f"📊 ViewScore: {result['score']:.1f}/100")
    print(f"  👁️  조회수 점수: {result['view_score']:.1f} (조회수: {result['metadata']['raw_view_count']:,})")
    print(f"  👥 구독자 점수: {result['subscriber_score']:.1f} (구독자: {result['metadata']['raw_subscriber_count']:,})")
    print(f"  📅 최신성 점수: {result['recency_score']:.1f} (업로드: {result['metadata']['raw_published_at']})")
    print(f"  💬 참여도 점수: {result['engagement_score']:.1f} (참여: {result['metadata']['raw_engagement']:,})")
