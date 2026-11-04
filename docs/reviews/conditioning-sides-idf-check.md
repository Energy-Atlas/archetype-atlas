# Conditioning sides in the prototype IDFs (ADR 0063)

Written by `python -m scripts.conditioning_sides --review` from the PNNL and DOE prototype IDFs outside the
repository (`ATLAS_PROTOTYPE_ROOT`, `ATLAS_DOE_IDF_ROOT`; checksums in `sources/reference-models-lock.json`),
base climate of each family. Each zone takes the sides of its zone equipment: an air terminal those of the air
loop that feeds it (its branches, unitary systems expanded), a zone unit its own coils. Listed: every zone
whose equipment does not serve both sides, with whether it has a thermostat. Plenums and attics are listed
under one line per model.

## PNNL ASHRAE 90.1-2007

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL ASHRAE 90.1-2013

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL ASHRAE 90.1-2019

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL IECC 2006

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL IECC 2009

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL IECC 2012

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL IECC 2015

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL IECC 2018

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## PNNL IECC 2021

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| ApartmentHighRise | g corridor | no | no | no | none |
| ApartmentHighRise | m corridor | no | no | no | none |
| ApartmentHighRise | t corridor | no | no | no | none |
| ApartmentMidRise | g corridor | no | no | no | none |
| ApartmentMidRise | m corridor | no | no | no | none |
| ApartmentMidRise | t corridor | no | no | no | none |
| HotelSmall | elevatorcoreflr1 | no | no | no | none |
| HotelSmall | elevatorcoreflr2 | no | no | no | none |
| HotelSmall | elevatorcoreflr3 | no | no | no | none |
| HotelSmall | elevatorcoreflr4 | no | no | no | none |
| HotelSmall | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | frontstorageflr1 | no | no | no | none |
| HotelSmall | frontstorageflr2 | no | no | no | none |
| HotelSmall | frontstorageflr3 | no | no | no | none |
| HotelSmall | frontstorageflr4 | no | no | no | none |
| HotelSmall | laundryroomflr1 | no | no | no | none |
| HotelSmall | mechanicalroomflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| HotelSmall | rearstorageflr1 | no | no | no | none |
| HotelSmall | rearstorageflr2 | no | no | no | none |
| HotelSmall | rearstorageflr3 | no | no | no | none |
| HotelSmall | rearstorageflr4 | no | no | no | none |
| OfficeLarge | datacenter_basement_zn_6 | no | no | yes | zonehvac:idealloadsairsystem |
| OfficeLarge | 3 plenum or attic zones | no | no | – | none |
| OfficeMedium | 3 plenum or attic zones | no | no | – | none |
| OfficeSmall | 1 plenum or attic zones | no | no | – | none |
| RestaurantFastFood | 1 plenum or attic zones | no | no | – | none |
| RestaurantSitDown | 1 plenum or attic zones | no | no | – | none |
| RetailStandalone | front_entry | yes | no | yes | zonehvac:unitheater |
| Warehouse | zone3 bulk storage | yes | no | yes | zonehvac:hightemperatureradiant, zonehvac:unitheater |

## DOE reference pre1980

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| RefBldgLargeOfficePre1980 | 3 plenum or attic zones | no | no | – | none |
| RefBldgMediumOfficePre1980 | 3 plenum or attic zones | no | no | – | none |
| RefBldgMidriseApartmentPre1980 | g corridor | yes | no | yes | zonehvac:unitheater |
| RefBldgMidriseApartmentPre1980 | m corridor | yes | no | yes | zonehvac:unitheater |
| RefBldgMidriseApartmentPre1980 | t corridor | yes | no | yes | zonehvac:unitheater |
| RefBldgOutPatientPre1980 | floor 1 electrical room | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 elevator pump room | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 lobby toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 mri toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 nurse janitor | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 nurse toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 pre-op toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 storage | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 utility janitor | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 1 utility room | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 conference toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 janitor | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 reception toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 storage 1 | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 storage 2 | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 storage 3 | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 utility | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 2 work toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 janitor | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 lounge toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 mechanical | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 office toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 physical therapy toilet | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 storage 1 | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 storage 2 | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 undeveloped 1 | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 undeveloped 2 | no | no | no | none |
| RefBldgOutPatientPre1980 | floor 3 utility | no | no | no | none |
| RefBldgOutPatientPre1980 | ne stair | no | no | no | none |
| RefBldgOutPatientPre1980 | nw elevator | no | no | no | none |
| RefBldgOutPatientPre1980 | nw stair | no | no | no | none |
| RefBldgOutPatientPre1980 | sw stair | no | no | no | none |
| RefBldgSmallHotelPre1980 | elevatorcoreflr1 | no | no | no | none |
| RefBldgSmallHotelPre1980 | elevatorcoreflr2 | no | no | no | none |
| RefBldgSmallHotelPre1980 | elevatorcoreflr3 | no | no | no | none |
| RefBldgSmallHotelPre1980 | elevatorcoreflr4 | no | no | no | none |
| RefBldgSmallHotelPre1980 | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | frontstorageflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | frontstorageflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | frontstorageflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | frontstorageflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstorageflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstorageflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstorageflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | rearstorageflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPre1980 | 1 plenum or attic zones | no | no | – | none |
| RefBldgStand-aloneRetailPre1980 | front_entry | yes | no | yes | zonehvac:unitheater |
| RefBldgWarehousePre1980 | bulkstorage | yes | no | yes | zonehvac:unitheater |

## DOE reference post1980

| Model | Zone | Heating | Cooling | Thermostat | Equipment |
| --- | --- | --- | --- | --- | --- |
| RefBldgFullServiceRestaurantPost1980 | 1 plenum or attic zones | no | no | – | none |
| RefBldgLargeOfficePost1980 | 3 plenum or attic zones | no | no | – | none |
| RefBldgMediumOfficePost1980 | 3 plenum or attic zones | no | no | – | none |
| RefBldgMidriseApartmentPost1980 | g corridor | yes | no | yes | zonehvac:unitheater |
| RefBldgMidriseApartmentPost1980 | m corridor | yes | no | yes | zonehvac:unitheater |
| RefBldgMidriseApartmentPost1980 | t corridor | yes | no | yes | zonehvac:unitheater |
| RefBldgOutPatientPost1980 | floor 1 electrical room | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 elevator pump room | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 lobby toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 mri toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 nurse janitor | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 nurse toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 pre-op toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 storage | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 utility janitor | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 1 utility room | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 conference toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 janitor | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 reception toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 storage 1 | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 storage 2 | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 storage 3 | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 utility | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 2 work toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 janitor | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 lounge toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 mechanical | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 office toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 physical therapy toilet | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 storage 1 | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 storage 2 | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 undeveloped 1 | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 undeveloped 2 | no | no | no | none |
| RefBldgOutPatientPost1980 | floor 3 utility | no | no | no | none |
| RefBldgOutPatientPost1980 | ne stair | no | no | no | none |
| RefBldgOutPatientPost1980 | nw elevator | no | no | no | none |
| RefBldgOutPatientPost1980 | nw stair | no | no | no | none |
| RefBldgOutPatientPost1980 | sw stair | no | no | no | none |
| RefBldgQuickServiceRestaurantPost1980 | 1 plenum or attic zones | no | no | – | none |
| RefBldgSmallHotelPost1980 | elevatorcoreflr1 | no | no | no | none |
| RefBldgSmallHotelPost1980 | elevatorcoreflr2 | no | no | no | none |
| RefBldgSmallHotelPost1980 | elevatorcoreflr3 | no | no | no | none |
| RefBldgSmallHotelPost1980 | elevatorcoreflr4 | no | no | no | none |
| RefBldgSmallHotelPost1980 | frontstairsflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | frontstairsflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | frontstairsflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | frontstairsflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | frontstorageflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | frontstorageflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | frontstorageflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | frontstorageflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstairsflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstairsflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstairsflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstairsflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstorageflr1 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstorageflr2 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstorageflr3 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | rearstorageflr4 | yes | no | yes | zonehvac:unitheater |
| RefBldgSmallHotelPost1980 | 1 plenum or attic zones | no | no | – | none |
| RefBldgSmallOfficePost1980 | 1 plenum or attic zones | no | no | – | none |
| RefBldgStand-aloneRetailPost1980 | front_entry | yes | no | yes | zonehvac:unitheater |
| RefBldgWarehousePost1980 | bulkstorage | yes | no | yes | zonehvac:unitheater |
