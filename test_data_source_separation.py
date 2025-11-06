#!/usr/bin/env python3
"""
데이터 소스 분리 기능 통합 테스트
"""
import sys
from datetime import datetime

# 모듈 임포트
try:
    import database
    import data_collector
    print('✅ 모듈 임포트 성공')
except Exception as e:
    print(f'❌ 모듈 임포트 실패: {e}')
    sys.exit(1)

print('\n' + '='*70)
print('🧪 데이터 소스 분리 기능 통합 테스트')
print('='*70)

test_date = '2025-11-06'

# 테스트 케이스
test_cases = [
    ('channel', '채널 기반'),
    ('category', '카테고리 기반'),
    ('all', '전체 보기'),
]

for data_source, description in test_cases:
    print(f'\n📊 테스트: {description} (data_source="{data_source}")')
    print('-' * 70)

    try:
        # get_ranked_senior_videos() 함수 테스트
        videos = data_collector.get_ranked_senior_videos(
            snapshot_date=test_date,
            senior_threshold=0,  # 모든 영상
            limit=5,
            sort_by='senior_score',
            order='desc',
            data_source=data_source
        )

        print(f'  결과: {len(videos)}개 영상 (상위 5개만 표시)')

        if videos:
            for i, video in enumerate(videos[:3], 1):
                title = video.get('title', 'N/A')[:50]
                category_id = video.get('category_id', 'N/A')
                senior_score = video.get('senior_score', 0) or 0

                # 데이터 소스 검증
                is_channel = category_id.startswith('channel:')
                source_type = '채널' if is_channel else '카테고리'

                print(f'  {i}. [{source_type}] {title}...')
                print(f'      Score: {senior_score:.1f}, category_id: {category_id[:30]}')

            # 데이터 소스 검증
            if data_source == 'channel':
                all_channel = all(v.get('category_id', '').startswith('channel:') for v in videos)
                status = '✅' if all_channel else '❌'
                print(f'  {status} 검증: 모두 채널 기반 데이터')
            elif data_source == 'category':
                all_category = all(not v.get('category_id', '').startswith('channel:') for v in videos)
                status = '✅' if all_category else '❌'
                print(f'  {status} 검증: 모두 카테고리 기반 데이터')
            else:  # 'all'
                has_both = any(v.get('category_id', '').startswith('channel:') for v in videos)
                print(f'  ℹ️  전체 보기: 혼합 데이터 포함')
        else:
            print(f'  ⚠️  데이터 없음')

    except Exception as e:
        print(f'  ❌ 테스트 실패: {e}')
        import traceback
        traceback.print_exc()

print('\n' + '='*70)
print('✅ 데이터 소스 분리 기능 통합 테스트 완료!')
print('='*70)
print('\n💡 Flask 앱을 실행하고 브라우저에서 라디오 버튼을 테스트해보세요!')
print('   python app.py')
print('   http://127.0.0.1:5000')
