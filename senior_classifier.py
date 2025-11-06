"""
시니어 분류기 - SeniorScore 계산 로직
프록시 특징을 조합하여 시니어 가능성 추정
"""
import re
import isodate
from typing import Dict, Any, List, Optional


# ============================================================
# 시니어 키워드 사전 (초안)
# ============================================================

SENIOR_KEYWORDS = {
    # 건강 관련
    '건강': 3.0,
    '관절': 2.5,
    '무릎': 2.5,
    '혈당': 2.5,
    '혈압': 2.5,
    '당뇨': 2.0,
    '고혈압': 2.0,
    '치매': 2.0,
    '치아': 1.5,
    '운동': 1.5,
    '스트레칭': 1.5,
    '요가': 1.0,

    # 복지/금융
    '연금': 3.0,
    '노후': 3.0,
    '실버': 3.0,
    '시니어': 3.0,
    '은퇴': 2.5,
    '복지': 2.0,
    '국민연금': 3.0,
    '기초연금': 3.0,

    # 음악/엔터
    '트로트': 3.0,
    '가요무대': 3.0,
    '국악': 2.5,
    '옛노래': 2.5,
    '가곡': 2.0,
    '민요': 2.5,
    '7080': 2.5,
    '8090': 2.0,

    # 라이프스타일
    '텃밭': 2.5,
    '전원': 2.0,
    '귀농': 2.5,
    '등산': 2.0,
    '산책': 1.5,
    '낚시': 1.5,
    '전통': 2.0,
    '한식': 1.5,
    '된장': 1.5,
    '김장': 2.0,

    # 가족/관계
    '손주': 3.0,
    '손자': 2.5,
    '손녀': 2.5,
    '할머니': 2.0,
    '할아버지': 2.0,
    '부모님': 1.5,
    '효도': 2.0,

    # 방송/교양
    '다큐': 1.5,
    '시사': 1.5,
    '교양': 1.5,
    '역사': 1.5,
    '문화재': 1.5,
    '전통시장': 1.5,
}

# 트로트 가수 (엔터티)
TROT_ARTISTS = [
    '임영웅', '영탁', '이찬원', '장민호', '김호중',
    '송가인', '홍진영', '진성', '태진아', '주현미',
    '설운도', '남진', '나훈아', '현숙', '박상철'
]

# 시니어 친화 채널 (예시 - 실제 운영 시 확장)
SENIOR_FRIENDLY_CHANNELS = {
    # 'UC채널ID': 가중치
}

# 댓글 연령 지표 키워드
COMMENT_AGE_INDICATORS = {
    '어머니': 2.0,
    '아버지': 2.0,
    '부모님': 1.5,
    '엄마': 1.5,
    '아빠': 1.5,
    '손주': 3.0,
    '무릎': 2.0,
    '관절': 2.0,
    '연세': 2.0,
    '~하십니다': 1.5,  # 존대 표현
    '~하세요': 1.5,
}

# Z세대 밈/이모티콘 (감점 요소)
ZGEN_MEMES = [
    'ㅋㅋ', 'ㄹㅇ', 'ㅇㅈ', 'ㅇㅋ', '실화냐', '개꿀', '레전드',
    '띵곡', '갓', '킹', '혜자', '핵', '찢었다', '미쳤다'
]


# ============================================================
# 점수 계산 함수들
# ============================================================

def calculate_keyword_score(text: str) -> tuple[float, List[str]]:
    """
    텍스트에서 시니어 키워드 매칭 점수 계산

    Returns:
        (점수, 매칭된 키워드 리스트)
    """
    if not text:
        return 0.0, []

    text_lower = text.lower()
    score = 0.0
    matched_keywords = []

    for keyword, weight in SENIOR_KEYWORDS.items():
        if keyword in text:
            score += weight
            matched_keywords.append(keyword)

    # 트로트 가수명 체크
    for artist in TROT_ARTISTS:
        if artist in text:
            score += 3.0
            matched_keywords.append(f"트로트:{artist}")

    return score, matched_keywords


def calculate_genre_score(title: str, tags: List[str]) -> tuple[float, List[str]]:
    """
    장르/엔터티 점수 계산 (트로트, 전통, 교양 등)

    Returns:
        (점수, 매칭된 장르 리스트)
    """
    score = 0.0
    matched_genres = []

    combined_text = title + ' ' + ' '.join(tags)

    # 트로트 판별
    if '트로트' in combined_text:
        score += 5.0
        matched_genres.append('트로트')

    # 전통/교양
    if any(kw in combined_text for kw in ['국악', '전통', '교양', '다큐', '시사']):
        score += 2.0
        matched_genres.append('교양/전통')

    # 가요무대 등 방송명
    if '가요무대' in combined_text:
        score += 5.0
        matched_genres.append('가요무대')

    return score, matched_genres


def calculate_comment_score(comments: List[Dict[str, Any]]) -> tuple[float, List[str]]:
    """
    댓글에서 연령 지표 추출

    Args:
        comments: 댓글 리스트 (youtube_api.get_video_comments 결과)

    Returns:
        (점수, 매칭된 지표 리스트)
    """
    if not comments:
        return 0.0, []

    score = 0.0
    matched_indicators = []

    for comment in comments[:50]:  # 상위 50개만 체크
        text = comment.get('text', '')

        for indicator, weight in COMMENT_AGE_INDICATORS.items():
            if indicator in text:
                score += weight * 0.1  # 댓글은 가중치 낮게
                if indicator not in matched_indicators:
                    matched_indicators.append(indicator)

    return score, matched_indicators


def calculate_channel_score(channel_id: str, subscriber_count: int) -> float:
    """
    채널 가중치 계산

    Args:
        channel_id: 채널 ID
        subscriber_count: 구독자 수

    Returns:
        채널 점수
    """
    # 화이트리스트/블랙리스트 체크
    if channel_id in SENIOR_FRIENDLY_CHANNELS:
        return SENIOR_FRIENDLY_CHANNELS[channel_id] * 5.0

    # 구독자 수 기반 보정 (작은 채널 발굴 장려)
    if subscriber_count < 10000:
        return 1.2  # 소규모 채널 가중
    elif subscriber_count < 100000:
        return 1.0
    else:
        return 0.8  # 대형 채널은 약간 감점


def calculate_length_score(duration_iso: str) -> tuple[float, str]:
    """
    영상 길이 점수 계산

    Args:
        duration_iso: ISO 8601 형식 (예: PT15M33S)

    Returns:
        (점수, 길이 범주)
    """
    try:
        duration = isodate.parse_duration(duration_iso)
        minutes = duration.total_seconds() / 60

        if minutes < 1:  # Shorts (60초 미만)
            return -2.0, 'Shorts'
        elif 1 <= minutes < 3:  # 너무 짧음
            return 0.0, '짧음'
        elif 3 <= minutes <= 30:  # 이상적
            return 2.0, '적정'
        elif 30 < minutes <= 60:
            return 1.0, '중간'
        else:  # 60분 이상
            return 0.5, '긴편'

    except Exception as e:
        return 0.0, '알수없음'


def check_zgen_penalty(title: str, description: str) -> tuple[float, List[str]]:
    """
    Z세대 밈/이모티콘 과다 사용 시 감점

    Returns:
        (감점 점수, 매칭된 밈 리스트)
    """
    combined = title + ' ' + description
    penalty = 0.0
    matched_memes = []

    for meme in ZGEN_MEMES:
        count = combined.count(meme)
        if count > 0:
            penalty -= count * 0.5
            matched_memes.append(meme)

    return penalty, matched_memes


# ============================================================
# 최종 SeniorScore 계산
# ============================================================

def calculate_senior_score(
    video_data: Dict[str, Any],
    comments: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    시니어 점수 계산 (규칙 기반 v0)

    Args:
        video_data: 비디오 정보 (youtube_api에서 반환)
        comments: 댓글 리스트 (선택)

    Returns:
        {
            'score': 총점,
            'keyword_score': 키워드 점수,
            'genre_score': 장르 점수,
            'comment_score': 댓글 점수,
            'channel_score': 채널 점수,
            'length_score': 길이 점수,
            'highlights': {
                'matched_keywords': [...],
                'matched_genres': [...],
                'comment_indicators': [...],
                'length_category': '...',
                'zgen_memes': [...],
            }
        }
    """
    title = video_data.get('title', '')
    description = video_data.get('description', '')
    tags = video_data.get('tags', [])
    duration = video_data.get('duration', '')
    channel_id = video_data.get('channel_id', '')

    # 구독자 수는 별도로 채널 조회 필요 (여기서는 0으로 가정)
    # 실제 사용 시 youtube_api.get_channel_info로 가져와야 함
    subscriber_count = 0

    # 1. 키워드 점수
    kw_score_title, kw_matched_title = calculate_keyword_score(title)
    kw_score_desc, kw_matched_desc = calculate_keyword_score(description)
    keyword_score = kw_score_title + kw_score_desc * 0.5  # 설명은 가중치 낮게
    matched_keywords = list(set(kw_matched_title + kw_matched_desc))

    # 2. 장르/엔터티 점수
    genre_score, matched_genres = calculate_genre_score(title, tags)

    # 3. 댓글 점수
    comment_score = 0.0
    comment_indicators = []
    if comments:
        comment_score, comment_indicators = calculate_comment_score(comments)

    # 4. 채널 점수
    channel_score = calculate_channel_score(channel_id, subscriber_count)

    # 5. 길이 점수
    length_score, length_category = calculate_length_score(duration)

    # 6. Z세대 밈 감점
    zgen_penalty, zgen_memes = check_zgen_penalty(title, description)

    # 최종 점수 계산 (가중치 적용)
    # w1*키워드 + w2*장르 + w3*댓글 + w4*채널 + w5*길이 + 감점
    weights = {
        'keyword': 1.0,
        'genre': 1.5,
        'comment': 0.5,
        'channel': 1.0,
        'length': 0.8,
    }

    total_score = (
        keyword_score * weights['keyword'] +
        genre_score * weights['genre'] +
        comment_score * weights['comment'] +
        channel_score * weights['channel'] +
        length_score * weights['length'] +
        zgen_penalty
    )

    return {
        'video_id': video_data.get('video_id'),
        'score': round(total_score, 2),
        'keyword_score': round(keyword_score, 2),
        'genre_score': round(genre_score, 2),
        'comment_score': round(comment_score, 2),
        'channel_score': round(channel_score, 2),
        'length_score': round(length_score, 2),
        'highlights': {
            'matched_keywords': matched_keywords,
            'matched_genres': matched_genres,
            'comment_indicators': comment_indicators,
            'length_category': length_category,
            'zgen_memes': zgen_memes,
        }
    }


def filter_by_senior_threshold(
    videos_with_scores: List[Dict[str, Any]],
    threshold: float = 5.0
) -> List[Dict[str, Any]]:
    """
    SeniorScore 임계값 이상인 영상만 필터링

    Args:
        videos_with_scores: SeniorScore가 포함된 영상 리스트
        threshold: 임계값 (기본 5.0)

    Returns:
        필터링된 영상 리스트 (점수 내림차순 정렬)
    """
    filtered = [v for v in videos_with_scores if v.get('senior_score', {}).get('score', 0) >= threshold]
    filtered.sort(key=lambda x: x.get('senior_score', {}).get('score', 0), reverse=True)
    return filtered


if __name__ == '__main__':
    # 테스트 코드
    test_video = {
        'video_id': 'test123',
        'title': '임영웅 트로트 메들리 - 건강한 노후를 위한 음악',
        'description': '어르신들을 위한 트로트 모음',
        'tags': ['트로트', '시니어', '가요'],
        'duration': 'PT15M30S',
        'channel_id': 'test_channel',
    }

    result = calculate_senior_score(test_video)
    print(f"SeniorScore: {result['score']}")
    print(f"매칭 키워드: {result['highlights']['matched_keywords']}")
    print(f"장르: {result['highlights']['matched_genres']}")
