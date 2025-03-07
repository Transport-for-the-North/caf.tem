import caf.tem as ct
from pathlib import Path
from .DLOG_create_input import create_hb_production_input, create_hb_attraction_input

my_tem_model = ct.TEM(
    model_years=[2024],
    scenario="Core",
    output_zoning="normits",
    iteration_name="20250307",
    export_home=r"T:\Yan_Kavana\TEM DLOG\Outputs",
    return_segmentation=["p", "m", "tp", "hh_type"]
)

path_dict = create_hb_production_input()
HBProd = my_tem_model.HBProductionModel(
    population_paths={2024: None}, # Yan to input
    trip_rates_path=path_dict["trip_rates"],
    mode_time_splits_path=path_dict["mode_time_splits"],
    adjustment_path=path_dict["adjustment"],
    population_translation_path=None
)

path_dict = create_hb_attraction_input()
HBAttr = my_tem_model.HBAttractionModel(
    trip_rates_paths="",
    emp_landuse_paths={}, # Yan to input
    hh_landuse_dirs={}, # Yan to input
    hh_landuse_prefix={}, # Yan to input
)

#NHBProd = my_tem_model.NHBProductionModel()

#NHBAttr = my_tem_model.NHBAttractionModel()

HBAttr.run()
HBProd.run()