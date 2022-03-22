"""
Genesys-Python-Library: control TDK-Lambda™ Genesys™ power supplies programmatically via Python™

    "TDK", "TDK-Lambda" & "Genesys" are registered trademarks of the TDK Corporation.
    "Python" is a registered trademark of the Python Software Foundation.
    pySerial Copyrighted by Chris Liechti.
    pytest Copyrighted by Holger Krekel and pytest-dev team.
    This script Copyright Amphenol Borisch Technologies, 2022
    - https://www.borisch.com/

    Genesys class.
"""
import re
import time
import serial # https://pypi.org/project/pyserial/ & https://pyserial.readthedocs.io/en/latest/pyserial.html

class Genesys(object):
    """ Class to programmatically control TDK-Lambda Genesys Power Supplies via their serial ports.
        - Reference  Genesys Manual 'TDK-Lambda Genesys Power Supplies User Manual, 83-507-013', especially Chapter 7, 'RS232 & RS485 Remote Control'
           - https://product.tdk.com/system/files/dam/doc/product/power/switching-power/prg-power/instruction_manual/gen1u-750-1500w_user_manual.pdf
        - Requires pySerial library:
          - https://pypi.org/project/pyserial/
          - https://pyserial.readthedocs.io/en/latest/pyserial.html
    """
    listening_addresses = {}
    ADDRESS_RANGE = range(0, 31, 1)
    BAUD_RATES = (1200, 2400, 4800, 9600, 19200)
    FORMAT = '{0:.3f}' # 3.3 format works for VOL, CUR, OVP & UVL for all Genesys models.

    # Genesys Manual Table 7.6.
    OVPs = {'GEN6-XY'    : {'min': 0.500, 'MAX':    7.500},
            'GEN8-XY'    : {'min': 0.500, 'MAX':   10.000},
            'GEN12.5-XY' : {'min': 1.000, 'MAX':   15.000},
            'GEN20-XY'   : {'min': 1.000, 'MAX':   24.000},
            'GEN30-XY'   : {'min': 2.000, 'MAX':   36.000},
            'GEN40-XY'   : {'min': 2.000, 'MAX':   44.000},
            'GEN60-XY'   : {'min': 5.000, 'MAX':   66.000},
            'GEN80-XY'   : {'min': 5.000, 'MAX':   88.000},
            'GEN100-XY'  : {'min': 5.000, 'MAX':  110.000},
            'GEN150-XY'  : {'min': 5.000, 'MAX':  165.000},
            'GEN300-XY'  : {'min': 5.000, 'MAX':  330.000},
            'GEN600-XY'  : {'min': 5.000, 'MAX':  660.000}}

    # Genesys Manual Table 7.7.  UVL['MAX'] ≈  95% * VOL['MAX'].
    UVLs = {'GEN6-XY'    : {'min': 0.000, 'MAX':    5.700},
            'GEN8-XY'    : {'min': 0.000, 'MAX':    7.600},
            'GEN12.5-XY' : {'min': 0.000, 'MAX':   11.900},
            'GEN20-XY'   : {'min': 0.000, 'MAX':   19.000},
            'GEN30-XY'   : {'min': 0.000, 'MAX':   28.500},
            'GEN40-XY'   : {'min': 0.000, 'MAX':   38.000},
            'GEN60-XY'   : {'min': 0.000, 'MAX':   57.000},
            'GEN80-XY'   : {'min': 0.000, 'MAX':   76.000},
            'GEN100-XY'  : {'min': 0.000, 'MAX':   95.000},
            'GEN150-XY'  : {'min': 0.000, 'MAX':  142.000},
            'GEN300-XY'  : {'min': 0.000, 'MAX':  285.000},
            'GEN600-XY'  : {'min': 0.000, 'MAX':  570.000}}

    def __init__(self, address: int, serial_port: serial) -> None:
        """ Initializer for Genesys class
            Inputs:        - address: int, address of TDK-Lambda GEN Power Supply
                           - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies
            Outputs:       None
            GEN commands:  RMT LLO
            Nuances:       - 'RMT LLO' disables Genesys front-panel operator controls:
                             - Prevents all operator interference/intervention, apart from powering Genesys off.
                             - Permits only programmatic control of the Genesys supply.
                           - Initializer __init__() deliberately doesn't issue any other Genesys commands:
                             - Instantiating a Genesys object literally only establishes communication with it.
                             - Whatever prior state a Genesys has before __init__() executes remains entirely intact after execution.
                             - Use Genesys class methods to change Genesys states.
                             - Use Genesys.configure() to configure Genesys with power off, voltage/amperage zeroed and options disabled.
        """
        Genesys.validate_address(address)
        if serial_port.baudrate not in Genesys.BAUD_RATES:
            raise ValueError('Invalid Baud Rate, must be in list ' + str(Genesys.BAUD_RATES) + '.')
        self.serial_port = serial_port
        self.timeout = serial_port.timeout
        self.address = address                           # Integer in range [0..30]
        self.last_command = ''                           # self.last_command updated by ._write_command_read_response.
        self.last_response = ''                          # self.last_response updated by ._write_command_read_response.
        self.set_remote_mode('LLO')                      # Disable Genesys front panel controls; permit only programmatic control henceforth.
        idn = self.get_identity()                        # Assuming idn ='Lambda, GEN40-38'
        idn = idn[idn.index('GEN') + 3 :]                # idn = '40-38'
        v = idn[: idn.index('-')]                        # v = '40'
        a = idn[idn.index('-') + 1 :]                    # a = '38'
        self.VOL = {'min':0.000, 'MAX':float(v)}         # self.VOL = {'min': 0.000, 'MAX': 40.000}
        self.CUR = {'min':0.000, 'MAX':float(a)}         # self.CUR = {'min': 0.000, 'MAX': 38.000}
        idn = 'GEN{}-XY'.format(v)                       # idn = 'GEN40-XY'
        self.OVP = Genesys.OVPs[idn]                     # self.OVP = {'min': 0.800, 'MAX': 44.000}
        self.UVL = Genesys.UVLs[idn]                     # self.UVL = {'min': 0.000, 'MAX': 38.000}
        return None

    def __str__(self) -> str:
        """ Printable string representation for Genesys class
            Inputs:        None
            Outputs:       str, GEN Identification
            GEN command:   IDN?
        """
        return self.get_identity()

    @staticmethod
    def validate_address(address: int) -> None:
        if type(address) != int:
            raise TypeError('Invalid Address, must be an integer.')
        if address not in Genesys.ADDRESS_RANGE:
            raise ValueError('Invalid Address, must be in range ' + str(Genesys.ADDRESS_RANGE) + '.')
        return None

    def clear_status(self) -> None:
        """ Sets GEN FEVE & SEVE registers to 0
            Inputs:       None
            Outputs:      None
            GEN command:  CLS
        """
        self.command_imperative('CLS')
        return None

    def reset(self) -> None:
        """ Reset command; brings GEN supply to a safe and known state
            Inputs:       None
            Outputs:      None
            GEN command:  RST
            Altered states:
            1) Output voltage: 0
            2) Output current: 0
            3) Output: OFF
            4) Auto-start: OFF
            5) Remote: REM
            6) OVP: maximum
            7) UVL: 0
            8) FOLD: OFF
            9) The FLT & STAT Condition registers are updated, other registers are not changed
        """
        self.command_imperative('RST')
        return None

    def set_remote_mode(self, mode: str) -> None:
        """ Programs GEN Remote state
            Inputs:        mode: str in ('LOC', 'REM', 'LLO')
            Outputs:       None
            GEN commands:  RMT {mode}
        """
        if type(mode) != str:
            raise TypeError('Invalid Remote Mode, must be a str.')
        mode = mode.upper()
        if mode not in ('LOC', 'REM', 'LLO'):
            raise ValueError('Invalid Remote Mode, must be in (''LOC'', ''REM'', ''LLO'').')
        self.command_imperative('RMT {}'.format(mode))
        return None

    def get_remote_mode(self) -> str:
        """ Reads GEN Remote latched mode
            Inputs:       None
            Outputs:      mode: str in ('LOC', 'REM', 'LLO')
            GEN command:  RMT?
        """
        return self.command_interrogative('RMT?')

    def multi_drop_installed(self) -> bool:
        """ Reads GEN Multi-drop option installed
            Inputs:       None
            Outputs:      bool, False if Multi-drop not installed, True if installed
            GEN command:  MDAV?
        """
        return self.command_interrogative('MDAV?') == 1

    def get_ms_parallel_operation(self) -> str:
        """ Reads GEN ms parallel operation
            Inputs:       None
            Outputs:      int: in (0, 1, 2, 3, 4)
            GEN command:  MS?
        """
        return self.command_interrogative('MS?')

    def repeat_last_command(self) -> str:
        """ Reads GEN ms parallel operation
            Inputs:       None
            Outputs:      str: response if Interrogative command, 'OK' if Imperative.
            GEN command:  \\
            Nuances:      - There's no apparent way to query Genesi supplies what they're last commands were; last commands
                            are apparently remebered internally, but inaccessibly.
                            - So, cannot know if Genesi last commands are:
                              - Interrogative, and should respond to their end-use/client applications.
                              - Imperative, and should not respond.
                            - Admittedly feeble resolution is to simply return Genesi responses regardless, and let client
                              applications handle them.
                              - This means Imperative last commands *will* return 'OK' to their client applications, unlike all other
                                methods in this library.
                              - Guessing '\\' is intended for Service Request error handling routines, where the last command
                                didn't complete correctly due to colliding with an SRQ message, so is reissued.
                            - Possible alternative implementation would be for client applications to directly access the Genesys class
                              instance variable self.last_command and directly call function self.command_interrogative() or
                              method self.command_imperative(), depending if self.last_command is Interrogative or Imperative.
        """
        return self._write_command_read_response('\\')

    def get_identity(self) -> str:
        """ Reads GEN Model info
            Inputs:       None
            Outputs:      str, GEN Identification
            GEN command:  IDN?
        """
        return self.command_interrogative('IDN?')

    def get_revision(self) -> str:
        """ Reads GEN Firmware revision
            Inputs:       None
            Outputs:      str, GEN Firmware revision
            GEN command:  REV?
        """
        return self.command_interrogative('REV?')

    def get_serial_number(self) -> str:
        """ Reads GEN serial Number
            Inputs:       None
            Outputs:      str, GEN serial number
            GEN command:  SN?
        """
        return self.command_interrogative('SN?')

    def get_date(self) -> str:
        """ Reads GEN date of last test
            Inputs:       None
            Outputs:      str, date of last test
            GEN command:  DATE?
        """
        return self.command_interrogative('DATE?')

    def program_voltage(self, volts: float) -> None:
        """ Programs GEN voltage
            Inputs:       volts: float, desired voltage
            Outputs:      None
            GEN command:  PV {volts}
            Nuances:      - Setting Voltage is best performed by first setting UVL = UVL['min'], OVP = OVP['MAX'],
                            then setting desired Voltage, so UVL/OVP don't interfere with Voltage.
                          - Note that below inequality *always* applies between UVL, Voltage & OVP:
                            - UVL ⪅ Voltage*95% ⪅ Voltage ⪅ Voltage*105% ⪅ OVP.
                            - The ⪅ symbol denotes less than or approximately equal.
                            - The ±5% difference is approximate, possibly due to roundoff in the Genesys.
        """
        if type(volts) not in (int, float):
            raise TypeError('Invalid Voltage, must be a real number.')
        if not (self.VOL['min'] <= volts <= self.VOL['MAX']):
            raise ValueError('Invalid Voltage, must *always* be in range [{}..{}].'.format(self.VOL['min'], self.VOL['MAX']))
        if not (self.get_under_voltage_limit() / 0.95 <= volts <= self.get_over_voltage_protection() / 1.05):
            raise ValueError('Invalid Voltage, must *presently* be in range [{}..{}].'.format(self.get_under_voltage_limit() / 0.95, self.get_over_voltage_protection() / 1.05))
        volts = Genesys.FORMAT.format(volts)
        self.command_imperative('PV {}'.format(volts))
        return None

    def get_voltage_programmed(self) -> float:
        """ Reads GEN voltage, programmed
            Inputs:       None
            Outputs:      float, programmed voltage
            GEN command:  PV?
        """
        return float(self.command_interrogative('PV?'))

    def get_voltage_measured(self) -> float:
        """ Reads GEN voltage, actual
            Inputs:       None
            Outputs:      float, actual voltage
            GEN command:  MV?
        """
        return float(self.command_interrogative('MV?'))

    def program_amperage(self, amperes: float) -> None:
        """ Programs GEN amperage
            Inputs:       amperes: float, desired amperage
            Outputs:      None
            GEN command:  PC {amperes}
        """
        if type(amperes) not in (int, float):
            raise TypeError('Invalid Amperage, must be a real number.')
        if not (self.CUR['min'] <= amperes <= self.CUR['MAX']):
            raise ValueError('Invalid Amperage, must be in range [{}..{}].'.format(self.CUR['min'], self.CUR['MAX']))
        amperes = Genesys.FORMAT.format(amperes)
        self.command_imperative('PC {}'.format(amperes))
        return None

    def get_amperage_programmed(self) -> float:
        """ Reads GEN amperage, programmed
            Inputs:       None
            Outputs:      float, programmed amperage
            GEN command:  PC?
        """
        return float(self.command_interrogative('PC?'))

    def get_amperage_measured(self) -> float:
        """ Reads GEN amperage, measured
            Inputs:       None
            Outputs:      float, measured amperage
            GEN command:  MC?
        """
        return float(self.command_interrogative('MC?'))

    def get_operation_mode(self) -> str:
        """ Reads GEN operation mode, Constant Current, Constant Voltage, or Off state
            Inputs:       None
            Outputs:      str, in ('CC', 'CV', 'OFF')
            GEN command:  MODE?
        """
        return self.command_interrogative('MODE?')

    def get_voltages_currents(self) -> dict:
        """ Reads GEN Voltage Measured, Voltage Programmed, Amperage Measured, Amperage Programmed, Over Voltage & Under Voltage
            Inputs:       None
            Outputs:      dict, {'Voltage Measured'     : float,
                                 'Voltage Programmed'   : float,
                                 'Amperage Measured'    : float,
                                 'Amperage Programmed'  : float,
                                 'Over Voltage'         : float,
                                 'Under Voltage'        : float}
            GEN command:  DVC?
        """
        va = self.command_interrogative('DCV?')
        va = va.split(',')
        for i in range(0, len(va), 1): va[i] = float(va[i])
        return {'Voltage Measured'      : va[0],
                'Voltage Programmed'    : va[1],
                'Amperage Measured'     : va[2],
                'Amperage Programmed'   : va[3],
                'Over Voltage'          : va[4],
                'Under Voltage'         : va[5]}

    def get_status(self) -> str:
        """ Reads GEN complete power supply status
            Inputs:       None
            Outputs:      dict, {'Voltage Measured'      : float,
                                 'Voltage Programmed'    : float,
                                 'Amperage Measured'     : float,
                                 'Amperage Programmed'   : float,
                                 'Status Register'       : int (hex format),
                                 'Fault Register'        : int (hex format)}
            GEN command:  STT?
        """
        st = self.command_interrogative('STT?')
        st = st.lower()
        st = re.sub('[a-z() ]*', '', st)     # Remove all alpha characters, '(', ')' & ' '.
        st = st.split(',')
        return {'Voltage Measured'      :      float(st[0]),
                'Voltage Programmed'    :      float(st[1]),
                'Amperage Measured'     :      float(st[2]),
                'Amperage Programmed'   :      float(st[3]),
                'Status Register'       : format(int(st[4]),'X'),
                'Fault Register'        : format(int(st[5]),'X')}

    def set_filter_frequency(self, hertz: int) -> None:
        """ Programs GEN low-pass filter frequency of A/D Converter for voltage & current measurement
            Inputs:        hertz: int in (18, 23, 46)
            Outputs:       None
            GEN commands:  FILTER {hertz}
        """
        if type(hertz) != int:
            raise TypeError('Invalid Frequency, must be an integer.')
        if not hertz in (18, 23, 46):
            raise ValueError('Invalid Frequency, must be in (18, 23, 46)')
        self.command_imperative('FILTER {}'.format(hertz))
        return None

    def get_filter_frequency(self) -> int:
        """ Reads GEN Status
            Inputs:       None
            Outputs:      int, GEN low-pass filter frequency of A/D Converter for voltage & current measurement
            GEN command:  FILTER?
        """
        return self.command_imperative('FILTER?')

    def set_power_state(self, binary_state: str) -> None:
        """ Programs GEN Power state
            Inputs:        binary_state: str in ('ON, 'OFF')
            Outputs:       None
            GEN commands:  OUT {binary_state}
        """
        binary_state = Genesys._validate_binary_state(binary_state)
        self.command_imperative('OUT {}'.format(binary_state))
        return None

    def get_power_state(self) -> str:
        """ Reads GEN Power state
            Inputs:       None
            Outputs:      binary_state: str in ('ON, 'OFF')
            GEN command:  OUT?
        """
        return self.command_interrogative('OUT?')

    def set_foldback_state(self, binary_state: str) -> None:
        """ Programs GEN Foldback state
            Inputs:        binary_state: str in ('ON, 'OFF')
            Outputs:       None
            GEN commands:  FLD {binary_state}
        """
        binary_state = Genesys._validate_binary_state(binary_state)
        self.command_imperative('FLD {}'.format(binary_state))
        return None

    def get_foldback_state(self) -> str:
        """ Reads GEN Foldback state
            Inputs:       None
            Outputs:      binary_state: str in ('ON, 'OFF')
            GEN command:  FLD?
        """
        return self.command_interrogative('FLD?')

    def set_additional_foldback_delay(self, milli_seconds: int) -> None:
        """ Programs GEN Foldback delay, in addition to standard 250 milli-seconds
            Inputs:        int:  milli_seconds in range (0, 256, 1)
            Outputs:       None
            GEN commands:  FDB {milli_seconds}
        """
        if type(milli_seconds) != int:
            raise TypeError('Invalid Foldback Delay, must be an integer.')
        if not milli_seconds in range(0, 256, 1):
            raise ValueError('Invalid Foldback Delay, must be in range(0, 256, 1)')
        self.command_imperative('FDB {}'.format(milli_seconds))
        return None

    def get_foldback_delay(self) -> int:
        """ Reads total GEN Foldback delay, sum of programmed & standard 250 milli-seconds
            Inputs:       None
            Outputs:      int, in range(250, 506, 1)
            GEN command:  FBD?
        """
        return self.command_interrogative('FBD?')

    def reset_foldback_delay(self) -> None:
        """ Resets GEN Foldback delay to 0 + standard inalterable 250 milli-seconds
            Inputs:       None
            Outputs:      int, in range(250, 506, 1)
            GEN command:  FBDRST
        """
        self.command_imperative('FBDRST')
        return None

    def program_over_voltage_protection(self, volts: float) -> None:
        """ Programs GEN over-voltage limit
            Inputs:       volts: float, desired maximum voltage
            Outputs:      None
            GEN command:  OVP{volts}
            Nuances:      - Setting Voltage is best performed by first setting UVL = UVL['min'], OVP = OVP['MAX'],
                            then setting desired Voltage, so UVL/OVP don't interfere with Voltage.
                          - Note that below inequality *always* applies between UVL, Voltage & OVP:
                            - UVL ⪅ Voltage*95% ⪅ Voltage ⪅ Voltage*105% ⪅ OVP.
                            - The ⪅ symbol denotes less than or approximately equal.
                            - The ±5% difference is approximate, possibly due to roundoff in the Genesys.
        """
        if type(volts) not in (int, float):
            raise TypeError('Invalid Over-Voltage, must be a real number.')
        if not (self.OVP['min'] <= volts <= self.OVP['MAX']):
            raise ValueError('Invalid Over-Voltage, must *always* be in range [{}..{}].'.format(self.OVP['min'], self.OVP['MAX']))
        if not (self.get_voltage_programmed() * 1.05 <= volts <= self.OVP['MAX']):
            raise ValueError('Invalid Over-Voltage, must *presently* be in range [{}..{}].'.format(self.get_voltage_programmed() * 1.05, self.OVP['MAX']))

        volts = Genesys.FORMAT.format(volts)
        self.command_imperative('OVP {}'.format(volts))
        return None

    def get_over_voltage_protection(self) -> float:
        """ Reads GEN over-voltage programmed limit
            Inputs:       None
            Outputs:      float, programmed over-voltage
            GEN command:  OVP?
        """
        return float(self.command_interrogative('OVP?'))

    def program_over_voltage_protection_max(self) -> None:
        """ Programs GEN over-voltage limit
            Inputs:       None
            Outputs:      None
            GEN command:  OVM
        """
        self.command_imperative('OVM')
        return None

    def program_under_voltage_limit(self, volts: float)  -> None:
        """ Programs GEN under-voltage limit
            Inputs:       volts: float, desired minimum voltage
            Outputs:      None
            GEN command:  UVL {volts}
            Nuances:      - Setting Voltage is best performed by first setting UVL = UVL['min'], OVP = OVP['MAX'],
                            then setting desired Voltage, so UVL/OVP don't interfere with Voltage.
                          - Note that below inequality *always* applies between UVL, Voltage & OVP:
                            - UVL ⪅ Voltage*95% ⪅ Voltage ⪅ Voltage*105% ⪅ OVP.
                            - The ⪅ symbol denotes less than or approximately equal.
                            - The ±5% difference is approximate, possibly due to roundoff in the Genesys.
        """
        if type(volts) not in (int, float):
            raise TypeError('Invalid Under-Voltage, must be a real number.')
        if not (self.UVL['min'] <= volts <= self.UVL['MAX']):
            raise ValueError('Invalid Under-Voltage, must *always* be in range [{}..{}].'.format(self.UVL['min'], self.UVL['MAX']))
        if not (self.UVL['min'] <= volts <= self.get_voltage_programmed() * 0.95):
            raise ValueError('Invalid Under-Voltage, must *presently* be in range [{}..{}].'.format(self.UVL['min'], self.get_voltage_programmed() * 0.95))
        volts = Genesys.FORMAT.format(volts)
        self.command_imperative('UVL {}'.format(volts))
        return None

    def get_under_voltage_limit(self) -> float:
        """ Reads GEN under-voltage programmed limit
            Inputs:       None
            Outputs:      float, programmed under-voltage
            GEN command:  UVL?
        """
        return float(self.command_interrogative('UVL?'))

    def set_autostart_state(self, binary_state: str) -> None:
        """ Programs GEN Autostart state
            Inputs:        binary_state: str in ('ON, 'OFF')
            Outputs:       None
            GEN commands:  AST {binary_state}
        """
        binary_state = Genesys._validate_binary_state(binary_state)
        self.command_imperative('AST {}'.format(binary_state))
        return None

    def get_autostart_state(self) -> str:
        """ Reads GEN Autostart state
            Inputs:       None
            Outputs:      binary_state: str in ('ON, 'OFF')
            GEN command:  AST?
        """
        return self.command_interrogative('AST?')

    def save_settings(self) -> None:
        """ Saves GEN 'Last Settings' with current settings
            Inputs:       None
            Outputs:      None
            GEN command:  SAV
            Current settings saved to GEN 'Last Settings' memory:
                 1) OUT ON or OFF
                 2) Output Voltage setting (PV setting)
                 3) Output Current setting (PC setting)
                 4) OVP level
                 5) UVL level
                 6) FOLD setting
                 7) Start-up mode (Safe-start or Auto-restart)
                 8) Remote/Local: If the last setting was Local Lockout, (latched mode), the supply will return to Remote mode (non-latched).
                 9) Address setting
                10) Baud rate
                11) Locked/Unlocked Front Panel (LFP/UFP)
                12) Master/Slave setting
        """
        self.command_imperative('SAV')
        return None

    def recall_settings(self) -> None:
        """ Recalls/restores GEN 'Last Settings' from memory
            Inputs:       None
            Outputs:      None
            GEN command:  RCL
            Settings recalled into current from GEN 'Last Settings' memory:
                 1) OUT ON or OFF
                 2) Output Voltage setting (PV setting)
                 3) Output Current setting (PC setting)
                 4) OVP level
                 5) UVL level
                 6) FOLD setting
                 7) Start-up mode (Safe-start or Auto-restart)
                 8) Remote/Local: If the last setting was Local Lockout, (latched mode), the supply will return to Remote mode (non-latched).
                 9) Address setting
                10) Baud rate
                11) Locked/Unlocked Front Panel (LFP/UFP)
                12) Master/Slave setting
        """
        self.command_imperative('RCL')
        return None

    @staticmethod
    def _fast_query(serial_port: serial, address: int, query: bytes, expected_bytes: int) -> bytes:
        """ Internal method to write GEN fast queries & read their responses through pySerial serial object
            Not intended for external use.
        """
        # Genesys User Manual paragraph 7.9, 'Fast Queries'.
        Genesys.validate_address(address)
        to = serial_port.timeout
        serial_port.timeout = 0
        serial_port.write(query)
        time.sleep(0.030)
        # If no response in 10 milli-seconds, Genesys supply is not responsive.  Add another 20 ms for RS-232/RS-485 transmission time; may need to tweak.
        response = serial_port.read_until('\r', expected_bytes)
        serial_port.timeout = to
        return response

    @staticmethod
    def is_responsive(serial_port: serial, address: int) -> bool:
        """ Fast queries GEN for responsiveness; semi-similar to a network ping of an IP address.
            Inputs:       - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies       
                          - address: int, address of TDK-Lambda GEN Power Supply
             Outputs:      bool:
                           - True if Genesys does respond.
                           - False if Genesys does not respond.
            GEN command:  bytes([0xAA, address])
        """
        # Genesys User Manual paragraph 7.9.1, 'Fast Test for Connection'.
        return Genesys._fast_query(serial_port, address, bytes([0xAA, address]), 5) is None

    @staticmethod
    def is_multi_drop_enabled(serial_port: serial, address: int) -> bool:
        """ Fast queries GEN if Multi-Drop enabled
            Inputs:       - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies       
                          - address: int, address of TDK-Lambda GEN Power Supply
            Outputs:      bool:
                          - True if Genesys responds *and* Multi-Drop is enabled.
                          - False if Genesys doesn't respond *or* Multi-Drop is disabled.
            GEN command:  bytes([0xAA, address])
        """
        # Genesys User Manual paragraph 7.9.1, 'Fast Test for Connection'.
        response = Genesys._fast_query(serial_port, address, bytes([0xAA, address]), 5)
        if response is None: return False
        return response[0] == 0x31

    @staticmethod
    def get_registers_fast(serial_port: serial, address: int) -> bytes:
        """ Fast queries GEN for STAT, SENA, SEVE, FLT, FENA & FEVE registers
            Inputs:       - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies       
                          - address: int, address of TDK-Lambda GEN Power Supply
            Outputs:      bytes(16):
                          - bytes[0:11] contain respectively the STAT, SENA, SEVE, FLT, FENA & FEVE registers.
                          - bytes[12:15] contain respectively '$', checksum of all 16 characters as 2 ASCII hex bytes & '\r'.
            GEN command:  bytes([0x80 | address, 0x80 | address])
        """
        # Genesys User Manual paragraph 7.9.2, 'Fast Read Registers'.
        byte = 0x80 | address
        return Genesys._fast_query(serial_port, address, bytes([byte, byte]), 16)

    @staticmethod
    def get_power_on_time(serial_port: serial, address: int) -> bytes:
        """ Fast queries GEN for lifelong active operational time
            Inputs:       - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies       
                          - address: int, address of TDK-Lambda GEN Power Supply
            Outputs:      bytes(12):
                          - bytes[0:7] are the minutes as a 32 Bit integer as 8 ASCII Hex bytes.
                          - bytes[8:11] contain respectively '$', checksum of all 12 characters as 2 ASCII hex bytes & '\r'.
            GEN command:  bytes([0xA6, address])
        """
        # Genesys User Manual paragraph 7.9.3, 'Read Power-On Time'.
        return Genesys._fast_query(serial_port, address, bytes([0xA6, address]), 12)

    def get_register_status_event(self) -> int:
        """ Reads GEN Status Event register
            Inputs:       None
            Outputs:      int, Status Event register contents in 2-digit hex
            GEN command:  SEVE?
        """
        rse = int(self.command_interrogative('SEVE?'))
        return format(rse,'X')

    def get_register_fault_condition(self) -> int:
        """ Reads GEN Fault Condition register
            Inputs:       None
            Outputs:      int, Fault Condition register contents in 2-digit hex
            GEN command:  FLT?
        """
        flt = int(self.command_interrogative('FLT?'))
        return format(flt,'X')

    def get_register_fault_enable(self) -> int:
        """ Reads GEN Fault Enable register
            Inputs:       None
            Outputs:      int, Fault Enable register contents in 2-digit hex
            GEN command:  FENA?
        """
        rfe = int(self.command_interrogative('FENA?'))
        return format(rfe,'X')

    def set_register_fault_enable(self, fault_enable: int) -> None:
        """ Programs GEN Fault Enable register
            Inputs:       fault_enable: int, desired Fault Enable register contents in 2-digit hex
            Outputs:      None
            GEN command:  FENA {}
            - Class Genesys supports Service Requests, but SRQ messages are be handled by the client application.
            - From 'TDK-Lambda Genesys Power Supplies User Manual, 83-507-013':
                - Since Service Request messages may be sent from any supply at any time,
                there is a chance they can collide with other messages from other supplies.
                - Your controller software has to be sophisticated enough to read messages that
                may come at any time, and to recover if messages are corrupted by collisions.
                - If you need Service Request messaging, please contact TDK-Lambda for assistance.
                We can provide several special communication commands and settings that will help with this.
        """
        if type(fault_enable) != int:
            raise TypeError('Invalid Fault Enable, must be an int.')
        if not (0 <= fault_enable <= 255):
            raise ValueError('Invalid Fault Enable, must be in range (0..255).')
        fault_enable = format(fault_enable,'X')
        self.command_imperative('FENA {}'.format(fault_enable))
        return None

    def get_register_fault_event(self) -> int:
        """ Reads GEN Fault Event register
            Inputs:       None
            Outputs:      int, Fault Event register contents in 2-digit hex
            GEN command:  FEVE?
        """
        rfe = int(self.command_interrogative('FEVE?'))
        return format(rfe,'X')

    def get_register_status_condition(self) -> int:
        """ Reads GEN Status Condition register
            Inputs:       None
            Outputs:      int, Status Condition register contents in 2-digit hex
            GEN command:  STAT?
        """
        rsc = int(self.command_interrogative('STAT?'))
        return format(rsc,'X')

    def set_register_status_condition(self, status_enable: int) -> None:
        """ Programs GEN Status Condition register
            Inputs:       status_enable: int, desire Status Condition register contents in 2-digit hex
            Outputs:      None
            GEN command:  SENA {}
            - Class Genesys supports Service Requests, but SRQ messages are be handled by the client application.
            - From 'TDK-Lambda Genesys Power Supplies User Manual, 83-507-013':
                - Since Service Request messages may be sent from any supply at any time,
                there is a chance they can collide with other messages from other supplies.
                - Your controller software has to be sophisticated enough to read messages that
                may come at any time, and to recover if messages are corrupted by collisions.
                - If you need Service Request messaging, please contact TDK-Lambda for assistance.
                We can provide several special communication commands and settings that will help with this.
        """
        if type(status_enable) != int:
            raise TypeError('Invalid Status Enable, must be an int.')
        if not (0 <= status_enable <= 255):
            raise ValueError('Invalid Status Enable, must be in range (0..255).')
        status_enable = format(status_enable,'X')
        self.command_imperative('SENA {}'.format(status_enable))
        return None

    def get_register_status_enable(self) -> int:
        """ Reads GEN Status Enable register
            Inputs:       None
            Outputs:      int, Status Enable register contents in 2-digit hex
            GEN command:  SENA?
        """
        rse = int(self.command_interrogative('SENA?'))
        return format(rse,'X')

    def command_imperative(self, command: str) -> None:
        """ Reads GEN Status Event register
            Inputs:       command: str, imperative command; a command to do something
            Outputs:      None
        """
        assert command[-1] != '?' # All Genesys imperative commands don't end with '?', and do respond with 'OK'.
        assert self._write_command_read_response(command + '\r') == 'OK'
        return None

    def command_interrogative(self, command: str) -> str:
        """ Reads GEN Status Event register
            Inputs:       command: str, interrogative command; a question or query
            Outputs:      str, response from interrogative command
        """
        assert command[-1] == '?' # All Genesys interrogative commands do end with '?', and don't respond with 'OK'.
        assert self._write_command_read_response(command + '\r') != 'OK'
        return self.last_response

    def _write_command_read_response(self, command: str) -> str:
        """ Internal method to write GEN commands & read their responses through pySerial serial object
            Not intended for external use.
        """
        # Reference Genesys User Manual section 7.5, 'Communication Interface Protocol'
        # Does *not* utilize checksums as detailed in pargraphs 7.5.5.
        if (self.serial_port.port not in Genesys.listening_addresses) or (Genesys.listening_addresses[self.serial_port.port] != self.address):
            Genesys.listening_addresses.update({self.serial_port.port : self.address})
            # Genesi only need to be addressed at the begininng of a command sequence.
            # The most recently addressed Genesys remains in "listen" mode until a different Genesys is addressed.
            # If the currently addressed & listening Genesys is also the Genesys object being commanded, then skip re-addressing it, avoiding delay.
            adr = 'ADR {}\r'.format(self.address)
            adr = adr.encode('utf-8')           # pySerial library requires UTF-8 byte encoding/decoding, not string.
            self.serial_port.write(adr)
            time.sleep(0.150)
            self.last_command = adr
            assert self._read_response() == 'OK'
        command = command.encode('utf-8')
        self.serial_port.write(command)
        time.sleep(0.150)
        self.last_command = command
        return self._read_response()

    def _read_response(self) -> str:
        """ Internal method to read GEN responses through Pyserial serial object
            Not intended for external use.
        """
        # Reference Genesys User Manual section 7.5, 'Communication Interface Protocol'
        # Does *not* utilize checksums as detailed in pargraphs 7.5.5.
        response = self.serial_port.readline()
        response = response.decode('utf-8')     # pySerial library requires UTF-8 byte encoding/decoding, not string.
        response = response.replace('\r','')    # Per Genesys Manual, paragraph 7.5.3, Genesi append '\r' to their responses; remove them.
        self.last_response = response
        return self.last_response

    @staticmethod
    def _validate_binary_state(binary_state: str) -> str:
        """ Internal method to error check ('OFF', 'ON') binary states
            Not intended for external use.
        """
        if type(binary_state) != str:
            raise TypeError('Invalid Binary State, must be a str.')
        binary_state = binary_state.upper()
        if binary_state not in ('OFF', 'ON'):
            raise ValueError('Invalid Binary State, must be in (''OFF'', ''ON'').')
        return binary_state

    @staticmethod
    def _group_write_command(serial_port: serial, command: str) -> None:
        """ Internal method to write GEN group commands through pySerial serial object
            Not intended for external use.
        """
        if serial_port.baudrate not in Genesys.BAUD_RATES:
            raise ValueError('Invalid Baud Rate, must be in list ' + str(Genesys.BAUD_RATES) + '.')
        serial_port.write(command.encode('utf-8'))
        # pySerial library requires UTF-8 byte encoding/decoding, not string.
        time.sleep(0.200)
        # Per Genesys Manual paragraph 7.8.1, Genesi require 200 milliSeconds delay after group commands.
        return None

    @staticmethod
    def group_reset(serial_port: serial) -> None:
        """ Group reset command; brings GEN group supplies to a safe and known state
            Inputs:       serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies       
            Outputs:      None
            GEN command:  GRST
            Reset states:
            1) Output voltage: 0
            2) Output current: 0
            3) Output: OFF
            4) Auto-start: OFF
            5) Remote: REM
            6) OVP: maximum
            7) UVL: 0
            8) The FLT & STAT Conditional registers are updated, other registers are not changed
            9) Non-Latching faults FB, OVP & SO are cleared, OUT fault remains
        """
        Genesys._group_write_command(serial_port, 'GRST')
        return None

    @staticmethod
    def group_program_voltage(serial_port: serial, volts: float) -> None:
        """ Group programs GEN voltages
            Inputs:       - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies       
                            - volts: float, desired voltage
            Outputs:      None
            GEN command:  GPV {volts}
            Assumptions:  - Desired voltage within capabilities of all Genesys supplies connected to serial_port.
                            - Desired voltage within UVL/OVP settings of all Genesys supplies connected to serial_port.
        """
        if type(volts) not in (int, float):
            raise TypeError('Invalid Voltage, must be a real number.')
        volts = '{:0>6.3f}'.format(volts)
        Genesys._group_write_command(serial_port, 'GPV {}'.format(volts))
        return None

    @staticmethod
    def group_program_current(serial_port: serial, amperes: float) -> None:
        """ Group programs GEN amperages
            Inputs:       - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies 
                            - amperes: float, desired amperage
            Outputs:      None
            GEN command:  GPC {amperes}
            Assumptions:  - Desired amperage within capabilities of all Genesys supplies connected to serial_port.
        """
        if type(amperes) not in (int, float):
            raise TypeError('Invalid Amperage, must be a real number.')
        amperes = '{:0>6.3f}'.format(amperes)
        Genesys._group_write_command(serial_port, 'GPC {}'.format(amperes))
        return None

    @staticmethod
    def group_set_power_state(serial_port: serial, binary_state: str) -> None:
        """ Group programs GEN power states
            Inputs:       - serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies 
                            - binary_state: str in ('ON, 'OFF')
            Outputs:      None
            GEN command:  GOUT {binary_state}
        """
        binary_state = Genesys._validate_binary_state(binary_state)
        Genesys._group_write_command(serial_port, 'GOUT {}'.format(binary_state))
        return None

    @staticmethod
    def group_save_settings(serial_port: serial) -> None:
        """ Group saves GEN supplies 'Last Settings' into memory
            Inputs:       serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies 
            Outputs:      None
            GEN command:  GSAV
            Current settings saved to GEN 'Last Settings' memory:
                    1) OUT ON or OFF
                    2) Output Voltage setting (PV setting)
                    3) Output Current setting (PC setting)
                    4) OVP level
                    5) UVL level
                    6) FOLD setting
                    7) Start-up mode (Safe-start or Auto-restart)
                    8) Remote/Local: If the last setting was Local Lockout, (latched mode), the supply will return to Remote mode (non-latched).
                    9) Locked/Unlocked Front Panel (LFP/UFP)
                10) Master/Slave setting
        """
        Genesys._group_write_command(serial_port, 'GSAV')
        return None

    @staticmethod
    def group_recall_settings(serial_port: serial) -> None:
        """ Group recalls GEN supplies 'Last Settings' from memory
            Inputs:       serial_port: pySerial serial object, RS-232 or RS-485 serial port connecting PC to GEN Power Supplies 
            Outputs:      None
            GEN command:  GRCL
            Settings recalled as current settings from GEN 'Last Settings' memory:
                    1) OUT ON or OFF
                    2) Output Voltage setting (PV setting)
                    3) Output Current setting (PC setting)
                    4) OVP level
                    5) UVL level
                    6) FOLD setting
                    7) Start-up mode (Safe-start or Auto-restart)
                    8) Remote/Local: If the last setting was Local Lockout, (latched mode), the supply will return to Remote mode (non-latched).
                    9) Locked/Unlocked Front Panel (LFP/UFP)
                10) Master/Slave setting
        """
        Genesys._group_write_command(serial_port, 'GRCL')
        return None
