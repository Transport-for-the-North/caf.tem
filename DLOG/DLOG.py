import caf.tem as ct
from pathlib import Path
from DLOG_create_input import create_hb_production_input, create_hb_attraction_input

my_tem_model = ct.TEM(
    model_years=[2023], # Yan to input - these need to match keys of dicts below
    scenario="Core",
    output_zoning="normits",
    iteration_name="test_run_TP",
    export_home=r"T:\Yan_Kavana\TEM DLOG\Outputs",
    return_segmentation=["p", "m", "tp", "hh_type"]
)

path_dict = create_hb_production_input()
input_dir_TP = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")
HBProd = my_tem_model.HBProductionModel(
    population_paths={2023: input_dir_TP / "lu_pop_2023.hdf"}, # Yan to input - path to DVector for each modelled year
    trip_rates_path=path_dict["trip_rates"],
    mode_time_splits_path=path_dict["mode_time_splits"],
    adjustment_path=path_dict["adjustment"],
    mts_adj_path=path_dict["mode_time_splits_adjustment"],
    population_translation_path=r"T:\Yan_Kavana\TEM DLOG\Inputs\translations\normits_lsoa_2021_pop.csv" # Yan to input / change (optional)
)

HBProd.run()

path_dict = create_hb_attraction_input()
HBAttr = my_tem_model.HBAttractionModel(
    trip_rates_paths=path_dict["trip_rates"],
    emp_landuse_paths = {2023: r"F:\Deliverables\Land-Use\241213_Employment\02_Final Outputs\Output E6.hdf"}, # Yan to input / change
    hh_landuse_dirs = {2023: r"F:\Deliverables\Land-Use\241220_Populationv2\02_Final Outputs"}, # Yan to input / change
    hh_landuse_prefix = "Output P13.3", # Yan to input / change
    mode_time_splits_path=path_dict["mts"],
    balance_production=True,
    trip_rate_adjustment_path=path_dict["tr_adj"],
    emp_translation_path=None,
    hh_translation_path=None,
    mode_time_splits_adjustment_path=path_dict["mts_adj"]
)

HBAttr.run()

#NHBProd = my_tem_model.NHBProductionModel()

#NHBAttr = my_tem_model.NHBAttractionModel()

