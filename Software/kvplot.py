#qpy:kivy

from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from kivy.core.text import Label as CoreLabel
from kivy.graphics import *
from kivy.lang import Builder
import numpy as np
import math

Builder.load_string('''
<Plot>
    on_pos: self.update_plot()
    on_size: self.update_plot()
''')

class Plot(Widget):

    class curve:

        def __init__(self, **kwargs):
            self.data_x = kwargs.get('data_x', np.array([]))
            self.data_y = kwargs.get('data_y', np.array([]))
            self.points_x = kwargs.get('points_x', [np.array([])])
            self.points_y = kwargs.get('points_y', [np.array([])])
            self.name = kwargs.get('name', '')
            self.yaxis = kwargs.get('yaxis', 'left')
            self.marker_color = kwargs.get('marker_color', '')
            self.marker = kwargs.get('marker', '')
            self.curve_color = kwargs.get('curve_color', '')
            self.curve_style = kwargs.get('curve_style', '')

        def __str__(self):
            return str(self.data)

        def __repr__(self):
            return repr(self.data)

    class y_axis:

        def __init__(self, **kwargs):
            self.name = kwargs.get('name', 'left')
            self.color = kwargs.get('color', '#000000')
            self.units = kwargs.get('units', '')
            self.yaxis_mode = kwargs.get('yaxis_mode', 'linear')
            self.yaxis_sign = 1.
            self.ylimits_mode = kwargs.get('ylimits_mode', 'auto')
            self.ylim = kwargs.get('ylim', [0., 1.])
            self.ymin = self.ylim[0]
            self.ymax = self.ylim[1]
            self.ylabel_value = kwargs.get('ylabel', '')

    def __init__(self, **kwargs):
        self.canvas_left = float(kwargs.pop('left', 0.))
        self.canvas_bottom = float(kwargs.pop('bottom', 0.))
        self.canvas_width = float(kwargs.pop('width', 560.))
        self.canvas_height = float(kwargs.pop('height', 420.))
        self.marker_radius = float(kwargs.pop('marker_radius', 4.))
        self.marker_lineweight = float(kwargs.pop('marker_lineweight', 1.))
        self.curve_lineweight = float(kwargs.pop('curve_lineweight', 1.))
        self.tick_length = float(kwargs.pop('tick_length', 6.))
        self.tick_lineweight = float(kwargs.pop('tick_lineweight', 1.))
        self.canvas_background_color = kwargs.pop('background', '#CDCDCD')
        self.axes_background_color = kwargs.pop('axes_background', '#FFFFFF')
        self.axes_color = kwargs.pop('axes_color', '#000000')
        self.axes_lineweight = kwargs.pop('axes_lineweight', 1.)
        self.grid_color = kwargs.pop('grid_color', '#333333')
        self.label_font_baseline = float(kwargs.pop('baseline', 0.6))
        self.label_fontsize = int(kwargs.pop('fontsize', 12))
        # Default to 'Roboto' which is registered from ./fonts directory
        self.label_font = kwargs.pop('font', 'Roboto')
        self.linear_minor_ticks = kwargs.pop('linear_minor_ticks', 'off')

        super(Plot, self).__init__(**kwargs)

        self.init_markers(self.marker_radius)

        self.marker_names = [[' ',  'No marker'], ['.', 'Point'], ['o', 'Circle'], ['x', 'Ex'], 
                             ['+', 'Plus'], ['*', 'Star'], ['s', 'Square'], ['d', 'Diamond'],
                             ['v', 'Triangle (down)'], ['^', 'Triangle (up)'], ['<', 'Triangle (left)'], 
                             ['>', 'Triangle (right)'], ['p', 'Pentagram'], ['h', 'Hexagram']]

        self.colors = {'b': '#0000FF', 'g': '#00FF00', 'r': '#FF0000', 
                       'c': '#00FFFF', 'm': '#FF00FF', 'y': '#FFFF00',
                       'k': '#000000', 'w': '#FFFFFF'}

        self.color_names = [['b', 'Blue'], ['r', 'Red'], ['g', 'Green'], ['c', 'Cyan'], 
                            ['m', 'Magenta'], ['y', 'Yellow'], ['k', 'Black'], ['w', 'White']]

        self.linestyles = {'-': (), ':': (1, 4), '--': (10, 4), '-.': (10, 4, 1, 4), '-:': (10, 4, 1, 4, 1, 4)}

        self.linestyle_names = [[' ',   'No line'], ['-',  'Solid'], [':',  'Dotted'], 
                                ['-.', 'Dash-dot'], ['-:', 'Dash-dot-dot'], ['--', 'Dashed']]

        self.multipliers = (1., 1e-3, 1e-6, 1e-9, 1e-12, 1e-15, 1e-18, 1e-21, 1e-24, 
                            1e24, 1e21, 1e18, 1e15, 1e12, 1e9, 1e6, 1e3)

        self.prefixes = (u'', u'k', u'M', u'G', u'T', u'P', u'E', u'Z', u'Y', 
                         u'y', u'z', u'a', u'f', u'p', u'n', u'\xB5', u'm')

        self.default_color_order = ('b', 'g', 'r', 'c', 'm', 'y')
        self.default_color_index = 0
        self.default_marker = '.'
        self.default_curve_style = '-'

        self.curve_id = 0
        self.curves = {}

        self.xaxis_mode = 'linear'
        self.xaxis_sign = 1.
        self.xaxis_color = None
        self.xaxis_units = ''
        self.xlimits_mode = 'auto'
        self.xlim = [0., 1.]
        self.xmin = 0.
        self.xmax = 1.
        self.xlabel_value = ''

        self.yaxes = {}
        self.yaxes['left'] = self.y_axis()
        self.left_yaxis = 'left'
        self.right_yaxis = ''

        self.update_sizes()

        self.find_x_ticks()
        self.find_y_ticks()

        self.grid_state = 'off'

        self.dw = 0.
        self.dh = 0.

        self.x0 = 0.
        self.y0 = 0.

        self.num_touches = 0
        self.touch_positions = []
        self.touch_net_movements = []
        self.looking_for_gesture = True
        self.gesture = ''
        self.swipe_dirs = ('W', 'SW', 'SW', 'S', 'S', 'SE', 'SE', 'E', 'E', 'NE', 'NE', 'N', 'N', 'NW', 'NW', 'W', 'W')
        self.pinch_dirs = ('E-W', 'NE-SW', 'NE-SW', 'N-S', 'N-S', 'NW-SE', 'NW-SE', 'E-W', 'E-W', 'NE-SW', 'NE-SW', 'N-S', 'N-S', 'NW-SE', 'NW-SE', 'E-W', 'E-W')
        self.MOTION_THRESHOLD = 25.
        self.ANGLE_THRESHOLD = 0.85

        self.draw_background()
        self.draw_axes()
        self.draw_x_ticks()
        self.draw_y_ticks()
        self.draw_axis_labels()

    def init_markers(self, r = 4.):
        r_over_sqrt2 = r / math.sqrt(2.)
        r_over_sqrt3 = r / math.sqrt(3.)
        pi_over_180 = math.pi / 180.
        r2 = r * math.sin(pi_over_180 * 18.) / math.sin(pi_over_180 * 54.)

        self.marker_coords = {}
        self.marker_coords['.'] = ((-0.5 * r, -0.5 * r), (0.5 * r, 0.5 * r))
        self.marker_coords['o'] = ((-r, -r), (r, r))
        self.marker_coords['x'] = ((0., 0.), (r_over_sqrt2, -r_over_sqrt2), 
                                   (0., 0.), (r_over_sqrt2, r_over_sqrt2), 
                                   (0., 0.), (-r_over_sqrt2, r_over_sqrt2), 
                                   (0., 0.), (-r_over_sqrt2, -r_over_sqrt2), 
                                   (0., 0.))
        self.marker_coords['+'] = ((0., 0.), (0., -r), 
                                   (0., 0.), (r, 0.), 
                                   (0., 0.), (0., r), 
                                   (0., 0.), (-r, 0.), 
                                   (0., 0.))
        self.marker_coords['*'] = ((0., 0.), (0., -r), 
                                   (0., 0.), (r_over_sqrt2, -r_over_sqrt2), 
                                   (0., 0.), (r, 0.), 
                                   (0., 0.), (r_over_sqrt2, r_over_sqrt2), 
                                   (0., 0.), (0., r), 
                                   (0., 0.), (-r_over_sqrt2, r_over_sqrt2), 
                                   (0., 0.), (-r, 0.), 
                                   (0., 0.), (-r_over_sqrt2, -r_over_sqrt2), 
                                   (0., 0.))
        self.marker_coords['s'] = ((-r_over_sqrt2, -r_over_sqrt2), (r_over_sqrt2, -r_over_sqrt2), 
                                   (r_over_sqrt2, r_over_sqrt2), (-r_over_sqrt2, r_over_sqrt2), 
                                   (-r_over_sqrt2, -r_over_sqrt2))
        self.marker_coords['d'] = ((0., -1.25 * r), (r, 0.), (0., 1.25 * r), (-r, 0.), (0., -1.25 * r))
        self.marker_coords['v'] = ((0., -r), 
                                   (r * math.cos(pi_over_180 * 150.), r * math.sin(pi_over_180 * 150.)), 
                                   (r * math.cos(pi_over_180 * 30.), r * math.sin(pi_over_180 * 30.)), 
                                   (0., -r))
        self.marker_coords['^'] = ((0., r), 
                                   (r * math.cos(pi_over_180 * 330.), r * math.sin(pi_over_180 * 330.)), 
                                   (r * math.cos(pi_over_180 * 210.), r * math.sin(pi_over_180 * 210.)), 
                                   (0., r))
        self.marker_coords['<'] = ((-r, 0.), 
                                   (r * math.cos(pi_over_180 * 60.), -r * math.sin(pi_over_180 * 60.)), 
                                   (r * math.cos(pi_over_180 * 300.), -r * math.sin(pi_over_180 * 300.)), 
                                   (-r, 0.))
        self.marker_coords['>'] = ((r, 0.), 
                                   (r * math.cos(pi_over_180 * 240.), -r * math.sin(pi_over_180 * 240.)), 
                                   (r * math.cos(pi_over_180 * 120.), -r * math.sin(pi_over_180 * 120.)), 
                                   (r, 0.))
        self.marker_coords['p'] = ((0., r),
                                   (r2 * math.cos(pi_over_180 * 54.), r2 * math.sin(pi_over_180 * 54.)), 
                                   (r * math.cos(pi_over_180 * 18.), r * math.sin(pi_over_180 * 18.)), 
                                   (r2 * math.cos(pi_over_180 * 342.), r2 * math.sin(pi_over_180 * 342.)), 
                                   (r * math.cos(pi_over_180 * 306.), r * math.sin(pi_over_180 * 306.)), 
                                   (0., -r2), 
                                   (r * math.cos(pi_over_180 * 234.), r * math.sin(pi_over_180 * 234.)), 
                                   (r2 * math.cos(pi_over_180 * 198.), r2 * math.sin(pi_over_180 * 198.)), 
                                   (r * math.cos(pi_over_180 * 162.), r * math.sin(pi_over_180 * 162.)), 
                                   (r2 * math.cos(pi_over_180 * 126.), r2 * math.sin(pi_over_180 * 126.)), 
                                   (0., r))
        self.marker_coords['h'] = ((0., -r), 
                                   (r_over_sqrt3 * math.cos(pi_over_180 * 60.), -r_over_sqrt3 * math.sin(pi_over_180 * 60.)), 
                                   (r * math.cos(pi_over_180 * 30.), -r * math.sin(pi_over_180 * 30.)), 
                                   (r_over_sqrt3, 0.), 
                                   (r * math.cos(pi_over_180 * 330.), -r * math.sin(pi_over_180 * 330.)), 
                                   (r_over_sqrt3 * math.cos(pi_over_180 * 300.), -r_over_sqrt3 * math.sin(pi_over_180 * 300.)), 
                                   (0., r), 
                                   (r_over_sqrt3 * math.cos(pi_over_180 * 240.), -r_over_sqrt3 * math.sin(pi_over_180 * 240.)), 
                                   (r * math.cos(pi_over_180 * 210.), -r * math.sin(pi_over_180 * 210.)), 
                                   (-r_over_sqrt3, 0.), 
                                   (r * math.cos(pi_over_180 * 150.), -r * math.sin(pi_over_180 * 150.)), 
                                   (r_over_sqrt3 * math.cos(pi_over_180 * 120.), -r_over_sqrt3 * math.sin(pi_over_180 * 120.)), 
                                   (0., -r))

    def update_sizes(self):
        self.axes_left = self.canvas_left + 6. * self.label_fontsize
        self.axes_top = self.canvas_bottom + self.canvas_height - 3. * self.label_fontsize
        self.axes_right = self.canvas_left + self.canvas_width - 6. * self.label_fontsize
        self.axes_bottom = self.canvas_bottom + 4. * self.label_fontsize
        self.axes_width = self.axes_right - self.axes_left
        self.axes_height = self.axes_top - self.axes_bottom

        self.xrange = self.xlim[1] - self.xlim[0]
        self.x_pix_per_unit = self.axes_width / self.xrange
        self.x_epsilon = self.xrange / self.axes_width
        
        for yaxis in self.yaxes.keys():
            self.yaxes[yaxis].yrange = self.yaxes[yaxis].ylim[1] - self.yaxes[yaxis].ylim[0]
            self.yaxes[yaxis].y_pix_per_unit = self.axes_height / self.yaxes[yaxis].yrange
            self.yaxes[yaxis].y_epsilon = self.yaxes[yaxis].yrange / self.axes_height

    def configure(self, **kwargs):
        self.canvas_left = float(kwargs.get('left', self.canvas_left))
        self.canvas_bottom = float(kwargs.get('top', self.canvas_bottom))
        self.canvas_width = float(kwargs.get('width', self.canvas_width))
        self.canvas_height = float(kwargs.get('height', self.canvas_height))
        self.marker_radius = float(kwargs.get('marker_radius', self.marker_radius))
        self.marker_lineweight = float(kwargs.get('marker_lineweight', self.marker_lineweight))
        self.curve_lineweight = float(kwargs.get('curve_lineweight', self.curve_lineweight))
        self.tick_length = float(kwargs.get('tick_length', self.tick_length))
        self.tick_lineweight = float(kwargs.get('tick_lineweight', self.tick_lineweight))
        self.canvas_background_color = kwargs.get('background', self.canvas_background_color)
        self.axes_background_color = kwargs.get('axes_background', self.axes_background_color)
        self.axes_color = kwargs.get('axes_color', self.axes_color)
        self.axes_lineweight = kwargs.get('axes_lineweight', self.axes_lineweight)
        self.label_font_baseline = float(kwargs.get('baseline', self.label_font_baseline))
        self.label_fontsize = int(kwargs.get('fontsize', self.label_fontsize))
        self.label_font = kwargs.get('font', self.label_font)
        self.linear_minor_ticks = kwargs.get('linear_minor_ticks', 'off')
        self.grid_color = kwargs.get('grid_color', self.grid_color)

        self.init_markers(self.marker_radius)
        self.refresh_plot()

    def clear_plot(self, **kwargs):
        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        if yaxis == 'all':
            self.curves = {}
        else:
            for name in self.curves.keys():
                if self.curves[name].yaxis == yaxis:
                    del(self.curves[name])

        self.refresh_plot()

    def draw_now(self):
        pass

    def update_plot(self):
        self.canvas_left = self.pos[0]
        self.canvas_bottom = self.pos[1]
        self.canvas_width = max(self.size[0], 17. * self.label_fontsize)
        self.canvas_height = max(self.size[1], 12. * self.label_fontsize)
        self.refresh_plot()

    def refresh_plot(self):
        self.find_axes_limits()
        self.update_sizes()
        self.find_x_ticks()
        self.find_y_ticks()
        self.erase_plot()
        self.draw_plot()

    def erase_plot(self):
        self.canvas.clear()
        self.clear_widgets()

    def draw_plot(self):
        self.draw_background()
        self.draw_axes_background()
        self.draw_grid()
        self.draw_x_ticks()
        self.draw_y_ticks()
        self.draw_axes()
        self.draw_curves()
        self.draw_axis_labels()

    def add_text(self, **kwargs):
        text = kwargs.get('text', '')
        anchor_pos = kwargs.get('anchor_pos', [0., 0.])
        anchor = kwargs.get('anchor', 'center')
        color = kwargs.get('color', '#FFFFFF')
        font_size = kwargs.get('font_size', 16)
        font_name = kwargs.get('font_name', self.label_font)

        if text == '':
            return

        label = CoreLabel(text = text, font_size = font_size, font_name = font_name, color = get_color_from_hex(color))
        label.refresh()

        texture = label.texture
        texture_size = list(texture.size)

        if anchor == 'center':
            pos = [round(anchor_pos[0] - 0.5 * texture_size[0]), round(anchor_pos[1] - 0.5 * texture_size[1])]
        elif anchor == 'n':
            pos = [round(anchor_pos[0] - 0.5 * texture_size[0]), round(anchor_pos[1] - texture_size[1])]
        elif anchor == 'ne':
            pos = [round(anchor_pos[0] - texture_size[0]), round(anchor_pos[1] - texture_size[1])]
        elif anchor == 'e':
            pos = [round(anchor_pos[0] - texture_size[0]), round(anchor_pos[1] - 0.5 * texture_size[1])]
        elif anchor == 'se':
            pos = [round(anchor_pos[0] - texture_size[0]), round(anchor_pos[1])]
        elif anchor == 's':
            pos = [round(anchor_pos[0] - 0.5 * texture_size[0]), round(anchor_pos[1])]
        elif anchor == 'sw':
            pos = [round(anchor_pos[0]), round(anchor_pos[1])]
        elif anchor == 'w':
            pos = [round(anchor_pos[0]), round(anchor_pos[1] - 0.5 * texture_size[1])]
        elif anchor == 'nw':
            pos = [round(anchor_pos[0]), round(anchor_pos[1] - texture_size[1])]
        else:
            raise ValueError('anchor value must be "center", "n", "ne", "e", "se", "s", "sw", "w", or "nw".')

        self.canvas.add(Color(*get_color_from_hex('#FFFFFF')))
        self.canvas.add(Rectangle(texture = texture, pos = pos, size = texture_size))

    def draw_background(self):
        self.canvas.add(Color(*get_color_from_hex(self.canvas_background_color)))
        self.canvas.add(Rectangle(pos = [self.canvas_left, self.canvas_bottom], size = [self.canvas_width, self.canvas_height]))

    def draw_axes_background(self):
        self.canvas.add(Color(*get_color_from_hex(self.axes_background_color)))
        self.canvas.add(Rectangle(pos = [self.axes_left, self.axes_bottom], size = [self.axes_width, self.axes_height]))

    def draw_axes(self):
        self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
        self.canvas.add(Line(points = [self.axes_left, self.axes_top, self.axes_right, self.axes_top]))
        self.canvas.add(Line(points = [self.axes_right, self.axes_top, self.axes_right, self.axes_bottom]))
        self.canvas.add(Line(points = [self.axes_left, self.axes_bottom, self.axes_right, self.axes_bottom]))
        self.canvas.add(Line(points = [self.axes_left, self.axes_top, self.axes_left, self.axes_bottom]))

    def to_canvas_x(self, x):
        return self.axes_left + self.x_pix_per_unit * (x - self.xlim[0])

    def to_canvas_y(self, y, yaxis = 'left'):
        return self.axes_bottom + self.yaxes[yaxis].y_pix_per_unit * (y - self.yaxes[yaxis].ylim[0])

    def from_canvas_x(self, x):
        return self.xlim[0] + (x - self.axes_left) / self.x_pix_per_unit

    def from_canvas_y(self, y, yaxis = 'left'):
        return self.yaxes[yaxis].ylim[0] + (y - self.axes_bottom) / self.yaxes[yaxis].y_pix_per_unit

    def draw_marker(self, x, y, marker, color, name = ''):
        coords = []
        for [dx, dy] in self.marker_coords[marker]:
            coords.append(x + dx)
            coords.append(y + dy)
        if marker == '.':
            self.canvas.add(Ellipse(pos = [coords[0], coords[1]], size = [coords[2] - coords[0], coords[3] - coords[1]]))
        elif marker == 'o':
            self.canvas.add(Line(ellipse = [coords[0], coords[1], coords[2] - coords[0], coords[3] - coords[1]], width = self.marker_lineweight))
        else:
            self.canvas.add(Line(points = coords, width = self.marker_lineweight))

    def draw_curve(self, curve):
        self.canvas.add(Color(*get_color_from_hex(self.colors[curve.curve_color])))
        yaxis = self.yaxes[curve.yaxis]
        for j in range(len(curve.points_x)):
            px = curve.points_x[j]
            py = curve.points_y[j]
            if len(px) > 1:
                pts_in_axes = np.logical_and(np.logical_and(px >= self.xlim[0], px <= self.xlim[1]), np.logical_and(py >= yaxis.ylim[0], py <= yaxis.ylim[1]))
                where_pts_in_axes = np.where(pts_in_axes)[0]
                runs_where_pts_in_axes = np.split(where_pts_in_axes, np.where(np.diff(where_pts_in_axes) != 1)[0] + 1)
                for run in runs_where_pts_in_axes:
                    if len(run) > 1:
                        x = self.axes_left + self.x_pix_per_unit * (px[run] - self.xlim[0])
                        y = self.axes_bottom + yaxis.y_pix_per_unit * (py[run] - yaxis.ylim[0])
                        coords = np.vstack((x, y)).T.flatten().tolist()
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))

                where_pts_leave_axes = np.where(np.logical_and(pts_in_axes[0:-1], pts_in_axes[1:] == False))[0]
                for i in where_pts_leave_axes:
                    NW = (py[i + 1] - yaxis.ylim[1]) * (px[i] - self.xlim[0]) - (px[i + 1] - self.xlim[0]) * (py[i] - yaxis.ylim[1])
                    NE = (py[i + 1] - py[i]) * (self.xlim[1] - px[i]) - (px[i + 1] - px[i]) * (yaxis.ylim[1] - py[i])
                    SE = (py[i + 1] - py[i]) * (self.xlim[1] - px[i]) - (px[i + 1] - px[i]) * (yaxis.ylim[0] - py[i])
                    SW = (py[i + 1] - yaxis.ylim[0]) * (px[i] - self.xlim[0]) - (px[i + 1] - self.xlim[0]) * (py[i] - yaxis.ylim[0])
                    if (NW > 0) and (NE > 0):
                        if py[i] == py[i + 1]:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.axes_right if px[i + 1] >= self.xlim[1] else self.axes_left, self.axes_top]
                        else:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.to_canvas_x(px[i] + (px[i + 1] - px[i]) * (yaxis.ylim[1] - py[i]) / (py[i + 1] - py[i])), self.axes_top]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    elif (SE <= 0) and (SW <= 0):
                        if py[i] == py[i + 1]:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.axes_right if px[i + 1] >= self.xlim[1] else self.axes_left, self.axes_bottom]
                        else:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.to_canvas_x(px[i] + (px[i + 1] - px[i]) * (yaxis.ylim[0] - py[i]) / (py[i + 1] - py[i])), self.axes_bottom]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    elif (NW <= 0) and (SW > 0):
                        if px[i] == px[i + 1]:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.axes_left, self.axes_top if py[i + 1] >= yaxis.ylim[1] else self.axes_bottom]
                        else:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.axes_left, self.to_canvas_y(py[i] + (py[i + 1] - py[i]) * (self.xlim[0] - px[i]) / (px[i + 1] - px[i]), curve.yaxis)]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    elif (NE <= 0) and (SE > 0):
                        if px[i] == px[i + 1]:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.axes_right, self.axes_top if py[i + 1] >= yaxis.ylim[1] else self.axes_bottom]
                        else:
                            coords = [self.to_canvas_x(px[i]), self.to_canvas_y(py[i], curve.yaxis), 
                                      self.axes_right, self.to_canvas_y(py[i] + (py[i + 1] - py[i]) * (self.xlim[1] - px[i]) / (px[i + 1] - px[i]), curve.yaxis)]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))

                where_pts_enter_axes = np.where(np.logical_and(pts_in_axes[0:-1] == False, pts_in_axes[1:]))[0]
                for i in where_pts_enter_axes:
                    NW = (py[i] - yaxis.ylim[1]) * (px[i + 1] - self.xlim[0]) - (px[i] - self.xlim[0]) * (py[i + 1] - yaxis.ylim[1])
                    NE = (py[i] - py[i + 1]) * (self.xlim[1] - px[i + 1]) - (px[i] - px[i + 1]) * (yaxis.ylim[1] - py[i + 1])
                    SE = (py[i] - py[i + 1]) * (self.xlim[1] - px[i + 1]) - (px[i] - px[i + 1]) * (yaxis.ylim[0] - py[i + 1])
                    SW = (py[i] - yaxis.ylim[0]) * (px[i + 1] - self.xlim[0]) - (px[i] - self.xlim[0]) * (py[i + 1] - yaxis.ylim[0])
                    if (NW > 0) and (NE > 0):
                        if py[i] == py[i + 1]:
                            coords = [self.axes_right if px[i] >= self.xlim[1] else self.axes_left, self.axes_top, 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        else:
                            coords = [self.to_canvas_x(px[i + 1] + (px[i] - px[i + 1]) * (yaxis.ylim[1] - py[i + 1]) / (py[i] - py[i + 1])), self.axes_top, 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    elif (SE <= 0) and (SW <= 0):
                        if py[i] == py[i + 1]:
                            coords = [self.axes_right if px[i] >= self.xlim[1] else self.axes_left, self.axes_bottom, 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        else:
                            coords = [self.to_canvas_x(px[i + 1] + (px[i] - px[i + 1]) * (yaxis.ylim[0] - py[i + 1]) / (py[i] - py[i + 1])), self.axes_bottom, 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    elif (NW <= 0) and (SW > 0):
                        if px[i] == px[i + 1]:
                            coords = [self.axes_left, self.axes_top if py[i] >= yaxis.ylim[1] else self.axes_bottom, 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        else:
                            coords = [self.axes_left, self.to_canvas_y(py[i + 1] + (py[i] - py[i + 1]) * (self.xlim[0] - px[i + 1]) / (px[i] - px[i + 1]), curve.yaxis), 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    elif (NE <= 0) and (SE > 0):
                        if px[i] == px[i + 1]:
                            coords = [self.axes_right, self.axes_top if py[i] >= yaxis.ylim[1] else self.axes_bottom, 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        else:
                            coords = [self.axes_right, self.to_canvas_y(py[i + 1] + (py[i] - py[i + 1]) * (self.xlim[1] - px[i + 1]) / (px[i] - px[i + 1]), curve.yaxis), 
                                      self.to_canvas_x(px[i + 1]), self.to_canvas_y(py[i + 1], curve.yaxis)]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))

                adj_pts_left_of_axes = np.logical_and(px[0:-1] < self.xlim[0], px[1:] < self.xlim[0])
                adj_pts_right_of_axes = np.logical_and(px[0:-1] > self.xlim[1], px[1:] > self.xlim[1])
                adj_pts_below_axes = np.logical_and(py[0:-1] < yaxis.ylim[0], py[1:] < yaxis.ylim[0])
                adj_pts_above_axes = np.logical_and(py[0:-1] > yaxis.ylim[1], py[1:] > yaxis.ylim[1])
                adj_pts_on_same_side_of_axes = np.logical_or(np.logical_or(adj_pts_left_of_axes, adj_pts_right_of_axes), np.logical_or(adj_pts_below_axes, adj_pts_above_axes))
                adj_pts_outside_axes = np.logical_and(pts_in_axes[0:-1] == False, pts_in_axes[1:] == False)

                where_adj_pts_may_straddle_axes = np.where(np.logical_and(adj_pts_outside_axes, adj_pts_on_same_side_of_axes == False))[0]
                for i in where_adj_pts_may_straddle_axes:
                    if (px[i] == px[i + 1]):
                        coords = [self.to_canvas_x(px[i]), self.axes_bottom, 
                                  self.to_canvas_x(px[i]), self.axes_top]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    elif (py[i] == py[i + 1]):
                        coords = [self.axes_left, self.to_canvas_y(py[i], curve.yaxis), 
                                  self.axes_right, self.to_canvas_y(py[i], curve.yaxis)]
                        self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                    else:
                        if px[i] < px[i + 1]:
                            x1, y1 = px[i], py[i]
                            x2, y2 = px[i + 1], py[i + 1]
                        else:
                            x1, y1 = px[i + 1], py[i + 1]
                            x2, y2 = px[i], py[i]
                        NW = (yaxis.ylim[1] - y1) * (x2 - x1) - (self.xlim[0] - x1) * (y2 - y1)
                        NE = (yaxis.ylim[1] - y1) * (x2 - x1) - (self.xlim[1] - x1) * (y2 - y1)
                        SE = (yaxis.ylim[0] - y1) * (x2 - x1) - (self.xlim[1] - x1) * (y2 - y1)
                        SW = (yaxis.ylim[0] - y1) * (x2 - x1) - (self.xlim[0] - x1) * (y2 - y1)
                        if (NW > 0) and (NE <= 0) and (SW <= 0):
                            coords = [self.axes_left, self.to_canvas_y(y1 + (y2 - y1) * (self.xlim[0] - x1) / (x2 - x1), curve.yaxis),
                                      self.to_canvas_x(x1 + (x2 - x1) * (yaxis.ylim[1] - y1) / (y2 - y1)), self.axes_top]
                            self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                        elif (NE > 0) and (NW <= 0) and (SE <= 0):
                            coords = [self.to_canvas_x(x1 + (x2 - x1) * (yaxis.ylim[1] - y1) / (y2 - y1)), self.axes_top,
                                      self.axes_right, self.to_canvas_y(y1 + (y2 - y1) * (self.xlim[1] - x1) / (x2 - x1), curve.yaxis)]
                            self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                        elif (SW <= 0) and (NW > 0) and (SE > 0):
                            coords = [self.axes_left, self.to_canvas_y(y1 + (y2 - y1) * (self.xlim[0] - x1) / (x2 - x1), curve.yaxis),
                                      self.to_canvas_x(x1 + (x2 - x1) * (yaxis.ylim[0] - y1) / (y2 - y1)), self.axes_bottom]
                            self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                        elif (SE <= 0) and (SW > 0) and (NE > 0):
                            coords = [self.to_canvas_x(x1 + (x2 - x1) * (yaxis.ylim[0] - y1) / (y2 - y1)), self.axes_bottom,
                                      self.axes_right, self.to_canvas_y(y1 + (y2 - y1) * (self.xlim[1] - x1) / (x2 - x1), curve.yaxis)]
                            self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                        elif (NW > 0) and (NE > 0) and (SW <= 0) and (SE <= 0):
                            coords = [self.axes_left, self.to_canvas_y(y1 + (y2 - y1) * (self.xlim[0] - x1) / (x2 - x1), curve.yaxis),
                                      self.axes_right, self.to_canvas_y(y1 + (y2 - y1) * (self.xlim[1] - x1) / (x2 - x1), curve.yaxis)]
                            self.canvas.add(Line(points = coords, width = self.curve_lineweight))
                        elif (NW * NE < 0) and (SW * SE < 0):
                            coords = [self.to_canvas_x(x1 + (x2 - x1) * (yaxis.ylim[0] - y1) / (y2 - y1)), self.axes_bottom,
                                      self.to_canvas_x(x1 + (x2 - x1) * (yaxis.ylim[1] - y1) / (y2 - y1)), self.axes_top]
                            self.canvas.add(Line(points = coords, width = self.curve_lineweight))

    def draw_curves(self):
        for name in self.curves.keys():
            curve = self.curves[name]
            yaxis = self.yaxes[curve.yaxis]
            if curve.curve_style != '':
                self.draw_curve(curve)
            if curve.marker != '':
                self.canvas.add(Color(*get_color_from_hex(self.colors[curve.marker_color])))
                for i in range(len(curve.points_x)):
                    px = curve.points_x[i]
                    py = curve.points_y[i]
                    pts_in_axes = np.logical_and(np.logical_and(px > self.xlim[0] - self.x_epsilon, px < self.xlim[1] + self.x_epsilon), np.logical_and(py > yaxis.ylim[0] - yaxis.y_epsilon, py < yaxis.ylim[1] + yaxis.y_epsilon))
                    where_pts_in_axes = np.where(pts_in_axes)[0]
                    x = self.axes_left + self.x_pix_per_unit * (px[where_pts_in_axes] - self.xlim[0])
                    y = self.axes_bottom + yaxis.y_pix_per_unit * (py[where_pts_in_axes] - yaxis.ylim[0])
                    for j in range(len(x)):
                        self.draw_marker(x[j], y[j], curve.marker, curve.marker_color, name)

    def draw_v_grid_line(self, x):
        self.canvas.add(Line(points = [x, self.axes_top, x, self.axes_bottom], width = self.tick_lineweight))

    def draw_h_grid_line(self, y):
        self.canvas.add(Line(points = [self.axes_left, y, self.axes_right, y], width = self.tick_lineweight))

    def draw_grid(self):
        if self.grid_state == 'on':
            self.canvas.add(Color(*get_color_from_hex(self.grid_color)))
            for [x, label] in self.x_ticks:
                self.draw_v_grid_line(self.to_canvas_x(x))
            if self.xaxis_mode == 'log':
                for [x, label] in self.x_minor_ticks:
                    self.draw_v_grid_line(self.to_canvas_x(x))

            for [y, label] in self.left_y_ticks:
                self.draw_h_grid_line(self.to_canvas_y(y, self.left_yaxis))
            if self.left_yaxis != '' and self.yaxes[self.left_yaxis].yaxis_mode == 'log':
                for [y, label] in self.left_y_minor_ticks:
                    self.draw_h_grid_line(self.to_canvas_y(y, self.left_yaxis))

            for [y, label] in self.right_y_ticks:
                self.draw_h_grid_line(self.to_canvas_y(y, self.right_yaxis))
            if self.right_yaxis != '' and self.yaxes[self.right_yaxis].yaxis_mode == 'log':
                for [y, label] in self.right_y_minor_ticks:
                    self.draw_h_grid_line(self.to_canvas_y(y, self.right_yaxis))

    def draw_top_tick(self, x):
        self.canvas.add(Line(points = [x, self.axes_top, x, self.axes_top - self.tick_length], width = self.tick_lineweight))
    
    def draw_bottom_tick(self, x):
        self.canvas.add(Line(points = [x, self.axes_bottom, x, self.axes_bottom + self.tick_length], width = self.tick_lineweight))

    def draw_left_tick(self, y):
        self.canvas.add(Line(points = [self.axes_left, y, self.axes_left + self.tick_length, y], width = self.tick_lineweight))

    def draw_right_tick(self, y):
        self.canvas.add(Line(points = [self.axes_right, y, self.axes_right - self.tick_length, y], width = self.tick_lineweight))

    def draw_top_minor_tick(self, x):
        self.canvas.add(Line(points = [x, self.axes_top, x, self.axes_top - 0.5 * self.tick_length], width = self.tick_lineweight))
    
    def draw_bottom_minor_tick(self, x):
        self.canvas.add(Line(points = [x, self.axes_bottom, x, self.axes_bottom + 0.5 * self.tick_length], width = self.tick_lineweight))

    def draw_left_minor_tick(self, y):
        self.canvas.add(Line(points = [self.axes_left, y, self.axes_left + 0.5 * self.tick_length, y], width = self.tick_lineweight))

    def draw_right_minor_tick(self, y):
        self.canvas.add(Line(points = [self.axes_right, y, self.axes_right - 0.5 * self.tick_length, y], width = self.tick_lineweight))

    def draw_bottom_tick_label(self, x, label):
        self.add_text(text = label, anchor_pos = [x, self.axes_bottom - 0.5 * self.label_fontsize], anchor = 'n', color = self.axes_color if self.xaxis_color is None else self.xaxis_color, font_size = self.label_fontsize)

    def draw_left_tick_label(self, y, label, label_color):
        self.add_text(text = label, anchor_pos = [self.axes_left - 0.5 * self.label_fontsize, y], anchor = 'e', color = label_color, font_size = self.label_fontsize)

    def draw_right_tick_label(self, y, label, label_color):
        self.add_text(text = label, anchor_pos = [self.axes_right + 0.5 * self.label_fontsize, y], anchor = 'w', color = label_color, font_size = self.label_fontsize)

    def draw_x_ticks(self):
        if (len(self.x_ticks) != 0) or (len(self.x_minor_ticks) != 0):
            self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
            for [x, label] in self.x_ticks:
                self.draw_top_tick(self.to_canvas_x(x))
                self.draw_bottom_tick(self.to_canvas_x(x))
            for [x, label] in self.x_minor_ticks:
                self.draw_top_minor_tick(self.to_canvas_x(x))
                self.draw_bottom_minor_tick(self.to_canvas_x(x))
            for [x, label] in self.x_ticks:
                if label != '':
                    self.draw_bottom_tick_label(self.to_canvas_x(x), label + self.xaxis_units)
            for [x, label] in self.x_minor_ticks:
                if label != '':
                    self.draw_bottom_tick_label(self.to_canvas_x(x), label + self.xaxis_units)

    def draw_y_ticks(self):
        left_curves = [curve_name for curve_name in self.curves if self.curves[curve_name].yaxis == self.left_yaxis]
        right_curves = [curve_name for curve_name in self.curves if self.curves[curve_name].yaxis == self.right_yaxis]
        if (self.left_yaxis != '') and ((self.right_yaxis == '') or (len(right_curves) == 0)):
            if (len(self.left_y_ticks) != 0) or (len(self.left_y_minor_ticks) != 0):
                self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
                for [y, label] in self.left_y_ticks:
                    self.draw_left_tick(self.to_canvas_y(y, self.left_yaxis))
                    self.draw_right_tick(self.to_canvas_y(y, self.left_yaxis))
                for [y, label] in self.left_y_minor_ticks:
                    self.draw_left_minor_tick(self.to_canvas_y(y, self.left_yaxis))
                    self.draw_right_minor_tick(self.to_canvas_y(y, self.left_yaxis))
                for [y, label] in self.left_y_ticks:
                    if label != '':
                        self.draw_left_tick_label(self.to_canvas_y(y, self.left_yaxis), label + self.yaxes[self.left_yaxis].units, self.yaxes[self.left_yaxis].color)
                for [y, label] in self.left_y_minor_ticks:
                    if label != '':
                        self.draw_left_tick_label(self.to_canvas_y(y, self.left_yaxis), label + self.yaxes[self.left_yaxis].units, self.yaxes[self.left_yaxis].color)
        elif ((self.left_yaxis == '') or (len(left_curves) == 0)) and (self.right_yaxis != ''):
            if (len(self.right_y_ticks) != 0) or (len(self.right_y_minor_ticks) != 0):
                self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
                for [y, label] in self.right_y_ticks:
                    self.draw_left_tick(self.to_canvas_y(y, self.right_yaxis))
                    self.draw_right_tick(self.to_canvas_y(y, self.right_yaxis))
                for [y, label] in self.right_y_minor_ticks:
                    self.draw_left_minor_tick(self.to_canvas_y(y, self.right_yaxis))
                    self.draw_right_minor_tick(self.to_canvas_y(y, self.right_yaxis))
                for [y, label] in self.right_y_ticks:
                    if label != '':
                        self.draw_right_tick_label(self.to_canvas_y(y, self.right_yaxis), label + self.yaxes[self.right_yaxis].units, self.yaxes[self.right_yaxis].color)
                for [y, label] in self.right_y_minor_ticks:
                    if label != '':
                        self.draw_right_tick_label(self.to_canvas_y(y, self.right_yaxis), label + self.yaxes[self.right_yaxis].units, self.yaxes[self.right_yaxis].color)
        elif (self.left_yaxis != '') and (self.right_yaxis != ''):
            if (len(self.left_y_ticks) != 0) or (len(self.left_y_minor_ticks) != 0) or (len(self.right_y_ticks) != 0) or (len(self.right_y_minor_ticks) != 0):
                self.canvas.add(Color(*get_color_from_hex(self.axes_color)))
                for [y, label] in self.left_y_ticks:
                    self.draw_left_tick(self.to_canvas_y(y, self.left_yaxis))
                for [y, label] in self.left_y_minor_ticks:
                    self.draw_left_minor_tick(self.to_canvas_y(y, self.left_yaxis))
                for [y, label] in self.left_y_ticks:
                    if label != '':
                        self.draw_left_tick_label(self.to_canvas_y(y, self.left_yaxis), label + self.yaxes[self.left_yaxis].units, self.yaxes[self.left_yaxis].color)
                for [y, label] in self.left_y_minor_ticks:
                    if label != '':
                        self.draw_left_tick_label(self.to_canvas_y(y, self.left_yaxis), label + self.yaxes[self.left_yaxis].units, self.yaxes[self.left_yaxis].color)
                for [y, label] in self.right_y_ticks:
                    self.draw_right_tick(self.to_canvas_y(y, self.right_yaxis))
                for [y, label] in self.right_y_minor_ticks:
                    self.draw_right_minor_tick(self.to_canvas_y(y, self.right_yaxis))
                for [y, label] in self.right_y_ticks:
                    if label != '':
                        self.draw_right_tick_label(self.to_canvas_y(y, self.right_yaxis), label + self.yaxes[self.right_yaxis].units, self.yaxes[self.right_yaxis].color)
                for [y, label] in self.right_y_minor_ticks:
                    if label != '':
                        self.draw_right_tick_label(self.to_canvas_y(y, self.right_yaxis), label + self.yaxes[self.right_yaxis].units, self.yaxes[self.right_yaxis].color)

    def draw_axis_labels(self):
        if self.xlabel_value != '':
            self.add_text(text = self.xlabel_value, anchor_pos = [0.5 * (self.axes_left + self.axes_right), self.axes_bottom - 2.5 * self.label_fontsize], anchor = 'n', color = self.axes_color if self.xaxis_color is None else self.xaxis_color, font_size = self.label_fontsize)
        if self.left_yaxis != '':
            if self.yaxes[self.left_yaxis].ylabel_value != '':
                self.add_text(text = self.yaxes[self.left_yaxis].ylabel_value, anchor_pos = [self.axes_left, self.axes_top + 0.5 * self.label_fontsize], anchor = 'sw', color = self.yaxes[self.left_yaxis].color, font_size = self.label_fontsize)
        if self.right_yaxis != '':
            if self.yaxes[self.right_yaxis].ylabel_value != '':
                self.add_text(text = self.yaxes[self.right_yaxis].ylabel_value, anchor_pos = [self.axes_right, self.axes_top + 0.5 * self.label_fontsize], anchor = 'se', color = self.yaxes[self.right_yaxis].color, font_size = self.label_fontsize)

    def find_x_ticks(self):
        self.x_ticks = []
        self.x_minor_ticks = []
        if self.curves != {}:
            if self.xaxis_mode == 'linear':
                self.x_ticks = self.find_linear_ticks(self.xlimits_mode, self.axes_width, self.xrange, self.xlim, self.x_epsilon, self.xmin, self.xmax)
                self.x_minor_ticks = self.find_linear_minor_ticks(self.axes_width, self.xrange, self.xlim, self.x_epsilon, self.xmin, self.xmax)
            elif self.xaxis_mode == 'log':
                self.x_ticks = self.find_log_ticks(self.xlimits_mode, self.axes_width, self.xrange, self.xlim, self.x_epsilon, self.xaxis_sign, self.xmin, self.xmax)
                self.x_minor_ticks = self.find_log_minor_ticks(self.axes_width, self.xrange, self.xlim, self.x_epsilon, self.xaxis_sign, self.xmin, self.xmax)

    def find_y_ticks(self):
        self.left_y_ticks = []
        self.left_y_minor_ticks = []
        self.right_y_ticks = []
        self.right_y_minor_ticks = []
        left_curves = [curve_name for curve_name in self.curves if self.curves[curve_name].yaxis == self.left_yaxis]
        right_curves = [curve_name for curve_name in self.curves if self.curves[curve_name].yaxis == self.right_yaxis]
        if self.curves != {}:
            if (self.left_yaxis != '') and (len(left_curves) != 0):
                yaxis = self.yaxes[self.left_yaxis]
                if yaxis.yaxis_mode == 'linear':
                    self.left_y_ticks = self.find_linear_ticks(yaxis.ylimits_mode, self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.ymin, yaxis.ymax)
                    self.left_y_minor_ticks = self.find_linear_minor_ticks(self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.ymin, yaxis.ymax)
                elif yaxis.yaxis_mode == 'log':
                    self.left_y_ticks = self.find_log_ticks(yaxis.ylimits_mode, self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.yaxis_sign, yaxis.ymin, yaxis.ymax)
                    self.left_y_minor_ticks = self.find_log_minor_ticks(self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.yaxis_sign, yaxis.ymin, yaxis.ymax)
            if (self.right_yaxis != '') and (len(right_curves) != 0):
                yaxis = self.yaxes[self.right_yaxis]
                if yaxis.yaxis_mode == 'linear':
                    self.right_y_ticks = self.find_linear_ticks(yaxis.ylimits_mode, self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.ymin, yaxis.ymax)
                    self.right_y_minor_ticks = self.find_linear_minor_ticks(self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.ymin, yaxis.ymax)
                elif yaxis.yaxis_mode == 'log':
                    self.right_y_ticks = self.find_log_ticks(yaxis.ylimits_mode, self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.yaxis_sign, yaxis.ymin, yaxis.ymax)
                    self.right_y_minor_ticks = self.find_log_minor_ticks(self.axes_height, yaxis.yrange, yaxis.ylim, yaxis.y_epsilon, yaxis.yaxis_sign, yaxis.ymin, yaxis.ymax)

    def find_linear_ticks(self, axis_limits_mode, axis_dimension, axis_range, axis_lim, epsilon, axis_min, axis_max):
        if axis_limits_mode == 'auto':
            axis_range = axis_max - axis_min
        tick_interval = axis_range / min(10., axis_dimension / (2.5 * self.label_fontsize))
        foo = math.log10(tick_interval)
        bar = math.floor(foo)
        foobar = foo - bar
        if foobar < 0.001:
            tick_interval = math.pow(10., bar)
        elif foobar < math.log10(2.001):
            tick_interval = 2. * math.pow(10., bar)
        elif foobar < math.log10(5.001):
            tick_interval = 5. * math.pow(10., bar)
        else:
            tick_interval = 10. * math.pow(10., bar)
        if axis_limits_mode == 'auto':
            axis_lim[0] = tick_interval * math.floor(axis_min / tick_interval)
            axis_lim[1] = tick_interval * math.ceil(axis_max / tick_interval)
            self.update_sizes()
        tick = tick_interval * round(axis_lim[0] / tick_interval)
        ticks = []
        for i in range(int(math.ceil((axis_lim[1] - axis_lim[0]) / tick_interval)) + 1):
            if (tick > axis_lim[0] - epsilon) and (tick < axis_lim[1] + epsilon):
                ticks.append(tick_interval * round(tick / tick_interval))
            tick += tick_interval

        if len(ticks) != 0:
            if (min(ticks) == 0.) and (max(ticks) == 0.):
                foo = 0
            else:
                foo = int(math.floor(math.log10(max(abs(min(ticks)), abs(max(ticks)), axis_range)) / 3.))
        axis_ticks = []
        for tick in ticks:
            if (foo >= -8) and (foo <= 8):
                if tick == -0.:
                    tick = 0.
                tick_label = '{:g}'.format(self.multipliers[foo] * tick)
                if tick_label[-2:] == '.0':
                    tick_label = tick_label.replace('.0', '')
                axis_ticks.append([tick, tick_label + self.prefixes[foo]])
            else:
                axis_ticks.append([tick, '{:g}'.format(tick)])
        return axis_ticks

    def find_linear_minor_ticks(self, axis_dimension, axis_range, axis_lim, epsilon, axis_min, axis_max):
        if self.linear_minor_ticks == 'off':
            return []

        tick_interval = axis_range / min(10., axis_dimension / (2.5 * self.label_fontsize))
        foo = math.log10(tick_interval)
        bar = math.floor(foo)
        foobar = foo - bar
        if foobar < 0.001:
            tick_interval = math.pow(10., bar)
            minor_tick_interval = 0.2 * tick_interval
        elif foobar < math.log10(2.001):
            tick_interval = 2. * math.pow(10., bar)
            minor_tick_interval = 0.25 * tick_interval
        elif foobar < math.log10(5.001):
            tick_interval = 5. * math.pow(10., bar)
            minor_tick_interval = 0.2 * tick_interval
        else:
            tick_interval = 10. * math.pow(10., bar)
            minor_tick_interval = 0.2 * tick_interval

        tick = tick_interval * round(axis_lim[0] / tick_interval)
        minor_tick = minor_tick_interval * round(axis_lim[0] / minor_tick_interval)
        if tick < minor_tick:
            tick += tick_interval

        axis_minor_ticks = []
        for i in range(int(math.ceil((axis_lim[1] - axis_lim[0]) / minor_tick_interval)) + 1):
            if (minor_tick > axis_lim[0] - epsilon) and (minor_tick < axis_lim[1] + epsilon) and abs(minor_tick - tick) > epsilon:
                axis_minor_ticks.append([minor_tick_interval * round(minor_tick / minor_tick_interval), ''])
            minor_tick += minor_tick_interval
            if tick < minor_tick:
                tick += tick_interval
    
        return axis_minor_ticks

    def find_log_ticks(self, axis_limits_mode, axis_dimension, axis_range, axis_lim, epsilon, sign, axis_min, axis_max):
        if axis_limits_mode == 'auto':
            axis_range = axis_max - axis_min
        tick_interval = math.ceil(axis_range / min(10., axis_dimension / (2.5 * self.label_fontsize)))
        if axis_limits_mode == 'auto':
            axis_lim[0] = tick_interval * math.floor(axis_min / tick_interval)
            axis_lim[1] = tick_interval * math.ceil(axis_max / tick_interval)
            self.update_sizes()
        tick = tick_interval * round(axis_lim[0] / tick_interval)
        ticks = []
        for i in range(int(math.ceil((axis_lim[1] - axis_lim[0]) / tick_interval)) + 1):
            if (tick > axis_lim[0] - epsilon) and (tick < axis_lim[1] + epsilon):
                ticks.append(tick_interval * round(tick / tick_interval))
            tick += tick_interval
        axis_ticks = []
        for tick in ticks:
            foo = int(math.floor(sign * tick / 3.))
            if (foo >= -8) and (foo <= 8):
                tick_label = '{:g}'.format(sign * round(self.multipliers[foo] * math.pow(10., sign * tick)))
                if tick_label[-2:] == '.0':
                    tick_label = tick_label.replace('.0', '')
                axis_ticks.append([tick, tick_label + self.prefixes[foo]])
            else:
                axis_ticks.append([tick, '{:g}'.format(sign * math.pow(10., sign * tick))])
        return axis_ticks

    def find_log_minor_ticks(self, axis_dimension, axis_range, axis_lim, epsilon, sign, axis_min, axis_max):
        minor_ticks = []
        tick_interval = axis_range / min(10., axis_dimension / (2.5 * self.label_fontsize))
        minor_tick_interval = 10. * min(1. - math.pow(10., -tick_interval), math.pow(10., tick_interval) - 1.)
        tick_interval = math.ceil(tick_interval)
        foo = math.log10(minor_tick_interval)
        bar = math.floor(foo)
        foobar = foo - bar
        if foobar < 0.001:
            minor_tick_interval = math.pow(10., bar)
        elif foobar < math.log10(2.001):
            minor_tick_interval = 2. * math.pow(10., bar)
        elif foobar < math.log10(5.001):
            minor_tick_interval = 5. * math.pow(10., bar)
        else:
            minor_tick_interval = 10. * math.pow(10., bar)
        if (tick_interval == 1.) and (axis_range <= 1.):
            label_threshold = 2.5 * self.label_fontsize * epsilon
            if minor_tick_interval < 1.:
                ticks_to_label = []
                tick = 1. + minor_tick_interval
                while tick < 10. - 0.001 * minor_tick_interval:
                    ticks_to_label.append(tick)
                    tick += minor_tick_interval
            elif math.log10(10. / 9.) > label_threshold:
                ticks_to_label = range(2, 10)
            elif math.log10(1.25) > label_threshold:
                ticks_to_label = range(2, 10, 2)
            elif math.log10(2) > label_threshold:
                ticks_to_label = [2, 5]
            elif math.log10(3) > label_threshold:
                ticks_to_label = [3]
            else:
                ticks_to_label = []
            for i in range(int(math.ceil(axis_range)) + 2):
                exponent = math.floor(axis_lim[0]) + i
                for j in ticks_to_label:
                    minor_tick = exponent + sign * math.log10(float(j))
                    if (minor_tick > axis_lim[0] - epsilon) and (minor_tick < axis_lim[1] + epsilon):
                        foo = int(math.floor(sign * minor_tick / 3.))
                        if (foo >= -8) and (foo <= 8):
                            tick_label = '{:g}'.format(sign * self.multipliers[foo] * math.pow(10., sign * minor_tick))
                            if tick_label[-2:] == '.0':
                                tick_label = tick_label.replace('.0', '')
                            minor_ticks.append([minor_tick, tick_label + self.prefixes[foo]])
                        else:
                            minor_ticks.append([minor_tick, '{:g}'.format(sign * math.pow(10., sign * minor_tick))])
        elif (tick_interval == 1.) and (math.log10(10. / 9.) > 2. * epsilon):
            for i in range(int(math.ceil(axis_range)) + 2):
                exponent = math.floor(axis_lim[0]) + i
                for j in range(2, 10):
                    minor_tick = exponent + sign * math.log10(float(j))
                    if (minor_tick > axis_lim[0] - epsilon) and (minor_tick < axis_lim[1] + epsilon):
                        minor_ticks.append([minor_tick, ''])
        elif (tick_interval > 1.) and (epsilon < 0.25):
            for i in range(int(math.ceil(axis_range)) + 2):
                minor_tick = math.floor(axis_lim[0]) + i
                if (minor_tick > axis_lim[0] - epsilon) and (minor_tick < axis_lim[1] + epsilon) and (minor_tick != tick_interval * round(minor_tick / tick_interval)):
                    minor_ticks.append([minor_tick, ''])
        return minor_ticks
 
    def find_axes_limits(self):
        if self.curves != {}:
            if self.xlimits_mode != 'manual':
                x_mins = []
                x_maxs = []
                for curve_name in self.curves.keys():
                    curve = self.curves[curve_name]
                    yaxis = self.yaxes[curve.yaxis]
                    if yaxis.ylimits_mode == 'manual':
                        for i in range(len(curve.points_x)):
                            pts_where_y_in_axes = np.where(np.logical_and(curve.points_y[i] > yaxis.ylim[0] - yaxis.y_epsilon, curve.points_y[i] < yaxis.ylim[1] + yaxis.y_epsilon))[0]
                            if len(pts_where_y_in_axes) != 0:
                                x_mins.append(np.amin(curve.points_x[i][pts_where_y_in_axes]))
                                x_maxs.append(np.amax(curve.points_x[i][pts_where_y_in_axes]))
                    else:
                        for i in range(len(curve.points_x)):
                            if len(curve.points_x[i]) != 0:
                                x_mins.append(np.amin(curve.points_x[i]))
                                x_maxs.append(np.amax(curve.points_x[i]))
                if (len(x_mins) > 0) and (len(x_maxs) > 0):
                    self.xlim[0] = min(x_mins)
                    self.xlim[1] = max(x_maxs)
                    if self.xlim[0] == self.xlim[1]:
                        if self.xlim[0] > 0.:
                            self.xlim[0] = 0.95 * self.xlim[0]
                            self.xlim[1] = 1.05 * self.xlim[1]
                        elif self.xlim[0] < 0.:
                            self.xlim[0] = 1.05 * self.xlim[0]
                            self.xlim[1] = 0.95 * self.xlim[1]
                        else:
                            self.xlim[0] = -0.05
                            self.xlim[1] = 0.05
                    self.xmin = self.xlim[0]
                    self.xmax = self.xlim[1]
            for yaxis_name in self.yaxes.keys():
                yaxis = self.yaxes[yaxis_name]
                if yaxis.ylimits_mode != 'manual':
                    y_mins = []
                    y_maxs = []
                    for curve_name in self.curves.keys():
                        curve = self.curves[curve_name]
                        if curve.yaxis == yaxis_name:
                            if self.xlimits_mode == 'manual':
                                for i in range(len(curve.points_y)):
                                    pts_where_x_in_axes = np.where(np.logical_and(curve.points_x[i] > self.xlim[0] - self.x_epsilon, curve.points_x[i] < self.xlim[1] + self.x_epsilon))[0]
                                    if len(pts_where_x_in_axes) != 0:
                                        y_mins.append(np.amin(curve.points_y[i][pts_where_x_in_axes]))
                                        y_maxs.append(np.amax(curve.points_y[i][pts_where_x_in_axes]))
                            else:
                                for i in range(len(curve.points_y)):
                                    if len(curve.points_y[i]) != 0:
                                        y_mins.append(np.amin(curve.points_y[i]))
                                        y_maxs.append(np.amax(curve.points_y[i]))
                    if (len(y_mins) > 0) and (len(y_maxs) > 0):
                        yaxis.ylim[0] = min(y_mins)
                        yaxis.ylim[1] = max(y_maxs)
                        if yaxis.ylim[0] == yaxis.ylim[1]:
                            if yaxis.ylim[0] > 0.:
                                yaxis.ylim[0] = 0.95 * yaxis.ylim[0]
                                yaxis.ylim[1] = 1.05 * yaxis.ylim[1]
                            elif yaxis.ylim[0] < 0.:
                                yaxis.ylim[0] = 1.05 * yaxis.ylim[0]
                                yaxis.ylim[1] = 0.95 * yaxis.ylim[1]
                            else:
                                yaxis.ylim[0] = -0.05
                                yaxis.ylim[1] = 0.05
                        yaxis.ymin = yaxis.ylim[0]
                        yaxis.ymax = yaxis.ylim[1]

    def parse_style(self, style):
        length = len(style)
        colors = self.colors.keys()
        markers = self.marker_coords.keys()
        linestyles = self.linestyles.keys()
        marker_color = ''
        marker = ''
        curve_color = ''
        curve_style = ''
        if (length >= 1) and (style[0] in colors):
            if (length >= 2) and (style[1] in markers):
                marker_color = style[0]
                marker = style[1]
                if (length >= 3) and (style[2] in colors):
                    curve_color = style[2]
                    if (length >= 5) and (style[3:5] in linestyles):
                        curve_style = style[3:5]
                    elif (length >= 4) and (style[3] in linestyles):
                        curve_style = style[3]
                elif (length >= 4) and (style[2:4] in linestyles):
                    curve_style = style[2:4]
                elif (length >= 3) and (style[2] in linestyles):
                    curve_style = style[2]
            elif (length >= 3) and (style[1:3] in linestyles):
                curve_color = style[0]
                curve_style = style[1:3]
            elif (length >= 2) and (style[1] in linestyles):
                curve_color = style[0]
                curve_style = style[1]
        elif (length >= 1) and (style[0] in markers):
            marker = style[0]
            if (length >= 2) and (style[1] in colors):
                curve_color = style[1]
                if (length >= 4) and (style[2:4] in linestyles):
                    curve_style = style[2:4]
                elif (length >= 3) and (style[2] in linestyles):
                    curve_style = style[2]
            elif (length >= 3) and (style[1:3] in linestyles):
                curve_style = style[1:3]
            elif (length >= 2) and (style[1] in linestyles):
                curve_style = style[1]
        elif (length >= 2) and (style[0:2] in linestyles):
            curve_style = style[0:2]
        elif (length >= 1) and (style[0] in linestyles):
            curve_style = style[0]
        if (marker == '') and (curve_style == ''):
            marker = self.default_marker
            curve_style = self.default_curve_style
        if ((marker != '') and (marker_color == '')) or ((curve_style != '') and (curve_color == '')):
            if marker_color == '':
                marker_color = self.default_color_order[self.default_color_index]
            if curve_color == '':
                curve_color = self.default_color_order[self.default_color_index]
            self.default_color_index = self.default_color_index + 1
            if self.default_color_index >= len(self.default_color_order):
                self.default_color_index = 0
        if (marker_color != '') and (curve_color == ''):
            curve_color = marker_color
        if (marker_color == '') and (curve_color != ''):
            marker_color = curve_color
        return [marker_color, marker, curve_color, curve_style]

    def new_data(self, x, y, style = '', name = '', yaxis = 'left', hold = 'off'):
        new_curves = {}
        if type(x) is np.ndarray:
            if type(y) is np.ndarray:
                if len(x) == len(y):
                    if name != '':
                        curve_name = name
                    else:
                        curve_name = 'curve{0:05d}'.format(self.curve_id)
                        self.curve_id += 1
                    new_curves[curve_name] = self.curve(name = curve_name, yaxis = yaxis, data_x = x.copy(), data_y = y.copy())
                    [new_curves[curve_name].marker_color, new_curves[curve_name].marker, new_curves[curve_name].curve_color, new_curves[curve_name].curve_style] = self.parse_style(style)
                else:
                    raise IndexError('x and y numpy arrays supplied did not have the same number of elements')
            elif (type(y) is list) and all([type(v) is np.ndarray for v in y]):
                if all([len(x) == len(v) for v in y]):
                    for j in range(len(y)):
                        if (type(name) is list) and name[j] != '':
                            curve_name = name[j]
                        else:
                            curve_name = 'curve{0:05d}'.format(self.curve_id)
                            self.curve_id += 1
                        new_curves[curve_name] = self.curve(name = curve_name, yaxis = yaxis, data_x = x.copy(), data_y = y[j].copy())
                        if type(style) is str:
                            [new_curves[curve_name].marker_color, new_curves[curve_name].marker, new_curves[curve_name].curve_color, new_curves[curve_name].curve_style] = self.parse_style(style)
                        else:
                            [new_curves[curve_name].marker_color, new_curves[curve_name].marker, new_curves[curve_name].curve_color, new_curves[curve_name].curve_style] = self.parse_style(style[j])
                else:
                    raise IndexError('at least one of the numpy arrays supplied in y did not have the same number of elements as x')
            else:
                raise TypeError('if x is a numpy array, y must either be a numpy array or a list of numpy arrays')
        elif (type(x) is list) and all([type(v) is np.ndarray for v in x]):
            if (type(y) is list) and all([type(v) is np.ndarray for v in y]):
                if len(x) == len(y):
                    if all([len(x[j]) == len(y[j]) for j in range(len(x))]):
                        for j in range(len(x)):
                            if (type(name) is list) and name[j] != '':
                                curve_name = name[j]
                            else:
                                curve_name = 'curve{0:05d}'.format(self.curve_id)
                                self.curve_id += 1
                            new_curves[curve_name] = self.curve(name = curve_name, yaxis = yaxis, data_x = x[j].copy(), data_y = y[j].copy())
                            if type(style) is str:
                                [new_curves[curve_name].marker_color, new_curves[curve_name].marker, new_curves[curve_name].curve_color, new_curves[curve_name].curve_style] = self.parse_style(style)
                            else:
                                [new_curves[curve_name].marker_color, new_curves[curve_name].marker, new_curves[curve_name].curve_color, new_curves[curve_name].curve_style] = self.parse_style(style[j])
                    else:
                        raise IndexError('at least one of the numpy arrays supplied in x did not have the same number of elements as the corresponding numpy arrays supplied in y')
                else:
                    raise IndexError('x and y supplied did not contain the same number of numpy arrays')
            else:
                raise TypeError('if x is a list of numpy arrays, y must also be a list of numpy arrays')
        else:
            raise TypeError('x and y supplied were not numpy arrays or lists of numpy arrays')
        if hold == 'off':
            self.curves = new_curves
        else:
            self.curves.update(new_curves)

    def plot(self, x, y, style = '', **kwargs):
        name = kwargs.get('name', '')

        yaxis = kwargs.get('yaxis', 'left')
        if yaxis not in self.yaxes.keys():
            raise ValueError("specified y-axis does not exist")

        hold = kwargs.get('hold', 'off')
        if hold not in ('on', 'off'):
            raise ValueError("if specified, hold must be 'on' or 'off'")
        if hold == 'off':
            self.default_color_index = 0

        self.new_data(x, y, style, name, yaxis, hold)

        self.xaxis_mode = 'linear'
        self.xlimits_mode = 'auto'

        self.yaxes[yaxis].yaxis_mode = 'linear'
        self.yaxes[yaxis].ylimits_mode = 'auto'

        for curve_name in self.curves.keys():
            curve = self.curves[curve_name]
            yaxis = self.yaxes[curve.yaxis]
            if yaxis.yaxis_mode == 'linear':
                curve.points_x = [curve.data_x.copy()]
                curve.points_y = [curve.data_y.copy()]
            elif yaxis.yaxis_mode == 'log':
                where_y_has_same_sign_as_yaxis = np.where(curve.data_y * yaxis.yaxis_sign > 0.)[0]
                runs_where_y_has_same_sign_as_yaxis = np.split(where_y_has_same_sign_as_yaxis, np.where(np.diff(where_y_has_same_sign_as_yaxis) != 1)[0] + 1)
                curve.points_x = [curve.data_x[run].copy() for run in runs_where_y_has_same_sign_as_yaxis]
                curve.points_y = [yaxis.yaxis_sign * np.log10(yaxis.yaxis_sign * curve.data_y[run]) for run in runs_where_y_has_same_sign_as_yaxis]

        self.refresh_plot()

    def semilogx(self, x, y, style = '', **kwargs):
        name = kwargs.get('name', '')

        yaxis = kwargs.get('yaxis', 'left')
        if yaxis not in self.yaxes.keys():
            raise ValueError("specified y-axis does not exist")

        hold = kwargs.get('hold', 'off')
        if hold not in ('on', 'off'):
            raise ValueError("if specified, hold must be 'on' or 'off'")
        if hold == 'off':
            self.default_color_index = 0

        self.new_data(x, y, style, name, yaxis, hold)

        self.xaxis_mode = 'log'
        pos_x_values = 0
        total_x_values = 0
        for curve_name in self.curves.keys():
            pos_x_values += len(np.where(self.curves[curve_name].data_x > 0.)[0])
            total_x_values += len(self.curves[curve_name].data_x)
        self.xaxis_sign = 1. if pos_x_values >= total_x_values // 2 else -1.
        self.xlimits_mode = 'auto'

        self.yaxes[yaxis].yaxis_mode = 'linear'
        self.yaxes[yaxis].ylimits_mode = 'auto'

        for curve_name in self.curves.keys():
            curve = self.curves[curve_name]
            yaxis = self.yaxes[curve.yaxis]
            if yaxis.yaxis_mode == 'linear':
                where_x_has_same_sign_as_xaxis = np.where(curve.data_x * self.xaxis_sign > 0.)[0]
                runs_where_x_has_same_sign_as_xaxis = np.split(where_x_has_same_sign_as_xaxis, np.where(np.diff(where_x_has_same_sign_as_xaxis) != 1)[0] + 1)
                curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_x_has_same_sign_as_xaxis]
                curve.points_y = [curve.data_y[run].copy() for run in runs_where_x_has_same_sign_as_xaxis]
            elif yaxis.yaxis_mode == 'log':
                where_xy_have_same_sign_as_axes = np.where(np.logical_and(curve.data_x * self.xaxis_sign > 0., curve.data_y * yaxis.yaxis_sign > 0.))[0]
                runs_where_xy_have_same_sign_as_axes = np.split(where_xy_have_same_sign_as_axes, np.where(np.diff(where_xy_have_same_sign_as_axes) != 1)[0] + 1)
                curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_xy_have_same_sign_as_axes]
                curve.points_y = [yaxis.yaxis_sign * np.log10(yaxis.yaxis_sign * curve.data_y[run]) for run in runs_where_xy_have_same_sign_as_axes]

        self.refresh_plot()

    def semilogy(self, x, y, style = '', **kwargs):
        name = kwargs.get('name', '')

        yaxis = kwargs.get('yaxis', 'left')
        if yaxis not in self.yaxes.keys():
            raise ValueError("specified y-axis does not exist")

        hold = kwargs.get('hold', 'off')
        if hold not in ('on', 'off'):
            raise ValueError("if specified, hold must be 'on' or 'off'")
        if hold == 'off':
            self.default_color_index = 0

        self.new_data(x, y, style, name, yaxis, hold)

        self.xaxis_mode = 'linear'
        self.xlimits_mode = 'auto'

        self.yaxes[yaxis].yaxis_mode = 'log'
        pos_y_values = 0
        total_y_values = 0
        for curve_name in self.curves.keys():
            if self.curves[curve_name].yaxis == yaxis:
                pos_y_values += len(np.where(self.curves[curve_name].data_y > 0.)[0])
                total_y_values += len(self.curves[curve_name].data_y)
        self.yaxes[yaxis].yaxis_sign = 1. if pos_y_values >= total_y_values // 2 else -1.
        self.yaxes[yaxis].ylimits_mode = 'auto'

        for curve_name in self.curves.keys():
            curve = self.curves[curve_name]
            yaxis = self.yaxes[curve.yaxis]
            if yaxis.yaxis_mode == 'linear':
                curve.points_x = [curve.data_x.copy()]
                curve.points_y = [curve.data_y.copy()]
            elif yaxis.yaxis_mode == 'log':
                where_y_has_same_sign_as_yaxis = np.where(curve.data_y * yaxis.yaxis_sign > 0.)[0]
                runs_where_y_has_same_sign_as_yaxis = np.split(where_y_has_same_sign_as_yaxis, np.where(np.diff(where_y_has_same_sign_as_yaxis) != 1)[0] + 1)
                curve.points_x = [curve.data_x[run].copy() for run in runs_where_y_has_same_sign_as_yaxis]
                curve.points_y = [yaxis.yaxis_sign * np.log10(yaxis.yaxis_sign * curve.data_y[run]) for run in runs_where_y_has_same_sign_as_yaxis]

        self.refresh_plot()

    def loglog(self, x, y, style = '', **kwargs):
        name = kwargs.get('name', '')

        yaxis = kwargs.get('yaxis', 'left')
        if yaxis not in self.yaxes.keys():
            raise ValueError("specified y-axis does not exist")

        hold = kwargs.get('hold', 'off')
        if hold not in ('on', 'off'):
            raise ValueError("if specified, hold must be 'on' or 'off'")
        if hold == 'off':
            self.default_color_index = 0

        self.new_data(x, y, style, name, yaxis, hold)

        self.xaxis_mode = 'log'
        pos_x_values = 0
        total_x_values = 0
        for curve_name in self.curves.keys():
            pos_x_values += len(np.where(self.curves[curve_name].data_x > 0.)[0])
            total_x_values += len(self.curves[curve_name].data_x)
        self.xaxis_sign = 1. if pos_x_values >= total_x_values // 2 else -1.
        self.xlimits_mode = 'auto'

        self.yaxes[yaxis].yaxis_mode = 'log'
        pos_y_values = 0
        total_y_values = 0
        for curve_name in self.curves.keys():
            if self.curves[curve_name].yaxis == yaxis:
                pos_y_values += len(np.where(self.curves[curve_name].data_y > 0.)[0])
                total_y_values += len(self.curves[curve_name].data_y)
        self.yaxes[yaxis].yaxis_sign = 1. if pos_y_values >= total_y_values // 2 else -1.
        self.yaxes[yaxis].ylimits_mode = 'auto'

        for curve_name in self.curves.keys():
            curve = self.curves[curve_name]
            yaxis = self.yaxes[curve.yaxis]
            if yaxis.yaxis_mode == 'linear':
                where_x_has_same_sign_as_xaxis = np.where(curve.data_x * self.xaxis_sign > 0.)[0]
                runs_where_x_has_same_sign_as_xaxis = np.split(where_x_has_same_sign_as_xaxis, np.where(np.diff(where_x_has_same_sign_as_xaxis) != 1)[0] + 1)
                curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_x_has_same_sign_as_xaxis]
                curve.points_y = [curve.data_y[run].copy() for run in runs_where_x_has_same_sign_as_xaxis]
            elif yaxis.yaxis_mode == 'log':
                where_xy_have_same_sign_as_axes = np.where(np.logical_and(curve.data_x * self.xaxis_sign > 0., curve.data_y * yaxis.yaxis_sign > 0.))[0]
                runs_where_xy_have_same_sign_as_axes = np.split(where_xy_have_same_sign_as_axes, np.where(np.diff(where_xy_have_same_sign_as_axes) != 1)[0] + 1)
                curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_xy_have_same_sign_as_axes]
                curve.points_y = [yaxis.yaxis_sign * np.log10(yaxis.yaxis_sign * curve.data_y[run]) for run in runs_where_xy_have_same_sign_as_axes]

        self.refresh_plot()

    def grid(self, *args):
        if len(args) == 0:
            return self.grid_state
        elif args[0] in ('on', 'off'):
            self.grid_state = args[0]
            self.erase_plot()
            self.draw_plot()
        else:
            raise ValueError("invalid grid state specified; it must either be 'on' or 'off'")

    def xlabel(self, *args):
        if len(args) == 0:
            return self.xlabel_value
        else:
            self.xlabel_value = args[0]
            self.erase_plot()
            self.draw_plot()

    def ylabel(self, *args, **kwargs):
        yaxis = kwargs.get('yaxis', 'left')
        if yaxis not in self.yaxes.keys():
            raise ValueError("specified y-axis does not exist")

        if len(args) == 0:
            return self.yaxes[yaxis].ylabel_value
        else:
            self.yaxes[yaxis].ylabel_value = str(args[0])
            self.erase_plot()
            self.draw_plot()

    def xaxis(self, *args):
        if len(args) == 0:
            return self.xaxis_mode
        elif args[0] == 'linear':
            self.xaxis_mode = 'linear'
            self.xlimits_mode = 'auto'

            for curve_name in self.curves.keys():
                curve = self.curves[curve_name]
                yaxis = self.yaxes[curve.yaxis]
                if yaxis.yaxis_mode == 'linear':
                    curve.points_x = [curve.data_x.copy()]
                    curve.points_y = [curve.data_y.copy()]
                elif yaxis.yaxis_mode == 'log':
                    where_y_has_same_sign_as_yaxis = np.where(curve.data_y * yaxis.yaxis_sign > 0.)[0]
                    runs_where_y_has_same_sign_as_yaxis = np.split(where_y_has_same_sign_as_yaxis, np.where(np.diff(where_y_has_same_sign_as_yaxis) != 1)[0] + 1)
                    curve.points_x = [curve.data_x[run].copy() for run in runs_where_y_has_same_sign_as_yaxis]
                    curve.points_y = [yaxis.yaxis_sign * np.log10(yaxis.yaxis_sign * curve.data_y[run]) for run in runs_where_y_has_same_sign_as_yaxis]
            self.refresh_plot()
        elif args[0] == 'log':
            self.xaxis_mode = 'log'
            pos_x_values = 0
            total_x_values = 0
            for curve_name in self.curves.keys():
                pos_x_values += len(np.where(self.curves[curve_name].data_x > 0.)[0])
                total_x_values += len(self.curves[curve_name].data_x)
            self.xaxis_sign = 1. if pos_x_values >= total_x_values // 2 else -1.
            self.xlimits_mode = 'auto'

            for curve_name in self.curves.keys():
                curve = self.curves[curve_name]
                yaxis = self.yaxes[curve.yaxis]
                if yaxis.yaxis_mode == 'linear':
                    where_x_has_same_sign_as_xaxis = np.where(curve.data_x * self.xaxis_sign > 0.)[0]
                    runs_where_x_has_same_sign_as_xaxis = np.split(where_x_has_same_sign_as_xaxis, np.where(np.diff(where_x_has_same_sign_as_xaxis) != 1)[0] + 1)
                    curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_x_has_same_sign_as_xaxis]
                    curve.points_y = [curve.data_y[run].copy() for run in runs_where_x_has_same_sign_as_xaxis]
                elif yaxis.yaxis_mode == 'log':
                    where_xy_have_same_sign_as_axes = np.where(np.logical_and(curve.data_x * self.xaxis_sign > 0., curve.data_y * yaxis.yaxis_sign > 0.))[0]
                    runs_where_xy_have_same_sign_as_axes = np.split(where_xy_have_same_sign_as_axes, np.where(np.diff(where_xy_have_same_sign_as_axes) != 1)[0] + 1)
                    curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_xy_have_same_sign_as_axes]
                    curve.points_y = [yaxis.yaxis_sign * np.log10(yaxis.yaxis_sign * curve.data_y[run]) for run in runs_where_xy_have_same_sign_as_axes]
            self.refresh_plot()
        else:
            raise ValueError("invalid x-axis mode specified; it must either be 'linear' or 'log'")

    def yaxis(self, *args, **kwargs):
        yaxis = kwargs.get('yaxis', 'left')
        if yaxis not in self.yaxes.keys():
            raise ValueError("specified y-axis does not exist")

        if len(args) == 0:
            return self.yaxes[yaxis].yaxis_mode
        elif args[0] == 'linear':
            self.yaxes[yaxis].yaxis_mode = 'linear'
            self.yaxes[yaxis].ylimits_mode = 'auto'

            if self.xaxis_mode == 'linear':
                for curve_name in self.curves.keys():
                    if self.curves[curve_name].yaxis == yaxis:
                        self.curves[curve_name].points_x = [self.curves[curve_name].data_x.copy()]
                        self.curves[curve_name].points_y = [self.curves[curve_name].data_y.copy()]
            elif self.xaxis_mode == 'log':
                for curve_name in self.curves.keys():
                    if self.curves[curve_name].yaxis == yaxis:
                        where_x_has_same_sign_as_xaxis = np.where(self.curves[curve_name].data_x * self.xaxis_sign > 0.)[0]
                        runs_where_x_has_same_sign_as_xaxis = np.split(where_x_has_same_sign_as_xaxis, np.where(np.diff(where_x_has_same_sign_as_xaxis) != 1)[0] + 1)
                        self.curves[curve_name].points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * self.curves[curve_name].data_x[run]) for run in runs_where_x_has_same_sign_as_xaxis]
                        self.curves[curve_name].points_y = [self.curves[curve_name].data_y[run].copy() for run in runs_where_x_has_same_sign_as_xaxis]
            self.refresh_plot()
        elif args[0] == 'log':
            self.yaxes[yaxis].yaxis_mode = 'log'
            pos_y_values = 0
            total_y_values = 0
            for curve_name in self.curves.keys():
                if self.curves[curve_name].yaxis == yaxis:
                    pos_y_values += len(np.where(self.curves[curve_name].data_y > 0.)[0])
                    total_y_values += len(self.curves[curve_name].data_y)
            self.yaxes[yaxis].yaxis_sign = 1. if pos_y_values >= total_y_values // 2 else -1.
            self.yaxes[yaxis].ylimits_mode = 'auto'

            if self.xaxis_mode == 'linear':
                for curve_name in self.curves.keys():
                    if self.curves[curve_name].yaxis == yaxis:
                        where_y_has_same_sign_as_yaxis = np.where(self.curves[curve_name].data_y * self.yaxes[yaxis].yaxis_sign > 0.)[0]
                        runs_where_y_has_same_sign_as_yaxis = np.split(where_y_has_same_sign_as_yaxis, np.where(np.diff(where_y_has_same_sign_as_yaxis) != 1)[0] + 1)
                        self.curves[curve_name].points_x = [self.curves[curve_name].data_x[run].copy() for run in runs_where_y_has_same_sign_as_yaxis]
                        self.curves[curve_name].points_y = [self.yaxes[yaxis].yaxis_sign * np.log10(self.yaxes[yaxis].yaxis_sign * self.curves[curve_name].data_y[run]) for run in runs_where_y_has_same_sign_as_yaxis]
            elif self.xaxis_mode == 'log':
                for curve_name in self.curves.keys():
                    if self.curves[curve_name].yaxis == yaxis:
                        where_xy_have_same_sign_as_axes = np.where(np.logical_and(self.curves[curve_name].data_x * self.xaxis_sign > 0., self.curves[curve_name].data_y * self.yaxes[yaxis].yaxis_sign > 0.))[0]
                        runs_where_xy_have_same_sign_as_axes = np.split(where_xy_have_same_sign_as_axes, np.where(np.diff(where_xy_have_same_sign_as_axes) != 1)[0] + 1)
                        self.curves[curve_name].points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * self.curves[curve_name].data_x[run]) for run in runs_where_xy_have_same_sign_as_axes]
                        self.curves[curve_name].points_y = [self.yaxes[yaxis].yaxis_sign * np.log10(self.yaxes[yaxis].yaxis_sign * self.curves[curve_name].data_y[run]) for run in runs_where_xy_have_same_sign_as_axes]
            self.refresh_plot()
        else:
            raise ValueError("invalid y-axis mode specified; it must either be 'linear' or 'log'")

    def xlimits(self, *args):
        if len(args) == 0:
            if self.xaxis_mode == 'linear':
                return [self.xlim[0], self.xlim[1]]
            elif self.xaxis_mode == 'log':
                return [self.xaxis_sign * math.pow(10., self.xaxis_sign * self.xlim[0]), self.xaxis_sign * math.pow(10., self.xaxis_sign * self.xlim[1])]
        elif args[0] in ('auto', 'tight'):
            self.xlimits_mode = args[0]
        elif type(args[0]) is list:
            if len(args[0]) == 2:
                args[0][0] = float(args[0][0])
                args[0][1] = float(args[0][1])
                if args[0][0] == args[0][1]:
                    raise ValueError('specified lower limit and upper limit were not distinct')
                else:
                    if self.xaxis_mode == 'linear':
                        self.xlimits_mode = 'manual'
                        if args[0][0] < args[0][1]:
                            self.xlim[0] = args[0][0]
                            self.xlim[1] = args[0][1]
                        else:
                            self.xlim[0] = args[0][1]
                            self.xlim[1] = args[0][0]
                    elif self.xaxis_mode == 'log':
                        if args[0][0] * args[0][1] < 0.:
                            raise ValueError('for a logarithmic axis, both limits must have the same sign')
                        if (args[0][0] * args[0][1] == 0.) or (args[0][0] * args[0][1] == -0.):
                            raise ValueError('for a logarithmic axis, neither limit can be zero')
                        self.xlimits_mode = 'manual'
                        if self.xaxis_sign * args[0][0] < 0.:
                            self.xaxis_sign = -self.xaxis_sign
                            for curve_name in self.curves.keys():
                                curve = self.curves[curve_name]
                                yaxis = self.yaxes[curve.yaxis]
                                if yaxis.yaxis_mode == 'linear':
                                    where_x_has_same_sign_as_xaxis = np.where(curve.data_x * self.xaxis_sign > 0.)[0]
                                    runs_where_x_has_same_sign_as_xaxis = np.split(where_x_has_same_sign_as_xaxis, np.where(np.diff(where_x_has_same_sign_as_xaxis) != 1)[0] + 1)
                                    curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_x_has_same_sign_as_xaxis]
                                    curve.points_y = [curve.data_y[run].copy() for run in runs_where_x_has_same_sign_as_xaxis]
                                elif yaxis.yaxis_mode == 'log':
                                    where_xy_have_same_sign_as_axes = np.where(np.logical_and(curve.data_x * self.xaxis_sign > 0., curve.data_y * yaxis.yaxis_sign > 0.))[0]
                                    runs_where_xy_have_same_sign_as_axes = np.split(where_xy_have_same_sign_as_axes, np.where(np.diff(where_xy_have_same_sign_as_axes) != 1)[0] + 1)
                                    curve.points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * curve.data_x[run]) for run in runs_where_xy_have_same_sign_as_axes]
                                    curve.points_y = [yaxis.yaxis_sign * np.log10(yaxis.yaxis_sign * curve.data_y[run]) for run in runs_where_xy_have_same_sign_as_axes]
                        if args[0][0] < args[0][1]:
                            self.xlim[0] = self.xaxis_sign * math.log10(self.xaxis_sign * args[0][0])
                            self.xlim[1] = self.xaxis_sign * math.log10(self.xaxis_sign * args[0][1])
                        else:
                            self.xlim[0] = self.xaxis_sign * math.log10(self.xaxis_sign * args[0][1])
                            self.xlim[1] = self.xaxis_sign * math.log10(self.xaxis_sign * args[0][0])
            elif len(args[0]) < 2:
                raise IndexError('did not specify both a lower and an upper limit for the x-axis')
            else:
                raise IndexError('more than two limits were specified for the x-axis')
        else:
            raise ValueError("invalid x-limits specification; it must be 'auto', 'tight', or a list of limits")
        self.refresh_plot()

    def ylimits(self, *args, **kwargs):
        yaxis = kwargs.get('yaxis', 'left')
        if yaxis not in self.yaxes.keys():
            raise ValueError("specified y-axis does not exist")

        if len(args) == 0:
            if self.yaxes[yaxis].yaxis_mode == 'linear':
                return [self.yaxes[yaxis].ylim[0], self.yaxes[yaxis].ylim[1]]
            elif self.yaxes[yaxis].yaxis_mode == 'log':
                return [self.yaxes[yaxis].yaxis_sign * math.pow(10., self.yaxes[yaxis].yaxis_sign * self.yaxes[yaxis].ylim[0]), self.yaxes[yaxis].yaxis_sign * math.pow(10., self.yaxes[yaxis].yaxis_sign * self.yaxes[yaxis].ylim[1])]
        elif args[0] in ('auto', 'tight'):
            self.yaxes[yaxis].ylimits_mode = args[0]
        elif type(args[0]) is list:
            if len(args[0]) == 2:
                args[0][0] = float(args[0][0])
                args[0][1] = float(args[0][1])
                if args[0][0] == args[0][1]:
                    raise ValueError('specified lower limit and upper limit were not distinct')
                else:
                    if self.yaxes[yaxis].yaxis_mode == 'linear':
                        self.yaxes[yaxis].ylimits_mode = 'manual'
                        if args[0][0] < args[0][1]:
                            self.yaxes[yaxis].ylim[0] = args[0][0]
                            self.yaxes[yaxis].ylim[1] = args[0][1]
                        else:
                            self.yaxes[yaxis].ylim[0] = args[0][1]
                            self.yaxes[yaxis].ylim[1] = args[0][0]
                    elif self.yaxes[yaxis].yaxis_mode == 'log':
                        if args[0][0] * args[0][1] < 0.:
                            raise ValueError('for a logarithmic axis, both limits must have the same sign')
                        if (args[0][0] * args[0][1] == 0.) or (args[0][0] * args[0][1] == -0.):
                            raise ValueError('for a logarithmic axis, neither limit can be zero')
                        self.yaxes[yaxis].ylimits_mode = 'manual'
                        if self.yaxes[yaxis].yaxis_sign * args[0][0] < 0.:
                            self.yaxes[yaxis].yaxis_sign = -self.yaxes[yaxis].yaxis_sign
                            if self.xaxis_mode == 'linear':
                                for curve_name in self.curves.keys():
                                    if self.curves[curve_name].yaxis == yaxis:
                                        where_y_has_same_sign_as_yaxis = np.where(self.curves[curve_name].data_y * self.yaxes[yaxis].yaxis_sign > 0.)[0]
                                        runs_where_y_has_same_sign_as_yaxis = np.split(where_y_has_same_sign_as_yaxis, np.where(np.diff(where_y_has_same_sign_as_yaxis) != 1)[0] + 1)
                                        self.curves[curve_name].points_x = [self.curves[curve_name].data_x[run].copy() for run in runs_where_y_has_same_sign_as_yaxis]
                                        self.curves[curve_name].points_y = [self.yaxes[yaxis].yaxis_sign * np.log10(self.yaxes[yaxis].yaxis_sign * self.curves[curve_name].data_y[run]) for run in runs_where_y_has_same_sign_as_yaxis]
                            elif self.xaxis_mode == 'log':
                                for curve_name in self.curves.keys():
                                    if self.curves[curve_name].yaxis == yaxis:
                                        where_xy_have_same_sign_as_axes = np.where(np.logical_and(self.curves[curve_name].data_x * self.xaxis_sign > 0., self.curves[curve_name].data_y * self.yaxes[yaxis].yaxis_sign > 0.))[0]
                                        runs_where_xy_have_same_sign_as_axes = np.split(where_xy_have_same_sign_as_axes, np.where(np.diff(where_xy_have_same_sign_as_axes) != 1)[0] + 1)
                                        self.curves[curve_name].points_x = [self.xaxis_sign * np.log10(self.xaxis_sign * self.curves[curve_name].data_x[run]) for run in runs_where_xy_have_same_sign_as_axes]
                                        self.curves[curve_name].points_y = [self.yaxes[yaxis].yaxis_sign * np.log10(self.yaxes[yaxis].yaxis_sign * self.curves[curve_name].data_y[run]) for run in runs_where_xy_have_same_sign_as_axes]
                        if args[0][0] < args[0][1]:
                            self.yaxes[yaxis].ylim[0] = self.yaxes[yaxis].yaxis_sign * math.log10(self.yaxes[yaxis].yaxis_sign * args[0][0])
                            self.yaxes[yaxis].ylim[1] = self.yaxes[yaxis].yaxis_sign * math.log10(self.yaxes[yaxis].yaxis_sign * args[0][1])
                        else:
                            self.yaxes[yaxis].ylim[0] = self.yaxes[yaxis].yaxis_sign * math.log10(self.yaxes[yaxis].yaxis_sign * args[0][1])
                            self.yaxes[yaxis].ylim[1] = self.yaxes[yaxis].yaxis_sign * math.log10(self.yaxes[yaxis].yaxis_sign * args[0][0])
            elif len(args[0]) < 2:
                raise IndexError('did not specify both a lower and an upper limit for the y-axis')
            else:
                raise IndexError('more than two limits were specified for the y-axis')
        else:
            raise ValueError("invalid y-limits specification; it must be 'auto', 'tight', or a list of limits")
        self.refresh_plot()

    def zoom_to_fit(self, **kwargs):
        mode = kwargs.get('mode', 'auto')
        if mode not in ('auto', 'tight'):
            raise ValueError("if specified, mode must be 'auto' or 'tight'")

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        self.xlimits_mode = mode

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                self.yaxes[yaxis].ylimits_mode = mode
        else:
            self.yaxes[yaxis].ylimits_mode = mode

        self.refresh_plot()

    def zoom_in(self, **kwargs):
        factor = kwargs.get('factor', math.sqrt(2))

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        cx = kwargs.get('cx', 0.5 * (self.axes_left + self.axes_right))
        cy = kwargs.get('cy', 0.5 * (self.axes_top + self.axes_bottom))

        x = self.from_canvas_x(cx)
        self.xlimits_mode = 'manual'
        self.xlim[0] = x - 0.5 * self.xrange / factor
        self.xlim[1] = x + 0.5 * self.xrange / factor

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                y = self.from_canvas_y(cy, yaxis)
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange / factor
                self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange / factor
        else:
            y = self.from_canvas_y(cy, yaxis)
            self.yaxes[yaxis].ylimits_mode = 'manual'
            self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange / factor
            self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange / factor

        self.refresh_plot()

    def zoom_in_x(self, **kwargs):
        factor = kwargs.get('factor', math.sqrt(2))

        cx = kwargs.get('cx', 0.5 * (self.axes_left + self.axes_right))

        x = self.from_canvas_x(cx)
        self.xlimits_mode = 'manual'
        self.xlim[0] = x - 0.5 * self.xrange / factor
        self.xlim[1] = x + 0.5 * self.xrange / factor

        self.refresh_plot()

    def zoom_in_y(self, **kwargs):
        factor = kwargs.get('factor', math.sqrt(2))

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        cy = kwargs.get('cy', 0.5 * (self.axes_top + self.axes_bottom))

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                y = self.from_canvas_y(cy, yaxis)
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange / factor
                self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange / factor
        else:
            y = self.from_canvas_y(cy, yaxis)
            self.yaxes[yaxis].ylimits_mode = 'manual'
            self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange / factor
            self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange / factor

        self.refresh_plot()

    def zoom_out(self, **kwargs):
        factor = kwargs.get('factor', math.sqrt(2))

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        cx = kwargs.get('cx', 0.5 * (self.axes_left + self.axes_right))
        cy = kwargs.get('cy', 0.5 * (self.axes_top + self.axes_bottom))

        x = self.from_canvas_x(cx)
        self.xlimits_mode = 'manual'
        self.xlim[0] = x - 0.5 * self.xrange * factor
        self.xlim[1] = x + 0.5 * self.xrange * factor

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                y = self.from_canvas_y(cy, yaxis)
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange * factor
                self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange * factor
        else:
            y = self.from_canvas_y(cy, yaxis)
            self.yaxes[yaxis].ylimits_mode = 'manual'
            self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange * factor
            self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange * factor

        self.refresh_plot()

    def zoom_out_x(self, **kwargs):
        factor = kwargs.get('factor', math.sqrt(2))

        cx = kwargs.get('cx', 0.5 * (self.axes_left + self.axes_right))

        x = self.from_canvas_x(cx)
        self.xlimits_mode = 'manual'
        self.xlim[0] = x - 0.5 * self.xrange * factor
        self.xlim[1] = x + 0.5 * self.xrange * factor

        self.refresh_plot()

    def zoom_out_y(self, **kwargs):
        factor = kwargs.get('factor', math.sqrt(2))

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        cy = kwargs.get('cy', 0.5 * (self.axes_top + self.axes_bottom))

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                y = self.from_canvas_y(cy, yaxis)
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange * factor
                self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange * factor
        else:
            y = self.from_canvas_y(cy, yaxis)
            self.yaxes[yaxis].ylimits_mode = 'manual'
            self.yaxes[yaxis].ylim[0] = y - 0.5 * self.yaxes[yaxis].yrange * factor
            self.yaxes[yaxis].ylim[1] = y + 0.5 * self.yaxes[yaxis].yrange * factor

        self.refresh_plot()

    def zoom_rect(self, *args, **kwargs):
        left = kwargs.get('left', self.axes_left)
        right = kwargs.get('right', self.axes_right)
        top = kwargs.get('top', self.axes_top)
        bottom = kwargs.get('bottom', self.axes_bottom)

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        if len(args) == 1:
            if (type(args[0]) is list) and (len(args[0]) == 4):
                left = float(args[0][0])
                right = float(args[0][2])
                top = float(args[0][1])
                bottom = float(args[0][3])
            else:
                raise ValueError('if specified, the optional argument must be a four-element list specifying the left, top, right, and bottom coordinates of the zoom rectangle')
        elif len(args) > 1:
            raise IndexError('too many arguments supplied to zoom_rect')

        if (left < right) and (top < bottom):
            self.xlimits_mode = 'manual'
            self.xlim[0], self.xlim[1] = self.from_canvas_x(left), self.from_canvas_x(right)

            if yaxis == 'all':
                for yaxis in self.yaxes.keys():
                    self.yaxes[yaxis].ylimits_mode = 'manual'
                    self.yaxes[yaxis].ylim[0], self.yaxes[yaxis].ylim[1] = self.from_canvas_y(bottom, yaxis), self.from_canvas_y(top, yaxis)
            else:
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0], self.yaxes[yaxis].ylim[1] = self.from_canvas_y(bottom, yaxis), self.from_canvas_y(top, yaxis)

            self.refresh_plot()

    def zoom_touch(self, old_p1, new_p1, old_p2, new_p2, **kwargs):
        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        self.xlimits_mode = 'manual'
        x1 = self.from_canvas_x(old_p1[0])
        if (abs(old_p1[0] - old_p2[0]) > 20) and (abs(new_p1[0] - new_p2[0]) > 20):
            xfactor = (new_p1[0] - new_p2[0]) / (old_p1[0] - old_p2[0])
            self.xlim[0] = x1 - (new_p1[0] - self.axes_left) / (self.x_pix_per_unit * xfactor)
            self.xlim[1] = x1 - (new_p1[0] - self.axes_right) / (self.x_pix_per_unit * xfactor)

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                y1 = self.from_canvas_y(old_p1[1], yaxis)
                self.yaxes[yaxis].ylimits_mode = 'manual'
                if (abs(old_p1[1] - old_p2[1]) > 20) and (abs(new_p1[1] - new_p2[1]) > 20):
                    yfactor = (new_p1[1] - new_p2[1]) / (old_p1[1] - old_p2[1])
                    self.yaxes[yaxis].ylim[0] = y1 - (new_p1[1] - self.axes_bottom) / (self.yaxes[yaxis].y_pix_per_unit * yfactor)
                    self.yaxes[yaxis].ylim[1] = y1 - (new_p1[1] - self.axes_top) / (self.yaxes[yaxis].y_pix_per_unit * yfactor)
        else:
            y1 = self.from_canvas_y(old_p1[1], yaxis)
            self.yaxes[yaxis].ylimits_mode = 'manual'
            if (abs(old_p1[1] - old_p2[1]) > 20) and (abs(new_p1[1] - new_p2[1]) > 20):
                yfactor = (new_p1[1] - new_p2[1]) / (old_p1[1] - old_p2[1])
                self.yaxes[yaxis].ylim[0] = y1 - (new_p1[1] - self.axes_bottom) / (self.yaxes[yaxis].y_pix_per_unit * yfactor)
                self.yaxes[yaxis].ylim[1] = y1 - (new_p1[1] - self.axes_top) / (self.yaxes[yaxis].y_pix_per_unit * yfactor)

        self.refresh_plot()

    def pan_left(self, **kwargs):
        fraction = kwargs.get('fraction', 0.1)

        self.xlimits_mode = 'manual'
        self.xlim[0] -= fraction * self.xrange
        self.xlim[1] -= fraction * self.xrange

        self.refresh_plot()

    def pan_right(self, **kwargs):
        fraction = kwargs.get('fraction', 0.1)

        self.xlimits_mode = 'manual'
        self.xlim[0] += fraction * self.xrange
        self.xlim[1] += fraction * self.xrange

        self.refresh_plot()

    def pan_up(self, **kwargs):
        fraction = kwargs.get('fraction', 0.1)

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0] += fraction * self.yaxes[yaxis].yrange
                self.yaxes[yaxis].ylim[1] += fraction * self.yaxes[yaxis].yrange
        else:
            self.yaxes[yaxis].ylimits_mode = 'manual'
            self.yaxes[yaxis].ylim[0] += fraction * self.yaxes[yaxis].yrange
            self.yaxes[yaxis].ylim[1] += fraction * self.yaxes[yaxis].yrange

        self.refresh_plot()

    def pan_down(self, **kwargs):
        fraction = kwargs.get('fraction', 0.1)

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        if yaxis == 'all':
            for yaxis in self.yaxes.keys():
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0] -= fraction * self.yaxes[yaxis].yrange
                self.yaxes[yaxis].ylim[1] -= fraction * self.yaxes[yaxis].yrange
        else:
            self.yaxes[yaxis].ylimits_mode = 'manual'
            self.yaxes[yaxis].ylim[0] -= fraction * self.yaxes[yaxis].yrange
            self.yaxes[yaxis].ylim[1] -= fraction * self.yaxes[yaxis].yrange

        self.refresh_plot()

    def pan(self, **kwargs):
        dx = kwargs.get('dx', 0.)
        dy = kwargs.get('dy', 0.)

        yaxis = kwargs.get('yaxis', 'all')
        if (yaxis != 'all') and (yaxis not in self.yaxes.keys()):
            raise ValueError('specified y-axis does not exist')

        if (dx != 0.) or (dy != 0.):
            self.xlimits_mode = 'manual'
            self.xlim[0] -= dx * self.x_epsilon
            self.xlim[1] -= dx * self.x_epsilon

            if yaxis == 'all':
                for yaxis in self.yaxes.keys():
                    self.yaxes[yaxis].ylimits_mode = 'manual'
                    self.yaxes[yaxis].ylim[0] -= dy * self.yaxes[yaxis].y_epsilon
                    self.yaxes[yaxis].ylim[1] -= dy * self.yaxes[yaxis].y_epsilon
            else:
                self.yaxes[yaxis].ylimits_mode = 'manual'
                self.yaxes[yaxis].ylim[0] -= dy * self.yaxes[yaxis].y_epsilon
                self.yaxes[yaxis].ylim[1] -= dy * self.yaxes[yaxis].y_epsilon

            self.refresh_plot()

    def delete_curve(self, name):
        if name in self.curves.keys():
            del(self.curves[name])
        else:
            raise NameError('no curve exists with name = {0!r}'.format(name))

        self.refresh_plot()

    def configure_curve(self, name, **kwargs):
        style = kwargs.get('style', '')

        if name in self.curves.keys():
            marker_color = kwargs.get('marker_color', self.curves[name].marker_color)
            marker = kwargs.get('marker', self.curves[name].marker)
            curve_color = kwargs.get('curve_color', self.curves[name].curve_color)
            curve_style = kwargs.get('curve_style', self.curves[name].curve_style)
            if style == '':
                self.curves[name].marker_color = marker_color
                self.curves[name].marker = marker
                self.curves[name].curve_color = curve_color
                self.curves[name].curve_style = curve_style
            else:
                [self.curves[name].marker_color, self.curves[name].marker, self.curves[name].curve_color, self.curves[name].curve_style] = self.parse_style(style)
        else:
            raise NameError('no curve exists with name = {0!r}'.format(name))

        self.refresh_plot()

    def on_touch_down(self, touch):
        if touch.is_double_tap:
            self.looking_for_gesture = False
            if (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top):
                self.zoom_to_fit()
            elif (touch.pos[0] >= self.axes_left) and (touch.pos[0] <= self.axes_right) and (touch.pos[1] >= self.canvas_bottom) and (touch.pos[1] < self.axes_bottom):
                self.xaxis('log') if self.xaxis() == 'linear' else self.xaxis('linear')
            elif (touch.pos[0] >= self.canvas_left) and (touch.pos[0] < self.axes_left) and (touch.pos[1] >= self.axes_bottom) and (touch.pos[1] <= self.axes_top):
                self.yaxis('log') if self.yaxis() == 'linear' else self.yaxis('linear')
        self.num_touches += 1
        self.touch_net_movements.append([0., 0.])
        self.touch_positions.append(touch.pos)

    def on_touch_move(self, touch):
        sqr_distances = [(touch.pos[0] - pos[0]) ** 2 + (touch.pos[1] - pos[1]) ** 2 for pos in self.touch_positions]
        try:
            i = min(enumerate(sqr_distances), key = lambda x: x[1])[0]
        except ValueError:
            return
        self.touch_net_movements[i][0] += touch.pos[0] - self.touch_positions[i][0]
        self.touch_net_movements[i][1] += touch.pos[1] - self.touch_positions[i][1]
        self.touch_positions[i] = touch.pos

    def on_touch_up(self, touch):
        if self.looking_for_gesture:
            if self.num_touches == 1:
                r = math.hypot(self.touch_net_movements[0][0], self.touch_net_movements[0][1])
                if r >= self.MOTION_THRESHOLD:
                    angle = 180. * math.atan2(self.touch_net_movements[0][1], self.touch_net_movements[0][0]) / math.pi
                    i = int((angle + 180.) / 22.5)
                    if self.swipe_dirs[i] == 'N':
                        self.pan_down()
                    elif self.swipe_dirs[i] == 'NE':
                        self.pan_down()
                        self.pan_left()
                    elif self.swipe_dirs[i] == 'E':
                        self.pan_left()
                    elif self.swipe_dirs[i] == 'SE':
                        self.pan_up()
                        self.pan_left()
                    elif self.swipe_dirs[i] == 'S':
                        self.pan_up()
                    elif self.swipe_dirs[i] == 'SW':
                        self.pan_up()
                        self.pan_right()
                    elif self.swipe_dirs[i] == 'W':
                        self.pan_right()
                    elif self.swipe_dirs[i] == 'NW':
                        self.pan_down()
                        self.pan_right()
            elif self.num_touches == 2:
                r1 = math.hypot(self.touch_net_movements[0][0], self.touch_net_movements[0][1])
                r2 = math.hypot(self.touch_net_movements[1][0], self.touch_net_movements[1][1])
                if (r1 >= self.MOTION_THRESHOLD) and (r2 >= self.MOTION_THRESHOLD):
                    dx = self.touch_positions[1][0] - self.touch_positions[0][0]
                    dy = self.touch_positions[1][1] - self.touch_positions[0][1]
                    r = math.hypot(dx, dy)
                    c1 = (dx * self.touch_net_movements[0][0] + dy * self.touch_net_movements[0][1]) / (r * r1)
                    c2 = (dx * self.touch_net_movements[1][0] + dy * self.touch_net_movements[1][1]) / (r * r2)
                    angle = 180. * math.atan2(dy, dx) / math.pi
                    i = int((angle + 180.) / 22.5)
                    if (c1 > self.ANGLE_THRESHOLD) and (c2 < -self.ANGLE_THRESHOLD):
                        if self.pinch_dirs[i] == 'E-W':
                            self.zoom_out_x()
                        elif self.pinch_dirs[i] == 'N-S':
                            self.zoom_out_y()
                        elif self.pinch_dirs[i] in ('NE-SW', 'NW-SE'):
                            self.zoom_out()
                    elif (c1 < -self.ANGLE_THRESHOLD) and (c2 > self.ANGLE_THRESHOLD):
                        if self.pinch_dirs[i] == 'E-W':
                            self.zoom_in_x()
                        elif self.pinch_dirs[i] == 'N-S':
                            self.zoom_in_y()
                        elif self.pinch_dirs[i] in ('NE-SW', 'NW-SE'):
                            self.zoom_in()
            self.looking_for_gesture = False

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

