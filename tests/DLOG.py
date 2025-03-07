import caf.tem as ct
from pathlib import Path

my_tem_model = ct.TEM(
    model_years=[2024],
    scenario="Core",
    output_zoning="normits",
    iteration_name="test1",
    export_home="./",
    return_segmentation=["p", "m", "tp", "hh_type"]
)

input_dir = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")
HBProd = my_tem_model.HBProductionModel(
    population_paths={2024: ""},
    trip_rates_path=input_dir / "hb_trip_rates_production.hdf",
    mode_time_splits_path=input_dir / "hb_mode_time_split_production_fr_reg.hdf",
    adjustment_path=input_dir / "trip_rate_adjustments_production_hb_fr.hdf",
)

HBAttr = my_tem_model.HBAttractionModel(
    trip_rates_paths={1: "",
                      2: ""},
    emp_landuse_paths={},
    hh_landuse_dirs={},
    hh_landuse_prefix={},
)

NHBProd = my_tem_model.NHBProductionModel()

NHBAttr = my_tem_model.NHBAttractionModel()

HBAttr.run()

my_tem_model.run()