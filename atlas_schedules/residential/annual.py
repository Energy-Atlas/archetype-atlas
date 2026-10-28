"""Annual energy of a ResStock unit's appliances, plug and fuel loads, pools and lighting (plan section 8, B5).

A readable port of the pinned OpenStudio-HPXML and ResStock methods (ResStock dd25369f), operational branch
(the resident count is known) with ERI version "latest", as scripts/recover_residential_inputs.rb executes
them:

- BuildResidentialHPXML `set_*`: which objects exist and their inputs, from the measure arguments
  (residential/arguments.py);
- `Defaults.apply_appliances`, `apply_plug_loads`, `apply_fuel_loads`, `apply_pools_and_permanent_spas`,
  `apply_ceiling_fans`: defaults for omitted inputs;
- ResStockArgumentsPostHPXML (lines 296-356): the stock usage multipliers;
- `HotWaterAndAppliances.calc_*`, `Lighting.calc_*_energy`, the `MiscLoads` annual terms and
  `HVAC.apply_ceiling_fans` (stochastic schedules: fan months from the weather).

Zero residents give zero energy except refrigeration, pools and spas, as upstream. Water heating belongs
to the building: appliances that need a water heater are present, and their hot water is reported in
gal/day. Fixture hot water is not ported.
"""
import math

APARTMENT = "apartment unit"
INDOORS = "conditioned space"


def equivalent_bedrooms(bedrooms: float, residents: float, unit_type: str = APARTMENT) -> float:
    """Defaults.get_equivalent_nbeds (2020 RECS regressions), operational branch."""
    a, b = {"apartment unit": (-1.36, 1.49), "single-family attached": (-1.98, 1.89),
            "single-family detached": (-2.19, 2.08), "manufactured home": (-1.26, 1.61)}[unit_type]
    return a + b * residents


def _multiplier(*values) -> float:
    """An omitted object multiplier defaults to 1; each stock multiplier then multiplies it."""
    result = 1.0
    for value in values:
        if value is not None:
            result *= float(value)
    return result


def _size_term(cfa: float, nbeds_eq: float) -> float:
    return 0.5 + 0.25 * nbeds_eq / 3.0 + 0.25 * cfa / 1920.0


def _energy(end_use, kwh, sensible, latent, fuel="electricity", therm=None):
    load = {"end_use": end_use, "annual_kwh": kwh, "fuel": fuel, "sensible_fraction": sensible,
            "latent_fraction": latent}
    if therm is not None:
        load["annual_therm"] = therm
    return load


def _water(end_use, gpd):
    return {"end_use": end_use, "daily_gallons": gpd}


def _clothes_washer(a: dict) -> dict | None:
    if a.get("appliance_clothes_washer") in (None, "None"):
        return None
    w = {"rated_annual_kwh": a.get("appliance_clothes_washer_rated_annual_consumption"),
         "label_electric_rate": a.get("appliance_clothes_washer_label_electric_rate"),
         "label_gas_rate": a.get("appliance_clothes_washer_label_gas_rate"),
         "label_annual_gas_cost": a.get("appliance_clothes_washer_label_annual_gas_cost"),
         "label_usage": a.get("appliance_clothes_washer_label_usage"),
         "capacity": a.get("appliance_clothes_washer_capacity"), "imef": None, "mef": None}
    kind = a.get("appliance_clothes_washer_efficiency_type")
    if kind == "ModifiedEnergyFactor":
        w["mef"] = a.get("appliance_clothes_washer_efficiency")
    elif kind == "IntegratedModifiedEnergyFactor":
        w["imef"] = a.get("appliance_clothes_washer_efficiency")
    if w["rated_annual_kwh"] is None:  # Defaults.get_clothes_washer_values (2019A and later)
        w.update(imef=1.0, rated_annual_kwh=400.0, label_electric_rate=0.12, label_gas_rate=1.09,
                 label_annual_gas_cost=27.0, capacity=3.0, label_usage=6.0)
    w["usage_multiplier"] = _multiplier(a.get("appliance_clothes_washer_usage_multiplier"),
                                        a.get("clothes_washer_usage_multiplier"))
    return w


def _washer_energy(w: dict, residents: float):
    gas_h2o, elec_h2o = 0.3914, 0.0178
    lcy = w["label_usage"] * 52.0
    scy = 123.0 + 61.0 * residents
    acy = scy * ((3.0 * 2.08 + 1.59) / (w["capacity"] * 2.08 + 1.59))
    appliance = ((w["label_annual_gas_cost"] * gas_h2o / w["label_gas_rate"]
                  - (w["rated_annual_kwh"] * w["label_electric_rate"]) * elec_h2o / w["label_electric_rate"])
                 / (w["label_electric_rate"] * gas_h2o / w["label_gas_rate"] - elec_h2o))
    kwh = appliance / lcy * acy * w["usage_multiplier"]
    gpd = (w["rated_annual_kwh"] - appliance) * elec_h2o * acy / 365.0 * w["usage_multiplier"]
    sensible = (1.0 - 0.70) * 0.90
    return max(kwh, 0.0), sensible, 1.0 - sensible - 0.70, max(gpd, 0.0)


def _dryer_energy(a: dict, w: dict, residents: float):
    fuel = a.get("appliance_clothes_dryer_fuel_type")
    kind = a.get("appliance_clothes_dryer_efficiency_type")
    cef = a.get("appliance_clothes_dryer_efficiency") if kind == "CombinedEnergyFactor" else None
    ef = a.get("appliance_clothes_dryer_efficiency") if kind == "EnergyFactor" else None
    if cef is None and ef is None:
        cef = 3.01  # Defaults.get_clothes_dryer_values (2019A and later)
    if cef is None:
        cef = ef / 1.15
    imef = w["imef"] if w["imef"] is not None else (w["mef"] - 0.503) / 0.95
    rmc = ((0.97 * (w["capacity"] / imef) - w["rated_annual_kwh"] / 312.0)
           / ((2.0104 * w["capacity"] + 1.4242) * 0.455) + 0.04)
    scy = 123.0 + 61.0 * residents
    acy = scy * ((3.0 * 2.08 + 1.59) / (w["capacity"] * 2.08 + 1.59))
    kwh = (((rmc - 0.04) * 100) / 55.5) * (8.45 / cef) * acy
    if fuel == "electricity":
        therm = 0.0
    else:
        therm = kwh * 3412.0 * (1.0 - 0.07) * (3.73 / 3.30) / 100000
        kwh = kwh * 0.07 * (3.73 / 3.30)
    usage = _multiplier(a.get("appliance_clothes_dryer_usage_multiplier"), a.get("clothes_dryer_usage_multiplier"))
    method = a.get("appliance_clothes_dryer_drying_method") or "conventional"
    vented = method not in ("condensing", "heat pump")
    lost = 0.85 if vented else 0.0
    sensible = (1.0 - lost) * 0.90
    return max(kwh * usage, 0.0), max(therm * usage, 0.0), sensible, 1.0 - sensible - lost, fuel


def _dishwasher_energy(a: dict, residents: float):
    kind = a.get("appliance_dishwasher_efficiency_type")
    rated = a.get("appliance_dishwasher_efficiency") if kind == "RatedAnnualkWh" else None
    ef = a.get("appliance_dishwasher_efficiency") if kind == "EnergyFactor" else None
    d = {"rated_annual_kwh": rated, "label_electric_rate": a.get("appliance_dishwasher_label_electric_rate"),
         "label_gas_rate": a.get("appliance_dishwasher_label_gas_rate"),
         "label_annual_gas_cost": a.get("appliance_dishwasher_label_annual_gas_cost"),
         "label_usage": a.get("appliance_dishwasher_label_usage"),
         "place_setting_capacity": a.get("appliance_dishwasher_place_setting_capacity")}
    if d["place_setting_capacity"] is None:  # Defaults.get_dishwasher_values (2019A and later)
        d.update(rated_annual_kwh=467.0, label_electric_rate=0.12, label_gas_rate=1.09, label_annual_gas_cost=33.12,
                 label_usage=4.0, place_setting_capacity=12.0)
    if d["rated_annual_kwh"] is None:
        d["rated_annual_kwh"] = 215.0 / ef
    lcy = d["label_usage"] * 52.0
    kwh_per_cycle = ((d["label_annual_gas_cost"] * 0.5497 / d["label_gas_rate"]
                      - d["rated_annual_kwh"] * d["label_electric_rate"] * 0.02504 / d["label_electric_rate"])
                     / (d["label_electric_rate"] * 0.5497 / d["label_gas_rate"] - 0.02504)) / lcy
    scy = 91.0 + 30.0 * residents
    cycles = scy * (12.0 / d["place_setting_capacity"])
    usage = _multiplier(a.get("appliance_dishwasher_usage_multiplier"), a.get("dishwasher_usage_multiplier"))
    kwh = kwh_per_cycle * cycles * usage
    gpd = (d["rated_annual_kwh"] - kwh_per_cycle * lcy) * 0.02504 * cycles / 365.0 * usage
    sensible = (1.0 - 0.40) * 0.50
    return max(kwh, 0.0), sensible, 1.0 - sensible - 0.40, max(gpd, 0.0)


def _range_energy(a: dict, nbeds_eq: float):
    fuel = a.get("appliance_cooking_range_oven_fuel_type")
    burner = 0.91 if a.get("appliance_cooking_range_oven_is_induction") else 1.0
    oven = 0.95 if a.get("appliance_cooking_range_oven_is_convection") else 1.0
    if fuel != "electricity":
        kwh = 22.6 + 2.7 * nbeds_eq
        therm = oven * (22.6 + 2.7 * nbeds_eq)
    else:
        kwh = burner * oven * (331 + 39.0 * nbeds_eq)
        therm = 0.0
    usage = _multiplier(a.get("appliance_cooking_range_oven_usage_multiplier"), a.get("cooking_range_oven_usage_multiplier"))
    lost = 0.20
    sensible = (1.0 - lost) * (0.90 if fuel == "electricity" else 0.80)
    return max(kwh * usage, 0.0), max(therm * usage, 0.0), sensible, 1.0 - sensible - lost, fuel


def _lighting_fraction_energy(kind: str, area: float, cfl: float, lfl: float, led: float) -> float:
    """Lighting.calc_interior/exterior/garage_energy, 2014AEG and later."""
    fluorescent = cfl + lfl
    adjustment = (1.0 - fluorescent - led) + fluorescent * 15.0 / 60.0 + led * 15.0 / 90.0
    if kind == "interior":
        return 0.9 / 0.925 * (455.0 + 0.8 * area) * adjustment + 0.1 * (455.0 + 0.8 * area)
    if kind == "exterior":
        return (100.0 + 0.05 * area) * adjustment
    return 100.0 * adjustment if area > 0 else 0.0  # garage


def annual_loads(arguments: dict, residents: float, bedrooms: float, cfa_ft2: float, fan_months: list,
                 unit_type: str = APARTMENT, garage_area_ft2: float = 0.0) -> list:
    """Annual energy (kWh, therm for fuels) and appliance hot water (gal/day) per end use, upstream order."""
    a = arguments
    occupied = residents != 0
    nbeds_eq = equivalent_bedrooms(bedrooms, residents, unit_type)
    loads = []
    has_water_heater = a.get("dhw_water_heater", "present") != "None"
    washer = _clothes_washer(a) if has_water_heater else None
    if washer is not None:
        kwh, sensible, latent, gpd = _washer_energy(washer, residents) if occupied else (0.0, 0.0, 0.0, 0.0)
        loads += [_energy("clothes_washer", kwh, sensible, latent), _water("hot_water_clothes_washer", gpd)]
    if has_water_heater and a.get("appliance_dishwasher") not in (None, "None"):
        kwh, sensible, latent, gpd = _dishwasher_energy(a, residents) if occupied else (0.0, 0.0, 0.0, 0.0)
        loads += [_energy("dishwasher", kwh, sensible, latent), _water("hot_water_dishwasher", gpd)]
    if washer is not None and a.get("appliance_clothes_dryer") not in (None, "None"):
        if occupied:
            kwh, therm, sensible, latent, fuel = _dryer_energy(a, washer, residents)
        else:
            kwh, therm, sensible, latent, fuel = 0.0, 0.0, 0.0, 0.0, a.get("appliance_clothes_dryer_fuel_type")
        loads.append(_energy("clothes_dryer", kwh, sensible, latent))
        if fuel != "electricity":
            loads.append(_energy("clothes_dryer", therm * 29.307107017222222, sensible, latent, fuel, therm))
    if a.get("appliance_cooking_range_oven") not in (None, "None"):
        if occupied:
            kwh, therm, sensible, latent, fuel = _range_energy(a, nbeds_eq)
        else:
            kwh, therm, sensible, latent, fuel = 0.0, 0.0, 0.0, 0.0, a.get("appliance_cooking_range_oven_fuel_type")
        loads.append(_energy("cooking_range", kwh, sensible, latent))
        if fuel != "electricity":
            loads.append(_energy("cooking_range", therm * 29.307107017222222, sensible, latent, fuel, therm))
    has_fridge = a.get("appliance_refrigerator") not in (None, "None")
    if has_fridge:
        rated = a.get("appliance_refrigerator_rated_annual_consumption")
        rated = 637.0 + 18.0 * bedrooms if rated is None else rated
        usage = _multiplier(a.get("appliance_refrigerator_usage_multiplier"), a.get("refrigerator_usage_multiplier"))
        loads.append(_energy("refrigerator", rated * usage, 1.0, 0.0))
    if a.get("appliance_extra_refrigerator") not in (None, "None"):
        rated = a.get("appliance_extra_refrigerator_rated_annual_consumption")
        rated = 243.6 if rated is None else rated
        usage = _multiplier(a.get("appliance_extra_refrigerator_usage_multiplier"), a.get("extra_refrigerator_usage_multiplier"))
        loads.append(_energy("extra_refrigerator", rated * usage, 1.0, 0.0))
    if a.get("appliance_freezer") not in (None, "None"):
        rated = a.get("appliance_freezer_rated_annual_consumption")
        rated = 319.8 if rated is None else rated
        usage = _multiplier(a.get("appliance_freezer_usage_multiplier"), a.get("freezer_usage_multiplier"))
        loads.append(_energy("freezer", rated * usage, 1.0, 0.0))
    if a.get("misc_television") not in (None, "None"):
        kwh = a.get("misc_television_annual_energy_use")
        if kwh is None:
            kwh = {"apartment unit": 190.3 + 81.0 * residents + 0.11 * cfa_ft2,
                   "single-family attached": 283.9 + 80.1 * residents + 0.07 * cfa_ft2,
                   "single-family detached": 334.0 + 92.2 * residents + 0.06 * cfa_ft2,
                   "manufactured home": 99.9 + 129.6 * residents + 0.21 * cfa_ft2}[unit_type]
        usage = _multiplier(a.get("misc_television_usage_multiplier"), a.get("misc_plug_loads_television_usage_multiplier"))
        loads.append(_energy("plug_loads_tv", kwh * usage if occupied else 0.0, 1.0, 0.0))
    kwh = a.get("misc_plug_loads_annual_energy_use")
    if kwh is None:
        kwh = {"apartment unit": 706.6 + 149.3 * residents + 0.10 * cfa_ft2,
               "single-family attached": 654.9 + 206.5 * residents + 0.21 * cfa_ft2,
               "single-family detached": 786.9 + 241.8 * residents + 0.33 * cfa_ft2,
               "manufactured home": 1795.1}[unit_type]
    sensible = a.get("misc_plug_loads_sensible_fraction")
    latent = a.get("misc_plug_loads_latent_fraction")
    if sensible is None:
        sensible = (1.0 - 0.10) * 0.95
    if latent is None:
        latent = 1.0 - (1.0 - 0.10) * 0.95 - 0.10
    usage = _multiplier(a.get("misc_plug_loads_usage_multiplier"), a.get("misc_plug_loads_other_usage_multiplier"))
    loads.append(_energy("plug_loads_other", kwh * usage if occupied else 0.0, sensible, latent))
    if a.get("misc_well_pump") not in (None, "None"):
        kwh = a.get("misc_well_pump_annual_energy_use")
        if kwh is None:
            kwh = 0.0 if not occupied else 50.8 / 0.127 * _size_term(cfa_ft2, nbeds_eq)
        usage = _multiplier(a.get("misc_well_pump_usage_multiplier"))
        loads.append(_energy("plug_loads_well_pump", kwh * usage if occupied else 0.0, 0.0, 0.0))
    for argument, end_use, default, sensible, latent in (
            ("misc_grill", "fuel_loads_grill", 0.87 / 0.029, 0.0, 0.0),
            ("misc_gas_lighting", "fuel_loads_lighting", 0.22 / 0.012, 0.0, 0.0),
            ("misc_fireplace", "fuel_loads_fireplace", 1.95 / 0.032, 0.5, 0.1)):
        if a.get(argument) in (None, "None"):
            continue
        therm = a.get(argument + "_annual_energy_use")
        if therm is None:
            therm = 0.0 if not occupied else default * _size_term(cfa_ft2, nbeds_eq)
        therm = therm * _multiplier(a.get(argument + "_usage_multiplier")) if occupied else 0.0
        loads.append(_energy(end_use, therm * 29.307107017222222, sensible, latent, a.get(argument + "_fuel_type"), therm))
    for argument, name, pump_default, heater in (
            ("misc_pool", "pool", 158.6 / 0.070, {"electric": 8.3 / 0.004, "gas": 3.0 / 0.014}),
            ("misc_permanent_spa", "permanent_spa", 59.5 / 0.059, {"electric": 49.0 / 0.048, "gas": 0.87 / 0.011})):
        if a.get(argument) in (None, "None"):
            continue
        pump = a.get(argument + "_pump_annual_energy_use")
        if pump is None:
            pump = pump_default * _size_term(cfa_ft2, nbeds_eq)
        loads.append(_energy(f"{name}_pump", pump * _multiplier(a.get(argument + "_pump_usage_multiplier"),
                                                                 a.get("pool_pump_usage_multiplier") if name == "pool" else None), 0.0, 0.0))
        kind = a.get(argument + "_heater_type")
        if kind in (None, "none"):
            continue
        usage = _multiplier(a.get(argument + "_heater_usage_multiplier"))
        if kind in ("electric resistance", "heat pump"):
            value = a.get(argument + "_heater_annual_electricity_use")
            if value is None:
                value = heater["electric"] * _size_term(cfa_ft2, nbeds_eq) / (5.0 if kind == "heat pump" else 1.0)
            loads.append(_energy(f"{name}_heater", value * usage, 0.0, 0.0))
        elif kind == "gas fired":
            value = a.get(argument + "_heater_annual_natural_gas_use")
            if value is None:
                value = heater["gas"] * _size_term(cfa_ft2, nbeds_eq)
            loads.append(_energy(f"{name}_heater", value * usage * 29.307107017222222, 0.0, 0.0, "natural gas", value * usage))
    if a.get("lighting") not in (None, "None"):
        for kind, area, stock in (("interior", cfa_ft2, "interior_lighting_usage_multiplier"),
                                  ("exterior", cfa_ft2, "exterior_lighting_usage_multiplier"),
                                  ("garage", garage_area_ft2, "garage_lighting_usage_multiplier")):
            fractions = [a.get(f"lighting_{kind}_fraction_{lamp}") for lamp in ("cfl", "lfl", "led")]
            if any(f is None for f in fractions) or not occupied or area == 0:
                kwh = 0.0
            else:
                kwh = _lighting_fraction_energy(kind, area, *fractions)
            kwh *= _multiplier(a.get(f"lighting_{kind}_usage_multiplier"), a.get(stock))
            loads.append({"end_use": f"lighting_{kind}", "annual_kwh": kwh, "fuel": "electricity"})
    if a.get("ceiling_fans") not in (None, "None"):
        count = a.get("ceiling_fans_count")
        count = bedrooms + 1 if count is None else count
        watts = a.get("ceiling_fans_label_energy_use")
        efficiency = a.get("ceiling_fans_efficiency")
        if watts is None:
            watts = 3000.0 / efficiency if efficiency is not None else 42.6
        kwh = 0.0 if not occupied else count * watts * 10.5 * 365.0 / 1000.0 * math.fsum(fan_months) / 12.0
        loads.append({"end_use": "ceiling_fan", "annual_kwh": kwh, "fuel": "electricity"})
    return loads
