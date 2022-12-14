#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Class PcanRW, depend on a device identifier as a parameter (0x1 et 0x2 for SPET modules, A and B as physically labeled),
allow read/write on matching CAN bus PCAN_USBBUS1 or PCAN_USBBUS2

The operation of the PCAN driver is such that bus 1 or 2 must be associated (connection order...) with a read ID
Bus 2 becomes 1 when 1 is disconnected! Except when it is reserved by a running program.

Include functions related to the SPET project (communications with Leclanché batteries, mppts modules and motor drive)

A software watchdog checks communications

@author: yvan + Peak librairies (the IDs are initially not properly managed !)



DRIVE and MPPT functions not tested (devices are not yet ready)
Their error/warning codes are not yet defined (numbers and texts to modify)
"""

import struct
from PCANlib import *


def hex2num(hex_s):
    """
    Hexadecimal string to unsigned number, valid with 1, 2, 4 bytes...
    """
    return int(hex_s, 16)

def hex2float(hex4bytes):
    """
    Convert a 4 hexadecimal bytes number or string, to float (import struct)
    """
    return struct.unpack('!f', bytes.fromhex(str(hex4bytes)))[0]

def i16(ui16):
    """
    Convert unsigned int (16bits) to int (signed 16bits)
    """
    return ui16-2*32768 if ui16 > 32767 else ui16

class PcanRW():
    """
    Object with PCAN identifier as a parameter -> device_id in __init__
    Here are PeakCAN USB functions, and SPET project variables and decoding functions
    """
    PcanHandle = PCAN_NONEBUS  # PCAN_USBBUS1, PCAN_USBBUS2, PCAN_NONEBUS
    Bitrate = PCAN_BAUD_250K
    # PcanId = 0

    m_DLLFound = False

    # Last read values with ProcessMessageCan function
    ReceivedTimestamp = 0  # seconds
    ReceivedId = 0
    ReceivedDatas = bytearray(8)

    def __init__(self, device_id):
        """
        Called at object creation
        """
        self.PcanId = device_id
        self.LeclancheInit()
        self.MpptInit()
        self.DriveInit()
        self.BAT_STATUS_TEXT_OLD = ''
        self.MPPT_STATUS_TEXT_OLD = ''
        self.DRIVE_STATUS_TEXT_OLD = ''

        ## Checks if PCANBasic.dll is available, if not, the terminates without PCAN hardware inits
        try:
            self.m_objPCANBasic = PCANBasic()
            self.m_DLLFound = True
        except:
            print("Unable to find the library: PCANBasic.dll !")
            self.m_DLLFound = False
            return

        self.TryToSetDevice()  ## only if PCAN library found

    def __del__(self):
        if self.m_DLLFound:
            self.m_objPCANBasic.Uninitialize(self.PcanHandle)

    def TryToSetDevice(self):
        """
        Try to initialize a device on increasing "PCAN_USBBUS" number (depend on device plugging order)
        """
        status = self.SetDevice(PCAN_USBBUS1)
        if status == 0:
            print("PCAN_USBBUS1 OK for device ID " + str(hex(self.PcanId)))
        else:
            status = self.SetDevice(PCAN_USBBUS2)
            if status == 0:
                print("PCAN_USBBUS2 OK for device ID " + str(hex(self.PcanId)))
            else:
                status = self.SetDevice(PCAN_NONEBUS)
                print("PCAN_NONEBUS for device ID " + str(hex(self.PcanId)))

    def SetDevice(self, bus):  # bus = PCAN_USBBUS1 (0x51 ou 81), PCAN_USBBUS2 (0x52 ou 82), PCAN_NONEBUS (0)
        """
        Initialize a device on a given "PCAN_USBBUS" number and check ID if successfull
        return 4 status
        """
        self.PcanHandle = bus
        try:
            stsResult = self.m_objPCANBasic.Initialize(self.PcanHandle, self.Bitrate)
        except:
            print("initialisation error on PcanHandle " + str(self.PcanHandle))
            return 1
        if stsResult == PCAN_ERROR_OK:  # PCAN_ERROR_OK défini à 0...
            if self.GetDeviceId() == self.PcanId:
                print("device ID " + str(hex(self.PcanId)) + " match on bus " + str(self.PcanHandle))
                return 0
            else:
                print("no match for device ID " + str(hex(self.PcanId)) + " on bus " + str(self.PcanHandle))
                return 2
        else:
            # print("PCAN initialisation error " + str(hex(stsResult)))
            return 3

    def UnsetDevice(self):
        """
        Unset device is necessary before a new possible initialisation (between checks and try to set if it has already been set)
        """
        try:
            self.m_objPCANBasic.Uninitialize(self.PcanHandle)
        except:
            print("Uninitialize error on PcanHandle " + str(self.PcanHandle))

    def WriteMessage(self, msgCanID, msgCanDATA):
        """
        Write messages on CAN, return a TPCANStatus error code
        """
        msgCanMessage = TPCANMsg()
        msgCanMessage.ID = msgCanID
        msgCanMessage.LEN = 8
        msgCanMessage.MSGTYPE = PCAN_MESSAGE_STANDARD.value
        msgCanMessage.DATA = msgCanDATA  # (0, 0, 0, 0xFF, 0, 0, 0, 0), <class 'tuple'>

        return self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)

    def ReadMessage(self):
        """
        Read CAN messages on normal CAN devices, returns a TPCANStatus error code
        """
        stsResult = self.m_objPCANBasic.Read(self.PcanHandle)
        if stsResult[0] == PCAN_ERROR_OK:
            self.ProcessMessageCan(stsResult[1], stsResult[2])

        return stsResult[0]

    def ProcessMessageCan(self, msg, itstimestamp):
        """
        Processes a received CAN message

        Parameters:
            msg = The received PCAN-Basic CAN message
            itstimestamp = Timestamp of the message as TPCANTimestamp structure
        """
        microsTimeStamp = itstimestamp.micros + 1000 * itstimestamp.millis + 0x100000000 * 1000 * itstimestamp.millis_overflow

        self.ReceivedTimestamp = microsTimeStamp / 1000000
        self.ReceivedId = msg.ID
        for i in range(8):
            self.ReceivedDatas[i] = msg.DATA[i]

        self.LeclancheDecode()
        self.MpptDecode()
        self.DriveDecode()

    def GetDeviceId(self):
        """
        Shows device identifier parameter
        """
        stsResult = self.m_objPCANBasic.GetValue(self.PcanHandle, PCAN_DEVICE_ID)
        if stsResult[0] == PCAN_ERROR_OK:
            return stsResult[1]

    def LeclancheInit(self):
        """
        Variables initialisations for battery module (decoded from CAN messages)
        """
        # tpdo_1
        self.BAT_HEARTBEAT1 = 0
        # print("self.BAT_HEARTBEAT1", self.BAT_HEARTBEAT1)
        self.BAT_SOC = 0
        self.BAT_ACTIVE_ERR = 0
        self.BAT_ACTIVE_WARN = 0
        self.BAT_CHARGE_I_LIM = 0
        self.BAT_DISCHARGE_I_LIM = 0

        # tpdo_2
        self.BAT_HEARTBEAT2 = 0
        self.BAT_SOH = 0
        self.BAT_STATUS_1 = 0
        self.BAT_STATUS_2 = 0
        self.BAT_VOLTAGE = 0
        self.BAT_CURRENT = 0
        self.BMS_OK = 0
        self.BMS_IDLE = 0
        self.BMS_CHARGE = 0
        self.BMS_DISCHARGE = 0
        self.BAT_FULL = 0

        # tpdo_3
        self.CELL_V_MIN = 0
        self.CELL_V_MIN_ID = 0
        self.CELL_V_MAX = 0
        self.CELL_V_MAX_ID = 0

        # tpdo_4
        self.BAT_T_MIN = 0
        self.BAT_T_MEAN = 0
        self.BAT_T_MAX = 0
        self.BAT_T_MIN_ID = 0
        self.BAT_T_MAX_ID = 0

        # tpdo_5
        self.BAT_STATE_CHARGING = 0
        self.BAT_STATE_DISCHARGING = 0
        self.BAT_STATE_CONTACTOR_1 = 0
        self.BAT_STATE_CONTACTOR_2 = 0
        self.BAT_STATE_CONTACTOR_3 = 0
        self.BAT_STATE_CONTACTOR_4 = 0
        self.BAT_STATE_BALANCING = 0
        self.GPIO = 0
        # tpdo_5 extraits de GPIO
        self.BAT_IO_1 = 0
        self.BAT_IO_2 = 0
        self.BAT_IO_3 = 0
        self.BAT_IO_4 = 0
        self.BAT_IO_5 = 0

        # tpdo_6
        self.BAT_FLAGS_ERR = 0
        self.BAT_FLAGS_WARN = 0

        # calculated or analysed:
        self.BAT_POWER = 0  # VOLTAGE x CURRENT / 1000 --> kW
        self.BAT_INITIAL_CAPACITY = 19  # kW.h of a new battery
        self.BAT_REMAINING_ENERGY = 0  # SOC x SOH x INITIAL_CAPACITY
        # self.BAT_STATUS_TEXT = ''
        self.BAT_STATUS_COLOR = 'RED'  # GREEN, ORANGE, RED
        self.BAT_WATCHDOG = 0   # each periodic necessary message activate bits 0x01 0x02 0x04 0x08 0x10 0x20...
                                # for BAT, periodic check that sum == 0x3F and reset to zero, or error activation (32 is free about BAT)
        self.BAT_WATCHDOG_FLAG = 1
        self.BAT_ACTIVE_ERR = 32
        self.BAT_FLAGS_ERR |= 0x80000000

    def LeclancheDecode(self):
        """
        Message identification from CAN ID,
        Set values according to ID and Leclanché tables
        function decode <-- status <-- table
        Called with each received CAN message
        """
        if self.ReceivedId >= 0x100 and self.ReceivedId <= 0x112:
            if self.ReceivedId == 0x100:  # tpdo_1
                self.BAT_HEARTBEAT1 = self.ReceivedDatas[0]
                self.BAT_SOC = self.ReceivedDatas[1] / 2  # %
                self.BAT_ACTIVE_ERR = self.ReceivedDatas[2]
                self.BAT_ACTIVE_WARN = self.ReceivedDatas[3]
                # Errors/Warning share same codes: 1...17, 19, 20, 25, 31
                self.BAT_CHARGE_I_LIM = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.BAT_DISCHARGE_I_LIM = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.BAT_CHARGE_I_LIM = hex2num(self.BAT_CHARGE_I_LIM) / 10  # A
                self.BAT_DISCHARGE_I_LIM = hex2num(self.BAT_DISCHARGE_I_LIM) / 10  # A

                # print("Module A, tpdo_1, BAT_HEARTBEAT1", self.BAT_HEARTBEAT1, "BAT_SOC", self.BAT_SOC, "BAT_ACTIVE_ERR",  self.BAT_ACTIVE_ERR,
                #       "BAT_ACTIVE_WARN", self.BAT_ACTIVE_WARN, "BAT_CHARGE_I_LIM", self.BAT_CHARGE_I_LIM, "BAT_DISCHARGE_I_LIM", self.BAT_DISCHARGE_I_LIM)

                self.BAT_REMAINING_ENERGY = self.BAT_SOC * self.BAT_SOH * self.BAT_INITIAL_CAPACITY * 0.0001  # kWh

                self.BAT_WATCHDOG |= 0x01

            elif self.ReceivedId == 0x101:  # tpdo_2
                self.BAT_HEARTBEAT2 = self.ReceivedDatas[0]
                self.BAT_SOH = self.ReceivedDatas[1] / 2  # %
                self.BAT_STATUS_1 = self.ReceivedDatas[2]
                self.BAT_STATUS_2 = self.ReceivedDatas[3]
                self.BAT_VOLTAGE = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.BAT_CURRENT = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.BAT_VOLTAGE = hex2num(self.BAT_VOLTAGE) / 10  # V
                self.BAT_CURRENT = i16(hex2num(self.BAT_CURRENT)) / 10  # A

                # print("Module A, tpdo_2, BAT_HEARTBEAT2", self.BAT_HEARTBEAT2, "BAT_SOH", self.BAT_SOH, "BAT_STATUS_1", self.BAT_STATUS_1,
                #       "BAT_STATUS_2", self.BAT_STATUS_2, "BAT_VOLTAGE", self.BAT_VOLTAGE, "BAT_CURRENT", self.BAT_CURRENT)

                # Boolean Status
                self.BMS_OK = self.BAT_STATUS_1 & 0x01
                self.BMS_IDLE = self.BAT_STATUS_1 & 0x02
                self.BMS_CHARGE = self.BAT_STATUS_1 & 0x04
                self.BMS_DISCHARGE = self.BAT_STATUS_1 & 0x08
                self.BAT_FULL = self.BAT_STATUS_2 & 0x01  # bit0: 0 bat not full, 1 bat full
                # print("BMS_OK", self.BMS_OK, "BMS_IDLE", self.BMS_IDLE, "BMS_CHARGE", self.BMS_CHARGE,
                #       "BMS_DISCHARGE", self.BMS_DISCHARGE, "BAT_FULL", self.BAT_FULL)

                self.BAT_POWER = self.BAT_VOLTAGE * self.BAT_CURRENT / 1000  # kW

                self.BAT_WATCHDOG |= 0x02

            elif self.ReceivedId == 0x102:  # tpdo_3
                self.CELL_V_MIN = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1]]).hex()
                self.CELL_V_MIN_ID = bytes([self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.CELL_V_MAX = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.CELL_V_MAX_ID = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.CELL_V_MIN = hex2num(self.CELL_V_MIN) / 1000  # V
                self.CELL_V_MAX = hex2num(self.CELL_V_MAX) / 1000  # V

                # print("Module A, tpdo_3, CELL_V_MIN", self.CELL_V_MIN, "CELL_V_MIN_ID", self.CELL_V_MIN_ID,
                #       "CELL_V_MAX", self.CELL_V_MAX, "CELL_V_MAX_ID", self.CELL_V_MAX_ID)

                self.BAT_WATCHDOG |= 0x04

            elif self.ReceivedId == 0x103:  # tpdo_4
                self.BAT_T_MIN = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1]]).hex()
                self.BAT_T_MEAN = bytes([self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.BAT_T_MAX = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.BAT_T_MIN_ID = self.ReceivedDatas[6]
                self.BAT_T_MAX_ID = self.ReceivedDatas[7]

                self.BAT_T_MIN = i16(hex2num(self.BAT_T_MIN)) / 10  # °C
                self.BAT_T_MEAN = i16(hex2num(self.BAT_T_MEAN)) / 10  # °C
                self.BAT_T_MAX = i16(hex2num(self.BAT_T_MAX)) / 10  # °C

                # print("Module A, tpdo_4, BAT_T_MIN", self.BAT_T_MIN, "BAT_T_MEAN", self.BAT_T_MEAN, "BAT_T_MAX", self.BAT_T_MAX,
                #       "BAT_T_MIN_ID", self.BAT_T_MIN_ID, "BAT_T_MAX_ID", self.BAT_T_MAX_ID)

                self.BAT_WATCHDOG |= 0x08

            elif self.ReceivedId == 0x104:  # tpdo_5
                self.BAT_STATE_CHARGING = self.ReceivedDatas[0]
                self.BAT_STATE_DISCHARGING = self.ReceivedDatas[1]
                self.BAT_STATE_CONTACTOR_1 = self.ReceivedDatas[2]
                self.BAT_STATE_CONTACTOR_2 = self.ReceivedDatas[3]
                self.BAT_STATE_CONTACTOR_3 = self.ReceivedDatas[4]
                self.BAT_STATE_CONTACTOR_4 = self.ReceivedDatas[5]
                self.BAT_STATE_BALANCING = self.ReceivedDatas[6]
                self.GPIO = self.ReceivedDatas[7]

                # print("Module A, tpdo_5, BAT_STATE_CHARGING", self.BAT_STATE_CHARGING, "BAT_STATE_DISCHARGING", self.BAT_STATE_DISCHARGING,
                #       "BAT_STATE_CONTACTOR_1", self.BAT_STATE_CONTACTOR_1, "BAT_STATE_CONTACTOR_2", self.BAT_STATE_CONTACTOR_2,
                #       "BAT_STATE_CONTACTOR_3", self.BAT_STATE_CONTACTOR_3, "BAT_STATE_CONTACTOR_4", self.BAT_STATE_CONTACTOR_4,
                #       "BAT_STATE_BALANCING", self.BAT_STATE_BALANCING, "GPIO", self.GPIO)

                # Boolean Status
                self.BAT_IO_1 = self.GPIO & 0x01
                self.BAT_IO_2 = self.GPIO & 0x02
                self.BAT_IO_3 = self.GPIO & 0x04
                self.BAT_IO_4 = self.GPIO & 0x08
                self.BAT_IO_5 = self.GPIO & 0x10

                # print("BAT_IO_1", self.BAT_IO_1, "BAT_IO_2", self.BAT_IO_2, "BAT_IO_3", self.BAT_IO_3, "BAT_IO_4", self.BAT_IO_4, "BAT_IO_5", self.BAT_IO_5)

                self.BAT_WATCHDOG |= 0x10

            elif self.ReceivedId == 0x105:  # tpdo_6
                self.BAT_FLAGS_ERR = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1], self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.BAT_FLAGS_WARN = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5], self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()
                # Errors/Warning share same codes: 1...17, 19, 20, 25, 31
                # Active bit position -> code number

                self.BAT_FLAGS_ERR = hex2num(self.BAT_FLAGS_ERR)
                self.BAT_FLAGS_WARN = hex2num(self.BAT_FLAGS_WARN)

                # print("Module A, tpdo_6, BAT_FLAGS_ERR", self.BAT_FLAGS_ERR, "BAT_FLAGS_WARN", self.BAT_FLAGS_WARN)

                self.BAT_WATCHDOG |= 0x20

            elif self.ReceivedId == 0x110:  # rsdo_1
                print("Module A, rsdo_1")
            elif self.ReceivedId == 0x111:  # rsdo_2
                print("Module A, rsdo_2")
            elif self.ReceivedId == 0x112:  # rsdo_3
                print("Module A, rsdo_3")

        if self.ReceivedId >= 0x200 and self.ReceivedId <= 0x212:
            if self.ReceivedId == 0x200:  # rpdo_1
                print("Module A, rpdo_1")
            elif self.ReceivedId == 0x210:  # psdo_1
                print("Module A, psdo_1")
            elif self.ReceivedId == 0x211:  # psdo_2
                print("Module A, psdo_2")
            elif self.ReceivedId == 0x212:  # psdo_3
                print("Module A, psdo_3")

        if self.BAT_WATCHDOG_FLAG == 1:
            self.BAT_ACTIVE_ERR = 32
            self.BAT_FLAGS_ERR |= 0x80000000

        # self.LeclancheStatus()    # called in main program, even when no can message received (watchdogs...)
                                    # and for better processing efficiency

    def LeclancheStatus(self):
        """
        Set status text and color about battery module
        See Leclanché document tables
        Initialisations
        self.BAT_STATUS_TEXT = ''
        self.BAT_STATUS_COLOR = 'RED'  # GREEN, ORANGE, RED
        
        A test with 2 modules is ok for B but A have anormal alternating status:
        BATTERY A status modification:  State Of Health < 80%
        BATTERY A status modification: BMS OK, DISCHARGING
        ....
        BATTERY A status modification: BMS OK
        BATTERY A status modification: BMS OK, DISCHARGING
        ....
        BATTERY A status modification: , BAT FULL, DISCHARGING
        BATTERY A status modification: BMS OK, DISCHARGING
        """
        self.BAT_STATUS_TEXT = ''

        # Error
        if self.BAT_ACTIVE_ERR != 0 or self.BAT_SOH < 80:
            self.BAT_STATUS_TEXT = 'ERROR ' + self.Leclanche_Err_Warn_table(self.BAT_ACTIVE_ERR)
            if self.BAT_SOH < 80 and self.BAT_WATCHDOG_FLAG == 0:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ' State Of Health < 80%'
            # print("self.BAT_STATUS_TEXT erreur", self.BAT_STATUS_TEXT)
            self.BAT_STATUS_COLOR = 'RED'

        # Warning
        elif self.BAT_ACTIVE_WARN != 0 or self.BAT_SOH < 82:
            self.BAT_STATUS_TEXT = 'WARNING ' + self.Leclanche_Err_Warn_table(self.BAT_ACTIVE_WARN)
            if self.BAT_SOH < 82:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ' State Of Health < 82%'
            # print("self.BAT_STATUS_TEXT warning", self.BAT_STATUS_TEXT)
            self.BAT_STATUS_COLOR = 'ORANGE'

        # Info
        else:
            self.BAT_STATUS_TEXT = 'INFO'
            if self.BMS_OK > 0:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', BMS OK'
            if self.BMS_IDLE > 0:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', BMS IDLE'
            # if self.BMS_CHARGE > 0:
            #     self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', CHARGE'
            # if self.BMS_DISCHARGE > 0:
            #     self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', DISCHARGE'
            if self.BAT_FULL > 0:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', BAT FULL'
            if self.BAT_STATE_CHARGING > 0:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', CHARGING'
            if self.BAT_STATE_DISCHARGING > 0:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', DISCHARGING'
            if self.BAT_STATE_BALANCING > 0:
                self.BAT_STATUS_TEXT = self.BAT_STATUS_TEXT + ', BALANCING'
            # print("self.BAT_STATUS_TEXT info", self.BAT_STATUS_TEXT)
            self.BAT_STATUS_COLOR = 'GREEN'

    def Leclanche_Err_Warn_table(self, code):
        """
        Return text for highest error/warning code (or for one specific flag weight to filter first)
        """
        if code == 0:
            description = ''
        elif code == 1:
            description = 'Cell voltage below limit'
        elif code == 2:
            description = 'Cell voltage above limit'
        elif code == 3:
            description = 'Discharge current above limit'
        elif code == 4:
            description = 'Charge current above limit'
        elif code == 5:
            description = 'Module temperature below limit'
        elif code == 6:
            description = 'Module temperature above limit'
        elif code == 7:
            description = 'Cell Voltage Difference'
        elif code == 8:
            description = 'Module Temperature Difference'
        elif code == 9:
            description = 'Cell Voltage Sum / Stack Voltage Difference'
        elif code == 10:
            description = 'Sensor Fault'
        elif code == 11:
            description = 'Precharge timeout'
        elif code == 12:
            description = 'Contactor Fault'
        elif code == 13:
            description = 'Isolation Fault'
        elif code == 15:
            description = 'Watchdog Reset Activated'
        elif code == 16:
            description = 'Emergency Stop Active'
        elif code == 17:
            description = 'BMU Communication Timeout'
        elif code == 19:
            description = 'FW Initialization Error'
        elif code == 20:
            description = 'Input alarm activated (Requires GPIO Configuration)'
        elif code == 25:
            description = 'CAN Host Timeout'
        elif code == 31:
            description = 'Software Error'
        elif code == 32:
            description = 'CAN SOFTWARE WATCHDOG'
        else:
            description = 'Unknow Error/Warning code'

        return description

    def MpptInit(self):
        """
        MPPT modules variables initialisations
        Arrays of 28 values, which index 0-27 is MPPT converter identifier
        """
        self.MPPT_NOMBRE = 10  # MPPTs modules connected on CAN bus (max 28, with consecutive identifiers strating at 0)
        self.MPPT_ID = -1  # actual processed ID (array index)

        self.MPPT_ERR = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.MPPT_WARN = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

        self.MPPT_IN_V = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.MPPT_IN_A = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.MPPT_IN_W = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.MPPT_T1 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

        self.MPPT_V = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.MPPT_A = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.MPPT_W = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.MPPT_T2 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

        # calculated or analysed:
        # self.MPPT_STATUS_TEXT = ''
        self.MPPT_STATUS_COLOR = 'RED'  # GREEN, ORANGE, RED
        self.MPPT_WATCHDOG = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]  # periodic sum for each MPPT module: valid watchdog is 0x07
        self.MPPT_WATCHDOG_FLAG = 1
        self.MPPT_ERR[0] |= 0x80000000

    def MpptDecode(self):
        """
        Message identification from CAN ID,
        Set values according to ID and "SPET pilot control system" document tables
        function decode <-- status <-- table
        Called with each received CAN message
        """
        if self.ReceivedId >= 0x155 and self.ReceivedId <= 0x1A9:
            self.MPPT_ID = (self.ReceivedId - 0x155) // 3  # floor division with "//"

            # messages 0,1,2 with CAN_ID - 0x155 - 3*ID :
            if self.ReceivedId - 0x155 - 3*self.MPPT_ID == 0:
                self.MPPT_ERR[self.MPPT_ID] = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1], self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.MPPT_WARN[self.MPPT_ID] = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5], self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()
                self.MPPT_ERR[self.MPPT_ID] = hex2num(self.MPPT_ERR[self.MPPT_ID])
                self.MPPT_WARN[self.MPPT_ID] = hex2num(self.MPPT_WARN[self.MPPT_ID])

                self.MPPT_WATCHDOG[self.MPPT_ID] |= 0x01

            if self.ReceivedId - 0x155 - 3*self.MPPT_ID == 1:
                self.MPPT_IN_V[self.MPPT_ID] = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1]]).hex()
                self.MPPT_IN_A[self.MPPT_ID] = bytes([self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.MPPT_IN_W[self.MPPT_ID] = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.MPPT_T1[self.MPPT_ID] = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.MPPT_IN_V[self.MPPT_ID] = hex2num(self.MPPT_IN_V[self.MPPT_ID]) / 100  # V
                self.MPPT_IN_A[self.MPPT_ID] = hex2num(self.MPPT_IN_A[self.MPPT_ID]) / 1000  # A
                self.MPPT_IN_W[self.MPPT_ID] = hex2num(self.MPPT_IN_W[self.MPPT_ID]) / 100  # W
                self.MPPT_T1[self.MPPT_ID] = i16(hex2num(self.MPPT_T1[self.MPPT_ID])) / 100  # °C

                self.MPPT_WATCHDOG[self.MPPT_ID] |= 0x02

            if self.ReceivedId - 0x155 - 3*self.MPPT_ID == 2:
                self.MPPT_V[self.MPPT_ID] = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1]]).hex()
                self.MPPT_A[self.MPPT_ID] = bytes([self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.MPPT_W[self.MPPT_ID] = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.MPPT_T2[self.MPPT_ID] = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.MPPT_V[self.MPPT_ID] = hex2num(self.MPPT_V[self.MPPT_ID]) / 100  # V
                self.MPPT_A[self.MPPT_ID] = hex2num(self.MPPT_A[self.MPPT_ID]) / 1000  # A
                self.MPPT_W[self.MPPT_ID] = hex2num(self.MPPT_W[self.MPPT_ID]) / 100  # W
                self.MPPT_T2[self.MPPT_ID] = i16(hex2num(self.MPPT_T2[self.MPPT_ID])) / 100  # °C

                self.MPPT_WATCHDOG[self.MPPT_ID] |= 0x04

        if self.MPPT_WATCHDOG_FLAG == 1:
            self.MPPT_ERR[0] |= 0x80000000  # no need to set them all, because status get the max...

        # self.MpptStatus() # called in main program, even when no can message received (watchdogs...)
                            # and for better processing efficiency

    def MpptStatus(self):
        """
        Set status text and color about MPPT modules
        See "SPET pilot control system" document tables
        Initialisations as for battery modules
        "Max" to get priority message between all modules
        """
        self.MPPT_STATUS_TEXT = ''

        # Error
        if max(self.MPPT_ERR) != 0:
            self.MPPT_STATUS_TEXT = 'ERROR ' + self.Mppt_Err_table(max(self.MPPT_ERR))
            # print("self.MPPT_STATUS_TEXT erreur", self.MPPT_STATUS_TEXT)
            self.MPPT_STATUS_COLOR = 'RED'

        # Warning
        elif max(self.MPPT_WARN) != 0:
            self.MPPT_STATUS_TEXT = 'WARNING ' + self.Mppt_Warn_table(max(self.MPPT_WARN))
            # print("self.MPPT_STATUS_TEXT warning", self.MPPT_STATUS_TEXT)
            self.MPPT_STATUS_COLOR = 'ORANGE'

        # Info
        else:
            self.MPPT_STATUS_TEXT = 'INFO, MPPT OK'
            # print("self.MPPT_STATUS_TEXT info", self.MPPT_STATUS_TEXT)
            self.MPPT_STATUS_COLOR = 'GREEN'

    def Mppt_Err_table(self, code):
        """
        Return text for highest code
        """
        description = ''
        if code & 0x80000000 != 0:
            description = 'CAN SOFTWARE WATCHDOG'
        elif code & 0x100 != 0:
            description = 'error 9'
        elif code & 0x80 != 0:
            description = 'error 8'
        elif code & 0x40 != 0:
            description = 'error 7'
        elif code & 0x20 != 0:
            description = 'error 6'
        elif code & 0x10 != 0:
            description = 'error 5'
        elif code & 0x8 != 0:
            description = 'error 4'
        elif code & 0x4 != 0:
            description = 'error 3'
        elif code & 0x2 != 0:
            description = 'error 2'
        elif code & 0x1 != 0:
            description = 'error 1'
        else:
            description = 'Unknow Error code'

        return description

    def Mppt_Warn_table(self, code):
        """
        Return text for highest code
        """
        description = ''
        if code & 0x80000000 != 0:
            description = 'warning 32'
        elif code & 0x100 != 0:
            description = 'warning 9'
        elif code & 0x80 != 0:
            description = 'warning 8'
        elif code & 0x40 != 0:
            description = 'warning 7'
        elif code & 0x20 != 0:
            description = 'warning 6'
        elif code & 0x10 != 0:
            description = 'warning 5'
        elif code & 0x8 != 0:
            description = 'warning 4'
        elif code & 0x4 != 0:
            description = 'warning 3'
        elif code & 0x2 != 0:
            description = 'warning 2'
        elif code & 0x1 != 0:
            description = 'warning 1'
        else:
            description = 'Unknow Warning code'

        return description

    def DriveInit(self):
        """
        Drive module variables initialisations
        """
        self.DRIVE_ERR = 0
        self.DRIVE_WARN = 0

        self.DRIVE_MOTOR_MECA_POWER = 0
        self.DRIVE_ELEC_POWER = 0

        self.DRIVE_MOTOR_CURRENT_U = 0
        self.DRIVE_MOTOR_CURRENT_V = 0
        self.DRIVE_MOTOR_CURRENT_W = 0
        self.DRIVE_DC_BUS_V = 0

        self.DRIVE_MOTOR_TORQUE = 0
        self.DRIVE_MOTOR_SPEED = 0  # rpm

        self.DRIVE_MOTOR_POSITION = 0
        self.DRIVE_POWER_ORDER = 0  # %
        self.DRIVE_RESERVED1 = 0
        self.DRIVE_POWER_LEVER = 0  # %

        self.DRIVE_HOURS = 0
        self.DRIVE_PCB_TEMP = 0  # °C
        self.DRIVE_MOTOR_TEMP = 0  # °C

        self.DRIVE_SIC_U_TEMP = 0
        self.DRIVE_SIC_V_TEMP = 0
        self.DRIVE_SIC_W_TEMP = 0
        self.DRIVE_RESERVED2 = 0

        # states 0x00/0xFF
        self.DRIVE_INPUT_0 = 0
        self.DRIVE_INPUT_1 = 0
        self.DRIVE_INPUT_2 = 0
        self.DRIVE_INPUT_3 = 0
        self.DRIVE_OUTPUT_0 = 0
        self.DRIVE_OUTPUT_1 = 0
        self.DRIVE_OUTPUT_2 = 0
        self.DRIVE_OUTPUT_3 = 0

        # 4-20mA
        self.DRIVE_ANALOG_INPUT_1 = 0
        self.DRIVE_ANALOG_INPUT_2 = 0

        # calculated or analysed:
        # self.DRIVE_STATUS_TEXT = ''
        self.DRIVE_STATUS_COLOR = 'RED'  # GREEN, ORANGE, RED
        self.DRIVE_WATCHDOG = 0  # periodic sum: valid watchdog is 0x1FF
        self.DRIVE_WATCHDOG_FLAG = 1
        self.DRIVE_ERR |= 0x80000000

    def DriveDecode(self):
        """
        Message identification from CAN ID,
        Set values according to ID and "SPET pilot control system" document tables
        function decode <-- status <-- table
        Called with each received CAN message
        """
        if self.ReceivedId >= 0x1AA and self.ReceivedId <= 0x1FF:
            if self.ReceivedId == 0x1AA:
                self.DRIVE_ERR = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1], self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_WARN = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5], self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_ERR = hex2num(self.DRIVE_ERR)
                self.DRIVE_WARN = hex2num(self.DRIVE_WARN)

                self.DRIVE_WATCHDOG |= 0x01
            elif self.ReceivedId == 0x1AB:
                self.DRIVE_MOTOR_MECA_POWER = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1], self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_ELEC_POWER = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5], self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_MOTOR_MECA_POWER = hex2float(self.DRIVE_MOTOR_MECA_POWER)  # W
                self.DRIVE_ELEC_POWER = hex2float(self.DRIVE_ELEC_POWER)  # W

                self.DRIVE_WATCHDOG |= 0x02
            elif self.ReceivedId == 0x1AC:
                self.DRIVE_MOTOR_CURRENT_U = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1]]).hex()
                self.DRIVE_MOTOR_CURRENT_V = bytes([self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_MOTOR_CURRENT_W = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.DRIVE_DC_BUS_V = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_MOTOR_CURRENT_U = i16(hex2num(self.DRIVE_MOTOR_CURRENT_U)) / 100  # Arms
                self.DRIVE_MOTOR_CURRENT_V = i16(hex2num(self.DRIVE_MOTOR_CURRENT_V)) / 100  # Arms
                self.DRIVE_MOTOR_CURRENT_W = i16(hex2num(self.DRIVE_MOTOR_CURRENT_W)) / 100  # Arms
                self.DRIVE_DC_BUS_V = hex2num(self.DRIVE_DC_BUS_V) / 100  # Vdc

                self.DRIVE_WATCHDOG |= 0x04
            elif self.ReceivedId == 0x1AD:
                self.DRIVE_MOTOR_MOTOR_TORQUE = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1], self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_MOTOR_SPEED = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5], self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_MOTOR_MOTOR_TORQUE = hex2float(self.DRIVE_MOTOR_MOTOR_TORQUE)  # N.m
                self.DRIVE_MOTOR_SPEED = hex2float(self.DRIVE_MOTOR_SPEED)  # rpm

                self.DRIVE_WATCHDOG |= 0x08
            elif self.ReceivedId == 0x1AE:
                self.DRIVE_MOTOR_POSITION = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1]]).hex()
                self.DRIVE_POWER_ORDER = bytes([self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_RESERVED1 = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.DRIVE_POWER_LEVER = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_MOTOR_POSITION = hex2num(self.DRIVE_MOTOR_POSITION) / 100  # °
                self.DRIVE_POWER_ORDER = hex2num(self.DRIVE_POWER_ORDER) / 100  # %
                self.DRIVE_RESERVED1 = hex2num(self.DRIVE_RESERVED1)
                self.DRIVE_POWER_LEVER = hex2num(self.DRIVE_POWER_LEVER) / 100  # %

                self.DRIVE_WATCHDOG |= 0x10
            elif self.ReceivedId == 0x1AF:
                self.DRIVE_HOURS = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1], self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_PCB_TEMP = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.DRIVE_MOTOR_TEMP = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_HOURS = hex2float(self.DRIVE_HOURS)
                self.DRIVE_PCB_TEMP = i16(hex2num(self.DRIVE_PCB_TEMP)) / 100  # °C
                self.DRIVE_MOTOR_TEMP = i16(hex2num(self.DRIVE_MOTOR_TEMP)) / 100  # °C

                self.DRIVE_WATCHDOG |= 0x20
            elif self.ReceivedId == 0x1B0:
                self.DRIVE_SIC_U_TEMP = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1]]).hex()
                self.DRIVE_SIC_V_TEMP = bytes([self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_SIC_W_TEMP = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5]]).hex()
                self.DRIVE_RESERVED2 = bytes([self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_SIC_U_TEMP = i16(hex2num(self.DRIVE_SIC_U_TEMP)) / 100  # °C
                self.DRIVE_SIC_V_TEMP = i16(hex2num(self.DRIVE_SIC_V_TEMP)) / 100  # °C
                self.DRIVE_SIC_W_TEMP = i16(hex2num(self.DRIVE_SIC_W_TEMP)) / 100  # °C
                self.DRIVE_RESERVED2 = hex2num(self.DRIVE_RESERVED2)

                self.DRIVE_WATCHDOG |= 0x40
            elif self.ReceivedId == 0x1B1:
                self.DRIVE_INPUT_0 = self.ReceivedDatas[0]  # 0x00/0xFF
                self.DRIVE_INPUT_1 = self.ReceivedDatas[1]  # 0x00/0xFF
                self.DRIVE_INPUT_2 = self.ReceivedDatas[2]  # 0x00/0xFF
                self.DRIVE_INPUT_3 = self.ReceivedDatas[3]  # 0x00/0xFF
                self.DRIVE_OUTPUT_0 = self.ReceivedDatas[4]  # 0x00/0xFF
                self.DRIVE_OUTPUT_1 = self.ReceivedDatas[5]  # 0x00/0xFF
                self.DRIVE_OUTPUT_2 = self.ReceivedDatas[6]  # 0x00/0xFF
                self.DRIVE_OUTPUT_3 = self.ReceivedDatas[7]  # 0x00/0xFF

                self.DRIVE_WATCHDOG |= 0x80
            elif self.ReceivedId == 0x1B2:
                self.DRIVE_ANALOG_INPUT_1 = bytes([self.ReceivedDatas[0], self.ReceivedDatas[1], self.ReceivedDatas[2], self.ReceivedDatas[3]]).hex()
                self.DRIVE_ANALOG_INPUT_2 = bytes([self.ReceivedDatas[4], self.ReceivedDatas[5], self.ReceivedDatas[6], self.ReceivedDatas[7]]).hex()

                self.DRIVE_ANALOG_INPUT_1 = hex2float(self.DRIVE_ANALOG_INPUT_1)  # 4-20mA
                self.DRIVE_ANALOG_INPUT_2 = hex2float(self.DRIVE_ANALOG_INPUT_2)  # 4-20mA

                self.DRIVE_WATCHDOG |= 0x100

        if self.DRIVE_WATCHDOG_FLAG == 1:  # checked and set back after each CAN message, and also in main program ("CAN_Watchdogs")
            self.DRIVE_ERR |= 0x80000000

        # self.DriveStatus()  # called in main program, even when no can message received (watchdogs...)
                              # and for better processing efficiency

    def DriveStatus(self):
        """
        Set status text and color about DRIVE MOTEUR modules
        See "SPET pilot control system" document tables
        Initialisations as for battery modules
        """
        self.DRIVE_STATUS_TEXT = ''

        # Error
        if self.DRIVE_ERR != 0:
            self.DRIVE_STATUS_TEXT = 'ERROR ' + self.Drive_Err_table(self.DRIVE_ERR)
            # print("self.DRIVE_STATUS_TEXT erreur", self.DRIVE_STATUS_TEXT)
            self.DRIVE_STATUS_COLOR = 'RED'

        # Warning
        elif self.DRIVE_WARN != 0:
            self.DRIVE_STATUS_TEXT = 'WARNING ' + self.Drive_Warn_table(self.DRIVE_WARN)
            # print("self.DRIVE_STATUS_TEXT warning", self.DRIVE_STATUS_TEXT)
            self.DRIVE_STATUS_COLOR = 'ORANGE'

        # Info
        else:
            self.DRIVE_STATUS_TEXT = 'INFO DRIVE OK'
            # print("self.DRIVE_STATUS_TEXT info", self.DRIVE_STATUS_TEXT)
            self.DRIVE_STATUS_COLOR = 'GREEN'

    def Drive_Err_table(self, code):
        """
        Return text for highest code
        """
        description = ''
        if code & 0x80000000 != 0:
            description = 'CAN SOFTWARE WATCHDOG'
        elif code & 0x100 != 0:
            description = 'error 9'
        elif code & 0x80 != 0:
            description = 'error 8'
        elif code & 0x40 != 0:
            description = 'error 7'
        elif code & 0x20 != 0:
            description = 'error 6'
        elif code & 0x10 != 0:
            description = 'error 5'
        elif code & 0x8 != 0:
            description = 'error 4'
        elif code & 0x4 != 0:
            description = 'error 3'
        elif code & 0x2 != 0:
            description = 'error 2'
        elif code & 0x1 != 0:
            description = 'error 1'
        else:
            description = 'Unknow Error code'

        return description

    def Drive_Warn_table(self, code):
        """
        Return text for highest code
        """
        description = ''
        if code & 0x80000000 != 0:
            description = 'warning 32'
        elif code & 0x100 != 0:
            description = 'warning 9'
        elif code & 0x80 != 0:
            description = 'warning 8'
        elif code & 0x40 != 0:
            description = 'warning 7'
        elif code & 0x20 != 0:
            description = 'warning 6'
        elif code & 0x10 != 0:
            description = 'warning 5'
        elif code & 0x8 != 0:
            description = 'warning 4'
        elif code & 0x4 != 0:
            description = 'warning 3'
        elif code & 0x2 != 0:
            description = 'warning 2'
        elif code & 0x1 != 0:
            description = 'warning 1'
        else:
            description = 'Unknow Warning code'

        return description