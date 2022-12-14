import numpy as np
from bokeh.models import ColumnDataSource, Range1d, Text, Circle
from bokeh.plotting import figure

from PIL import Image
from requests import get
from io import BytesIO


class Needle():
    def __init__(self, fig, x0, y0, start_angle, end_angle, min_value, max_value, needle_lenght: float = 0.9,
                 inner_needle_lenght: float = 0.6, initial_value: float = 0, line_width: int = 4,
                 inner_line_width: int = 8, line_color: str = "black"):

        self.fig = fig
        self.x0 = x0
        self.y0 = y0
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.min_value = min_value
        self.max_value = max_value
        self.needle_lenght = needle_lenght
        self.inner_needle_lenght = inner_needle_lenght
        self.value = initial_value
        self.with_indicator = False
        self.text_format = None
        self.x_text = None
        self.y_text = None
        self.needle_source = ColumnDataSource(data=dict())
        self.indicator_source = ColumnDataSource(data=dict())
        self.set_needle_value(self.value)
        self.fig.line(x="x", y="y", source=self.needle_source, line_width=line_width,
                      line_color=line_color)

        self.fig.line(x="x_inner", y="y_inner", source=self.needle_source, line_width=inner_line_width,
                      line_color=line_color)


    def add_indicator(self, radius: float = 0.5, angle: float = -np.pi / 2, text_angle: float = 0,
                      initial_value: float = 0, round_nb: int = 0, unit: str = "", indicator_color: str = "black",
                      text_size: int = 40):
        self.with_indicator = True
        self.text_format = self.set_text_format(round_nb=round_nb, unit=unit)
        self.value = initial_value
        self.set_text_position(angle=angle, length=radius)
        self.set_needle_value(self.value)

        glyph = Text(x="x_text", y="y_text", text="text", text_color=indicator_color, text_align="center",
                     text_baseline="middle", text_font_size=str(text_size) + "px", angle=text_angle)
        self.fig.add_glyph(self.indicator_source, glyph)

    def get_angle(self, value: float):
        return self.start_angle + (self.end_angle - self.start_angle) * \
               (max(self.min_value, min(self.max_value, value)) - self.min_value) / \
               (self.max_value - self.min_value)

    def get_position(self, value: float, length: float = 1):
        angle = self.get_angle(value=value)
        return self.x0 + length * np.cos(angle), self.y0 + length * np.sin(angle)

    def set_text_position(self, angle: float, length: float):
        self.x_text = [self.x0 + length * np.cos(angle)]
        self.y_text = [self.y0 + length * np.sin(angle)]

    def set_text_format(self, round_nb: int = 0, unit: str = ""):
        return "{:." + str(round_nb) + "f}" + unit

    def set_needle_value(self, value):
        self.value = value
        position = self.get_position(self.value, self.needle_lenght)
        inner_position = self.get_position(self.value, self.inner_needle_lenght)
        self.needle_source.data = {"x": [self.x0, position[0]],
                                   "y": [self.y0, position[1]],
                                   "x_inner": [self.x0, inner_position[0]],
                                   "y_inner": [self.y0, inner_position[1]]}
        if self.with_indicator:
            self.indicator_source.data = {"x_text": self.x_text,
                                          "y_text": self.y_text,
                                          "text": [self.text_format.format(self.value)]}


class Gauge():
    def __init__(self, fig, pixcel_factor, x0: float = 0, y0: float = 0, r: float = 1, start_angle: float = np.pi,
                 end_angle: float = 0, min_value: float = 0, max_value: float = 100, direction: str = 'clock'):

        self.fig = fig
        self.pixcel_factor = pixcel_factor
        self.x0 = x0
        self.y0 = y0
        self.r = r

        self.min_value = min_value
        self.max_value = max_value
        self.start_angle = start_angle

        self.end_angle = end_angle
        self.direction = direction
        self.needles = []
        self.text_format = None

    def add_circle(self, circle_radius: float = None, line_color: str = "black", line_width: int = 2):
        if circle_radius is None:
            circle_radius = self.r

        self.fig.arc(x=self.x0, y=self.y0, radius=circle_radius, start_angle=self.start_angle,
                     end_angle=self.end_angle, direction=self.direction, line_color=line_color,
                     line_width=line_width)

    def add_annular(self, values: list[tuple], colors: list[str], inner_radius: float = 0.7,
                    outer_radius: float = None, fill_alpha: float = 1, limited: bool = True):
        if outer_radius is None:
            outer_radius = self.r
        for value, color in zip(values, colors):
            first_angle = self.get_angle(value=value[0], limited=limited)
            second_angle = self.get_angle(value=value[1], limited=limited)
            self.fig.annular_wedge(x=self.x0, y=self.y0, inner_radius=inner_radius, outer_radius=outer_radius,
                                   start_angle=first_angle, end_angle=second_angle, color=color,
                                   alpha=fill_alpha, direction=self.direction)

    def add_ticks(self, tick_nb: int = 10, sub_tick_nb: int = 2, outer_radius: float = None,
                  tick_length: float = 0.2, sub_tick_length: float = None, tick_width: int = 2,
                  sub_tick_width: int = 2, tick_color: str = "black"):
        if outer_radius is None:
            outer_radius = self.r
        if sub_tick_length is None:
            sub_tick_length = tick_length / 2

        for tick_index, tick_value in enumerate(np.linspace(self.min_value, self.max_value,
                                                            (tick_nb * sub_tick_nb) + 1)):
            if tick_index % sub_tick_nb == 0:
                actual_tick_length = tick_length
                actual_tick_width = tick_width
            else:
                actual_tick_length = sub_tick_length
                actual_tick_width = sub_tick_width

            tick_position = [self.get_position(tick_value, length=outer_radius),
                             self.get_position(tick_value, length=outer_radius - actual_tick_length)]
            self.fig.line(x=[tick_position[0][0], tick_position[1][0]],
                          y=[tick_position[0][1], tick_position[1][1]],
                          line_width=actual_tick_width, line_color=tick_color)

    def add_ticks_label(self, label_nb: int = 5, label_radius: float = 0.7, round_nb: int = 0,
                        unit: str = "", label_color: str = "black", label_size: int = 20, label_values: list = None):

        if label_values is None:
            label_values = np.linspace(self.min_value, self.max_value, label_nb + 1)

        for label_value in label_values:
            label_position = self.get_position(label_value, length=label_radius)
            text_value = self.set_text_format(round_nb=round_nb, unit=unit).format(label_value)
            self.fig.text(x=[label_position[0]], y=[label_position[1]], text=[text_value],
                          text_align="center", text_baseline="middle", text_color=label_color,
                          text_font_size=str(label_size) + "px")

    def add_inner_circle(self, r: float = 0.1, fill_color: str = "black", line_color:
                         str = "black", line_width: int = 2):

        self.fig.circle(x=self.x0, y=self.y0, size=int(2*r*self.pixcel_factor), fill_color=fill_color, line_color=line_color,
                        line_width=line_width)

    def add_custom_tick(self, tick_value, outer_radius: float = None, tick_length: float = 0.3,  tick_width: int = 8,
                        tick_color: str = "red"):
        if outer_radius is None:
            outer_radius = self.r
        tick_position = [self.get_position(tick_value, length=outer_radius),
                         self.get_position(tick_value, length=outer_radius - tick_length)]
        self.fig.line(x=[tick_position[0][0], tick_position[1][0]],
                      y=[tick_position[0][1], tick_position[1][1]],
                      line_width=tick_width, line_color=tick_color)


    def add_label(self, label, r: float = 0.3, angle: float = None, text_color: str = "black", text_size: int = 20,
                  text_align: str = "center", text_baseline: str = "middle"):
        if angle is None:
            angle = self.get_angle((self.max_value-self.min_value)/2)
        self.fig.text(x=[self.x0 + r * np.cos(angle)], y=[self.y0 + r * np.sin(angle)], text=[label],
                      text_align=text_align, text_baseline=text_baseline,
                      text_color=text_color, text_font_size=str(text_size) + "px")

    def add_needle(self, needle_name: str, needle_lenght: float = 0.9, initial_value: float = 0,
                   line_width: int = 4, needle_color: str = "black", inner_needle_lenght: float = 0.6,
                   inner_line_width: float = 8):
        needle = Needle(fig=self.fig, x0=self.x0, y0=self.y0, start_angle=self.start_angle,
                        end_angle=self.end_angle, min_value=self.min_value, max_value=self.max_value,
                        needle_lenght=needle_lenght, initial_value=initial_value,
                        line_width=line_width, line_color=needle_color, inner_line_width=inner_line_width,
                        inner_needle_lenght=inner_needle_lenght)
        self.needles.append(needle)
        setattr(self, needle_name, needle)

    def get_needle(self, needle_name) -> Needle:
        return getattr(self, needle_name)

    def set_value(self, new_values: list[float]):
        if len(new_values) == len(self.needles):
            for new_value, needle in zip(new_values, self.needles):
                if needle.value != new_value:
                    needle.set_needle_value(new_value)

    def set_text_format(self, round_nb: int = 0, unit: str = ""):
        return "{:." + str(round_nb) + "f}" + unit

    def get_angle(self, value: float, limited: bool = True):
        if limited:
            return self.start_angle + (self.end_angle - self.start_angle) * \
                   (max(self.min_value, min(self.max_value, value)) - self.min_value) / \
                   (self.max_value - self.min_value)
        else:
            return self.start_angle + (self.end_angle - self.start_angle) * \
                   (value - self.min_value) / (self.max_value - self.min_value)

    def get_position(self, value: float, length: float = 1):
        angle = self.get_angle(value=value)
        return self.x0 + length * np.cos(angle), self.y0 + length * np.sin(angle)


class Boolean():
    def __init__(self, fig, x0: float = 0, y0: float = 0, true_color: str = "green", false_color: str = "gray",
                 true_alpha: float = 1, false_alpha: float = 1, initial_value: bool = False, size: int = 30,
                 line_color: str = "black", line_width: str = 2):

        self.fig = fig
        self.x0 = x0
        self.y0 = y0
        self.initial_value = initial_value
        self.false_alpha = false_alpha
        self.true_alpha = true_alpha
        self.false_color = false_color
        self.true_color = true_color
        self.value = None
        self.boolean_source = ColumnDataSource(data=dict())
        self.set_value(initial_value)
        glyph = Circle(x="x", y="y", size=size, fill_alpha="alpha", fill_color="color",
                       line_width=line_width, line_color=line_color)
        self.fig.add_glyph(self.boolean_source, glyph)

    def set_value(self, new_value: float):
        if self.value != new_value:
            self.value = new_value
            if self.value:
                self.boolean_source.data = {"x": [self.x0], "y": [self.y0],
                                            "alpha": [self.true_alpha],
                                            "color": [self.true_color]}
            else:
                self.boolean_source.data = {"x": [self.x0], "y": [self.y0],
                                            "alpha": [self.false_alpha],
                                            "color": [self.false_color]}

    def add_label(self, label, x: float = 0, y: float = 0, text_color: str = "black", text_size: int = 20,
                  text_align: str = "left", text_baseline: str = "middle"):

        self.fig.text(x=[x + self.x0], y=[y + self.y0], text=[label], text_align=text_align, text_baseline=text_baseline,
                      text_color=text_color, text_font_size=str(text_size) + "px")


class Enum():
    def __init__(self, fig, x0: float = 0, y0: float = 0, colors=None,
                 initial_value: int = 0, size: int = 30, line_color: str = "saddlebrown", line_width: int = 2):

        self.fig = fig
        self.x0 = x0
        self.y0 = y0
        if colors is None:
            self.colors = ["gray", "green", "gold", "red"]
        else:
            self.colors = colors
        self.value = None
        self.enum_source = ColumnDataSource(data=dict())
        self.set_value(initial_value)
        glyph = Circle(x="x", y="y", size=size, fill_alpha=1, fill_color="color",
                       line_width=line_width, line_color=line_color)
        self.fig.add_glyph(self.enum_source, glyph)

    def set_value(self, new_value: float):
        if self.value != new_value:
            self.value = new_value
            if (self.value >= 0) & (self.value < len(self.colors)):
                self.enum_source.data = {"x": [self.x0], "y": [self.y0],
                                            "color": [self.colors[self.value]]}
            else:
                self.enum_source.data = {"x": [self.x0], "y": [self.y0],
                                            "color": [self.colors[0]]}

    def add_label(self, label, x: float = 0, y: float = 0, text_color: str = "black", text_size: int = 20,
                  text_align: str = "left", text_baseline: str = "middle"):

        self.fig.text(x=[x + self.x0], y=[y + self.y0], text=[label], text_align=text_align, text_baseline=text_baseline,
                      text_color=text_color, text_font_size=str(text_size) + "px")

class Counter():
    def __init__(self, fig, x0: float = 0, y0: float = 0, digit_nb: int = 5, decimal_nb: int = 1, unit: str = "",
                 initial_value: int = 0, text_size: int = 30, text_color: str = "black", text_align="center",
                 text_baseline="middle"):

        self.fig = fig
        self.x = x0
        self.y = y0
        self.digit_nb = digit_nb
        self.decimal_nb = decimal_nb
        self.unit = unit
        self.value = None
        self.counter_source = ColumnDataSource(data=dict())
        self.set_value(initial_value)
        glyph = Text(x="x_text", y="y_text", text="text", text_color=text_color, text_align=text_align,
                     text_baseline=text_baseline, text_font_size=str(text_size) + "px")
        self.fig.add_glyph(self.counter_source, glyph)

    def set_value(self, value):
        if value != self.value:
            self.value = value
            if self.decimal_nb != 0:
                dig, dec = str(min(max(0.0, round(float(self.value), self.decimal_nb)),
                                       (10**(self.digit_nb+self.decimal_nb)-1)/(10**self.decimal_nb))).split(".")
                text = "0"*(self.digit_nb-len(dig)) + dig + "." \
                       + dec + "0"*(self.decimal_nb-len(dec)) + self.unit
            else:
                dig = str(min(max(0, int(self.value)), 10**self.digit_nb-1))
                text = "0" * (self.digit_nb - self.decimal_nb - len(dig)) + dig + self.unit

            self.counter_source.data = {"x_text": [self.x],
                                        "y_text": [self.y],
                                        "text": [text]}

class Dashboard():

    def __init__(self, size: int = 400, background_fill: str = None,
                 x_lim: tuple = (-1.1, 1.1), y_lim: tuple = (-1.1, 1.1)):
        self.image_factor = (y_lim[1] - y_lim[0])/(x_lim[1] - x_lim[0])
        self.pixcel_factor = size/(x_lim[1] - x_lim[0])
        self.fig = figure(title=None, toolbar_location=None, match_aspect=True, width=size,
                          height=int(size*self.image_factor))
        self.fig.background_fill_color = background_fill
        self.fig.axis.visible = False
        self.fig.grid.visible = False
        self.fig.min_border = 0
        self.fig.toolbar.active_drag = None
        self.fig.outline_line_color = None
        self.fig.x_range = Range1d(*x_lim)
        self.fig.y_range = Range1d(*y_lim)

    def set_text_format(self, round_nb: int = 0, unit: str = ""):
        return "{:." + str(round_nb) + "f}" + unit

    def add_gauge(self, gauge_name: str,  x0: float = 0, y0: float = 0, r: float = 1, start_angle: float = np.pi,
                  end_angle: float = 0, min_value: float = 0, max_value: float = 100, clockwise: bool = True,
                  with_background: bool = False, background_color: str = "black", background_r: float = 1.2,
                  background_line_width: float = 5, background_line_color: str = "saddlebrown", background_x: float = 0,
                  background_y: float = 0):
        if clockwise:
            direction = "clock"
        else:
            direction = "anticlock"
        if with_background:
            self.fig.circle(x=x0+background_x, y=y0+background_y, size=int(2*background_r*self.pixcel_factor),
                            fill_color=background_color, line_color=background_line_color,
                            line_width=background_line_width)

        gauge = Gauge(fig=self.fig, pixcel_factor=self.pixcel_factor, x0=x0, y0=y0, r=r, start_angle=start_angle,
                      end_angle=end_angle, min_value=min_value, max_value=max_value, direction=direction)
        setattr(self, gauge_name, gauge)

    def add_booolean(self, boolean_name: str, x0: float = 0, y0: float = 0, true_color: str = "lightgreen",
                                false_color: str = "gray", true_alpha: float = 1, false_alpha: float = 0.5,
                                initial_value: bool = False, size: int = 30, line_color: str = "black",
                                line_width: str = 2):

        boolean = Boolean(fig=self.fig, x0=x0, y0=y0, true_color=true_color, false_color=false_color,
                           true_alpha=true_alpha, false_alpha=false_alpha, initial_value=initial_value, size=size,
                           line_color=line_color, line_width=line_width)
        setattr(self, boolean_name, boolean)

    def add_enum(self, enum_name: str, x0: float = 0, y0: float = 0, colors: list = None,
                 initial_value: bool = False, r: int = 0.2, line_color: str = "saddlebrown",
                 line_width: int = 3):
        size = int(2*r*self.pixcel_factor)
        enum = Enum(fig=self.fig, x0=x0, y0=y0, colors=colors, initial_value=initial_value, size=size,
                       line_color=line_color, line_width=line_width)
        setattr(self, enum_name, enum)

    def add_counter(self, counter_name, x: float = 0, y: float = 0, digit_nb: int = 4, decimal_nb: int = 1,
                    unit: str = "", initial_value: int = 0, text_size: int = 30, text_color: str = "black",
                    text_align: str = "center", text_baseline: str = "middle"):

        counter = Counter(fig=self.fig, x0=x, y0=y, digit_nb=digit_nb, decimal_nb=decimal_nb, unit=unit,
                          initial_value=initial_value, text_size=text_size, text_color=text_color,
                          text_align=text_align, text_baseline=text_baseline)
        setattr(self, counter_name, counter)

    def add_background(self, x0: float, y0: float, height: float, width: float, angle_r: float = 0.2,
                       fill_color:str = None, line_color: str = "saddlebrown", line_width: int = 5):
        if fill_color is not None:
            self.fig.circle(x=[x0 + angle_r, x0 + width - angle_r, x0 + angle_r, x0 + width - angle_r],
                            y=[y0 + angle_r, y0 + angle_r, y0 + height - angle_r, y0 + height - angle_r],
                            size=int(2 * angle_r * self.pixcel_factor), fill_color=fill_color)
            self.fig.rect(x=x0 + width / 2, y=y0 + height / 2, width=width - 2 * angle_r, height=height,
                          color=fill_color)
            self.fig.rect(x=x0 + width / 2, y=y0 + height / 2, width=width, height=height - 2 * angle_r,
                          color=fill_color)

        self.fig.segment(x0=x0 + angle_r - 1 / self.pixcel_factor, x1=x0 + width - angle_r + 1 / self.pixcel_factor,
                         y0=y0, y1=y0, line_color=line_color, line_width=line_width)
        self.fig.segment(x0=x0 + angle_r - 1 / self.pixcel_factor, x1=x0 + width - angle_r + 1 / self.pixcel_factor,
                         y0=y0 + height, y1=y0 + height, line_color=line_color, line_width=line_width)
        self.fig.segment(x0=x0, x1=x0, y0=y0 + angle_r - 1 / self.pixcel_factor,
                         y1=y0 + height - angle_r + 1 / self.pixcel_factor, line_color=line_color,
                         line_width=line_width)
        self.fig.segment(x0=x0 + width, x1=x0 + width, y0=y0 + angle_r - 1 / self.pixcel_factor,
                         y1=y0 + height - angle_r + 1 / self.pixcel_factor, line_color=line_color,
                         line_width=line_width)

        self.fig.arc(x=x0+angle_r, y=y0+angle_r, radius=angle_r, start_angle=np.pi,
                     end_angle=3*np.pi/2, line_color=line_color, line_width=line_width)
        self.fig.arc(x=x0+width-angle_r, y=y0+angle_r, radius=angle_r, start_angle=3*np.pi/2,
                     end_angle=0, line_color=line_color, line_width=line_width)
        self.fig.arc(x=x0+width-angle_r, y=y0+height-angle_r, radius=angle_r, start_angle=0,
                     end_angle=np.pi/2, line_color=line_color, line_width=line_width)
        self.fig.arc(x=x0+angle_r, y=y0+height-angle_r, radius=angle_r, start_angle=np.pi/2,
                     end_angle=np.pi, line_color=line_color, line_width=line_width)

    def add_label(self, label, x: float = 0, y: float = 0, text_color: str = "black", text_size: int = 20,
                  text_align: str = "left", text_baseline: str = "middle"):

        self.fig.text(x=[x], y=[y], text=[label], text_align=text_align, text_baseline=text_baseline,
                      text_color=text_color, text_font_size=str(text_size) + "px")

    # def add_image(self, img_path, x0, y0, size):
    #     picture = Image.open(img_path)
    #     # picture.show()
    #     width, height = picture.size  # 1024 352
    #     # self.fig.image(image=[img_path], x=x0, y=y0, dw=size, dh=size*height/width)

    #     # imgArray = np.array(picture)
    #     # self.fig.image([imgArray], x=x0, y=y0, dw=size, dh=size*height/width)

    #     fileurl = str('file://') + img_path
    #     # self.fig.image_url(url=[img_path], x=x0, y=y0, w=size, h=size*height/width)
    #     self.fig.image_url(url=[fileurl], x=x0, y=y0, w=size, h=size*height/width)

    def add_image(self, img_path, x0, y0, size):
        image_raw = get(img_path)
        image = Image.open(BytesIO(image_raw.content))
        width, height = image.size
        self.fig.image_url(url=[img_path], x=x0, y=y0, w=size, h=size*height/width)

    def set_values(self, new_values: dict):
        for name, new_value in new_values.items():
            getattr(self, name).set_value(new_value)

    def get_gauge(self, gauge_name: str) -> Gauge:
        return getattr(self, gauge_name)

    def get_boolean(self, gauge_name: str) -> Boolean:
        return getattr(self, gauge_name)

    def get_enum(self, enum_name: str) -> Enum:
        return getattr(self, enum_name)

    def get_counter(self, counter_name: str) -> Counter:
        return getattr(self, counter_name)

