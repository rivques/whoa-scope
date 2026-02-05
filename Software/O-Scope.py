
from kivy.config import Config
Config.set('kivy', 'exit_on_escape', '0')
Config.set('graphics', 'width', 1200)
Config.set('graphics', 'height', 800)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # Disable red touch dots on right-click

# Initialize settings early to get preferences before UI loads
from settings_manager import settings_manager, AVAILABLE_FONTS, get_font_path, COLOR_THEMES, AVAILABLE_THEMES
settings_manager.initialize()

# Register all available fonts with Kivy
from kivy.core.text import LabelBase
for font_name, font_path in AVAILABLE_FONTS.items():
    try:
        LabelBase.register(font_name, font_path)
    except Exception as e:
        print(f"Warning: Could not register font '{font_name}': {e}")

from kvplot import Plot
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.spinner import SpinnerOption
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior, ToggleButtonBehavior
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.utils import get_color_from_hex
from kivy.graphics import *
from kivy.animation import Animation
from kivy.factory import Factory
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.utils import platform

import numpy as np
import sigfig
import math
import oscope
import os, pathlib, sys
import kivy.resources as kivy_resources
import serial.tools.list_ports as list_ports

import toml
from pathlib import Path



if getattr(sys, 'frozen', False):
    kivy_resources.resource_add_path(sys._MEIPASS)
    kivy_resources.resource_add_path(os.path.join(sys._MEIPASS, 'resources'))
    pyproject = toml.loads(Path(os.path.join(sys._MEIPASS, "pyproject.toml")).read_text())
else:
    kivy_resources.resource_add_path(os.getcwd())
    kivy_resources.resource_add_path(os.path.join(os.getcwd(), 'resources'))
    pyproject = toml.loads(Path("pyproject.toml").read_text())

__version__ = pyproject["project"]["version"]


class TooltipBehavior:
    """
    Mixin class that provides tooltip functionality for widgets.
    
    When the mouse hovers over a widget with this behavior for a short delay,
    a tooltip with descriptive text will appear near the cursor.
    
    Usage:
        class MyButton(TooltipBehavior, Button):
            pass
        
        # In KV:
        MyButton:
            tooltip_text: 'Click to do something'
    """
    
    # Tooltip text to display
    tooltip_text = StringProperty('')
    
    # Delay before showing tooltip (in seconds)
    tooltip_delay = NumericProperty(0.5)
    
    # Internal references
    _tooltip_widget = None
    _tooltip_show_event = None
    _is_hovering = False
    
    def __init__(self, **kwargs):
        super(TooltipBehavior, self).__init__(**kwargs)
        # Bind to window mouse position
        Window.bind(mouse_pos=self._on_mouse_pos)
    
    def _on_mouse_pos(self, window, pos):
        """Track mouse position to detect hover state."""
        if not self.get_root_window():
            return
        
        # Check if mouse is over this widget
        is_over = self.collide_point(*self.to_widget(*pos))
        
        if is_over and not self._is_hovering:
            # Mouse just entered the widget
            self._is_hovering = True
            self._schedule_tooltip_show()
        elif not is_over and self._is_hovering:
            # Mouse just left the widget
            self._is_hovering = False
            self._cancel_tooltip()
            self._hide_tooltip()
    
    def _schedule_tooltip_show(self):
        """Schedule the tooltip to be shown after a delay."""
        self._cancel_tooltip()
        if self.tooltip_text:
            self._tooltip_show_event = Clock.schedule_once(
                self._show_tooltip, settings_manager.tooltip_delay
            )
    
    def _cancel_tooltip(self):
        """Cancel any scheduled tooltip show."""
        if self._tooltip_show_event:
            self._tooltip_show_event.cancel()
            self._tooltip_show_event = None
    
    def _show_tooltip(self, dt):
        """Display the tooltip widget."""
        if not self.tooltip_text or not self._is_hovering:
            return
        
        # Hide any existing tooltip
        self._hide_tooltip()
        
        # Get theme colors
        theme = settings_manager.get_current_theme()
        bg_color = theme.get('tooltip_background', [0.2, 0.2, 0.2, 0.95])
        text_color = theme.get('tooltip_text_color', [1.0, 1.0, 1.0, 1.0])
        
        # Create tooltip label
        tooltip = TooltipLabel(
            text=self.tooltip_text,
            bg_color=bg_color,
            text_color=text_color
        )
        
        # Position the tooltip near the mouse cursor
        mouse_pos = Window.mouse_pos
        
        # Add to window
        Window.add_widget(tooltip)
        
        # Calculate position after the widget has been added (so size is computed)
        # Position above and to the right of cursor, but keep within window bounds
        x = mouse_pos[0] + 10
        y = mouse_pos[1] + 10
        
        # Schedule position update after size is calculated
        def update_pos(dt):
            # Keep tooltip within window bounds
            if x + tooltip.width > Window.width:
                tooltip.x = Window.width - tooltip.width - 5
            else:
                tooltip.x = x
            
            if y + tooltip.height > Window.height:
                tooltip.y = mouse_pos[1] - tooltip.height - 10
            else:
                tooltip.y = y
        
        tooltip.x = x
        tooltip.y = y
        Clock.schedule_once(update_pos, 0)
        
        self._tooltip_widget = tooltip
    
    def _hide_tooltip(self):
        """Hide and remove the tooltip widget."""
        if self._tooltip_widget:
            try:
                Window.remove_widget(self._tooltip_widget)
            except:
                pass
            self._tooltip_widget = None
    
    def on_disabled(self, instance, value):
        """Hide tooltip when widget is disabled."""
        if hasattr(super(), 'on_disabled'):
            super().on_disabled(instance, value)
        if value:
            self._cancel_tooltip()
            self._hide_tooltip()


class TooltipLabel(Label):
    """
    A styled label widget used to display tooltip text.
    Automatically sizes to fit content and has themed background.
    """
    
    bg_color = ListProperty([0.2, 0.2, 0.2, 0.95])
    text_color = ListProperty([1.0, 1.0, 1.0, 1.0])
    
    def __init__(self, **kwargs):
        # Extract our custom properties before passing to super
        bg = kwargs.pop('bg_color', [0.2, 0.2, 0.2, 0.95])
        tc = kwargs.pop('text_color', [1.0, 1.0, 1.0, 1.0])
        
        super(TooltipLabel, self).__init__(**kwargs)
        
        self.bg_color = bg
        self.color = tc
        self.size_hint = (None, None)
        self.padding = [8, 4]
        self.font_size = int(14 * App.get_running_app().fontscale)
        
        # Bind size to texture size
        self.bind(texture_size=self._update_size)
        self._update_size()
        
        # Draw background
        with self.canvas.before:
            Color(*self.bg_color)
            self._bg_rect = SmoothRoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[5]
            )
        
        self.bind(pos=self._update_bg, size=self._update_bg)
    
    def _update_size(self, *args):
        """Update widget size to fit text content."""
        self.size = (
            self.texture_size[0] + self.padding[0] * 2,
            self.texture_size[1] + self.padding[1] * 2
        )
    
    def _update_bg(self, *args):
        """Update background rectangle position and size."""
        if hasattr(self, '_bg_rect'):
            self._bg_rect.pos = self.pos
            self._bg_rect.size = self.size


class SettingsDialog(Popup):
    """Settings dialog with keyboard support for escape key."""
    
    def __init__(self, **kwargs):
        super(SettingsDialog, self).__init__(**kwargs)
        self._keyboard = None
    
    def on_open(self):
        # Request keyboard
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        if self._keyboard:
            self._keyboard.bind(on_key_down=self._on_keyboard_down)
        
        # Start live updates
        app.start_settings_updates(self.ids.connection_label, self.ids.ports_label)
    
    def on_dismiss(self):
        # Stop live updates
        app.stop_settings_updates()
        
        # Unbind keyboard
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None
        
        # Rebind main keyboard and update visibility flag
        try:
            app.root.bind_keyboard()
        except:
            pass
        app.settings_dialog_visible = False
    
    def _keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None
    
    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'escape':
            self.dismiss()
            return True
        return False


class ThemeSpinnerOption(SpinnerOption):
    """Custom spinner option that shows theme name with color swatches inline."""
    
    def __init__(self, **kwargs):
        super(ThemeSpinnerOption, self).__init__(**kwargs)
        self.halign = 'left'
        self.valign = 'middle'
        self.bind(size=self._update_text_size)
        self.bind(text=self._rebuild_with_swatches)
        Clock.schedule_once(self._rebuild_with_swatches, 0)
    
    def _update_text_size(self, *args):
        self.text_size = (self.width * 0.4, self.height)
    
    def _rebuild_with_swatches(self, *args):
        """Redraw with color swatches after the text."""
        # Draw color swatches on the canvas
        self.canvas.after.clear()
        
        theme_name = self.text
        if theme_name in COLOR_THEMES:
            theme = COLOR_THEMES[theme_name]
        elif theme_name == 'custom':
            theme = settings_manager.custom_theme or COLOR_THEMES['default']
        else:
            return
        
        # Create color swatches
        colors_to_show = ['ch1_color', 'ch2_color', 'axes_background', 'grid_color']
        swatch_width = 18
        swatch_height = self.height * 0.6
        start_x = self.x + self.width * 0.45
        y = self.y + (self.height - swatch_height) / 2
        
        with self.canvas.after:
            for i, color_key in enumerate(colors_to_show):
                color_value = theme.get(color_key, '#FFFFFF')
                if isinstance(color_value, str):
                    Color(*get_color_from_hex(color_value))
                else:
                    Color(*color_value)
                Rectangle(pos=(start_x + i * (swatch_width + 2), y), size=(swatch_width, swatch_height))
                Color(0.5, 0.5, 0.5, 1)
                Line(rectangle=[start_x + i * (swatch_width + 2), y, swatch_width, swatch_height], width=1)
    
    def on_size(self, *args):
        self._rebuild_with_swatches()
    
    def on_pos(self, *args):
        self._rebuild_with_swatches()


class ThemePreviewWidget(BoxLayout):
    """Widget that shows color swatches for a theme preview."""
    theme_name = StringProperty('')
    
    def __init__(self, **kwargs):
        super(ThemePreviewWidget, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.spacing = 2
        self.padding = [2, 2, 2, 2]
    
    def on_theme_name(self, instance, value):
        """Update swatches when theme name changes."""
        self.clear_widgets()
        if value and value in COLOR_THEMES:
            theme = COLOR_THEMES[value]
        elif value == 'custom':
            theme = settings_manager.custom_theme or COLOR_THEMES['default']
        else:
            return
        
        # Create color swatches for CH1, CH2, background, and grid
        colors_to_show = [
            ('ch1_color', 'CH1'),
            ('ch2_color', 'CH2'),
            ('axes_background', 'BG'),
            ('grid_color', 'Grid'),
        ]
        
        for color_key, label in colors_to_show:
            color_value = theme.get(color_key, '#FFFFFF')
            swatch = Widget(size_hint=(None, 1), width=20)
            with swatch.canvas:
                if isinstance(color_value, str):
                    Color(*get_color_from_hex(color_value))
                else:
                    Color(*color_value)
                swatch._rect = Rectangle(pos=swatch.pos, size=swatch.size)
            swatch.bind(pos=self._update_rect, size=self._update_rect)
            self.add_widget(swatch)
    
    def _update_rect(self, instance, value):
        if hasattr(instance, '_rect'):
            instance._rect.pos = instance.pos
            instance._rect.size = instance.size


class ColorPickerButton(ButtonBehavior, Widget):
    """A button that shows a color and opens a color picker when clicked."""
    color_value = StringProperty('#FFFFFF')
    color_key = StringProperty('')
    
    def __init__(self, **kwargs):
        super(ColorPickerButton, self).__init__(**kwargs)
        self._update_color()
    
    def on_color_value(self, instance, value):
        self._update_color()
    
    def _update_color(self):
        self.canvas.clear()
        with self.canvas:
            if self.color_value.startswith('#'):
                Color(*get_color_from_hex(self.color_value))
            else:
                Color(1, 1, 1, 1)
            self._rect = Rectangle(pos=self.pos, size=self.size)
            Color(0.5, 0.5, 0.5, 1)
            Line(rectangle=[self.pos[0], self.pos[1], self.size[0], self.size[1]], width=1)
        self.bind(pos=self._update_rect, size=self._update_rect)
    
    def _update_rect(self, *args):
        if hasattr(self, '_rect'):
            self._rect.pos = self.pos
            self._rect.size = self.size
    
    def on_release(self):
        """Open color picker popup."""
        if self.color_key:
            app.open_color_picker(self.color_key, self.color_value, self._on_color_selected)
    
    def _on_color_selected(self, color_hex):
        """Called when a color is selected from the picker."""
        self.color_value = color_hex


# Register custom widgets with Factory before loading kv file
Factory.register('SettingsDialog', cls=SettingsDialog)
Factory.register('ThemeSpinnerOption', cls=ThemeSpinnerOption)
Factory.register('ThemePreviewWidget', cls=ThemePreviewWidget)
Factory.register('ColorPickerButton', cls=ColorPickerButton)

Builder.load_file('scopeui.kv')


class DisplayLabel(Label):

    bkgnd_color = ListProperty([0., 0., 0.])

class DisplayLabelAlt(Label):

    bkgnd_color = ListProperty([0., 0., 0., 0.])

class DisplayToggleButton(ToggleButton, TooltipBehavior):

    bkgnd_color = ListProperty([0.345, 0.345, 0.345])

    def __init__(self, **kwargs):
        super(DisplayToggleButton, self).__init__(**kwargs)
        theme = settings_manager.get_current_theme()
        self.bkgnd_color = theme['button_normal']

    def on_state(self, widget, value):
        theme = settings_manager.get_current_theme()
        if self.disabled:
            if value == 'down':
                self.bkgnd_color = theme['button_pressed']
            else:
                self.bkgnd_color = theme['button_normal']
        else:
            self.bkgnd_color = theme['button_normal']

class ImageButton(ButtonBehavior, TooltipBehavior, Image):

    bkgnd_color = ListProperty([0.345, 0.345, 0.345])

    def __init__(self, **kwargs):
        super(ImageButton, self).__init__(**kwargs)
        theme = settings_manager.get_current_theme()
        self.bkgnd_color = theme['button_normal']

    def on_state(self, widget, value):
        theme = settings_manager.get_current_theme()
        if value == 'down':
            self.bkgnd_color = theme['button_pressed']
        else:
            self.bkgnd_color = theme['button_normal']

class AltImageButton(ButtonBehavior, TooltipBehavior, Image):

    bkgnd_color = ListProperty([0.03125, 0.03125, 0.03125, 0.8])

    def __init__(self, **kwargs):
        super(AltImageButton, self).__init__(**kwargs)
        theme = settings_manager.get_current_theme()
        self.bkgnd_color = theme['panel_background']

class ImageToggleButton(ToggleButtonBehavior, TooltipBehavior, Image):

    bkgnd_color = ListProperty([0.345, 0.345, 0.345])

    def __init__(self, **kwargs):
        super(ImageToggleButton, self).__init__(**kwargs)
        theme = settings_manager.get_current_theme()
        self.bkgnd_color = theme['button_normal']

    def on_state(self, widget, value):
        theme = settings_manager.get_current_theme()
        if value == 'down':
            self.bkgnd_color = theme['button_pressed']
        else:
            self.bkgnd_color = theme['button_normal']

class AltImageToggleButton(ToggleButtonBehavior, TooltipBehavior, Image):

    bkgnd_color = ListProperty([0.03125, 0.03125, 0.03125, 0.8])
    normal_source = StringProperty('')
    down_source = StringProperty('')

    def on_state(self, widget, value):
        if value == 'down':
            self.source = self.down_source
        else:
            self.source = self.normal_source
        self.reload()

class ImageSpinButton(ButtonBehavior, TooltipBehavior, Image):

    bkgnd_color = ListProperty([0.345, 0.345, 0.345])
    index = NumericProperty(0)
    sources = ListProperty([])
    actions = ListProperty([])

    def __init__(self, **kwargs):
        super(ImageSpinButton, self).__init__(**kwargs)
        theme = settings_manager.get_current_theme()
        self.bkgnd_color = theme['button_normal']
        

    def on_state(self, widget, value):
        theme = settings_manager.get_current_theme()
        if value == 'down':
            self.bkgnd_color = theme['button_pressed']
        else:
            self.bkgnd_color = theme['button_normal']

    def on_release(self):
        self.index += 1
        if self.index >= len(self.sources):
            self.index = 0
        self.source = self.sources[self.index]
        try:
            self.actions[self.index]()
        except TypeError:
            pass
        

class LabelSpinButton(ButtonBehavior, TooltipBehavior, Label):

    bkgnd_color = ListProperty([0.345, 0.345, 0.345])
    index = NumericProperty(0)
    texts = ListProperty([])
    actions = ListProperty([])

    def __init__(self, **kwargs):
        super(LabelSpinButton, self).__init__(**kwargs)
        theme = settings_manager.get_current_theme()
        self.bkgnd_color = theme['button_normal']

    def on_state(self, widget, value):
        theme = settings_manager.get_current_theme()
        if value == 'down':
            self.bkgnd_color = theme['button_pressed']
        else:
            self.bkgnd_color = theme['button_normal']

    def on_release(self):
        self.index += 1
        if self.index >= len(self.texts):
            self.index = 0
        self.text = self.texts[self.index]
        try:
            self.actions[self.index]()
        except TypeError:
            pass

class LinearSlider(BoxLayout):

    minimum = NumericProperty(1.)
    maximum = NumericProperty(100.)
    initial_value = NumericProperty(10.)
    value = NumericProperty()
    step = NumericProperty(0.)
    label_text = StringProperty('')
    units = StringProperty('')

class LogarithmicSlider(BoxLayout):

    minimum = NumericProperty(1.)
    maximum = NumericProperty(100.)
    initial_value = NumericProperty(10.)
    value = NumericProperty()
    label_text = StringProperty('')
    units = StringProperty('')

    def nearest_one_two_five(self, x):
        exponent = math.floor(x)
        mantissa = x - exponent
        if mantissa < math.log10(math.sqrt(2.)):
            mantissa = 0.
        elif mantissa < math.log10(math.sqrt(10.)):
            mantissa = math.log10(2.)
        elif mantissa < math.log10(math.sqrt(50.)):
            mantissa = math.log10(5.)
        else:
            mantissa = 0.
            exponent += 1.
        return exponent + mantissa

class ScopePlot(Plot):

    def __init__(self, **kwargs):
        super(ScopePlot, self).__init__(**kwargs)

        self.update_job = None

        self.grid_state = 'on'

        self.default_color_order = ('c', 'm', 'y', 'b', 'g', 'r')
        self.default_marker = ''

        self.trigger_mode = 'Single'
        self.trigger_level = 0.
        self.trigger_source = 'CH1'
        self.trigger_edge = 'Rising'
        self.triggered = False
        self.trigger_repeat = False

        self.sweep_in_progress = 0
        self.samples_left = app.dev.SCOPE_BUFFER_SIZE // 2

        self.volts_per_lsb = (5e-3, 1e-3)
        self.voltage_ranges = (u':\xB110V', u':\xB12V') 

        self.show_sampling_rate = True
        self.sampling_rate_display = 'Not connected'

        self.show_h_cursors = False
        self.show_v_cursors = False

        self.dragging_ch1_zero_point = False
        self.dragging_ch2_zero_point = False
        self.dragging_trigger_point = False
        self.dragging_trigger_level = False
        self.dragging_h_cursor1 = False
        self.dragging_h_cursor2 = False
        self.dragging_v_cursor1 = False
        self.dragging_v_cursor2 = False
        self.pressing_chs_display = False
        self.CONTROL_PT_THRESHOLD = 60.

        self.xaxis_mode = 'linear'
        self.xlimits_mode = 'manual'
        self.xlim = [-1e-3, 1e-3]
        self.xmin = -1e-3
        self.xmax = 1e-3
        self.xaxis_units = 's'

        self.h_cursor1 = 0.
        self.h_cursor2 = 0.

        # Get theme colors
        theme = settings_manager.get_current_theme()
        
        # Add CH1/CH2 colors to the plot's color dict for curve rendering
        self.colors['ch1'] = theme['ch1_color']
        self.colors['ch2'] = theme['ch2_color']

        self.yaxes['left'].color = theme['axes_color']
        self.yaxes['left'].yaxis_mode = 'linear'
        self.yaxes['left'].ylimits_mode = 'manual'
        self.yaxes['left'].ylim = [0., 5.]

        self.yaxes['CH1'] = self.y_axis(name = 'CH1', color = theme['ch1_color'], units = 'V', yaxis_mode = 'linear', ylimits_mode = 'manual', ylim = [-10., 10.])
        self.yaxes['CH1'].v_cursor1 = 0.
        self.yaxes['CH1'].v_cursor2 = 0.

        self.yaxes['CH2'] = self.y_axis(name = 'CH2', color = theme['ch2_color'], units = 'V', yaxis_mode = 'linear', ylimits_mode = 'manual', ylim = [-10., 10.])
        self.yaxes['CH2'].v_cursor1 = 0.
        self.yaxes['CH2'].v_cursor2 = 0.

        self.left_yaxis = 'CH1'

        self.ch1_display = u'CH1:\xB110V'
        self.ch2_display = u'CH2:\xB110V'

        self.curves['CH1'] = self.curve(name = 'CH1', yaxis = 'CH1', curve_color = 'ch1', curve_style = '-')
        self.curves['CH2'] = self.curve(name = 'CH2', yaxis = 'CH2', curve_color = 'ch2', curve_style = '-')

        self.configure(background = theme['plot_background'], axes_background = theme['axes_background'], 
                       axes_color = theme['axes_color'], grid_color = theme['grid_color'], 
                       fontsize = int(18 * app.fontscale), font = app.fontname, linear_minor_ticks = 'on')

        self.refresh_plot()

    def on_oscope_disconnect(self):
        if self.update_job is not None:
            self.update_job.cancel()
            self.update_job = None

        self.trigger_mode = 'Single'

        self.show_sampling_rate = True
        self.sampling_rate_display = 'Not connected'
        self.refresh_plot()

    def draw_plot(self):
        super(ScopePlot, self).draw_plot()
        self.draw_zero_levels()
        self.draw_trigger_point()
        self.draw_trigger_level()
        self.draw_v_cursors()
        self.draw_h_cursors()
        self.draw_chs_display()
        if self.show_sampling_rate and (self.sampling_rate_display != ''):
            self.add_text(text = self.sampling_rate_display, anchor_pos = [self.axes_right, self.axes_bottom - 3 * self.label_fontsize], anchor = 'se', color = self.axes_color, font_size = self.label_fontsize)

    def draw_zero_levels(self, r = 2.):
        for name in ('CH2', 'CH1') if self.left_yaxis == 'CH1' else ('CH1', 'CH2'):
            yaxis = self.yaxes[name]
            self.canvas.add(Color(*get_color_from_hex(yaxis.color)))
            if (0. > yaxis.ylim[0] - yaxis.y_epsilon) and (0. < yaxis.ylim[1] + yaxis.y_epsilon):
                y = self.to_canvas_y(0., name)
                self.canvas.add(Mesh(vertices = [self.axes_left + r * self.tick_length, y, 0., 0., self.axes_left, y - r * self.tick_length, 0., 0., self.axes_left, y + r * self.tick_length, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
            elif 0. < yaxis.ylim[0]:
                self.canvas.add(Mesh(vertices = [self.axes_left, self.axes_bottom - r * self.tick_length, 0., 0., self.axes_left - r * self.tick_length, self.axes_bottom, 0., 0., self.axes_left + r * self.tick_length, self.axes_bottom, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
            elif 0. > yaxis.ylim[1]:
                self.canvas.add(Mesh(vertices = [self.axes_left, self.axes_top + r * self.tick_length, 0., 0., self.axes_left + r * self.tick_length, self.axes_top, 0., 0., self.axes_left - r * self.tick_length, self.axes_top, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))

    def draw_trigger_point(self, r = 2.):
        if self.triggered:
            self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
            if (0. > self.xlim[0] - self.x_epsilon) and (0. < self.xlim[1] + self.x_epsilon):
                x = self.to_canvas_x(0.)
                self.canvas.add(Mesh(vertices = [x, self.axes_top - r * self.tick_length, 0., 0., x - r * self.tick_length, self.axes_top, 0., 0., x + r * self.tick_length, self.axes_top, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
            elif 0. < self.xlim[0]:
                self.canvas.add(Mesh(vertices = [self.axes_left - r * self.tick_length, self.axes_top, 0., 0., self.axes_left, self.axes_top + r * self.tick_length, 0., 0., self.axes_left, self.axes_top - r * self.tick_length, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
            elif 0. > self.xlim[1]:
                self.canvas.add(Mesh(vertices = [self.axes_right + r * self.tick_length, self.axes_top, 0., 0., self.axes_right, self.axes_top - r * self.tick_length, 0., 0., self.axes_right, self.axes_top + r * self.tick_length, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))

    def draw_trigger_level(self, r = 2.):
        if self.trigger_source != '':
            yaxis = self.yaxes[self.trigger_source]
            self.canvas.add(Color(*get_color_from_hex(yaxis.color)))
            if (self.trigger_level > yaxis.ylim[0] - yaxis.y_epsilon) and (self.trigger_level < yaxis.ylim[1] + yaxis.y_epsilon):
                y = self.to_canvas_y(self.trigger_level, yaxis.name)
                self.canvas.add(Mesh(vertices = [self.axes_right - r * self.tick_length, y, 0., 0., self.axes_right, y + r * self.tick_length, 0., 0., self.axes_right, y - r * self.tick_length, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
                if self.dragging_trigger_level:
                    self.add_text(text = app.num2str(self.trigger_level, 4) + 'V', anchor_pos = [self.axes_right + 0.5 * self.label_fontsize, y], anchor = 'w', color = yaxis.color, font_size = self.label_fontsize)
            elif self.trigger_level < yaxis.ylim[0]:
                self.canvas.add(Mesh(vertices = [self.axes_right, self.axes_bottom - r * self.tick_length, 0., 0., self.axes_right - r * self.tick_length, self.axes_bottom, 0., 0., self.axes_right + r * self.tick_length, self.axes_bottom, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
            elif self.trigger_level > yaxis.ylim[1]:
                self.canvas.add(Mesh(vertices = [self.axes_right, self.axes_top + r * self.tick_length, 0., 0., self.axes_right + r * self.tick_length, self.axes_top, 0., 0., self.axes_right - r * self.tick_length, self.axes_top, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))

    def draw_v_cursors(self):
        if self.show_v_cursors:
            yaxis = self.yaxes[self.left_yaxis]
            cursor1_visible = False
            cursor2_visible = False
            if (yaxis.v_cursor1 > yaxis.ylim[0] - yaxis.y_epsilon) and (yaxis.v_cursor1 < yaxis.ylim[1] + yaxis.y_epsilon):
                y = self.to_canvas_y(yaxis.v_cursor1, self.left_yaxis)
                self.canvas.add(Color(*get_color_from_hex(yaxis.color)))
                self.canvas.add(Line(points = [self.axes_left, y, self.axes_right, y], width = self.tick_lineweight))
                cursor1_visible = True
            if (yaxis.v_cursor2 > yaxis.ylim[0] - yaxis.y_epsilon) and (yaxis.v_cursor2 < yaxis.ylim[1] + yaxis.y_epsilon):
                y = self.to_canvas_y(yaxis.v_cursor2, self.left_yaxis)
                self.canvas.add(Color(*get_color_from_hex(yaxis.color)))
                self.canvas.add(Line(points = [self.axes_left, y, self.axes_right, y], width = self.tick_lineweight))
                cursor2_visible = True
            if cursor1_visible and cursor2_visible:
                delta_display  = app.num2str(abs(yaxis.v_cursor1 - yaxis.v_cursor2), 4) + 'V'
                y = self.to_canvas_y(0.5 * (yaxis.v_cursor1 + yaxis.v_cursor2), self.left_yaxis)
                self.add_text(text = delta_display, anchor_pos = [self.axes_right + 0.5 * self.label_fontsize, y], anchor = 'w', color = yaxis.color, font_size = self.label_fontsize)

    def draw_h_cursors(self):
        if self.show_h_cursors:
            cursor1_visible = False
            cursor2_visible = False
            if (self.h_cursor1 > self.xlim[0] - self.x_epsilon) and (self.h_cursor1 < self.xlim[1] + self.x_epsilon):
                x = self.to_canvas_x(self.h_cursor1)
                self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
                self.canvas.add(Line(points = [x, self.axes_top, x, self.axes_bottom], width = self.tick_lineweight))
                cursor1_visible = True
            if (self.h_cursor2 > self.xlim[0] - self.x_epsilon) and (self.h_cursor2 < self.xlim[1] + self.x_epsilon):
                x = self.to_canvas_x(self.h_cursor2)
                self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
                self.canvas.add(Line(points = [x, self.axes_top, x, self.axes_bottom], width = self.tick_lineweight))
                cursor2_visible = True
            if cursor1_visible and cursor2_visible:
                delta_display  = app.num2str(abs(self.h_cursor1 - self.h_cursor2), 4) + 's'
                x = max(self.to_canvas_x(0.5 * (self.h_cursor1 + self.h_cursor2)), self.axes_left + 12.5 * self.label_fontsize)
                self.add_text(text = delta_display, anchor_pos = [x, self.axes_top + 0.5 * self.label_fontsize], anchor = 's', color = self.axes_color, font_size = self.label_fontsize)

    def draw_chs_display(self):
        if self.left_yaxis == 'CH1':
            self.canvas.add(Color(*get_color_from_hex(self.yaxes['CH1'].color)))
            self.canvas.add(Rectangle(pos = [self.axes_left, self.axes_top + 3.], size = [5. * self.label_fontsize - 2., 2. * self.label_fontsize - 1.]))
            self.canvas.add(Line(rectangle = [self.axes_left, self.axes_top + 3., 5. * self.label_fontsize - 2., 2. * self.label_fontsize - 1.]))
            self.add_text(text = self.ch1_display, anchor_pos = [self.axes_left + 2.5 * self.label_fontsize, self.axes_top + 0.5 * self.label_fontsize], anchor = 's', color = self.axes_background_color, font_size = self.label_fontsize)
            self.canvas.add(Color(*get_color_from_hex(self.yaxes['CH2'].color)))
            self.canvas.add(Line(rectangle = [self.axes_left + 5. * self.label_fontsize, self.axes_top + 3., 5. * self.label_fontsize - 2., 2. * self.label_fontsize - 1.]))
            self.add_text(text = self.ch2_display, anchor_pos = [self.axes_left + 7.5 * self.label_fontsize, self.axes_top + 0.5 * self.label_fontsize], anchor = 's', color = self.yaxes['CH2'].color, font_size = self.label_fontsize)
        else:
            self.canvas.add(Color(*get_color_from_hex(self.yaxes['CH1'].color)))
            self.canvas.add(Line(rectangle = [self.axes_left, self.axes_top + 3., 5. * self.label_fontsize - 2., 2. * self.label_fontsize - 1.]))
            self.add_text(text = self.ch1_display, anchor_pos = [self.axes_left + 2.5 * self.label_fontsize, self.axes_top + 0.5 * self.label_fontsize], anchor = 's', color = self.yaxes['CH1'].color, font_size = self.label_fontsize)
            self.canvas.add(Color(*get_color_from_hex(self.yaxes['CH2'].color)))
            self.canvas.add(Rectangle(pos = [self.axes_left + 5. * self.label_fontsize, self.axes_top + 3.], size = [5. * self.label_fontsize - 2., 2. * self.label_fontsize - 1.]))
            self.canvas.add(Line(rectangle = [self.axes_left + 5. * self.label_fontsize, self.axes_top + 3., 5. * self.label_fontsize - 2., 2. * self.label_fontsize - 1.]))
            self.add_text(text = self.ch2_display, anchor_pos = [self.axes_left + 7.5 * self.label_fontsize, self.axes_top + 0.5 * self.label_fontsize], anchor = 's', color = self.axes_background_color, font_size = self.label_fontsize)

    def update_scope_plot(self, t):
        if not app.dev.connected:
            return

        try:
            sampling_interval = app.dev.sampling_interval

            ch1_range = app.dev.ch1_range
            ch2_range = app.dev.ch2_range

            self.ch1_display = 'CH1' + self.voltage_ranges[ch1_range]
            self.ch2_display = 'CH2' + self.voltage_ranges[ch2_range]

            if self.show_sampling_rate:
                sampling_rate = 1. / sampling_interval
                self.sampling_rate_display = app.num2str(sampling_rate, 4) + 'S/s'
                acquire_modes = ('SAMP', 'AVG02', 'AVG04', 'AVG08', 'AVG16')
                self.sampling_rate_display = acquire_modes[app.dev.num_avg] + ', ' + self.sampling_rate_display

            if sampling_interval == 0.25e-6:
                ch1_zero = app.dev.ch1_zero_4MSps[ch1_range]
                ch1_gain = app.dev.ch1_gain_4MSps[ch1_range]
                ch2_zero = app.dev.ch2_zero_4MSps[ch2_range]
                ch2_gain = app.dev.ch2_gain_4MSps[ch2_range]
            else:
                ch1_zero = app.dev.ch1_zero[app.dev.num_avg][ch1_range]
                ch1_gain = app.dev.ch1_gain[app.dev.num_avg][ch1_range]
                ch2_zero = app.dev.ch2_zero[app.dev.num_avg][ch2_range]
                ch2_gain = app.dev.ch2_gain[app.dev.num_avg][ch2_range]

            num_samples = app.dev.SCOPE_BUFFER_SIZE // 2

            if self.trigger_mode == 'Continuous':
                scope_buffer = app.dev.trigger()
            elif self.trigger_mode == 'Armed':
                scope_buffer = app.dev.trigger()
                self.trigger_mode = 'Single'
            else:
                scope_buffer = app.dev.get_bufferbin()
                if not app.dev.sweep_in_progress():
                    app.root.scope.play_pause_button.source = kivy_resources.resource_find('play.png')
                    app.root.scope.play_pause_button.reload()
                    self.trigger_mode = 'Single'

            ch1_vals = np.array(scope_buffer[0:num_samples])
            ch2_vals = np.array(scope_buffer[num_samples:])

            [self.sweep_in_progress, self.samples_left] = app.dev.get_sweep_progress()
            if (self.sweep_in_progress == 1) and (sampling_interval <= 200e-6):
                ch1 = self.curves['CH1'].points_y[0]
                ch2 = self.curves['CH2'].points_y[0]
            else:
                ch1 = self.volts_per_lsb[ch1_range] * ch1_gain * (ch1_vals - ch1_zero)
                ch2 = self.volts_per_lsb[ch2_range] * ch2_gain * (ch2_vals - ch2_zero)

            if self.trigger_source == 'CH1':
                ch = ch1
            else:
                ch = ch2
            if self.trigger_edge == 'Rising':
                triggers = np.where(np.logical_and(ch[0:-1] <= self.trigger_level, ch[1:] > self.trigger_level))[0]
            elif self.trigger_edge == 'Falling':
                triggers = np.where(np.logical_and(ch[0:-1] >= self.trigger_level, ch[1:] < self.trigger_level))[0]
            else:
                triggers = np.array([], dtype = np.int64)

            middle = len(ch) >> 1
            if len(triggers) == 0:
                self.triggered = False
                zero = middle
                offset = 0.
            else:
                self.triggered = True
                zero = triggers[np.argmin(abs(triggers - middle))]
                offset = (self.trigger_level - ch[zero]) / (ch[zero + 1] - ch[zero])

            if self.trigger_source == 'CH1':
                t1 = sampling_interval * (np.arange(num_samples) - zero - offset)
                t2 = sampling_interval * (np.arange(num_samples) - zero - offset) + 0.125e-6
            else:
                t2 = sampling_interval * (np.arange(num_samples) - zero - offset)
                t1 = sampling_interval * (np.arange(num_samples) - zero - offset) - 0.125e-6

            self.curves['CH1'].points_x = [t1]
            self.curves['CH1'].points_y = [ch1]
            self.curves['CH2'].points_x = [t2]
            self.curves['CH2'].points_y = [ch2]

            self.refresh_plot()

            if app.root.scope.meter_visible:
                ch1_mean = float(np.sum(ch1)) / num_samples
                ch2_mean = float(np.sum(ch2)) / num_samples

                ch1_rms = math.sqrt(float(np.sum((ch1 - ch1_mean) ** 2)) / num_samples)
                ch2_rms = math.sqrt(float(np.sum((ch2 - ch2_mean) ** 2)) / num_samples)

                theme = settings_manager.get_current_theme()
                base_meter_text = '[b][color={}]{{}}V[/color]\n[color={}]{{}}V[/color][/b]'.format(theme['ch1_color'], theme['ch2_color'])
                ch1_str = app.num2str(ch1_rms if app.root.scope.meter_ch1rms else ch1_mean, 4, positive_sign=True, trailing_zeros=True)
                ch2_str = app.num2str(ch2_rms if app.root.scope.meter_ch2rms else ch2_mean, 4, positive_sign=True, trailing_zeros=True)
                app.root.scope.meter_label.text = base_meter_text.format(ch1_str, ch2_str)
                

            if app.root.scope.xyplot_visible:
                if app.root.scope.scope_xyplot.ch1_vs_ch2:
                    app.root.scope.scope_xyplot.curves['XY'].points_x = [ch2]
                    app.root.scope.scope_xyplot.curves['XY'].points_y = [ch1]
                else:
                    app.root.scope.scope_xyplot.curves['XY'].points_x = [ch1]
                    app.root.scope.scope_xyplot.curves['XY'].points_y = [ch2]
                app.root.scope.scope_xyplot.refresh_plot()

            self.update_job = Clock.schedule_once(self.update_scope_plot, 0.05)
        except:
            app.disconnect_from_oscope()

    def home_view(self):
        if not app.dev.connected:
            return

        try:
            sampling_interval = app.dev.get_period()
            ch1_range = app.dev.get_ch1range()
            ch2_range = app.dev.get_ch2range()
            self.xlim = [-250. * sampling_interval, 250. * sampling_interval]
            self.yaxes['CH1'].ylim = [-2000. * self.volts_per_lsb[ch1_range], 2000. * self.volts_per_lsb[ch1_range]]
            self.yaxes['CH2'].ylim = [-2000. * self.volts_per_lsb[ch2_range], 2000. * self.volts_per_lsb[ch2_range]]
            self.refresh_plot()
        except:
            app.disconnect_from_oscope()

    def set_sampling_interval(self, interval):
        if not app.dev.connected:
            return

        try:
            app.dev.set_period(interval)
            self.xlim = [-250. * app.dev.sampling_interval, 250. * app.dev.sampling_interval]
            self.refresh_plot()
        except:
            app.disconnect_from_oscope()

    def decrease_sampling_interval(self):
        if app.dev.connected:
            interval = app.dev.sampling_interval
            foo = math.log10(interval)
            bar = math.floor(foo)
            foobar = foo - bar
            if foobar < 0.5 * math.log10(2.001):
                interval = 0.5 * math.pow(10., bar)
            elif foobar < 0.5 * math.log10(2.001 * 5.001):
                interval = math.pow(10., bar)
            elif foobar < 0.5 * math.log10(5.001 * 10.001):
                interval = 2. * math.pow(10., bar)
            else:
                interval = 5. * math.pow(10., bar)
            self.set_sampling_interval(interval)

    def increase_sampling_interval(self):
        if app.dev.connected:
            interval = app.dev.sampling_interval
            foo = math.log10(interval)
            bar = math.floor(foo)
            foobar = foo - bar
            if foobar < 0.5 * math.log10(2.001):
                interval = 2. * math.pow(10., bar)
            elif foobar < 0.5 * math.log10(2.001 * 5.001):
                interval = 5. * math.pow(10., bar)
            elif foobar < 0.5 * math.log10(5.001 * 10.001):
                interval = 10. * math.pow(10., bar)
            else:
                interval = 20. * math.pow(10., bar)
            self.set_sampling_interval(interval)

    def increase_gain(self):
        if not app.dev.connected:
            return

        try:
            if self.left_yaxis == 'CH1':
                gain = app.dev.ch1_range
                app.dev.set_ch1range(gain + 1 if gain < 1 else gain)
            elif self.left_yaxis == 'CH2':
                gain = app.dev.ch2_range
                app.dev.set_ch2range(gain + 1 if gain < 1 else gain)
        except:
            app.disconnect_from_oscope()

    def decrease_gain(self):
        if not app.dev.connected:
            return

        try:
            if self.left_yaxis == 'CH1':
                gain = app.dev.ch1_range
                app.dev.set_ch1range(gain - 1 if gain > 0 else gain)
            elif self.left_yaxis == 'CH2':
                gain = app.dev.ch2_range
                app.dev.set_ch2range(gain - 1 if gain > 0 else gain)
        except:
            app.disconnect_from_oscope()

    def reset_touches(self):
        self.num_touches = 0
        self.touch_positions = []
        self.touch_net_movements = []
        self.looking_for_gesture = True

    def on_touch_down(self, touch):
        if (app.root.scope.xyplot_visible or app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible) and touch.pos[0] < 0.6 * Window.size[0]:
            return

        if (touch.pos[0] < self.canvas_left) or (touch.pos[0] > self.canvas_left + self.canvas_width) or (touch.pos[1] < self.canvas_bottom) or (touch.pos[1] > self.canvas_bottom + self.canvas_height):
            self.looking_for_gesture = False

        self.num_touches += 1
        self.touch_net_movements.append([0., 0.])
        self.touch_positions.append(touch.pos)

        if (self.num_touches == 1):
            if (self.trigger_source != '') and ((touch.pos[0] - self.axes_right) ** 2 + (touch.pos[1] - self.to_canvas_y(self.trigger_level, self.trigger_source)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.dragging_trigger_level = True
            elif (self.left_yaxis == 'CH1') and ((touch.pos[0] - (self.axes_left + 7.5 * self.label_fontsize)) ** 2 + (touch.pos[1] - (self.axes_top + 0.5 * self.label_fontsize)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.pressing_chs_display = True
            elif (self.left_yaxis == 'CH2') and ((touch.pos[0] - (self.axes_left + 2.5 * self.label_fontsize)) ** 2 + (touch.pos[1] - (self.axes_top + 0.5 * self.label_fontsize)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.pressing_chs_display = True
            elif self.triggered and ((touch.pos[0] - self.to_canvas_x(0.)) ** 2 + (touch.pos[1] - self.axes_top) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.dragging_trigger_point = True
            elif self.show_h_cursors and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top) and (abs(touch.pos[0] - self.to_canvas_x(self.h_cursor1)) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_h_cursor1 = True
            elif self.show_h_cursors and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top) and (abs(touch.pos[0] - self.to_canvas_x(self.h_cursor2)) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_h_cursor2 = True
            elif (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (abs(touch.pos[1] - self.axes_bottom) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_trigger_point = True
            elif (self.left_yaxis == 'CH1') and ((touch.pos[0] - self.axes_left) ** 2 + (touch.pos[1] - self.to_canvas_y(0., 'CH2')) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.dragging_ch2_zero_point = True
            elif (self.left_yaxis == 'CH1') and self.show_v_cursors and (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (abs(touch.pos[1] - self.to_canvas_y(self.yaxes['CH1'].v_cursor1, 'CH1')) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_v_cursor1 = True
            elif (self.left_yaxis == 'CH1') and self.show_v_cursors and (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (abs(touch.pos[1] - self.to_canvas_y(self.yaxes['CH1'].v_cursor2, 'CH1')) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_v_cursor2 = True
            elif (self.left_yaxis == 'CH1') and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top) and (abs(touch.pos[0] - self.axes_left) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_ch1_zero_point = True
            elif (self.left_yaxis == 'CH2') and ((touch.pos[0] - self.axes_left) ** 2 + (touch.pos[1] - self.to_canvas_y(0., 'CH1')) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.dragging_ch1_zero_point = True
            elif (self.left_yaxis == 'CH2') and self.show_v_cursors and (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (abs(touch.pos[1] - self.to_canvas_y(self.yaxes['CH2'].v_cursor1, 'CH2')) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_v_cursor1 = True
            elif (self.left_yaxis == 'CH2') and self.show_v_cursors and (touch.pos[0] >= self.axes_left) and (abs(touch.pos[1] - self.to_canvas_y(self.yaxes['CH2'].v_cursor2, 'CH2')) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_v_cursor2 = True
            elif (self.left_yaxis == 'CH2') and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top) and (abs(touch.pos[0] - self.axes_left) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_ch2_zero_point = True

    def on_touch_move(self, touch):
        if app.root.scope.wavegen_visible:
            return

        if (app.root.scope.xyplot_visible or app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible) and touch.pos[0] < 0.6 * Window.size[0]:
            return

        sqr_distances = [(touch.pos[0] - pos[0]) ** 2 + (touch.pos[1] - pos[1]) ** 2 for pos in self.touch_positions]
        try:
            i = min(enumerate(sqr_distances), key = lambda x: x[1])[0]
        except ValueError:
            return

        if i == 0:
            if self.dragging_trigger_level:
                self.trigger_level += self.yaxes[self.trigger_source].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.refresh_plot()
            elif self.dragging_trigger_point:
                dx = self.x_epsilon * (touch.pos[0] - self.touch_positions[i][0])
                self.xlim[0] -= dx
                self.xlim[1] -= dx
                self.refresh_plot()
            elif self.dragging_ch1_zero_point:
                dy = self.yaxes['CH1'].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.yaxes['CH1'].ylim[0] -= dy
                self.yaxes['CH1'].ylim[1] -= dy
                self.refresh_plot()
            elif self.dragging_ch2_zero_point:
                dy = self.yaxes['CH2'].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.yaxes['CH2'].ylim[0] -= dy
                self.yaxes['CH2'].ylim[1] -= dy
                self.refresh_plot()
            elif self.dragging_h_cursor1:
                self.h_cursor1 += self.x_epsilon * (touch.pos[0] - self.touch_positions[i][0])
                self.refresh_plot()
            elif self.dragging_h_cursor2:
                self.h_cursor2 += self.x_epsilon * (touch.pos[0] - self.touch_positions[i][0])
                self.refresh_plot()
            elif self.dragging_v_cursor1:
                self.yaxes[self.left_yaxis].v_cursor1 += self.yaxes[self.left_yaxis].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.refresh_plot()
            elif self.dragging_v_cursor2:
                self.yaxes[self.left_yaxis].v_cursor2 += self.yaxes[self.left_yaxis].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.refresh_plot()

        self.touch_net_movements[i][0] += touch.pos[0] - self.touch_positions[i][0]
        self.touch_net_movements[i][1] += touch.pos[1] - self.touch_positions[i][1]
        self.touch_positions[i] = touch.pos

    def on_touch_up(self, touch):
        if app.root.scope.wavegen_visible:
            return

        if (app.root.scope.xyplot_visible or app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible) and touch.pos[0] < 0.6 * Window.size[0]:
            return

        if self.looking_for_gesture:
            self.looking_for_gesture = False

        if self.dragging_trigger_level:
            self.dragging_trigger_level = False

        if self.dragging_trigger_point:
            self.dragging_trigger_point = False

        if self.dragging_ch1_zero_point:
            self.dragging_ch1_zero_point = False

        if self.dragging_ch2_zero_point:
            self.dragging_ch2_zero_point = False

        if self.dragging_h_cursor1:
            self.dragging_h_cursor1 = False

        if self.dragging_h_cursor2:
            self.dragging_h_cursor2 = False

        if self.dragging_v_cursor1:
            self.dragging_v_cursor1 = False

        if self.dragging_v_cursor2:
            self.dragging_v_cursor2 = False

        if self.pressing_chs_display:
            if (self.left_yaxis == 'CH1') and ((touch.pos[0] - (self.axes_left + 7.5 * self.label_fontsize)) ** 2 + (touch.pos[1] - (self.axes_top + 0.5 * self.label_fontsize)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.left_yaxis = 'CH2'
                self.refresh_plot()
            elif (self.left_yaxis == 'CH2') and ((touch.pos[0] - (self.axes_left + 2.5 * self.label_fontsize)) ** 2 + (touch.pos[1] - (self.axes_top + 0.5 * self.label_fontsize)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.left_yaxis = 'CH1'
                self.refresh_plot()
            self.pressing_chs_display = False

        self.num_touches -= 1
        sqr_distances = [(touch.pos[0] - pos[0]) ** 2 + (touch.pos[1] - pos[1]) ** 2 for pos in self.touch_positions]
        try:
            i = min(enumerate(sqr_distances), key = lambda x: x[1])[0]
            del self.touch_net_movements[i]
            del self.touch_positions[i]
        except ValueError:
            if self.num_touches < 0:
                self.num_touches = 0

        if self.num_touches == 0:
            self.looking_for_gesture = True

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if key == 'up' or key == 'k':
            if 'shift' in modifiers:
                self.pan_up(fraction = 1. / self.axes_height, yaxis = self.left_yaxis)
            elif 'ctrl' in modifiers:
                self.pan_up(fraction = 0.5, yaxis = self.left_yaxis)
            else:
                self.pan_up(yaxis = self.left_yaxis)
        elif key == 'down' or key == 'j':
            if 'shift' in modifiers:
                self.pan_down(fraction = 1. / self.axes_height, yaxis = self.left_yaxis)
            elif 'ctrl' in modifiers:
                self.pan_down(fraction = 0.5, yaxis = self.left_yaxis)
            else:
                self.pan_down(yaxis = self.left_yaxis)
        elif key == 'left' or key == 'h':
            if 'shift' in modifiers:
                self.pan_left(fraction = 1. / self.axes_width)
            elif 'ctrl' in modifiers:
                self.pan_left(fraction = 0.5)
            else:
                self.pan_left()
        elif key == 'right' or key == 'l':
            if 'shift' in modifiers:
                self.pan_right(fraction = 1. / self.axes_width)
            elif 'ctrl' in modifiers:
                self.pan_right(fraction = 0.5)
            else:
                self.pan_right()
        elif key == '=':
            if 'shift' in modifiers:
                self.increase_gain()
            else:
                self.zoom_in_y(yaxis = self.left_yaxis)
        elif key == '-':
            if 'shift' in modifiers:
                self.decrease_gain()
            else:
                self.zoom_out_y(yaxis = self.left_yaxis)
        elif key == ',':
            if 'shift' in modifiers:
                self.increase_sampling_interval()
            else:
                self.zoom_in_x()
        elif key == '.':
            if 'shift' in modifiers:
                self.decrease_sampling_interval()
            else:
                self.zoom_out_x()
        elif key == 'g':
            if self.grid() == 'off':
                self.grid('on')
            else:
                self.grid('off')
        elif key == 'spacebar':
            self.home_view()
        elif key == 'r':
            app.root.scope.set_trigger_edge_rising()
            app.root.scope.trigger_edge_button.index = 0
            app.root.scope.trigger_edge_button.source = app.root.scope.trigger_edge_button.sources[0]
            app.root.scope.trigger_edge_button.reload()
        elif key == 'f':
            app.root.scope.set_trigger_edge_falling()
            app.root.scope.trigger_edge_button.index = 1
            app.root.scope.trigger_edge_button.source = app.root.scope.trigger_edge_button.sources[1]
            app.root.scope.trigger_edge_button.reload()
        elif key == 'x':
            app.root.scope.toggle_h_cursors()
            app.root.scope.h_cursors_button.state = 'down' if app.root.scope.h_cursors_button.state == 'normal' else 'normal'
        elif key == 'y':
            app.root.scope.toggle_v_cursors()
            app.root.scope.v_cursors_button.state = 'down' if app.root.scope.v_cursors_button.state == 'normal' else 'normal'
        elif key == '1':
            if 'shift' in modifiers:
                app.root.scope.set_trigger_src_ch1()
                app.root.scope.trigger_src_button.index = 0
                app.root.scope.trigger_src_button.text = app.root.scope.trigger_src_button.texts[0]
            else:
                self.left_yaxis = 'CH1'
                self.refresh_plot()
        elif key == '2':
            if 'shift' in modifiers:
                app.root.scope.set_trigger_src_ch2()
                app.root.scope.trigger_src_button.index = 1
                app.root.scope.trigger_src_button.text = app.root.scope.trigger_src_button.texts[1]
            else:
                self.left_yaxis = 'CH2'
                self.refresh_plot()
        elif key == '0':
            try:
                app.dev.set_max_avg(0)
            except:
                app.disconnect_from_oscope()
        elif key == '6':
            try:
                app.dev.set_max_avg(1)
            except:
                app.disconnect_from_oscope()
        elif key == '7':
            try:
                app.dev.set_max_avg(2)
            except:
                app.disconnect_from_oscope()
        elif key == '8':
            try:
                app.dev.set_max_avg(3)
            except:
                app.disconnect_from_oscope()
        elif key == '9':
            try:
                app.dev.set_max_avg(4)
            except:
                app.disconnect_from_oscope()
        elif key == 'a':
            if 'shift' in modifiers:
                app.root.scope.meter_ch2rms = True
                app.root.scope.meter_ch2_button.index = 1
                app.root.scope.meter_ch2_button.source = app.root.scope.meter_ch2_button.sources[1]
                app.root.scope.meter_ch2_button.reload()
            else:
                app.root.scope.meter_ch1rms = True
                app.root.scope.meter_ch1_button.index = 1
                app.root.scope.meter_ch1_button.source = app.root.scope.meter_ch1_button.sources[1]
                app.root.scope.meter_ch1_button.reload()
        elif key == 'd':
            if 'shift' in modifiers:
                app.root.scope.meter_ch2rms = False
                app.root.scope.meter_ch2_button.index = 0
                app.root.scope.meter_ch2_button.source = app.root.scope.meter_ch2_button.sources[0]
                app.root.scope.meter_ch2_button.reload()
            else:
                app.root.scope.meter_ch1rms = False
                app.root.scope.meter_ch1_button.index = 0
                app.root.scope.meter_ch1_button.source = app.root.scope.meter_ch1_button.sources[0]
                app.root.scope.meter_ch1_button.reload()

class ScopeXYPlot(Plot):

    def __init__(self, **kwargs):
        super(ScopeXYPlot, self).__init__(**kwargs)

        self.ch1_vs_ch2 = True

        self.grid_state = 'on'

        self.default_color_order = ('c', 'm', 'y', 'b', 'g', 'r')
        self.default_marker = ''

        self.volts_per_lsb = (5e-3, 1e-3)
        self.voltage_ranges = (u':\xB110V', u':\xB12V') 

        self.show_h_cursors = False
        self.show_v_cursors = False

        self.dragging_h_zero_point = False
        self.dragging_v_zero_point = False
        self.dragging_h_cursor1 = False
        self.dragging_h_cursor2 = False
        self.dragging_v_cursor1 = False
        self.dragging_v_cursor2 = False

        self.CONTROL_PT_THRESHOLD = 60.

        # Get theme colors
        theme = settings_manager.get_current_theme()

        self.xaxis_color = theme['ch2_color']
        self.xaxis_mode = 'linear'
        self.xlimits_mode = 'manual'
        self.xlim = [-10., 10.]
        self.xmin = -10.
        self.xmax = 10.
        self.xlabel_value = 'CH2 (V)'
        self.h_cursor1 = 0.
        self.h_cursor2 = 0.

        self.yaxes['left'].color = theme['ch1_color']
        self.yaxes['left'].yaxis_mode = 'linear'
        self.yaxes['left'].ylimits_mode = 'manual'
        self.yaxes['left'].ylim = [-10., 10.]
        self.yaxes['left'].ymin = -10.
        self.yaxes['left'].ymax = 10.
        self.yaxes['left'].ylabel_value = 'CH1 (V)'
        self.yaxes['left'].v_cursor1 = 0.
        self.yaxes['left'].v_cursor2 = 0.

        self.left_yaxis = 'left'
        
        # Add XY color (blend of CH1/CH2) to colors dict
        self.colors['xy'] = theme['phase_color']  # Use phase color (magenta-ish) for XY

        self.curves['XY'] = self.curve(name = 'XY', yaxis = 'left', curve_color = 'xy', curve_style = '-')

        self.configure(background = theme['plot_background'], axes_background = theme['axes_background'], 
                       axes_color = theme['axes_color'], grid_color = theme['grid_color'], 
                       fontsize = int(18 * app.fontscale), font = app.fontname, linear_minor_ticks = 'on')

        self.refresh_plot()

    def draw_plot(self):
        super(ScopeXYPlot, self).draw_plot()
        self.draw_zero_levels()
        self.draw_v_cursors()
        self.draw_h_cursors()

    def draw_zero_levels(self, r = 2.):
        self.canvas.add(Color(*get_color_from_hex(self.xaxis_color)))
        if (0. > self.xlim[0] - self.x_epsilon) and (0. < self.xlim[1] + self.x_epsilon):
            x = self.to_canvas_x(0.)
            self.canvas.add(Mesh(vertices = [x, self.axes_bottom + r * self.tick_length, 0., 0., x - r * self.tick_length, self.axes_bottom, 0., 0., x + r * self.tick_length, self.axes_bottom, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
        elif 0. < self.xlim[0]:
            self.canvas.add(Mesh(vertices = [self.axes_left - r * self.tick_length, self.axes_bottom, 0., 0., self.axes_left, self.axes_bottom + r * self.tick_length, 0., 0., self.axes_left, self.axes_bottom - r * self.tick_length, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
        elif 0. > self.xlim[1]:
            self.canvas.add(Mesh(vertices = [self.axes_right + r * self.tick_length, self.axes_bottom, 0., 0., self.axes_right, self.axes_bottom - r * self.tick_length, 0., 0., self.axes_right, self.axes_bottom + r * self.tick_length, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))

        yaxis = self.yaxes[self.left_yaxis]
        self.canvas.add(Color(*get_color_from_hex(yaxis.color)))
        if (0. > yaxis.ylim[0] - yaxis.y_epsilon) and (0. < yaxis.ylim[1] + yaxis.y_epsilon):
            y = self.to_canvas_y(0., self.left_yaxis)
            self.canvas.add(Mesh(vertices = [self.axes_left + r * self.tick_length, y, 0., 0., self.axes_left, y - r * self.tick_length, 0., 0., self.axes_left, y + r * self.tick_length, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
        elif 0. < yaxis.ylim[0]:
            self.canvas.add(Mesh(vertices = [self.axes_left, self.axes_bottom - r * self.tick_length, 0., 0., self.axes_left - r * self.tick_length, self.axes_bottom, 0., 0., self.axes_left + r * self.tick_length, self.axes_bottom, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))
        elif 0. > yaxis.ylim[1]:
            self.canvas.add(Mesh(vertices = [self.axes_left, self.axes_top + r * self.tick_length, 0., 0., self.axes_left + r * self.tick_length, self.axes_top, 0., 0., self.axes_left - r * self.tick_length, self.axes_top, 0., 0.], indices = [0, 1, 2], mode = 'triangle_fan'))

    def draw_v_cursors(self):
        if self.show_v_cursors:
            yaxis = self.yaxes[self.left_yaxis]
            cursor1_visible = False
            cursor2_visible = False
            if (yaxis.v_cursor1 > yaxis.ylim[0] - yaxis.y_epsilon) and (yaxis.v_cursor1 < yaxis.ylim[1] + yaxis.y_epsilon):
                y = self.to_canvas_y(yaxis.v_cursor1, self.left_yaxis)
                self.canvas.add(Color(*get_color_from_hex(yaxis.color)))
                self.canvas.add(Line(points = [self.axes_left, y, self.axes_right, y], width = self.tick_lineweight))
                cursor1_visible = True
            if (yaxis.v_cursor2 > yaxis.ylim[0] - yaxis.y_epsilon) and (yaxis.v_cursor2 < yaxis.ylim[1] + yaxis.y_epsilon):
                y = self.to_canvas_y(yaxis.v_cursor2, self.left_yaxis)
                self.canvas.add(Color(*get_color_from_hex(yaxis.color)))
                self.canvas.add(Line(points = [self.axes_left, y, self.axes_right, y], width = self.tick_lineweight))
                cursor2_visible = True
            if cursor1_visible and cursor2_visible:
                delta_display  = app.num2str(abs(yaxis.v_cursor1 - yaxis.v_cursor2), 4) + 'V'
                y = min(0.6 * Window.size[1], self.to_canvas_y(0.5 * (yaxis.v_cursor1 + yaxis.v_cursor2), self.left_yaxis))
                self.add_text(text = delta_display, anchor_pos = [self.axes_right + 0.5 * self.label_fontsize, y], anchor = 'w', color = yaxis.color, font_size = self.label_fontsize)

    def draw_h_cursors(self):
        if self.show_h_cursors:
            cursor1_visible = False
            cursor2_visible = False
            if (self.h_cursor1 > self.xlim[0] - self.x_epsilon) and (self.h_cursor1 < self.xlim[1] + self.x_epsilon):
                x = self.to_canvas_x(self.h_cursor1)
                self.canvas.add(Color(*get_color_from_hex(self.xaxis_color)))
                self.canvas.add(Line(points = [x, self.axes_top, x, self.axes_bottom], width = self.tick_lineweight))
                cursor1_visible = True
            if (self.h_cursor2 > self.xlim[0] - self.x_epsilon) and (self.h_cursor2 < self.xlim[1] + self.x_epsilon):
                x = self.to_canvas_x(self.h_cursor2)
                self.canvas.add(Color(*get_color_from_hex(self.xaxis_color)))
                self.canvas.add(Line(points = [x, self.axes_top, x, self.axes_bottom], width = self.tick_lineweight))
                cursor2_visible = True
            if cursor1_visible and cursor2_visible:
                delta_display  = app.num2str(abs(self.h_cursor1 - self.h_cursor2), 4) + 'V'
                x = max(self.to_canvas_x(0.5 * (self.h_cursor1 + self.h_cursor2)), self.axes_left + 6 * self.label_fontsize)
                self.add_text(text = delta_display, anchor_pos = [x, self.axes_top + 0.5 * self.label_fontsize], anchor = 's', color = self.xaxis_color, font_size = self.label_fontsize)

    def home_view(self):
        if not app.dev.connected:
            return

        try:
            ch1_range = app.dev.get_ch1range()
            ch2_range = app.dev.get_ch2range()
            if self.ch1_vs_ch2:
                self.xlim = [-2000. * self.volts_per_lsb[ch2_range], 2000. * self.volts_per_lsb[ch2_range]]
                self.yaxes['left'].ylim = [-2000. * self.volts_per_lsb[ch1_range], 2000. * self.volts_per_lsb[ch1_range]]
            else:
                self.yaxes['left'].ylim = [-2000. * self.volts_per_lsb[ch1_range], 2000. * self.volts_per_lsb[ch1_range]]
                self.xlim = [-2000. * self.volts_per_lsb[ch2_range], 2000. * self.volts_per_lsb[ch2_range]]
            self.refresh_plot()
        except:
            app.disconnect_from_oscope()

    def toggle_h_cursors(self):
        self.show_h_cursors = not self.show_h_cursors
        self.refresh_plot()

    def toggle_v_cursors(self):
        self.show_v_cursors = not self.show_v_cursors
        self.refresh_plot()

    def swap_axes(self):
        self.ch1_vs_ch2 = not self.ch1_vs_ch2
        theme = settings_manager.get_current_theme()
        if self.ch1_vs_ch2:
            self.xaxis_color = theme['ch2_color']
            self.xlabel_value = 'CH2 (V)'
            self.yaxes['left'].color = theme['ch1_color']
            self.yaxes['left'].ylabel_value = 'CH1 (V)'
        else:
            self.xaxis_color = theme['ch1_color']
            self.xlabel_value = 'CH1 (V)'
            self.yaxes['left'].color = theme['ch2_color']
            self.yaxes['left'].ylabel_value = 'CH2 (V)'
        self.xlim, self.yaxes['left'].ylim = self.yaxes['left'].ylim, self.xlim
        self.h_cursor1, self.yaxes['left'].v_cursor1 = self.yaxes['left'].v_cursor1, self.h_cursor1
        self.h_cursor2, self.yaxes['left'].v_cursor2 = self.yaxes['left'].v_cursor2, self.h_cursor2
        self.show_h_cursors, self.show_v_cursors = self.show_v_cursors, self.show_h_cursors
        self.curves['XY'].points_x, self.curves['XY'].points_y = self.curves['XY'].points_y, self.curves['XY'].points_x
        self.refresh_plot()

    def reset_touches(self):
        self.num_touches = 0
        self.touch_positions = []
        self.touch_net_movements = []
        self.looking_for_gesture = True

    def on_touch_down(self, touch):
        if not app.root.scope.xyplot_visible:
            return

        if app.root.scope.wavegen_visible or app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        if (touch.pos[0] < self.canvas_left) or (touch.pos[0] > self.canvas_left + self.canvas_width) or (touch.pos[1] < self.canvas_bottom) or (touch.pos[1] > self.canvas_bottom + self.canvas_height):
            self.looking_for_gesture = False

        self.num_touches += 1
        self.touch_net_movements.append([0., 0.])
        self.touch_positions.append(touch.pos)

        if (self.num_touches == 1):
            if ((touch.pos[0] - self.to_canvas_x(0.)) ** 2 + (touch.pos[1] - self.axes_bottom) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.dragging_h_zero_point = True
            elif self.show_h_cursors and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top) and (abs(touch.pos[0] - self.to_canvas_x(self.h_cursor1)) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_h_cursor1 = True
            elif self.show_h_cursors and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top) and (abs(touch.pos[0] - self.to_canvas_x(self.h_cursor2)) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_h_cursor2 = True
            elif (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (abs(touch.pos[1] - self.axes_bottom) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_h_zero_point = True
            elif ((touch.pos[0] - self.axes_left) ** 2 + (touch.pos[1] - self.to_canvas_y(0., self.left_yaxis)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
                self.looking_for_gesture = False
                self.dragging_v_zero_point = True
            elif self.show_v_cursors and (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (abs(touch.pos[1] - self.to_canvas_y(self.yaxes[self.left_yaxis].v_cursor1, self.left_yaxis)) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_v_cursor1 = True
            elif self.show_v_cursors and (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (abs(touch.pos[1] - self.to_canvas_y(self.yaxes[self.left_yaxis].v_cursor2, self.left_yaxis)) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_v_cursor2 = True
            elif (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top) and (abs(touch.pos[0] - self.axes_left) <= self.CONTROL_PT_THRESHOLD):
                self.looking_for_gesture = False
                self.dragging_v_zero_point = True

    def on_touch_move(self, touch):
        if not app.root.scope.xyplot_visible:
            return

        if app.root.scope.wavegen_visible or app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        sqr_distances = [(touch.pos[0] - pos[0]) ** 2 + (touch.pos[1] - pos[1]) ** 2 for pos in self.touch_positions]
        try:
            i = min(enumerate(sqr_distances), key = lambda x: x[1])[0]
        except ValueError:
            return

        if i == 0:
            if self.dragging_h_zero_point:
                dx = self.x_epsilon * (touch.pos[0] - self.touch_positions[i][0])
                self.xlim[0] -= dx
                self.xlim[1] -= dx
                self.refresh_plot()
            elif self.dragging_v_zero_point:
                dy = self.yaxes[self.left_yaxis].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.yaxes[self.left_yaxis].ylim[0] -= dy
                self.yaxes[self.left_yaxis].ylim[1] -= dy
                self.refresh_plot()
            elif self.dragging_h_cursor1:
                self.h_cursor1 += self.x_epsilon * (touch.pos[0] - self.touch_positions[i][0])
                self.refresh_plot()
            elif self.dragging_h_cursor2:
                self.h_cursor2 += self.x_epsilon * (touch.pos[0] - self.touch_positions[i][0])
                self.refresh_plot()
            elif self.dragging_v_cursor1:
                self.yaxes[self.left_yaxis].v_cursor1 += self.yaxes[self.left_yaxis].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.refresh_plot()
            elif self.dragging_v_cursor2:
                self.yaxes[self.left_yaxis].v_cursor2 += self.yaxes[self.left_yaxis].y_epsilon * (touch.pos[1] - self.touch_positions[i][1])
                self.refresh_plot()

        self.touch_net_movements[i][0] += touch.pos[0] - self.touch_positions[i][0]
        self.touch_net_movements[i][1] += touch.pos[1] - self.touch_positions[i][1]
        self.touch_positions[i] = touch.pos

    def on_touch_up(self, touch):
        if not app.root.scope.xyplot_visible:
            return

        if app.root.scope.wavegen_visible or app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        if self.looking_for_gesture:
            self.looking_for_gesture = False

        if self.dragging_h_zero_point:
            self.dragging_h_zero_point = False

        if self.dragging_v_zero_point:
            self.dragging_v_zero_point = False

        if self.dragging_h_cursor1:
            self.dragging_h_cursor1 = False

        if self.dragging_h_cursor2:
            self.dragging_h_cursor2 = False

        if self.dragging_v_cursor1:
            self.dragging_v_cursor1 = False

        if self.dragging_v_cursor2:
            self.dragging_v_cursor2 = False

        self.num_touches -= 1
        sqr_distances = [(touch.pos[0] - pos[0]) ** 2 + (touch.pos[1] - pos[1]) ** 2 for pos in self.touch_positions]
        try:
            i = min(enumerate(sqr_distances), key = lambda x: x[1])[0]
            del self.touch_net_movements[i]
            del self.touch_positions[i]
        except ValueError:
            if self.num_touches < 0:
                self.num_touches = 0

        if self.num_touches == 0:
            self.looking_for_gesture = True

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if key == 'up' or key == 'k':
            if 'shift' in modifiers:
                self.pan_up(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_up(fraction = 0.5)
            else:
                self.pan_up()
        elif key == 'down' or key == 'j':
            if 'shift' in modifiers:
                self.pan_down(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_down(fraction = 0.5)
            else:
                self.pan_down()
        elif key == 'left' or key == 'h':
            if 'shift' in modifiers:
                self.pan_left(fraction = 1. / self.axes_width)
            elif 'ctrl' in modifiers:
                self.pan_left(fraction = 0.5)
            else:
                self.pan_left()
        elif key == 'right' or key == 'l':
            if 'shift' in modifiers:
                self.pan_right(fraction = 1. / self.axes_width)
            elif 'ctrl' in modifiers:
                self.pan_right(fraction = 0.5)
            else:
                self.pan_right()
        elif key == '=':
            if 'shift' in modifiers:
                self.zoom_in(factor = math.sqrt(math.sqrt(2.)))
            elif 'ctrl' in modifiers:
                self.zoom_in(factor = 2.)
            else:
                self.zoom_in()
        elif key == '-':
            if 'shift' in modifiers:
                self.zoom_out(factor = math.sqrt(math.sqrt(2.)))
            elif 'ctrl' in modifiers:
                self.zoom_out(factor = 2.)
            else:
                self.zoom_out()
        elif key == 'g':
            if self.grid() == 'off':
                self.grid('on')
            else:
                self.grid('off')
        elif key == 'spacebar':
            self.home_view()
        elif key == 'x':
            app.root.scope.xy_h_cursors_button.state = 'down' if app.root.scope.xy_h_cursors_button.state == 'normal' else 'normal'
            self.toggle_h_cursors()
        elif key == 'y':
            app.root.scope.xy_v_cursors_button.state = 'down' if app.root.scope.xy_v_cursors_button.state == 'normal' else 'normal'
            self.toggle_v_cursors()
        elif key == 'i':
            app.root.scope.xy_h_cursors_button.state, app.root.scope.xy_v_cursors_button.state = app.root.scope.xy_v_cursors_button.state, app.root.scope.xy_h_cursors_button.state
            self.swap_axes()

class WavegenPlot(Plot):

    def __init__(self, **kwargs):
        super(WavegenPlot, self).__init__(**kwargs)

        self.grid_state = 'on'

        self.default_color_order = ('c', 'm', 'y', 'b', 'g', 'r')
        self.default_marker = ''

        self.control_point_color = self.colors['g']
        self.drag_direction = None
        self.dragging_offset_control_pt = False
        self.dragging_amp_control_pt = False
        self.dragging_amp_control_pt_h_xor_v = False
        self.CONTROL_PT_THRESHOLD = 60.

        self.shape = 'SIN'
        self.frequency = 1e3
        self.amplitude = 1.
        self.offset = 2.5

        self.MIN_FREQUENCY = 20e-3
        self.MAX_FREQUENCY = 200e3
        self.MIN_AMPLITUDE = 0.
        self.MAX_AMPLITUDE = 2.5
        self.MIN_OFFSET = 0.
        self.MAX_OFFSET = 5.

        self.num_points = 401

        self.xaxis_mode = 'linear'
        self.xlimits_mode = 'manual'
        self.xlim = [0., 1e-3]
        self.xmin = 0.
        self.xmax = 1e-3
        self.xaxis_units = 's'

        # Get theme colors
        theme = settings_manager.get_current_theme()
        
        # Add waveform color to the colors dict for curve rendering
        self.colors['waveform'] = theme['waveform_color']
        self.control_point_color = theme['waveform_color']

        self.yaxes['left'].color = theme['axes_color']
        self.yaxes['left'].units = 'V'
        self.yaxes['left'].yaxis_mode = 'linear'
        self.yaxes['left'].ylimits_mode = 'manual'
        self.yaxes['left'].ylim = [0., 5.]
        self.yaxes['left'].ymin = 0.
        self.yaxes['left'].ymax = 5.

        self.generate_preview()

        self.configure(background = theme['plot_background'], axes_background = theme['axes_background'], 
                       axes_color = theme['axes_color'], grid_color = theme['grid_color'], 
                       fontsize = int(18 * app.fontscale), font = app.fontname, linear_minor_ticks = 'on')

        self.refresh_plot()

    def draw_plot(self):
        super(WavegenPlot, self).draw_plot()
        self.draw_offset_control_point()
        self.draw_amp_control_point()

    def draw_background(self):
        self.canvas.add(Color(*get_color_from_hex(self.canvas_background_color + 'CD')))
#        self.canvas.add(Rectangle(pos = [self.canvas_left, self.canvas_bottom], size = [self.canvas_width, self.canvas_height]))
        self.canvas.add(Rectangle(pos = [self.canvas_left, self.canvas_bottom], size = [self.canvas_width, self.axes_bottom - self.canvas_bottom]))
        self.canvas.add(Rectangle(pos = [self.canvas_left, self.axes_top], size = [self.canvas_width, self.canvas_bottom + self.canvas_height - self.axes_top]))
        self.canvas.add(Rectangle(pos = [self.canvas_left, self.axes_bottom], size = [self.axes_left - self.canvas_left, self.axes_height]))
        self.canvas.add(Rectangle(pos = [self.axes_right, self.axes_bottom], size = [self.canvas_left + self.canvas_width - self.axes_right, self.axes_height]))

    def draw_axes_background(self):
        self.canvas.add(Color(*get_color_from_hex(self.axes_background_color + '9A')))
        self.canvas.add(Rectangle(pos = [self.axes_left, self.axes_bottom], size = [self.axes_width, self.axes_height]))

    def draw_offset_control_point(self, r = 5.):
        curve = self.curves['WG']
        yaxis = self.yaxes[curve.yaxis]
        if (0. > self.xlim[0] - self.x_epsilon) and (0. < self.xlim[1] + self.x_epsilon) and (self.offset > yaxis.ylim[0] - yaxis.y_epsilon) and (self.offset < yaxis.ylim[1] + yaxis.y_epsilon):
            x = self.to_canvas_x(0.)
            y = self.to_canvas_y(self.offset, curve.yaxis)
            self.canvas.add(Color(*get_color_from_hex(self.control_point_color.replace('FF', 'B4') + '66')))
            self.canvas.add(Ellipse(pos = [x - 3. * r - 2., y - 3. * r - 2.], size = [6. * r + 4., 6. * r + 4.]))
            self.canvas.add(Color(*get_color_from_hex(self.control_point_color)))
            self.canvas.add(Ellipse(pos = [x - r, y - r], size = [2. * r, 2. * r]))
            self.canvas.add(Line(ellipse = [x - 3. * r, y - 3. * r, 6. * r, 6. * r], width = self.curve_lineweight))

    def draw_amp_control_point(self, r = 5.):
        curve = self.curves['WG']
        yaxis = self.yaxes[curve.yaxis]
        x = 0.25 / self.frequency
        y = self.offset + self.amplitude
        if (self.shape != 'DC') and (x > self.xlim[0] - self.x_epsilon) and (x < self.xlim[1] + self.x_epsilon) and (y > yaxis.ylim[0] - yaxis.y_epsilon) and (y < yaxis.ylim[1] + yaxis.y_epsilon):
            x = self.to_canvas_x(x)
            y = self.to_canvas_y(y, curve.yaxis)
            self.canvas.add(Color(*get_color_from_hex(self.control_point_color.replace('FF', 'B4') + '66')))
            self.canvas.add(Ellipse(pos = [x - 3. * r - 2., y - 3. * r - 2.], size = [6. * r + 4., 6. * r + 4.]))
            self.canvas.add(Color(*get_color_from_hex(self.control_point_color)))
            self.canvas.add(Ellipse(pos = [x - r, y - r], size = [2. * r, 2. * r]))
            self.canvas.add(Line(ellipse = [x - 3. * r, y - 3. * r, 6. * r, 6. * r], width = self.curve_lineweight))

    def generate_preview(self):
        t = np.linspace(self.xlim[0], self.xlim[1], self.num_points)

        if self.shape == 'DC':
            v = self.offset * np.ones(self.num_points)
        elif self.shape == 'SIN':
            v = self.offset + self.amplitude * np.sin(2. * math.pi * self.frequency * t)
        elif self.shape == 'SQUARE':
            v = self.offset + self.amplitude * np.sign(np.sin(2. * math.pi * self.frequency * t))
        elif self.shape == 'TRIANGLE':
            v = self.offset + self.amplitude * 2. * np.arcsin(np.sin(2. * math.pi * self.frequency * t)) / math.pi
        else:
            raise ValueError("waveform shape must be 'DC', 'SIN', 'SQUARE', or 'TRIANGLE'")

        where_over = np.where(v > self.MAX_OFFSET)[0]
        v[where_over] = self.MAX_OFFSET
        where_under = np.where(v < self.MIN_OFFSET)[0]
        v[where_under] = self.MIN_OFFSET

        self.curves['WG'] = self.curve(name = 'WG', curve_color = 'waveform', curve_style = '-', points_x = [t], points_y = [v])
        if self.shape == 'DC':
            self.yaxes['left'].ylabel_value = 'WG: DC, offset = {}V'.format(app.num2str(self.offset, 4))
        else:
            self.yaxes['left'].ylabel_value = 'WG: {}, freq = {}Hz, amp = {}V, offset = {}V'.format(self.shape, app.num2str(self.frequency, 4), app.num2str(self.amplitude, 4), app.num2str(self.offset, 4))

    def update_preview(self):
        t = np.linspace(self.xlim[0], self.xlim[1], self.num_points)

        if self.shape == 'DC':
            v = self.offset * np.ones(self.num_points)
        elif self.shape == 'SIN':
            v = self.offset + self.amplitude * np.sin(2. * math.pi * self.frequency * t)
        elif self.shape == 'SQUARE':
            v = self.offset + self.amplitude * np.sign(np.sin(2. * math.pi * self.frequency * t))
        elif self.shape == 'TRIANGLE':
            v = self.offset + self.amplitude * 2. * np.arcsin(np.sin(2. * math.pi * self.frequency * t)) / math.pi
        else:
            raise ValueError("waveform shape must be 'DC', 'SIN', 'SQUARE', or 'TRIANGLE'")

        where_over = np.where(v > self.MAX_OFFSET)[0]
        v[where_over] = self.MAX_OFFSET
        where_under = np.where(v < self.MIN_OFFSET)[0]
        v[where_under] = self.MIN_OFFSET

        self.curves['WG'].points_x = [t]
        self.curves['WG'].points_y = [v]
        if self.shape == 'DC':
            self.yaxes['left'].ylabel_value = 'WG: DC, offset = {}V'.format(app.num2str(self.offset, 4))
        else:
            self.yaxes['left'].ylabel_value = 'WG: {}, freq = {}Hz, amp = {}V, offset = {}V'.format(self.shape, app.num2str(self.frequency, 4), app.num2str(self.amplitude, 4), app.num2str(self.offset, 4))

    def home_view(self):
        self.yaxes['left'].ylim = [0., 5.]
        self.update_preview()
        self.refresh_plot()

    def decrease_frequency(self):
        foo = math.log10(self.frequency)
        bar = math.floor(foo)
        foobar = foo - bar
        if foobar < 0.5 * math.log10(2.001):
            self.frequency = 0.5 * math.pow(10., bar)
        elif foobar < 0.5 * math.log10(2.001 * 5.001):
            self.frequency = math.pow(10., bar)
        elif foobar < 0.5 * math.log10(5.001 * 10.001):
            self.frequency = 2. * math.pow(10., bar)
        else:
            self.frequency = 5. * math.pow(10., bar)

        if self.frequency < self.MIN_FREQUENCY:
            self.frequency = self.MIN_FREQUENCY
        if self.frequency > self.MAX_FREQUENCY:
            self.frequency = self.MAX_FREQUENCY

        self.xlim = [0., 1. / self.frequency]
        self.xmin = self.xlim[0]
        self.xmax = self.xlim[1]

        app.root.scope.set_frequency(self.frequency)
        self.update_preview()
        self.refresh_plot()

    def increase_frequency(self):
        foo = math.log10(self.frequency)
        bar = math.floor(foo)
        foobar = foo - bar
        if foobar < 0.5 * math.log10(2.001):
            self.frequency = 2. * math.pow(10., bar)
        elif foobar < 0.5 * math.log10(2.001 * 5.001):
            self.frequency = 5. * math.pow(10., bar)
        elif foobar < 0.5 * math.log10(5.001 * 10.001):
            self.frequency = 10. * math.pow(10., bar)
        else:
            self.frequency = 20. * math.pow(10., bar)

        if self.frequency < self.MIN_FREQUENCY:
            self.frequency = self.MIN_FREQUENCY
        if self.frequency > self.MAX_FREQUENCY:
            self.frequency = self.MAX_FREQUENCY

        self.xlim = [0., 1. / self.frequency]
        self.xmin = self.xlim[0]
        self.xmax = self.xlim[1]

        app.root.scope.set_frequency(self.frequency)
        self.update_preview()
        self.refresh_plot()

    def reset_touches(self):
        self.num_touches = 0
        self.touch_positions = []
        self.touch_net_movements = []
        self.looking_for_gesture = True

    def on_touch_down(self, touch):
        if not app.root.scope.wavegen_visible:
            return

        if app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        if (touch.pos[0] < self.canvas_left) or (touch.pos[0] > self.canvas_left + self.canvas_width) or (touch.pos[1] < self.canvas_bottom) or (touch.pos[1] > self.canvas_bottom + self.canvas_height):
            self.looking_for_gesture = False

        self.num_touches += 1
        self.touch_net_movements.append([0., 0.])
        self.touch_positions.append(touch.pos)

        if (self.num_touches == 1) and ((touch.pos[0] - self.axes_left) ** 2 + (touch.pos[1] - self.to_canvas_y(self.offset)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
            self.looking_for_gesture = False
            self.dragging_offset_control_pt = True
        elif (self.shape != 'DC') and ((touch.pos[0] - self.to_canvas_x(0.25 / self.frequency)) ** 2 + (touch.pos[1] - self.to_canvas_y(self.offset + self.amplitude)) ** 2 <= self.CONTROL_PT_THRESHOLD ** 2):
            if self.num_touches == 1:
                self.looking_for_gesture = False
                self.dragging_amp_control_pt = True
            elif self.num_touches == 2:
                self.looking_for_gesture = False
                self.dragging_amp_control_pt_h_xor_v = True

    def on_touch_move(self, touch):
        if not app.root.scope.wavegen_visible:
            return

        if app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        sqr_distances = [(touch.pos[0] - pos[0]) ** 2 + (touch.pos[1] - pos[1]) ** 2 for pos in self.touch_positions]
        try:
            i = min(enumerate(sqr_distances), key = lambda x: x[1])[0]
        except ValueError:
            return

        if self.dragging_offset_control_pt and (i == 0):
            self.offset = self.from_canvas_y(self.to_canvas_y(self.offset) + touch.pos[1] - self.touch_positions[i][1])
            if self.offset < self.MIN_OFFSET:
                self.offset = self.MIN_OFFSET
            if self.offset > self.MAX_OFFSET:
                self.offset = self.MAX_OFFSET
            app.root.scope.set_offset(self.offset)
            self.update_preview()
            self.refresh_plot()

        if self.dragging_amp_control_pt and (i == 0):
            self.amplitude = self.from_canvas_y(self.to_canvas_y(self.offset + self.amplitude) + touch.pos[1] - self.touch_positions[i][1]) - self.offset
            if self.amplitude < self.MIN_AMPLITUDE:
                self.amplitude = self.MIN_AMPLITUDE
            if self.amplitude > self.MAX_AMPLITUDE:
                self.amplitude = self.MAX_AMPLITUDE
            t_peak = self.from_canvas_x(self.to_canvas_x(0.25 / self.frequency) + touch.pos[0] - self.touch_positions[i][0])
            if t_peak < 0.025 * self.xlim[1]:
                t_peak = 0.025 * self.xlim[1]
            if t_peak > self.xlim[1]:
                t_peak = self.xlim[1]
            self.frequency = 0.25 / t_peak
            if self.frequency < self.MIN_FREQUENCY:
                self.frequency = self.MIN_FREQUENCY
            if self.frequency > self.MAX_FREQUENCY:
                self.frequency = self.MAX_FREQUENCY
            app.root.scope.set_amplitude(self.amplitude)
            app.root.scope.set_frequency(self.frequency)
            self.update_preview()
            self.refresh_plot()

        if self.dragging_amp_control_pt_h_xor_v and (i == 1):
            if self.drag_direction is None:
                dx = abs(touch.pos[0] - self.touch_positions[i][0])
                dy = abs(touch.pos[1] - self.touch_positions[i][1])
                if dx > dy:
                    self.drag_direction = 'HORIZONTAL'
                else:
                    self.drag_direction = 'VERTICAL'
            if self.drag_direction == 'VERTICAL':
                self.amplitude = self.from_canvas_y(self.to_canvas_y(self.offset + self.amplitude) + touch.pos[1] - self.touch_positions[i][1]) - self.offset
                if self.amplitude < self.MIN_AMPLITUDE:
                    self.amplitude = self.MIN_AMPLITUDE
                if self.amplitude > self.MAX_AMPLITUDE:
                    self.amplitude = self.MAX_AMPLITUDE
                app.root.scope.set_amplitude(self.amplitude)
            else:
                t_peak = self.from_canvas_x(self.to_canvas_x(0.25 / self.frequency) + touch.pos[0] - self.touch_positions[i][0])
                if t_peak < 0.025 * self.xlim[1]:
                    t_peak = 0.025 * self.xlim[1]
                if t_peak > self.xlim[1]:
                    t_peak = self.xlim[1]
                self.frequency = 0.25 / t_peak
                if self.frequency < self.MIN_FREQUENCY:
                    self.frequency = self.MIN_FREQUENCY
                if self.frequency > self.MAX_FREQUENCY:
                    self.frequency = self.MAX_FREQUENCY
                app.root.scope.set_frequency(self.frequency)
            self.update_preview()
            self.refresh_plot()

        self.touch_net_movements[i][0] += touch.pos[0] - self.touch_positions[i][0]
        self.touch_net_movements[i][1] += touch.pos[1] - self.touch_positions[i][1]
        self.touch_positions[i] = touch.pos

    def on_touch_up(self, touch):
        if not app.root.scope.wavegen_visible:
            return

        if app.root.scope.digital_controls_visible or app.root.scope.offset_waveform_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        if self.looking_for_gesture:
            self.looking_for_gesture = False

        if self.dragging_offset_control_pt:
            self.dragging_offset_control_pt = False

        if self.dragging_amp_control_pt:
            self.dragging_amp_control_pt = False

        if self.dragging_amp_control_pt_h_xor_v:
            self.dragging_amp_control_pt_h_xor_v = False
            self.drag_direction = None

        self.num_touches -= 1
        sqr_distances = [(touch.pos[0] - pos[0]) ** 2 + (touch.pos[1] - pos[1]) ** 2 for pos in self.touch_positions]
        try:
            i = min(enumerate(sqr_distances), key = lambda x: x[1])[0]
            del self.touch_net_movements[i]
            del self.touch_positions[i]
        except ValueError:
            if self.num_touches < 0:
                self.num_touches = 0
        if self.num_touches == 0:
            self.looking_for_gesture = True

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if key == 'up' or key == 'k':
            if 'shift' in modifiers:
                self.pan_up(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_up(fraction = 0.5)
            else:
                self.pan_up()
        elif key == 'down' or key == 'j':
            if 'shift' in modifiers:
                self.pan_down(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_down(fraction = 0.5)
            else:
                self.pan_down()
        elif key == '=':
            self.zoom_in_y()
        elif key == '-':
            if 'shift' in modifiers:
                app.root.scope.set_shape('DC')
                app.root.scope.dc_button.state = 'down'
                app.root.scope.sin_button.state = 'normal'
                app.root.scope.square_button.state = 'normal'
                app.root.scope.triangle_button.state = 'normal'
            else:
                self.zoom_out_y()
        elif key == ',' and 'shift' in modifiers:
            self.increase_frequency()
        elif key == '.' and 'shift' in modifiers:
            self.decrease_frequency()
        elif key == 'g':
            if self.grid() == 'off':
                self.grid('on')
            else:
                self.grid('off')
        elif key == 'spacebar':
            self.home_view()
        elif key == '9' and 'shift' in modifiers:
            app.root.scope.set_shape('SIN')
            app.root.scope.dc_button.state = 'normal'
            app.root.scope.sin_button.state = 'down'
            app.root.scope.square_button.state = 'normal'
            app.root.scope.triangle_button.state = 'normal'
        elif key == '[':
            app.root.scope.set_shape('SQUARE')
            app.root.scope.dc_button.state = 'normal'
            app.root.scope.sin_button.state = 'normal'
            app.root.scope.square_button.state = 'down'
            app.root.scope.triangle_button.state = 'normal'
        elif key == '6' and 'shift' in modifiers:
            app.root.scope.set_shape('TRIANGLE')
            app.root.scope.dc_button.state = 'normal'
            app.root.scope.sin_button.state = 'normal'
            app.root.scope.square_button.state = 'normal'
            app.root.scope.triangle_button.state = 'down'

class OffsetWaveformPlot(Plot):

    def __init__(self, **kwargs):
        super(OffsetWaveformPlot, self).__init__(**kwargs)

        self.num_samples = 0
        self.offset_interval = 30e-3

        self.grid_state = 'on'

        self.default_color_order = ('c', 'm', 'y', 'b', 'g', 'r')
        self.default_marker = ''

        self.CONTROL_PT_THRESHOLD = 60.

        self.xaxis_color = ''
        self.xaxis_units = 's'
        self.xaxis_mode = 'linear'
        self.xlimits_mode = 'manual'
        self.xlim = [0., 1.]
        self.xmin = 0.
        self.xmax = 1.
        self.xlabel_value = ''

        # Get theme colors
        theme = settings_manager.get_current_theme()
        
        # Add waveform color to the colors dict for curve rendering
        self.colors['waveform'] = theme['waveform_color']

        self.yaxes['left'].color = theme['axes_color']
        self.yaxes['left'].units = 'V'
        self.yaxes['left'].yaxis_mode = 'linear'
        self.yaxes['left'].ylimits_mode = 'manual'
        self.yaxes['left'].ylim = [0., 5.]
        self.yaxes['left'].ymin = 0.
        self.yaxes['left'].ymax = 5.
        self.yaxes['left'].ylabel_value = 'No waveform present'

        self.left_yaxis = 'left'

        self.curves['OffsetWaveform'] = self.curve(name = 'OffsetWaveform', yaxis = 'left', curve_color = 'waveform', curve_style = '-')

        self.configure(background = theme['plot_background'], axes_background = theme['axes_background'], 
                       axes_color = theme['axes_color'], grid_color = theme['grid_color'], 
                       fontsize = int(18 * app.fontscale), font = app.fontname, marker_radius = 6., linear_minor_ticks = 'on')

        self.refresh_plot()

    def on_oscope_disconnect(self):
        self.num_samples = 0

        self.xlim = [0., 1.]
        self.xmin = 0.
        self.xmax = 1.

        self.yaxes['left'].ylim = [0., 5.]
        self.yaxes['left'].ymin = 0.
        self.yaxes['left'].ymax = 5.
        self.yaxes['left'].ylabel_value = 'No waveform present'

        self.curves['OffsetWaveform'].points_x = [np.array([])]
        self.curves['OffsetWaveform'].points_y = [np.array([])]

        self.refresh_plot()

    def draw_background(self):
        self.canvas.add(Color(*get_color_from_hex(self.canvas_background_color + 'CD')))
#        self.canvas.add(Rectangle(pos = [self.canvas_left, self.canvas_bottom], size = [self.canvas_width, self.canvas_height]))
        self.canvas.add(Rectangle(pos = [self.canvas_left, self.canvas_bottom], size = [self.canvas_width, self.axes_bottom - self.canvas_bottom]))
        self.canvas.add(Rectangle(pos = [self.canvas_left, self.axes_top], size = [self.canvas_width, self.canvas_bottom + self.canvas_height - self.axes_top]))
        self.canvas.add(Rectangle(pos = [self.canvas_left, self.axes_bottom], size = [self.axes_left - self.canvas_left, self.axes_height]))
        self.canvas.add(Rectangle(pos = [self.axes_right, self.axes_bottom], size = [self.canvas_left + self.canvas_width - self.axes_right, self.axes_height]))

    def draw_axes_background(self):
        self.canvas.add(Color(*get_color_from_hex(self.axes_background_color + '9A')))
        self.canvas.add(Rectangle(pos = [self.axes_left, self.axes_bottom], size = [self.axes_width, self.axes_height]))

    def home_view(self):
        self.xlim = [0., self.offset_interval * self.num_samples if self.num_samples != 0 else 1.]
        self.yaxes['left'].ylim = [0., 5.]
        self.refresh_plot()

    def on_touch_down(self, touch):
        if not app.root.scope.offset_waveform_visible:
            return

        if app.root.scope.digital_controls_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        super(OffsetWaveformPlot, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if not app.root.scope.offset_waveform_visible:
            return

        if app.root.scope.digital_controls_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        super(OffsetWaveformPlot, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if not app.root.scope.offset_waveform_visible:
            return

        if app.root.scope.digital_controls_visible:
            return

        if touch.pos[0] > 0.9 * 0.6 * Window.size[0]:
            return

        super(OffsetWaveformPlot, self).on_touch_up(touch)

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if key == 'up' or key == 'k':
            if 'shift' in modifiers:
                self.pan_up(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_up(fraction = 0.5)
            else:
                self.pan_up()
        elif key == 'down' or key == 'j':
            if 'shift' in modifiers:
                self.pan_down(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_down(fraction = 0.5)
            else:
                self.pan_down()
        elif key == '=':
            if 'shift' in modifiers:
                self.zoom_in_y(factor = math.sqrt(math.sqrt(2.)))
            elif 'ctrl' in modifiers:
                self.zoom_in_y(factor = 2.)
            else:
                self.zoom_in_y()
        elif key == '-':
            if 'shift' in modifiers:
                self.zoom_out_y(factor = math.sqrt(math.sqrt(2.)))
            elif 'ctrl' in modifiers:
                self.zoom_out_y(factor = 2.)
            else:
                self.zoom_out_y()
        elif key == 'g':
            if self.grid() == 'off':
                self.grid('on')
            else:
                self.grid('off')
        elif key == 'spacebar':
            self.home_view()

class BodePlot(Plot):

    def __init__(self, **kwargs):
        super(BodePlot, self).__init__(**kwargs)

        self.trigger_mode = 'Single'
        self.trigger_repeat = False

        self.grid_state = 'on'

        self.default_color_order = ('c', 'm', 'y', 'b', 'g', 'r')
        self.default_marker = ''

        self.CONTROL_PT_THRESHOLD = 60.

        self.xaxis_color = ''
        self.xaxis_mode = 'log'
        self.xlimits_mode = 'manual'
        self.xlim = [1., 1e5]
        self.xmin = 1.
        self.xmax = 1e5
        self.xlabel_value = 'Frequency (Hz)'

        # Get theme colors
        theme = settings_manager.get_current_theme()

        self.yaxes['left'].color = theme['gain_color']
        self.yaxes['left'].yaxis_mode = 'linear'
        self.yaxes['left'].ylimits_mode = 'manual'
        self.yaxes['left'].ylim = [-40., 10.]
        self.yaxes['left'].ymin = -40.
        self.yaxes['left'].ymax = 10.
        self.yaxes['left'].ylabel_value = 'Gain (dB)'

        self.yaxes['right'] = self.y_axis()

        self.yaxes['right'].color = theme['phase_color']
        self.yaxes['right'].yaxis_mode = 'linear'
        self.yaxes['right'].ylimits_mode = 'manual'
        self.yaxes['right'].ylim = [-90., 0.]
        self.yaxes['right'].ymin = -90.
        self.yaxes['right'].ymax = 0.
        self.yaxes['right'].ylabel_value = 'Phase (\u00B0)'

        self.left_yaxis = 'left'
        self.right_yaxis = 'right'

        self.configure(background = theme['plot_background'], axes_background = theme['axes_background'], 
                       axes_color = theme['axes_color'], grid_color = theme['grid_color'], 
                       fontsize = int(18 * app.fontscale), font = app.fontname, marker_radius = 6., linear_minor_ticks = 'on')

        self.refresh_plot()

    def draw_grid(self):
        if self.grid_state == 'on':
            self.canvas.add(Color(*get_color_from_hex(self.grid_color)))
            for [x, label] in self.x_ticks:
                self.draw_v_grid_line(self.to_canvas_x(x))
            if self.xaxis_mode == 'log':
                for [x, label] in self.x_minor_ticks:
                    self.draw_v_grid_line(self.to_canvas_x(x))

            self.canvas.add(Color(*get_color_from_hex(self.yaxes[self.left_yaxis].color.replace('FF', '58'))))
            for [y, label] in self.left_y_ticks:
                self.draw_h_grid_line(self.to_canvas_y(y, self.left_yaxis))
            if self.left_yaxis != '' and self.yaxes[self.left_yaxis].yaxis_mode == 'log':
                for [y, label] in self.left_y_minor_ticks:
                    self.draw_h_grid_line(self.to_canvas_y(y, self.left_yaxis))

            if self.right_yaxis != '':
                self.canvas.add(Color(*get_color_from_hex(self.yaxes[self.right_yaxis].color.replace('FF', '58'))))
            for [y, label] in self.right_y_ticks:
                self.draw_h_grid_line(self.to_canvas_y(y, self.right_yaxis))
            if self.right_yaxis != '' and self.yaxes[self.right_yaxis].yaxis_mode == 'log':
                for [y, label] in self.right_y_minor_ticks:
                    self.draw_h_grid_line(self.to_canvas_y(y, self.right_yaxis))

    def home_view(self):
        pass

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if key == 'up' or key == 'k':
            if 'shift' in modifiers:
                self.pan_up(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_up(fraction = 0.5)
            else:
                self.pan_up()
        elif key == 'down' or key == 'j':
            if 'shift' in modifiers:
                self.pan_down(fraction = 1. / self.axes_height)
            elif 'ctrl' in modifiers:
                self.pan_down(fraction = 0.5)
            else:
                self.pan_down()
        elif key == 'left' or key == 'h':
            if 'shift' in modifiers:
                self.pan_left(fraction = 1. / self.axes_width)
            elif 'ctrl' in modifiers:
                self.pan_left(fraction = 0.5)
            else:
                self.pan_left()
        elif key == 'right' or key == 'l':
            if 'shift' in modifiers:
                self.pan_right(fraction = 1. / self.axes_width)
            elif 'ctrl' in modifiers:
                self.pan_right(fraction = 0.5)
            else:
                self.pan_right()
        elif key == '=':
            if 'shift' in modifiers:
                self.zoom_in(factor = math.sqrt(math.sqrt(2.)))
            elif 'ctrl' in modifiers:
                self.zoom_in(factor = 2.)
            else:
                self.zoom_in()
        elif key == '-':
            if 'shift' in modifiers:
                self.zoom_out(factor = math.sqrt(math.sqrt(2.)))
            elif 'ctrl' in modifiers:
                self.zoom_out(factor = 2.)
            else:
                self.zoom_out()
        elif key == 'g':
            if self.grid() == 'off':
                self.grid('on')
            else:
                self.grid('off')
        elif key == 'spacebar':
            self.home_view()

class DigitalControlPanel(BoxLayout):

    def __init__(self, **kwargs):
        super(DigitalControlPanel, self).__init__(**kwargs)
        self.update_job = None

    def on_oscope_disconnect(self):
        if self.update_job is not None:
            self.update_job.cancel()
            self.update_job = None

    def sync_controls(self):
        if not app.dev.connected:
            return

        try:
            led_button_vals = ('normal', 'down')
            self.led_one_button.state = led_button_vals[app.dev.get_led1()]
            self.led_two_button.state = led_button_vals[app.dev.get_led2()]
            self.led_three_button.state = led_button_vals[app.dev.get_led3()]

            self.servo_period_slider.slider.value = math.log10(app.dev.dig_get_period())

            od_spinner_vals = ('PP', 'OD')
            self.d_zero_od_spinner.text = od_spinner_vals[app.dev.dig_get_od(0)]
            self.d_one_od_spinner.text = od_spinner_vals[app.dev.dig_get_od(1)]
            self.d_two_od_spinner.text = od_spinner_vals[app.dev.dig_get_od(2)]
            self.d_three_od_spinner.text = od_spinner_vals[app.dev.dig_get_od(3)]

            mode_spinner_vals = ('OUT', 'IN', 'PWM', 'SERVO')
            new_mode = mode_spinner_vals[app.dev.dig_get_mode(0)]
            if self.d_zero_mode_spinner.text == new_mode:
                self.d0_mode_callback()
            else:
                self.d_zero_mode_spinner.text = new_mode
            new_mode = mode_spinner_vals[app.dev.dig_get_mode(1)]
            if self.d_one_mode_spinner.text == new_mode:
                self.d1_mode_callback()
            else:
                self.d_one_mode_spinner.text = new_mode
            new_mode = mode_spinner_vals[app.dev.dig_get_mode(2)]
            if self.d_two_mode_spinner.text == new_mode:
                self.d2_mode_callback()
            else:
                self.d_two_mode_spinner.text = new_mode
            new_mode = mode_spinner_vals[app.dev.dig_get_mode(3)]
            if self.d_three_mode_spinner.text == new_mode:
                self.d3_mode_callback()
            else:
                self.d_three_mode_spinner.text = new_mode
        except:
            app.disconnect_from_oscope()

    def update_button_displays(self, t):
        if not app.dev.connected:
            return

        try:
            at_least_one_input = False

            if self.d_zero_mode_spinner.text == 'IN':
                at_least_one_input = True
                if app.dev.dig_read(0) == 1:
                    self.d_zero_button.state = 'down'
                else:
                    self.d_zero_button.state = 'normal'

            if self.d_one_mode_spinner.text == 'IN':
                at_least_one_input = True
                if app.dev.dig_read(1) == 1:
                    self.d_one_button.state = 'down'
                else:
                    self.d_one_button.state = 'normal'

            if self.d_two_mode_spinner.text == 'IN':
                at_least_one_input = True
                if app.dev.dig_read(2) == 1:
                    self.d_two_button.state = 'down'
                else:
                    self.d_two_button.state = 'normal'

            if self.d_three_mode_spinner.text == 'IN':
                at_least_one_input = True
                if app.dev.dig_read(3) == 1:
                    self.d_three_button.state = 'down'
                else:
                    self.d_three_button.state = 'normal'

            if at_least_one_input:
                self.update_job = Clock.schedule_once(self.update_button_displays, 0.05)
        except:
            app.disconnect_from_oscope()

    def led1_callback(self):
        try:
            if self.led_one_button.state == 'down':
                app.dev.set_led1(1)
            else:
                app.dev.set_led1(0)
        except:
            app.disconnect_from_oscope()

    def led2_callback(self):
        try:
            if self.led_two_button.state == 'down':
                app.dev.set_led2(1)
            else:
                app.dev.set_led2(0)
        except:
            app.disconnect_from_oscope()

    def led3_callback(self):
        try:
            if self.led_three_button.state == 'down':
                app.dev.set_led3(1)
            else:
                app.dev.set_led3(0)
        except:
            app.disconnect_from_oscope()

    def servo_period_callback(self):
        try:
            app.dev.dig_set_period(self.servo_period_slider.value)
        except:
            app.disconnect_from_oscope()

    def d0_button_callback(self):
        try:
            if not self.d_zero_button.disabled:
                if self.d_zero_button.state == 'down':
                    app.dev.dig_write(0, 1)
                else:
                    app.dev.dig_write(0, 0)
        except:
            app.disconnect_from_oscope()

    def d0_mode_callback(self):
        try:
            if self.d_zero_mode_spinner.text == 'OUT':
                app.dev.dig_set_mode(0, 0)
                self.d_zero_button.disabled = False
                self.d_zero_freq_slider.slider.disabled = True
                self.d_zero_freq_slider.snap_button.disabled = True
                self.d_zero_duty_slider.slider.disabled = True
                self.d_zero_duty_slider.snap_button.disabled = True
                if app.dev.connected:
                    if app.dev.dig_read(0) == 1:
                        self.d_zero_button.state = 'down'
                    else:
                        self.d_zero_button.state = 'normal'
            elif self.d_zero_mode_spinner.text == 'IN':
                app.dev.dig_set_mode(0, 1)
                self.d_zero_button.disabled = True
                self.d_zero_button.state = 'normal'
                self.d_zero_freq_slider.slider.disabled = True
                self.d_zero_freq_slider.snap_button.disabled = True
                self.d_zero_duty_slider.slider.disabled = True
                self.d_zero_duty_slider.snap_button.disabled = True
                if self.update_job is None:
                    self.update_job = Clock.schedule_once(self.update_button_displays, 0.05)
            elif self.d_zero_mode_spinner.text == 'PWM':
                app.dev.dig_set_mode(0, 2)
                self.d_zero_button.disabled = True
                self.d_zero_button.state = 'normal'
                self.d_zero_freq_slider.slider.disabled = False
                self.d_zero_freq_slider.snap_button.disabled = False
                if app.dev.connected:
                    self.d_zero_freq_slider.slider.value = math.log10(app.dev.dig_get_freq(0))
                self.d_zero_duty_slider.slider.disabled = False
                self.d_zero_duty_slider.snap_button.disabled = False
                self.d_zero_duty_slider.label_text = 'Duty\nCycle\n'
                self.d_zero_duty_slider.units = '%'
                self.d_zero_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_zero_duty_slider.slider.value = 100. * app.dev.dig_get_duty(0)
                else:
                    self.d_zero_duty_slider.slider.value = 50.
                self.d_zero_duty_slider.minimum = 0.
                self.d_zero_duty_slider.maximum = 100.
                self.d_zero_duty_slider.step = 5.
            elif self.d_zero_mode_spinner.text == 'SERVO':
                app.dev.dig_set_mode(0, 3)
                self.d_zero_button.disabled = True
                self.d_zero_button.state = 'normal'
                self.d_zero_freq_slider.slider.disabled = True
                self.d_zero_freq_slider.snap_button.disabled = True
                self.d_zero_duty_slider.slider.disabled = False
                self.d_zero_duty_slider.snap_button.disabled = False
                self.d_zero_duty_slider.label_text = 'Pulse\nWidth\n'
                self.d_zero_duty_slider.units = 's'
                self.d_zero_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_zero_duty_slider.slider.value = app.dev.dig_get_width(0)
                else:
                    self.d_zero_duty_slider.slider.value = 1.5e-3
                self.d_zero_duty_slider.minimum = 0.
                self.d_zero_duty_slider.maximum = 4e-3
                self.d_zero_duty_slider.step = 0.1e-3
        except:
            app.disconnect_from_oscope()

    def d0_od_callback(self):
        try:
            if self.d_zero_od_spinner.text == 'PP':
                app.dev.dig_set_od(0, 0)
            else:
                app.dev.dig_set_od(0, 1)
        except:
            app.disconnect_from_oscope()

    def d0_freq_callback(self):
        try:
            app.dev.dig_set_freq(0, self.d_zero_freq_slider.value)
        except:
            app.disconnect_from_oscope()

    def d0_duty_callback(self):
        try:
            if self.d_zero_mode_spinner.text == 'PWM':
                app.dev.dig_set_duty(0, self.d_zero_duty_slider.value / 100.)
            elif self.d_zero_mode_spinner.text == 'SERVO':
                app.dev.dig_set_width(0, self.d_zero_duty_slider.value)
        except:
            app.disconnect_from_oscope()

    def d1_button_callback(self):
        try:
            if not self.d_one_button.disabled:
                if self.d_one_button.state == 'down':
                    app.dev.dig_write(1, 1)
                else:
                    app.dev.dig_write(1, 0)
        except:
            app.disconnect_from_oscope()

    def d1_mode_callback(self):
        try:
            if self.d_one_mode_spinner.text == 'OUT':
                app.dev.dig_set_mode(1, 0)
                self.d_one_button.disabled = False
                self.d_one_freq_slider.slider.disabled = True
                self.d_one_freq_slider.snap_button.disabled = True
                self.d_one_duty_slider.slider.disabled = True
                self.d_one_duty_slider.snap_button.disabled = True
                if app.dev.connected:
                    if app.dev.dig_read(1) == 1:
                        self.d_one_button.state = 'down'
                    else:
                        self.d_one_button.state = 'normal'
            elif self.d_one_mode_spinner.text == 'IN':
                app.dev.dig_set_mode(1, 1)
                self.d_one_button.disabled = True
                self.d_one_button.state = 'normal'
                self.d_one_freq_slider.slider.disabled = True
                self.d_one_freq_slider.snap_button.disabled = True
                self.d_one_duty_slider.slider.disabled = True
                self.d_one_duty_slider.snap_button.disabled = True
                if self.update_job is None:
                    self.update_job = Clock.schedule_once(self.update_button_displays, 0.05)
            elif self.d_one_mode_spinner.text == 'PWM':
                app.dev.dig_set_mode(1, 2)
                self.d_one_button.disabled = True
                self.d_one_button.state = 'normal'
                self.d_one_freq_slider.slider.disabled = False
                self.d_one_freq_slider.snap_button.disabled = False
                if app.dev.connected:
                    self.d_one_freq_slider.slider.value = math.log10(app.dev.dig_get_freq(1))
                self.d_one_duty_slider.slider.disabled = False
                self.d_one_duty_slider.snap_button.disabled = False
                self.d_one_duty_slider.label_text = 'Duty\nCycle\n'
                self.d_one_duty_slider.units = '%'
                self.d_one_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_one_duty_slider.slider.value = 100. * app.dev.dig_get_duty(1)
                else:
                    self.d_one_duty_slider.slider.value = 50.
                self.d_one_duty_slider.minimum = 0.
                self.d_one_duty_slider.maximum = 100.
                self.d_one_duty_slider.step = 5.
            elif self.d_one_mode_spinner.text == 'SERVO':
                app.dev.dig_set_mode(1, 3)
                self.d_one_button.disabled = True
                self.d_one_button.state = 'normal'
                self.d_one_freq_slider.slider.disabled = True
                self.d_one_freq_slider.snap_button.disabled = True
                self.d_one_duty_slider.slider.disabled = False
                self.d_one_duty_slider.snap_button.disabled = False
                self.d_one_duty_slider.label_text = 'Pulse\nWidth\n'
                self.d_one_duty_slider.units = 's'
                self.d_one_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_one_duty_slider.slider.value = app.dev.dig_get_width(1)
                else:
                    self.d_one_duty_slider.slider.value = 1.5e-3
                self.d_one_duty_slider.minimum = 0.
                self.d_one_duty_slider.maximum = 4e-3
                self.d_one_duty_slider.step = 0.1e-3
        except:
            app.disconnect_from_oscope()

    def d1_od_callback(self):
        try:
            if self.d_one_od_spinner.text == 'PP':
                app.dev.dig_set_od(1, 0)
            else:
                app.dev.dig_set_od(1, 1)
        except:
            app.disconnect_from_oscope()

    def d1_freq_callback(self):
        try:
            app.dev.dig_set_freq(1, self.d_one_freq_slider.value)
        except:
            app.disconnect_from_oscope()

    def d1_duty_callback(self):
        try:
            if self.d_one_mode_spinner.text == 'PWM':
                app.dev.dig_set_duty(1, self.d_one_duty_slider.value / 100.)
            elif self.d_one_mode_spinner.text == 'SERVO':
                app.dev.dig_set_width(1, self.d_one_duty_slider.value)
        except:
            app.disconnect_from_oscope()

    def d2_button_callback(self):
        try:
            if not self.d_two_button.disabled:
                if self.d_two_button.state == 'down':
                    app.dev.dig_write(2, 1)
                else:
                    app.dev.dig_write(2, 0)
        except:
            app.disconnect_from_oscope()

    def d2_mode_callback(self):
        try:
            if self.d_two_mode_spinner.text == 'OUT':
                app.dev.dig_set_mode(2, 0)
                self.d_two_button.disabled = False
                self.d_two_freq_slider.slider.disabled = True
                self.d_two_freq_slider.snap_button.disabled = True
                self.d_two_duty_slider.slider.disabled = True
                self.d_two_duty_slider.snap_button.disabled = True
                if app.dev.connected:
                    if app.dev.dig_read(2) == 1:
                        self.d_two_button.state = 'down'
                    else:
                        self.d_two_button.state = 'normal'
            elif self.d_two_mode_spinner.text == 'IN':
                app.dev.dig_set_mode(2, 1)
                self.d_two_button.disabled = True
                self.d_two_button.state = 'normal'
                self.d_two_freq_slider.slider.disabled = True
                self.d_two_freq_slider.snap_button.disabled = True
                self.d_two_duty_slider.slider.disabled = True
                self.d_two_duty_slider.snap_button.disabled = True
                if self.update_job is None:
                    self.update_job = Clock.schedule_once(self.update_button_displays, 0.05)
            elif self.d_two_mode_spinner.text == 'PWM':
                app.dev.dig_set_mode(2, 2)
                self.d_two_button.disabled = True
                self.d_two_button.state = 'normal'
                self.d_two_freq_slider.slider.disabled = False
                self.d_two_freq_slider.snap_button.disabled = False
                if app.dev.connected:
                    self.d_two_freq_slider.slider.value = math.log10(app.dev.dig_get_freq(2))
                self.d_two_duty_slider.slider.disabled = False
                self.d_two_duty_slider.snap_button.disabled = False
                self.d_two_duty_slider.label_text = 'Duty\nCycle\n'
                self.d_two_duty_slider.units = '%'
                self.d_two_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_two_duty_slider.slider.value = 100. * app.dev.dig_get_duty(2)
                else:
                    self.d_two_duty_slider.slider.value = 50.
                self.d_two_duty_slider.minimum = 0.
                self.d_two_duty_slider.maximum = 100.
                self.d_two_duty_slider.step = 5.
            elif self.d_two_mode_spinner.text == 'SERVO':
                app.dev.dig_set_mode(2, 3)
                self.d_two_button.disabled = True
                self.d_two_button.state = 'normal'
                self.d_two_freq_slider.slider.disabled = True
                self.d_two_freq_slider.snap_button.disabled = True
                self.d_two_duty_slider.slider.disabled = False
                self.d_two_duty_slider.snap_button.disabled = False
                self.d_two_duty_slider.label_text = 'Pulse\nWidth\n'
                self.d_two_duty_slider.units = 's'
                self.d_two_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_two_duty_slider.slider.value = app.dev.dig_get_width(2)
                else:
                    self.d_two_duty_slider.slider.value = 1.5e-3
                self.d_two_duty_slider.minimum = 0.
                self.d_two_duty_slider.maximum = 4e-3
                self.d_two_duty_slider.step = 0.1e-3
        except:
            app.disconnect_from_oscope()

    def d2_od_callback(self):
        try:
            if self.d_two_od_spinner.text == 'PP':
                app.dev.dig_set_od(2, 0)
            else:
                app.dev.dig_set_od(2, 1)
        except:
            app.disconnect_from_oscope()

    def d2_freq_callback(self):
        try:
            app.dev.dig_set_freq(2, self.d_two_freq_slider.value)
        except:
            app.disconnect_from_oscope()

    def d2_duty_callback(self):
        try:
            if self.d_two_mode_spinner.text == 'PWM':
                app.dev.dig_set_duty(2, self.d_two_duty_slider.value / 100.)
            elif self.d_two_mode_spinner.text == 'SERVO':
                app.dev.dig_set_width(2, self.d_two_duty_slider.value)
        except:
            app.disconnect_from_oscope()

    def d3_button_callback(self):
        try:
            if not self.d_three_button.disabled:
                if self.d_three_button.state == 'down':
                    app.dev.dig_write(3, 1)
                else:
                    app.dev.dig_write(3, 0)
        except:
            app.disconnect_from_oscope()

    def d3_mode_callback(self):
        try:
            if self.d_three_mode_spinner.text == 'OUT':
                app.dev.dig_set_mode(3, 0)
                self.d_three_button.disabled = False
                self.d_three_freq_slider.slider.disabled = True
                self.d_three_freq_slider.snap_button.disabled = True
                self.d_three_duty_slider.slider.disabled = True
                self.d_three_duty_slider.snap_button.disabled = True
                if app.dev.connected:
                    if app.dev.dig_read(3) == 1:
                        self.d_three_button.state = 'down'
                    else:
                        self.d_three_button.state = 'normal'
            elif self.d_three_mode_spinner.text == 'IN':
                app.dev.dig_set_mode(3, 1)
                self.d_three_button.disabled = True
                self.d_three_button.state = 'normal'
                self.d_three_freq_slider.slider.disabled = True
                self.d_three_freq_slider.snap_button.disabled = True
                self.d_three_duty_slider.slider.disabled = True
                self.d_three_duty_slider.snap_button.disabled = True
                if self.update_job is None:
                    self.update_job = Clock.schedule_once(self.update_button_displays, 0.05)
            elif self.d_three_mode_spinner.text == 'PWM':
                app.dev.dig_set_mode(3, 2)
                self.d_three_button.disabled = True
                self.d_three_button.state = 'normal'
                self.d_three_freq_slider.slider.disabled = False
                self.d_three_freq_slider.snap_button.disabled = False
                if app.dev.connected:
                    self.d_three_freq_slider.slider.value = math.log10(app.dev.dig_get_freq(3))
                self.d_three_duty_slider.slider.disabled = False
                self.d_three_duty_slider.snap_button.disabled = False
                self.d_three_duty_slider.label_text = 'Duty\nCycle\n'
                self.d_three_duty_slider.units = '%'
                self.d_three_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_three_duty_slider.slider.value = 100. * app.dev.dig_get_duty(3)
                else:
                    self.d_three_duty_slider.slider.value = 50.
                self.d_three_duty_slider.minimum = 0.
                self.d_three_duty_slider.maximum = 100.
                self.d_three_duty_slider.step = 5.
            elif self.d_three_mode_spinner.text == 'SERVO':
                app.dev.dig_set_mode(3, 3)
                self.d_three_button.disabled = True
                self.d_three_button.state = 'normal'
                self.d_three_freq_slider.slider.disabled = True
                self.d_three_freq_slider.snap_button.disabled = True
                self.d_three_duty_slider.slider.disabled = False
                self.d_three_duty_slider.snap_button.disabled = False
                self.d_three_duty_slider.label_text = 'Pulse\nWidth\n'
                self.d_three_duty_slider.units = 's'
                self.d_three_duty_slider.step = 0.
                if app.dev.connected:
                    self.d_three_duty_slider.slider.value = app.dev.dig_get_width(3)
                else:
                    self.d_three_duty_slider.slider.value = 1.5e-3
                self.d_three_duty_slider.minimum = 0.
                self.d_three_duty_slider.maximum = 4e-3
                self.d_three_duty_slider.step = 0.1e-3
        except:
            app.disconnect_from_oscope()

    def d3_od_callback(self):
        try:
            if self.d_three_od_spinner.text == 'PP':
                app.dev.dig_set_od(3, 0)
            else:
                app.dev.dig_set_od(3, 1)
        except:
            app.disconnect_from_oscope()

    def d3_freq_callback(self):
        try:
            app.dev.dig_set_freq(3, self.d_three_freq_slider.value)
        except:
            app.disconnect_from_oscope()

    def d3_duty_callback(self):
        try:
            if self.d_three_mode_spinner.text == 'PWM':
                app.dev.dig_set_duty(3, self.d_three_duty_slider.value / 100.)
            elif self.d_three_mode_spinner.text == 'SERVO':
                app.dev.dig_set_width(3, self.d_three_duty_slider.value)
        except:
            app.disconnect_from_oscope()

class ScopeRoot(Screen):

    def __init__(self, **kwargs):
        super(ScopeRoot, self).__init__(**kwargs)

        self.toolbar_visible = False
        self.wavegen_visible = False
        self.xyplot_visible = False
        self.offset_waveform_visible = False
        self.digital_controls_visible = False
        self.meter_visible = False
        self.meter_ch1rms = False
        self.meter_ch2rms = False
        self.view_toolbar_visible = False

        self.read_offset_waveform = False
        self.offset_waveform_play_pause_button_update_job = None

    def on_oscope_disconnect(self):
        if self.offset_waveform_play_pause_button_update_job is not None:
            self.offset_waveform_play_pause_button_update_job.cancel()
            self.offset_waveform_play_pause_button_update_job = None

        self.scope_plot.on_oscope_disconnect()
        self.offset_waveform_plot.on_oscope_disconnect()
        self.digital_control_panel.on_oscope_disconnect()

        self.play_pause_button.source = kivy_resources.resource_find('play.png')
        self.play_pause_button.reload()

        self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('play.png')
        self.offset_waveform_play_pause_button.reload()

        self.read_offset_waveform = False

    def on_enter(self):
        try:
            if app.dev.connected:
                self.scope_plot.update_job = Clock.schedule_once(self.scope_plot.update_scope_plot, 0.1)

            if self.wavegen_visible:
                self.sync_preview()

            self.sync_offset_waveform()

            self.digital_control_panel.sync_controls()
            
            # Update meter label colors from theme
            app.update_meter_label_colors()
        except:
            pass

    def on_leave(self):
        if self.scope_plot.update_job is not None:
            self.scope_plot.update_job.cancel()
            self.scope_plot.update_job = None

        if self.digital_control_panel.update_job is not None:
            self.digital_control_panel.update_job.cancel()
            self.digital_control_panel.update_job = None

        if self.offset_waveform_play_pause_button_update_job is not None:
            self.offset_waveform_play_pause_button_update_job.cancel()
            self.offset_waveform_play_pause_button_update_job = None

    def toggle_toolbar(self):
        if self.toolbar_visible:
            anim = Animation(x_hint = 1, duration = 0.1)
            anim.start(self.scope_toolbar)
            self.toolbar_visible = False
        else:
            anim = Animation(x_hint = 0.94, duration = 0.1)
            anim.start(self.scope_toolbar)
            self.toolbar_visible = True

    def toggle_offset_waveform(self):
        if self.offset_waveform_visible:
            anim = Animation(right_hint = 0, duration = 0.3)
            anim.start(self.offset_waveform_control_panel)
            self.offset_waveform_visible = False
            self.scope_plot.reset_touches()
            self.scope_xyplot.reset_touches()
            self.wavegen_plot.reset_touches()
        else:
            self.sync_offset_waveform()
            anim = Animation(right_hint = 0.6, duration = 0.3)
            anim.start(self.offset_waveform_control_panel)
            self.offset_waveform_visible = True
            #self.offset_waveform_plot.reset_touches()

    def toggle_wavegen(self):
        if self.wavegen_visible:
            anim = Animation(right_hint = 0, duration = 0.3)
            anim.start(self.wavegen)
            self.wavegen_visible = False
            self.scope_plot.reset_touches()
            self.scope_xyplot.reset_touches()
        else:
            self.sync_preview()
            anim = Animation(right_hint = 0.6, duration = 0.3)
            anim.start(self.wavegen)
            self.wavegen_visible = True
            self.wavegen_plot.reset_touches()

    def toggle_xyplot(self):
        if self.xyplot_visible:
            anim = Animation(right_hint = 0, duration = 0.3)
            anim.start(self.xyplot)
            self.xyplot_visible = False
            self.scope_plot.reset_touches()
        else:
            anim = Animation(right_hint = 0.6, duration = 0.3)
            anim.start(self.xyplot)
            self.xyplot_visible = True
            self.scope_xyplot.reset_touches()

    def toggle_digital_controls(self):
        if self.digital_controls_visible:
            anim = Animation(right_hint = 0, duration = 0.3)
            anim.start(self.digital_controls)
            self.digital_controls_visible = False
        else:
            anim = Animation(right_hint = 0.6, duration = 0.3)
            anim.start(self.digital_controls)
            self.digital_controls_visible = True

    def toggle_meter(self):
        if self.meter_visible:
            anim = Animation(y_hint = 1., duration = 0.1)
            anim.start(self.meter)
            self.meter_visible = False
        else:
            anim = Animation(y_hint = 0.75, duration = 0.1)
            anim.start(self.meter)
            self.meter_visible = True

    def toggle_view_toolbar(self):
        if self.view_toolbar_visible:
            anim = Animation(y_hint = 1., duration = 0.1)
            anim.start(self.view_toolbar)
            self.view_toolbar_visible = False
        else:
            anim = Animation(y_hint = 7 / 9, duration = 0.1)
            anim.start(self.view_toolbar)
            self.view_toolbar_visible = True

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if app.save_dialog_visible:
            return False

        if self.offset_waveform_visible:
            self.offset_waveform_plot.on_keyboard_down(keyboard, keycode, text, modifiers)
        elif self.wavegen_visible:
            self.wavegen_plot.on_keyboard_down(keyboard, keycode, text, modifiers)
        elif self.xyplot_visible:
            self.scope_xyplot.on_keyboard_down(keyboard, keycode, text, modifiers)
        else:
            self.scope_plot.on_keyboard_down(keyboard, keycode, text, modifiers)

        return True

    def nearest_one_three(self, x):
        exponent = math.floor(x)
        mantissa = x - exponent
        if mantissa < math.log10(math.sqrt(3.)):
            mantissa = 0.
        elif mantissa < math.log10(math.sqrt(30.)):
            mantissa = math.log10(3.)
        else:
            mantissa = 0.
            exponent += 1.
        return exponent + mantissa

    def sync_offset_waveform(self):
        if not app.dev.connected:
            return

        try:
            if not self.read_offset_waveform:
                self.read_offset_waveform = True

                offset_interval = app.dev.get_offset_interval()
                self.offset_waveform_interval_slider.value = math.log10(offset_interval)
                self.offset_waveform_plot.offset_interval = offset_interval

                samples = app.dev.read_offset_waveform_as_voltages()
                num_samples = len(samples)
                self.offset_waveform_plot.num_samples = num_samples
                if num_samples > 0:
                    self.offset_waveform_plot.curves['OffsetWaveform'].points_x = [offset_interval * np.arange(num_samples)]
                    self.offset_waveform_plot.curves['OffsetWaveform'].points_y = [np.array(samples)]

                    self.offset_waveform_plot.yaxes['left'].ylabel_value = f'Offset Waveform: {num_samples:d} points, interval = {app.num2str(offset_interval, 4)}s'
                    self.offset_waveform_plot.xlim = [0., offset_interval * num_samples]

                    self.offset_waveform_plot.refresh_plot()

            if app.dev.get_offset_mode() == 1:
                self.offset_waveform_repeat_button.state = 'down'
            else:
                self.offset_waveform_repeat_button.state = 'normal'

            [sweep_in_progress, samples_left] = app.dev.offset_get_sweep_progress()
            if sweep_in_progress == 1:
                if self.offset_waveform_repeat_button.state == 'down':
                    self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('pause.png')
                else:
                    if self.offset_waveform_play_pause_button_update_job is None:
                        time_left = samples_left * self.offset_waveform_plot.offset_interval
                        self.offset_waveform_play_pause_button_update_job = Clock.schedule_once(self.update_offset_waveform_play_pause_button, time_left)
                    self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('stop.png')
            else:
                self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('play.png')
            self.offset_waveform_play_pause_button.reload()
        except:
            app.disconnect_from_oscope()

    def update_offset_waveform_play_pause_button(self, t):
        self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('play.png')
        self.offset_waveform_play_pause_button.reload()
        self.offset_waveform_play_pause_button_update_job = None

    def offset_waveform_play_pause_button_callback(self):
        if not app.dev.connected:
            return
        try:
            if app.dev.offset_sweep_in_progress():
                app.dev.offset_stop()
                if self.offset_waveform_play_pause_button_update_job is not None:
                    self.offset_waveform_play_pause_button_update_job.cancel()
                    self.offset_waveform_play_pause_button_update_job = None
                self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('play.png')
            else:
                app.dev.offset_start()
                if self.offset_waveform_repeat_button.state == 'down':
                    self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('pause.png')
                else:
                    time_left = self.offset_waveform_plot.num_samples * self.offset_waveform_plot.offset_interval
                    self.offset_waveform_play_pause_button_update_job = Clock.schedule_once(self.update_offset_waveform_play_pause_button, time_left)
                    self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('stop.png')
            self.offset_waveform_play_pause_button.reload()
        except:
            app.disconnect_from_oscope()

    def offset_waveform_repeat_button_callback(self):
        if not app.dev.connected:
            return

        try:
            new_mode = 1 - app.dev.get_offset_mode()
            app.dev.set_offset_mode(new_mode)

            [sweep_in_progress, samples_left] = app.dev.offset_get_sweep_progress()
            if sweep_in_progress == 1:
                if new_mode == 1:
                    if self.offset_waveform_play_pause_button_update_job is not None:
                        self.offset_waveform_play_pause_button_update_job.cancel()
                        self.offset_waveform_play_pause_button_update_job = None
                    self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('pause.png')
                else:
                    if self.offset_waveform_play_pause_button_update_job is None:
                        time_left = samples_left * self.offset_waveform_plot.offset_interval
                        self.offset_waveform_play_pause_button_update_job = Clock.schedule_once(self.update_offset_waveform_play_pause_button, time_left)
                    self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('stop.png')
                self.offset_waveform_play_pause_button.reload()
        except:
            app.disconnect_from_oscope()

    def offset_waveform_interval_slider_callback(self):
        if not app.dev.connected:
            return

        try:
            value = self.offset_waveform_interval_slider.value
            if self.offset_waveform_interval_snap_button.state == 'down':
                value = self.nearest_one_three(value)
            offset_interval = math.pow(10., value)
            app.dev.set_offset_interval(offset_interval)

            self.offset_waveform_plot.offset_interval = offset_interval
            num_samples = self.offset_waveform_plot.num_samples
            if num_samples != 0:
                self.offset_waveform_plot.curves['OffsetWaveform'].points_x = [offset_interval * np.arange(num_samples)]
                self.offset_waveform_plot.yaxes['left'].ylabel_value = f'Offset Waveform: {num_samples:d} points, interval = {app.num2str(offset_interval, 4)}s'
                self.offset_waveform_plot.xlim = [0., offset_interval * num_samples]
                self.offset_waveform_plot.refresh_plot()

            if self.offset_waveform_play_pause_button_update_job is not None:
                self.offset_waveform_play_pause_button_update_job.cancel()
                self.offset_waveform_play_pause_button_update_job = None

            self.offset_waveform_play_pause_button.source = kivy_resources.resource_find('play.png')
            self.offset_waveform_play_pause_button.reload()
        except:
            app.disconnect_from_oscope()

    def toggle_h_cursors(self):
        self.scope_plot.show_h_cursors = not self.scope_plot.show_h_cursors
        self.scope_plot.show_sampling_rate = not self.scope_plot.show_sampling_rate
        self.scope_plot.refresh_plot()

    def toggle_v_cursors(self):
        self.scope_plot.show_v_cursors = not self.scope_plot.show_v_cursors
        self.scope_plot.refresh_plot()

    def set_trigger_src_ch1(self):
        self.scope_plot.trigger_source = 'CH1'
        self.scope_plot.refresh_plot()

    def set_trigger_src_ch2(self):
        self.scope_plot.trigger_source = 'CH2'
        self.scope_plot.refresh_plot()

    def set_trigger_edge_rising(self):
        self.scope_plot.trigger_edge = 'Rising'

    def set_trigger_edge_falling(self):
        self.scope_plot.trigger_edge = 'Falling'

    def play_pause(self):
        try:
            if self.scope_plot.trigger_repeat:
                if self.scope_plot.trigger_mode == 'Single':
                    self.scope_plot.trigger_mode = 'Continuous'
                    self.play_pause_button.source = kivy_resources.resource_find('pause.png')
                    self.play_pause_button.reload()
                elif self.scope_plot.trigger_mode == 'Continuous':
                    if app.dev.connected and app.dev.sweep_in_progress():
                        # Set the sampling interval to its current value, which has 
                        #   the side effect of canceling the sweep in progress.
                        app.dev.set_period(app.dev.sampling_interval)
                    self.scope_plot.trigger_mode = 'Single'
                    self.play_pause_button.source = kivy_resources.resource_find('play.png')
                    self.play_pause_button.reload()
            else:
                if app.dev.connected:
                    if app.dev.sweep_in_progress():
                        # Set the sampling interval to its current value, which has 
                        #   the side effect of canceling the sweep in progress.
                        app.dev.set_period(app.dev.sampling_interval)
                        self.scope_plot.trigger_mode = 'Single'
                        self.play_pause_button.source = kivy_resources.resource_find('play.png')
                        self.play_pause_button.reload()
                    else:
                        self.scope_plot.trigger_mode = 'Armed'
                        self.play_pause_button.source = kivy_resources.resource_find('stop.png')
                        self.play_pause_button.reload()
                else:
                    self.scope_plot.trigger_mode = 'Single'
                    self.play_pause_button.source = kivy_resources.resource_find('play.png')
                    self.play_pause_button.reload()
        except:
            app.disconnect_from_oscope()

    def toggle_trigger_repeat(self):
        try:
            self.scope_plot.trigger_repeat = not self.scope_plot.trigger_repeat
            if (self.scope_plot.trigger_repeat == False) and (self.scope_plot.trigger_mode == 'Continuous'):
                self.scope_plot.trigger_mode = 'Single'
                self.play_pause_button.source = kivy_resources.resource_find('stop.png')
                self.play_pause_button.reload()
            elif (self.scope_plot.trigger_repeat == True) and (self.scope_plot.trigger_mode == 'Single'):
                if app.dev.connected and app.dev.sweep_in_progress():
                    self.scope_plot.trigger_mode = 'Continuous'
                    self.play_pause_button.source = kivy_resources.resource_find('pause.png')
                    self.play_pause_button.reload()
                else:
                    self.play_pause_button.source = kivy_resources.resource_find('play.png')
                    self.play_pause_button.reload()
        except:
            app.disconnect_from_oscope()

    def xyplot_swap_axes(self):
        self.scope_xyplot.swap_axes()
        self.xy_h_cursors_button.state, self.xy_v_cursors_button.state = self.xy_v_cursors_button.state, self.xy_h_cursors_button.state

    def toggle_xy_h_cursors(self):
        self.scope_xyplot.toggle_h_cursors()

    def toggle_xy_v_cursors(self):
        self.scope_xyplot.toggle_v_cursors()

    def sync_scope_to_wavegen(self):
        """Sync scope plot view and sampling rate to match wavegen period."""
        frequency = self.wavegen_plot.frequency
        period = 1.0 / frequency
        
        # Calculate sampling interval so buffer (1500 samples) shows ~3 periods
        # This gives good resolution while showing context around trigger
        num_samples = app.dev.SCOPE_BUFFER_SIZE // 2  # 1500 samples per channel
        desired_periods_in_buffer = 3.0
        ideal_interval = (desired_periods_in_buffer * period) / num_samples
        
        # Set the sampling interval if connected
        if app.dev.connected:
            try:
                app.dev.set_period(ideal_interval)
                # Update the actual sampling interval from device
                actual_interval = app.dev.sampling_interval
            except:
                app.disconnect_from_oscope()
                return
        else:
            actual_interval = ideal_interval
        
        # Set the scope plot view to show one period centered at trigger (t=0)
        self.scope_plot.xlim = [-period / 2, period / 2]
        self.scope_plot.refresh_plot()

    def sync_preview(self):
        if not app.dev.connected:
            return

        try:
            self.wavegen_plot.shape = app.dev.get_shape()
            self.wavegen_plot.frequency = app.dev.get_freq()
            self.wavegen_plot.amplitude = app.dev.get_amplitude()
            self.wavegen_plot.offset = app.dev.get_offset()

            app.dev.set_shape(self.wavegen_plot.shape)
            app.dev.set_freq(self.wavegen_plot.frequency)
            app.dev.set_amplitude(self.wavegen_plot.amplitude)
            app.dev.set_offset(self.wavegen_plot.offset)

            if self.wavegen_plot.shape == 'DC':
                self.dc_button.state = 'down'
                self.sin_button.state = 'normal'
                self.square_button.state = 'normal'
                self.triangle_button.state = 'normal'
            elif self.wavegen_plot.shape == 'SIN':
                self.dc_button.state = 'normal'
                self.sin_button.state = 'down'
                self.square_button.state = 'normal'
                self.triangle_button.state = 'normal'
            elif self.wavegen_plot.shape == 'SQUARE':
                self.dc_button.state = 'normal'
                self.sin_button.state = 'normal'
                self.square_button.state = 'down'
                self.triangle_button.state = 'normal'
            elif self.wavegen_plot.shape == 'TRIANGLE':
                self.dc_button.state = 'normal'
                self.sin_button.state = 'normal'
                self.square_button.state = 'normal'
                self.triangle_button.state = 'down'

            foo = math.log10(self.wavegen_plot.frequency)
            bar = math.floor(foo)
            foobar = foo - bar
            if foobar < 0.5 * math.log10(2.001):
                self.wavegen_plot.xlim[1] = 1. / math.pow(10., bar)
            elif foobar < 0.5 * math.log10(2.001 * 5.001):
                self.wavegen_plot.xlim[1] = 0.5 / math.pow(10., bar)
            elif foobar < 0.5 * math.log10(5.001 * 10.001):
                self.wavegen_plot.xlim[1] = 0.2 / math.pow(10., bar)
            else:
                self.wavegen_plot.xlim[1] = 0.1 / math.pow(10., bar)

            self.wavegen_plot.update_preview()
            self.wavegen_plot.refresh_plot()

            if self.wavegen_plot.shape == 'SQUARE':
                self.offset_adj_slider.value = app.dev.get_sq_offset_adj()
            else:
                self.offset_adj_slider.value = app.dev.get_nsq_offset_adj()
        except:
            app.disconnect_from_oscope()

    def set_shape(self, shape):
        self.wavegen_plot.shape = shape
        self.wavegen_plot.update_preview()
        self.wavegen_plot.refresh_plot()
        if not app.dev.connected:
            return

        try:
            app.dev.set_shape(shape)
            if shape == 'SQUARE':
                self.offset_adj_slider.value = app.dev.get_sq_offset_adj()
            else:
                self.offset_adj_slider.value = app.dev.get_nsq_offset_adj()
        except:
            app.disconnect_from_oscope()

    def set_frequency(self, frequency):
        if not app.dev.connected:
            return

        try:
            app.dev.set_freq(frequency)
            self.wavegen_plot.frequency = app.dev.get_freq()
        except:
            app.disconnect_from_oscope()

    def set_amplitude(self, amplitude):
        if not app.dev.connected:
            return

        try:
            app.dev.set_amplitude(amplitude)
            self.wavegen_plot.amplitude = amplitude
        except:
            app.disconnect_from_oscope()

    def set_offset(self, offset):
        if not app.dev.connected:
            return

        try:
            app.dev.set_offset(offset)
#            self.wavegen_plot.offset = app.dev.get_offset()
        except:
            app.disconnect_from_oscope()

    def update_offset_adj(self):
        if not app.dev.connected:
            return

        try:
            if self.wavegen_plot.shape == 'SQUARE':
                app.dev.set_sq_offset_adj(int(self.offset_adj_slider.value))
            else:
                app.dev.set_nsq_offset_adj(int(self.offset_adj_slider.value))
        except:
            app.disconnect_from_oscope()

    def pan_left(self):
        if self.offset_waveform_visible:
            pass
        elif self.wavegen_visible:
            pass
        elif self.xyplot_visible:
            self.scope_xyplot.pan_left()
        else:
            self.scope_plot.pan_left()

    def pan_up(self):
        if self.offset_waveform_visible:
            self.offset_waveform_plot.pan_up()
        elif self.wavegen_visible:
            self.wavegen_plot.pan_up()
        elif self.xyplot_visible:
            self.scope_xyplot.pan_up()
        else:
            self.scope_plot.pan_up(yaxis = self.scope_plot.left_yaxis)

    def pan_down(self):
        if self.offset_waveform_visible:
            self.offset_waveform_plot.pan_down()
        elif self.wavegen_visible:
            self.wavegen_plot.pan_down()
        elif self.xyplot_visible:
            self.scope_xyplot.pan_down()
        else:
            self.scope_plot.pan_down(yaxis = self.scope_plot.left_yaxis)

    def pan_right(self):
        if self.offset_waveform_visible:
            pass
        elif self.wavegen_visible:
            pass
        elif self.xyplot_visible:
            self.scope_xyplot.pan_right()
        else:
            self.scope_plot.pan_right()

    def home_view(self):
        if self.offset_waveform_visible:
            self.offset_waveform_plot.home_view()
        elif self.wavegen_visible:
            self.wavegen_plot.home_view()
        elif self.xyplot_visible:
            self.scope_xyplot.home_view()
        else:
            self.scope_plot.home_view()

    def zoom_in_y(self):
        if self.offset_waveform_visible:
            self.offset_waveform_plot.zoom_in_y()
        elif self.wavegen_visible:
            self.wavegen_plot.zoom_in_y()
        elif self.xyplot_visible:
            self.scope_xyplot.zoom_in_y()
        else:
            self.scope_plot.zoom_in_y(yaxis = self.scope_plot.left_yaxis)

    def zoom_out_y(self):
        if self.offset_waveform_visible:
            self.offset_waveform_plot.zoom_out_y()
        elif self.wavegen_visible:
            self.wavegen_plot.zoom_out_y()
        elif self.xyplot_visible:
            self.scope_xyplot.zoom_out_y()
        else:
            self.scope_plot.zoom_out_y(yaxis = self.scope_plot.left_yaxis)

    def zoom_in_x(self):
        if self.offset_waveform_visible:
            pass
        elif self.wavegen_visible:
            pass
        elif self.xyplot_visible:
            self.scope_xyplot.zoom_in_x()
        else:
            self.scope_plot.zoom_in_x()

    def zoom_out_x(self):
        if self.offset_waveform_visible:
            pass
        elif self.wavegen_visible:
            pass
        elif self.xyplot_visible:
            self.scope_xyplot.zoom_out_x()
        else:
            self.scope_plot.zoom_out_x()

    def set_ch1_rms(self):
        self.meter_ch1rms = True

    def set_ch1_mean(self):
        self.meter_ch1rms = False

    def set_ch2_rms(self):
        self.meter_ch2rms = True

    def set_ch2_mean(self):
        self.meter_ch2rms = False

class BodeRoot(Screen):

    def __init__(self, **kwargs):
        super(BodeRoot, self).__init__(**kwargs)

        self.state_handler = None

        self.index = 0
        self.sweep_in_progress = False

        self.bode_toolbar_visible = False
        self.bode_controls_visible = False

    def on_oscope_disconnect(self):
        if self.sweep_in_progress:
            self.stop_sweep()

    def on_enter(self):
        pass

    def on_leave(self):
        if self.sweep_in_progress:
            self.stop_sweep()

    def toggle_bode_toolbar(self):
        if self.bode_toolbar_visible:
            anim = Animation(x_hint = 1, duration = 0.1)
            anim.start(self.bode_toolbar)
            self.bode_toolbar_visible = False
        else:
            anim = Animation(x_hint = 0.94, duration = 0.1)
            anim.start(self.bode_toolbar)
            self.bode_toolbar_visible = True

    def toggle_bode_controls(self):
        pass

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if app.save_dialog_visible:
            return False

        self.bode_plot.on_keyboard_down(keyboard, keycode, text, modifiers)

        return True

    def play_stop(self):
        if not self.sweep_in_progress:
            self.start_sweep()
        else:
            self.stop_sweep()

    def toggle_pointmarkers(self):
        if self.pointmarkers_button.state == 'down':
            self.bode_plot.default_marker = '.'
        else:
            self.bode_plot.default_marker = ''

        try:
            self.bode_plot.configure_curve('gain', marker = self.bode_plot.default_marker)
            self.bode_plot.configure_curve('phase', marker = self.bode_plot.default_marker)
        except NameError:
            pass

    def start_sweep(self):
        if not app.dev.connected:
            self.stop_sweep()
            return

        self.sweep_in_progress = True
        self.play_stop_button.source = kivy_resources.resource_find('stop.png')
        self.play_stop_button.reload()

        num_points = int(self.num_points_slider.value)
        if num_points == 1:
            self.target_freq = [self.start_freq_slider.value]
        else:
            self.target_freq = list(np.logspace(math.log10(self.start_freq_slider.value), math.log10(self.end_freq_slider.value), num_points))
        self.freq = []
        self.gain = []
        self.phase = []
        self.index = 0

        try:
            app.dev.wave(shape = 'SIN', freq = self.target_freq[0], amplitude = self.amplitude_slider.value, offset = self.offset_slider.value)
            app.dev.set_period(12. / (app.dev.SCOPE_BUFFER_SIZE * self.target_freq[0]))
        except:
            app.disconnect_from_oscope()

        self.state_handler = Clock.schedule_once(self.trigger, 0.05)

    def stop_sweep(self):
        if self.state_handler is not None:
            self.state_handler.cancel()
            self.state_handler = None

        self.sweep_in_progress = False
        self.play_stop_button.source = kivy_resources.resource_find('play.png')
        self.play_stop_button.reload()

    def trigger(self, t):
        try:
            scope_buffer = app.dev.trigger()
            if app.dev.sweep_in_progress():
                self.state_handler = Clock.schedule_once(self.wait_for_sweep, 0.01)
                return
            self.process_buffer(scope_buffer)
        except:
            app.disconnect_from_oscope()

    def wait_for_sweep(self, t):
        try:
            if app.dev.sweep_in_progress():
                self.state_handler = Clock.schedule_once(self.wait_for_sweep, 0.01)
                return
            scope_buffer = app.dev.get_bufferbin()
            self.process_buffer(scope_buffer)
        except:
            app.disconnect_from_oscope()

    def process_buffer(self, scope_buffer):
        try:
            sampling_interval = app.dev.sampling_interval
            ch1_range = app.dev.ch1_range
            ch2_range = app.dev.ch2_range

            if sampling_interval == 0.25e-6:
                ch1_zero = app.dev.ch1_zero_4MSps[ch1_range]
                ch1_gain = app.dev.ch1_gain_4MSps[ch1_range]
                ch2_zero = app.dev.ch2_zero_4MSps[ch2_range]
                ch2_gain = app.dev.ch2_gain_4MSps[ch2_range]
            else:
                ch1_zero = app.dev.ch1_zero[app.dev.num_avg][ch1_range]
                ch1_gain = app.dev.ch1_gain[app.dev.num_avg][ch1_range]
                ch2_zero = app.dev.ch2_zero[app.dev.num_avg][ch2_range]
                ch2_gain = app.dev.ch2_gain[app.dev.num_avg][ch2_range]

            num_samples = app.dev.SCOPE_BUFFER_SIZE // 2
            ch1 = [app.dev.volts_per_lsb[ch1_range] * ch1_gain * (sample - ch1_zero) for sample in scope_buffer[0:num_samples]]
            ch2 = [app.dev.volts_per_lsb[ch2_range] * ch2_gain * (sample - ch2_zero) for sample in scope_buffer[num_samples:]]

            freq = app.dev.get_freq()

            per_est = 1. / (sampling_interval * freq)
            per_est_int = int(per_est)
            per_est_frac = per_est - float(per_est_int)

            Z = range(num_samples)
            s = [math.sin(2. * math.pi * i / per_est) for i in Z]
            c = [math.cos(2. * math.pi * i / per_est) for i in Z]

            ch1_s = [ch1[i] * s[i] for i in Z]
            ch1_c = [ch1[i] * c[i] for i in Z]
            ch2_s = [ch2[i] * s[i] for i in Z]
            ch2_c = [ch2[i] * c[i] for i in Z]

            ch1_A_cos_phi = [2. * (sum(ch1_s[i:i + per_est_int]) - 0.5 * (ch1_s[i] + ch1_s[i + per_est_int]) + per_est_frac * (ch1_s[i + per_est_int] + 0.5 * per_est_frac * (ch1_s[i + per_est_int + 1] - ch1_s[i + per_est_int]))) / per_est for i in range(num_samples - per_est_int - 1)]
            ch1_A_sin_phi = [2. * (sum(ch1_c[i:i + per_est_int]) - 0.5 * (ch1_c[i] + ch1_c[i + per_est_int]) + per_est_frac * (ch1_c[i + per_est_int] + 0.5 * per_est_frac * (ch1_c[i + per_est_int + 1] - ch1_c[i + per_est_int]))) / per_est for i in range(num_samples - per_est_int - 1)]
            ch2_A_cos_phi = [2. * (sum(ch2_s[i:i + per_est_int]) - 0.5 * (ch2_s[i] + ch2_s[i + per_est_int]) + per_est_frac * (ch2_s[i + per_est_int] + 0.5 * per_est_frac * (ch2_s[i + per_est_int + 1] - ch2_s[i + per_est_int]))) / per_est for i in range(num_samples - per_est_int - 1)]
            ch2_A_sin_phi = [2. * (sum(ch2_c[i:i + per_est_int]) - 0.5 * (ch2_c[i] + ch2_c[i + per_est_int]) + per_est_frac * (ch2_c[i + per_est_int] + 0.5 * per_est_frac * (ch2_c[i + per_est_int + 1] - ch2_c[i + per_est_int]))) / per_est for i in range(num_samples - per_est_int - 1)]

            ch1_AcosPhi = sum(ch1_A_cos_phi) / float(len(ch1_A_cos_phi))
            ch1_AsinPhi = sum(ch1_A_sin_phi) / float(len(ch1_A_sin_phi))
            ch2_AcosPhi = sum(ch2_A_cos_phi) / float(len(ch2_A_cos_phi))
            ch2_AsinPhi = sum(ch2_A_sin_phi) / float(len(ch2_A_sin_phi))

            ch2_offset = 2. * math.pi * 0.125e-6 * freq
            ch2_AcosPhi, ch2_AsinPhi = ch2_AcosPhi * math.cos(ch2_offset) + ch2_AsinPhi * math.sin(ch2_offset), ch2_AsinPhi * math.cos(ch2_offset) - ch2_AcosPhi * math.sin(ch2_offset)

            ch1_A = math.sqrt(ch1_AcosPhi ** 2 + ch1_AsinPhi ** 2)
            ch2_A = math.sqrt(ch2_AcosPhi ** 2 + ch2_AsinPhi ** 2)

            gain = 20. * math.log10(ch2_A / ch1_A)
            sign = 1. if ch1_AcosPhi * ch2_AsinPhi - ch1_AsinPhi * ch2_AcosPhi >= 0. else -1.
            phase = sign * 180. * math.acos((ch1_AcosPhi * ch2_AcosPhi + ch1_AsinPhi * ch2_AsinPhi) / (ch1_A * ch2_A)) / math.pi

            self.freq.append(freq)
            self.gain.append(gain)
            self.phase.append(phase)

            self.bode_plot.semilogx(np.array(self.freq), np.array(self.gain), 'm.m-' if self.pointmarkers_button.state == 'down' else 'm-', name = 'gain', yaxis = 'left')
            self.bode_plot.semilogx(np.array(self.freq), np.array(self.phase), 'c.c-' if self.pointmarkers_button.state == 'down' else 'c-', name = 'phase', yaxis = 'right', hold = 'on')
            self.bode_plot.xlimits([min(self.target_freq), max(self.target_freq)])

            self.index += 1
            if self.index < len(self.target_freq):
                app.dev.set_freq(self.target_freq[self.index])
                app.dev.set_period(12. / (app.dev.SCOPE_BUFFER_SIZE * self.target_freq[self.index]))
                self.state_handler = Clock.schedule_once(self.trigger, 0.05)
            elif self.trigger_repeat_button.state == 'down':
                self.start_sweep()
            else:
                self.stop_sweep()
        except:
            app.disconnect_from_oscope()

class RootWidget(ScreenManager):

    def __init__(self, **kwargs):
        super(RootWidget, self).__init__(**kwargs)
        self.keyboard = None
        self.bind_keyboard()

    def bind_keyboard(self):
        if platform != 'android' and self.keyboard is None:
            self.keyboard = Window.request_keyboard(self.keyboard_closed, self, 'text')
            self.keyboard.bind(on_key_down = self.on_keyboard_down)
        else:
            self.keyboard = None

    def keyboard_closed(self):
        if self.keyboard is not None:
            self.keyboard.unbind(on_key_down = self.on_keyboard_down)
        self.keyboard = None

    def on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, key = keycode

        if key == 'q' and 'ctrl' in modifiers:
            app.close_application()
            return True

        if self.current == 'scope':
            self.scope.on_keyboard_down(keyboard, keycode, text, modifiers)
        elif self.current == 'bode':
            self.bode.on_keyboard_down(keyboard, keycode, text, modifiers)

        return True

class MainApp(App):
    # Font settings as Kivy properties for proper binding in KV
    fontname = StringProperty('Roboto')
    fontscale = NumericProperty(1.0)  # Scale factor (1.0 = 100%)
    
    # Color theme property
    color_theme = StringProperty('default')

    def __init__(self, **kwargs):
        super(MainApp, self).__init__(**kwargs)
        # Settings manager already initialized at module load time for font config
        
        self.dev = oscope.oscope()
        self.connect_job = None
        self.save_dialog_visible = False
        self.save_dialog_path = os.path.expanduser('~')
        self.save_dialog_file = None
        
        # Load font settings from persistent storage
        self.fontscale = settings_manager.font_scale
        self.fontname = settings_manager.font_name
        
        # Load launch maximized setting
        self.launch_maximized = settings_manager.launch_maximized

        self.tooltip_delay = settings_manager.tooltip_delay
        
        # Load color theme setting
        self.color_theme = settings_manager.color_theme
        
        # Settings dialog visibility and update job
        self.settings_dialog_visible = False
        self.settings_update_job = None

    def build(self):
        self.root = RootWidget()
        self.title = f"Whoa-Scope v{__version__}"
        self.root.current = 'scope'
        
        # Apply launch maximized setting
        if settings_manager.launch_maximized:
            Window.maximize()
        
        if self.dev.connected:
            self.root.scope.scope_plot.update_job = Clock.schedule_once(self.root.scope.scope_plot.update_scope_plot, 0.1)
            self.root.scope.digital_control_panel.sync_controls()
        else:
            self.connect_job = Clock.schedule_once(self.connect_to_oscope, 0.2)
        return self.root
    
    def get_serial_port_info(self):
        """Get detailed information about serial ports for the settings panel."""
        port_info = []
        devices = list_ports.comports()
        
        for device in devices:
            info = {
                'port': device.device,
                'description': device.description,
                'hwid': device.hwid,
                'vid': device.vid,
                'pid': device.pid,
                'serial_number': device.serial_number,
                'manufacturer': device.manufacturer,
                'product': device.product,
                'is_oscope': device.vid == 0x6666 and device.pid == 0xCDC,
            }
            port_info.append(info)
        
        return port_info
    
    def get_connection_status_text(self):
        """Get formatted connection status text for display."""
        if self.dev.connected:
            try:
                port_name = self.dev.dev.port if self.dev.dev else "Unknown"
                return f"[color=#00FF00][b]Connected[/b][/color] to {port_name}"
            except:
                return "[color=#00FF00][b]Connected[/b][/color]"
        else:
            return "[color=#FF0000][b]Disconnected[/b][/color]"
    
    def get_serial_ports_text(self):
        """Get formatted list of serial ports for display."""
        ports = self.get_serial_port_info()
        if not ports:
            return "No serial ports detected"
        
        lines = []
        for port in ports:
            status = "[color=#00FF00]●[/color]" if port['is_oscope'] else "[color=#888888]○[/color]"
            desc = port['description'] or "Unknown device"
            vid_pid = f"VID:0x{port['vid']:04X} PID:0x{port['pid']:04X}" if port['vid'] else ""
            lines.append(f"{status} {port['port']}: {desc}")
            if vid_pid:
                lines.append(f"    {vid_pid}")
        
        return "\\n".join(lines)
    
    def get_available_fonts(self):
        """Get list of available font names for the spinner."""
        return list(AVAILABLE_FONTS.keys())
    
    def update_fontscale(self, scale):
        """Update font scale and save to settings."""
        self.fontscale = float(scale)
        settings_manager.font_scale = float(scale)
    
    def update_fontname(self, name):
        """Update font name and save to settings."""
        self.fontname = name
        settings_manager.font_name = name
    
    def update_launch_maximized(self, value):
        """Update launch maximized setting and save."""
        self.launch_maximized = value
        settings_manager.launch_maximized = value
    
    def update_tooltip_delay(self, delay):
        """Update tooltip delay setting and save."""
        settings_manager.tooltip_delay = delay
    
    def get_available_themes(self):
        """Get list of available theme names for the spinner."""
        return AVAILABLE_THEMES
    
    def get_theme_display_name(self, theme_key):
        """Get the display name for a theme key."""
        return COLOR_THEMES.get(theme_key, {}).get('name', theme_key)
    
    def get_theme_preview_color(self, theme_name, color_key):
        """Get a color value for theme preview swatches."""
        if theme_name == 'custom':
            custom_theme = settings_manager.custom_theme
            if custom_theme and color_key in custom_theme:
                return custom_theme[color_key]
        if theme_name in COLOR_THEMES:
            return COLOR_THEMES[theme_name].get(color_key, '#FFFFFF')
        return '#FFFFFF'
    
    def get_color_from_hex(self, color_value):
        """Convert hex color to RGBA tuple for canvas use."""
        if isinstance(color_value, str) and color_value.startswith('#'):
            return get_color_from_hex(color_value)
        elif isinstance(color_value, (list, tuple)):
            return color_value
        return (1, 1, 1, 1)
    
    def reset_custom_theme_and_refresh(self, dialog):
        """Reset custom theme and refresh the color picker buttons in the dialog."""
        self.reset_custom_theme()
        # Update the color picker buttons if they exist
        try:
            if hasattr(dialog, 'ids'):
                for color_key in ['ch1_color', 'ch2_color', 'plot_background', 'axes_background', 
                                  'axes_color', 'grid_color', 'gain_color', 'phase_color']:
                    btn_id = f'custom_{color_key.replace("_color", "").replace("plot_", "").replace("axes_", "")}_btn'
                    if btn_id in dialog.ids:
                        dialog.ids[btn_id].color_value = self.get_custom_theme_color(color_key)
        except Exception as e:
            print(f"Error refreshing color buttons: {e}")
    
    def get_current_theme(self):
        """Get the current theme's color dictionary."""
        return settings_manager.get_current_theme()
    
    def update_color_theme(self, theme_name):
        """Update color theme and save to settings."""
        self.color_theme = theme_name
        settings_manager.color_theme = theme_name
        # Apply theme to plots
        self.apply_color_theme()
    
    def apply_color_theme(self):
        """Apply the current color theme to all plots and UI elements."""
        theme = self.get_current_theme()
        
        # Apply to plots if they exist
        if hasattr(self, 'root') and self.root is not None:
            try:
                scope = self.root.scope
                # Update ScopePlot colors
                scope.scope_plot.colors['ch1'] = theme['ch1_color']
                scope.scope_plot.colors['ch2'] = theme['ch2_color']
                scope.scope_plot.yaxes['CH1'].color = theme['ch1_color']
                scope.scope_plot.yaxes['CH2'].color = theme['ch2_color']
                scope.scope_plot.configure(
                    background=theme['plot_background'],
                    axes_background=theme['axes_background'],
                    axes_color=theme['axes_color'],
                    grid_color=theme['grid_color']
                )
                scope.scope_plot.refresh_plot()
                
                # Update ScopeXYPlot colors
                scope.scope_xyplot.colors['xy'] = theme['phase_color']
                if scope.scope_xyplot.ch1_vs_ch2:
                    scope.scope_xyplot.xaxis_color = theme['ch2_color']
                    scope.scope_xyplot.yaxes['left'].color = theme['ch1_color']
                else:
                    scope.scope_xyplot.xaxis_color = theme['ch1_color']
                    scope.scope_xyplot.yaxes['left'].color = theme['ch2_color']
                scope.scope_xyplot.configure(
                    background=theme['plot_background'],
                    axes_background=theme['axes_background'],
                    axes_color=theme['axes_color'],
                    grid_color=theme['grid_color']
                )
                scope.scope_xyplot.refresh_plot()
                
                # Update WavegenPlot colors
                scope.wavegen_plot.colors['waveform'] = theme['waveform_color']
                scope.wavegen_plot.control_point_color = theme['waveform_color']
                scope.wavegen_plot.configure(
                    background=theme['plot_background'],
                    axes_background=theme['axes_background'],
                    axes_color=theme['axes_color'],
                    grid_color=theme['grid_color']
                )
                scope.wavegen_plot.refresh_plot()
                
                # Update OffsetWaveformPlot colors
                scope.offset_waveform_plot.colors['waveform'] = theme['waveform_color']
                scope.offset_waveform_plot.configure(
                    background=theme['plot_background'],
                    axes_background=theme['axes_background'],
                    axes_color=theme['axes_color'],
                    grid_color=theme['grid_color']
                )
                scope.offset_waveform_plot.refresh_plot()
                
                # Update BodePlot colors
                bode = self.root.bode
                bode.bode_plot.yaxes['left'].color = theme['gain_color']
                bode.bode_plot.yaxes['right'].color = theme['phase_color']
                bode.bode_plot.configure(
                    background=theme['plot_background'],
                    axes_background=theme['axes_background'],
                    axes_color=theme['axes_color'],
                    grid_color=theme['grid_color']
                )
                bode.bode_plot.refresh_plot()
                
                # Update meter label colors in scope panel
                self.update_meter_label_colors()
                
                # Update all button colors
                self.update_button_colors()
                
            except Exception as e:
                print(f"Error applying color theme: {e}")
    
    def update_button_colors(self):
        """Update all button background colors based on theme."""
        theme = self.get_current_theme()
        button_normal = theme['button_normal']
        button_pressed = theme['button_pressed']
        
        def update_widget_colors(widget):
            """Recursively update button colors in widget tree."""
            # Check if this widget has bkgnd_color and is a button type
            # Only update widgets with 3-element RGB colors (not 4-element RGBA like AltImageButton)
            if hasattr(widget, 'bkgnd_color') and hasattr(widget, 'state') and len(widget.bkgnd_color) == 3:
                # It's a button-like widget with RGB color
                if widget.state == 'down':
                    widget.bkgnd_color = button_pressed
                else:
                    widget.bkgnd_color = button_normal
            
            # Recurse into children
            if hasattr(widget, 'children'):
                for child in widget.children:
                    update_widget_colors(child)
        
        try:
            if self.root:
                update_widget_colors(self.root)
        except Exception:
            pass  # Widget tree may not be ready
    
    def update_meter_label_colors(self):
        """Update meter label colors based on theme."""
        theme = self.get_current_theme()
        try:
            # Update the default meter label text with themed colors
            meter_text = '[b][color={}]CH1[/color]\n[color={}]CH2[/color][/b]'.format(
                theme['ch1_color'], theme['ch2_color'])
            self.root.scope.meter_label.text = meter_text
        except Exception:
            pass  # Widget may not exist yet
    
    def get_custom_theme_color(self, color_key):
        """Get a color value from the custom theme."""
        custom_theme = settings_manager.custom_theme
        if custom_theme and color_key in custom_theme:
            return custom_theme[color_key]
        return COLOR_THEMES['default'].get(color_key, '#FFFFFF')
    
    def update_custom_theme_color(self, color_key, color_value):
        """Update a single color in the custom theme and apply if active."""
        settings_manager.update_custom_theme_color(color_key, color_value)
        # If custom theme is active, apply the change
        if self.color_theme == 'custom':
            self.apply_color_theme()
    
    def reset_custom_theme(self):
        """Reset the custom theme to default values."""
        settings_manager.reset_custom_theme()
        if self.color_theme == 'custom':
            self.apply_color_theme()
    
    def open_color_picker(self, color_key, current_color, callback):
        """Open a color picker popup for selecting a color."""
        from kivy.uix.colorpicker import ColorPicker
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label
        
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        color_picker = ColorPicker()
        # Convert hex to RGBA
        if current_color.startswith('#'):
            rgba = get_color_from_hex(current_color)
            color_picker.color = rgba
        
        color_picker.foreground_color = (0, 0, 0, 1)
        
        content.add_widget(color_picker)
        
        # # Selected color preview section
        # preview_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10, padding=[10, 5, 10, 5])
        # preview_label = Label(text='Selected Color:', size_hint_x=0.3, font_size=int(14 * self.fontscale))
        # preview_box.add_widget(preview_label)
        
        # # Color preview widget
        # color_preview = Widget(size_hint_x=0.7)
        # with color_preview.canvas:
        #     Color(*color_picker.color)
        #     preview_rect = Rectangle(pos=color_preview.pos, size=color_preview.size)
        #     Color(0.5, 0.5, 0.5, 1)
        #     preview_border = Line(rectangle=[color_preview.pos[0], color_preview.pos[1], color_preview.size[0], color_preview.size[1]], width=1.5)
        
        # def update_preview_rect(*args):
        #     preview_rect.pos = color_preview.pos
        #     preview_rect.size = color_preview.size
        #     preview_border.rectangle = [color_preview.pos[0], color_preview.pos[1], color_preview.size[0], color_preview.size[1]]
        
        # color_preview.bind(pos=update_preview_rect, size=update_preview_rect)
        # preview_box.add_widget(color_preview)
        # content.add_widget(preview_box)
        
        # # Update preview when color changes
        # def update_preview_color(instance, value):
        #     color_preview.canvas.clear()
        #     with color_preview.canvas:
        #         Color(*value)
        #         rect = Rectangle(pos=color_preview.pos, size=color_preview.size)
        #         Color(0.5, 0.5, 0.5, 1)
        #         Line(rectangle=[color_preview.pos[0], color_preview.pos[1], color_preview.size[0], color_preview.size[1]], width=1.5)
        
        # color_picker.bind(color=update_preview_color)
        
        # Buttons
        buttons = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        cancel_btn = Button(text='Cancel', font_size=int(16 * self.fontscale))
        ok_btn = Button(text='OK', font_size=int(16 * self.fontscale))
        
        buttons.add_widget(cancel_btn)
        buttons.add_widget(ok_btn)
        content.add_widget(buttons)
        
        popup = Popup(
            title=f'Select Color for {color_key.replace("_", " ").title()}',
            content=content,
            size_hint=(0.8, 0.9),
            auto_dismiss=False
        )
        
        def on_cancel(instance):
            popup.dismiss()
        
        def on_ok(instance):
            # Convert RGBA to hex
            r, g, b, a = color_picker.color
            color_hex = '#{:02X}{:02X}{:02X}'.format(int(r*255), int(g*255), int(b*255))
            callback(color_hex)
            self.update_custom_theme_color(color_key, color_hex)
            popup.dismiss()
        
        cancel_btn.bind(on_release=on_cancel)
        ok_btn.bind(on_release=on_ok)
        
        popup.open()
    
    def get_settings_directory(self):
        """Get the settings directory path for display."""
        return settings_manager.get_settings_directory()
    
    def start_settings_updates(self, connection_label, ports_label):
        """Start periodic updates of the settings dialog connection info."""
        self._settings_connection_label = connection_label
        self._settings_ports_label = ports_label
        if self.settings_update_job is not None:
            self.settings_update_job.cancel()
        self.settings_update_job = Clock.schedule_interval(self._update_settings_connection, 1.0)
    
    def stop_settings_updates(self):
        """Stop periodic updates of the settings dialog."""
        if self.settings_update_job is not None:
            self.settings_update_job.cancel()
            self.settings_update_job = None
    
    def _update_settings_connection(self, dt):
        """Update connection status labels in the settings dialog."""
        try:
            if hasattr(self, '_settings_connection_label') and self._settings_connection_label:
                self._settings_connection_label.text = self.get_connection_status_text()
            if hasattr(self, '_settings_ports_label') and self._settings_ports_label:
                self._settings_ports_label.text = self.get_serial_ports_text()
        except Exception:
            pass  # Widget may have been destroyed

    def close_application(self):
        App.get_running_app().stop()
        Window.close()

    def connect_to_oscope(self, t):
        if self.dev.connected:
            return

        self.dev = oscope.oscope()
        if self.dev.connected:
            self.connect_job = None
            self.root.scope.scope_plot.update_job = Clock.schedule_once(self.root.scope.scope_plot.update_scope_plot, 0.1)
            self.root.scope.digital_control_panel.sync_controls()
        else:
            self.connect_job = Clock.schedule_once(self.connect_to_oscope, 0.2)

    def disconnect_from_oscope(self):
        if not self.dev.connected:
            return

        self.dev.dev = None
        self.dev.connected = False

        self.root.scope.on_oscope_disconnect()
        self.root.bode.on_oscope_disconnect()

        if self.connect_job is not None:
            self.connect_job.cancel()
        self.connect_job = Clock.schedule_once(self.connect_to_oscope, 0.2)

    def num2str(self, num_raw, ndigits = 0, positive_sign = False, trailing_zeros = False):
        """
        Convert a numeric value to a string with an SI prefix.
        Parameters
        ----------
        num : float or int
            The numeric value to convert.
        ndigits : int, optional
            The number of significant digits to include in the output
            string. The default is 0, which means to use as many digits
            as necessary to represent the number exactly. E.g., ndigits=3
            would format 0.012345 as '12.3m', 0.0005432 as '0.543m
        positive_sign : bool, optional
            If True, a plus sign is prepended to positive numbers.
            The default is False.
        trailing_zeros : bool, optional
            If True, trailing zeros are included in the output string
            to ensure that the length of the string matches the specified
            number of significant digits. The default is False.
        Returns
        -------
        str
            The formatted string with an SI prefix.
        """
        ndigits = ndigits - 1 if ndigits > 0 else ndigits # for compatibility with previous behavior   
        num_str = sigfig.round(num_raw, sigfigs = ndigits, prefix=True)
        if positive_sign and num_raw > 0:
            num_str = '+' + num_str
        if trailing_zeros:
            strlen = len(num_str.replace('-', '').replace('+', ''))
            if '.' in num_str:
                num_str = num_str + '0' * (ndigits - strlen + 1)
            else:
                if ndigits - strlen >= 2:
                    num_str = num_str + '.' + '0' * (ndigits - strlen)
                elif ndigits - strlen == 1:
                    num_str = '0' + num_str
        return num_str


    def process_selection(self, selection):
        if selection == '':
            return selection
        else:
            return pathlib.Path(selection).name

    def export_waveforms(self, path, filename, overwrite_existing_file = False):
        self.save_dialog_path = path
        self.save_dialog_file = None

        if filename == '':
            return

        if os.path.exists(os.path.join(path, filename)) and not overwrite_existing_file:
            self.save_dialog_file = filename
            Factory.FileExistsAlert().open()
            return

        try:
            outfile = open(os.path.join(path, filename), 'w')
        except:
            return

        if filename[-4:] == '.txt' or filename[-4:] == '.TXT':
            outfile.write('t1\tch1\tt2\tch2\n')
            sep = '\t'
        else:
            outfile.write('t1,ch1,t2,ch2\n')
            sep = ','

        for i in range(len(self.root.scope.scope_plot.curves['CH1'].points_x)):
            for j in range(len(self.root.scope.scope_plot.curves['CH1'].points_x[i])):
                line = '{!s}{!s}'.format(self.root.scope.scope_plot.curves['CH1'].points_x[i][j], sep)
                line += '{!s}{!s}'.format(self.root.scope.scope_plot.curves['CH1'].points_y[i][j], sep)
                line += '{!s}{!s}'.format(self.root.scope.scope_plot.curves['CH2'].points_x[i][j], sep)
                line += '{!s}\n'.format(self.root.scope.scope_plot.curves['CH2'].points_y[i][j])
                outfile.write(line)

        outfile.close()

    def export_freqresp(self, path, filename, overwrite_existing_file = False):
        self.save_dialog_path = path
        self.save_dialog_file = None

        if filename == '':
            return

        if os.path.exists(os.path.join(path, filename)) and not overwrite_existing_file:
            self.save_dialog_file = filename
            Factory.FileExistsAlert().open()
            return

        try:
            outfile = open(os.path.join(path, filename), 'w')
        except:
            return

        if filename[-4:] == '.txt' or filename[-4:] == '.TXT':
            outfile.write('freq\tgain\tphase\n')
            sep = '\t'
        else:
            outfile.write('freq,gain,phase\n')
            sep = ','

        for i in range(len(self.root.bode.freq)):
            line = '{!s}{!s}'.format(self.root.bode.freq[i], sep)
            line += '{!s}{!s}'.format(self.root.bode.gain[i], sep)
            line += '{!s}\n'.format(self.root.bode.phase[i])
            outfile.write(line)

        outfile.close()

    def load_offset_waveform(self, path, filename):
        if not self.dev.connected:
            return

        try:
            if self.dev.offset_sweep_in_progress():
                self.dev.offset_stop()
                if self.root.scope.offset_waveform_play_pause_button_update_job is not None:
                    self.root.scope.offset_waveform_play_pause_button_update_job.cancel()
                    self.root.scope.offset_waveform_play_pause_button_update_job = None
                self.root.scope.offset_waveform_play_pause_button.source = kivy_resources.resource_find('play.png')
                self.root.scope.offset_waveform_play_pause_button.reload()
        except:
            self.disconnect_from_oscope()

        try:
            if not self.dev.write_offset_waveform_as_voltages(os.path.join(path, filename)):
                return
        except:
            self.disconnect_from_oscope()
            return

        self.root.scope.read_offset_waveform = False
        self.root.scope.sync_offset_waveform()

if __name__ == '__main__':
    app = MainApp()
    oscope.app = app
    app.run()

