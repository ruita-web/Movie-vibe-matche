import streamlit as st
import os
import requests
import json
import random
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_local_storage import LocalStorage

# 1. Load the secret keys
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 2. Page Setup
st.set_page_config(page_title="Movie Vibe Matcher", page_icon="🍿", layout="wide")

# ==========================================
# 🎨 THE REAL UI OVERHAUL (CSS)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    .stApp { background-color: #0a0a0c !important; color: #fff; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; max-width: 95% !important; }

    /* Pure Icon Buttons */
    .stButton > button {
        background: transparent !important;
        border: none !important;
        color: #fff !important;
        box-shadow: none !important;
        padding: 0 !important;
        font-size: 1.2rem !important;
        transition: transform 0.2s ease, color 0.2s ease !important;
    }
    .stButton > button:hover {
        color: #ff4b4b !important;
        transform: scale(1.15);
        background: transparent !important;
    }
    
    /* Main Action Buttons */
    .main-btn .stButton > button, .action-btn .stButton > button {
        background: #ff4b4b !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        width: 100% !important;
        border: 1px solid #ff4b4b !important;
    }
    .main-btn .stButton > button:hover, .action-btn .stButton > button:hover { 
        background: #ff7676 !important; 
        transform: none; 
    }
    
    /* Secondary Button */
    .secondary-btn .stButton > button {
        background: transparent !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        border: 1px solid #444 !important;
    }
    .secondary-btn .stButton > button:hover {
        border-color: #ff4b4b !important;
        color: #ff4b4b !important;
    }

    /* Movie Cards */
    .tv-card { background: transparent; border: none; margin-bottom: 20px; }
    .tv-card img { border-radius: 8px; transition: transform 0.3s ease, box-shadow 0.3s ease; box-shadow: 0 4px 10px rgba(0,0,0,0.5); width: 100%; object-fit: cover; }
    .tv-card img:hover { transform: scale(1.05); box-shadow: 0 8px 20px rgba(255, 75, 75, 0.2); }
    
    /* Rich Cards */
    .movie-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .movie-card:hover { border-color: rgba(255, 75, 75, 0.4); }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 30px; justify-content: center; border-bottom: 1px solid #222; padding-bottom: 10px;}
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: 600; color: #888; }
    .stTabs [aria-selected="true"] { color: #ff4b4b !important; }
    
    /* Inputs & Selectboxes */
    .stTextInput > div > div > input { background-color: #1a1a1a !important; color: white !important; border-radius: 8px !important; border: 1px solid #333 !important; padding: 12px 20px !important; }
    div[data-baseweb="select"] > div { background-color: #1a1a1a !important; border-radius: 8px !important; color: white !important; border: 1px solid #333 !important; }
    
    /* Dropdown Menu (Popover) styling */
    div[data-baseweb="popover"] { background-color: #1a1a1a !important; border: 1px solid #333 !important; }
    ul[data-baseweb="menu"] { background-color: #1a1a1a !important; }
    li[data-baseweb="menu-item"] { color: white !important; }
    li[data-baseweb="menu-item"]:hover { background-color: #333 !important; color: #ff4b4b !important; }
    
    /* Trailer Button */
    .trailer-btn { display: inline-flex; align-items: center; justify-content: center; background: #ff4b4b; color: white !important; text-decoration: none !important; padding: 10px 15px; border-radius: 6px; font-weight: 600; font-size: 0.9rem; width: 100%; white-space: nowrap;}
    .trailer-btn:hover { background: #ff7676; }

    /* 📱 BULLETPROOF MOBILE CSS */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 10px !important; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { width: calc(50% - 10px) !important; flex: 0 0 calc(50% - 10px) !important; min-width: calc(50% - 10px) !important; }
        div[data-testid="column"] > div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 0 !important; }
        div[data-testid="column"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { width: 33.33% !important; flex: 1 1 33.33% !important; min-width: 33.33% !important; padding: 0 2px !important; }
        div[data-testid="column"] > div[data-testid="stHorizontalBlock"] .stButton > button { padding: 4px !important; font-size: 1.1rem !important; }
        .movie-card > div { flex-direction: column !important; align-items: flex-start !important; }
        .movie-card img { width: 100% !important; max-width: 200px !important; margin-bottom: 15px !important; align-self: center !important; }
        .top-bar-spacer { display: none !important; }
    }
</style>
""", unsafe_allow_html=True)

# 🌍 COUNTRIES DICTIONARY
COUNTRIES = {
    "US": "United States", "KE": "Kenya", "GB": "United Kingdom",
    "CA": "Canada", "AU": "Australia", "IN": "India",
    "ZA": "South Africa", "NG": "Nigeria", "DE": "Germany",
    "FR": "France", "ES": "Spain", "IT": "Italy",
    "BR": "Brazil", "MX": "Mexico", "JP": "Japan"
}

if "region" not in st.session_state:
    st.session_state.region = "US"

# 3. Header & Top Bar Layout
col_title, col_spacer, col_region = st.columns([3, 2, 1])
with col_title:
    st.markdown("<h1 style='text-align: left; font-weight: 800; letter-spacing: -1px; margin-bottom: 0;'>Movie Vibe</h1>", unsafe_allow_html=True)
with col_region:
    st.selectbox("Region", options=list(COUNTRIES.keys()), format_func=lambda x: f"🌍 {COUNTRIES[x]}", key="region", label_visibility="collapsed")

st.markdown("<p style='text-align: left; color: #888; margin-bottom: 2rem;'>Find your next watch</p>", unsafe_allow_html=True)

# 4. TMDB Data
GENRES = {"Action": 28, "Comedy": 35, "Horror": 27, "Sci-Fi": 878, "Drama": 18, "Thriller": 53, "Romance": 10749, "Animation": 16, "Mystery": 9648, "Fantasy": 14, "Adventure": 12, "Crime": 80}
DECADES = {"2020s": ("2020-01-01", "2029-12-31"), "2010s": ("2010-01-01", "2019-12-31"), "2000s": ("2000-01-01", "2009-12-31"), "90s": ("1990-01-01", "1999-12-31"), "80s": ("1980-01-01", "1989-12-31"), "70s": ("1970-01-01", "1979-12-31")}
SURPRISE_VIBES = ["mind-bending", "tearjerker", "funny but sad", "action-packed", "slow burn", "feel-good", "dark and gritty", "visually stunning", "twist ending", "nostalgic"]

# ==========================================
# 💾 NEW: WATCHLIST LOGIC WITH LOCAL STORAGE
# ==========================================
localS = LocalStorage()

if "watchlist" not in st.session_state:
    saved_list = localS.getItem("user_watchlist")
    if saved_list and isinstance(saved_list, str):
        try:
            st.session_state.watchlist = json.loads(saved_list)
        except:
            st.session_state.watchlist = []
    else:
        st.session_state.watchlist = []

def save_watchlist_to_browser():
    localS.setItem("user_watchlist", json.dumps(st.session_state.watchlist))

if "current_candidates" not in st.session_state: st.session_state.current_candidates = []
if "current_recommendations" not in st.session_state: st.session_state.current_recommendations = []
if "media_type" not in st.session_state: st.session_state.media_type = "Both"
if "genres" not in st.session_state: st.session_state.genres = []
if "decades" not in st.session_state: st.session_state.decades = []
if "min_rating" not in st.session_state: st.session_state.min_rating = 6.0
if "num_recs" not in st.session_state: st.session_state.num_recs = 5
if "vibe" not in st.session_state: st.session_state.vibe = ""
if "run_search" not in st.session_state: st.session_state.run_search = False
if "is_surprise" not in st.session_state: st.session_state.is_surprise = False
if "similar_target" not in st.session_state: st.session_state.similar_target = None

def toggle_watchlist(media_id, title, poster, rating, p_type):
    is_saved = any(item['id'] == media_id for item in st.session_state.watchlist)
    if is_saved:
        st.session_state.watchlist = [m for m in st.session_state.watchlist if m['id'] != media_id]
        st.toast(f"Removed **{title}**")
    else:
        st.session_state.watchlist.append({"id": media_id, "title": title, "poster": poster, "rating": rating, "type": p_type})
        st.toast(f"Added **{title}**")
    
    save_watchlist_to_browser()
    st.rerun()

def find_similar_callback(title):
    st.session_state.similar_target = title

# 5. API Functions (With Timeouts and Error Handling)
def get_watch_providers(media_id, media_type):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/watch/providers?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get("results", {}).get(st.session_state.region, {})
        providers = []
        if "flatrate" in data:
            for p in data["flatrate"]: providers.append(f"📺 {p['provider_name']}")
        if "rent" in data:
            for p in data["rent"]:
                if f"🎟️ {p['provider_name']}" not in providers: providers.append(f"🎟️ {p['provider_name']}")
        return " | ".join(providers) if providers else "Not available on streaming."
    except:
        return "Could not load provider data."

def get_trailer_url(media_id, media_type):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/videos?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        videos = response.json().get("results", [])
        for video in videos:
            if video.get("site") == "YouTube" and video.get("type") == "Trailer": return f"https://www.youtube.com/watch?v={video.get('key')}"
        for video in videos:
            if video.get("site") == "YouTube": return f"https://www.youtube.com/watch?v={video.get('key')}"
    except:
        pass
    return None

@st.cache_data(ttl=3600)
def get_credits(media_id, media_type):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{media_id}/credits?api_key={TMDB_API_KEY}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        directors = [crew['name'] for crew in data.get('crew', []) if crew.get('job') == 'Director']
        director_str = directors[0] if directors else "Unknown"
        cast = [actor['name'] for actor in data.get('cast', [])[:3]]
        return director_str, ", ".join(cast) if cast else "Unknown"
    except:
        return "Unknown", "Unknown"

@st.cache_data(ttl=3600)
def fetch_trending(media_type):
    try:
        response = requests.get(f"https://api.themoviedb.org/3/trending/{media_type}/week?api_key={TMDB_API_KEY}", timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])[:10]
    except:
        return []

@st.cache_data(ttl=3600)
def fetch_upcoming(media_type):
    try:
        today = date.today().isoformat()
        if media_type == "movie":
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&sort_by=popularity.desc&primary_release_date.gte={today}"
        else:
            url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&sort_by=popularity.desc&first_air_date.gte={today}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])[:10]
    except:
        return []

def search_media(query):
    try:
        response = requests.get(f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={query}", timeout=10)
        response.raise_for_status()
        return [r for r in response.json().get("results", []) if r.get('media_type') in ['movie', 'tv']]
    except:
        return []

def fetch_discover(media_type, genres, decades, min_rating, vibe=""):
    try:
        candidates = []
        genre_ids = ",".join([str(GENRES[g]) for g in genres]) if genres else ""
        date_ranges = [DECADES[d] for d in decades] if decades else [(None, None)]
        
        if vibe:
            search_res = search_media(vibe)
            if search_res:
                for sr in search_res[:3]:
                    if sr.get('title', '').lower() == vibe.lower() or sr.get('name', '').lower() == vibe.lower():
                        rec_url = f"https://api.themoviedb.org/3/{sr.get('media_type')}/{sr.get('id')}/recommendations?api_key={TMDB_API_KEY}"
                        rec_res = requests.get(rec_url, timeout=10)
                        if rec_res.status_code == 200:
                            candidates.extend(rec_res.json().get("results", [])[:15])
                        break
        
        for start_date, end_date in date_ranges:
            movie_url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&sort_by=popularity.desc&vote_count.gte=50&vote_average.gte={min_rating}"
            if genre_ids: movie_url += f"&with_genres={genre_ids}"
            if start_date: movie_url += f"&primary_release_date.gte={start_date}&primary_release_date.lte={end_date}"
            tv_url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&sort_by=popularity.desc&vote_count.gte=50&vote_average.gte={min_rating}"
            if genre_ids: tv_url += f"&with_genres={genre_ids}"
            if start_date: tv_url += f"&first_air_date.gte={start_date}&first_air_date.lte={end_date}"
            
            if media_type in ["Movies", "Both"]:
                res = requests.get(movie_url, timeout=10)
                if res.status_code == 200: candidates.extend(res.json().get("results", [])[:10])
            if media_type in ["TV Shows", "Both"]:
                res = requests.get(tv_url, timeout=10)
                if res.status_code == 200: candidates.extend(res.json().get("results", [])[:10])
                
        seen_ids = set()
        unique_candidates = []
        for m in candidates:
            if m['id'] not in seen_ids:
                unique_candidates.append(m)
                seen_ids.add(m['id'])
        return unique_candidates[:40]
    except:
        return []

def get_ai_recommendation(vibe, media_list, genres, decades, media_type, num_recs):
    try:
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY, timeout=15)
        media_list_text = ""
        for m in media_list:
            title = m.get('title') or m.get('name') or 'Unknown'
            date_val = m.get('release_date') or m.get('first_air_date') or 'Unknown'
            year = date_val[:4] if date_val != 'Unknown' else 'Unknown'
            media_list_text += f"Title: {title} ({year})\nOverview: {m.get('overview')}\n\n"
        vibe_text = f"The user wants this vibe: '{vibe}'." if vibe else "Pick the most interesting ones."
        prompt = f"""
        The user is looking for a {', '.join(genres) if genres else 'Any'} {media_type} from the {', '.join(decades) if decades else 'Any'}.
        {vibe_text}
        Candidates: {media_list_text}
        Task: Select top {num_recs}. Output ONLY a valid JSON array: [{{"title": "Title", "reason": "Why it matches"}}]
        """
        response = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}], temperature=0.7)
        ai_text = response.choices[0].message.content.strip().replace("```json", "").replace("```", "")
        return json.loads(ai_text)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None 

# ==========================================
# 🚨 POPUP DIALOGS
# ==========================================
@st.dialog("Similar Movies", width="large")
def show_similar_dialog(target_title):
    st.markdown(f"### If you liked **{target_title}**, try these:")
    with st.spinner("Finding matches..."):
        candidates = fetch_discover("Both", [], [], 0.0, target_title)
        candidates = [m for m in candidates if target_title.lower() not in (m.get('title') or m.get('name') or '').lower()]
        
        if candidates:
            recs = get_ai_recommendation(target_title, candidates, [], [], "Both", 5)
            if recs is None:
                st.error("🚨 Our AI is a bit busy right now. Please close this and try again in a few seconds.")
                return
                
            if recs:
                for i, rec in enumerate(recs):
                    t = rec.get("title", "")
                    r = rec.get("reason", "")
                    poster_url = "https://via.placeholder.com/500x750/24243e/ffffff?text=No+Poster"
                    rt = "Not yet rated"
                    m_id = None
                    is_tv = False
                    
                    for m in candidates:
                        m_title = m.get('title') or m.get('name') or ''
                        if t.lower() in m_title.lower() or m_title.lower() in t.lower():
                            if m.get('poster_path'): poster_url = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
                            vote_avg = m.get('vote_average', 0)
                            if vote_avg > 0: rt = f"{vote_avg:.1f}/10"
                            m_id = m.get('id')
                            if 'name' in m and 'first_air_date' in m: is_tv = True
                            break
                    
                    p_type = "tv" if is_tv else "movie"
                    
                    c1, c2 = st.columns([1, 3])
                    with c1: st.image(poster_url, width='stretch')
                    with c2:
                        st.markdown(f"#### {t}")
                        st.markdown(f"⭐ **{rt}**")
                        st.write(r)
                        
                        if m_id:
                            is_saved = any(item['id'] == m_id for item in st.session_state.watchlist)
                            if st.button("Save", key=f"dlg_save_{m_id}_{i}", icon=":material/check:" if is_saved else ":material/add:", width='stretch'):
                                toggle_watchlist(m_id, t, poster_url, rt, p_type)
                                st.rerun()
                    st.divider()

@st.dialog("Details", width="large")
def show_details(m, media_type):
    title = m.get('title') or m.get('name')
    rating = f"{m.get('vote_average', 0):.1f}/10" if m.get('vote_average') else "Not yet rated"
    poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750/24243e/ffffff?text=No+Poster"
    p_type = media_type.lower() if media_type else "movie"
    
    col1, col2 = st.columns([1, 2])
    with col1: st.image(poster, width='stretch')
    with col2:
        st.markdown(f"## {title}")
        st.markdown(f"⭐ **{rating}**")
        director, cast = get_credits(m['id'], p_type)
        st.markdown(f"🎬 **Dir:** {director} | 🎭 **Cast:** {cast}")
        st.write(m.get('overview', 'No overview available.'))
        providers = get_watch_providers(m['id'], p_type)
        st.info(f"**Where to Watch ({COUNTRIES[st.session_state.region]}):** {providers}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            trailer = get_trailer_url(m['id'], p_type)
            if trailer: st.markdown(f'<a href="{trailer}" target="_blank" class="trailer-btn">▶️ Trailer</a>', unsafe_allow_html=True)
        with c2:
            is_saved = any(item['id'] == m['id'] for item in st.session_state.watchlist)
            if st.button("", key=f"modal_save_{m['id']}", icon=":material/check:" if is_saved else ":material/add:", width='stretch'):
                toggle_watchlist(m['id'], title, poster, rating, p_type)
        with c3:
            st.button("", key=f"modal_sim_{m['id']}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(title,), width='stretch')

# ==========================================
# SESSION STATE CALLBACKS
# ==========================================
def do_search(): 
    st.session_state.run_search = True
    st.session_state.is_surprise = False

def do_surprise():
    st.session_state.media_type = random.choice(["Movies", "TV Shows", "Both"])
    st.session_state.genres = [random.choice(list(GENRES.keys()))]
    st.session_state.decades = [random.choice(list(DECADES.keys()))]
    st.session_state.min_rating = random.choice([5.0, 6.0, 7.0])
    st.session_state.vibe = random.choice(SURPRISE_VIBES)
    st.session_state.run_search = True
    st.session_state.is_surprise = True

# ==========================================
# TABS
# ==========================================
tab_home, tab_upcoming, tab_search, tab_watchlist = st.tabs(["Trending", "Upcoming", "Vibe Matcher", "Watchlist"])

# ==========================================
# TAB 1: TRENDING
# ==========================================
with tab_home:
    st.markdown("### Trending Movies")
    for i, m in enumerate(fetch_trending("movie")):
        if i % 5 == 0: cols = st.columns(5)
        with cols[i % 5]:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750"
            st.image(poster, width='stretch')
            st.markdown(f"<div style='font-weight:600; font-size:0.95rem; margin-top:8px;'>{m.get('title')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:#ffd700; font-size:0.85rem; margin-bottom:8px;'>⭐ {m.get('vote_average', 0):.1f}</div>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("", key=f"i_m_{m['id']}_{i}", icon=":material/info:", help="Details"):
                    show_details(m, "movie")
            with c2:
                is_saved = any(item['id'] == m['id'] for item in st.session_state.watchlist)
                if st.button("", key=f"s_m_{m['id']}_{i}", icon=":material/check:" if is_saved else ":material/add:", help="Save"):
                    toggle_watchlist(m['id'], m.get('title'), poster, f"{m.get('vote_average', 0):.1f}", "movie")
            with c3:
                st.button("", key=f"sim_m_{m['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(m.get('title'),))
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Trending TV Shows")
    for i, m in enumerate(fetch_trending("tv")):
        if i % 5 == 0: cols = st.columns(5)
        with cols[i % 5]:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750"
            st.image(poster, width='stretch')
            st.markdown(f"<div style='font-weight:600; font-size:0.95rem; margin-top:8px;'>{m.get('name')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:#ffd700; font-size:0.85rem; margin-bottom:8px;'>⭐ {m.get('vote_average', 0):.1f}</div>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("", key=f"i_tv_{m['id']}_{i}", icon=":material/info:", help="Details"):
                    show_details(m, "tv")
            with c2:
                is_saved = any(item['id'] == m['id'] for item in st.session_state.watchlist)
                if st.button("", key=f"s_tv_{m['id']}_{i}", icon=":material/check:" if is_saved else ":material/add:", help="Save"):
                    toggle_watchlist(m['id'], m.get('name'), poster, f"{m.get('vote_average', 0):.1f}", "tv")
            with c3:
                st.button("", key=f"sim_tv_{m['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(m.get('name'),))
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 2: UPCOMING
# ==========================================
with tab_upcoming:
    st.text_input("Search any future movie...", placeholder="e.g., 'Avengers Doomsday'", key="up_search")
    if st.session_state.get("up_search"):
        res = search_media(st.session_state.up_search)
        if res:
            if st.button(f"View Details for {res[0].get('title') or res[0].get('name')}", width='stretch'):
                show_details(res[0], res[0].get('media_type'))

    st.markdown("### Upcoming Movies")
    for i, m in enumerate(fetch_upcoming("movie")):
        if i % 5 == 0: cols = st.columns(5)
        with cols[i % 5]:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750"
            st.image(poster, width='stretch')
            st.markdown(f"<div style='font-weight:600; font-size:0.95rem; margin-top:8px;'>{m.get('title')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:#888; font-size:0.85rem; margin-bottom:8px;'>📅 {m.get('release_date', 'TBA')}</div>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("", key=f"ui_m_{m['id']}_{i}", icon=":material/info:", help="Details"):
                    show_details(m, "movie")
            with c2:
                is_saved = any(item['id'] == m['id'] for item in st.session_state.watchlist)
                if st.button("", key=f"us_m_{m['id']}_{i}", icon=":material/check:" if is_saved else ":material/add:", help="Save"):
                    toggle_watchlist(m['id'], m.get('title'), poster, f"{m.get('vote_average', 0):.1f}", "movie")
            with c3:
                st.button("", key=f"sim_up_m_{m['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(m.get('title'),))
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Upcoming TV Shows")
    for i, m in enumerate(fetch_upcoming("tv")):
        if i % 5 == 0: cols = st.columns(5)
        with cols[i % 5]:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750"
            st.image(poster, width='stretch')
            st.markdown(f"<div style='font-weight:600; font-size:0.95rem; margin-top:8px;'>{m.get('name')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:#888; font-size:0.85rem; margin-bottom:8px;'>📅 {m.get('first_air_date', 'TBA')}</div>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("", key=f"ui_tv_{m['id']}_{i}", icon=":material/info:", help="Details"):
                    show_details(m, "tv")
            with c2:
                is_saved = any(item['id'] == m['id'] for item in st.session_state.watchlist)
                if st.button("", key=f"us_tv_{m['id']}_{i}", icon=":material/check:" if is_saved else ":material/add:", help="Save"):
                    toggle_watchlist(m['id'], m.get('name'), poster, f"{m.get('vote_average', 0):.1f}", "tv")
            with c3:
                st.button("", key=f"sim_up_tv_{m['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(m.get('name'),))
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 3: VIBE MATCHER
# ==========================================
with tab_search:
    with st.expander("🔍 Filters & Options", expanded=False):
        col1, col2, col3 = st.columns([1, 2, 2])
        with col1: st.selectbox("Media", ["Movies", "TV Shows", "Both"], key="media_type")
        with col2: st.multiselect("Genres", list(GENRES.keys()), key="genres")
        with col3: st.multiselect("Decades", list(DECADES.keys()), key="decades")
        
        col4, col5 = st.columns(2)
        with col4: st.slider("Min Rating", 0.0, 10.0, 6.0, 0.5, key="min_rating")
        with col5: st.slider("Results", 3, 10, 5, key="num_recs")
    
    st.text_input("Vibe", placeholder="e.g. 'lonely space' or a movie title...", key="vibe")
    
    c1, c2 = st.columns(2)
    with c1: st.markdown('<div class="main-btn">', unsafe_allow_html=True); st.button("Find Match", on_click=do_search); st.markdown('</div>', unsafe_allow_html=True)
    with c2: st.markdown('<div class="main-btn">', unsafe_allow_html=True); st.button("🎲 Surprise", on_click=do_surprise); st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.run_search:
        st.session_state.run_search = False 
        with st.spinner("Searching..."):
            candidates = fetch_discover(st.session_state.media_type, st.session_state.genres, st.session_state.decades, st.session_state.min_rating, st.session_state.vibe)
            if candidates:
                recommendations = get_ai_recommendation(st.session_state.vibe, candidates, st.session_state.genres, st.session_state.decades, st.session_state.media_type, st.session_state.num_recs)
                
                if recommendations is None:
                    st.error("🚨 Our AI is currently handling a lot of requests. Please wait a few seconds and try again!")
                    st.session_state.current_recommendations = []
                elif not recommendations:
                    st.warning("No matches found. Try adjusting your filters or vibe.")
                    st.session_state.current_recommendations = []
                else:
                    st.session_state.current_candidates = candidates
                    st.session_state.current_recommendations = recommendations
            else:
                st.error("🚨 Could not connect to the movie database. Please check your internet or try again later.")
                st.session_state.current_recommendations = []

    if st.session_state.current_recommendations:
        st.markdown(f"### Top Matches")
        for i, rec in enumerate(st.session_state.current_recommendations):
            title = rec.get("title", "")
            reason = rec.get("reason", "")
            poster_url = "https://via.placeholder.com/500x750/24243e/ffffff?text=No+Poster"
            rating = "Not yet rated"
            media_id = None
            is_tv = False
            
            for m in st.session_state.current_candidates:
                m_title = m.get('title') or m.get('name') or ''
                if title.lower() in m_title.lower() or m_title.lower() in title.lower():
                    if m.get('poster_path'): poster_url = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
                    vote_avg = m.get('vote_average', 0)
                    if vote_avg > 0: rating = f"{vote_avg:.1f}/10"
                    media_id = m.get('id')
                    if 'name' in m and 'first_air_date' in m: is_tv = True
                    break
            
            p_type = "tv" if is_tv else "movie"
            providers_text = "Not available"
            trailer_html = ""
            credits_html = ""
            
            if media_id:
                providers_text = get_watch_providers(media_id, p_type)
                trailer_url = get_trailer_url(media_id, p_type)
                director, cast = get_credits(media_id, p_type)
                credits_html = f"<p style='color: #aaa; font-size: 0.95rem; margin-top: -5px; margin-bottom: 15px;'>🎬 <b>Dir:</b> {director} | 🎭 <b>Cast:</b> {cast}</p>"
                
                if trailer_url:
                    trailer_html = f'<a href="{trailer_url}" target="_blank" class="trailer-btn">▶️ Watch Trailer</a>'

            st.html(f"""
            <div class="movie-card">
                <div style="display: flex; gap: 20px; align-items: center;">
                    <img src="{poster_url}" style="width: 140px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); object-fit: cover;">
                    <div style="width: 100%;">
                        <h3 style="margin-top: 0; color: #fff; font-size: 1.8rem; margin-bottom: 5px;">{title}</h3>
                        
                        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 5px;">
                            <div style="display: flex; align-items: center; gap: 5px;">
                                <span style="color: #ffd700; font-size: 1.3rem;">⭐</span>
                                <span style="color: #ffd700; font-weight: bold; font-size: 1.1rem;">{rating}</span>
                            </div>
                            <span style="color: #888; font-size: 0.9rem;">TMDB Rating</span>
                        </div>
                        
                        {credits_html}
                        
                        <p style="color: #ccc; font-size: 1.05rem; line-height: 1.5; margin-bottom: 15px;">{reason}</p>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 15px;">
                            <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border-left: 4px solid #ff4b4b; flex-grow: 1;">
                                <span style="color: #aaa; font-size: 0.9rem; font-weight: bold;">WHERE TO WATCH ({COUNTRIES[st.session_state.region]}):</span><br>
                                <span style="color: #fff; font-size: 0.95rem;">{providers_text}</span>
                            </div>
                            {trailer_html}
                        </div>
                    </div>
                </div>
            </div>
            """)
            
            if media_id:
                b1, b2, b3 = st.columns([1, 1, 1])
                with b1:
                    is_saved = any(item['id'] == media_id for item in st.session_state.watchlist)
                    st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                    if st.button("Saved" if is_saved else "Save", key=f"save_v_{media_id}_{i}", icon=":material/check:" if is_saved else ":material/add:", width='stretch'):
                        toggle_watchlist(media_id, title, poster_url, rating, p_type)
                    st.markdown('</div>', unsafe_allow_html=True)
                with b2:
                    st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                    st.button("Find Similar", key=f"sim_v_{media_id}_{i}", icon=":material/auto_awesome:", on_click=find_similar_callback, args=(title,), width='stretch')
                    st.markdown('</div>', unsafe_allow_html=True)
                with b3:
                    st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
                    if st.button("More Info", key=f"info_v_{media_id}_{i}", icon=":material/info:", width='stretch'):
                        m_data = next((x for x in st.session_state.current_candidates if x['id'] == media_id), None)
                        if m_data: show_details(m_data, p_type)
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("This title isn't in the TMDB database yet, so streaming and trailer info is unavailable.")

# ==========================================
# TAB 4: WATCHLIST
# ==========================================
with tab_watchlist:
    if not st.session_state.watchlist:
        st.info("Nothing saved yet. Hit the + icon anywhere.")
    else:
        col_w1, col_w2 = st.columns([4, 1])
        with col_w2:
            if st.button("🗑️ Clear All", width='stretch'):
                st.session_state.watchlist = []
                save_watchlist_to_browser()
                st.rerun()

        for i, item in enumerate(st.session_state.watchlist):
            if i % 5 == 0: cols = st.columns(5)
            with cols[i % 5]:
                st.image(item['poster'], width='stretch')
                st.markdown(f"<div style='font-weight:600; font-size:0.95rem; margin-top:8px;'>{item['title']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='color:#ffd700; font-size:0.85rem; margin-bottom:8px;'>⭐ {item['rating']}</div>", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("", key=f"rm_{item['id']}_{i}", icon=":material/delete:", help="Remove"):
                        toggle_watchlist(item['id'], item['title'], item['poster'], item['rating'], item['type'])
                with c2:
                    st.button("", key=f"sim_w_{item['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(item['title'],))

# ==========================================
# 🚨 DIALOG TRIGGER
# ==========================================
if st.session_state.get("similar_target"):
    target = st.session_state.similar_target
    st.session_state.similar_target = None
    show_similar_dialog(target)