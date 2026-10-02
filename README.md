# FOC Motor Driver — Rev B

Closed-loop FOC driver for 2-phase steppers, BLDC/PMSM and brushed DC motors.
4 half-bridges (2× DRV8300 + CSD19534Q5A), 36–48 V, 5 A continuous, STM32G431RBT6, CAN-FD.

Driver split: U3 drives HB1+HB2+HB3, U4 drives HB4. A BLDC-only board can be built with a single
DRV8300 (U4, Q7, Q8 and the HB4 parts are DNP; they carry a `Variant` field in the schematic).

| Path | Contents |
|---|---|
| `HANDOVER.md` | Rev B handover: decisions, layout guidance, firmware impacts |
| `FOC-surucu-analiz.md` | Technical audit and price survey |
| `BOM_revB.csv` | Rev B bill of materials |
| `hardware/` | KiCad 10 project (4 sheets: MCU, Interfaces, Power Supply, Power Stage) |
| `hardware/build/` | Schematic PDF, sheet PNGs, ERC report |
| `tools/` | Python generator for the schematics (`build.py`), netlist checks (`check_net.py`), renderer |
| `datasheets/` | Reference datasheets |

The schematics are generated: run `python3 tools/build.py`, then verify with
`kicad-cli sch export netlist` + `python3 tools/check_net.py <netlist>`.
Edits made directly in KiCad are overwritten by the next build.
