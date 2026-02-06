"""
Settings manager for Whoa-Scope application.
Handles persistent storage of user preferences using Kivy's JsonStore.
Settings are stored in the OS-appropriate user data directory.
"""

import os
import glob
import copy
from kivy.storage.jsonstore import JsonStore
from kivy.app import App
from kivy.utils import platform


# Color theme definitions
# Each theme contains colors for various UI elements
COLOR_THEMES = {
    'default': {
        'name': 'Default (Dark)',
        'ch1_color': '#FFFF00',           # Yellow
        'ch2_color': '#00FFFF',           # Cyan
        'plot_background': '#080808',      # Near black
        'axes_background': '#000000',      # Black
        'axes_color': '#FFFFFF',           # White
        'grid_color': '#585858',           # Gray
        'text_color': [1.0, 1.0, 1.0, 1.0],  # White (RGBA)
        'button_normal': [0.345, 0.345, 0.345],  # Gray
        'button_pressed': [0.196, 0.643, 0.808],  # Blue
        'panel_background': [0.03125, 0.03125, 0.03125, 0.8],  # Dark translucent
        'waveform_color': '#00FF00',       # Green (for wavegen)
        'gain_color': '#FF00FF',           # Magenta (for bode gain)
        'phase_color': '#00FFFF',          # Cyan (for bode phase)
        'tooltip_background': [0.2, 0.2, 0.2, 0.95],  # Dark gray translucent
        'tooltip_text_color': [1.0, 1.0, 1.0, 1.0],   # White
    },
    'light': {
        'name': 'Light Mode',
        'ch1_color': '#0000CC',           # Dark blue
        'ch2_color': '#CC0000',           # Dark red
        'plot_background': '#F0F0F0',      # Light gray
        'axes_background': '#FFFFFF',      # White
        'axes_color': '#000000',           # Black
        'grid_color': '#CCCCCC',           # Light gray
        'text_color': [0.0, 0.0, 0.0, 1.0],  # Black (RGBA)
        'button_normal': [0.8, 0.8, 0.8],  # Light gray
        'button_pressed': [0.4, 0.7, 0.9],  # Light blue
        'panel_background': [0.9, 0.9, 0.9, 0.9],  # Light translucent
        'waveform_color': '#008800',       # Dark green (for wavegen)
        'gain_color': '#8800AA',           # Purple (for bode gain)
        'phase_color': '#CC0000',          # Dark red (for bode phase)
        'tooltip_background': [0.95, 0.95, 0.9, 0.95],  # Light cream
        'tooltip_text_color': [0.0, 0.0, 0.0, 1.0],     # Black
    },
    'homebrew': {
        'name': 'Homebrew',
        'ch1_color': '#00FF00',           # Bright green
        'ch2_color': '#006600',           # Darker green
        'plot_background': '#000000',      # Black
        'axes_background': '#001100',      # Very dark green
        'axes_color': '#00FF00',           # Green
        'grid_color': '#004400',           # Dark green
        'text_color': [0.0, 1.0, 0.0, 1.0],  # Green (RGBA)
        'button_normal': [0.0, 0.2, 0.0],  # Dark green
        'button_pressed': [0.0, 0.5, 0.0],  # Medium green
        'panel_background': [0.0, 0.05, 0.0, 0.9],  # Dark green translucent
        'waveform_color': '#00FF00',       # Green (for wavegen)
        'gain_color': '#00FF00',           # Green (for bode gain)
        'phase_color': '#006600',          # Darker green (for bode phase)
        'tooltip_background': [0.0, 0.15, 0.0, 0.95],  # Dark green
        'tooltip_text_color': [0.0, 1.0, 0.0, 1.0],    # Green
    },
    'rat': {
        'name': 'Rat',
        'ch1_color': "#582B00",     
        'ch2_color': "#FF11F3",       
        'plot_background': "#777777",   
        'axes_background': '#777777',     
        'axes_color': "#000000",        
        'grid_color': '#000000',    
        'text_color': [1.0, 1.0, 0.0, 1.0], 
        'button_normal': [1, 0.35, 0], 
        'button_pressed': [0.5, 0.2, 0], 
        'panel_background': [0.1, 0.0, 0.1, 0.8],
        'waveform_color': "#00CCFF", 
        'gain_color': '#FF00FF',           # Magenta (for bode gain)
        'phase_color': '#FFFF00',          # Yellow (for bode phase)
        'tooltip_background': [0.3, 0.15, 0.0, 0.95],  # Brown
        'tooltip_text_color': [1.0, 1.0, 0.0, 1.0],    # Yellow
    },
    'nook': {
        'name': 'Nook',
        'ch1_color': '#5F305C',           # Pink
        'ch2_color': "#0038A8",           # Blue
        'plot_background': "#D60270",      # Purple
        'axes_background': '#D60270',      # Purple
        'axes_color': '#000000',           # Black
        'grid_color': '#585858',           # Grey
        'text_color': [1.0, 1.0, 1.0, 1.0],  # White (RGBA)
        'button_normal': [0.5, 0.0, 0.5],  # Purple
        'button_pressed': [1.0, 0.0, 1.0],  # Magenta
        'panel_background': [0.1, 0.0, 0.1, 0.8],  # Dark purple translucent
        'waveform_color': '#00FFFF',       # Cyan (for wavegen)
        'gain_color': '#FF00FF',           # Magenta (for bode gain)
        'phase_color': '#FFFF00',          # Yellow (for bode phase)
        'tooltip_background': [0.3, 0.0, 0.3, 0.95],  # Dark purple
        'tooltip_text_color': [1.0, 1.0, 1.0, 1.0],   # White
    },
    'garfield': {
        'name': 'Garfield',
        'ch1_color': '#f8a5c2',
        'ch2_color': "#f8a5c2",
        'plot_background': "#ffa502",
        'axes_background': '#ffa502',
        'axes_color': '#000000',
        'grid_color': '#585858',
        'text_color': [1.0, 1.0, 1.0, 1.0],
        'button_normal': [255/255,159/255,67/255],
        'button_pressed': [255/511,159/511,67/511],
        'panel_background': [0.0, 0.0, 0.0, 0.8],
        'waveform_color': '#00FFFF',
        'gain_color': '#FF00FF',
        'phase_color': '#FFFF00',
        'tooltip_background': [0.8, 0.4, 0.0, 0.95],  # Orange
        'tooltip_text_color': [0.0, 0.0, 0.0, 1.0],   # Black
    },
    'shark': {
        'name': 'Shark',
        'ch1_color': '#F5A9B8',
        'ch2_color': "#FFFFFF",
        'plot_background': "#6996AD",
        'axes_background': '#6996AD',
        'axes_color': '#000000',
        'grid_color': '#585858',
        'text_color': [1.0, 1.0, 1.0, 1.0],
        'button_normal': [91/255, 206/255, 250/255],
        'button_pressed': [91/511, 206/511, 250/511],
        'panel_background': [0.0, 0.0, 0.0, 0.8],
        'waveform_color': '#00FFFF',
        'gain_color': '#FF00FF',
        'phase_color': '#FFFF00',
        'tooltip_background': [0.2, 0.5, 0.7, 0.95],  # Blue-ish
        'tooltip_text_color': [1.0, 1.0, 1.0, 1.0],   # White
    },
    'ireland': {
        'name': 'ireland',
        'ch1_color': '#FF8200',
        'ch2_color': "#FFFFFF",
        'plot_background': "#009844",
        'axes_background': '#009844',
        'axes_color': '#FFFFFF',
        'grid_color': "#FFFFFF",
        'text_color': [1.0, 1.0, 1.0, 1.0],
        'button_normal': [255/255, 130/255, 0/255],
        'button_pressed': [255/511, 130/511, 0/511],
        'panel_background': [0.0, 0.0, 0.0, 0.8],
        'waveform_color': '#00FFFF',
        'gain_color': '#FF00FF',
        'phase_color': '#FFFF00',
        'tooltip_background': [0.2, 0.5, 0.7, 0.95],  # Blue-ish
        'tooltip_text_color': [1.0, 1.0, 1.0, 1.0],   # White
    },
    'custom': {
        'name': 'Custom',
        'ch1_color': '#FFFF00',
        'ch2_color': '#00FFFF',
        'plot_background': '#080808',
        'axes_background': '#000000',
        'axes_color': '#FFFFFF',
        'grid_color': '#585858',
        'text_color': [1.0, 1.0, 1.0, 1.0],
        'button_normal': [0.345, 0.345, 0.345],
        'button_pressed': [0.196, 0.643, 0.808],
        'panel_background': [0.03125, 0.03125, 0.03125, 0.8],
        'waveform_color': '#00FF00',
        'gain_color': '#FF00FF',
        'phase_color': '#00FFFF',
        'tooltip_background': [0.2, 0.2, 0.2, 0.95],
        'tooltip_text_color': [1.0, 1.0, 1.0, 1.0],
    },
}

# List of available theme names for UI
AVAILABLE_THEMES = list(COLOR_THEMES.keys())


def get_fonts_directory():
    """Get the path to the fonts directory."""
    import sys
    # Try relative to current directory first
    fonts_dir = os.path.join(os.getcwd(), 'fonts')
    if os.path.isdir(fonts_dir):
        return fonts_dir
    # Try relative to script location (for frozen apps)
    if getattr(sys, 'frozen', False):
        fonts_dir = os.path.join(sys._MEIPASS, 'fonts')
        if os.path.isdir(fonts_dir):
            return fonts_dir
    return None


def scan_available_fonts():
    """
    Scan the ./fonts directory for available font files.
    Returns a dict mapping display names to font file paths.
    """
    fonts = {}
    fonts_dir = get_fonts_directory()
    
    if fonts_dir and os.path.isdir(fonts_dir):
        for ext in ['*.ttf', '*.otf', '*.TTF', '*.OTF']:
            for font_path in glob.glob(os.path.join(fonts_dir, ext)):
                # Extract display name from filename
                filename = os.path.basename(font_path)
                # Remove extension and clean up name
                name = os.path.splitext(filename)[0]
                # Make name more readable (replace dashes/underscores with spaces)
                display_name = name.replace('-', ' ').replace('_', ' ')
                # Remove common suffixes like "Regular", "VariableFont", etc.
                for suffix in ['Regular', 'VariableFont wdth,wght', 'VariableFont']:
                    display_name = display_name.replace(suffix, '').strip()
                fonts[display_name] = font_path
    
    return fonts


# Scan available fonts from ./fonts directory
AVAILABLE_FONTS = scan_available_fonts()

# Default settings - use first available font or 'Roboto' (Kivy default)
default_font = list(AVAILABLE_FONTS.keys())[0] if AVAILABLE_FONTS else 'Roboto'
DEFAULT_SETTINGS = {
    'font_name': default_font,
    'font_scale': 1.0,  # 100% scale factor for font sizes
    'launch_maximized': False,
    'color_theme': 'default',  # Current theme name
    'custom_theme': copy.deepcopy(COLOR_THEMES['default']),  # Custom theme settings
}


def get_font_path(font_name):
    """Get the full path to a font file by its display name."""
    return AVAILABLE_FONTS.get(font_name, None)


class SettingsManager:
    """
    Manages application settings with persistent storage.
    Uses Kivy's JsonStore for cross-platform compatibility.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._store = None
        self._settings = DEFAULT_SETTINGS.copy()
    
    def _get_settings_path(self):
        """
        Get the path to the settings file in the appropriate OS directory.
        Uses platformdirs for cross-platform compatibility.
        """
        if platform == 'win':
            # Windows: %APPDATA%/WhoaScope/
            base_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
            settings_dir = os.path.join(base_dir, 'WhoaScope')
        elif platform == 'macosx':
            # macOS: ~/Library/Application Support/WhoaScope/
            settings_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'WhoaScope')
        elif platform == 'linux':
            # Linux: ~/.config/WhoaScope/ or $XDG_CONFIG_HOME/WhoaScope/
            xdg_config = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
            settings_dir = os.path.join(xdg_config, 'WhoaScope')
        else:
            # Fallback for other platforms (iOS, Android, etc.)
            settings_dir = os.path.join(os.path.expanduser('~'), '.whoascope')
        
        # Create directory if it doesn't exist
        os.makedirs(settings_dir, exist_ok=True)
        
        return os.path.join(settings_dir, 'settings.json')
    
    def initialize(self):
        """Initialize the settings store and load saved settings."""
        settings_path = self._get_settings_path()
        self._store = JsonStore(settings_path)
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from the store."""
        if self._store is None:
            return
        
        for key, default_value in DEFAULT_SETTINGS.items():
            if self._store.exists(key):
                try:
                    stored = self._store.get(key)
                    self._settings[key] = stored.get('value', default_value)
                except Exception:
                    self._settings[key] = default_value
            else:
                self._settings[key] = default_value
    
    def _save_setting(self, key, value):
        """Save a single setting to the store."""
        if self._store is None:
            return
        self._store.put(key, value=value)
    
    def get(self, key, default=None):
        """Get a setting value."""
        return self._settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))
    
    def set(self, key, value):
        """Set a setting value and persist it."""
        self._settings[key] = value
        self._save_setting(key, value)
    
    @property
    def font_name(self):
        return self.get('font_name')
    
    @font_name.setter
    def font_name(self, value):
        self.set('font_name', value)
    
    @property
    def font_scale(self):
        return self.get('font_scale')
    
    @font_scale.setter
    def font_scale(self, value):
        self.set('font_scale', value)
    
    @property
    def launch_maximized(self):
        return self.get('launch_maximized')
    
    @launch_maximized.setter
    def launch_maximized(self, value):
        self.set('launch_maximized', value)
    
    @property
    def color_theme(self):
        return self.get('color_theme')
    
    @color_theme.setter
    def color_theme(self, value):
        self.set('color_theme', value)
    
    @property
    def tooltip_delay(self):
        return self.get('tooltip_delay', 0.5)
    
    @tooltip_delay.setter
    def tooltip_delay(self, value):
        self.set('tooltip_delay', value)
    
    @property
    def custom_theme(self):
        return self.get('custom_theme')
    
    @custom_theme.setter
    def custom_theme(self, value):
        self.set('custom_theme', value)
    
    def get_current_theme(self):
        """Get the current theme's color dictionary."""
        theme_name = self.color_theme
        if theme_name == 'custom':
            return self.custom_theme
        return COLOR_THEMES.get(theme_name, COLOR_THEMES['default'])
    
    def update_custom_theme_color(self, color_key, color_value):
        """Update a single color in the custom theme."""
        custom = self.custom_theme
        if custom is None:
            custom = copy.deepcopy(COLOR_THEMES['default'])
        custom[color_key] = color_value
        self.custom_theme = custom
    
    def reset_custom_theme(self):
        """Reset custom theme to default values."""
        self.custom_theme = copy.deepcopy(COLOR_THEMES['default'])
        self.custom_theme['name'] = 'Custom'
    
    def get_settings_directory(self):
        """Return the directory where settings are stored."""
        return os.path.dirname(self._get_settings_path())


# Singleton instance
settings_manager = SettingsManager()
