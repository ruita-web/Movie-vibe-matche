import streamlit as st
import os
import requests
import json
import random
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI
import extra_streamlit_components as stx
from supabase import create_client, Client
import uuid

# 1. Load the secret keys
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 2. Page Setup
st.set_page_config(page_title="Movie Vibe Matcher", page_icon="🍿", layout="wide")

# ==========================================
# 🚨 SUPABASE & COOKIE SETUP
# ==========================================
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

cookie_manager = stx.CookieManager(key="cookie_manager")

if "user_id" not in st.session_state:
    if "uid" in st.query_params:
        st.session_state.user_id = st.query_params["uid"]
    else:
        cookie_id = cookie_manager.get(cookie="movie_vibe_uid")
        if cookie_id:
            st.session_state.user_id = cookie_id
            st.query_params["uid"] = cookie_id
        else:
            new_id = str(uuid.uuid4())
            cookie_manager.set("movie_vibe_uid", new_id)
            st.query_params["uid"] = new_id
            st.session_state.user_id = new_id
            st.rerun()

user_id = st.session_state.user_id

# ==========================================
# 🚨 SESSION STATE INITIALIZATION
# ==========================================
if "watchlist" not in st.session_state: 
    try:
        res = supabase.table("watchlists").select("movie_data").eq("user_id", user_id).execute()
        st.session_state.watchlist = [item['movie_data'] for item in res.data]
    except:
        st.session_state.watchlist = []

if "media_type" not in st.session_state: st.session_state.media_type = "Both"
if "genres" not in st.session_state: st.session_state.genres = []
if "decades" not in st.session_state: st.session_state.decades = []
if "min_rating" not in st.session_state: st.session_state.min_rating = 6.0
if "num_recs" not in st.session_state: st.session_state.num_recs = 5
if "vibe" not in st.session_state: st.session_state.vibe = ""
if "run_search" not in st.session_state: st.session_state.run_search = False
if "is_surprise" not in st.session_state: st.session_state.is_surprise = False
if "similar_target" not in st.session_state: st.session_state.similar_target = None
if "current_candidates" not in st.session_state: st.session_state.current_candidates = []
if "current_recommendations" not in st.session_state: st.session_state.current_recommendations = []

def toggle_watchlist(media_id, title, poster, rating, p_type):
    is_saved = any(item['id'] == media_id for item in st.session_state.watchlist)
    if is_saved:
        try:
            supabase.table("watchlists").delete().eq("user_id", user_id).filter("movie_data->>id", "eq", str(media_id)).execute()
            st.session_state.watchlist = [m for m in st.session_state.watchlist if m['id'] != media_id]
            st.toast(f"Removed **{title}**")
            st.rerun()
        except Exception as e:
            st.error(f"Error removing: {e}")
    else:
        new_movie = {"id": media_id, "title": title, "poster": poster, "rating": rating, "type": p_type}
        try:
            supabase.table("watchlists").insert({"user_id": user_id, "movie_data": new_movie}).execute()
            st.session_state.watchlist.append(new_movie)
            st.toast(f"Added **{title}**")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving: {e}")

# ==========================================
# 🎨 CSS (2 COLUMNS & FLOATING MENU)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    .stApp { background-color: #0a0a0c !important; color: #fff; }
    
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    [data-testid="stBottom"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}

    .block-container { padding-top: 1.5rem !important; padding-bottom: 5rem !important; max-width: 95% !important; }

    div[data-testid="stRadio"] > div {
        flex-direction: row !important;
        gap: 20px !important;
        justify-content: center !important;
        border-bottom: 1px solid #222 !important;
        padding-bottom: 10px !important;
    }
    div[data-testid="stRadio"] label {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        color: #888 !important;
        cursor: pointer !important;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        color: #ff4b4b !important;
    }
    div[data-testid="stRadio"] label > div:first-child { display: none !important; }

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
    
    .main-btn .stButton > button {
        background: #ff4b4b !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        width: 100% !important;
        border: 1px solid #ff4b4b !important;
    }
    .main-btn .stButton > button:hover { background: #ff7676 !important; transform: none; }
    
    .secondary-btn .stButton > button {
        background: transparent !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        border: 1px solid #444 !important;
    }

    .tv-card { background: transparent; border: none; margin-bottom: 15px; }
    .tv-card img { border-radius: 8px; transition: transform 0.3s ease, box-shadow 0.3s ease; box-shadow: 0 4px 10px rgba(0,0,0,0.5); width: 100%; object-fit: cover; }
    .tv-card img:hover { transform: scale(1.05); box-shadow: 0 8px 20px rgba(255, 75, 75, 0.2); }
    
    .tv-title { 
        font-weight: 600; font-size: 0.95rem; margin-top: 8px; 
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; 
        overflow: hidden; text-overflow: ellipsis; min-height: 2.4rem; line-height: 1.2;
    }
    
    .movie-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .movie-card:hover { border-color: rgba(255, 75, 75, 0.4); }
    
    .stTextInput > div > div > input { background-color: #1a1a1a !important; color: white !important; border-radius: 8px !important; border: 1px solid #333 !important; padding: 12px 20px !important; }
    div[data-baseweb="select"] > div { background-color: #1a1a1a !important; border-radius: 8px !important; color: white !important; border: 1px solid #333 !important; }
    
    div[data-baseweb="popover"] { background-color: #1a1a1a !important; border: 1px solid #333 !important; }
    ul[data-baseweb="menu"] { background-color: #1a1a1a !important; }
    li[data-baseweb="menu-item"] { color: white !important; }
    li[data-baseweb="menu-item"]:hover { background-color: #333 !important; color: #ff4b4b !important; }
    
    .trailer-btn { display: inline-flex; align-items: center; justify-content: center; background: #ff4b4b; color: white !important; text-decoration: none !important; padding: 10px 15px; border-radius: 6px; font-weight: 600; font-size: 0.9rem; width: 100%; white-space: nowrap;}

    @media (max-width: 768px) {
        div[data-testid="stRadio"] { display: none !important; }

        div[data-testid="stHorizontalBlock"]:nth-of-type(1) {
            display: flex !important;
            flex-direction: column !important;
            gap: 10px !important;
        }
        div[data-testid="stHorizontalBlock"]:nth-of-type(1) > div {
            width: 100% !important;
            min-width: 100% !important;
        }
        h1 { font-size: 2.2rem !important; margin-bottom: 0 !important; }

        div[data-testid="stHorizontalBlock"]:not(:nth-of-type(1)) {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 15px !important;
            width: 100% !important;
        }
        
        div[data-testid="stHorizontalBlock"]:not(:nth-of-type(1)) > div[data-testid="column"] {
            width: calc(50% - 7.5px) !important;
            min-width: calc(50% - 7.5px) !important;
            flex: 0 0 calc(50% - 7.5px) !important;
            padding: 0 !important;
        }
        
        div[data-testid="column"] > div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            justify-content: space-between !important;
            gap: 4px !important;
            margin-top: 6px !important;
        }
        div[data-testid="column"] > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: 33.33% !important;
            min-width: 33.33% !important;
            flex: 1 !important;
            padding: 0 !important;
        }
        div[data-testid="column"] > div[data-testid="stHorizontalBlock"] .stButton > button {
            padding: 6px !important;
            font-size: 1.1rem !important;
            border: 1px solid #333 !important;
            border-radius: 8px !important;
            background: rgba(255,255,255,0.05) !important;
        }

        .movie-card > div {
            flex-direction: column !important;
            align-items: flex-start !important;
        }
        .movie-card img {
            width: 100% !important;
            max-width: 180px !important;
            margin-bottom: 15px !important;
            align-self: center !important;
        }

        div[data-testid="stPopover"] {
            position: fixed !important;
            bottom: 80px !important; 
            right: 20px !important;
            z-index: 999999 !important;
            width: 60px !important;
            height: 60px !important;
        }
        
        div[data-testid="stPopover"] > button {
            width: 60px !important;
            height: 60px !important;
            border-radius: 50% !important;
            background-color: #ff4b4b !important;
            color: white !important;
            font-size: 24px !important;
            font-weight: bold !important;
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.6) !important;
            padding: 0 !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            border: none !important;
        }
    }

    @media (min-width: 769px) {
        div[data-testid="stPopover"] { display: none !important; }
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

# ==========================================
# 🚨 NAVIGATION SYSTEM
# ==========================================
tabs_list = ["Trending", "Search", "Upcoming", "Actors", "Vibe Matcher", "Watchlist"]

if "tab" not in st.query_params:
    st.query_params["tab"] = "Trending"

current_tab = st.query_params["tab"]

def set_tab(tab_name):
    st.query_params["tab"] = tab_name
    st.rerun()

# 3. Header & Top Bar Layout
col_title, col_region = st.columns([3, 1])
with col_title:
    st.markdown("<h1 style='text-align: left; font-weight: 800; letter-spacing: -1px; margin-bottom: 0;'>Movie Vibe</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: left; color: #888; margin-bottom: 0;'>Find your next watch</p>", unsafe_allow_html=True)
with col_region:
    st.selectbox("Region", options=list(COUNTRIES.keys()), format_func=lambda x: f"🌍 {COUNTRIES[x]}", key="region", label_visibility="collapsed")

selected_tab = st.radio("Navigation", tabs_list, index=tabs_list.index(current_tab), horizontal=True, label_visibility="collapsed")

if selected_tab != current_tab:
    set_tab(selected_tab)

with st.popover("☰"):
    st.markdown("### Navigation")
    if st.button("🏠 Trending", use_container_width=True): set_tab("Trending")
    if st.button("🔍 Search", use_container_width=True): set_tab("Search")
    if st.button("🗓️ Upcoming", use_container_width=True): set_tab("Upcoming")
    if st.button("👤 Actors", use_container_width=True): set_tab("Actors")
    if st.button("✨ Vibe Matcher", use_container_width=True): set_tab("Vibe Matcher")
    if st.button("❤️ Watchlist", use_container_width=True): set_tab("Watchlist")

st.write("")

# 4. TMDB Data
GENRES = {"Action": 28, "Comedy": 35, "Horror": 27, "Sci-Fi": 878, "Drama": 18, "Thriller": 53, "Romance": 10749, "Animation": 16, "Mystery": 9648, "Fantasy": 14, "Adventure": 12, "Crime": 80}
DECADES = {"2020s": ("2020-01-01", "2029-12-31"), "2010s": ("2010-01-01", "2019-12-31"), "2000s": ("2000-01-01", "2009-12-31"), "90s": ("1990-01-01", "1999-12-31"), "80s": ("1980-01-01", "1989-12-31"), "70s": ("1970-01-01", "1979-12-31")}
SURPRISE_VIBES = ["mind-bending", "tearjerker", "funny but sad", "action-packed", "slow burn", "feel-good", "dark and gritty", "visually stunning", "twist ending", "nostalgic"]

def find_similar_callback(title):
    st.session_state.similar_target = title

# 5. API Functions
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
        creators = [crew['name'] for crew in data.get('crew', []) if crew.get('job') in ['Director', 'Creator', 'Executive Producer']]
        creator_str = creators[0] if creators else "Unknown"
        cast = [actor['name'] for actor in data.get('cast', [])[:3]]
        return creator_str, ", ".join(cast) if cast else "Unknown"
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

def fetch_full_details(media_id, media_type):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={TMDB_API_KEY}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

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
        return None 

# ==========================================
# 🚨 ACTOR SEARCH FUNCTIONS
# ==========================================
def get_actor_id(actor_name):
    url = f"https://api.themoviedb.org/3/search/person?api_key={TMDB_API_KEY}&query={actor_name}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("results"):
            return data["results"][0]
    except:
        pass
    return None

def get_actor_movies(actor_id):
    url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_people={actor_id}&sort_by=vote_average.desc&vote_count.gte=100"
    try:
        response = requests.get(url, timeout=10)
        return response.json().get("results", [])[:20]
    except:
        return []

# ==========================================
# 🚨 POPUP DIALOGS
# ==========================================
@st.dialog("Similar Movies", width="large")
def show_similar_dialog(target_title):
    col_title, col_slider, col_close = st.columns([2, 3, 1])
    with col_title:
        st.markdown(f"### Like **{target_title}**?")
    with col_slider:
        min_rating = st.slider("Min Rating", 0.0, 10.0, 5.0, 0.5, key=f"sim_rating_{target_title}")
    with col_close:
        st.write("")
        st.write("")
        if st.button("❌ Close", key="close_sim_modal", width='stretch'):
            st.session_state.similar_target = None
            st.rerun()
            
    st.write("---")
    
    with st.spinner("Finding matches..."):
        candidates = fetch_discover("Both", [], [], min_rating, target_title)
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
            else:
                st.warning("No recommendations found for that rating limit.")

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
        st.markdown(f"🎬 **Dir/Creator:** {director} | 🎭 **Cast:** {cast}")
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
            if st.button("", key=f"modal_sim_{m['id']}", icon=":material/auto_awesome:", help="Find Similar", width='stretch'):
                st.session_state.similar_target = title
                st.rerun()

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
# PAGE RENDERING
# ==========================================

if current_tab == "Trending":
    st.markdown("### Trending Movies")
    for i, m in enumerate(fetch_trending("movie")):
        if i % 5 == 0: cols = st.columns(5)
        with cols[i % 5]:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750"
            st.image(poster, width='stretch')
            st.markdown(f"<div class='tv-title'>{m.get('title')}</div>", unsafe_allow_html=True)
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
            st.markdown(f"<div class='tv-title'>{m.get('name')}</div>", unsafe_allow_html=True)
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

elif current_tab == "Search":
    st.markdown("### 🔍 Search")
    search_query = st.text_input("Search for a specific title...", placeholder="e.g., 'Spider-Man', 'The Office'")
    
    if search_query:
        with st.spinner("Searching..."):
            results = search_media(search_query)
            if not results:
                st.warning("No results found. Try checking the spelling.")
            else:
                for i, m in enumerate(results[:10]): 
                    if i % 5 == 0: cols = st.columns(5)
                    with cols[i % 5]:
                        st.markdown('<div class="tv-card">', unsafe_allow_html=True)
                        poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750"
                        st.image(poster, width='stretch')
                        
                        title = m.get('title') or m.get('name')
                        rating = f"{m.get('vote_average', 0):.1f}" if m.get('vote_average') else "N/A"
                        p_type = m.get('media_type')
                        
                        st.markdown(f"<div class='tv-title'>{title}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='color:#ffd700; font-size:0.85rem; margin-bottom:8px;'>⭐ {rating}</div>", unsafe_allow_html=True)
                        
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("", key=f"i_srch_{m['id']}_{i}", icon=":material/info:", help="Details"):
                                show_details(m, p_type)
                        with c2:
                            is_saved = any(item['id'] == m['id'] for item in st.session_state.watchlist)
                            if st.button("", key=f"s_srch_{m['id']}_{i}", icon=":material/check:" if is_saved else ":material/add:", help="Save"):
                                toggle_watchlist(m['id'], title, poster, rating, p_type)
                        with c3:
                            st.button("", key=f"sim_srch_{m['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(title,))
                        st.markdown('</div>', unsafe_allow_html=True)

elif current_tab == "Upcoming":
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
            st.markdown(f"<div class='tv-title'>{m.get('title')}</div>", unsafe_allow_html=True)
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
            st.markdown(f"<div class='tv-title'>{m.get('name')}</div>", unsafe_allow_html=True)
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

elif current_tab == "Actors":
    st.markdown("### 👤 Actor Search")
    actor_query = st.text_input("Search for an actor...", placeholder="e.g., 'Jackie Chan', 'Dwayne Johnson', 'Scarlett Johansson'")
    
    if actor_query:
        with st.spinner(f"Finding movies for {actor_query}..."):
            actor = get_actor_id(actor_query)
            if actor:
                st.markdown(f"#### Movies starring **{actor['name']}** (Sorted by Highest Rating)")
                movies = get_actor_movies(actor['id'])
                
                if not movies:
                    st.warning("No movies found for this actor.")
                else:
                    for i, m in enumerate(movies):
                        if i % 5 == 0: cols = st.columns(5)
                        with cols[i % 5]:
                            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
                            poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get('poster_path') else "https://via.placeholder.com/500x750"
                            st.image(poster, width='stretch')
                            
                            title = m.get('title') or m.get('name')
                            rating = f"{m.get('vote_average', 0):.1f}" if m.get('vote_average') else "N/A"
                            p_type = "movie"
                            
                            st.markdown(f"<div class='tv-title'>{title}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='color:#ffd700; font-size:0.85rem; margin-bottom:8px;'>⭐ {rating}</div>", unsafe_allow_html=True)
                            
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                if st.button("", key=f"i_act_{m['id']}_{i}", icon=":material/info:", help="Details"):
                                    show_details(m, p_type)
                            with c2:
                                is_saved = any(item['id'] == m['id'] for item in st.session_state.watchlist)
                                if st.button("", key=f"s_act_{m['id']}_{i}", icon=":material/check:" if is_saved else ":material/add:", help="Save"):
                                    toggle_watchlist(m['id'], title, poster, rating, p_type)
                            with c3:
                                st.button("", key=f"sim_act_{m['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(title,))
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error(f"Could not find an actor named **{actor_query}**. Try checking the spelling.")

elif current_tab == "Vibe Matcher":
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
                credits_html = f"<p style='color: #aaa; font-size: 0.95rem; margin-top: -5px; margin-bottom: 15px;'>🎬 <b>Dir/Creator:</b> {director} | 🎭 <b>Cast:</b> {cast}</p>"
                
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

elif current_tab == "Watchlist":
    if not st.session_state.watchlist:
        st.info("Nothing saved yet. Hit the + icon anywhere.")
    else:
        col_w1, col_w2 = st.columns([4, 1])
        with col_w2:
            if st.button("🗑️ Clear All", width='stretch'):
                for item in st.session_state.watchlist:
                    try:
                        supabase.table("watchlists").delete().eq("user_id", user_id).filter("movie_data->>id", "eq", str(item['id'])).execute()
                    except Exception as e:
                        pass
                st.session_state.watchlist = []
                st.rerun()

        for i, item in enumerate(st.session_state.watchlist):
            if i % 5 == 0: cols = st.columns(5)
            with cols[i % 5]:
                st.image(item['poster'], width='stretch')
                st.markdown(f"<div class='tv-title'>{item['title']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='color:#ffd700; font-size:0.85rem; margin-bottom:8px;'>⭐ {item['rating']}</div>", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("", key=f"rm_{item['id']}_{i}", icon=":material/delete:", help="Remove"):
                        toggle_watchlist(item['id'], item['title'], item['poster'], item['rating'], item['type'])
                with c2:
                    st.button("", key=f"sim_w_{item['id']}_{i}", icon=":material/auto_awesome:", help="Find Similar", on_click=find_similar_callback, args=(item['title'],))
                with c3:
                    if st.button("", key=f"info_w_{item['id']}_{i}", icon=":material/info:", help="Details"):
                        with st.spinner("Loading details..."):
                            full_data = fetch_full_details(item['id'], item['type'])
                            if full_data:
                                show_details(full_data, item['type'])
                            else:
                                st.error("Could not load details.")

# ==========================================
# 🚨 DIALOG TRIGGER
# ==========================================
if st.session_state.get("similar_target"):
    target = st.session_state.similar_target
    show_similar_dialog(target)

# ==========================================
# 🚨 DEBUG INFO
# ==========================================
with st.sidebar:
    st.write("### 🛠️ Debug Info")
    st.write(f"**User ID:** `{user_id}`")
    st.write(f"**Watchlist Count:** {len(st.session_state.watchlist)}")
    if st.button("Test Supabase Connection"):
        try:
            res = supabase.table("watchlists").select("*").limit(1).execute()
            st.success("Supabase connected successfully!")
        except Exception as e:
            st.error(f"Supabase Error: {e}")