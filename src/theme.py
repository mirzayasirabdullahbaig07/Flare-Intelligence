"""
FLARE Intelligence - design system v3 (light theme, built for st.navigation apps)

Put this file at  src/theme.py  and use it from app.py and every page:

    app.py:
        from src.theme import apply_theme, sidebar
        apply_theme()
        nav = st.navigation(pages)          # position="hidden" is used automatically when supported
        sidebar(pages, nav)
        nav.run()

    any page:
        from src.theme import header, stat_cards, card, panel, panel_title, section_title, \
            insight, timeline, table, plot, module_grid, icon

Icon names: home flask chart scale bot trophy rocket database flame activity star bulb shield
            book users sparkles clock search download upload layers zap globe trending arrow
Requires Streamlit >= 1.42 (pip install -U streamlit plotly pandas).
"""
import base64
import html as _html
import re
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import streamlit as st

# ----------------------------------------------------------------------------
# Icons
# ----------------------------------------------------------------------------
_ICONS = {
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "flask": '<path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    "bot": '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "bulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "trending": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
}


def icon(name: str, size: int = 22, stroke: float = 2) -> str:
    """Inline SVG icon (inherits text color)."""
    body = _ICONS.get(name, _ICONS["sparkles"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
            f'fill="none" stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round" class="ic">{body}</svg>')


# page title keyword -> (material icon for sidebar, svg icon for cards)
_PAGE_ICONS = [
    ("overview", ":material/home:", "home"),
    ("explorer", ":material/science:", "flask"),
    ("analytics", ":material/bar_chart:", "chart"),
    ("comparison", ":material/balance:", "scale"),
    ("assistant", ":material/smart_toy:", "bot"),
    ("ranking", ":material/emoji_events:", "trophy"),
    ("mission", ":material/rocket_launch:", "rocket"),
    ("management", ":material/database:", "database"),
    ("data", ":material/database:", "database"),
]


def _page_icons(title: str):
    t = (title or "").lower()
    for key, mat, svg in _PAGE_ICONS:
        if key in t:
            return mat, svg
    return ":material/article:", "layers"


def _esc(x) -> str:
    return _html.escape(str(x), quote=True)


# ----------------------------------------------------------------------------
# CSS (light theme)
# ----------------------------------------------------------------------------
ROOT = """
--bg:#F5F6FB; --surface:#FFFFFF; --sidebar:#FFFFFF; --text:#12172B;
--muted:#6B7280; --border:#E8EAF2; --accent:#F97316; --accent-soft:#FFEDD5;
--shadow:0 6px 24px rgba(17,24,39,.06); --input:#F3F4F9; --row:#FAFAFD;
"""

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

@property --num { syntax:'<integer>'; initial-value:0; inherits:false; }
@keyframes fadeUp { from{opacity:0; transform:translateY(18px)} to{opacity:1; transform:translateY(0)} }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
@keyframes slideIn { from{opacity:0; transform:translateX(-16px)} to{opacity:1; transform:translateX(0)} }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
@keyframes drift { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(-50px,30px) scale(1.18)} }
@keyframes shimmer { to{background-position:200% center} }
@keyframes twinkle { 0%,100%{opacity:.25} 50%{opacity:.95} }
@keyframes sweep { from{left:-60%} to{left:140%} }
@keyframes countup { from{--num:0} }
@keyframes glow { 0%,100%{filter:drop-shadow(0 4px 10px rgba(249,115,22,.35))} 50%{filter:drop-shadow(0 6px 18px rgba(249,115,22,.7))} }

html, body, [class*="css"], .stApp { font-family:'Inter',sans-serif; }
.stApp { background:var(--bg); color:var(--text); }
header[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer { visibility:hidden; }
[data-testid="stAppDeployButton"], .stDeployButton { display:none !important; }
.block-container { padding-top:1.4rem; padding-bottom:3rem; max-width:1400px; animation:fadeIn .45s ease; }
h1,h2,h3,h4,h5,h6,p,label,li { color:var(--text); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:var(--muted); }
.ic { display:block; }
[data-baseweb="tab-highlight"] { background-color:var(--accent) !important; }
[data-testid="stHeaderActionElements"], .hero a[href^="#"] { display:none !important; }  /* heading anchor icons */
.card a, .ftable-wrap a { color:var(--accent); font-weight:600; text-decoration:none; }
.card a:hover { text-decoration:underline; }

/* equal-height cards inside st.columns */
[data-testid="stColumn"] > div, [data-testid="stColumn"] [data-testid="stVerticalBlock"] { height:100%; }
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .card),
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .card) > [data-testid="stMarkdown"],
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .card) [data-testid="stMarkdownContainer"],
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .stat),
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .stat) > [data-testid="stMarkdown"],
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .stat) [data-testid="stMarkdownContainer"] { height:100%; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] { background:var(--sidebar); border-right:1px solid var(--border); }
[data-testid="stSidebarNav"] { display:none; }
[data-testid="stSidebar"] .block-container { padding-top:1rem; }
[data-testid="stSidebarCollapseButton"] *, [data-testid="stExpandSidebarButton"] * { color:var(--text) !important; }
.brand { text-align:center; padding:.4rem 0 1rem; border-bottom:1px solid var(--border); margin-bottom:1rem; animation:fadeUp .6s ease backwards; }
.brand .logo { display:flex; justify-content:center; color:#F97316; animation:float 3.2s ease-in-out infinite, glow 3.2s ease-in-out infinite; }
.brand .name { font-weight:800; font-size:1.35rem; letter-spacing:-.02em; margin-top:.35rem; color:var(--text); }
.brand .tag { color:var(--muted); font-size:.78rem; margin-top:.25rem; line-height:1.35; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
  border-radius:12px; padding:.55rem .8rem; margin-bottom:3px; transition:all .2s ease; animation:slideIn .5s ease backwards; background:transparent; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p,
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] span { font-weight:500; font-size:.92rem; color:var(--text) !important; transition:color .2s ease; }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover { background:var(--accent-soft) !important; transform:translateX(4px); }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover p,
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover span { color:var(--accent) !important; }
/* the current page is rendered as a disabled link -> style it as active */
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][disabled] {
  opacity:1 !important; pointer-events:none; cursor:default; background:var(--accent-soft) !important; box-shadow:inset 3px 0 0 var(--accent); }
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][disabled] p,
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][disabled] span { color:var(--accent) !important; font-weight:700; opacity:1 !important; }
.side-foot { margin-top:1.2rem; padding:.9rem; border:1px solid var(--border); border-radius:14px;
  text-align:center; font-size:.78rem; color:var(--muted); background:var(--bg); transition:all .25s ease; }
.side-foot:hover { transform:translateY(-3px); border-color:var(--accent); }
.side-foot .ic { margin:0 auto .3rem; color:var(--accent); }
.side-foot img { height:60px; max-width:100%; object-fit:contain; display:block; margin:0 auto .5rem; }
.brand .logo-img { height:72px; max-width:100%; object-fit:contain; display:block; margin:0 auto; animation:float 3.2s ease-in-out infinite; }
.side-foot b { color:var(--text); }

/* ---------- Hero / page header ---------- */
.hero { position:relative; overflow:hidden; border-radius:22px; padding:2.3rem 2.5rem; margin-bottom:1.3rem;
  color:#fff; box-shadow:var(--shadow); animation:fadeUp .7s ease backwards;
  background:linear-gradient(120deg,#070B1A 0%,#101B3D 55%,#1B2B5E 100%); background-size:cover; background-position:right center; }
.hero.compact { padding:1.5rem 2.2rem; border-radius:20px; }
.hero::after { content:""; position:absolute; right:-90px; top:-90px; width:400px; height:400px; border-radius:50%;
  background:radial-gradient(circle,rgba(249,115,22,.55),transparent 65%); animation:drift 9s ease-in-out infinite; pointer-events:none; }
.hero .stars { position:absolute; inset:0; pointer-events:none; animation:twinkle 4s ease-in-out infinite;
  background-image:radial-gradient(1.5px 1.5px at 18% 30%,#fff,transparent),radial-gradient(1px 1px at 68% 22%,#fff,transparent),
  radial-gradient(1.5px 1.5px at 84% 62%,#fff,transparent),radial-gradient(1px 1px at 42% 82%,#fff,transparent),
  radial-gradient(1px 1px at 56% 46%,#fff,transparent),radial-gradient(1.5px 1.5px at 92% 18%,#fff,transparent); }
.hero .bar { position:absolute; left:0; top:1.6rem; bottom:1.6rem; width:4px; background:linear-gradient(#F97316,#FBBF24); border-radius:4px; }
.hero h1, .hero h1 span { color:#fff !important; }
.hero h1 { font-size:2.05rem; line-height:1.2; font-weight:800; margin:0 0 .7rem; max-width:680px; letter-spacing:-.02em; padding:0; }
.hero.compact h1 { font-size:1.65rem; margin:0 0 .35rem; }
.hero h1 em { font-style:normal; display:block; color:#FB923C;
  background:linear-gradient(90deg,#FB923C,#FDE68A,#F97316,#FB923C); background-size:200% auto;
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; animation:shimmer 4s linear infinite; }
.hero p { color:#C9D2EE !important; font-size:.98rem; max-width:540px; margin:0; }
.hero > * { position:relative; z-index:1; }

/* ---------- Cards ---------- */
.card, [class*="st-key-card_"] { position:relative; overflow:hidden; background:var(--surface); border:1px solid var(--border); border-radius:18px;
  padding:1.15rem 1.3rem; box-shadow:var(--shadow); animation:fadeUp .6s ease backwards; box-sizing:border-box;
  transition:transform .28s ease, box-shadow .28s ease, border-color .28s ease; }
.card { height:100%; }
.card::before, [class*="st-key-card_"]::before { content:""; position:absolute; left:0; top:0; height:3px; width:0; background:linear-gradient(90deg,#F97316,#FBBF24); transition:width .45s ease; }
.card:hover, [class*="st-key-card_"]:hover { transform:translateY(-4px); border-color:rgba(249,115,22,.45); box-shadow:0 16px 36px rgba(249,115,22,.14); }
.card:hover::before, [class*="st-key-card_"]:hover::before { width:100%; }
.ch { margin:0 0 .85rem; font-size:1.02rem; font-weight:700; display:flex; align-items:center; gap:.65rem; color:var(--text); }
.ch .hico { width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
  background:var(--cs); color:var(--c); transition:transform .3s ease; flex-shrink:0; }
.card:hover .ch .hico, [class*="st-key-card_"]:hover .ch .hico { transform:rotate(-8deg) scale(1.1); }
.card .desc { color:var(--muted); font-size:.88rem; line-height:1.5; margin:0; }
.bignum { font-size:2.1rem; font-weight:800; letter-spacing:-.02em; line-height:1.1; }

.t-orange { --c:#F97316; --cs:rgba(249,115,22,.14); } .t-blue { --c:#3B82F6; --cs:rgba(59,130,246,.14); }
.t-purple { --c:#8B5CF6; --cs:rgba(139,92,246,.14); } .t-green { --c:#10B981; --cs:rgba(16,185,129,.14); }
.t-red { --c:#EF4444; --cs:rgba(239,68,68,.14); }

.stat { position:relative; overflow:hidden; display:flex; align-items:center; gap:.85rem; border-radius:18px; padding:1.1rem 1rem;
  border:1px solid var(--border); box-shadow:var(--shadow); background:var(--surface); animation:fadeUp .65s ease backwards;
  min-height:142px; height:100%; box-sizing:border-box;
  transition:transform .28s ease, box-shadow .28s ease, border-color .28s ease; }
.stat::after { content:""; position:absolute; right:-30px; bottom:-40px; width:150px; height:110px; border-radius:50%;
  background:radial-gradient(circle,var(--cs),transparent 70%); transition:transform .5s ease; }
.stat:hover { transform:translateY(-5px); border-color:var(--c); box-shadow:0 16px 34px var(--cs); }
.stat:hover::after { transform:scale(1.5); }
.stat .ico { width:50px; height:50px; border-radius:15px; display:flex; align-items:center; justify-content:center;
  background:var(--cs); color:var(--c); flex-shrink:0; transition:transform .3s ease; z-index:1; }
.stat .ico .ic { animation:float 3s ease-in-out infinite; }
.stat:hover .ico { transform:rotate(-8deg) scale(1.1); }
.stat .txt { z-index:1; min-width:0; }
.stat .val { font-size:1.75rem; font-weight:800; line-height:1.1; letter-spacing:-.02em; }
.stat .val.small { font-size:1.15rem; }
.stat .lbl { font-weight:600; font-size:.9rem; }
.stat .sub { color:var(--muted); font-size:.74rem; }
.count { --num:var(--to); counter-reset:num var(--num); animation:countup 1.6s cubic-bezier(.2,.7,.2,1) backwards; }
.count::after { content:counter(num) var(--suf); }

.section-title { font-size:1.15rem; font-weight:700; margin:1.5rem 0 .75rem; display:flex; align-items:center; gap:.6rem; animation:fadeUp .5s ease backwards; }
.section-title .sico { width:30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center;
  background:var(--accent-soft); color:var(--accent); }
.section-title small { color:var(--muted); font-weight:500; font-size:.82rem; }

.insight { display:flex; gap:.9rem; align-items:center; padding:.6rem .4rem; border-radius:12px; animation:slideIn .55s ease backwards; transition:background .2s ease, transform .2s ease; }
.insight:hover { background:var(--cs); transform:translateX(4px); }
.insight .dot { width:42px; height:42px; border-radius:50%; background:var(--cs); color:var(--c);
  display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.insight div:last-child { font-size:.9rem; line-height:1.45; }

.tl { position:relative; padding-left:1.7rem; }
.tl::before { content:""; position:absolute; left:6px; top:6px; bottom:6px; width:2px; background:linear-gradient(var(--accent),transparent); }
.tl-item { position:relative; padding:.35rem 0 .9rem; animation:slideIn .55s ease backwards; }
.tl-item::before { content:""; position:absolute; left:-1.7rem; top:.5rem; width:14px; height:14px; border-radius:50%;
  background:var(--accent); border:3px solid var(--surface); box-shadow:0 0 0 2px var(--accent); }
.tl-time { font-size:.78rem; color:var(--muted); }
.tl-text { font-size:.92rem; font-weight:500; }
.empty { color:var(--muted); font-size:.9rem; padding:.4rem 0; }

.pill { display:inline-block; padding:.28rem .75rem; border-radius:999px; background:var(--accent-soft);
  color:var(--accent); font-weight:700; font-size:.75rem; margin:0 .3rem .3rem 0; }

.ftable-wrap { border:1px solid var(--border); border-radius:14px; overflow:auto; background:var(--surface); box-shadow:var(--shadow); animation:fadeUp .6s ease backwards; }
table.ftable { width:100%; border-collapse:collapse; font-size:.88rem; }
table.ftable th { position:sticky; top:0; background:var(--accent-soft); color:var(--accent); text-align:left; padding:.7rem .9rem;
  font-weight:700; font-size:.78rem; text-transform:uppercase; letter-spacing:.04em; }
table.ftable td { padding:.65rem .9rem; border-top:1px solid var(--border); color:var(--text); }
table.ftable tbody tr:nth-child(even) { background:var(--row); }
table.ftable tbody tr { transition:background .15s ease; }
table.ftable tbody tr:hover { background:var(--accent-soft); }

/* ---------- Native widgets ---------- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  position:relative; overflow:hidden; background:linear-gradient(135deg,#F97316,#FB923C); color:#fff; border:0; border-radius:12px;
  padding:.55rem 1.25rem; font-weight:600; box-shadow:0 6px 16px rgba(249,115,22,.3); transition:all .2s ease; }
.stButton > button::after, .stDownloadButton > button::after, .stFormSubmitButton > button::after { content:""; position:absolute; top:0; left:-60%; width:40%; height:100%;
  background:linear-gradient(120deg,transparent,rgba(255,255,255,.4),transparent); transform:skewX(-20deg); }
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover { transform:translateY(-2px); color:#fff; box-shadow:0 12px 24px rgba(249,115,22,.4); }
.stButton > button:hover::after, .stDownloadButton > button:hover::after, .stFormSubmitButton > button:hover::after { animation:sweep .7s ease; }
.stButton > button:active { transform:translateY(0) scale(.98); }
.stButton > button p, .stDownloadButton > button p, .stFormSubmitButton > button p { color:#fff !important; }
/* long button labels wrap instead of being cut with an ellipsis */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { height:auto; min-height:2.6rem; }
.stButton > button p, .stDownloadButton > button p, .stFormSubmitButton > button p { white-space:normal !important; overflow:visible !important; text-overflow:clip !important; line-height:1.3; }
[class*="st-key-card_"] [data-testid="stColumn"] .stButton > button { min-height:4.4rem; }
div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input {
  background:var(--input) !important; border:1px solid var(--border) !important; border-radius:12px !important; color:var(--text) !important; transition:border-color .2s ease, box-shadow .2s ease; }
div[data-baseweb="select"] > div:focus-within, .stTextInput input:focus, .stTextArea textarea:focus { border-color:var(--accent) !important; box-shadow:0 0 0 3px var(--accent-soft) !important; }
li[role="option"]:hover, li[aria-selected="true"] { background:var(--accent-soft) !important; }
[data-testid="stFileUploaderDropzone"] { background:var(--input); border:1.5px dashed var(--border); border-radius:14px; transition:all .2s ease; }
[data-testid="stFileUploaderDropzone"]:hover { border-color:var(--accent); background:var(--accent-soft); }
[data-testid="stMetric"] { background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:.9rem 1rem; box-shadow:var(--shadow);
  animation:fadeUp .6s ease backwards; transition:transform .25s ease, border-color .25s ease; }
[data-testid="stMetric"]:hover { transform:translateY(-3px); border-color:var(--accent); }
[data-testid="stMetricValue"] { font-weight:800; }
[data-testid="stMetricLabel"] p { color:var(--muted); }
.stTabs [data-baseweb="tab-list"] { gap:.4rem; border-bottom:1px solid var(--border); }
.stTabs [data-baseweb="tab"] { border-radius:10px 10px 0 0; padding:.5rem 1rem; font-weight:600; transition:background .2s ease; }
.stTabs [data-baseweb="tab"]:hover { background:var(--accent-soft); }
.stTabs [aria-selected="true"] { color:var(--accent); }
[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:14px; overflow:hidden; }
[data-testid="stExpander"] { background:var(--surface); border:1px solid var(--border); border-radius:14px; transition:border-color .2s ease; }
[data-testid="stExpander"]:hover { border-color:var(--accent); }
[data-testid="stChatMessage"] { background:var(--surface); border:1px solid var(--border); border-radius:16px; animation:fadeUp .4s ease backwards; }
[data-testid="stPlotlyChart"], [data-testid="stImage"] { animation:fadeUp .7s ease backwards; }
hr { border-color:var(--border); }

@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation:none !important; transition:none !important; } }
"""


def _h(s: str) -> str:
    """Collapse multi-line html so Streamlit's markdown parser never treats it as a code block."""
    return "".join(line.strip() for line in s.splitlines())


def _require_boot():
    """If a page was opened directly (cold server / refresh on a sub-page) Streamlit can skip app.py,
    which would leave the page unstyled. Detect that and bounce through app.py once."""
    if not st.session_state.get("_flare_boot"):
        st.switch_page("app.py")
        st.stop()


def apply_theme():
    """Inject the stylesheet. Call once in app.py (after st.set_page_config)."""
    st.session_state["_flare_boot"] = True
    st.markdown(_h(f"<style>:root{{{ROOT}}}{BASE_CSS}</style>"), unsafe_allow_html=True)


@lru_cache(maxsize=8)
def _logo_tag(stem: str, css_class: str = "") -> str:
    """<img> for assets/<stem>.png|jpg|jpeg|webp|svg (project root), or '' if the file is not there."""
    root = Path(__file__).resolve().parents[1] / "assets"
    mimes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
             ".webp": "image/webp", ".svg": "image/svg+xml"}
    for ext, mime in mimes.items():
        f = root / f"{stem}{ext}"
        if f.exists():
            data = base64.b64encode(f.read_bytes()).decode()
            return f'<img class="{css_class}" src="data:{mime};base64,{data}" alt="{stem}">'
    return ""


def sidebar(pages, current=None):
    """Branded sidebar. pages = list of st.Page, current = object returned by st.navigation(pages).
    Logos: put assets/flare_logo.png and assets/nasa_logo.png in the project root (optional)."""
    cur = getattr(current, "url_path", None)
    flare_logo = _logo_tag("flare_logo", "logo-img") or f'<div class="logo">{icon("flame", 46, 1.8)}</div>'
    nasa_logo = _logo_tag("nasa_logo") or icon("globe", 26, 1.6)
    with st.sidebar:
        st.markdown(_h(f"""
            <div class="brand">{flare_logo}
            <div class="name">FLARE Intelligence</div>
            <div class="tag">AI-Powered Microgravity<br>Combustion Analysis</div></div>"""),
                    unsafe_allow_html=True)
        for p in pages:
            mat, _ = _page_icons(p.title)
            st.page_link(p, label=p.title, icon=mat, disabled=(cur is not None and p.url_path == cur))
        st.markdown(_h(f"""
            <div class="side-foot">{nasa_logo}<b>NASA Space Apps<br>Challenge 2026</b><br>
            <span>Team Techbees</span></div>"""), unsafe_allow_html=True)


def navigation(pages):
    """st.navigation with the built-in menu hidden (our sidebar() draws it). Works on old and new Streamlit."""
    try:
        return st.navigation(pages, position="hidden")
    except TypeError:
        return st.navigation(pages)


# ----------------------------------------------------------------------------
# Components
# ----------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _img_css(path: str) -> str:
    try:
        p = Path(path)
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        data = base64.b64encode(p.read_bytes()).decode()
        return ("background-image:linear-gradient(90deg,rgba(7,11,26,1) 34%,rgba(7,11,26,.7) 52%,rgba(7,11,26,0) 82%),"
                f"url('data:{mime};base64,{data}');"
                "background-color:#070B1A;background-repeat:no-repeat;"
                "background-size:100% 100%,auto 118%;background-position:0 0,right top;")
    except Exception:
        return ""


def hero(title: str, highlight: str = "", subtitle: str = "", image: str | None = None):
    """Big animated hero banner. image = optional local file path, e.g. 'assets/astronaut.png'."""
    _require_boot()
    hl = f"<em>{highlight}</em>" if highlight else ""
    assets = Path(__file__).resolve().parents[1] / "assets"
    found = None
    if image:  # a path given by the page (absolute, or relative to the project folder)
        p = Path(image)
        p = p if p.is_absolute() else Path(__file__).resolve().parents[1] / p
        found = str(p) if p.exists() else None
    if not found:  # fall back to the default banner picture
        found = next((str(assets / n) for n in ("hero_bg.jpg", "hero_bg.png", "astronaut.png", "astronaut.jpg")
                      if (assets / n).exists()), None)
    image = found
    style = _img_css(image) if image else ""
    st.markdown(_h(f"""
        <div class="hero" style="{style}"><div class="stars"></div><div class="bar"></div>
        <h1>{title} {hl}</h1><p>{subtitle}</p></div>"""), unsafe_allow_html=True)


def header(title: str, subtitle: str = ""):
    """Compact page banner for inner pages (same signature idea as the old src.ui.header)."""
    _require_boot()
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(_h(f"""
        <div class="hero compact"><div class="stars"></div><div class="bar"></div>
        <h1>{title}</h1>{sub}</div>"""), unsafe_allow_html=True)


def _count(val) -> str:
    m = re.fullmatch(r"\s*(\d+)(\D*)\s*", str(val))
    if not m:
        return f'<span class="small">{_esc(val)}</span>'
    suf = m.group(2).replace("'", "").replace('"', "")
    return f'<span class="count" style="--to:{m.group(1)};--suf:\'{suf}\'" aria-label="{_esc(val)}"></span>'


def stat_cards(items):
    """items = [(icon_name, value, label, sublabel, tint)]  tint: orange|blue|purple|green|red
    Whole numbers (3, '12+') count up automatically."""
    cols = st.columns(len(items))
    for i, (col, (ico, val, lbl, sub, tint)) in enumerate(zip(cols, items)):
        col.markdown(_h(f"""
            <div class="stat t-{tint}" style="animation-delay:{i * 0.09}s">
            <div class="ico">{icon(ico, 28, 1.8)}</div>
            <div class="txt"><div class="val">{_count(val)}</div><div class="lbl">{_esc(lbl)}</div>
            <div class="sub">{_esc(sub)}</div></div></div>"""), unsafe_allow_html=True)


def card(title: str, body_html: str = "", icon_name: str = "", tint: str = "orange",
         min_height: int = 0, delay: float = 0.0):
    """Animated content card. body_html is raw html (use _esc / timeline / insight for text)."""
    ico = f'<span class="hico">{icon(icon_name, 18, 2)}</span>' if icon_name else ""
    st.markdown(_h(f"""
        <div class="card t-{tint}" style="min-height:{min_height}px;animation-delay:{delay}s">
        <div class="ch">{ico}<span>{title}</span></div>{body_html}</div>"""), unsafe_allow_html=True)


@contextmanager
def panel(key: str):
    """Card-styled container for native widgets/charts:  with panel('tests'): panel_title(...); plot(fig)"""
    try:
        c = st.container(key=f"card_{key}")
    except TypeError:  # very old Streamlit
        c = st.container(border=True)
    with c:
        yield


def panel_title(text: str, icon_name: str = "", tint: str = "orange"):
    ico = f'<span class="hico">{icon(icon_name, 18, 2)}</span>' if icon_name else ""
    st.markdown(_h(f'<div class="ch t-{tint}">{ico}<span>{text}</span></div>'), unsafe_allow_html=True)


def section_title(text: str, sub: str = "", icon_name: str = ""):
    s = f"<small>{sub}</small>" if sub else ""
    ico = f'<span class="sico">{icon(icon_name, 17, 2)}</span>' if icon_name else ""
    st.markdown(_h(f'<div class="section-title">{ico}{text} {s}</div>'), unsafe_allow_html=True)


def insight(icon_name: str, text: str, tint: str = "orange", i: int = 0) -> str:
    """Returns html row; join several and pass into card(body_html=...)."""
    return _h(f'<div class="insight t-{tint}" style="animation-delay:{i * 0.1}s">'
              f'<div class="dot">{icon(icon_name, 20, 1.9)}</div><div>{text}</div></div>')


def timeline(items) -> str:
    """items = [(time_text, text), ...] -> html (text is escaped)."""
    rows = "".join(
        f'<div class="tl-item" style="animation-delay:{i * 0.12}s"><div class="tl-time">{_esc(t)}</div>'
        f'<div class="tl-text">{_esc(x)}</div></div>' for i, (t, x) in enumerate(items))
    return _h(f'<div class="tl">{rows}</div>')


def badge(text: str) -> str:
    return f'<span class="pill">{_esc(text)}</span>'


def table(df, max_height: int = 420):
    """Styled HTML table (use instead of st.dataframe when you want the exact brand look)."""
    html = df.to_html(index=False, border=0, classes="ftable", escape=True)
    st.markdown(_h(f'<div class="ftable-wrap" style="max-height:{max_height}px">{html}</div>'),
                unsafe_allow_html=True)


def module_grid(modules, columns: int = 3):
    """modules = [(page_or_path, title, description)] -> clickable cards."""
    tints = ["orange", "blue", "purple", "green"]
    for start in range(0, len(modules), columns):
        row = modules[start:start + columns]
        cols = st.columns(columns)
        for j, (target, title, desc) in enumerate(row):
            _, svg = _page_icons(title)
            with cols[j]:
                card(_esc(title), f'<p class="desc">{_esc(desc)}</p>', svg, tints[(start + j) % 4],
                     min_height=125, delay=(start + j) * 0.06)
                try:
                    st.page_link(target, label="Open module", icon=":material/arrow_forward:")
                except Exception:
                    pass


def style_fig(fig, height: int = 380):
    """Brand look for any Plotly figure."""
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", template="plotly_white",
        font=dict(family="Inter", color="#12172B"), margin=dict(l=48, r=16, t=40, b=48),
        colorway=["#F97316", "#3B82F6", "#8B5CF6", "#10B981", "#EF4444", "#EAB308"],
        legend=dict(orientation="h", y=1.12, x=0),
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family="Inter", color="#12172B")),
    )
    fig.update_xaxes(gridcolor="#E8EAF2", zeroline=False, linecolor="#E8EAF2", automargin=True)
    fig.update_yaxes(gridcolor="#E8EAF2", zeroline=False, linecolor="#E8EAF2", automargin=True)
    return fig


def plot(fig, height: int = 380, **kwargs):
    """Style + render a Plotly figure in one call."""
    fig = style_fig(fig, height)
    try:
        st.plotly_chart(fig, theme=None, width="stretch", **kwargs)
    except TypeError:  # older Streamlit
        st.plotly_chart(fig, theme=None, use_container_width=True, **kwargs)