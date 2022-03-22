"""
Genesys-Python-Library: control TDK-Lambda™ Genesys™ power supplies programmatically via Python™

    "TDK", "TDK-Lambda" & "Genesys" are registered trademarks of the TDK Corporation.
    "Python" is a registered trademark of the Python Software Foundation.
    pySerial Copyrighted by Chris Liechti.
    pytest Copyrighted by Holger Krekel and pytest-dev team.
    This script Copyright Amphenol Borisch Technologies, 2022
    - https://www.borisch.com/

    Pytest tests for Genesys class.
    Dependencies:
    - Functioning TDK-Lambda Genesys power supply(s) connected to PC via RS232 and/or RS485 serial.
    - pySerial library:
       - https://pypi.org/project/pyserial/
       - https://pyserial.readthedocs.io/en/latest/pyserial.html
    - pytest library:
       - https://docs.pytest.org/en/6.2.x/

        - Reference  Genesys Manual 'TDK-Lambda Genesys Power Supplies User Manual, 83-507-013', especially Chapter 7, 'RS232 & RS485 Remote Control':
           - https://product.tdk.com/system/files/dam/doc/product/power/switching-power/prg-power/instruction_manual/gen1u-750-1500w_user_manual.pdf
"""
import time
import pytest # https://docs.pytest.org/en/6.2.x/
import serial # https://pypi.org/project/pyserial/
from Genesys import Genesys

def test_format() -> None:
    assert Genesys.FORMAT.format(   0.2468) ==    '0.247'
    assert Genesys.FORMAT.format(   2.2468) ==    '2.247'
    assert Genesys.FORMAT.format(  42.2468) ==   '42.247'
    assert Genesys.FORMAT.format( 642.2468) ==  '642.247'
    assert Genesys.FORMAT.format(8642.2468) == '8642.247'
    assert Genesys.FORMAT.format(    0.246) ==    '0.246'
    assert Genesys.FORMAT.format(    0.24)  ==    '0.240'
    assert Genesys.FORMAT.format(    0.2)   ==    '0.200'
    return None

def test__init__fails_() -> None:
    sp = serial.Serial(port='COM4', baudrate=115200, bytesize=serial.EIGHTBITS,
                       parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,timeout=2, xonxoff=True,
                       rtscts=False, write_timeout=0, dsrdtr=False, inter_byte_timeout=None)
    assert 0 in Genesys.ADDRESS_RANGE
    assert 115200 not in Genesys.BAUD_RATES
    with pytest.raises(ValueError):
        g = Genesys(0, sp)

    assert 19200 in Genesys.BAUD_RATES
    sp.baudrate = 19200
    assert '0' not in Genesys.ADDRESS_RANGE
    with pytest.raises(TypeError):
        g = Genesys('0', sp)

    assert 42 not in Genesys.ADDRESS_RANGE # A nod to Deep Thought...
    with pytest.raises(ValueError):
        g = Genesys(42, sp)
    sp.close()
    return None

@pytest.fixture(name="serial_port", scope='session')
#
def fixture_serial_port() -> serial:
    sp = serial.Serial(port='COM4', baudrate=19200, bytesize=serial.EIGHTBITS,
         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,timeout=0, xonxoff=True,
         rtscts=False, write_timeout=0, dsrdtr=False, inter_byte_timeout=None)
    return sp

@pytest.fixture(name="genesys_address",params={0})
def fixture_zup_address(request):
    return request.param

@pytest.fixture(name="genesys")
def fixture_Genesys(genesys_address, serial_port) -> Genesys:
    return Genesys(genesys_address, serial_port)

def test__init__passes(genesys: Genesys) -> None:
    assert genesys.address in genesys.ADDRESS_RANGE                                     ;  print(genesys.address)
    assert genesys.serial_port.baudrate in genesys.BAUD_RATES                           ;  print(genesys.serial_port.baudrate)
    assert genesys.serial_port.port == 'COM4'                                           ;  print(genesys.serial_port.port)
    assert genesys.listening_addresses == {genesys.serial_port.port : genesys.address}  ;  print(genesys.listening_addresses)
    rm = genesys.get_remote_mode()
    assert rm == 'LLO'
    idn = genesys.get_identity()                                                        ;  print('idn:     ' + idn)
    assert 'LAMBDA,GEN' in idn
    idn = idn[idn.index('GEN') + 3 :]
    v = idn[: idn.index('-')]
    a = idn[idn.index('-') + 1 :]
    assert genesys.VOL == {'min':0.000, 'MAX':float(v)}
    assert genesys.CUR == {'min':0.000, 'MAX':float(a)}
    idn = 'GEN{}-XY'.format(v)
    assert genesys.OVP == genesys.OVPs[idn]
    assert genesys.UVL == genesys.UVLs[idn]
    return None

def test__str__(genesys: Genesys) -> None:
    _str_ = genesys.__str__()
    assert type(_str_) == str
    idn = genesys.get_identity()
    assert _str_ == idn
    return None

def test_clear_status(genesys: Genesys) -> None:
    assert genesys.clear_status() is None
    rfe = genesys.get_register_fault_event()
    assert rfe == 0x00
    rse = genesys.get_register_status_event()
    assert rse == 0x00
    return None

def test_reset(genesys: Genesys) -> None:
    assert genesys.reset() is None
    assert genesys.get_voltage_programmed() == 0
    assert genesys.get_amperage_programmed() == 0
    assert genesys.get_power_state() == 'OFF'
    assert genesys.get_autostart_state() == 'OFF'
    assert genesys.get_remote_mode() == 'REM'
    assert genesys.get_over_voltage_protection() == genesys.OVP['MAX']
    assert genesys.get_under_voltage_limit() == genesys.UVL['min']
    assert genesys.get_foldback_state() == 'OFF'
    assert genesys.get_register_fault_condition() == 0x00
    assert genesys.get_register_status_condition() == 0x04
    return None

def test_set_remote_mode(genesys: Genesys) -> None:
    with pytest.raises(ValueError):
        genesys.set_remote_mode('Invalid Remote Mode, so should fail.')
    assert genesys.set_remote_mode('REM') is None
    rm = genesys.get_remote_mode
    assert rm == 'REM'
    genesys.set_remote_mode('LLO')
    rm = genesys.get_remote_mode
    assert rm == 'LLO'
    return None

def test_get_remote_mode(genesys: Genesys) -> None:
    assert type(genesys.get_remote_mode()) == str
    return None

def test_multi_drop_installed(genesys: Genesys) -> None:
    assert type(genesys.multi_drop_installed()) == bool
    return None

def test_get_ms_parallel_operation(genesys: Genesys) -> None:
    mspo = genesys.get_ms_parallel_operation()
    assert type(mspo) == int
    assert mspo in (0,1,2,3,4)
    return None

def test_repeat_last_command(genesys: Genesys) -> None:
    idn = genesys.get_identity()
    rlc = genesys.repeat_last_command()
    assert idn == rlc
    return None

def test_get_identity(genesys: Genesys) -> None:
    idn = genesys.get_identity()
    assert type(idn) == str
    assert 'LAMBDA,GEN' in idn
    return None

def test_get_revision(genesys: Genesys) -> None:
    rev = genesys.get_revision()
    assert type(rev) == str
    assert 'REV' in rev
    return None

def test_get_serial_number(genesys: Genesys) -> None:
    sn = genesys.get_serial_number()
    assert type(sn) == str
    return None

def test_get_date(genesys: Genesys) -> None:
    dte = genesys.get_date()
    assert type(dte) == str
    return None

def test_program_voltage(genesys: Genesys) -> None:
    with pytest.raises(TypeError):
        genesys.program_voltage('Invalid Voltage, so should fail.')
    with pytest.raises(ValueError):
        genesys.program_voltage(genesys.VOL['MAX'] + 1)
    genesys.set_power_state('ON')
    v = genesys.VOL['MAX'] / 2              ;  print(v)
    assert genesys.program_voltage(v) is None
    vp = genesys.get_voltage_programmed()
    assert (v * 0.9 <= vp <= v * 1.1) # Allow for rounding.
    vm = genesys.get_voltage_measured()
    assert (v * 0.9 <= vm <= v * 1.1) # Allow for rounding.
    return None

def test_get_voltage_programmed(genesys: Genesys) -> None:
    vp = genesys.get_voltage_programmed()
    assert type(vp) == float
    assert (genesys.VOL['min'] <= vp <= genesys.VOL['MAX'])
    return None

def test_get_voltage_measured(genesys: Genesys) -> None:
    vm = genesys.get_voltage_measured()
    assert type(vm) == float
    assert (genesys.VOL['min'] <= vm <= genesys.VOL['MAX'])
    return None

def test_program_amperage(genesys: Genesys) -> None:
    with pytest.raises(TypeError):
        genesys.program_amperage('Invalid Amperage, so should fail.')
    with pytest.raises(ValueError):
        genesys.program_amperage(genesys.CUR['MAX'] + 1)
    # Cannot measure amperage without also programming voltage and powering with a real load impedance.
    # So only test programmed amperage.
    genesys.set_power_state('OFF')
    a = genesys.CUR['MAX'] / 2              ; print(a)
    assert genesys.program_amperage(a) is None
    ap = genesys.get_amperage_programmed()  ; print(ap)
    assert type(ap) == float
    assert (a * 0.9 <= ap <= a * 1.1) # Allow for rounding.
    return None

def test_get_amperage_programmed(genesys: Genesys) -> None:
    ap = genesys.get_amperage_programmed()  ;  print(ap)
    assert type(ap) == float
    assert (genesys.CUR['min'] <= ap <= genesys.CUR['MAX'])
    return None

def test_get_amperage_measured(genesys: Genesys) -> None:
    am = genesys.get_amperage_measured()     ; print(am)
    assert type(am) == float
    assert (genesys.CUR['min'] <= am <= genesys.CUR['MAX'])
    return None

def test_get_operation_mode(genesys: Genesys) -> None:
    genesys.set_power_state('ON')
    om = genesys.get_operation_mode()
    assert type(om) == str
    assert om in ('CC', 'CV')
    genesys.set_power_state('OFF')
    om = genesys.get_operation_mode()
    assert om == 'OFF'
    return None

def test_get_voltages_currents(genesys: Genesys) -> None:
    vc = genesys.get_voltages_currents()     ; print(vc)
    print(vc)
    assert type(vc) == dict
    assert len(vc) == 6
    assert type(vc['Voltage Measured']   == float)
    assert type(vc['Voltage Programmed'] == float)
    assert type(vc['Amperage Measured']  == float)
    assert type(vc['Voltage Programmed'] == float)
    assert type(vc['Over Voltage']       == float)
    assert type(vc['Under Voltage']      == float)
    return None

def test_get_status(genesys: Genesys) -> None:
    s = genesys.get_status()                 ; print(s)
    assert type(s) == dict
    assert len(s) == 6
    assert type(s['Voltage Measured']   == float)
    assert type(s['Voltage Programmed'] == float)
    assert type(s['Amperage Measured']  == float)
    assert type(s['Voltage Programmed'] == float)
    assert type(s['Status Register']    == int)
    assert type(s['Fault Register']     == int)
    return None

def test_set_filter_frequency(genesys: Genesys) -> None:
    with pytest.raises(TypeError):
        genesys.set_filter_frequency('Invalid Frequency, so should fail.')
    with pytest.raises(ValueError):
        genesys.set_filter_frequency(42)
    for hz in (18,23,46):
        assert genesys.set_filter_frequency(hz) is None
        ff = genesys.get_filter_frequency()
        assert type(ff) == int
        assert ff == hz
    return None

# def test_get_filter_frequency() -> None:
    # See test_set_filter_frequency(genesys: Genesys) above.

def test_set_power_state(genesys: Genesys) -> None:
    assert genesys.set_power_state('ON') is None
    ps = genesys.get_power_state()
    assert type(ps) == str
    assert ps == 'ON'
    genesys.set_power_state('OFF')
    assert genesys.get_power_state() == 'OFF'
    return None

# def test_get_power_state() -> None:
    # See test_set_power_state(genesys: Genesys) above.

def test_set_foldback_state(genesys: Genesys) -> None:
    assert genesys.set_foldback_state('ON') is None
    fld = genesys.get_foldback_state()
    assert type(fld) == str
    assert fld == 'ON'
    genesys.set_foldback_state('OFF')
    assert genesys.get_foldback_state() == 'OFF'
    return None

# def test_get_foldback_state() -> None:
    # See test_set_foldback_state(genesys: Genesys) above.

def test_set_additional_foldback_delay(genesys: Genesys) -> None:
    with pytest.raises(TypeError):
        genesys.set_additional_foldback_delay('Invalid Foldback Delay, so should fail.')
    with pytest.raises(ValueError):
        genesys.set_additional_foldback_delay(256)
    for sd in (0, 255):
        assert genesys.set_additional_foldback_delay(sd) is None
        fd = genesys.get_foldback_delay()
        assert type(fd) == int
        assert fd == sd + 250
    assert genesys.reset_foldback_delay() is None
    assert genesys.get_foldback_delay() == 250
    return None

# def test_get_foldback_delay() -> None:
    # See test_set_additional_foldback_delay(genesys: Genesys) above.

# def test_reset_foldback_delay(genesys: Genesys) -> None:
    # See test_set_additional_foldback_delay(genesys: Genesys) above.

def test_program_over_voltage_protection(genesys: Genesys) -> None:
    with pytest.raises(TypeError):
        genesys.program_over_voltage_protection('Invalid Over-Voltage, so should fail.')
    with pytest.raises(ValueError):
        genesys.program_over_voltage_protection(genesys.OVP['MAX'] + 1)
    genesys.set_power_state('OFF')
    assert genesys.program_over_voltage_protection(genesys.OVP['MAX'] / 2) is None
    op = genesys.get_over_voltage_protection()
    assert type(op) == float
    assert (genesys.OVP['MAX'] / 2 * 0.9 <= op <= genesys.OVP['MAX'] / 2 * 1.1) # Allow for rounding.
    assert genesys.program_over_voltage_protection_max() is None
    op = genesys.get_over_voltage_protection()
    assert (genesys.OVP['MAX'] * 0.9 <= op <= genesys.OVP['MAX'] * 1.1)         # Allow for rounding.
    return None

# def test_get_over_voltage_protection(genesys: Genesys) -> None:
    # See test_program_over_voltage_protection(genesys: Genesys) above.

# def test_program_over_voltage_protection_max(genesys: Genesys) -> None:
    # See test_program_over_voltage_protection(genesys: Genesys) above.

def test_program_under_voltage_limit(genesys: Genesys) -> None:
    with pytest.raises(TypeError):
        genesys.program_under_voltage_limit('Invalid Under-Voltage, so should fail.')
    with pytest.raises(ValueError):
        genesys.program_under_voltage_limit(genesys.UVL['min'] - 1)
    genesys.set_power_state('OFF')
    assert genesys.program_under_voltage_limit(genesys.UVL['min']) is None
    ul = genesys.get_under_voltage_limit()
    assert type(ul) == float
    assert ul == genesys.UVL['min']
    return None

# def test_get_under_voltage_limit(genesys: Genesys) -> None:
    # See test_program_under_voltage_limit(genesys: Genesys) above.

def test_set_autostart_state(genesys: Genesys) -> None:
    assert genesys.set_autostart_state('ON') is None
    ast = genesys.get_autostart_state()
    assert type(ast) == str
    assert ast == 'ON'
    genesys.set_autostart_state('OFF')
    assert genesys.get_autostart_state() == 'OFF'
    return None

# def test_get_autostart_state(genesys: Genesys) -> None:
    # See test_set_autostart_state(genesys: Genesys) above.

def test_save_settings(genesys: Genesys) -> None:
    genesys.set_power_state('OFF')
    genesys.set_foldback_state('OFF')
    genesys.set_autostart_state('OFF')
    genesys.set_remote_mode('LLO')
    genesys.program_over_voltage_protection(genesys.OVP['MAX'])
    genesys.program_under_voltage_limit(genesys.UVL['min'])
    genesys.program_voltage(genesys.VOL['MAX'] / 2)
    genesys.program_amperage(genesys.CUR['MAX'] / 2)
    # Ignore Address, Baud rate, LFP/UFP & M/S settings; problematic and/or overkill.
    assert genesys.get_power_state() == 'OFF'
    assert genesys.get_foldback_state() == 'OFF'
    assert genesys.get_autostart_state() == 'OFF'
    assert genesys.get_remote_mode() == 'LLO'
    assert genesys.get_over_voltage_protection() == genesys.OVP['MAX']
    assert genesys.get_under_voltage_limit() == genesys.UVL['min']
    assert genesys.get_voltage_programmed() == genesys.VOL['MAX'] / 2
    assert genesys.get_amperage_programmed() == genesys.CUR['MAX'] / 2
    genesys.save_settings()

    genesys.set_power_state('ON')
    genesys.set_foldback_state('ON')
    genesys.set_autostart_state('ON')
    genesys.set_remote_mode('REM')
    genesys.program_voltage(genesys.VOL['MAX'] / 4)
    genesys.program_amperage(genesys.CUR['MAX'] / 4)
    genesys.program_over_voltage_protection(genesys.OVP['MAX'] / 2)
    genesys.program_under_voltage_limit(genesys.UVL['min'] + 0.5) # Works for even GEN6-XY.
    assert genesys.get_power_state() == 'ON'
    assert genesys.get_foldback_state() == 'ON'
    assert genesys.get_autostart_state() == 'ON'
    assert genesys.get_remote_mode() == 'REM'
    assert genesys.get_voltage_programmed() == genesys.VOL['MAX'] / 4
    assert genesys.get_amperage_programmed() == genesys.CUR['MAX'] / 4
    assert genesys.get_over_voltage_protection() == genesys.OVP['MAX'] / 2
    assert genesys.get_under_voltage_limit() == genesys.UVL['MAX'] + 0.5

    genesys.recall_settings()
    assert genesys.get_power_state() == 'OFF'
    assert genesys.get_foldback_state() == 'OFF'
    assert genesys.get_autostart_state() == 'OFF'
    assert genesys.get_remote_mode() == 'LLO'
    assert genesys.get_over_voltage_protection() == genesys.OVP['MAX']
    assert genesys.get_under_voltage_limit() == genesys.UVL['min']
    assert genesys.get_voltage_programmed() == genesys.VOL['MAX'] / 2
    assert genesys.get_amperage_programmed() == genesys.CUR['MAX'] / 2
    return None

# def test_recall_settings(genesys: Genesys) -> None:
    # See test_save_settings(genesys: Genesys) above.







def get_register_status_event(self) -> int:
    """ Reads GEN Status Event register
        Inputs:       None
        Outputs:      int, Status Event register contents in 2-digit hex
        GEN command:  SEVE?
    """
    rse = int(self.command_interrogative('SEVE?'))
    return format(rse,'X')

def get_register_fault_condition(genesys: Genesys) -> None:
    """ Reads GEN Fault Condition register
        Inputs:       None
        Outputs:      int, Fault Condition register contents in 2-digit hex
        GEN command:  FLT?
    """
    flt = int(genesys.command_interrogative('FLT?'))
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

def format_test(reg: str, reg_format: str, valid_chars: tuple) -> None:
    assert len(reg) == len(reg_format)
    assert reg[0:2] == reg_format[0:2]
    for i in range(2, len(reg_format), 1):
        assert reg[i] in valid_chars
    return None

def test__read_response(genesys: Genesys) -> None:
    if (genesys.serial_port.port not in genesys.listening_addresses) or (genesys.listening_addresses[genesys.serial_port.port] != genesys.address):
        genesys.listening_addresses.update({genesys.serial_port.port : genesys.address})
        t0 = time.time()  ;  time.sleep(0.150)  ;  t_slept = time.time() - t0     ;  print(t_slept)
        assert (0.150 <= t_slept <= 0.250)
        adr = '{:0>2d}'.format(genesys.address)                                   ;  print(adr)
        assert adr in ('00','01','02','03','04','05','06','07','08','09',
                       '10','11','12','13','14','15','16','17','18','19',
                       '20','21','22','23','24','25','26','27','28','29',
                       '30')
        cmd = 'ADR {}\r'.format(adr)                                               ;  print(cmd)
        assert cmd == 'ADR ' + adr + '\r'
        genesys.serial_port.write(cmd.encode('utf-8'))
        t0 = time.time()  ;  time.sleep(0.150)  ;  t_slept = time.time() - t0     ;  print(t_slept)
        assert (0.150 <= t_slept <= 0.250)
        r = genesys._read_response()
        assert r == 'OK'
    assert genesys.serial_port.port in genesys.listening_addresses
    assert genesys.listening_addresses[genesys.serial_port.port] == genesys.address
    assert genesys.serial_port.write('IDN?\r'.encode('utf-8')) == 5 # 5 = number of bytes written, from 'IDN?\r'.
    t0 = time.time()  ;  time.sleep(0.150)  ;  t_slept = time.time() - t0         ;  print(t_slept)
    assert (0.150 <= t_slept <= 0.250)
    r = genesys._read_response()                                                  ;  print(r)
    assert type(r) == str
    assert 'LAMBDA,GEN' in r
    assert '\r' not in r
    return None

def test__write_command_read_response(genesys: Genesys) -> None:
    r = genesys._write_command_read_response('IDN?\r')
    assert type(r) == str
    assert 'LAMBDA,GEN' in r
    return None

def test__validate_binary_state() -> None:
    with pytest.raises(TypeError):
        binary_state = Genesys._validate_binary_state(1)
    with pytest.raises(ValueError):
        binary_state = Genesys._validate_binary_state('Invalid Binary State, so should fail.')
    binary_state = Genesys._validate_binary_state('ofF')
    assert type(binary_state) == str
    assert binary_state == 'OFF'
    binary_state = Genesys._validate_binary_state('oN')
    assert binary_state == 'ON'
    return None
