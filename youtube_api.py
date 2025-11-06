"""
YouTube Data API v3 연동 모듈
"""
import os
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
API_KEY = os.getenv('YOUTUBE_API_KEY')

if not API_KEY:
    raise ValueError("YOUTUBE_API_KEY가 .env 파일에 설정되지 않았습니다.")


def get_youtube_client():
    """YouTube API 클라이언트 생성"""
    return build('youtube', 'v3', developerKey=API_KEY)


def get_video_categories(region_code: str = 'KR') -> List[Dict[str, Any]]:
    """
    YouTube 카테고리 목록 가져오기

    Args:
        region_code: 국가 코드 (기본값: KR)

    Returns:
        카테고리 목록 [{'id': '10', 'title': 'Music'}, ...]
    """
    try:
        youtube = get_youtube_client()
        request = youtube.videoCategories().list(
            part='snippet',
            regionCode=region_code
        )
        response = request.execute()

        categories = []
        for item in response.get('items', []):
            categories.append({
                'id': item['id'],
                'title': item['snippet']['title']
            })

        return categories

    except HttpError as e:
        print(f"YouTube API 에러: {e}")
        return []


def get_trending_videos(category_id: str, region_code: str = 'KR', max_results: int = 50) -> List[Dict[str, Any]]:
    """
    특정 카테고리의 인기 영상 목록 가져오기

    Args:
        category_id: 카테고리 ID
        region_code: 국가 코드
        max_results: 최대 결과 수 (기본값: 50)

    Returns:
        영상 목록 (기본 정보만 포함, 상세 정보는 get_video_details 사용)
    """
    try:
        youtube = get_youtube_client()
        request = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            chart='mostPopular',
            regionCode=region_code,
            videoCategoryId=category_id,
            maxResults=max_results
        )
        response = request.execute()

        videos = []
        for idx, item in enumerate(response.get('items', []), start=1):
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})

            videos.append({
                'video_id': item['id'],
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'channel_id': snippet['channelId'],
                'channel_title': snippet['channelTitle'],
                'category_id': snippet['categoryId'],
                'published_at': snippet['publishedAt'],
                'thumbnail_url': snippet['thumbnails'].get('high', {}).get('url', ''),
                'tags': snippet.get('tags', []),
                'duration': content_details.get('duration', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'rank_position': idx
            })

        return videos

    except HttpError as e:
        print(f"YouTube API 에러 (카테고리 {category_id}): {e}")
        return []


def get_video_details(video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    비디오 상세 정보 가져오기 (최대 50개씩)

    Args:
        video_ids: 비디오 ID 리스트

    Returns:
        비디오 상세 정보 리스트
    """
    if not video_ids:
        return []

    try:
        youtube = get_youtube_client()

        # YouTube API는 한 번에 최대 50개까지만 조회 가능
        all_videos = []
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]

            request = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch_ids)
            )
            response = request.execute()

            for item in response.get('items', []):
                snippet = item['snippet']
                statistics = item.get('statistics', {})
                content_details = item.get('contentDetails', {})

                all_videos.append({
                    'video_id': item['id'],
                    'title': snippet['title'],
                    'description': snippet.get('description', ''),
                    'channel_id': snippet['channelId'],
                    'channel_title': snippet['channelTitle'],
                    'category_id': snippet['categoryId'],
                    'published_at': snippet['publishedAt'],
                    'thumbnail_url': snippet['thumbnails'].get('high', {}).get('url', ''),
                    'tags': snippet.get('tags', []),
                    'duration': content_details.get('duration', ''),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0))
                })

        return all_videos

    except HttpError as e:
        print(f"YouTube API 에러 (비디오 상세): {e}")
        return []


def get_channel_info(channel_ids: List[str]) -> List[Dict[str, Any]]:
    """
    채널 정보 가져오기

    Args:
        channel_ids: 채널 ID 리스트

    Returns:
        채널 정보 리스트
    """
    if not channel_ids:
        return []

    try:
        youtube = get_youtube_client()

        all_channels = []
        for i in range(0, len(channel_ids), 50):
            batch_ids = channel_ids[i:i+50]

            request = youtube.channels().list(
                part='snippet,statistics',
                id=','.join(batch_ids)
            )
            response = request.execute()

            for item in response.get('items', []):
                snippet = item['snippet']
                statistics = item.get('statistics', {})

                all_channels.append({
                    'channel_id': item['id'],
                    'channel_title': snippet['title'],
                    'subscriber_count': int(statistics.get('subscriberCount', 0)),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'video_count': int(statistics.get('videoCount', 0))
                })

        return all_channels

    except HttpError as e:
        print(f"YouTube API 에러 (채널 정보): {e}")
        return []


def get_video_comments(video_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
    """
    비디오 댓글 가져오기 (시니어 판별용)

    Args:
        video_id: 비디오 ID
        max_results: 최대 결과 수

    Returns:
        댓글 리스트
    """
    try:
        youtube = get_youtube_client()
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=max_results,
            order='relevance',  # 관련성 높은 댓글 우선
            textFormat='plainText'
        )
        response = request.execute()

        comments = []
        for item in response.get('items', []):
            snippet = item['snippet']['topLevelComment']['snippet']
            comments.append({
                'text': snippet['textDisplay'],
                'author': snippet['authorDisplayName'],
                'like_count': snippet['likeCount'],
                'published_at': snippet['publishedAt']
            })

        return comments

    except HttpError as e:
        # 댓글이 비활성화된 경우 등
        print(f"댓글 가져오기 실패 (비디오 {video_id}): {e}")
        return []


def get_channel_id_from_url(url: str) -> Optional[str]:
    """
    유튜브 채널 URL에서 채널 ID 추출 (또는 채널 ID 직접 입력)

    Args:
        url: 채널 URL (https://www.youtube.com/channel/UCxxxx) 또는 채널 ID (UCxxxx)

    Returns:
        채널 ID 또는 None
    """
    import re

    url = url.strip()

    # 패턴 1: /channel/UCxxxxx 형식
    match = re.search(r'/channel/(UC[\w-]+)', url)
    if match:
        return match.group(1)

    # 패턴 2: UCxxxxx 채널 ID 직접 입력
    if re.match(r'^UC[\w-]+$', url):
        return url

    # 그 외에는 None 반환 (/@handle, /c/ 등은 지원 안함)
    return None


def get_channel_recent_videos(channel_id: str, max_results: int = 50, days: int = 7) -> List[Dict[str, Any]]:
    """
    특정 채널의 최근 업로드 영상 가져오기

    Args:
        channel_id: 채널 ID
        max_results: 최대 결과 수
        days: 최근 N일 이내 영상

    Returns:
        영상 목록
    """
    try:
        from datetime import datetime, timedelta

        youtube = get_youtube_client()

        # 날짜 계산 (RFC 3339 형식)
        published_after = (datetime.utcnow() - timedelta(days=days)).isoformat("T") + "Z"

        # 채널의 업로드 재생목록 ID 가져오기
        channel_request = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        channel_response = channel_request.execute()

        if not channel_response.get('items'):
            print(f"채널을 찾을 수 없습니다: {channel_id}")
            return []

        # 업로드 재생목록 ID (UUxxxxx)
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # 재생목록에서 영상 ID 가져오기
        playlist_request = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=max_results
        )
        playlist_response = playlist_request.execute()

        video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]

        if not video_ids:
            return []

        # 영상 상세 정보 가져오기
        videos = get_video_details(video_ids)

        # 날짜 필터링 및 순위 부여
        filtered_videos = []
        for idx, video in enumerate(videos, start=1):
            published_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
            if published_date >= datetime.fromisoformat(published_after.replace('Z', '+00:00')):
                video['rank_position'] = idx
                filtered_videos.append(video)

        return filtered_videos

    except HttpError as e:
        print(f"YouTube API 에러 (채널 {channel_id}): {e}")
        return []


if __name__ == '__main__':
    # 테스트 코드
    print("=== 카테고리 목록 ===")
    categories = get_video_categories()
    for cat in categories[:5]:
        print(f"{cat['id']}: {cat['title']}")

    print("\n=== Music 카테고리 인기 영상 (상위 5개) ===")
    videos = get_trending_videos('10', max_results=5)
    for video in videos:
        print(f"{video['rank_position']}. {video['title']} - {video['view_count']:,} views")
