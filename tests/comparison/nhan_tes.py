import caf.tem as ct

tem = ct.TEM(
    model_years=[2023],
    scenario="Core",
    output_zoning="normits",
    iteration_name="HBAttr_specific_test",
    export_home=r"T:\ThomasPrince\TEM I-Drive Comparison\Outputs - caf.tem",
    return_segmentation=["p", "m", "tp", "ns_sec", "soc"],
)

HBAttr = tem.AttractionModel(
    trip_rates_paths={
        1: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p1.hdf",
        2: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p2.hdf",
        3: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p3.hdf",
        4: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p4.hdf",
        5: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p5.hdf",
        6: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p6.hdf",
        7: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p7.hdf",
        8: r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p8.hdf",
    },
    emp_landuse={
        2023: r"F:\Deliverables\Land-Use\241213_Employment\02_Final Outputs\Output E6.hdf"
    },
    hh_landuse={2023: r"F:\Deliverables\Land-Use\241220_Populationv2\02_Final Outputs"},
    mode_time_splits_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg.hdf",
    balance_production=True,
    trip_rate_adjustment_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rate_adjustments_attractions_hb_fr.hdf",
    mode_time_splits_adjustment_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_adjustments.hdf",
    mts_uni_path=r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg_uni.hdf",
)

HBAttr.run()
