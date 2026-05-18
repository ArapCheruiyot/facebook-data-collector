from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import re
from datetime import datetime, timedelta
import os
import sqlite3

app = Flask(__name__)

# ============= FILE PATHS (GENERIC) =============
POSTS_FILE = 'data/facebook_posts.csv'
COMMENTS_FILE = 'data/facebook_comments.csv'
SQLITE_DB = 'data/facebook_sqlite.db'

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# ============= INITIALIZE CSV FILES =============
if not os.path.exists(POSTS_FILE):
    df_posts = pd.DataFrame(columns=[
        'post_id', 'post_date', 'saved_at', 'raw_text', 'location', 'action_type', 
        'people_mentioned', 'emotion', 'key_quote', 'image_url', 'source'
    ])
    df_posts.to_csv(POSTS_FILE, index=False)

if not os.path.exists(COMMENTS_FILE):
    df_comments = pd.DataFrame(columns=[
        'post_id', 'commenter_name', 'comment_text', 'comment_date', 'sentiment'
    ])
    df_comments.to_csv(COMMENTS_FILE, index=False)

# ============= DATE EXTRACTION FUNCTIONS =============

def convert_facebook_date_to_iso(date_str):
    """Convert ANY Facebook date format to ISO format YYYY-MM-DD HH:MM:SS"""
    date_str = date_str.strip()
    now = datetime.now()
    
    # FORMAT 1: "2 hours ago", "45 minutes ago"
    ago_pattern = r'(\d+)\s+(hour|hours|minute|minutes|day|days)\s+ago'
    match = re.search(ago_pattern, date_str, re.IGNORECASE)
    if match:
        number = int(match.group(1))
        unit = match.group(2).lower()
        if 'hour' in unit:
            result = now - timedelta(hours=number)
        elif 'minute' in unit:
            result = now - timedelta(minutes=number)
        elif 'day' in unit:
            result = now - timedelta(days=number)
        else:
            result = now
        return result.strftime('%Y-%m-%d %H:%M:%S')
    
    # FORMAT 2: "just now"
    if 'just now' in date_str.lower():
        return now.strftime('%Y-%m-%d %H:%M:%S')
    
    # FORMAT 3: "Yesterday at 5:40 AM"
    yesterday_pattern = r'Yesterday at (\d+):(\d+) (AM|PM)'
    match = re.search(yesterday_pattern, date_str, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3).upper()
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        yesterday = now - timedelta(days=1)
        result = yesterday.replace(hour=hour, minute=minute, second=0)
        return result.strftime('%Y-%m-%d %H:%M:%S')
    
    # FORMAT 4: "Friday at 2:30 PM"
    day_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) at (\d+):(\d+) (AM|PM)'
    match = re.search(day_pattern, date_str, re.IGNORECASE)
    if match:
        day_name = match.group(1).lower()
        hour = int(match.group(2))
        minute = int(match.group(3))
        ampm = match.group(4).upper()
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        day_map = {'monday':0, 'tuesday':1, 'wednesday':2, 'thursday':3, 'friday':4, 'saturday':5, 'sunday':6}
        target_weekday = day_map.get(day_name, 0)
        current_weekday = now.weekday()
        days_ago = current_weekday - target_weekday
        if days_ago <= 0:
            days_ago += 7
        result_date = now - timedelta(days=days_ago)
        result = result_date.replace(hour=hour, minute=minute, second=0)
        return result.strftime('%Y-%m-%d %H:%M:%S')
    
    # FORMAT 5: Full date "April 28 at 5:40 AM"
    month_map = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }
    pattern = r'([A-Za-z]+) (\d+)(?:st|nd|rd|th)? at (\d+):(\d+) (AM|PM)'
    match = re.search(pattern, date_str, re.IGNORECASE)
    if match:
        month_name = match.group(1).lower()
        day = int(match.group(2))
        hour = int(match.group(3))
        minute = int(match.group(4))
        ampm = match.group(5).upper()
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        month = month_map.get(month_name, '01')
        year = now.year
        try:
            result_date = datetime(year, int(month), day, hour, minute)
            if result_date > now:
                result_date = result_date.replace(year=year - 1)
            return result_date.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    
    # FORMAT 6: Simple date "May 11"
    simple_pattern = r'([A-Za-z]+) (\d+)'
    match = re.search(simple_pattern, date_str)
    if match and 'at' not in date_str.lower():
        month_name = match.group(1).lower()
        day = int(match.group(2))
        month = month_map.get(month_name, '01')
        year = now.year
        try:
            result_date = datetime(year, int(month), day, 12, 0)
            if result_date > now:
                result_date = result_date.replace(year=year - 1)
            return result_date.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    return None

def extract_facebook_date_line_based(raw_text):
    """Extract date from first few lines (fast)"""
    lines = raw_text.split('\n')
    for i in range(min(5, len(lines))):
        line = lines[i].strip()
        if re.match(r'^(\d+)(h|d|m|hr|min)$', line, re.IGNORECASE):
            return convert_facebook_date_to_iso(line)
        if 'yesterday' in line.lower():
            return convert_facebook_date_to_iso(line)
        if 'just now' in line.lower() or line.lower() == 'now':
            return convert_facebook_date_to_iso('just now')
        ago_match = re.search(r'(\d+)\s+(hours?|days?|minutes?)\s+ago', line, re.IGNORECASE)
        if ago_match:
            return convert_facebook_date_to_iso(ago_match.group(0))
    return None

def extract_facebook_date(raw_text):
    line_date = extract_facebook_date_line_based(raw_text)
    if line_date:
        return line_date
    # Full text fallback patterns
    ago_pattern = r'(\d+)\s+(hours?|minutes?|days?)\s+ago'
    match = re.search(ago_pattern, raw_text, re.IGNORECASE)
    if match:
        return convert_facebook_date_to_iso(match.group(0))
    if 'just now' in raw_text.lower():
        return convert_facebook_date_to_iso('just now')
    yesterday_pattern = r'Yesterday at \d+:\d+ (?:AM|PM)'
    match = re.search(yesterday_pattern, raw_text, re.IGNORECASE)
    if match:
        return convert_facebook_date_to_iso(match.group(0))
    day_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) at \d+:\d+ (?:AM|PM)'
    match = re.search(day_pattern, raw_text, re.IGNORECASE)
    if match:
        return convert_facebook_date_to_iso(match.group(0))
    date_pattern = r'([A-Za-z]+ \d+(?:st|nd|rd|th)? at \d+:\d+ (?:AM|PM))'
    match = re.search(date_pattern, raw_text, re.IGNORECASE)
    if match:
        return convert_facebook_date_to_iso(match.group(1))
    simple_pattern = r'([A-Za-z]+ \d+)'
    match = re.search(simple_pattern, raw_text, re.IGNORECASE)
    if match and 'at' not in match.group(0):
        return convert_facebook_date_to_iso(match.group(1))
    return None

def extract_source(raw_text):
    """Generic source detection - returns 'unknown' for generic use"""
    return 'unknown'

def extract_comments_from_raw_text(raw_text, post_id):
    lines = raw_text.split('\n')
    comments = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        name_match = re.match(r'^([A-Z][a-z]+ [A-Z][a-z]+)$', line)
        name_match_single = re.match(r'^([A-Z][a-z]+)$', line)
        if (name_match or name_match_single) and i + 1 < len(lines):
            commenter = name_match.group(1) if name_match else name_match_single.group(1)
            comment_text = lines[i + 1].strip()
            if comment_text and not re.match(r'^\d+[dhw]$', comment_text) and comment_text != 'Reply':
                sentiment = 'neutral'
                comment_lower = comment_text.lower()
                if any(word in comment_lower for word in ['good', 'thanks', 'congrats', 'proud', 'amen', 'bless', 'nice', 'great']):
                    sentiment = 'positive'
                elif any(word in comment_lower for word in ['bad', 'wrong', 'hate', 'useless']):
                    sentiment = 'negative'
                comment_date = 'unknown'
                date_match = re.search(r'(\d+[dw])\s+Reply', ' '.join(lines[i+2:i+4]))
                if date_match:
                    comment_date = date_match.group(1)
                comments.append({
                    'commenter_name': commenter,
                    'comment_text': comment_text[:500],
                    'comment_date': comment_date,
                    'sentiment': sentiment
                })
                i += 2
                continue
        i += 1
    return comments

# ============= KEYWORD DETECTION =============

def init_keywords_table():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE,
            created_at TEXT
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM tracked_keywords')
    count = cursor.fetchone()[0]
    if count == 0:
        default_keywords = ['roads', 'water', 'funeral', 'church', 'fundraising', 
                           'environment', 'education', 'health', 'sports', 'business',
                           'meeting', 'wedding', 'graduation', 'conference', 'workshop']
        for kw in default_keywords:
            cursor.execute('INSERT OR IGNORE INTO tracked_keywords (keyword, created_at) VALUES (?, ?)',
                          (kw, datetime.now().isoformat()))
        print(f"✅ Added {len(default_keywords)} default keywords")
    conn.commit()
    conn.close()
    print("✅ Keywords table initialized")

def detect_action_from_text(raw_text):
    raw_text_lower = raw_text.lower()
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT keyword FROM tracked_keywords ORDER BY keyword')
    keywords = [row[0] for row in cursor.fetchall()]
    conn.close()
    for keyword in keywords:
        if keyword in raw_text_lower:
            return keyword
    return 'other'

def extract_info_from_post(raw_text):
    raw_text_lower = raw_text.lower()
    locations = []
    location_keywords = ['kirobon', 'tulwet', 'ngata', 'sumeek', 'nyaituga', 
                         'ogilgei', 'chepseon', 'kapchemusar', 'roret', 
                         'mosop', 'salgaa', 'lelechwet']
    for loc in location_keywords:
        if loc in raw_text_lower:
            locations.append(loc.capitalize())
    action = detect_action_from_text(raw_text)
    names = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)', raw_text)
    names += re.findall(r'(Mr\.? [A-Z][a-z]+)', raw_text)
    names += re.findall(r'(Hon\.? [A-Z][a-z]+)', raw_text)
    names = list(dict.fromkeys(names))[:5]
    sentences = re.split(r'[.!?\n]+', raw_text)
    key_quote = ''
    for sent in sentences:
        sent = sent.strip()
        if len(sent) > 20 and len(sent) < 150:
            key_quote = sent[:120]
            break
    if not key_quote and sentences:
        key_quote = sentences[0].strip()[:120] if len(sentences[0].strip()) > 20 else ''
    return {
        'locations': ', '.join(locations) if locations else '',
        'action_type': action,
        'people_mentioned': ', '.join(names) if names else '',
        'key_quote': key_quote
    }

# ============= SQLITE INIT =============

def init_sqlite_db():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_date TEXT,
            saved_at TEXT,
            raw_text TEXT,
            location TEXT,
            action_type TEXT,
            people_mentioned TEXT,
            key_quote TEXT,
            source TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fb_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            commenter_name TEXT,
            comment_text TEXT,
            comment_date TEXT,
            sentiment TEXT,
            FOREIGN KEY (post_id) REFERENCES fb_posts(id)
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ SQLite database initialized")

init_keywords_table()
init_sqlite_db()

# ============= ROUTES =============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug_date', methods=['POST'])
def debug_date():
    data = request.json
    raw_text = data.get('post_text', '')
    if not raw_text:
        return jsonify({'error': 'No text provided'}), 400
    line_date = extract_facebook_date_line_based(raw_text)
    regex_date = extract_facebook_date(raw_text)
    lines = raw_text.split('\n')
    first_few_lines = '\n'.join(lines[:5])
    return jsonify({
        'raw_text_preview': first_few_lines[:500],
        'line_based_extraction': line_date,
        'regex_extraction': regex_date,
        'extracted_date': regex_date,
        'date_found': regex_date is not None,
        'hint': 'Facebook dates look like "14h", "Yesterday", or "April 28 at 5:40 AM"'
    })

@app.route('/api/keywords', methods=['GET'])
def get_keywords():
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tracked_keywords ORDER BY keyword')
    keywords = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(keywords)

@app.route('/api/keywords', methods=['POST'])
def add_keyword():
    data = request.json
    keyword = data.get('keyword', '').strip().lower()
    if not keyword or len(keyword) < 2:
        return jsonify({'error': 'Keyword must be at least 2 characters'}), 400
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO tracked_keywords (keyword, created_at) VALUES (?, ?)',
                      (keyword, datetime.now().isoformat()))
        conn.commit()
        keyword_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': f'Keyword "{keyword}" already exists'}), 400
    finally:
        conn.close()
    return jsonify({'message': 'Keyword added', 'id': keyword_id}), 201

@app.route('/api/keywords/<int:keyword_id>', methods=['DELETE'])
def delete_keyword(keyword_id):
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tracked_keywords WHERE id = ?', (keyword_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Keyword deleted'})

@app.route('/save_post_unified', methods=['POST'])
def save_post_unified():
    data = request.json
    raw_text = data.get('post_text', '')
    if not raw_text:
        return jsonify({'error': 'No post text provided'}), 400
    post_date = extract_facebook_date(raw_text)
    if post_date is None:
        post_date = ''
    source = extract_source(raw_text)
    extracted = extract_info_from_post(raw_text)
    df_posts = pd.read_csv(POSTS_FILE)
    post_id = len(df_posts)
    new_post = pd.DataFrame([{
        'post_id': post_id,
        'post_date': post_date,
        'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'raw_text': raw_text[:3000],
        'location': extracted['locations'],
        'action_type': extracted['action_type'],
        'people_mentioned': extracted['people_mentioned'],
        'emotion': '',
        'key_quote': extracted['key_quote'],
        'image_url': data.get('image_url', ''),
        'source': source
    }])
    df_posts = pd.concat([df_posts, new_post], ignore_index=True)
    df_posts.to_csv(POSTS_FILE, index=False)
    comments = extract_comments_from_raw_text(raw_text, post_id)
    comments_saved = 0
    if comments:
        df_comments = pd.read_csv(COMMENTS_FILE)
        for comment in comments:
            new_comment = pd.DataFrame([{
                'post_id': post_id,
                'commenter_name': comment['commenter_name'],
                'comment_text': comment['comment_text'],
                'comment_date': comment['comment_date'],
                'sentiment': comment['sentiment']
            }])
            df_comments = pd.concat([df_comments, new_comment], ignore_index=True)
        df_comments.to_csv(COMMENTS_FILE, index=False)
        comments_saved = len(comments)
    sqlite_post_id = None
    try:
        conn = sqlite3.connect(SQLITE_DB)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO fb_posts (
                post_date, saved_at, raw_text, location, 
                action_type, people_mentioned, key_quote, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_date if post_date else None,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            raw_text[:3000],
            extracted['locations'],
            extracted['action_type'],
            extracted['people_mentioned'],
            extracted['key_quote'],
            source
        ))
        sqlite_post_id = cursor.lastrowid
        for comment in comments:
            cursor.execute('''
                INSERT INTO fb_comments (post_id, commenter_name, comment_text, comment_date, sentiment)
                VALUES (?, ?, ?, ?, ?)
            ''', (sqlite_post_id, comment['commenter_name'], comment['comment_text'], comment['comment_date'], comment['sentiment']))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite save error: {e}")
    return jsonify({
        'message': 'Post saved to both CSV and SQLite',
        'extracted': extracted,
        'post_date': post_date if post_date else '❌ Not detected',
        'comments_found': comments_saved,
        'total_posts': len(df_posts),
        'sqlite_id': sqlite_post_id
    })

@app.route('/get_posts', methods=['GET'])
def get_posts():
    df_posts = pd.read_csv(POSTS_FILE)
    df_posts = df_posts.fillna('')
    return jsonify(df_posts.to_dict(orient='records'))

@app.route('/get_comments', methods=['GET'])
def get_comments():
    if os.path.exists(COMMENTS_FILE):
        df_comments = pd.read_csv(COMMENTS_FILE)
        df_comments = df_comments.fillna('')
        return jsonify(df_comments.to_dict(orient='records'))
    return jsonify([])

@app.route('/get_posts_sqlite', methods=['GET'])
def get_posts_sqlite():
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM fb_posts ORDER BY id DESC')
    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(posts)

@app.route('/sqlite_stats', methods=['GET'])
def sqlite_stats():
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM fb_posts')
    post_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM fb_comments')
    comment_count = cursor.fetchone()[0]
    conn.close()
    return jsonify({'total_posts': post_count, 'total_comments': comment_count})

@app.route('/export_posts_csv', methods=['GET'])
def export_posts_csv():
    return send_file(POSTS_FILE, as_attachment=True, download_name='facebook_posts.csv')

@app.route('/export_comments_csv', methods=['GET'])
def export_comments_csv():
    if os.path.exists(COMMENTS_FILE):
        return send_file(COMMENTS_FILE, as_attachment=True, download_name='facebook_comments.csv')
    return jsonify({'error': 'No comments file yet'}), 404

@app.route('/extract_from_text', methods=['POST'])
def extract_from_text():
    data = request.json
    raw_text = data.get('post_text', '')
    if not raw_text:
        return jsonify({'error': 'No text provided'}), 400
    post_date = extract_facebook_date(raw_text)
    source = extract_source(raw_text)
    extracted = extract_info_from_post(raw_text)
    comments = extract_comments_from_raw_text(raw_text, 0)
    return jsonify({
        'post_date': post_date if post_date else '❌ Not detected',
        'locations': extracted['locations'],
        'action_type': extracted['action_type'],
        'people_mentioned': extracted['people_mentioned'],
        'key_quote': extracted['key_quote'],
        'source': source,
        'comments': comments
    })

@app.route('/test_date_extraction', methods=['POST'])
def test_date_extraction():
    data = request.json
    raw_text = data.get('post_text', '')
    if not raw_text:
        return jsonify({'error': 'No text provided'}), 400
    lines = raw_text.split('\n')
    result = {
        'first_5_lines': lines[:5],
        'line_based_extraction': extract_facebook_date_line_based(raw_text),
        'regex_extraction': extract_facebook_date(raw_text),
        'raw_text_length': len(raw_text),
        'success': extract_facebook_date(raw_text) is not None
    }
    return jsonify(result)


@app.route('/force-refresh')
def force_refresh():
    import os
    template_path = os.path.join('templates', 'index.html')
    if os.path.exists(template_path):
        with open(template_path, 'r') as f:
            content = f.read()
        # Check if new footer exists
        if 'Moses Kipkorir Cheruiyot' in content:
            return '✅ New template detected! Your name is in the file. Clear your browser cache.'
        else:
            return '❌ Old template still on server. Force redeploy needed.'
    return 'Template not found'

if __name__ == '__main__':
    print("🚀 Starting Facebook Data Collector...")
    print("📍 http://127.0.0.1:5000/")
    app.run(debug=True)