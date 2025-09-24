import caf.tem as ct
from pathlib import Path

tem = ct.TEM(
    model_years=[2023],
    scenario="Core",
    output_zoning="normits",
    iteration_name="20250310",
    export_home=r"T:\ThomasPrince\TEM I-Drive Comparison\Outputs - caf.tem",
    return_segmentation=["hh_type", "p", "m", "tp"],
)

input_dir = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")

HBProd = tem.HBProductionModel(
    population={2023: input_dir / "lu_pop_2023.hdf"},
    trip_rates_path=input_dir / "hb_trip_rates_production.hdf",
    mode_time_splits_path=input_dir / "mode_time_split_production_hb_fr_reg.hdf",
    adjustment_path=input_dir / "trip_rate_adjustments_production_hb_fr.hdf",
    mts_adj_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction\mode_time_split_adjustments.hdf",
)

HBProd.run()
