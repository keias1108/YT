"""
Flask 웹 애플리케이션
시니어층 유튜브 트렌드 추적 시스템
"""
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json

import database
import youtube_api
import data_collector

app = Flask(__name__)

# 데이터베이스 초기화
database.init_database()


# ============================================================
# 웹 페이지 라우트
# ============================================================

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/labeling')
def labeling():
    """라벨링 페이지"""
    return render_template('labeling.html')


@app.route('/channels')
def channels():
    """채널 관리 페이지"""
    return render_template('channels.html')


# ============================================================
# API 엔드포인트
# ============================================================

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """
    YouTube 카테고리 목록 조회

    Returns:
        JSON: [{'id': '10', 'title': 'Music'}, ...]
    """
    try:
        categories = youtube_api.get_video_categories(region_code='KR')
        return jsonify({
            'success': True,
            'data': categories
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/collect', methods=['POST'])
def collect_data():
    """
    선택된 카테고리의 인기 영상 수집 (항상 오늘 날짜로 저장)

    Request Body:
        {
            "category_ids": ["10", "19", "22"],
            "max_results": 50
        }

    Returns:
        JSON: 수집 통계
    """
    try:
        data = request.get_json()
        category_ids = data.get('category_ids', [])
        max_results = data.get('max_results', 50)

        if not category_ids:
            return jsonify({
                'success': False,
                'error': '카테고리를 선택해주세요.'
            }), 400

        # 데이터 수집 (snapshot_date=None이면 오늘 날짜 사용)
        stats = data_collector.collect_trending_videos(
            category_ids=category_ids,
            snapshot_date=None,
            max_results=max_results
        )

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos', methods=['GET'])
def get_videos():
    """
    수집된 비디오 조회 (DB에서 읽기, API 호출 X)

    Query Parameters:
        - snapshot_date: 날짜 (YYYY-MM-DD, 기본값: 오늘)
        - senior_threshold: SeniorScore 최소값 (기본값: 0)
        - limit: 최대 반환 수 (기본값: 100)
        - sort_by: 정렬 기준 (기본값: senior_score)
                  허용값: view_count, senior_score, delta_views_14d
        - order: 정렬 방향 (기본값: desc)
                허용값: asc, desc

    Returns:
        JSON: 비디오 리스트
    """
    try:
        snapshot_date = request.args.get('snapshot_date')
        senior_threshold = float(request.args.get('senior_threshold', 0))
        limit = int(request.args.get('limit', 100))
        sort_by = request.args.get('sort_by', 'senior_score')
        order = request.args.get('order', 'desc')

        if snapshot_date is None:
            snapshot_date = datetime.now().strftime('%Y-%m-%d')

        # DB에서 조회 (API 호출 없음)
        videos = data_collector.get_ranked_senior_videos(
            snapshot_date=snapshot_date,
            senior_threshold=senior_threshold,
            limit=limit,
            sort_by=sort_by,
            order=order
        )

        return jsonify({
            'success': True,
            'data': videos,
            'count': len(videos),
            'snapshot_date': snapshot_date
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/video/<video_id>', methods=['GET'])
def get_video_details(video_id):
    """
    비디오 상세 정보 조회

    Returns:
        JSON: 비디오 정보 + SeniorScore + Δviews
    """
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        # 비디오 기본 정보 + 최신 스냅샷 + SeniorScore
        cursor.execute("""
            SELECT
                v.*,
                s.view_count, s.like_count, s.comment_count,
                s.snapshot_date, s.rank_position,
                ss.score as senior_score,
                ss.keyword_score, ss.genre_score, ss.comment_score,
                ss.channel_score, ss.length_score, ss.highlights
            FROM videos v
            LEFT JOIN snapshots s ON v.video_id = s.video_id
            LEFT JOIN senior_scores ss ON s.id = ss.snapshot_id
            WHERE v.video_id = ?
            ORDER BY s.snapshot_date DESC
            LIMIT 1
        """, (video_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({
                'success': False,
                'error': '비디오를 찾을 수 없습니다.'
            }), 404

        video = dict(row)

        # highlights JSON 파싱
        if video.get('highlights'):
            video['highlights'] = json.loads(video['highlights'])

        # tags JSON 파싱
        if video.get('tags'):
            video['tags'] = json.loads(video['tags'])

        # Δviews 계산
        delta_views = database.get_delta_views(video_id, days=14)
        video['delta_views_14d'] = delta_views if delta_views else 0

        return jsonify({
            'success': True,
            'data': video
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/label', methods=['POST'])
def save_label():
    """
    라벨링 저장

    Request Body:
        {
            "video_id": "abc123",
            "is_senior_content": true,
            "labeled_by": "user1",
            "notes": "트로트 영상"
        }
    """
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        is_senior_content = data.get('is_senior_content')
        labeled_by = data.get('labeled_by', 'unknown')
        notes = data.get('notes', '')

        if not video_id or is_senior_content is None:
            return jsonify({
                'success': False,
                'error': 'video_id와 is_senior_content는 필수입니다.'
            }), 400

        # DB에 저장
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO labels (video_id, is_senior_content, labeled_by, notes)
            VALUES (?, ?, ?, ?)
        """, (video_id, int(is_senior_content), labeled_by, notes))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': '라벨이 저장되었습니다.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/labels/unlabeled', methods=['GET'])
def get_unlabeled_videos():
    """
    라벨링 안 된 비디오 가져오기 (주간 50개)

    Query Parameters:
        - limit: 최대 반환 수 (기본값: 50)

    Returns:
        JSON: 비디오 리스트 (SeniorScore 높은 순)
    """
    try:
        limit = int(request.args.get('limit', 50))

        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT
                v.video_id, v.title, v.channel_title, v.thumbnail_url,
                ss.score as senior_score, ss.highlights
            FROM videos v
            JOIN snapshots s ON v.video_id = s.video_id
            JOIN senior_scores ss ON s.id = ss.snapshot_id
            LEFT JOIN labels l ON v.video_id = l.video_id
            WHERE l.id IS NULL
            ORDER BY ss.score DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        videos = []
        for row in rows:
            video = dict(row)
            if video.get('highlights'):
                video['highlights'] = json.loads(video['highlights'])
            videos.append(video)

        return jsonify({
            'success': True,
            'data': videos,
            'count': len(videos)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    전체 통계 조회

    Returns:
        JSON: {
            total_videos: 전체 비디오 수,
            total_snapshots: 전체 스냅샷 수,
            total_labels: 라벨링 수,
            latest_snapshot_date: 최신 스냅샷 날짜
        }
    """
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM videos")
        total_videos = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM snapshots")
        total_snapshots = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM labels")
        total_labels = cursor.fetchone()['count']

        cursor.execute("SELECT MAX(snapshot_date) as latest FROM snapshots")
        latest_snapshot_date = cursor.fetchone()['latest']

        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'total_videos': total_videos,
                'total_snapshots': total_snapshots,
                'total_labels': total_labels,
                'latest_snapshot_date': latest_snapshot_date
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# 채널 관리 API
# ============================================================

@app.route('/api/channels', methods=['GET'])
def get_channels():
    """
    등록된 모든 채널 조회

    Returns:
        JSON: 채널 리스트
    """
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM channels
            WHERE is_whitelist = 1
            ORDER BY updated_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        channels = [dict(row) for row in rows]

        return jsonify({
            'success': True,
            'data': channels,
            'count': len(channels)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels/add', methods=['POST'])
def add_channel():
    """
    채널 추가 (URL 또는 채널 ID)

    Request Body:
        {
            "url": "https://www.youtube.com/@channel_name",
            OR
            "channel_id": "UCxxxxx"
        }

    Returns:
        JSON: 추가된 채널 정보
    """
    try:
        data = request.get_json()
        url = data.get('url')
        channel_id = data.get('channel_id')

        # URL에서 채널 ID 추출
        if url:
            channel_id = youtube_api.get_channel_id_from_url(url)
            if not channel_id:
                return jsonify({
                    'success': False,
                    'error': '채널 ID를 추출할 수 없습니다. URL을 확인해주세요.'
                }), 400

        if not channel_id:
            return jsonify({
                'success': False,
                'error': 'url 또는 channel_id를 제공해주세요.'
            }), 400

        # 채널 정보 가져오기
        channel_info_list = youtube_api.get_channel_info([channel_id])

        if not channel_info_list:
            return jsonify({
                'success': False,
                'error': '채널을 찾을 수 없습니다.'
            }), 404

        channel_info = channel_info_list[0]

        # DB에 저장 (화이트리스트로)
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO channels (channel_id, channel_title, subscriber_count, senior_weight, is_whitelist)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_title = excluded.channel_title,
                subscriber_count = excluded.subscriber_count,
                is_whitelist = 1,
                updated_at = CURRENT_TIMESTAMP
        """, (
            channel_info['channel_id'],
            channel_info['channel_title'],
            channel_info['subscriber_count'],
            1.0,
            1  # 화이트리스트
        ))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': '채널이 추가되었습니다.',
            'data': channel_info
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels/names', methods=['GET'])
def get_channel_names():
    """
    등록된 모든 채널명 리스트 조회 (확장프로그램 - 검색 결과 페이지용)

    Returns:
        JSON: {
            "success": true,
            "data": ["채널명1", "채널명2", ...]
        }
    """
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT channel_title
            FROM channels
            WHERE is_whitelist = 1
        """)

        rows = cursor.fetchall()
        conn.close()

        channel_names = [row['channel_title'] for row in rows]

        return jsonify({
            'success': True,
            'data': channel_names,
            'count': len(channel_names)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels/check/<channel_id>', methods=['GET'])
def check_channel(channel_id):
    """
    채널이 등록되어 있는지 확인 (확장프로그램용)

    Returns:
        JSON: {
            "exists": true/false,
            "channel_title": "채널명" (exists=true일 때만)
        }
    """
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT channel_id, channel_title
            FROM channels
            WHERE channel_id = ? AND is_whitelist = 1
        """, (channel_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                'success': True,
                'exists': True,
                'channel_title': row['channel_title']
            })
        else:
            return jsonify({
                'success': True,
                'exists': False
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels/<channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """
    채널 삭제 (화이트리스트에서 제거)

    Returns:
        JSON: 성공 메시지
    """
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE channels
            SET is_whitelist = 0
            WHERE channel_id = ?
        """, (channel_id,))

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': '채널이 삭제되었습니다.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/channels/collect', methods=['POST'])
def collect_from_channels():
    """
    등록된 채널들의 최근 영상 수집

    Request Body:
        {
            "max_results": 50,  // 채널당 수집 수
            "days": 7           // 최근 N일
        }

    Returns:
        JSON: 수집 통계
    """
    try:
        data = request.get_json() or {}
        max_results = data.get('max_results', 50)
        days = data.get('days', 7)

        # 등록된 채널 조회
        conn = database.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT channel_id FROM channels
            WHERE is_whitelist = 1
        """)

        rows = cursor.fetchall()
        conn.close()

        channel_ids = [row['channel_id'] for row in rows]

        if not channel_ids:
            return jsonify({
                'success': False,
                'error': '등록된 채널이 없습니다. 먼저 채널을 추가해주세요.'
            }), 400

        # 데이터 수집
        stats = data_collector.collect_from_channels(
            channel_ids=channel_ids,
            max_results_per_channel=max_results,
            days=days
        )

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
