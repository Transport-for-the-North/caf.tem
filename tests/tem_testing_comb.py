import caf.tem as ct
from caf.tem.inputs import Landuse
import caf.base as cb
from pathlib import Path
import pandas as pd

# === Define your entities and model years ===
entities = ["total", "ls_growth"]  # , "ls_growth" # Add more if needed ["total", "ls_growth"]
model_years = [2023]  # 2042 , 2052

# === Define root path for LU inputs ===
lu_inputs_root = Path(r"I:\Data\D-Log\DLIT\Outputs\test21_v0.20")

# === File naming rules based on entity ===
pop_file = lambda year, entity: (
    Path(r"T:\Yan_Kavana\tem_inputs_isaac\landuse\pop.dvec")
    if year == 2023
    else lu_inputs_root
    / "M4_split"
    / "dvec_pop"
    / f"pop{'_large' if entity == 'ls_growth' else ''}_{year}.dvec"
)

emp_file = lambda year, entity: (
    r"T:\Yan_Kavana\tem_inputs_isaac\landuse\emp.dvec"
    if year == 2023
    else lu_inputs_root
    / "M4_split"
    / "dvec_emp"
    / f"emp{'_large' if entity == 'ls_growth' else ''}_{year}.dvec"
)

hh_file = lambda year, entity: (
    r"T:\Yan_Kavana\tem_inputs_isaac\landuse"
    if year == 2023
    else lu_inputs_root
    / "M4_split"
    / "dvec_hh"
    / f"hh{'_large' if entity == 'ls_growth' else ''}_{year}.dvec"
)


# === Loop through entities ===
for entity in entities:
    iteration_name = f"Dlog_test21_{entity}"

    print(f"\n=== Running for entity: {entity} | Iteration: {iteration_name} ===")

    model = ct.TEM(
        model_years=model_years,
        scenario="Core",
        output_zoning="normits",
        agg_zoning="tfn_at",
        iteration_name=iteration_name,
        export_home=r"T:\Yan_Kavana\tem_new_outputs",
        return_segmentation=["p", "m", "tp", "hh_type"],
        trans_file=r"I:\NorMITs NoTEM\Inputs\normits_lsoa21_trans.csv",
    )

    input_dir = Path(
        r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\01-HBProduction"
    )
    gor = cb.ZoningSystem.get_zoning("gor")

    # === HB Production ===
    population_paths = {year: pop_file(year, entity) for year in model_years}

    HBProd = model.HBProductionModel(
        population_paths=population_paths,
        trip_rates_path=Path(r"T:\Yan_Kavana\tem_inputs_isaac\hb_prod_triprates.dvec"),
        mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\mts_prod.dvec",
        adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\trip_adj_factors.dvec",
        mts_adj_path=r"T:\Yan_Kavana\tem_inputs_isaac\mts_adj_factors.dvec",
        pop_zoning="lsoa_2021",
    )
    HBProd.run(export_pure_production=True, export_reports=False, mts_geo_constraint=gor)

    # === Employment & Household Landuse Dictionaries ===
    emp_segmentation = ["soc", "sic_1_digit", "sic_2_digit"]
    hh_segmentation = [
        "accom_h",
        "ns_sec",
        "adults",
        "car_availability",
        "children",
        "adult_nssec",
    ]
    out_zoning = [model.output_zoning, model.agg_zoning, "uni", gor]

    emp_landuse = {}
    hh_landuse = {}

    for year in model_years:
        emp_path = emp_file(year, entity)
        hh_path = hh_file(year, entity)

        # Household object
        hh_obj = (
            Landuse(
                type="pop",
                land_use=hh_path,
                prefix=r"Output P14.1_{}.hdf",  # used only if 2023
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
                out_zoning=out_zoning,
            )
            if year == 2023
            else Landuse(
                type="pop",
                land_use=hh_path,
                segmentation=hh_segmentation,
                out_zoning=out_zoning,
                trans_tag="uni",
            )
        )

        # Employment object
        emp_obj = Landuse(
            land_use=emp_path,
            type="emp",
            segmentation=emp_segmentation,
            out_zoning=out_zoning,
            trans_tag="uni",
        )

        emp_landuse[year] = emp_obj
        hh_landuse[year] = hh_obj

        # === HB Attractions ===
        trip_rate_paths_hb_attr = {
            i: rf"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rates_p{i}.hdf"
            for i in range(1, 9)
        }

        HBAttr = model.AttractionModel(
            trip_rates_paths=trip_rate_paths_hb_attr,
            emp_landuse=emp_landuse,
            hh_landuse=hh_landuse,
            mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg.hdf",
            balance_production=False,
            trip_rate_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rate_adjustments_attractions_hb_fr.hdf",
            mode_time_splits_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_adjustments.hdf",
            mts_uni_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg_uni.hdf",
        )

        # if entity == "total":
        #     HBAttr = model.AttractionModel(
        #         trip_rates_paths=trip_rate_paths_hb_attr,
        #         emp_landuse=emp_landuse,
        #         hh_landuse=hh_landuse,
        #         mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg.hdf",
        #         balance_production=False,
        #         trip_rate_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rate_adjustments_attractions_hb_fr.hdf",
        #         mode_time_splits_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_adjustments.hdf",
        #         mts_uni_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg_uni.hdf",
        #     )

        # else:
        #     HBAttr = model.AttractionModel(
        #         trip_rates_paths=trip_rate_paths_hb_attr,
        #         emp_landuse=emp_landuse,
        #         hh_landuse=hh_landuse,
        #         mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg.hdf",
        #         balance_production=False,
        #         trip_rate_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\trip_rate_adjustments_attractions_hb_fr.hdf",
        #         mode_time_splits_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_adjustments.hdf",
        #         mts_uni_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\02-HBAttraction\mode_time_split_attraction_hb_fr_reg_uni.hdf",
        #     )

        HBAttr.run(export_pure_attractions=True, mts_geo_constraint=gor, export_reports=False)

        # === NHB Production ===
        NHBProd = model.NHBProductionModel(
            trip_rates_path=r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\03-NHBProduction\nhb_trip_rates_production.hdf",
            mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\mts_nhb_prod.dvec",
            balance_production=True,
        )
        NHBProd.run(export_reports=False)

        # === NHB Attraction ===
        trip_rate_paths_nhb_attr = {
            1: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p11.dvec",
            2: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p12.dvec",
            3: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p13.dvec",
            4: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p14.dvec",
            5: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p15.dvec",
            6: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p16.dvec",
            7: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p7.csv",  # Check file format compatibility
            8: r"T:\Yan_Kavana\tem_inputs_isaac\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel\nhb_attraction_triprates_p18.dvec",
        }

        NHBAttr = model.AttractionModel(
            trip_rates_paths=trip_rate_paths_nhb_attr,
            emp_landuse=emp_landuse,
            hh_landuse=hh_landuse,
            balance_production=False,
            mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_new.dvec",
            trip_rate_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_tr_adj.dvec",
            mode_time_splits_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_adj.dvec",
            mts_uni_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_uni.dvec",
            origin="nhb",
        )

        # if entity == "total":
        #     NHBAttr = model.AttractionModel(
        #         trip_rates_paths=trip_rate_paths_nhb_attr,
        #         emp_landuse=emp_landuse,
        #         hh_landuse=hh_landuse,
        #         balance_production=False,
        #         mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_new.dvec",
        #         trip_rate_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_tr_adj.dvec",
        #         mode_time_splits_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_adj.dvec",
        #         mts_uni_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_uni.dvec",
        #         origin="nhb",
        #     )

        # else:
        #     NHBAttr = model.AttractionModel(
        #         trip_rates_paths=trip_rate_paths_nhb_attr,
        #         emp_landuse=emp_landuse,
        #         hh_landuse=hh_landuse,
        #         balance_production=False,
        #         mode_time_splits_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_new.dvec",
        #         trip_rate_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_tr_adj.dvec",
        #         mode_time_splits_adjustment_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_adj.dvec",
        #         mts_uni_path=r"T:\Yan_Kavana\tem_inputs_isaac\nhb_attr_mts_uni.dvec",
        #         origin="nhb",
        #     )

        NHBAttr.run(export_reports=False)
