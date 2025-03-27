import caf.tem as ct
from pathlib import Path
from DLOG_create_input import create_hb_production_input, create_hb_attraction_input

my_tem_model = ct.TEM(
    model_years=[2024], 
    scenario="Core",
    output_zoning="normits",
    iteration_name="26032025_nhb",
    export_home=r"T:\Yan_Kavana\TEM DLOG\Outputs",
    return_segmentation=["p", "m", "tp", "hh_type"]
)

input_dir = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")
# HBProd = my_tem_model.HBProductionModel(
#         population_paths={2024: input_dir / "dlog_tt_pop_2024_small.dvec"},
#         trip_rates_path=input_dir / "triprates.dvec",
#         mode_time_splits_path=input_dir / "mts.dvec",
#         adjustment_path=input_dir / "trip_rate_adjustments_production_hb_fr.hdf",
#         mts_adj_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction\mode_time_split_adjustments.hdf"      
#     )


# HBProd.run()

# # path_dict = create_hb_attraction_input()
# HBAttr = my_tem_model.HBAttractionModel(
#     trip_rates_paths={
#         1: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p1.hdf",
#         2: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p2.hdf",
#         3: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p3.hdf",
#         4: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p4.hdf",
#         5: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p5.hdf",
#         6: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p6.hdf",
#         7: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p7.hdf",
#         8: r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rates_p8.hdf"
#     },
#     emp_landuse_paths = {2024: r"I:\Data\D-Log\DLIT\Outputs\Test17_DLog24_v0.13_rnn\07_tripend\dlog_soc_sic_emp\soc_sic_emp\dlog_soc_sic_emp_2024.dvec"}, # Yan to input / change
#     hh_landuse_dirs = {2024: r"I:\Data\D-Log\DLIT\Outputs\Test17_DLog24_v0.13_rnn\07_tripend\dlog_hh\hh\dlog_hh_2024.dvec"}, # Yan to input / change
#     hh_landuse_prefix = "dlog_hh_2024", # Yan to input / change
#     mode_time_splits_path=r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\mode_time_split_attraction_hb_fr_reg.hdf",
#     balance_production=True,
#     trip_rate_adjustment_path=r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\trip_rate_adjustments_attractions_hb_fr.hdf",
#     emp_translation_path=None,
#     hh_translation_path=None,
#     mode_time_splits_adjustment_path=r"T:\ThomasPrince\TEM Input\comparison\02_HBAttraction\input\mode_time_split_adjustments.hdf"
# )

# HBAttr.run()

NHBProd = my_tem_model.NHBProductionModel(
    trip_rates_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\03-NHBProduction\nhb_trip_rates_production.hdf",
    mode_time_splits_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\03-NHBProduction\mts_fixed.dvec"
)

NHBProd.run()

#NHBAttr = my_tem_model.NHBAttractionModel()

