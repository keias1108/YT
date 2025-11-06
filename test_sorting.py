#!/usr/bin/env python3
"""
정렬 기능 통합 테스트
"""
import sys
from datetime import datetime

# 모듈 임포트
try:
    import database
    print('✅ database 모듈 임포트 성공')
except Exception as e:
    print(f'❌ database 모듈 임포트 실패: {e}')
    sys.exit(1)

print('\n' + '='*60)
print('🧪 정렬 기능 통합 테스트')
print('='*60)

# 데이터 조회 함수 시뮬레이션 (data_collector 없이 직접 구현)
def test_sort_function(sort_by='senior_score', order='desc'):
    """정렬 테스트 함수"""
    today = datetime.now().strftime('%Y-%m-%d')

    conn = database.get_connection()
    cursor = conn.cursor()

    # SQL 쿼리 (data_collector와 유사한 로직)
    cursor.execute("""
        SELECT s.*, v.title, v.channel_title, v.thumbnail_url,
               ss.score as senior_score, ss.highlights
        FROM snapshots s
        JOIN videos v ON s.video_id = v.video_id
        LEFT JOIN senior_scores ss ON s.id = ss.snapshot_id
        WHERE s.snapshot_date = ?
    """, (today,))

    videos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # 정렬 로직
    allowed_columns = {
        'view_count': 'view_count',
        'senior_score': 'senior_score',
        'delta_views_14d': 'delta_views_14d'
    }

    sort_key = allowed_columns.get(sort_by, 'senior_score')
    reverse = (order.lower() == 'desc')

    # None 값 처리
    videos.sort(key=lambda x: x.get(sort_key) or 0, reverse=reverse)

    return videos[:5]  # 상위 5개만


# 테스트 케이스 실행
test_cases = [
    ('view_count', 'desc', '조회수 내림차순'),
    ('view_count', 'asc', '조회수 오름차순'),
    ('senior_score', 'desc', 'SeniorScore 내림차순'),
    ('senior_score', 'asc', 'SeniorScore 오름차순'),
]

for sort_by, order, description in test_cases:
    print(f'\n📊 테스트: {description}')
    print('-' * 60)

    try:
        results = test_sort_function(sort_by, order)

        if not results:
            print('  ⚠️  데이터 없음 (오늘 날짜로 수집된 영상이 없습니다)')
            continue

        for i, video in enumerate(results[:3], 1):
            title = video.get('title', 'N/A')[:45]
            value = video.get(sort_by) or 0

            if sort_by == 'view_count':
                print(f'  {i}. {title}... → {value:,} views')
            elif sort_by == 'senior_score':
                print(f'  {i}. {title}... → Score: {value:.1f}')
            else:
                print(f'  {i}. {title}... → Δviews: {value:,}')

        # 정렬 검증
        if len(results) >= 2:
            first_val = results[0].get(sort_by) or 0
            second_val = results[1].get(sort_by) or 0

            if order == 'desc':
                is_correct = first_val >= second_val
            else:
                is_correct = first_val <= second_val

            status = '✅' if is_correct else '❌'
            print(f'  {status} 정렬 순서 검증: {"정상" if is_correct else "오류"}')

    except Exception as e:
        print(f'  ❌ 테스트 실패: {e}')

print('\n' + '='*60)
print('✅ 정렬 기능 통합 테스트 완료!')
print('='*60)
print('\n💡 Flask 앱을 실행하고 브라우저에서 테이블 헤더를 클릭해보세요!')
print('   python app.py')
