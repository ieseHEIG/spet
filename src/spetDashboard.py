from customDashboard import *
from bokeh.plotting import output_file, show

# import os


def create_rpm_indicators(board, x0, y0, label_size= 22, text_size = 25, tick_width = 6,
                         tick_length=0.3, ):
    name = "rpm"
    board.add_gauge(name, x0=x0, y0=y0, min_value=5, max_value=30, start_angle=7 / 6 * np.pi, end_angle=-np.pi / 6,
                    with_background=True, r=1.6, background_r=1.8)


    board.get_gauge(name).add_annular(values=[(10, 20), (20, 25)], colors=["green", "gold"],
                                            inner_radius=1.55)
    board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=5, sub_tick_nb=5, tick_width=tick_width,
                                    tick_length=tick_length, sub_tick_length=0.15, sub_tick_width=3)
    board.get_gauge(name).add_custom_tick(tick_value=25, outer_radius=1.65, tick_length=0.4, tick_width=10)
    board.get_gauge(name).add_ticks_label(label_color="lightgray", label_nb=5, label_size=label_size,
                                          label_radius=1.1)

    board.get_gauge(name).add_label(text_color="lightgray", label="rpm\nx100", r=0.6, angle= np.pi/2, text_size=text_size)
    board.get_gauge(name).add_needle("neddle_1", needle_color="white", initial_value=18, needle_lenght=1.5,
                                     inner_needle_lenght=1, inner_line_width=10)
    board.get_gauge(name).add_inner_circle(r=0.35)

    board.add_counter("use_time", x=x0, y=y0-1, text_color="lightgray", unit="\nminutes")



def create_battery_indicators(board, x0, y0, ind_name, gauge_nb, label_size= 13, text_size = 16, tick_width = 4,
                              tick_length=0.15, label_radius=0.75):
    name = "soc_bat_" + str(gauge_nb)
    board.add_gauge(name, x0=x0, y0=y0, start_angle=31/24 * np.pi, end_angle=np.pi/2, with_background=True, background_r=1.15)
    board.get_gauge(name).add_label(angle=np.pi/2, r=1.3, text_size=30, text_color="black", label=ind_name)
    board.get_gauge(name).add_annular(values=[(0, 20), (20, 30), (30, 100)], colors=["red", "gold", "green"],
                                            inner_radius=0.95)
    board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=4, sub_tick_nb=5, tick_width=tick_width, tick_length=tick_length)
    board.get_gauge(name).add_ticks_label(label_color="lightgray", label_nb=4, label_size=label_size, label_radius=label_radius)
    board.get_gauge(name).add_label(text_color="lightgray", label="SOC\n[kWh]", r=0.45, angle=-5*np.pi/6, text_size=text_size)

    name = "power_bat_" + str(gauge_nb)
    board.add_gauge(name, x0=x0, y0=y0, start_angle=np.pi/24, end_angle=3*np.pi/8, clockwise=False,
                    min_value=-10, max_value=40)
    board.get_gauge(name).add_annular(values=[(-10, 20), (20, 25), (25, 40)], colors=["green", "gold", "red"],
                                             inner_radius=0.95)

    board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=5, tick_width=tick_width,tick_length=tick_length)
    board.get_gauge(name).add_ticks_label(label_color="lightgray", label_values=[-10, 0, 40], label_size=label_size, label_radius=label_radius)
    board.get_gauge(name).add_needle("neddle_1", needle_color="white", initial_value=10, inner_needle_lenght=0.7)
    board.get_gauge(name).add_annular(values=[(-20, 50)], colors=["black"],
                                               inner_radius=0.22, outer_radius=0.5, limited=False)
    board.get_gauge(name).add_label(text_color="lightgray", label="P [kW]", r=0.33, angle=4*np.pi/12,  text_size=text_size)
    name = "temp_bat_" + str(gauge_nb)
    board.add_gauge(name, x0=x0, y0=y0, start_angle=-7*np.pi/12, end_angle=-np.pi/12, clockwise=False,
                    min_value=0, max_value=60)
    board.get_gauge(name).add_annular(values=[(0, 10), (10, 55),  (45, 55), (55, 60)],
                                              colors=["gold", "green", "gold", "red"], inner_radius=0.95)

    board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=3, sub_tick_nb=4, tick_width=tick_width,tick_length=tick_length)
    board.get_gauge(name).add_ticks_label(label_color="lightgray", label_nb=3, label_size=label_size, label_radius=label_radius)
    board.get_gauge(name).add_label(text_color="lightgray", label="Temp\n[°C]", r=0.45, angle=-np.pi/6, text_size=text_size)

    board.get_gauge("soc_bat_" + str(gauge_nb)).add_needle("neddle_1", needle_color="white", initial_value=50)
    board.get_gauge(name).add_needle("min", needle_color="lawngreen", initial_value=25)
    board.get_gauge(name).add_needle("mean", needle_color="white", initial_value=30)
    board.get_gauge(name).add_needle("max", needle_color="red", initial_value=33)
    board.get_gauge(name).add_inner_circle(r=0.22)


def create_drive_indicators(board, x0, y0, ind_name, nb, label_size=13, text_size=16, tick_width=4,
                            tick_length=0.15, label_radius=0.75):
    name = "temp_drive_" + str(nb)
    board.add_gauge(name, x0=x0, y0=y0, start_angle=4/3 * np.pi, end_angle=2/3 * np.pi, with_background=True, background_r=1.15)
    board.get_gauge(name).add_label(angle=np.pi / 2, r=1.3, text_size=30, text_color="black", label=ind_name)
    board.get_gauge(name).add_annular(values=[(0, 70), (70, 90), (90, 100)], colors=["green", "gold", "red"],
                                            inner_radius=0.95)
    board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=4, sub_tick_nb=5, tick_width=tick_width, tick_length=tick_length)
    board.get_gauge(name).add_ticks_label(label_color="lightgray", label_nb=4, label_size=label_size, label_radius=label_radius)
    board.get_gauge(name).add_label(text_color="lightgray", label="Temp\n[°C]", r=0.4, angle=6*np.pi/7, text_size=text_size)
    board.get_gauge(name).add_needle("neddle_1", needle_color="white", initial_value=50)

    name = "power_drive_" + str(nb)
    board.add_gauge(name, x0=x0, y0=y0, start_angle=-1 / 3 * np.pi, end_angle=1 / 3 * np.pi, min_value=0, max_value=40, clockwise=False)

    board.get_gauge(name).add_annular(values=[(0, 25), (25, 30), (30, 40)], colors=["green", "gold", "red"],
                                      inner_radius=0.95)
    board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=4, sub_tick_nb=5, tick_width=tick_width,
                                    tick_length=tick_length)
    board.get_gauge(name).add_ticks_label(label_color="lightgray", label_nb=4, label_size=label_size,
                                          label_radius=label_radius)
    board.get_gauge(name).add_label(text_color="lightgray", label="P [kW]", r=0.4, angle=np.pi / 7,
                                    text_size=text_size)
    board.get_gauge(name).add_needle("neddle_1", needle_color="white", initial_value=10)
    board.get_gauge(name).add_inner_circle(r=0.22)

def create_mppt_indicators(board, x0, y0, ind_name, nb, label_size=13, text_size=16, tick_width=4,
                                tick_length=0.15, label_radius=0.75):
        name = "temp_mppt_" + str(nb)
        board.add_gauge(name, x0=x0, y0=y0, start_angle=4 / 3 * np.pi, end_angle=2 / 3 * np.pi, with_background=True,
                        background_r=1.15)
        board.get_gauge(name).add_label(angle=np.pi / 2, r=1.3, text_size=30, text_color="black", label=ind_name)
        board.get_gauge(name).add_annular(values=[(0, 70), (70, 90), (90, 100)], colors=["green", "gold", "red"],
                                          inner_radius=0.95)
        board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=4, sub_tick_nb=5, tick_width=tick_width,
                                        tick_length=tick_length)
        board.get_gauge(name).add_ticks_label(label_color="lightgray", label_nb=4, label_size=label_size,
                                              label_radius=label_radius)
        board.get_gauge(name).add_label(text_color="lightgray", label="Temp\n[°C]", r=0.4, angle=6 * np.pi / 7,
                                        text_size=text_size)
        board.get_gauge(name).add_needle("min", needle_color="lawngreen", initial_value=25)
        board.get_gauge(name).add_needle("max", needle_color="red", initial_value=33)

        name = "power_mppt_" + str(nb)
        board.add_gauge(name, x0=x0, y0=y0, start_angle=-1 / 3 * np.pi, end_angle=1 / 3 * np.pi, min_value=0,
                        max_value=4, clockwise=False)

        board.get_gauge(name).add_annular(values=[(0, 3.5), (3.5, 4)], colors=["green", "gold"],
                                          inner_radius=0.95)
        board.get_gauge(name).add_ticks(tick_color="lightgray", tick_nb=4, sub_tick_nb=5, tick_width=tick_width,
                                        tick_length=tick_length)
        board.get_gauge(name).add_ticks_label(label_color="lightgray", label_nb=4, label_size=label_size,
                                              label_radius=label_radius)
        board.get_gauge(name).add_label(text_color="lightgray", label="P [kW]", r=0.4, angle=np.pi / 7,
                                        text_size=text_size)
        board.get_gauge(name).add_needle("neddle_1", needle_color="white", initial_value=10)
        board.get_gauge(name).add_inner_circle(r=0.22)

def create_status_indicators(board, x0, y0, width=3.6,height=1.8, ):
    names = ["stat_drive_1", "stat_drive_2", "stat_bat_1", "stat_bat_2","stat_mppt_1", "stat_mppt_2"]
    labels = ["Drive I", "Drive II", "Battery I", "Battery II", "MPPT I", "MPPT II"]
    x1 = [0.55, 2.15]
    y1 = [1.4, 0.9, 0.4]
    board.add_background(x0=x0, y0=y0, angle_r=0.25, width=width, height=height, fill_color="black")
    board.add_label("Status", x=x0+width/2, y=y0+height+0.2, text_align="center", text_size=30)
    for i, name in enumerate(names):
        board.add_enum(name, x0=x0 + x1[i % 2], y0=y0 + y1[int(i/2)])
        board.get_enum(name).add_label(labels[i], x=0.3, text_color="lightgray")


def cockpit_view():

    board = Dashboard(size=1000, x_lim=(0, 9.2), y_lim=(0, 8.4))
    board.add_background(x0=0.1, y0=0.1, angle_r=0.25, width=9, height=8.2)
    create_battery_indicators(board, x0=5.3, y0=4.1, ind_name="Battery I", gauge_nb=1)
    create_battery_indicators(board, x0=7.8, y0=4.1, ind_name="Battery II", gauge_nb=2)

    create_mppt_indicators(board, x0=5.3, y0=1.45, nb=1, ind_name="MPPT I")
    create_mppt_indicators(board, x0=7.8, y0=1.45, nb=2, ind_name="MPPT II")

    create_drive_indicators(board, x0=5.3, y0=6.75, nb=1, ind_name="Drive I")
    create_drive_indicators(board, x0=7.8, y0=6.75, nb=2, ind_name="Drive II")

    create_rpm_indicators(board, x0=2.1, y0=4.05)
    create_status_indicators(board, x0=0.3, y0=6.05)

    img_path = "https://heig-vd.ch/images/default-source/img-institut-iese/iese_heig-vd_logotype_rouge-rvb.png?sfvrsn=345f44e5_0"
    try:
        board.add_image(img_path, x0=0.3, y0=1.4, size=3)
    except:
        print("no internet connection to add logo")

    ## local file display doesn't work (grey zone...)
    # img_path = os.path.join(os.getcwd(), 'iese_heig-vd_logotype_rouge-rvb.png')
    # board.add_image(img_path, x0=0.3, y0=0.3, size=3.5)  # 4 division de pixels entiers (1024x352)

    return board


if __name__ == "__main__":
    board_1 = cockpit_view()
    output_file("board_1.html")
    show(board_1.fig)
