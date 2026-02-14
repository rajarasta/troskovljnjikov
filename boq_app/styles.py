"""CSS architecture for the BoQ Matcher UI.

Light frosted glass aesthetic. Two-column layout:
  Left: match carousel with stacked cards
  Right: unified unit panel with subdivisions
"""


def _base_css() -> str:
    return """
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

    .stApp {
        background: var(--bg-secondary) !important;
        background-image:
            radial-gradient(ellipse at 15% 40%, rgba(59, 130, 246, 0.04) 0%, transparent 50%),
            radial-gradient(ellipse at 85% 25%, rgba(99, 102, 241, 0.03) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 90%, rgba(59, 130, 246, 0.02) 0%, transparent 40%) !important;
    }

    .block-container {
        padding-top: 0.75rem !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent !important; }
    """


def _glassmorphism_css() -> str:
    return """
    .glass-panel {
        position: relative;
        background: var(--bg-panel);
        backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturation));
        -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturation));
        border: 1px solid var(--border-panel);
        border-radius: var(--radius-card);
        box-shadow: var(--shadow-card);
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        transition: var(--transition-default);
    }

    .glass-panel:hover {
        background: var(--bg-panel-hover);
        box-shadow: var(--shadow-card), var(--shadow-glow);
    }

    .glass-panel::before {
        content: '';
        position: absolute;
        top: 0;
        left: 10%;
        right: 10%;
        height: 1px;
        background: var(--glow-line);
        opacity: 0.35;
        border-radius: var(--radius-card) var(--radius-card) 0 0;
    }

    .glass-panel-header {
        font-family: var(--font-heading);
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--text-muted);
        padding-bottom: 0.6rem;
        margin-bottom: 0.6rem;
        border-bottom: 1px solid var(--border-subtle);
    }

    .glass-panel-compact {
        padding: 0.6rem 0.9rem;
    }

    /* Unified panel — the big merged right side */
    .unit-panel {
        position: relative;
        background: var(--bg-panel);
        backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturation));
        -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturation));
        border: 1px solid var(--border-panel);
        border-radius: var(--radius-card);
        box-shadow: var(--shadow-float);
        padding: 0;
        overflow: hidden;
    }
    .unit-panel::before {
        content: '';
        position: absolute;
        top: 0;
        left: 5%;
        right: 5%;
        height: 1px;
        background: var(--glow-line);
        opacity: 0.4;
        z-index: 1;
    }

    .unit-section {
        padding: 1rem 1.5rem;
        border-bottom: 1px solid var(--border-divider);
    }
    .unit-section:last-child {
        border-bottom: none;
    }
    .unit-section-header {
        font-family: var(--font-heading);
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--text-muted);
        margin-bottom: 0.6rem;
    }
    """


def _pipeline_css() -> str:
    return """
    .pipeline-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 0;
        padding: 0.5rem 1rem;
        margin-bottom: 0.5rem;
    }

    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 0.35rem;
    }

    .pipeline-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        border: 2px solid var(--border-panel);
        background: transparent;
        transition: var(--transition-default);
        flex-shrink: 0;
    }
    .pipeline-dot.done {
        background: var(--accent-success);
        border-color: var(--accent-success);
    }
    .pipeline-dot.active {
        background: var(--accent-primary);
        border-color: var(--accent-primary);
        animation: pulse-dot 1.5s ease-in-out infinite;
    }
    .pipeline-dot.error {
        background: var(--accent-danger);
        border-color: var(--accent-danger);
    }

    .pipeline-label {
        font-family: var(--font-heading);
        font-size: 0.65rem;
        font-weight: 500;
        letter-spacing: 0.04em;
        color: var(--text-muted);
        transition: var(--transition-default);
    }
    .pipeline-label.done { color: var(--accent-success); }
    .pipeline-label.active { color: var(--accent-primary); font-weight: 600; }

    .pipeline-line {
        width: 28px;
        height: 2px;
        background: var(--border-subtle);
        margin: 0 0.2rem;
        transition: var(--transition-default);
        flex-shrink: 0;
    }
    .pipeline-line.done { background: var(--accent-success); }

    @keyframes pulse-dot {
        0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
        50% { box-shadow: 0 0 0 5px rgba(59, 130, 246, 0); }
    }
    """


def _carousel_css() -> str:
    """Match carousel — stacked cards with depth layering."""
    return """
    .carousel-card {
        position: relative;
        background: var(--bg-panel);
        backdrop-filter: blur(var(--glass-blur));
        border: 1px solid var(--border-panel);
        border-radius: var(--radius-card);
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.5rem;
        transition: var(--transition-default);
        cursor: pointer;
    }
    .carousel-card:hover {
        background: var(--bg-panel-hover);
        border-color: var(--border-glow);
        box-shadow: var(--shadow-glow);
        transform: translateX(4px);
    }
    .carousel-card.active {
        background: var(--bg-panel-active);
        border-color: var(--accent-primary);
        box-shadow: var(--shadow-glow-strong);
    }

    /* Stacked depth effect — cards behind */
    .carousel-stack {
        position: relative;
        margin-bottom: 1.2rem;
    }
    .carousel-stack::after {
        content: '';
        position: absolute;
        bottom: -4px;
        left: 6px;
        right: 6px;
        height: 8px;
        background: var(--bg-card-stack);
        border-radius: 0 0 var(--radius-card) var(--radius-card);
        border: 1px solid var(--border-subtle);
        border-top: none;
        z-index: -1;
    }
    .carousel-stack::before {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 12px;
        right: 12px;
        height: 8px;
        background: var(--bg-card-stack);
        border-radius: 0 0 var(--radius-card) var(--radius-card);
        border: 1px solid var(--border-subtle);
        border-top: none;
        z-index: -2;
        opacity: 0.6;
    }

    .carousel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.4rem;
    }

    .carousel-source {
        font-family: var(--font-heading);
        font-size: 0.78rem;
        font-weight: 500;
        color: var(--text-primary);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
    }

    .carousel-confidence {
        font-family: var(--font-mono);
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--accent-primary);
        flex-shrink: 0;
        margin-left: 0.5rem;
    }

    .carousel-year {
        font-family: var(--font-mono);
        font-size: 0.62rem;
        padding: 1px 5px;
        border-radius: var(--radius-sm);
        background: var(--bg-card-stack);
        color: var(--text-muted);
        flex-shrink: 0;
        margin-left: 0.4rem;
    }

    .confidence-bar {
        height: 3px;
        border-radius: 2px;
        background: var(--border-subtle);
        overflow: hidden;
        margin: 0.35rem 0;
    }
    .confidence-bar-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.5s ease-out;
    }
    .confidence-bar-fill.high   { background: var(--accent-success); }
    .confidence-bar-fill.medium { background: var(--accent-warning); }
    .confidence-bar-fill.low    { background: var(--accent-danger); }

    .carousel-meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.72rem;
        color: var(--text-secondary);
    }

    .delta-badge {
        display: inline-block;
        padding: 1px 6px;
        border-radius: var(--radius-sm);
        font-size: 0.68rem;
        font-weight: 600;
        font-family: var(--font-mono);
    }
    .delta-badge.positive { background: rgba(16, 185, 129, 0.1); color: var(--accent-success); }
    .delta-badge.neutral  { background: rgba(245, 158, 11, 0.1); color: var(--accent-warning); }
    .delta-badge.negative { background: rgba(239, 68, 68, 0.1); color: var(--accent-danger); }

    .carousel-price {
        font-family: var(--font-mono);
        font-size: 0.75rem;
        color: var(--text-primary);
    }
    .carousel-price .cur {
        color: var(--text-muted);
        font-size: 0.65rem;
    }

    /* Sub-layer: expanded detail within a card */
    .carousel-detail {
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid var(--border-subtle);
    }
    .carousel-detail-table {
        width: 100%;
        border-collapse: collapse;
    }
    .carousel-detail-table th {
        padding: 3px 6px;
        font-size: 0.62rem;
        color: var(--text-muted);
        text-align: left;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid var(--border-subtle);
    }
    .carousel-detail-table td {
        padding: 3px 6px;
        font-size: 0.72rem;
        color: var(--text-secondary);
    }
    .carousel-detail-table td.mono {
        font-family: var(--font-mono);
        font-size: 0.7rem;
    }
    .carousel-detail-table td.price {
        font-family: var(--font-mono);
        color: var(--accent-primary);
        text-align: right;
    }
    """


def _unit_panel_css() -> str:
    """Styles for the unified unit detail panel subdivisions."""
    return """
    .item-number-badge {
        display: inline-block;
        font-family: var(--font-mono);
        font-size: 0.75rem;
        font-weight: 600;
        padding: 2px 9px;
        border-radius: var(--radius-sm);
        background: rgba(245, 158, 11, 0.1);
        color: var(--accent-secondary);
        margin-right: 0.4rem;
    }

    .item-title {
        font-family: var(--font-heading);
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        line-height: 1.3;
    }

    .item-description {
        font-size: 0.78rem;
        color: var(--text-secondary);
        line-height: 1.5;
        max-height: 100px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: var(--border-panel) transparent;
        white-space: pre-wrap;
    }

    .item-breadcrumb {
        font-size: 0.68rem;
        color: var(--text-muted);
        font-family: var(--font-mono);
        margin-bottom: 0.35rem;
    }
    .item-breadcrumb span { margin: 0 0.2rem; }

    /* Reasoning inside the unit panel */
    .reasoning-container {
        max-height: 200px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: var(--border-panel) transparent;
    }

    .reasoning-entry {
        padding: 0.25rem 0;
        border-bottom: 1px solid var(--border-subtle);
        font-family: var(--font-mono);
        font-size: 0.7rem;
        line-height: 1.35;
        color: var(--text-secondary);
    }
    .reasoning-entry:last-child { border-bottom: none; }

    .reasoning-timestamp {
        color: var(--text-muted);
        margin-right: 0.3rem;
        font-size: 0.63rem;
    }

    .agent-badge {
        display: inline-block;
        padding: 0px 4px;
        border-radius: var(--radius-sm);
        font-size: 0.6rem;
        font-weight: 600;
        margin-right: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .agent-badge.indexer  { background: rgba(59, 130, 246, 0.1); color: var(--accent-primary); }
    .agent-badge.matcher  { background: rgba(245, 158, 11, 0.1); color: var(--accent-secondary); }
    .agent-badge.pricer   { background: rgba(16, 185, 129, 0.1); color: var(--accent-success); }
    .agent-badge.system   { background: var(--border-subtle); color: var(--text-muted); }

    .reasoning-thinking { color: var(--text-muted); font-style: italic; }
    .reasoning-result   { color: var(--accent-success); }
    .reasoning-error    { color: var(--accent-danger); }

    /* Confidence breakdown inside unit panel */
    .confidence-breakdown-item { margin-bottom: 0.45rem; }
    .confidence-breakdown-label {
        display: flex;
        justify-content: space-between;
        font-family: var(--font-heading);
        font-size: 0.68rem;
        color: var(--text-secondary);
        margin-bottom: 0.15rem;
    }
    .confidence-breakdown-value {
        font-family: var(--font-mono);
        color: var(--text-primary);
    }
    .confidence-breakdown-bar {
        height: 3px;
        border-radius: 2px;
        background: var(--border-subtle);
        overflow: hidden;
    }
    .confidence-breakdown-fill {
        height: 100%;
        border-radius: 2px;
        background: var(--accent-primary);
        transition: width 0.5s ease-out;
    }

    .confidence-overall {
        font-family: var(--font-mono);
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--accent-primary);
        text-align: center;
    }
    .confidence-overall-label {
        font-family: var(--font-heading);
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
        text-align: center;
        margin-bottom: 0.6rem;
    }

    /* Stats row inside unit panel */
    .stats-row {
        display: flex;
        gap: 1rem;
        justify-content: center;
    }
    .stat-item {
        text-align: center;
    }
    .stat-value {
        font-family: var(--font-mono);
        font-size: 1rem;
        font-weight: 600;
        color: var(--accent-primary);
    }
    .stat-label {
        font-family: var(--font-heading);
        font-size: 0.58rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
    }
    """


def _header_css() -> str:
    return """
    .app-title {
        font-family: var(--font-heading);
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: 0.02em;
    }
    .app-subtitle {
        font-family: var(--font-heading);
        font-size: 0.62rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.15em;
    }
    """


def _streamlit_overrides() -> str:
    return """
    /* Buttons */
    .stButton > button {
        background: var(--bg-panel) !important;
        border: 1px solid var(--border-panel) !important;
        color: var(--text-primary) !important;
        border-radius: var(--radius-badge) !important;
        backdrop-filter: blur(10px) !important;
        transition: var(--transition-default) !important;
        font-size: 0.75rem !important;
        padding: 0.3rem 0.7rem !important;
    }
    .stButton > button:hover {
        border-color: var(--accent-primary) !important;
        box-shadow: var(--shadow-glow) !important;
    }
    .stButton > button[kind="primary"] {
        background: rgba(59, 130, 246, 0.12) !important;
        border-color: var(--accent-primary) !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: var(--bg-panel) !important;
        border: 1px dashed var(--border-panel) !important;
        border-radius: var(--radius-card) !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: var(--radius-badge) !important;
        overflow: hidden;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: var(--bg-panel) !important;
        border: 1px solid var(--border-panel) !important;
        border-radius: var(--radius-badge) !important;
        padding: 0.5rem 0.6rem !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--accent-primary) !important;
        font-family: var(--font-mono) !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
        font-size: 0.6rem !important;
        letter-spacing: 0.08em !important;
    }

    /* Selectbox */
    [data-testid="stSelectbox"] > div > div {
        background: var(--bg-input) !important;
        border-color: var(--border-panel) !important;
    }

    /* Radio — tree nav style */
    div[data-testid="stRadio"] > label { display: none !important; }
    div[data-testid="stRadio"] > div { gap: 0 !important; }
    div[data-testid="stRadio"] > div > label {
        background: transparent !important;
        padding: 0.3rem 0.5rem !important;
        margin: 0 !important;
        border-left: 3px solid transparent;
        transition: var(--transition-fast) !important;
        font-size: 0.78rem !important;
    }
    div[data-testid="stRadio"] > div > label:hover {
        background: rgba(59, 130, 246, 0.04) !important;
    }
    div[data-testid="stRadio"] > div > label[data-checked="true"] {
        border-left-color: var(--accent-primary) !important;
        background: rgba(59, 130, 246, 0.06) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        border-bottom: 1px solid var(--border-subtle) !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--text-muted) !important;
        font-size: 0.72rem !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--accent-primary) !important;
    }

    hr { border-color: var(--border-subtle) !important; }

    ::-webkit-scrollbar { width: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: var(--border-panel);
        border-radius: 2px;
    }
    """


def get_all_css(theme_vars: str) -> str:
    """Combine all CSS with injected theme variables."""
    return f"""<style>
:root {{
{theme_vars}
}}
{_base_css()}
{_glassmorphism_css()}
{_pipeline_css()}
{_carousel_css()}
{_unit_panel_css()}
{_header_css()}
{_streamlit_overrides()}

@supports not (backdrop-filter: blur(20px)) {{
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(255, 255, 255, 0.85) !important;
    }}
}}
</style>"""
