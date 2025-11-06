"""
데이터베이스 스키마 및 초기화
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DATABASE_PATH = 'youtube_senior_trends.db'


def get_connection():
    """데이터베이스 연결 반환"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
    return conn


def init_database():
    """데이터베이스 초기화 - 모든 테이블 생성"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. videos 테이블: 비디오 기본 정보
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            channel_id TEXT NOT NULL,
            channel_title TEXT,
            category_id TEXT,
            published_at TEXT,
            thumbnail_url TEXT,
            duration TEXT,
            tags TEXT,  -- JSON 배열
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. snapshots 테이블: 일별 스냅샷 (같은 비디오가 여러 날짜에 수집)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            category_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,  -- YYYY-MM-DD
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            rank_position INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            UNIQUE(video_id, snapshot_date, category_id)  -- 중복 방지
        )
    """)

    # 3. senior_scores 테이블: 시니어 점수 계산 결과 (DEPRECATED - 사용 안함)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senior_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            snapshot_id INTEGER,
            score REAL NOT NULL,
            keyword_score REAL DEFAULT 0,
            genre_score REAL DEFAULT 0,
            comment_score REAL DEFAULT 0,
            channel_score REAL DEFAULT 0,
            length_score REAL DEFAULT 0,
            highlights TEXT,  -- JSON: 매칭된 키워드, 근거 등
            calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        )
    """)

    # 3.5. view_scores 테이블: ViewScore 계산 결과 (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS view_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            snapshot_id INTEGER,
            score REAL NOT NULL,

            -- 각 요소별 점수
            view_score REAL DEFAULT 0,
            subscriber_score REAL DEFAULT 0,
            recency_score REAL DEFAULT 0,
            engagement_score REAL DEFAULT 0,

            -- 사용된 가중치
            view_weight REAL DEFAULT 1.0,
            subscriber_weight REAL DEFAULT 1.0,
            recency_weight REAL DEFAULT 1.0,
            engagement_weight REAL DEFAULT 1.0,

            -- 메타데이터 (JSON: 원본 데이터, 디버깅용)
            metadata TEXT,
            calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        )
    """)

    # 4. labels 테이블: 사람이 라벨링한 결과
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            is_senior_content INTEGER NOT NULL,  -- 0 or 1 (BOOLEAN)
            labeled_by TEXT,
            labeled_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    """)

    # 5. channels 테이블: 채널 정보 및 가중치
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_title TEXT,
            subscriber_count INTEGER,
            senior_weight REAL DEFAULT 1.0,  -- 시니어 가중치
            is_whitelist INTEGER DEFAULT 0,  -- 화이트리스트 여부
            is_blacklist INTEGER DEFAULT 0,  -- 블랙리스트 여부
            last_collected_date TEXT,  -- 마지막 수집 날짜 (YYYY-MM-DD)
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots(snapshot_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_video ON snapshots(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senior_scores_video ON senior_scores(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_view_scores_video ON view_scores(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_view_scores_snapshot ON view_scores(snapshot_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_video ON labels(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_channel ON videos(channel_id)")  # JOIN 성능 향상

    conn.commit()
    conn.close()
    print("✓ 데이터베이스 초기화 완료")


def insert_video(video_data: Dict[str, Any]) -> None:
    """비디오 정보 삽입 (중복 시 무시)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO videos
        (video_id, title, description, channel_id, channel_title,
         category_id, published_at, thumbnail_url, duration, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        video_data['video_id'],
        video_data['title'],
        video_data.get('description', ''),
        video_data['channel_id'],
        video_data['channel_title'],
        video_data.get('category_id', ''),
        video_data.get('published_at', ''),
        video_data.get('thumbnail_url', ''),
        video_data.get('duration', ''),
        json.dumps(video_data.get('tags', []), ensure_ascii=False)
    ))

    conn.commit()
    conn.close()


def insert_snapshot(snapshot_data: Dict[str, Any]) -> Optional[int]:
    """스냅샷 삽입 (중복 시 무시), 삽입된 ID 반환"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO snapshots
            (video_id, category_id, snapshot_date, view_count,
             like_count, comment_count, rank_position)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_data['video_id'],
            snapshot_data['category_id'],
            snapshot_data['snapshot_date'],
            snapshot_data['view_count'],
            snapshot_data.get('like_count', 0),
            snapshot_data.get('comment_count', 0),
            snapshot_data.get('rank_position', 0)
        ))
        conn.commit()
        snapshot_id = cursor.lastrowid
        conn.close()
        return snapshot_id
    except sqlite3.IntegrityError:
        # 중복 데이터 - 이미 해당 날짜에 수집됨
        conn.close()
        return None


def insert_senior_score(score_data: Dict[str, Any]) -> None:
    """시니어 점수 삽입"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO senior_scores
        (video_id, snapshot_id, score, keyword_score, genre_score,
         comment_score, channel_score, length_score, highlights)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        score_data['video_id'],
        score_data.get('snapshot_id'),
        score_data['score'],
        score_data.get('keyword_score', 0),
        score_data.get('genre_score', 0),
        score_data.get('comment_score', 0),
        score_data.get('channel_score', 0),
        score_data.get('length_score', 0),
        json.dumps(score_data.get('highlights', {}), ensure_ascii=False)
    ))

    conn.commit()
    conn.close()


def insert_view_score(score_data: Dict[str, Any]) -> None:
    """ViewScore 삽입"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO view_scores
        (video_id, snapshot_id, score,
         view_score, subscriber_score, recency_score, engagement_score,
         view_weight, subscriber_weight, recency_weight, engagement_weight,
         metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        score_data['video_id'],
        score_data.get('snapshot_id'),
        score_data['score'],
        score_data.get('view_score', 0),
        score_data.get('subscriber_score', 0),
        score_data.get('recency_score', 0),
        score_data.get('engagement_score', 0),
        score_data.get('view_weight', 1.0),
        score_data.get('subscriber_weight', 1.0),
        score_data.get('recency_weight', 1.0),
        score_data.get('engagement_weight', 1.0),
        json.dumps(score_data.get('metadata', {}), ensure_ascii=False)
    ))

    conn.commit()
    conn.close()


def get_snapshots_by_date(date: str) -> List[Dict[str, Any]]:
    """특정 날짜의 모든 스냅샷 조회"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.*, v.title, v.channel_title, v.thumbnail_url,
               v.channel_id, v.published_at,
               ss.score as senior_score, ss.highlights
        FROM snapshots s
        JOIN videos v ON s.video_id = v.video_id
        LEFT JOIN senior_scores ss ON s.id = ss.snapshot_id
        WHERE s.snapshot_date = ?
        ORDER BY s.rank_position
    """, (date,))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_snapshots_by_date_and_source(date: str, data_source: str = 'all') -> List[Dict[str, Any]]:
    """
    특정 날짜의 스냅샷 조회 (데이터 소스 필터링)

    Args:
        date: 조회 날짜 (YYYY-MM-DD)
        data_source: 'channel' (채널 기반), 'category' (카테고리 기반), 'all' (전체)

    Returns:
        필터링된 스냅샷 리스트
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 데이터 소스에 따라 WHERE 절 구성
    if data_source == 'channel':
        where_clause = "s.snapshot_date = ? AND s.category_id LIKE 'channel:%'"
    elif data_source == 'category':
        where_clause = "s.snapshot_date = ? AND s.category_id NOT LIKE 'channel:%'"
    else:  # 'all'
        where_clause = "s.snapshot_date = ?"

    cursor.execute(f"""
        SELECT s.*, v.title, v.channel_title, v.thumbnail_url,
               v.channel_id, v.published_at,
               ss.score as senior_score, ss.highlights
        FROM snapshots s
        JOIN videos v ON s.video_id = v.video_id
        LEFT JOIN senior_scores ss ON s.id = ss.snapshot_id
        WHERE {where_clause}
        ORDER BY s.rank_position
    """, (date,))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_delta_views(video_id: str, days: int = 14) -> Optional[int]:
    """특정 비디오의 Δviews 계산 (최근 N일)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT view_count, snapshot_date
        FROM snapshots
        WHERE video_id = ?
        ORDER BY snapshot_date DESC
        LIMIT ?
    """, (video_id, days + 1))

    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return None

    latest_views = rows[0]['view_count']
    oldest_views = rows[-1]['view_count']
    return latest_views - oldest_views


def get_channel_info(channel_id: str) -> Optional[Dict[str, Any]]:
    """채널 정보 조회"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def upsert_channel(channel_data: Dict[str, Any]) -> None:
    """채널 정보 삽입 또는 업데이트"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO channels (channel_id, channel_title, subscriber_count, senior_weight)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(channel_id) DO UPDATE SET
            channel_title = excluded.channel_title,
            subscriber_count = excluded.subscriber_count,
            updated_at = CURRENT_TIMESTAMP
    """, (
        channel_data['channel_id'],
        channel_data.get('channel_title', ''),
        channel_data.get('subscriber_count', 0),
        channel_data.get('senior_weight', 1.0)
    ))

    conn.commit()
    conn.close()


def get_channel_by_id(channel_id: str) -> Optional[Dict[str, Any]]:
    """채널 정보 조회 (channel_id로)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM channels WHERE channel_id = ?
    """, (channel_id,))

    result = cursor.fetchone()
    conn.close()

    return dict(result) if result else None


def check_snapshot_exists(video_id: str, snapshot_date: str, category_id: str) -> bool:
    """스냅샷 존재 여부 확인"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) as count FROM snapshots
        WHERE video_id = ? AND snapshot_date = ? AND category_id = ?
    """, (video_id, snapshot_date, category_id))

    result = cursor.fetchone()
    conn.close()

    return result['count'] > 0


def check_channel_collected_today(channel_id: str) -> bool:
    """채널이 오늘 수집되었는지 확인"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("""
        SELECT last_collected_date FROM channels
        WHERE channel_id = ?
    """, (channel_id,))

    result = cursor.fetchone()
    conn.close()

    if result and result['last_collected_date'] == today:
        return True
    return False


def update_channel_collected_date(channel_id: str) -> None:
    """채널의 마지막 수집 날짜를 오늘로 업데이트"""
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')

    cursor.execute("""
        UPDATE channels
        SET last_collected_date = ?, updated_at = CURRENT_TIMESTAMP
        WHERE channel_id = ?
    """, (today, channel_id))

    conn.commit()
    conn.close()


if __name__ == '__main__':
    # 데이터베이스 초기화 테스트
    init_database()
