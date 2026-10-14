# Construction applicability release v2.1.0

Checksum-locked delta over immutable v2.0.0; consumer schema stays 2.0.0.
SmallHotel 2019 attaches its native generic GuestRoom recipe. Older SmallHotel
sets explicitly declare generic GuestRoom inheritance through existing building/
story rules. All specific variants, physics and infiltration remain unchanged.
Atlas-added applicability is marked on selector receipts with typed provenance.
No program, ground, system or BEMGen translator changes.

Load with scripts.construction_hotel_applicability.load_current_release(), then
use the existing hydrate_context(). The original v2.0.0 API stays unchanged.
Run python -m scripts.construction_hotel_applicability --check to reproduce.
This delta requires the frozen v2.0.0 tables and their original license notices;
it contains no copied material or assembly physics. Original Atlas work remains
unlicensed by user choice. No production publication is part of this task.
