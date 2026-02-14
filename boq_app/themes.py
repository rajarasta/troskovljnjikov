"""Theme definitions for the BoQ Matcher UI.

Each theme is a dict of CSS custom property name -> value.
Switching themes re-injects the :root variables on rerun.
"""

THEMES: dict[str, dict[str, str]] = {
    "minority_report": {
        "name": "Minority Report",
        # Backgrounds — light frosted glass
        "--bg-primary": "rgba(240, 244, 250, 0.97)",
        "--bg-secondary": "#eef2f8",
        "--bg-panel": "rgba(255, 255, 255, 0.55)",
        "--bg-panel-hover": "rgba(255, 255, 255, 0.7)",
        "--bg-panel-active": "rgba(255, 255, 255, 0.8)",
        "--bg-input": "rgba(255, 255, 255, 0.6)",
        "--bg-card-stack": "rgba(255, 255, 255, 0.35)",
        # Borders
        "--border-panel": "rgba(180, 200, 230, 0.4)",
        "--border-glow": "rgba(80, 140, 240, 0.3)",
        "--border-subtle": "rgba(180, 200, 230, 0.2)",
        "--border-divider": "rgba(180, 200, 230, 0.25)",
        # Text
        "--text-primary": "rgba(20, 30, 55, 0.92)",
        "--text-secondary": "rgba(60, 75, 105, 0.75)",
        "--text-muted": "rgba(100, 120, 155, 0.6)",
        "--text-bright": "#0a1428",
        # Accents
        "--accent-primary": "#3b82f6",
        "--accent-secondary": "#f59e0b",
        "--accent-success": "#10b981",
        "--accent-danger": "#ef4444",
        "--accent-warning": "#f59e0b",
        # Glass effect
        "--glass-blur": "24px",
        "--glass-saturation": "120%",
        # Shadows
        "--shadow-card": "0 4px 24px rgba(0, 30, 80, 0.08)",
        "--shadow-glow": "0 0 20px rgba(60, 130, 246, 0.06)",
        "--shadow-glow-strong": "0 0 30px rgba(60, 130, 246, 0.1)",
        "--shadow-float": "0 12px 40px rgba(0, 30, 80, 0.12)",
        # Radii
        "--radius-card": "18px",
        "--radius-badge": "10px",
        "--radius-sm": "6px",
        # Fonts
        "--font-mono": "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
        "--font-heading": "'Inter', 'SF Pro Display', system-ui, sans-serif",
        # Transitions
        "--transition-default": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "--transition-fast": "all 0.15s ease-out",
        # Glow line
        "--glow-line": "linear-gradient(90deg, transparent, var(--accent-primary), transparent)",
    },
    "blueprint": {
        "name": "Blueprint",
        "--bg-primary": "rgba(0, 25, 70, 0.97)",
        "--bg-secondary": "#001237",
        "--bg-panel": "rgba(5, 35, 90, 0.5)",
        "--bg-panel-hover": "rgba(10, 50, 110, 0.6)",
        "--bg-panel-active": "rgba(15, 60, 130, 0.65)",
        "--bg-input": "rgba(0, 20, 60, 0.7)",
        "--bg-card-stack": "rgba(10, 30, 70, 0.4)",
        "--border-panel": "rgba(255, 255, 255, 0.18)",
        "--border-glow": "rgba(255, 255, 255, 0.35)",
        "--border-subtle": "rgba(255, 255, 255, 0.06)",
        "--border-divider": "rgba(255, 255, 255, 0.1)",
        "--text-primary": "rgba(255, 255, 255, 0.93)",
        "--text-secondary": "rgba(200, 215, 240, 0.7)",
        "--text-muted": "rgba(150, 175, 210, 0.5)",
        "--text-bright": "#ffffff",
        "--accent-primary": "#ffffff",
        "--accent-secondary": "#80b4ff",
        "--accent-success": "#66ffa6",
        "--accent-danger": "#ff6680",
        "--accent-warning": "#ffe066",
        "--glass-blur": "16px",
        "--glass-saturation": "150%",
        "--shadow-card": "0 6px 24px rgba(0, 0, 0, 0.5)",
        "--shadow-glow": "0 0 16px rgba(255, 255, 255, 0.06)",
        "--shadow-glow-strong": "0 0 24px rgba(255, 255, 255, 0.1)",
        "--shadow-float": "0 12px 40px rgba(0, 0, 0, 0.6)",
        "--radius-card": "14px",
        "--radius-badge": "8px",
        "--radius-sm": "4px",
        "--font-mono": "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
        "--font-heading": "'Inter', 'SF Pro Display', system-ui, sans-serif",
        "--transition-default": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "--transition-fast": "all 0.15s ease-out",
        "--glow-line": "linear-gradient(90deg, transparent, rgba(255,255,255,0.7), transparent)",
    },
    "construction_site": {
        "name": "Construction Site",
        "--bg-primary": "rgba(250, 245, 240, 0.97)",
        "--bg-secondary": "#f5efe8",
        "--bg-panel": "rgba(255, 255, 255, 0.5)",
        "--bg-panel-hover": "rgba(255, 255, 255, 0.65)",
        "--bg-panel-active": "rgba(255, 255, 255, 0.75)",
        "--bg-input": "rgba(255, 255, 255, 0.55)",
        "--bg-card-stack": "rgba(255, 250, 245, 0.4)",
        "--border-panel": "rgba(200, 170, 130, 0.3)",
        "--border-glow": "rgba(245, 158, 11, 0.35)",
        "--border-subtle": "rgba(200, 170, 130, 0.15)",
        "--border-divider": "rgba(200, 170, 130, 0.2)",
        "--text-primary": "rgba(50, 40, 30, 0.92)",
        "--text-secondary": "rgba(100, 80, 60, 0.7)",
        "--text-muted": "rgba(150, 125, 95, 0.6)",
        "--text-bright": "#1a1208",
        "--accent-primary": "#d97706",
        "--accent-secondary": "#ea580c",
        "--accent-success": "#16a34a",
        "--accent-danger": "#dc2626",
        "--accent-warning": "#d97706",
        "--glass-blur": "20px",
        "--glass-saturation": "130%",
        "--shadow-card": "0 4px 20px rgba(80, 60, 30, 0.08)",
        "--shadow-glow": "0 0 16px rgba(217, 119, 6, 0.06)",
        "--shadow-glow-strong": "0 0 28px rgba(217, 119, 6, 0.1)",
        "--shadow-float": "0 12px 40px rgba(80, 60, 30, 0.12)",
        "--radius-card": "16px",
        "--radius-badge": "9px",
        "--radius-sm": "5px",
        "--font-mono": "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
        "--font-heading": "'Inter', 'SF Pro Display', system-ui, sans-serif",
        "--transition-default": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "--transition-fast": "all 0.15s ease-out",
        "--glow-line": "linear-gradient(90deg, transparent, var(--accent-primary), transparent)",
    },
}


def get_theme_css_vars(theme_name: str) -> str:
    """Return CSS variable declarations for the given theme."""
    theme = THEMES.get(theme_name, THEMES["minority_report"])
    return "\n".join(
        f"    {k}: {v};"
        for k, v in theme.items()
        if k.startswith("--")
    )
