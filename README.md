# Genesys-Python-Library: control TDK-Lambda Genesys power supplies programmatically via Python
"TDK", "TDK-Lambda" & "Genesys" are registered trademarks of the TDK Corporation.

"Python" is a registered trademark of the Python Software Foundation.

pySerial Copyrighted by Chris Liechti.

pytest Copyrighted by Holger Krekel and pytest-dev team.

Reference: Genesys User Manual at https://product.tdk.com/system/files/dam/doc/product/power/switching-power/prg-power/instruction_manual/gen1u-750-1500w_user_manual.pdf

Chapter 7 is especially relevant.

- Procure & install RS-232 & RS-485 serial cables connecting your PC to your Genesys power supplies.
  - RS-232 PC to Genesys cable: GEN/232-9
    - Need 1 GEN/232-9 to connect your PC to the first Genesys in your serial chain.
  - RS-485 Genesys to Genesys cables: GEN/RJ45
    - Need 1 each for remaining Genesys supplies in your serial chain.  For 6 Genesys supplies, will need 5 GEN/RJ45s.
- Configure your Genesys supplies for serial communication.
  - Note that the Genesys connected to your PC communicates via RS-232 or RS-485; the Genesys daisy-chained to one another only via RS-485.
- Install Python:  https://www.python.org/
- Install pySerial: https://pypi.org/project/pyserial/
- Install Genesys.py library from this repository.
- Modify genesys_example_usage.py from this repository as needed.
