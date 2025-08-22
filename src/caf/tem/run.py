import caf.tem as ct
from caf.tem.inputs import Landuse
import caf.base as cb
from pathlib import Path

model = ct.TEM(
    model_years=[2023],
    scenario="Core",
    output_zoning="normits",
    agg_zoning="tfn_at",
    iteration_name="full_test",
    export_home=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs",
    return_segmentation=["p", "m", "tp", "hh_type", "soc", "ns_sec", "adult_nssec"],
    trans_file=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\normits_lsoa21_trans.csv",
)

input_dir = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs")

gor = cb.ZoningSystem.get_zoning("gor")

HBProd = model.HBProductionModel(
    population={2023: Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\landuse\pop.dvec")},
    trip_rates_path=Path(
        r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\hb_prod_triprates.dvec"
    ),
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_prod.dvec",
    phi_factors_path=Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\phi_factors"),
    mts_return_home_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_production_return_home.dvec",
    mts_return_home_adj_factor_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_return_home_prod_adj_factor.dvec",
    adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\trip_adj_factors.dvec",
    mts_adj_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_adj_factors.dvec",
)

HBProd.run(
    export_pure_production=False,
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
    geographies=("EM", "EoE", "Lon", "NE", "NW", "SE", "SW", "Wales", "WM", "YH", "Scotland"),
    out_zoning=[model.output_zoning, model.agg_zoning, "uni", gor],
)


HBAttr = model.AttractionModel(
    trip_rates_paths={
        1: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p1.hdf",  # move from T drive
        2: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p2.hdf",
        3: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p3.hdf",
        4: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p4.hdf",
        5: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p5.hdf",
        6: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p6.hdf",
        7: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p7.hdf",
        8: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rates_p8.hdf",
    },
    emp_landuse={2023: emp},
    hh_landuse={2023: hh},
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg.hdf",
    balance_production=True,
    trip_rate_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\trip_rate_adjustments_attractions_hb_fr.hdf",
    mode_time_splits_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\mode_time_split_adjustments.hdf",
    mts_uni_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg_uni.hdf",
    mts_return_home_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_attraction_return_home.dvec",
    mts_return_home_adj_factor_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_return_home_attr_adj_factor.dvec",
    phi_factors_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\phi_factors",
)

HBAttr.run(
    export_pure_attractions=False, mts_geo_constraint=gor, return_tripends=True
)  # this still doesn't work - seems to be an issue with cb.DVector

NHBProd = model.NHBProductionModel(
    trip_rates_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\03-NHBProduction\nhb_trip_rates_production.hdf",
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_nhb_prod.dvec",  # provide
    balance_production=True,
)

NHBProd.run()

NHBAttr = model.AttractionModel(
    trip_rates_paths={
        1: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p11.dvec",
        2: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p12.dvec",
        3: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p13.dvec",
        4: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p14.dvec",
        5: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p15.dvec",
        6: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p16.dvec",
        7: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p7.csv",
        8: r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\inputs\04_NHBAttractionModel\nhb_attraction_triprates_p18.dvec",
    },
    emp_landuse={2023: emp},
    hh_landuse={2023: hh},
    mode_time_splits_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\nhb_attr_mts_new.dvec",  # provide all
    trip_rate_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\nhb_tr_adj.dvec",
    mode_time_splits_adjustment_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\nhb_attr_mts_adj.dvec",
    mts_uni_path=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\nhb_attr_mts_uni.dvec",
    origin="nhb",
)

NHBAttr.run()
