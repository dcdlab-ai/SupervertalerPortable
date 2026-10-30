"""Platform-agnostic shortcut display helpers.

Historically these functions converted ``Ctrl``/``Alt``/``Shift``/``Meta``
tokens to macOS symbol glyphs (⌘/⌥/⇧/⌃) on macOS. The macOS build was
retired (batch P1.7), so on every supported platform (Windows, Linux) the
functions are the identity transform. They are kept as the stable display
API used throughout the UI text formatting code.
"""


def format_shortcut_for_display(shortcut: str) -> str:
    """Return a platform-appropriate shortcut label suitable for UI text."""
    return shortcut


def format_shortcuts_in_text(text: str) -> str:
    """Replace all shortcut-like tokens in text with platform-native display."""
    return text
