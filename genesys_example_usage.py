"""
    "TDK", "TDK-Lambda" & "Genesys" are registered trademarks of the TDK Corporation.
    "Python" is a registered trademark of the Python Software Foundation.
    pySerial Copyrighted by Chris Liechti.
    pytest Copyrighted by Holger Krekel and pytest-dev team.
    This script Copyright Amphenol Borisch Technologies, 2022
    - https://www.borisch.com/

    Example usage of Genesys class.
"""
import serial # https://pythonhosted.org/pyserial/#
from Genesys import Genesys

# For this example script, used below Genesys:
# Address     Model:
# -------    --------------
#    1     GEN40-38
serial_port = serial.Serial(port='COM4', baudrate=19200, bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                            timeout=0, xonxoff=True, rtscts=False,
                            write_timeout=0, dsrdtr=False, inter_byte_timeout=None)

gens = {}
for address in range(0, 1, 1): gens.update({address : Genesys(address, serial_port)})
# Create and add 1 Genesys class objects to dict 'gens'.
# 'gens' thus models a physical chain of 1 Genesys supply connected to COM4, with address 0.
# Change range() as/if needed.
#
# Notes:
# - The Genesys.__init__() initializer disables Genesys front-panel controls, permitting only programmatic control
#   (like this script), preventing operator interference.
#   - It also prevents operator intervention, so keep that in mind!
# - Initializer __init__() deliberately doesn't issue any other Genesys commands:
#   - Instantiating a Genesys object literally only establishes communication with it.
#   - Whatever prior state a Genesys has before __init__() executes remains entirely intact after execution:
#     - If a Genesys's power was set to 5.0V/1.0A with output on before __init__() executes, it will be powered
#       on identically at 5.0V/1.0A after __init__().
#     - It may seem counter-intuitive, but this behavior is actually useful & preferable to performing
#       any other initializations during __init__().
#     - Sole exception is the 'last command', which isn't remembered.
#   - Use Genesys class methods to individually configure specific Genesys states; set power output off or on,
#     change voltage/amperage, etc.
#   - Or, Genesys.configure() can be invoked to generically configure a Genesys supply with multiple settings if desired.

for address in gens:
    gens[address].reset()
    gens[address].clear_status()
# Clears Genesys communication & alarm registers.
# It would seem sensible to include this in Genesys.__init__(), but that would erase any existing register
# alarms when re-connecting to Gens, preventing appropriate actions to accomodate them.
# But for our purposes here clearing without first reading is preferable, as we don't care about
# prior behavior, but instead just want to get on with present/future behavior.

for address in gens: gens[address].set_power_state('OFF')
# Power all Genesys outputs off prior to configuring them any further.
# Powering off the Genesys objects in their own for/in loop like this ensures they're all powered off
# as simultaneously as possible, as is typically desirable.

for address in gens:
    gens[address].program_under_voltage_limit(gens[address].UVL['min'])
    gens[address].program_over_voltage_protection(gens[address].OVP['MAX'])
# Set Genesys UVLs/OVPs to their specific min/MAX values so we can most easily set voltages afterwards.
# - Setting UVL/OVP is best performed by first setting UVL = UVL['min'], OVP = OVP['MAX'],
#   then setting desired Voltage, then finally resetting UVL/OVP to desired values so
#   UVL/OVP values don't interfere with setting Voltages.  More on this shortly.

gens[0].program_voltage(4.0)   ;  gens[0].program_amperage(1.0)
# Now selectively set voltages & amperages of the specific Gens actively needed.
# For this application, the Genesys supplies with addresses 1, 2 & 6 are needed, so their voltages &
# amperages are re-configured while those with addresses 3, 4 & 5 are left configured with
# their pre-script voltages/amperages, but still de-powered from 2nd for/in loop above.

# gens[0].program_under_voltage_limit(gens[0].get_voltage_programmed() * 0.90)
# gens[0].program_over_voltage_protection( gens[0].get_voltage_programmed() * 1.10)
# Above sets UVLs/OVPs to 90%/110% of current set voltages.
# - Note that below inequality *always* applies between UVL, Voltage & OVP:
#         UVL['min'] ≤ UVL ⪅ Voltage*95% ⪅ Voltage ⪅ Voltage*105% ⪅ OVP ≤ OVP['MAX']
#   - The ⪅ symbol denotes less than or approximately equal.
#   - The ±5% difference is approximate, possibly due to roundoff in the Genesys; safer to use ≥ ±7.5%.
#   - Violating above inequality doesn't end well, hence set UVL/OVP to min/MAX, set desired Voltage,
#     then reset UVL/OVP appropriately.

for address in gens: gens[address].set_power_state('ON')
# Finally, power on Genesys supplies as simultaneously as possible, in their own exclusive for/in loop.

for address in gens:
    i = 4
    while i < 6.0:
        gens[address].program_voltage(i)
        i += 0.1
    while i > 4.0:
        i -= 0.1
        gens[address].program_voltage(i)
# Occasionally it's useful to ramp supplies up/down to ensure that whatever they're powering continues
# working correctly with varying input voltages.  Here input varies as 5.0VDC ±20%.

for address in gens: gens[address].set_remote_mode('REM')
serial_port.close()
# Lastly, we explicitly clean up after ourselves with the above 2 statements.
