"""
Run caf.tem
"""

from pathlib import Path
import caf.tem as ct
from caf.tem.inputs import Landuse
import caf.base as cb


model = ct.TEM(
    model_years=[2023],
    scenario="Core",
    output_zoning="normits",
    agg_zoning="tfn_at",
    iteration_name="full_test_aj_1",
    export_home=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs",
    return_segmentation=["p", "m", "tp", "hh_type", "soc"],
    trans_file=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\normits_lsoa21_trans.csv",
)

input_dir = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs")

gor = cb.ZoningSystem.get_zoning("gor")

pop = Landuse(
    land_use=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\landuse\pop.dvec",
    type="pop",
    segmentation=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"],
    out_zoning=[model.output_zoning, model.agg_zoning, gor],
)

HBProd = model.HBProductionModel(
    population={2023: pop},  # provide
    trip_rates_path=Path(
        r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\trip_rates\hb_trip_rates_production_trip_rates.dvec"
    ),  # provide
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\mode_time_splits\mode_time_split_production_hb_fr_reg_rho.dvec",  # provide
    phi_factors_path=Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\phi_factors"),
    mts_return_home_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\mode_time_splits\mode_time_split_production_hb_to_reg_trips.est.dvec",
    mts_return_home_adj_factor_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\mode_time_split_adjustments_p_hb_to_adj.dvec",
    adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\trip_rate_adjustments_p_hb_fr_adj.dvec",
    mts_adj_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\mode_time_split_adjustments_p_hb_fr_adj.dvec",
)

HBProd.run(
    export_pure_production=True,
    export_reports=False,
    mts_geo_constraint=gor,
    return_tripends=True,
)

emp = Landuse(
    land_use=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\landuse\emp.dvec",  # provide
    type="emp",
    segmentation=["soc", "sic_1_digit", "sic_2_digit"],
    out_zoning=[model.output_zoning, model.agg_zoning, "uni", gor],
    trans_tag="uni",
)

hh = Landuse(
    type="pop",
    land_use=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\landuse",  # path to F drive
    prefix=r"Output P14.1_{}.hdf",
    geographies=(
        "EM",
        "EoE",
        "Lon",
        "NE",
        "NW",
        "SE",
        "SW",
        "Wales",
        "WM",
        "YH",
        "Scotland",
    ),
    out_zoning=[model.output_zoning, model.agg_zoning, "uni", gor],
)


HBAttr = model.AttractionModel(
    trip_rates_paths={
        1: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p1_hb_alpha.dvec",
        2: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p2_hb_alpha.dvec",
        3: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p3_hb_alpha.dvec",
        4: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p4_hb_alpha.dvec",
        5: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p5_hb_alpha.dvec",
        6: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p6_hb_alpha.dvec",
        7: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p7_hb_alpha.dvec",
        8: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p8_hb_alpha.dvec",
    },
    emp_landuse={2023: emp},
    hh_landuse={2023: hh},
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\mode_time_splits\mode_time_split_attraction_hb_fr_reg_rho.dvec",
    balance_production=True,
    trip_rate_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\trip_rate_adjustments_a_hb_fr_adj.dvec",
    mode_time_splits_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\mode_time_split_adjustments_a_hb_fr_adj.dvec",
    mts_uni_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\mode_time_splits\mode_time_split_attraction_hb_fr_uni_reg_rho.dvec",
    mts_return_home_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\mode_time_splits\mode_time_split_attraction_hb_to_reg_trips.est.dvec",
    mts_return_home_adj_factor_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\mode_time_split_adjustments_a_hb_to_adj.dvec",
    phi_factors_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\phi_factors",
)

HBAttr.run(
    export_pure_attractions=True, mts_geo_constraint=gor, return_tripends=True
)  # this still doesn't work - seems to be an issue with cb.DVector

NHBProd = model.NHBProductionModel(
    trip_rates_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\nhb\trip_rates\nhb_trip_rates_production_gamma.dvec",  # seg name doubt
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\nhb\mode_time_splits\mode_time_split_production_nhb_reg_rho.dvec",  # provide
    balance_production=True,
)

NHBProd.run()

NHBAttr = model.AttractionModel(
    trip_rates_paths={
        11: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p1_nhb_alpha.dvec",
        12: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p2_nhb_alpha.dvec",
        13: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p3_nhb_alpha.dvec",
        14: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p4_nhb_alpha.dvec",
        15: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p5_nhb_alpha.dvec",
        16: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p6_nhb_alpha.dvec",
        17: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p7_nhb_alpha.dvec",
        18: r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\trip_rates\trip_rates_attraction_p8_nhb_alpha.dvec",
    },
    emp_landuse={2023: emp},
    hh_landuse={2023: hh},
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\nhb\mode_time_splits\mode_time_split_attraction_nhb_reg_rho.dvec",  # provide all
    trip_rate_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\trip_rate_adjustments_a_nhb_adj.dvec",
    mode_time_splits_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\mode_time_split_adjustments_a_nhb_adj.dvec",
    mts_uni_path=r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\nhb\mode_time_splits\mode_time_split_attraction_nhb_uni_reg_rho.dvec",
    origin="nhb",
)

NHBAttr.run(mts_geo_constraint=gor)
