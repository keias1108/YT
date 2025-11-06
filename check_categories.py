"""
한국에서 사용 가능한 YouTube 카테고리 확인 스크립트
"""
import youtube_api

print("=" * 60)
print("한국(KR)에서 사용 가능한 YouTube 카테고리 목록")
print("=" * 60)

categories = youtube_api.get_video_categories(region_code='KR')

print(f"\n총 {len(categories)}개 카테고리:\n")

for cat in categories:
    print(f"ID: {cat['id']:>3} | {cat['title']}")

print("\n" + "=" * 60)
print("시니어층 관련 추천 카테고리:")
print("=" * 60)

# 시니어층에 적합한 카테고리 추천
senior_relevant = ['10', '15', '17', '19', '22', '23', '24', '25', '26', '28']
senior_cat_names = {
    '10': 'Music',
    '15': 'Pets & Animals',
    '17': 'Sports',
    '19': 'Travel & Events',
    '22': 'People & Blogs',
    '23': 'Comedy',
    '24': 'Entertainment',
    '25': 'News & Politics',
    '26': 'Howto & Style',
    '28': 'Science & Technology'
}

available_senior = []
for cat in categories:
    if cat['id'] in senior_relevant:
        available_senior.append(cat['id'])
        print(f"ID: {cat['id']:>3} | {cat['title']} ✓")

print("\n" + "=" * 60)
print(f"자바스크립트 코드에 넣을 배열:")
print("=" * 60)
print(f"const seniorCategoryIds = {available_senior};")
