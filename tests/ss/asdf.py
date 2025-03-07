import caf.tem as ct
from pathlib import Path
import caf.base as cb

tem = ct.TEM(
    model_years=[2023],
    scenario="Core",
    output_zoning="normits",
    iteration_name="full-run-new",
    export_home=r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\Export",
    return_segmentation=["hh_type", "p", "m", "tp"]
)

dvec_fldr = Path(r"C:\Users\Spiral\Documents\Thomas Prince\(normitsefs) Transfer\TP_20250128-copy\tem_inputs")

HBProd = tem.HBProductionModel(
    population_paths={2023: dvec_fldr / "pop_2023.dvec"},
    trip_rates_path=dvec_fldr / "hb_trip_rates_production_dvector.dvec",
    mode_time_splits_path=dvec_fldr / "hb_mode_time_split_production_hb_fr.dvec")

HBAttr = tem.HBAttractionModel(
    trip_rates_paths={
        1: r"T:\ThomasPrince\hb_attraction_triprates_p1.dvec",
        2: r"T:\ThomasPrince\hb_attraction_triprates_p2.dvec",
        3: r"T:\ThomasPrince\hb_attraction_triprates_p3.dvec",
        4: r"T:\ThomasPrince\hb_attraction_triprates_p4.dvec",
        5: r"T:\ThomasPrince\hb_attraction_triprates_p5.dvec",
        6: r"T:\ThomasPrince\hb_attraction_triprates_p6.dvec",
        8: r"T:\ThomasPrince\hb_attraction_triprates_p8.dvec"
    },
    balance_production=True,
    emp_landuse_paths = {2023: r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\Inputs\Land Use\employment\normits\Output E6.hdf"},
    hh_landuse_dirs = {2023: r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\Inputs\Land Use\population\normits"},
    hh_landuse_prefix = "Output P14.1",
    hb_mts_path=r"C:\Users\Spiral\Documents\Thomas Prince\NTS Processing DVec\outputs_is\attractions\hb\mode_time_splits\hb_mode_time_split_attraction_hb_fr.dvec"
)

NHBProd = tem.NHBProductionModel(
    trip_rates_path=r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\NTS Output\productions\nhb\trip_rates\nhb_trip_rates_production.hdf",
    nhb_mts_path=r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\NTS Output\productions\nhb\mode_time_splits\nhb_mode_time_split_production.dvec"
)

NHBAttr = tem.NHBAttractionModel(trip_rates_paths={
        11: r"T:\ThomasPrince\nhb_attraction_triprates_p1.dvec",
        12: r"T:\ThomasPrince\nhb_attraction_triprates_p2.dvec",
        13: r"T:\ThomasPrince\nhb_attraction_triprates_p3.dvec",
        14: r"T:\ThomasPrince\nhb_attraction_triprates_p4.dvec",
        15: r"T:\ThomasPrince\nhb_attraction_triprates_p5.dvec",
        16: r"T:\ThomasPrince\nhb_attraction_triprates_p6.dvec",
        18: r"T:\ThomasPrince\nhb_attraction_triprates_p8.dvec"
    },
    balance_production=True,
    emp_landuse_paths = {2023: r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\Inputs\Land Use\employment\normits\Output E6.hdf"},
    hh_landuse_dirs = {2023: r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\Inputs\Land Use\population\normits"},
    hh_landuse_prefix = "Output P14.1",
    nhb_mts_path=r"C:\Users\Spiral\Documents\Thomas Prince\NTS Processing DVec\outputs_is\attractions\nhb\mode_time_splits\nhb_mode_time_split_attraction.dvec")

tem.run()
