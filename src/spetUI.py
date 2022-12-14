"""
Graphical User Interface (web browser) for SPET project
@authors: luca, yvan

install peak-can drivers, python then "pip install panel" which include bokeh

Todo: Add 6 texts zones relatives to the 6 color status (BAT_ MPPT_ and DRIVE_ STATUS_TEXT) then remove STATUS_TEXT_prints

Add 2x 5 ticks linked to 5 variables (0x00 or 0xFF), they will be sent over CAN bus for module A and B
Safe Shutdown
Charge Request
Discharge Request
Clear Faults
Reboot Request

with a 24v/6A power supply instead of 3A, it is possible to remove delays between activations:
serach for parts relative to TS_UPDATE_OLD1 and TS_UPDATE_OLD2


PCAN_RW:
DRIVE & MPPT tests, errors/warning table definitions
"""
# from bokeh.layouts import column
# from bokeh.models import Slider, Button

from bokeh.server.server import Server
from bokeh.models import TabPanel, Tabs

from spetDashboard import cockpit_view

import time

from PCAN_RW import *


class SpetUI:
    """
    Main class to create user interface of spet project
    """
    def __init__(self):
        """
        Constructor & initialisations
        """
        # Initialisation with identifier, written on the PeakCAN-USB device, and set with the manufacturer software
        self.module_a = PcanRW(0x1)
        self.module_b = PcanRW(0x2)
        # Initialisation CAN variable
        self.TS = 0.0
        self.module_a_ID = 0
        self.module_b_ID = 0
        # Initialisation user interface dashboard
        self.cockpit_view = cockpit_view()
        self.update_rate_data = 100  # ms, min approx. 20ms
        self.update_rate_display = 250  # ms, min approx. 20ms
        # Initialisation CAN variable
        self.CAN_set_module(module_id="module_a")
        # 24V power supply not enough powerfull to start 2 BMS at the same time.
        # Need 3A/module (peak at activation then 0.9 for both once activated...)
        # Delays can be removed using a 6A power supply
        time.sleep(3)
        self.CAN_set_module(module_id="module_b")
        # "set_module" commands will be periodicly sent
        self.TS_START = time.time()
        self.TS_ID_OLD = self.TS_START
        self.TS_CAN_OLD = self.TS_START
        # 6s offset to not update set_module a and b at the same time (not enough 24V power)
        self.TS_UPDATE_OLD1 = self.TS_START - 6
        self.TS_UPDATE_OLD2 = self.TS_START
        # Initaliation of the displaying server
        self.server = Server({'/': self.bkapp}, num_procs=1)
        self.server.start()

    def bkapp(self, doc):
        """
        Bokeh application definitions
        """
        tab1 = TabPanel(child=self.cockpit_view.fig, title="Cockpit view")
        # tab2 = TabPanel(child=column(self.diag_view, plot), title="Diagnostic")
        doc.add_root(Tabs(tabs=[tab1]))
        doc.add_periodic_callback(self._get_data, self.update_rate_data)
        doc.add_periodic_callback(self._update_indicators, self.update_rate_display)

    def _update_indicators(self):
        """
        UI display périodic calls (update_rate_display)
        """
        color_dict = {"GREEN": 1, "ORANGE": 2, "RED": 3}  # to match PCAN_RW colors with bokeh UI

        mppt_1_t1 = self.module_a.MPPT_T1[0]
        mppt_1_t2 = self.module_a.MPPT_T1[0]
        mppt_1_kw = 0

        mppt_2_t1 = self.module_b.MPPT_T1[0]
        mppt_2_t2 = self.module_b.MPPT_T1[0]
        mppt_2_kw = 0

        for i in range(self.module_a.MPPT_NOMBRE):
            mppt_1_kw += self.module_a.MPPT_W[i] / 1000
            mppt_1_t1 = min(mppt_1_t1, self.module_a.MPPT_T1[i], self.module_a.MPPT_T2[i])
            mppt_1_t2 = max(mppt_1_t1, self.module_a.MPPT_T1[i], self.module_a.MPPT_T2[i])

        for i in range(self.module_b.MPPT_NOMBRE):
            mppt_2_kw += self.module_b.MPPT_W[i] / 1000
            mppt_2_t1 = min(mppt_2_t1, self.module_b.MPPT_T1[i], self.module_b.MPPT_T2[i])
            mppt_2_t2 = max(mppt_2_t1, self.module_b.MPPT_T1[i], self.module_b.MPPT_T2[i])

        self.STATUS_TEXT_prints()

        self.cockpit_view.set_values({
            "rpm":           [0],
            "soc_bat_1":     [self.module_a.BAT_SOC],
            "soc_bat_2":     [self.module_b.BAT_SOC],
            "power_bat_1":   [self.module_a.BAT_POWER],
            "power_bat_2":   [self.module_b.BAT_POWER],
            "temp_bat_1":    [self.module_a.BAT_T_MIN, self.module_a.BAT_T_MEAN, self.module_a.BAT_T_MAX],
            "temp_bat_2":    [self.module_b.BAT_T_MIN,  self.module_b.BAT_T_MEAN, self.module_b.BAT_T_MAX],
            "temp_drive_1":  [max(self.module_a.DRIVE_SIC_U_TEMP,
                                  self.module_a.DRIVE_SIC_V_TEMP,
                                  self.module_a.DRIVE_SIC_W_TEMP)],
            "temp_drive_2":  [max(self.module_b.DRIVE_SIC_U_TEMP,
                                  self.module_b.DRIVE_SIC_V_TEMP,
                                  self.module_b.DRIVE_SIC_W_TEMP)],
            "power_drive_1": [self.module_a.DRIVE_ELEC_POWER],
            "power_drive_2": [self.module_b.DRIVE_ELEC_POWER],
            "temp_mppt_1":   [mppt_1_t1, mppt_1_t2],
            "temp_mppt_2":   [mppt_2_t1, mppt_2_t2],
            "power_mppt_1":  [mppt_1_kw],
            "power_mppt_2":  [mppt_2_kw],
            "stat_drive_1":  color_dict[self.module_a.DRIVE_STATUS_COLOR],
            "stat_drive_2":  color_dict[self.module_b.DRIVE_STATUS_COLOR],
            "stat_mppt_1":   color_dict[self.module_a.MPPT_STATUS_COLOR],
            "stat_mppt_2":   color_dict[self.module_b.MPPT_STATUS_COLOR],
            "stat_bat_1":    color_dict[self.module_a.BAT_STATUS_COLOR],
            "stat_bat_2":    color_dict[self.module_b.BAT_STATUS_COLOR],
            "use_time":      (self.TS - self.TS_START) / 60  # minutes
        })

    def _get_data(self):
        """
        infinite call loop (_get_data, 1 / self.update_rate_data frequency),
        except ID (and watchdogs) checked slowly
        """
        # PCAN ID periodical check (1Hz), appropriate resets if necessary
        # and watchdogs checks/resets
        if self.TS - self.TS_ID_OLD > 1:
            self.TS_ID_OLD = self.TS
            self.CAN_check_devices()
            self.CAN_Watchdogs(module_id="module_a")
            self.CAN_Watchdogs(module_id="module_b")

        # CAN bus read messages, until empty buffer
        if self.TS - self.TS_CAN_OLD > 0.25:
            # 4Hz but always true 0.25s after start if commented following line --> self.update_rate_data
            # self.TS_CAN_OLD = self.TS  # commented, next lines will be processed at each call (_get_data, at self.update_rate_data frequency)
            while self.CAN_read_module(module_id="module_a") == 0:
                pass
            while self.CAN_read_module(module_id="module_b") == 0:
                pass
        # Send module configuration messages periodically, or at each changed state (user interface not yet implemented),
        # with delay between both modules in case they're not activated because of a weak 24V power (need 3A peak/module...)
        if self.TS - self.TS_UPDATE_OLD1 > 12:
            self.CAN_set_module(module_id="module_a")
            self.TS_UPDATE_OLD1 = self.TS
        if self.TS - self.TS_UPDATE_OLD2 > 12:
            self.CAN_set_module(module_id="module_b")
            self.TS_UPDATE_OLD2 = self.TS_UPDATE_OLD1 + 6
            # from OLD1 to avoid an intervall drift (execution times...)

    def CAN_check_devices(self):
        """
        PCAN ID check (connexion, correct device...)
        On error: Erase decoded values and error displayed
                  Try to re-initialise Pcan module A, or B
                  Small "side effect" of A on B, all ok after 2 calls...
        """
        try:
            self.module_a_ID = self.module_a.GetDeviceId()
        except():
            self.module_a_ID = 0
            print("PCAN ID 1 error on module A")
        try:
            self.module_b_ID = self.module_b.GetDeviceId()
        except():
            self.module_b_ID = 0
            print("PCAN ID 2 error on module B")

        if self.module_a_ID != 1:
            self.module_a.UnsetDevice()
            self.module_a.TryToSetDevice()
        if self.module_b_ID != 2:
            self.module_b.UnsetDevice()
            self.module_b.TryToSetDevice()

    def CAN_read_module(self, module_id: str):
        """
        CAN bus message reads:
        need to be called at a frequency higher than messages, to avoid buffer gap, then overflow (max 32768 messages)
        A reading loop is best practice, until error or empty buffer
        """
        try:
            status = getattr(self, module_id).ReadMessage()  # 0 ok, 7168 NOK
            if status == PCAN_ERROR_OK:
                return 0
            elif status == PCAN_ERROR_QRCVEMPTY:
                return 1
            else:
                print("PCAN_ERROR {} on {}, see PCANlib.py or try to unplug/replug PCAN_USB"
                      .format(hex(status), module_id))
                return 2
        except():
            print("CAN read error on {}".format(module_id))
            return 2

    def CAN_set_module(self, module_id: str):
        """
        CAN bus sent message, first check ID
        """
        if getattr(self, module_id).PcanHandle == PCAN_NONEBUS:
            return
        try:
            setattr(self, module_id + "_ID", getattr(self, module_id).GetDeviceId())
        except():
            print("PCAN ID 2 error for {}".format(module_id))
            return

        datas_r = [0, 0, 0, 0xFF, 0, 0, 0, 0]  # discharge
        tuple_r = tuple(datas_r)
        print("sent bytes {}, can id 0x200: {}".format(module_id, tuple_r))
        try:
            getattr(self, module_id).WriteMessage(0x200, tuple_r)
        except():
            print("CAN sent error on {}".format(module_id))

    def CAN_Watchdogs(self, module_id):
        """
        Control all watchdog bits have been activated by their CAN message
        (periodic call with time margin to control all activations)
        Flags and errors are activated if wrong sum, through Init() calls to reset displayed values at the same time
        Watchdogs resets
        """
        if getattr(self, module_id).BAT_WATCHDOG == 0x3F:  # sum of all activated bits
            getattr(self, module_id).BAT_WATCHDOG_FLAG = 0
        else:
            getattr(self, module_id).LeclancheInit()

        if getattr(self, module_id).MPPT_WATCHDOG == 0x07:
            getattr(self, module_id).MPPT_WATCHDOG_FLAG = 0
        else:
            getattr(self, module_id).MpptInit()

        if getattr(self, module_id).DRIVE_WATCHDOG == 0x1FF:
            getattr(self, module_id).DRIVE_WATCHDOG_FLAG = 0
        else:
            getattr(self, module_id).DriveInit()
        getattr(self, module_id).BAT_WATCHDOG = 0
        getattr(self, module_id).DRIVE_WATCHDOG = 0
        getattr(self, module_id).MPPT_WATCHDOG = [0]*25
        # called here, in case there is no received CAN messages (watchdogs...)
        getattr(self, module_id).LeclancheDecode()
        getattr(self, module_id).MpptDecode()
        getattr(self, module_id).DriveDecode()
        # and for better processing efficiency (no intermediaite status_text)
        getattr(self, module_id).LeclancheStatus()
        getattr(self, module_id).MpptStatus()
        getattr(self, module_id).DriveStatus()

    def STATUS_TEXT_prints(self):
        """
        Print status text modifications in console,
        can be removed after graphical user interface implementation
        """
        if self.module_a.BAT_STATUS_TEXT_OLD != self.module_a.BAT_STATUS_TEXT:
            print("BATTERY A status modification: " + self.module_a.BAT_STATUS_TEXT)
            self.module_a.BAT_STATUS_TEXT_OLD = self.module_a.BAT_STATUS_TEXT

        if self.module_b.BAT_STATUS_TEXT_OLD != self.module_b.BAT_STATUS_TEXT:
            print("BATTERY B status modification: " + self.module_b.BAT_STATUS_TEXT)
            self.module_b.BAT_STATUS_TEXT_OLD = self.module_b.BAT_STATUS_TEXT

        if self.module_a.MPPT_STATUS_TEXT_OLD != self.module_a.MPPT_STATUS_TEXT:
            print("MPPT A status modification: " + self.module_a.MPPT_STATUS_TEXT)
            self.module_a.MPPT_STATUS_TEXT_OLD = self.module_a.MPPT_STATUS_TEXT

        if self.module_b.MPPT_STATUS_TEXT_OLD != self.module_b.MPPT_STATUS_TEXT:
            print("MPPT B status modification: " + self.module_b.MPPT_STATUS_TEXT)
            self.module_b.MPPT_STATUS_TEXT_OLD = self.module_b.MPPT_STATUS_TEXT

        if self.module_a.DRIVE_STATUS_TEXT_OLD != self.module_a.DRIVE_STATUS_TEXT:
            print("DRIVE A status modification: " + self.module_a.DRIVE_STATUS_TEXT)
            self.module_a.DRIVE_STATUS_TEXT_OLD = self.module_a.DRIVE_STATUS_TEXT

        if self.module_b.DRIVE_STATUS_TEXT_OLD != self.module_b.DRIVE_STATUS_TEXT:
            print("DRIVE B status modification: " + self.module_b.DRIVE_STATUS_TEXT)
            self.module_b.DRIVE_STATUS_TEXT_OLD = self.module_b.DRIVE_STATUS_TEXT


if __name__ == '__main__':
    print('Opening Bokeh application on http://localhost:5006/')
    spetUI = SpetUI()
    spetUI.server.io_loop.add_callback(spetUI.server.show, "/")
    spetUI.server.io_loop.start()
