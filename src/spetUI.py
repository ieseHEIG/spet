"""
Graphical User Interface (web browser) for SPET project
@authors: luca, yvan

install peak-can drivers, python then "pip install panel" which include bokeh

To do:
Add 6 texts zones relatives to the 6 color status

Add 2x 5 ticks linked to 5 variables (0x00 or 0xFF), they will be sent over CAN bus for module A and B
Safe Shutdown
Charge Request
Discharge Request
Clear Faults
Reboot Request


PCAN_RW:
DRIVE & MPPT tests, errors/warning table definitions
"""
# from bokeh.layouts import column
# from bokeh.models import Slider, Button

from bokeh.server.server import Server
from bokeh.models import TabPanel, Tabs

from spetDashboard import *

import time

from PCAN_RW import *
spet_a = PcanRW(0x1)  # initialisation with identifier, written on the PeakCAN-USB device, and set with the manufacturer software
spet_b = PcanRW(0x2)  # initialisation with identifier, written on the PeakCAN-USB device, and set with the manufacturer software


class SpetUI():

    def __init__(self):
        """
        Constructor & initialisations
        """
        self.CAN_init()

        self.cockpit_view = cockpit_view()

        self.update_rate_data = 100  # ms, min approx. 20ms
        self.update_rate_display = 250  # ms, min approx. 20ms

        self.server = Server({'/': self.bkapp}, num_procs=1)
        self.server.start()

    def bkapp(self, doc):
        """
        Bokeh application definitions
        """
        tab1 = TabPanel(child=self.cockpit_view.fig, title="Cockpit view")
        # tab2 = Panel(child=column(self.diag_view, plot), title="Diagnostic")
        doc.add_root(Tabs(tabs=[tab1]))  # doc.add_root(Tabs(tabs=[tab1, tab2]))
        doc.add_periodic_callback(self._get_data, self.update_rate_data)
        doc.add_periodic_callback(self._update_indicators, self.update_rate_display)
    
    def _get_data(self):
        """
        UI data périodic calls (update_rate_data)
        """
        self.CAN_main()

    def _update_indicators(self):
        """
        UI display périodic calls (update_rate_display)
        """
        color_dict = {"GREEN":1, "ORANGE":2, "RED":3}  # to match PCAN_RW colors with bokeh UI

        mppt_1_t1 = spet_a.MPPT_T1[0]
        mppt_1_t2 = spet_a.MPPT_T1[0]
        mppt_1_kw = 0

        mppt_2_t1 = spet_b.MPPT_T1[0]
        mppt_2_t2 = spet_b.MPPT_T1[0]
        mppt_2_kw = 0

        for i in range(spet_a.MPPT_NOMBRE):
            mppt_1_kw += spet_a.MPPT_W[i] / 1000
            mppt_1_t1 = min(mppt_1_t1, spet_a.MPPT_T1[i], spet_a.MPPT_T2[i])
            mppt_1_t2 = max(mppt_1_t1, spet_a.MPPT_T1[i], spet_a.MPPT_T2[i])

        for i in range(spet_b.MPPT_NOMBRE):
            mppt_2_kw += spet_b.MPPT_W[i] / 1000
            mppt_2_t1 = min(mppt_2_t1, spet_b.MPPT_T1[i], spet_b.MPPT_T2[i])
            mppt_2_t2 = max(mppt_2_t1, spet_b.MPPT_T1[i], spet_b.MPPT_T2[i])

        # called here, in case there is no received CAN messages (watchdogs...)
        # and for better processing efficiency
        spet_a.LeclancheStatus()
        spet_a.MpptStatus()
        spet_a.DriveStatus()
        spet_b.LeclancheStatus()
        spet_b.MpptStatus()
        spet_b.DriveStatus()

        self.cockpit_view.set_values({
                                      "rpm":           [0],
                                      "soc_bat_1":     [spet_a.BAT_SOC],
                                      "soc_bat_2":     [spet_b.BAT_SOC],
                                      "power_bat_1":   [spet_a.BAT_POWER],
                                      "power_bat_2":   [spet_b.BAT_POWER],
                                      "temp_bat_1":    [spet_a.BAT_T_MIN,
                                                        spet_a.BAT_T_MEAN,
                                                        spet_a.BAT_T_MAX],
                                      "temp_bat_2":    [spet_b.BAT_T_MIN,
                                                        spet_b.BAT_T_MEAN,
                                                        spet_b.BAT_T_MAX],
                                      "temp_drive_1":  [max(spet_a.DRIVE_SIC_U_TEMP, spet_a.DRIVE_SIC_V_TEMP, spet_a.DRIVE_SIC_W_TEMP)],
                                      "temp_drive_2":  [max(spet_b.DRIVE_SIC_U_TEMP, spet_b.DRIVE_SIC_V_TEMP, spet_b.DRIVE_SIC_W_TEMP)],
                                      "power_drive_1": [spet_a.DRIVE_ELEC_POWER],
                                      "power_drive_2": [spet_b.DRIVE_ELEC_POWER],
                                      "temp_mppt_1":   [mppt_1_t1,
                                                        mppt_1_t2],
                                      "temp_mppt_2":   [mppt_2_t1,
                                                        mppt_2_t2],
                                      "power_mppt_1":  [mppt_1_kw],
                                      "power_mppt_2":  [mppt_2_kw],
                                      "stat_drive_1":  color_dict[spet_a.DRIVE_STATUS_COLOR],
                                      "stat_drive_2":  color_dict[spet_b.DRIVE_STATUS_COLOR],
                                      "stat_mppt_1":   color_dict[spet_a.MPPT_STATUS_COLOR],
                                      "stat_mppt_2":   color_dict[spet_b.MPPT_STATUS_COLOR],
                                      "stat_bat_1":    color_dict[spet_a.BAT_STATUS_COLOR],
                                      "stat_bat_2":    color_dict[spet_b.BAT_STATUS_COLOR],
                                      "use_time":      (self.TS - self.TS_START) / 60  # minutes
                                      })

    def CAN_init(self):
        """
        initialisations for CAN bus communications
        called with __init__ constructor
        """
        self.CAN_set_module_a()
        time.sleep(3)  # 24V power supply not enough powerfull to start 2 BMS at the same time.
                       # Need 3A/module (peak at activation then 0.9 for both once activated...)
                       # Delays can be removed using a 6A power supply
        self.CAN_set_module_b()
        # "set_module" commands will be periodicly sent

        self.TS_START = time.time()
        self.TS_ID_OLD = self.TS_START
        self.TS_CAN_OLD = self.TS_START
        self.TS_UPDATE_OLD1 = self.TS_START - 6  ## 6s offset to not update set_module a and b at the same time (not enough 24V power)
        self.TS_UPDATE_OLD2 = self.TS_START

    def CAN_main(self):
        """
        infinite call loop (_get_data, 1 / self.update_rate_data frequency),
        except ID (and watchdogs) checked slowly
        """
        self.TS = time.time()

        # PCAN ID periodical check (1Hz), appropriate resets if necessary
        # and watchdogs checks/resets
        if self.TS - self.TS_ID_OLD > 1:
            self.TS_ID_OLD = self.TS
            self.CAN_check_devices()
            self.CAN_Watchdogs()

        # CAN bus read messages, until empty buffer
        if self.TS - self.TS_CAN_OLD > 0.25:  # 4Hz but always true 0.25s after start if commented following line --> self.update_rate_data
            # self.TS_CAN_OLD = self.TS  # commented, next lines will be processed at each call (_get_data, at self.update_rate_data frequency)
            while self.CAN_read_module_a() == 0:
                pass
            while self.CAN_read_module_b() == 0:
                pass

        # Send module configuration messages periodically, or at each changed state (user interface not yet implemented),
        # with delay between both modules in case they're not activated because of a weak 24V power (need 3A peak/module...)
        if self.TS - self.TS_UPDATE_OLD1 > 12:
            self.CAN_set_module_a()
            self.TS_UPDATE_OLD1 = self.TS
        if self.TS - self.TS_UPDATE_OLD2 > 12:
            self.CAN_set_module_b()
            self.TS_UPDATE_OLD2 = self.TS_UPDATE_OLD1 + 6 # from OLD1 to avoid an intervall drift (execution times...)

        return 0

    def CAN_check_devices(self):
        """
        PCAN ID check (connexion, correct device...)
        On error: Erase decoded values and error displayed
                  Try to re-initialise Pcan module A, or B
                  Small "side effect" of A on B, all ok after 2 calls...
        """
        try:
            spet_a_ID = spet_a.GetDeviceId()
        except:
            spet_a_ID = 0
            print("PCAN ID 1 error on module A")
        try:
            spet_b_ID = spet_b.GetDeviceId()
        except:
            spet_b_ID = 0
            print("PCAN ID 2 error on module B")

        if spet_a_ID != 1:
            spet_a.UnsetDevice()
            spet_a.TryToSetDevice()
        if spet_b_ID != 2:
            spet_b.UnsetDevice()
            spet_b.TryToSetDevice()

    def CAN_read_module_a(self):
        """
        CAN bus message reads:
        need to be called at a frequency higher than messages, to avoid buffer gap, then overflow (max 32768 messages)
        A reading loop is best practice, until error or empty buffer
        """
        try:
            status_a = spet_a.ReadMessage()  # 0 ok, 7168 NOK
        except:
            status_a = PCAN_ERROR_ILLOPERATION
            print("CAN read error on module A")
            return 2

        if status_a == PCAN_ERROR_OK:
            return 0
        elif status_a == PCAN_ERROR_QRCVEMPTY:
            return 1
        else:
            print("PCAN_ERROR " + str(hex(status_a)))
            return 2

    def CAN_read_module_b(self):
        """
        CAN bus message reads:
        need to be called at a frequency higher than messages, to avoid buffer gap, then overflow (max 32768 messages)
        A reading loop is best practice, until error or empty buffer
        """
        try:
            status_b = spet_b.ReadMessage()  # 0 ok
        except:
            status_b = PCAN_ERROR_ILLOPERATION
            print("CAN read error on module B")
            return 2

        if status_b == PCAN_ERROR_OK:
            return 0
        elif status_b == PCAN_ERROR_QRCVEMPTY:
            return 1
        else:
            print("PCAN_ERROR " + str(hex(status_b)))
            return 2

    def CAN_set_module_a(self):
        """
        CAN bus sent message, first check ID
        """
        try:
            spet_a_ID = spet_a.GetDeviceId()
        except:
            print("PCAN ID 1 error for module A")
            return

        # datas_l = [0, 0xFF, 0, 0, 0, 0, 0, 0]  # safe shutdown
        datas_l = [0, 0, 0, 0xFF, 0, 0, 0, 0]  # discharge
        tuple_l = tuple(datas_l)
        print("sent bytes on module_a, can id 0x200: " + str(tuple_l))
        try:
            spet_a.WriteMessage(0x200, tuple_l)
        except:
            print("CAN sent error on module A")

    def CAN_set_module_b(self):
        """
        CAN bus sent message, first check ID
        """
        try:
            spet_b_ID = spet_b.GetDeviceId()
        except:
            print("PCAN ID 2 error for module B")
            return

        # datas_r = [0, 0xFF, 0, 0, 0, 0, 0, 0]  # safe shutdown
        datas_r = [0, 0, 0, 0xFF, 0, 0, 0, 0]  # discharge
        tuple_r = tuple(datas_r)
        print("sent bytes on module_b, can id 0x200: " + str(tuple_r))
        try:
            spet_b.WriteMessage(0x200, tuple_r)
        except:
            print("CAN sent error on module B")

    def CAN_Watchdogs(self):
        """
        Control all watchdog bits have been activated by their CAN message
        (periodic call with time margin to control all activations)
        Flags and errors are activated if wrong sum, through Init() calls to reset displayed values at the same time
        Watchdogs resets
        """
        if spet_a.BAT_WATCHDOG == 0x3F:  # sum of all activated bits
            spet_a.BAT_WATCHDOG_FLAG = 0
        else:
            spet_a.LeclancheInit()

        if spet_b.BAT_WATCHDOG == 0x3F:
            spet_b.BAT_WATCHDOG_FLAG = 0
        else:
            spet_b.LeclancheInit()


        if spet_a.MPPT_WATCHDOG == 0x07:
            spet_a.MPPT_WATCHDOG_FLAG = 0
        else:
            spet_a.MpptInit()

        if spet_b.MPPT_WATCHDOG == 0x07:
            spet_b.MPPT_WATCHDOG_FLAG = 0
        else:
            spet_b.MpptInit()


        if spet_a.DRIVE_WATCHDOG == 0x1FF:
            spet_a.DRIVE_WATCHDOG_FLAG = 0
        else:
            spet_a.DriveInit()

        if spet_b.DRIVE_WATCHDOG == 0x1FF:
            spet_b.DRIVE_WATCHDOG_FLAG = 0
        else:
            spet_b.DriveInit()


        spet_a.BAT_WATCHDOG = 0
        spet_a.DRIVE_WATCHDOG = 0
        spet_a.MPPT_WATCHDOG = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

        spet_b.BAT_WATCHDOG = 0
        spet_b.DRIVE_WATCHDOG = 0
        spet_b.MPPT_WATCHDOG = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]


if __name__ == '__main__':
    print('Opening Bokeh application on http://localhost:5006/')
    spetUI = SpetUI()
    spetUI.server.io_loop.add_callback(spetUI.server.show, "/")
    spetUI.server.io_loop.start()
