"""
데이터 수집 및 스냅샷 저장 로직
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any

import youtube_api
import database
import senior_classifier


def collect_trending_videos(
    category_ids: List[str],
    snapshot_date: str = None,
    max_results: int = 50
) -> Dict[str, Any]:
    """
    선택된 카테고리의 인기 영상 수집 및 저장

    Args:
        category_ids: 카테고리 ID 리스트
        snapshot_date: 스냅샷 날짜 (YYYY-MM-DD), None이면 오늘
        max_results: 카테고리당 최대 수집 수

    Returns:
        수집 결과 통계
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().strftime('%Y-%m-%d')

    # 결과 통계
    stats = {
        'snapshot_date': snapshot_date,
        'total_videos': 0,
        'new_videos': 0,
        'duplicate_skipped': 0,
        'categories': {}
    }

    # 스냅샷 저장 디렉토리 생성
    snapshot_dir = f'data/{snapshot_date}'
    os.makedirs(snapshot_dir, exist_ok=True)

    all_videos = []

    for category_id in category_ids:
        print(f"\n📊 카테고리 {category_id} 수집 중...")

        # 인기 영상 가져오기
        videos = youtube_api.get_trending_videos(
            category_id=category_id,
            max_results=max_results
        )

        if not videos:
            print(f"⚠️  카테고리 {category_id}: 결과 없음")
            stats['categories'][category_id] = {'collected': 0, 'new': 0, 'duplicates': 0}
            continue

        category_stats = {'collected': len(videos), 'new': 0, 'duplicates': 0}

        for video in videos:
            video_id = video['video_id']

            # 중복 체크: 같은 날짜, 같은 카테고리에 이미 수집되었는지
            if database.check_snapshot_exists(video_id, snapshot_date, category_id):
                print(f"  ⏭️  중복 스킵: {video['title'][:50]}")
                category_stats['duplicates'] += 1
                stats['duplicate_skipped'] += 1
                continue

            # 1. 비디오 정보 저장 (videos 테이블)
            database.insert_video(video)

            # 2. 스냅샷 저장 (snapshots 테이블)
            snapshot_data = {
                'video_id': video_id,
                'category_id': category_id,
                'snapshot_date': snapshot_date,
                'view_count': video['view_count'],
                'like_count': video['like_count'],
                'comment_count': video['comment_count'],
                'rank_position': video['rank_position']
            }
            snapshot_id = database.insert_snapshot(snapshot_data)

            if snapshot_id is None:
                # 중복 (이미 존재)
                category_stats['duplicates'] += 1
                stats['duplicate_skipped'] += 1
                continue

            # 3. SeniorScore 계산
            # (댓글은 API 쿼터 절약을 위해 선택적으로)
            # comments = youtube_api.get_video_comments(video_id, max_results=50)
            comments = None  # 일단 댓글 없이

            senior_score_result = senior_classifier.calculate_senior_score(video, comments)
            senior_score_result['snapshot_id'] = snapshot_id

            # 4. SeniorScore 저장
            database.insert_senior_score(senior_score_result)

            # 5. 채널 정보 업데이트 (선택적)
            # channel_info = youtube_api.get_channel_info([video['channel_id']])
            # if channel_info:
            #     database.upsert_channel(channel_info[0])

            # 수집 결과에 추가
            video['senior_score'] = senior_score_result
            all_videos.append(video)

            category_stats['new'] += 1
            stats['new_videos'] += 1

            print(f"  ✓ {video['title'][:50]} (SeniorScore: {senior_score_result['score']})")

        stats['categories'][category_id] = category_stats
        stats['total_videos'] += category_stats['collected']

    # JSONL 파일로 저장 (날짜별 스냅샷)
    snapshot_file = f'{snapshot_dir}/videos.jsonl'
    with open(snapshot_file, 'a', encoding='utf-8') as f:
        for video in all_videos:
            f.write(json.dumps(video, ensure_ascii=False) + '\n')

    print(f"\n✅ 수집 완료: {snapshot_file}")
    print(f"   총 {stats['total_videos']}개, 신규 {stats['new_videos']}개, 중복 스킵 {stats['duplicate_skipped']}개")

    return stats


def calculate_delta_views_for_date(snapshot_date: str, days: int = 14) -> List[Dict[str, Any]]:
    """
    특정 날짜의 모든 비디오에 대해 Δviews 계산

    Args:
        snapshot_date: 기준 날짜
        days: 비교 기간 (기본 14일)

    Returns:
        Δviews가 포함된 비디오 리스트
    """
    snapshots = database.get_snapshots_by_date(snapshot_date)

    results = []
    for snapshot in snapshots:
        video_id = snapshot['video_id']
        delta_views = database.get_delta_views(video_id, days)

        snapshot['delta_views_14d'] = delta_views if delta_views is not None else 0
        results.append(snapshot)

    return results


def get_ranked_senior_videos(
    snapshot_date: str = None,
    senior_threshold: float = 5.0,
    min_delta_views: int = 0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    시니어 친화 영상 랭킹 가져오기

    Args:
        snapshot_date: 날짜 (None이면 오늘)
        senior_threshold: SeniorScore 임계값
        min_delta_views: 최소 Δviews (0이면 필터링 안함)
        limit: 최대 반환 수

    Returns:
        랭킹 리스트 (SeniorScore 내림차순)
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().strftime('%Y-%m-%d')

    # Δviews 계산
    videos = calculate_delta_views_for_date(snapshot_date)

    # 필터링
    filtered = []
    for video in videos:
        senior_score = video.get('senior_score', 0)
        delta_views = video.get('delta_views_14d', 0)

        if senior_score >= senior_threshold and delta_views >= min_delta_views:
            filtered.append(video)

    # 정렬: SeniorScore 내림차순, 동점이면 Δviews 내림차순
    filtered.sort(key=lambda x: (x.get('senior_score', 0), x.get('delta_views_14d', 0)), reverse=True)

    return filtered[:limit]


def load_snapshot_from_file(snapshot_date: str) -> List[Dict[str, Any]]:
    """
    파일에서 스냅샷 불러오기 (API 호출 없이)

    Args:
        snapshot_date: 날짜 (YYYY-MM-DD)

    Returns:
        비디오 리스트
    """
    snapshot_file = f'data/{snapshot_date}/videos.jsonl'

    if not os.path.exists(snapshot_file):
        return []

    videos = []
    with open(snapshot_file, 'r', encoding='utf-8') as f:
        for line in f:
            videos.append(json.loads(line))

    return videos


def collect_from_channels(
    channel_ids: List[str],
    snapshot_date: str = None,
    max_results_per_channel: int = 50,
    days: int = 7,
    skip_today_collected: bool = False
) -> Dict[str, Any]:
    """
    등록된 채널들의 최근 영상 수집

    Args:
        channel_ids: 채널 ID 리스트
        snapshot_date: 스냅샷 날짜 (YYYY-MM-DD), None이면 오늘
        max_results_per_channel: 채널당 최대 수집 수
        days: 최근 N일 이내 영상
        skip_today_collected: 오늘 이미 수집한 채널 건너뛰기 (쿼터 절약)

    Returns:
        수집 결과 통계
    """
    if snapshot_date is None:
        snapshot_date = datetime.now().strftime('%Y-%m-%d')

    # 결과 통계
    stats = {
        'snapshot_date': snapshot_date,
        'total_videos': 0,
        'new_videos': 0,
        'duplicate_skipped': 0,
        'channels_skipped': 0,
        'channels': {}
    }

    # 스냅샷 저장 디렉토리 생성
    snapshot_dir = f'data/{snapshot_date}'
    os.makedirs(snapshot_dir, exist_ok=True)

    all_videos = []

    for channel_id in channel_ids:
        # 오늘 이미 수집한 채널인지 확인 (쿼터 절약)
        if skip_today_collected and database.check_channel_collected_today(channel_id):
            print(f"\n⏭️  채널 {channel_id} 스킵 (오늘 이미 수집 완료)")
            stats['channels_skipped'] += 1
            stats['channels'][channel_id] = {'collected': 0, 'new': 0, 'duplicates': 0, 'skipped': True}
            continue

        print(f"\n📺 채널 {channel_id} 수집 중...")

        # 채널의 최근 영상 가져오기
        videos = youtube_api.get_channel_recent_videos(
            channel_id=channel_id,
            max_results=max_results_per_channel,
            days=days
        )

        if not videos:
            print(f"⚠️  채널 {channel_id}: 결과 없음")
            stats['channels'][channel_id] = {'collected': 0, 'new': 0, 'duplicates': 0}
            continue

        channel_stats = {'collected': len(videos), 'new': 0, 'duplicates': 0}

        for video in videos:
            video_id = video['video_id']

            # 중복 체크: 같은 날짜에 이미 수집되었는지
            # 채널 기반 수집은 category_id를 'channel'로 표시
            if database.check_snapshot_exists(video_id, snapshot_date, f'channel:{channel_id}'):
                print(f"  ⏭️  중복 스킵: {video['title'][:50]}")
                channel_stats['duplicates'] += 1
                stats['duplicate_skipped'] += 1
                continue

            # 1. 비디오 정보 저장 (videos 테이블)
            database.insert_video(video)

            # 2. 스냅샷 저장 (snapshots 테이블)
            snapshot_data = {
                'video_id': video_id,
                'category_id': f'channel:{channel_id}',  # 채널 기반임을 표시
                'snapshot_date': snapshot_date,
                'view_count': video['view_count'],
                'like_count': video['like_count'],
                'comment_count': video['comment_count'],
                'rank_position': video['rank_position']
            }
            snapshot_id = database.insert_snapshot(snapshot_data)

            if snapshot_id is None:
                # 중복 (이미 존재)
                channel_stats['duplicates'] += 1
                stats['duplicate_skipped'] += 1
                continue

            # 3. SeniorScore 계산
            comments = None  # API 쿼터 절약
            senior_score_result = senior_classifier.calculate_senior_score(video, comments)
            senior_score_result['snapshot_id'] = snapshot_id

            # 4. SeniorScore 저장
            database.insert_senior_score(senior_score_result)

            # 수집 결과에 추가
            video['senior_score'] = senior_score_result
            all_videos.append(video)

            channel_stats['new'] += 1
            stats['new_videos'] += 1

            print(f"  ✓ {video['title'][:50]} (SeniorScore: {senior_score_result['score']})")

        stats['channels'][channel_id] = channel_stats
        stats['total_videos'] += channel_stats['collected']

        # 채널 수집 날짜 업데이트 (오늘로 갱신)
        database.update_channel_collected_date(channel_id)

    # JSONL 파일로 저장 (날짜별 스냅샷)
    snapshot_file = f'{snapshot_dir}/videos_channels.jsonl'
    with open(snapshot_file, 'a', encoding='utf-8') as f:
        for video in all_videos:
            f.write(json.dumps(video, ensure_ascii=False) + '\n')

    print(f"\n✅ 수집 완료: {snapshot_file}")
    print(f"   총 {stats['total_videos']}개, 신규 {stats['new_videos']}개, 중복 스킵 {stats['duplicate_skipped']}개")

    return stats


if __name__ == '__main__':
    # 테스트: 카테고리 10 (Music) 수집
    print("=== 데이터 수집 테스트 ===")
    database.init_database()

    stats = collect_trending_videos(
        category_ids=['10'],
        max_results=10
    )

    print("\n=== 수집 통계 ===")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
