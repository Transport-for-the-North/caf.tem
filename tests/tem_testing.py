import caf.tem as ct
from caf.tem.inputs import Landuse
import caf.base as cb
from pathlib import Path

model = ct.TEM(
    model_years=[2025],
    scenario="Core",
    output_zoning="normits",
    agg_zoning="tfn_at",
    iteration_name="Dlog_test20_ls",
    export_home=r"T:\Yan_Kavana\tem_new_outputs",
    return_segmentation=["p", "m", "tp", "hh_type"],# 'ns_sec', 'soc', 'adult_nssec'],
    trans_file=r"I:\NorMITs NoTEM\Inputs\normits_lsoa21_trans.csv"
)

input_dir = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")

gor = cb.ZoningSystem.get_zoning('gor')

HBProd = model.HBProductionModel(population={
    # 2023: Path(r"T:\Yan_Kavana\tem_inputs_isaac\landuse\pop.dvec"),
    # 2024: Path(r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_pop\pop_2024.dvec"),
    2025: Path(
        r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_pop\pop_large_2025.dvec"),
    # 2035: Path(r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_pop\pop_large_2035.dvec"),
    # population_paths={2023: Path(r"T:\Yan_Kavana\tem_inputs_isaac\landuse\pop.dvec")
}, trip_rates_path=Path(r"T:\Yan_Kavana\tem_inputs_isaac\hb_prod_triprates.dvec"),
    mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\mts_prod.dvec",
    adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\trip_adj_factors.dvec",
    mts_adj_path=r"T:\Yan_Kavana\tem_inputs_isaac\mts_adj_factors.dvec")

# HBProd.run(export_pure_production=True, export_reports=False, mts_geo_constraint=gor)

# emp_2023 = Landuse(land_use=r"T:\Yan_Kavana\tem_inputs_isaac\landuse\emp.dvec", # provide
#         type='emp',
#         segmentation=["soc", "sic_1_digit", "sic_2_digit"],
#         out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor],
#         trans_tag='uni')

# emp_2024 = Landuse(land_use=r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_emp\emp_2024.dvec", # provide
#         type='emp',
#         segmentation=["soc", "sic_1_digit", "sic_2_digit"],
#         out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor],
#         trans_tag='uni')

emp_2025 = Landuse(land_use=r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_emp\emp_large_2025.dvec", # provide
        type='emp',
        segmentation=["soc", "sic_1_digit", "sic_2_digit"],
        out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor],
        trans_tag='uni')
# emp_2035 = Landuse(land_use=r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_emp\emp_large_2035.dvec", # provide
#         type='emp',
#         segmentation=["soc", "sic_1_digit", "sic_2_digit"],
#         out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor],
#         trans_tag='uni')

# hh_2023 = Landuse(type='pop',
#              land_use=r"T:\Yan_Kavana\tem_inputs_isaac\landuse", # path to F drive
#              prefix=r"Output P14.1_{}.hdf",
#              geographies=('EM', 'EoE', 'Lon', 'NE', 'NW', 'SE', 'SW', 'Wales', 'WM', 'YH', 'Scotland'),
#              out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor])

# hh_2024 = Landuse(land_use=r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_hh\hh_2024.dvec", # provide
#         type='pop',
#         segmentation=["accom_h", "ns_sec", "adults", "car_availability", "children", "adult_nssec"],
#         out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor],
#         trans_tag='uni')
hh_2025 = Landuse(land_use=r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_hh\hh_large_2025.dvec", # provide
        type='pop',
        segmentation=["accom_h", "ns_sec", "adults", "car_availability", "children", "adult_nssec"],
        out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor],
        trans_tag='uni')
# hh_2035 = Landuse(land_use=r"I:\Data\D-Log\DLIT\Outputs\test20_v0.19_updated\M4_split\dvec_hh\hh_large_2035.dvec", # provide
#         type='pop',
#         segmentation=["accom_h", "ns_sec", "adults", "car_availability", "children", "adult_nssec"],
#         out_zoning=[model.output_zoning, model.agg_zoning, 'uni', gor],
#         trans_tag='uni')



HBAttr = model.AttractionModel(trip_rates_paths={
    1: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p1.hdf", # move from T drive
    2: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p2.hdf",
    3: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p3.hdf",
    4: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p4.hdf",
    5: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p5.hdf",
    6: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p6.hdf",
    7: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p7.hdf",
    8: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p8.hdf"
}, emp_landuse={
    # 2023: emp_2023,
    # 2024: emp_2024,
    2025: emp_2025,
    # 2035: emp_2035,
    }, 
    hh_landuse={
        # 2023: hh_2023,
        # 2024: hh_2024,
        2025: hh_2025,
        # 2035: hh_2035,
        },
    mode_time_splits_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg.hdf",
    balance_production=True,
    trip_rate_adjustment_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rate_adjustments_attractions_hb_fr.hdf",
    mode_time_splits_adjustment_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_adjustments.hdf",
    mts_uni_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg_uni.hdf")

HBAttr.run(export_pure_attractions=True, mts_geo_constraint=gor, export_reports=False) # this still doesn't work - seems to be an issue with cb.DVector

NHBProd = model.NHBProductionModel(
    trip_rates_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\03-NHBProduction\nhb_trip_rates_production.hdf",
    mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\mts_nhb_prod.dvec", #provide
    balance_production=True
)

NHBProd.run(export_reports=False)

NHBAttr = model.AttractionModel(trip_rates_paths={
    1: r"T:\ThomasPrince\nhb_attraction_triprates_p1.dvec",
    2: r"T:\ThomasPrince\nhb_attraction_triprates_p2.dvec",
    3: r"T:\ThomasPrince\nhb_attraction_triprates_p3.dvec",
    4: r"T:\ThomasPrince\nhb_attraction_triprates_p4.dvec",
    5: r"T:\ThomasPrince\nhb_attraction_triprates_p5.dvec",
    6: r"T:\ThomasPrince\nhb_attraction_triprates_p6.dvec",
    7: r"T:\ThomasPrince\nhb_attraction_triprates_p7.csv",
    8: r"T:\ThomasPrince\nhb_attraction_triprates_p8.dvec"
}, emp_landuse={
    # 2023: emp_2023,
    # 2024: emp_2024,
    2025: emp_2025,
    # 2035: emp_2035,
    }, 
    hh_landuse={
        # 2023: hh_2023,
        # 2024: hh_2024,
        2025: hh_2025,
        # 2035: hh_2035,
        },
    mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_new.dvec", #provide all
    trip_rate_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_tr_adj.dvec",
    mode_time_splits_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_adj.dvec",
    mts_uni_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_uni.dvec",
    origin='nhb')

NHBAttr.run(export_reports=False)