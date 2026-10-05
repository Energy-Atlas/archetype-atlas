# Building and program names

Catalogue titles, filters, category tables, mapping entries and shared schedule
contexts use the same reviewed display vocabulary. For example, `MediumOffice`
appears as **Medium Office**, `apartment_unit` as **Apartment unit**, and
`elec_mechroom` as **Electrical / mechanical room**. Old filter URLs, category
addresses and searches using those original codes remain usable.

The downloadable research records retain their original building/program codes,
variants, IDs and source fields. Display names help browsing; they do not change
the underlying energy semantics or establish that two source rows are equivalent.

## Source variants

Numbered programs remain distinct: **Corridor**, **Corridor 2** and **Corridor 4**
have separate program categories. The number remains a source identifier; it
does not by itself establish a floor assignment. Occupied and vacant guest-room
variants, front/rear storage variants and strip-mall types also remain separate.

Apartment source variants share the **Apartment unit** program filter, while
their titles distinguish **Apartment unit, top floor NS** and **Apartment unit,
top floor WE**. Large Office titles distinguish **Office, basement** and
**Office, other floors**. Inspect the original `source_space_type` and `variant`
fields before assigning these rules. An apartment building's corridor or office
program remains separate from a dwelling unit.

Equivalent source spellings share a browsing label: `NurseStn` and `NurseStation`
appear as **Nurse station**, while `PhysTherapy` and `PhysicalTherapy` appear as
**Physical therapy**. Their separate records and building/template applicability
remain intact. **Hall (infil)** preserves the source qualifier; its name does
not fill an unknown infiltration field.

## Applicability

The same building display label may appear on Standards program records and
ResStock dwelling fixtures. These records retain their separate source families,
templates, scopes and unresolved inputs. A coarse source description such as
“Multi-Family with 5+ Units” does not collapse low-, mid- and high-rise categories.

DOE existing-stock benchmark rules remain distinct from code/prototype rules.
Shared schedule filters preserve the actual building/template pairs that
reference the schedule; readable names do not create new combinations.

The vocabulary covers all 22 building codes and 108 program codes in the active
v0.2.0 release, including the v0.1.0 vocabulary. Future unreviewed source strings
remain visible as reported until their display names are explicitly reviewed.
