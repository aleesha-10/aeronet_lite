from __future__ import annotations

import streamlit as st

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
  @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
  @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

  :root {
    /* Palette A */
    --puce-red: #6C3134;
    --light-red: #FBC8CC;
    --charm-pink: #E092A7;
    --quin-magenta: #8C3352;
    --eggplant: #623A4B;

    /* Palette B */
    --english-violet: #593E58;
    --mountbatten-pink: #A17F98;
    --ruddy-pink: #E9819A;
    --deep-taupe: #7D5265;
    --moonstone: #399DB5;

    /* Palette C */
    --metallic-pink: #EDABBE;
    --blush: #DE5C8F;
    --boysenberry: #872D72;
    --american-purple: #411E57;
    --royal-purple: #7C4EBB;

    /* Map to app tokens (use ONLY palette colors) */
    --veranda-blue: var(--moonstone);
    --sky-cloud: var(--mountbatten-pink);
    --lychee: var(--light-red);
    --melon: var(--metallic-pink);
    --cupid-pink: var(--ruddy-pink);

    --eerie-black: var(--american-purple);
    --deep-space: var(--royal-purple);
    --cadet-grey: var(--mountbatten-pink);
    --pewter-blue: var(--deep-taupe);
    --brink-pink: var(--blush);

    --purple-taupe: var(--american-purple);
    --english-red: var(--quin-magenta);
    --peach-orange: var(--metallic-pink);

    /* App background */
    --app-bg: #EBE8D6; /* White Coffee */
    /* DataFrame chrome (match parchment; avoid stark white / hot pink wash) */
    --df-header-bg: #ded8cc;
    --df-header-text: #50314b;
    --df-index-bg: #e6e2d6;
    --df-body-wash: rgba(235, 232, 214, 0.45);
  }

  /* Main background */
  html, body, [data-testid="stAppViewContainer"] { background: var(--app-bg); }

  /* Use more width; reduce left/right empty space */
  .block-container {
    max-width: 1400px;
    padding-left: 1.8rem;
    padding-right: 1.8rem;
  }
  html, body, [data-testid="stAppViewContainer"] * {
    font-family: "Space Grotesk", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  }
  /* Keep typography consistent everywhere (including code blocks) */
  code, pre, kbd, samp, textarea {
    font-family: "Space Grotesk", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
  }
  /* Streamlit icons: prevent them rendering as plain text */
  .material-icons,
  .material-symbols-outlined,
  .material-symbols-rounded,
  .material-symbols-sharp {
    font-family: "Material Icons", "Material Symbols Outlined", sans-serif !important;
    font-weight: normal !important;
    font-style: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    display: inline-block !important;
    white-space: nowrap !important;
    word-wrap: normal !important;
    direction: ltr !important;
    -webkit-font-smoothing: antialiased !important;
  }
  /* Some Streamlit versions use BaseWeb icon spans */
  span[role="img"][aria-label][class*="material"] {
    font-family: "Material Icons", "Material Symbols Outlined", sans-serif !important;
  }

  /*
   * App chrome (header/toolbar): Streamlit emits Material ligature names in plain spans;
   * global Space Grotesk wins otherwise → leaked text like "double_arrow_right" / "keyboard_double…".
   */
  header[data-testid="stHeader"] button span,
  [data-testid="stHeader"] button span,
  [data-testid="stToolbar"] button span,
  [data-testid="stToolbarActions"] button span,
  [data-testid="stAppToolbar"] button span,
  [data-testid="collapsedControl"] button span {
    font-family: "Material Symbols Outlined", "Material Icons", sans-serif !important;
    font-variation-settings: "FILL" 0, "wght" 400, "GRAD" 0, "opsz" 24 !important;
    font-weight: normal !important;
    font-style: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    white-space: nowrap !important;
    -webkit-font-smoothing: antialiased !important;
  }

  /* Default text color for readability (MAIN area only) */
  [data-testid="stMain"] {
    color: var(--american-purple);
  }
  [data-testid="stMain"] p,
  [data-testid="stMain"] li,
  [data-testid="stMain"] span,
  [data-testid="stMain"] div {
    color: var(--american-purple);
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: var(--american-purple);
  }
  [data-testid="stSidebar"] * {
    color: var(--lychee) !important;
  }
  [data-testid="stSidebar"] a,
  [data-testid="stSidebar"] a:visited {
    color: var(--lychee) !important;
    text-decoration: none;
  }
  [data-testid="stSidebar"] a:hover {
    color: var(--sky-cloud) !important;
  }
  /* Sidebar nav text (Streamlit sometimes nests spans) */
  [data-testid="stSidebarNav"] span,
  [data-testid="stSidebarNav"] a span,
  [data-testid="stSidebarNav"] ul li a {
    color: var(--lychee) !important;
  }
  [data-testid="stSidebarNav"] ul li a:hover span {
    color: var(--sky-cloud) !important;
  }

  /* Sidebar: solid panel (no frosted / glass layers) */
  [data-testid="stSidebar"] > div:first-child {
    background: var(--american-purple);
    border-right: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow: 14px 0 44px rgba(24, 26, 30, 0.22);
    animation: aeronetSidebarIn 420ms ease both;
  }
  @keyframes aeronetSidebarIn {
    from { opacity: 0; transform: translateX(-10px); }
    to { opacity: 1; transform: translateX(0); }
  }

  /* Sidebar nav items: pill buttons + micro-interactions */
  [data-testid="stSidebarNav"] ul {
    padding-top: 8px !important;
  }
  [data-testid="stSidebarNav"] ul li a {
    transition: background 160ms ease, transform 160ms ease, box-shadow 160ms ease;
  }
  [data-testid="stSidebarNav"] ul li a:hover {
    background: rgba(237, 171, 190, 0.10) !important;
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(24, 26, 30, 0.18);
  }
  /* Active page highlight */
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(251, 200, 204, 0.14) !important;
    box-shadow: inset 0 0 0 1px rgba(251, 200, 204, 0.16);
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: var(--lychee) !important;
    font-weight: 750;
  }
  /* Left accent bar for active */
  [data-testid="stSidebarNav"] a[aria-current="page"]::after {
    content: "";
    position: absolute;
    left: 6px;
    width: 4px;
    height: 18px;
    border-radius: 999px;
    background: linear-gradient(180deg, rgba(57,157,181,1), rgba(124,78,187,1));
    box-shadow: 0 0 0 3px rgba(57,157,181,0.12);
  }
  [data-testid="stSidebarNav"] ul li a {
    position: relative;
  }

  /* Icon styling (mask icons) */
  [data-testid="stSidebarNav"] ul li a::before {
    opacity: 0.92;
    filter: drop-shadow(0 6px 12px rgba(24, 26, 30, 0.20));
  }

  /* Sidebar collapse/expand button: make it feel like a control */
  button[aria-label="Open sidebar"],
  button[aria-label="Close sidebar"],
  button[aria-label="Expand sidebar"],
  button[aria-label="Collapse sidebar"] {
    border-radius: 10px !important;
    transition: background 160ms ease, transform 160ms ease;
  }
  button[aria-label="Open sidebar"]:hover,
  button[aria-label="Close sidebar"]:hover,
  button[aria-label="Expand sidebar"]:hover,
  button[aria-label="Collapse sidebar"]:hover {
    background: rgba(251, 200, 204, 0.12) !important;
    transform: translateY(-1px);
  }

  /* Sidebar open/close / expand/collapse: SVG mask icons (fixes leaked Material ligatures e.g. keyboard_double…) */
  button[aria-label="Open sidebar"],
  button[aria-label="Close sidebar"],
  button[aria-label="Expand sidebar"],
  button[aria-label="Collapse sidebar"] {
    color: var(--lychee) !important;
    position: relative;
    width: 40px !important;
    height: 40px !important;
    border-radius: 10px !important;
  }
  button[aria-label="Open sidebar"] span,
  button[aria-label="Close sidebar"] span,
  button[aria-label="Expand sidebar"] span,
  button[aria-label="Collapse sidebar"] span {
    opacity: 0 !important;
  }
  button[aria-label="Open sidebar"]::after,
  button[aria-label="Close sidebar"]::after,
  button[aria-label="Expand sidebar"]::after,
  button[aria-label="Collapse sidebar"]::after {
    content: "";
    position: absolute;
    inset: 0;
    margin: auto;
    width: 18px;
    height: 18px;
    background: var(--lychee);
    -webkit-mask-size: 18px 18px;
    -webkit-mask-repeat: no-repeat;
    -webkit-mask-position: center;
            mask-size: 18px 18px;
            mask-repeat: no-repeat;
            mask-position: center;
    opacity: 0.95;
    pointer-events: none;
  }
  /* Expand / Open: chevron reveals sidebar */
  button[aria-label="Open sidebar"]::after,
  button[aria-label="Expand sidebar"]::after {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M15.4 12L8.3 19.1 6.9 17.7 12.6 12 6.9 6.3l1.4-1.4z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M15.4 12L8.3 19.1 6.9 17.7 12.6 12 6.9 6.3l1.4-1.4z'/%3E%3C/svg%3E");
  }
  /* Close / Collapse: chevron hides sidebar */
  button[aria-label="Close sidebar"]::after,
  button[aria-label="Collapse sidebar"]::after {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M8.6 12l7.1-7.1 1.4 1.4L11.4 12l5.7 5.7-1.4 1.4z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M8.6 12l7.1-7.1 1.4 1.4L11.4 12l5.7 5.7-1.4 1.4z'/%3E%3C/svg%3E");
  }

  /* Streamlit 1.38+: in-sidebar control uses data-testid; same ligature leak if font fails */
  [data-testid="stSidebarCollapseButton"] {
    position: relative !important;
    border-radius: 10px !important;
    transition: background 160ms ease, transform 160ms ease;
    color: var(--lychee) !important;
    min-width: 2.5rem !important;
    min-height: 2.5rem !important;
  }
  [data-testid="stSidebarCollapseButton"]:hover {
    background: rgba(251, 200, 204, 0.12) !important;
  }
  [data-testid="stSidebarCollapseButton"] span {
    opacity: 0 !important;
  }
  [data-testid="stSidebarCollapseButton"]::after {
    content: "";
    position: absolute;
    inset: 0;
    margin: auto;
    width: 18px;
    height: 18px;
    background: var(--lychee);
    -webkit-mask-size: 18px 18px;
    -webkit-mask-repeat: no-repeat;
    -webkit-mask-position: center;
            mask-size: 18px 18px;
            mask-repeat: no-repeat;
            mask-position: center;
    opacity: 0.95;
    pointer-events: none;
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M8.6 12l7.1-7.1 1.4 1.4L11.4 12l5.7 5.7-1.4 1.4z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M8.6 12l7.1-7.1 1.4 1.4L11.4 12l5.7 5.7-1.4 1.4z'/%3E%3C/svg%3E");
  }

  /* Sidebar sizing: bigger type + icons */
  [data-testid="stSidebarNav"] ul li a {
    font-size: 15px !important;
  }
  [data-testid="stSidebarNav"] ul li a::before {
    width: 18px;
    height: 18px;
    -webkit-mask-size: 18px 18px;
            mask-size: 18px 18px;
  }
  [data-testid="stSidebarNav"] ul li a:hover::before {
    transform: translateY(-0.5px);
  }

  /* Headings */
  h1 {
    color: var(--american-purple);
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  h2 {
    color: var(--royal-purple);
    font-weight: 650;
    letter-spacing: -0.015em;
  }

  /* Metrics */
  [data-testid="stMetricLabel"] {
    color: var(--cadet-grey);
  }
  [data-testid="stMetricValue"] {
    color: var(--purple-taupe);
    font-weight: 700;
  }

  /* Alerts */
  [data-testid="stAlert"] {
    border: none;
  }
  [data-testid="stAlert"][data-baseweb="notification"][kind="success"] div {
    background: var(--veranda-blue);
  }
  [data-testid="stAlert"][data-baseweb="notification"][kind="error"] div {
    background: var(--brink-pink);
  }
  [data-testid="stAlert"][data-baseweb="notification"][kind="info"] div {
    background: var(--deep-space);
  }
  [data-testid="stAlert"][data-baseweb="notification"][kind="warning"] div {
    background: color-mix(in srgb, var(--peach-orange) 35%, white);
  }
  /* Ensure alert text remains readable
     Each kind gets a text color picked for contrast against its painted bg.
     Also targets code/pre/strong/span inside the alert (covers tracebacks). */
  [data-testid="stAlert"][data-baseweb="notification"][kind="info"] *,
  [data-testid="stAlert"][data-baseweb="notification"][kind="info"] code,
  [data-testid="stAlert"][data-baseweb="notification"][kind="info"] pre {
    color: #FFFFFF !important;
  }
  [data-testid="stAlert"][data-baseweb="notification"][kind="success"] *,
  [data-testid="stAlert"][data-baseweb="notification"][kind="success"] code,
  [data-testid="stAlert"][data-baseweb="notification"][kind="success"] pre {
    color: var(--eerie-black) !important;
  }
  [data-testid="stAlert"][data-baseweb="notification"][kind="error"] *,
  [data-testid="stAlert"][data-baseweb="notification"][kind="error"] code,
  [data-testid="stAlert"][data-baseweb="notification"][kind="error"] pre {
    color: #FFFFFF !important;
  }
  [data-testid="stAlert"][data-baseweb="notification"][kind="warning"] *,
  [data-testid="stAlert"][data-baseweb="notification"][kind="warning"] code,
  [data-testid="stAlert"][data-baseweb="notification"][kind="warning"] pre {
    color: var(--eerie-black) !important;
  }
  /* Give code blocks inside alerts a matching, slightly darker bg
     so the text doesn't blend into the colored alert surface */
  [data-testid="stAlert"] code,
  [data-testid="stAlert"] pre {
    background: rgba(24, 26, 30, 0.22) !important;
    border-radius: 6px;
    padding: 2px 6px;
  }

  /* DataFrame headers + row index (parchment; matches --app-bg) */
  [data-testid="stDataFrame"] thead tr th {
    background: var(--df-header-bg) !important;
    color: var(--df-header-text) !important;
    font-weight: 800 !important;
    letter-spacing: 0.01em !important;
    border-color: rgba(24, 26, 30, 0.12) !important;
  }
  [data-testid="stDataFrame"] thead tr th *,
  [data-testid="stDataFrame"] thead tr th span,
  [data-testid="stDataFrame"] thead tr th div {
    color: var(--df-header-text) !important;
    font-weight: 800 !important;
  }
  /* Row labels (index column) — often <th> in tbody or first column */
  [data-testid="stDataFrame"] tbody tr th,
  [data-testid="stDataFrame"] table tbody th {
    background: var(--df-index-bg) !important;
    color: var(--df-header-text) !important;
    font-weight: 700 !important;
    border-color: rgba(24, 26, 30, 0.10) !important;
  }
  [data-testid="stDataFrame"] tbody tr th *,
  [data-testid="stDataFrame"] table tbody th * {
    color: var(--df-header-text) !important;
  }
  /* DataFrame body: transparent cells so Pandas Styler heatmaps show */
  [data-testid="stDataFrame"] tbody tr td {
    background: transparent !important;
    color: var(--american-purple) !important;
    font-weight: 520;
    white-space: normal !important;
  }
  [data-testid="stDataFrame"] tbody tr td div,
  [data-testid="stDataFrame"] tbody tr td span {
    color: var(--american-purple) !important;
  }
  /* Soft parchment behind the grid (was pink; clashed with heatmaps + app bg) */
  [data-testid="stDataFrame"] [data-baseweb="data-table"] tbody {
    background: var(--df-body-wash) !important;
    color: var(--american-purple) !important;
  }
  [data-testid="stDataFrame"] [data-baseweb="data-table"] a {
    color: var(--royal-purple) !important;
  }
  /* DataFrame body */
  [data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(167, 188, 189, 0.14) !important;
  }
  /* DataFrame toolbar / icon buttons (make icons visible) */
  [data-testid="stDataFrame"] [role="toolbar"] {
    color: var(--lychee) !important;
  }
  [data-testid="stDataFrame"] button,
  [data-testid="stDataFrame"] [role="button"] {
    color: var(--lychee) !important;
  }
  [data-testid="stDataFrame"] button svg,
  [data-testid="stDataFrame"] [role="button"] svg {
    fill: var(--lychee) !important;
    color: var(--lychee) !important;
  }
  [data-testid="stDataFrame"] button:hover,
  [data-testid="stDataFrame"] [role="button"]:hover {
    background: rgba(64, 92, 111, 0.18) !important;
  }

  /* Metric values — larger digits (Fleet, Path, Simulation, ML, Disruption, etc.) */
  section[data-testid="stMain"] [data-testid="stMetricValue"] > div,
  section[data-testid="stMain"] [data-testid="stMetricValue"] > p,
  section[data-testid="stMain"] [data-testid="stMetricValue"] span {
    font-size: clamp(1.32rem, 2.5vw, 1.85rem) !important;
    line-height: 1.15 !important;
  }

  /*
   * Expander: <summary><span heading row> [icon span(s)] <div label + StreamlitMarkdown> </span></summary>
   * If Material Symbols fail to load, chevron text e.g. "_arrow_right" prints and stacks on the title.
   * Do not rely on icon fonts: hide every direct <span> under the heading row (icons only; label is a div).
   * Expand/collapse still works via the whole summary row.
   */
  [data-testid="stExpander"] details summary {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    min-width: 0 !important;
    list-style: none !important;
  }
  [data-testid="stExpander"] summary > span:first-of-type {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    flex: 1 1 auto !important;
    min-width: 0 !important;
    gap: 0.5rem !important;
  }
  [data-testid="stExpander"] summary > span:first-of-type > span {
    display: none !important;
  }
  [data-testid="stExpander"] summary > span:first-of-type > div,
  [data-testid="stExpander"] summary > span:first-of-type > div * {
    font-family: "Space Grotesk", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
    font-feature-settings: normal !important;
    font-variant-numeric: normal !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    font-style: normal !important;
    font-variant: normal !important;
  }
  [data-testid="stExpander"] summary > span:first-of-type > div {
    flex: 1 1 auto !important;
    min-width: 0 !important;
  }
  [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p {
    font-weight: 600 !important;
    font-size: 1rem !important;
    line-height: 1.35 !important;
    margin: 0 !important;
  }

  /* Expander top border */
  [data-testid="stExpander"] details {
    border-top: 3px solid var(--veranda-blue);
    border-radius: 10px;
    padding-top: 0.25rem;
  }

  /* AeroNet grid styling + animation */
  .aeronet-grid-wrap {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 10px 0 2px 0;
    width: 100%;
  }
  .aeronet-grid-card {
    width: fit-content;
    max-width: 100%;
    border-radius: 18px;
    padding: 16px 16px 18px 16px;
    background: #f2f1ea;
    border: 1px solid rgba(24, 26, 30, 0.14);
    box-shadow: 0 12px 28px rgba(24, 26, 30, 0.10);
  }
  .aeronet-grid-stage {
    perspective: 1200px;
    padding: 14px 14px 18px 14px;
    border-radius: 16px;
    background: #e9e6dc;
    border: 1px solid rgba(24, 26, 30, 0.10);
    overflow: auto;
    max-width: 100%;
  }
  table.aeronet-grid {
    border-collapse: collapse;
    border-spacing: 0;
    /* Match .aeronet-grid-stage so subpixel seams / anti-alias gaps are not tinted cool gray */
    background: #e9e6dc;
    transform: none;
    transform-origin: center;
    filter: saturate(1.10) brightness(1.04) contrast(1.02);
  }

  /* Hide Streamlit "Deploy" / share actions (toolbar DOM varies by Streamlit version) */
  [data-testid="stDeployButton"],
  [data-testid="stAppDeployButton"],
  [data-testid="baseButton-header_deployAppButton"],
  [data-testid="stToolbarDeployButton"] {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    pointer-events: none !important;
  }
  .stAppDeployButton,
  .stDeployButton,
  header button[aria-label="Deploy"],
  header button[title="Deploy"],
  header a[aria-label*="Deploy"],
  header a[href*="streamlit.io/cloud"],
  header a[href*="share.streamlit.io"] {
    display: none !important;
    visibility: hidden !important;
  }

  /* Top ribbon (sticky): opaque — no backdrop blur */
  .aeronet-top-ribbon {
    position: sticky;
    top: 0;
    z-index: 30;
    margin: 0 0 10px 0;
    padding: 14px 16px;
    border-radius: 16px;
    background: #ebe8d6;
    border: 1px solid rgba(24, 26, 30, 0.12);
    box-shadow: 0 8px 20px rgba(24, 26, 30, 0.07);
  }
  .aeronet-ribbon-cta {
    margin-top: -62px;
    margin-bottom: 26px;
    display: flex;
    justify-content: flex-end;
  }
  .aeronet-ribbon-cta > div {
    min-width: 280px;
  }
  table.aeronet-grid td.aeronet-cell {
    transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
    animation: aeronetPopIn 380ms ease both;
    box-shadow:
      inset 0 1px 0 rgba(255,255,255,0.55),
      inset 0 -2px 0 rgba(24,26,30,0.10);
    border: 0 !important;
    padding: 0 !important;
  }
  table.aeronet-grid td.aeronet-cell > .aeronet-cell-inner {
    background: inherit;
    border-radius: 8px;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    /* grid lines without creating gaps */
    box-shadow:
      inset 0 0 0 1px rgba(24, 26, 30, 0.16),
      inset 0 10px 16px rgba(255, 255, 255, 0.22),
      inset 0 -10px 16px rgba(24, 26, 30, 0.06);
  }
  /* Legend swatches */
  span.zone-swatch {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 3px;
    margin-right: 6px;
    vertical-align: middle;
    border: 1px solid rgba(24,26,30,0.18);
  }
  /* Shimmer animation */
  table.aeronet-grid td.aeronet-cell > .aeronet-cell-inner::before {
    content: "";
    position: absolute;
    inset: -40%;
    background: linear-gradient(115deg,
      rgba(255,255,255,0.00) 0%,
      rgba(255,255,255,0.22) 40%,
      rgba(255,255,255,0.00) 70%);
    transform: translateX(-60%) rotate(10deg);
    animation: none;
    opacity: 0;
    pointer-events: none;
  }
  @keyframes aeronetShimmer {
    0%   { transform: translateX(-70%) rotate(10deg); }
    55%  { transform: translateX(85%) rotate(10deg); }
    100% { transform: translateX(85%) rotate(10deg); }
  }
  table.aeronet-grid td.aeronet-cell:hover > .aeronet-cell-inner::before {
    opacity: 0.70;
    animation: aeronetShimmer 1.1s ease-out 1;
  }
  table.aeronet-grid tr:first-child td.aeronet-cell {
    border-top: 1px solid rgba(24,26,30,0.28) !important;
  }
  table.aeronet-grid td.aeronet-cell:first-child {
    border-left: 1px solid rgba(24,26,30,0.28) !important;
  }
  table.aeronet-grid td.aeronet-cell:hover {
    transform: translateY(-3px) scale(1.05);
    box-shadow:
      0 14px 28px rgba(24, 26, 30, 0.18),
      inset 0 1px 0 rgba(255,255,255,0.55);
    filter: saturate(1.05);
    z-index: 2;
  }
  table.aeronet-grid td.aeronet-cell:hover > .aeronet-cell-inner {
    box-shadow:
      inset 0 0 0 1px rgba(24, 26, 30, 0.20),
      0 10px 20px rgba(24, 26, 30, 0.14),
      inset 0 10px 16px rgba(255, 255, 255, 0.24),
      inset 0 -10px 16px rgba(24, 26, 30, 0.08);
  }
  /* Custom tooltip: bubble dialog with arrow */
  table.aeronet-grid td.aeronet-cell[data-tooltip]::after {
    content: attr(data-tooltip);
    position: absolute;
    left: 50%;
    bottom: calc(100% + 10px);
    transform: translateX(-50%);
    width: max-content;
    max-width: 260px;
    background: rgba(44, 44, 59, 0.95);
    color: #EBE8D6;
    padding: 10px 12px;
    border-radius: 14px;
    font-size: 11.5px;
    line-height: 1.25;
    white-space: pre-line;
    text-align: left;
    word-break: break-word;
    letter-spacing: 0.01em;
    font-family: "Space Grotesk", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    opacity: 0;
    pointer-events: none;
    transition: opacity 120ms ease;
    box-shadow:
      0 14px 28px rgba(24, 26, 30, 0.20),
      0 2px 0 rgba(255, 255, 255, 0.06) inset;
    z-index: 50;
  }
  table.aeronet-grid td.aeronet-cell[data-tooltip]::before {
    content: "";
    position: absolute;
    left: 50%;
    bottom: calc(100% + 4px);
    transform: translateX(-50%);
    width: 10px;
    height: 10px;
    background: rgba(44, 44, 59, 0.95);
    rotate: 45deg;
    opacity: 0;
    pointer-events: none;
    transition: opacity 120ms ease;
    z-index: 49;
  }
  table.aeronet-grid td.aeronet-cell:hover::after {
    opacity: 1;
  }
  table.aeronet-grid td.aeronet-cell:hover::before {
    opacity: 1;
  }

  /* Flip tooltip for top rows so it doesn't shoot off-screen */
  table.aeronet-grid tr:nth-child(-n+2) td.aeronet-cell[data-tooltip]::after {
    top: calc(100% + 10px);
    bottom: auto;
  }
  table.aeronet-grid tr:nth-child(-n+2) td.aeronet-cell[data-tooltip]::before {
    top: calc(100% + 4px);
    bottom: auto;
  }
  @keyframes aeronetPopIn {
    from { opacity: 0; transform: scale(0.96); }
    to { opacity: 1; transform: scale(1); }
  }

  /* Primary buttons */
  div.stButton > button {
    background: var(--veranda-blue);
    color: white;
    border-radius: 8px;
    border: none;
  }
  div.stButton > button:hover {
    background: var(--deep-space);
    color: white;
    border: none;
  }

  /* CSP rule cards animation */
  .aeronet-rule-card {
    animation: aeronetCardIn 420ms ease both;
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
  }
  .aeronet-rule-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 34px rgba(24, 26, 30, 0.10) !important;
    border-color: rgba(24, 26, 30, 0.18) !important;
  }
  @keyframes aeronetCardIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* Sidebar: add simple nav icons + make collapse control always icon-based */
  [data-testid="stSidebarNav"] ul li a {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    padding: 8px 10px !important;
    border-radius: 10px !important;
  }
  [data-testid="stSidebarNav"] ul li a:hover {
    background: rgba(167, 188, 189, 0.10) !important;
  }
  [data-testid="stSidebarNav"] ul li a::before {
    content: "";
    width: 16px;
    height: 16px;
    display: inline-block;
    background: var(--lychee);
    opacity: 0.95;
    -webkit-mask-size: 16px 16px;
    -webkit-mask-repeat: no-repeat;
    -webkit-mask-position: center;
            mask-size: 16px 16px;
            mask-repeat: no-repeat;
            mask-position: center;
  }
  [data-testid="stSidebarNav"] a[href$="/"]::before,
  [data-testid="stSidebarNav"] a[href="/"]::before,
  [data-testid="stSidebarNav"] a[href*="app"]::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z'/%3E%3C/svg%3E");
  }
  [data-testid="stSidebarNav"] a[href*="CSP_Validator"]::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M4 6h16v2H4zm0 5h10v2H4zm0 5h16v2H4z'/%3E%3Cpath fill='black' d='M19 11a2 2 0 1 0 0 4 2 2 0 0 0 0-4z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M4 6h16v2H4zm0 5h10v2H4zm0 5h16v2H4z'/%3E%3Cpath fill='black' d='M19 11a2 2 0 1 0 0 4 2 2 0 0 0 0-4z'/%3E%3C/svg%3E");
  }
  [data-testid="stSidebarNav"] a[href*="Fleet_Selector"]::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M7 17h10v2H7zM6 7h12l1 7H5z'/%3E%3Cpath fill='black' d='M8 6h8v2H8z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M7 17h10v2H7zM6 7h12l1 7H5z'/%3E%3Cpath fill='black' d='M8 6h8v2H8z'/%3E%3C/svg%3E");
  }
  [data-testid="stSidebarNav"] a[href*="Path_Planner"]::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z'/%3E%3C/svg%3E");
  }
  [data-testid="stSidebarNav"] a[href*="Disruption_Handler"]::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z'/%3E%3C/svg%3E");
  }
  [data-testid="stSidebarNav"] a[href*="ML_Pipeline"]::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M9 2h6v2h-2v2.1c2.6.5 4.5 2.8 4.5 5.5S15.6 18.6 13 19.1V21h2v2H9v-2h2v-1.9c-2.6-.5-4.5-2.8-4.5-5.5S8.4 6.6 11 6.1V4H9V2zm3 6a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M9 2h6v2h-2v2.1c2.6.5 4.5 2.8 4.5 5.5S15.6 18.6 13 19.1V21h2v2H9v-2h2v-1.9c-2.6-.5-4.5-2.8-4.5-5.5S8.4 6.6 11 6.1V4H9V2zm3 6a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z'/%3E%3C/svg%3E");
  }
  /* Simulation — bar dashboard (masked like other routes; complements 📊 favicon text) */
  [data-testid="stSidebarNav"] a[href*="6_Simulation"]::before,
  [data-testid="stSidebarNav"] a[href*="Simulation"]::before {
    -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M3 21h18v2H3v-2zm2-10h4v10H5V11zm7-6h4v16h-4V5zm8 4h4v12h-4V9z'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M3 21h18v2H3v-2zm2-10h4v10H5V11zm7-6h4v16h-4V5zm8 4h4v12h-4V9z'/%3E%3C/svg%3E");
  }

  /* Sidebar collapse/expand control: tint (mask draws the glyph) */
  button[aria-label="Open sidebar"],
  button[aria-label="Close sidebar"],
  button[aria-label="Expand sidebar"],
  button[aria-label="Collapse sidebar"] {
    color: var(--lychee) !important;
  }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

