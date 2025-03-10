import caf.base as cb
import pandas as pd
import os
from typing import Union, Dict

from pathlib import Path

NTS_DIR = Path(r"I:\NTS\outputs")

# # # HB PRODUCTION # # #
def create_hb_production_input() -> dict[str, Path]:

    hb_production_input_paths = {}

    out_dir = Path(r"T:\Yan_Kavana\TEM DLOG\Inputs\01-HBProduction")

    # Trip Rates
    dvec_path = out_dir / "hb_trip_rates_production.hdf"
    hb_production_input_paths["trip_rates"] = dvec_path
    if not os.path.exists(dvec_path):
        tr = pd.read_csv(NTS_DIR / "productions/hb/trip_rates/hb_trip_rates_production.csv")
        tr = tr.rename(columns={"gender": "gender_3", "ns": "ns_sec", "purpose": "p"}).pivot(index=["gender_3", "aws", "ns_sec", "soc", "hh_type", "p"], columns="tfn_at", values="beta")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["gender_3", "aws", "ns_sec", "soc", "hh_type", "p"],
                                                            naming_order=["gender_3", "aws", "ns_sec", "soc", "hh_type", "p"]))
        zoning_system = cb.ZoningSystem.get_zoning("tfn_at")
        tr_dvec = cb.DVector(segmentation=segmentation, import_data=tr, zoning_system=zoning_system)
        tr_dvec.save(dvec_path)

    # Trip Rate Adjustment
    dvec_path = out_dir / "trip_rate_adjustments_production_hb_fr.hdf"
    hb_production_input_paths["adjustment"] = dvec_path
    if not os.path.exists(dvec_path):
        adj = pd.read_csv(NTS_DIR / "others/trip_rate_adjustments.csv")
        adj = adj.rename(columns={"purpose": "p"}).loc[(adj["pa"]=="p") & (adj["direction"]=="hb_fr")].pivot(index=["p"], columns="gor", values="adj")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p"],
                                                            naming_order=["p"]))
        zoning_system = cb.ZoningSystem.get_zoning("gor")
        adj_dvec = cb.DVector(segmentation=segmentation, import_data=adj, zoning_system=zoning_system)
        adj_dvec.save(dvec_path)

    # Mode Time Split
    dvec_path = out_dir / "mode_time_split_production_hb_fr_reg.hdf"
    hb_production_input_paths["mode_time_splits"] = dvec_path
    if not os.path.exists(dvec_path):
        mts = pd.read_csv(NTS_DIR / "productions/hb/mode_time_splits/mode_time_split_production_hb_fr_reg.csv") # TODO double check correct path 25 Feb.
        mts = mts.rename(columns={"mode": "m", "period": "tp", "purpose": "p"}).pivot(index=["p", "m", "tp", "hh_type"], columns="tfn_at", values="rho")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p", "m", "tp", "hh_type"],
                                                            naming_order=["p", "m", "tp", "hh_type"]))
        zoning_system = cb.ZoningSystem.get_zoning("tfn_at")
        mts_dvec = cb.DVector(segmentation=segmentation, import_data=mts, zoning_system=zoning_system)
        mts_dvec.save(dvec_path)

    # Mode Time Split Adjustment
    dvec_path = out_dir / "mode_time_split_adjustments.hdf"
    hb_production_input_paths["mode_time_splits_adjustment"] = dvec_path
    if not os.path.exists(dvec_path):
        adj = pd.read_csv(NTS_DIR / "others/mode_time_split_adjustments.csv")
        adj = adj.rename(columns={"purpose": "p", "period": "tp", "mode": "m"}).loc[(adj["pa"]=="p") & (adj["direction"]=="hb_fr")].pivot(index=["p", "tp", "m"], columns="gor", values="adj")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p", "tp", "m"],
                                                            naming_order=["p", "tp", "m"]))
        zoning_system = cb.ZoningSystem.get_zoning("gor")
        adj_dvec = cb.DVector(segmentation=segmentation, import_data=adj, zoning_system=zoning_system)
        adj_dvec.save(dvec_path)

    return hb_production_input_paths

# # # HB ATTRACTION # # #
def create_hb_attraction_input() -> dict:

    out_dir = Path(r"T:\Yan_Kavana\TEM DLOG\Inputs\02-HBAttraction")

    hb_attraction_input_paths = {}
     
    # Trip Rates
    tr = pd.read_csv(NTS_DIR / "attractions/hb/trip_rates/trip_rates_attraction.csv")
    tr = tr.loc[tr["dir"]=="hb"]

    # Segmentations
    soc = cb.Segmentation(cb.SegmentationInput(enum_segments=["soc"], naming_order=["soc"]))
    sic = cb.Segmentation(cb.SegmentationInput(enum_segments=["sic_2_digit"], naming_order=["sic_2_digit"]))
    total = cb.Segmentation(cb.SegmentationInput(enum_segments=["total"], naming_order=["total"]))
    tfn_at = cb.ZoningSystem.get_zoning("tfn_at")

    tr_paths = {}

    #p1
    if not os.path.exists(out_dir / "trip_rates_p1.hdf"):
        tr1 = tr.loc[tr["p"]==1]
        tr1 = tr1.pivot(index = "soc", columns="tfn_at", values="alpha")
        tr1.index = tr1.index.astype(int)
        cb.DVector(segmentation=soc, import_data=tr1, zoning_system=tfn_at).save(out_dir / "trip_rates_p1.hdf")
    tr_paths[1] = out_dir / "trip_rates_p1.hdf"

    #p2
    if not os.path.exists(out_dir / "trip_rates_p2.hdf"):
        tr2 = tr.loc[tr["p"]==2]
        tr2 = tr2.pivot(index = "soc", columns="tfn_at", values="alpha")
        tr2.index = tr2.index.astype(int)
        cb.DVector(segmentation=soc, import_data=tr2, zoning_system=tfn_at).save(out_dir / "trip_rates_p2.hdf")
    tr_paths[2] = out_dir / "trip_rates_p2.hdf"

    #p3
    if not os.path.exists(out_dir / "trip_rates_p3.hdf"):
        tr3 = tr.loc[tr["p"]==3]
        tr3["sic_2_digit"] = 85
        tr3 = tr3.pivot(index = "sic_2_digit", columns="tfn_at", values="alpha")
        cb.DVector(segmentation=sic, import_data=tr3, zoning_system=tfn_at).save(out_dir / "trip_rates_p3.hdf")
    tr_paths[3] = out_dir / "trip_rates_p3.hdf"

    #p4
    if not os.path.exists(out_dir / "trip_rates_p4.hdf"):
        tr4 = tr.loc[tr["p"]==4]
        tr4["sic_2_digit"] = tr4.loc[:, "e_code"].apply(lambda x: [46, 47])
        tr4 = tr4.explode("sic_2_digit")
        tr4 = tr4.pivot(index = "sic_2_digit", columns="tfn_at", values="alpha")
        cb.DVector(segmentation=sic, import_data=tr4, zoning_system=tfn_at).save(out_dir / "trip_rates_p4.hdf")
    tr_paths[4] = out_dir / "trip_rates_p4.hdf"

    #p5
    if not os.path.exists(out_dir / "trip_rates_p5.hdf"):
        tr5 = tr.loc[tr["p"]==5]
        tr5_1 = tr5.loc[tr5["e_code"]=="e08"].copy()
        tr5_1["sic_2_digit"] = 86
        tr5_2 = tr5.loc[tr5["e_code"]=="e09"].copy()
        tr5_2["sic_2_digit"] = tr5_2.loc[:, "e_code"].apply(lambda x: [64, 65, 66, 68, 69, 75, 77, 79, 80, 95, 96])
        tr5_2 = tr5_2.explode("sic_2_digit")
        tr5_3 = tr5.loc[tr5["e_code"]=="e11"].copy()
        tr5_3["sic_2_digit"] = 56
        tr5 = pd.concat([tr5_1,tr5_2,tr5_3])
        tr5 = tr5.pivot(index = "sic_2_digit", columns="tfn_at", values="alpha")
        cb.DVector(segmentation=sic, import_data=tr5, zoning_system=tfn_at).save(out_dir / "trip_rates_p5.hdf")
    tr_paths[5] = out_dir / "trip_rates_p5.hdf"

    #p6
    if not os.path.exists(out_dir / "trip_rates_p6.hdf"):
        tr6 = tr.loc[tr["p"]==6]
        tr6["sic_2_digit"] = tr6["e_code"].apply(lambda x: [90, 91, 92, 93, 94])
        tr6 = tr6.explode("sic_2_digit")
        tr6 = tr6.pivot(index = "sic_2_digit", columns="tfn_at", values="alpha")
        cb.DVector(segmentation=sic, import_data=tr6, zoning_system=tfn_at).save(out_dir / "trip_rates_p6.hdf")
    tr_paths[6] = out_dir / "trip_rates_p6.hdf"

    #p7
    if not os.path.exists(out_dir / "trip_rates_p7.hdf"):
        tr7 = tr.loc[tr["p"]==7]
        tr7["total"] = 1
        tr7 = tr7.pivot(index = "total", columns="tfn_at", values="alpha")
        tr7.index = tr7.index.astype(int)
        cb.DVector(segmentation=total, import_data=tr7, zoning_system=tfn_at).save(out_dir / "trip_rates_p7.hdf")
    tr_paths[7] = out_dir / "trip_rates_p7.hdf"

    #p8
    if not os.path.exists(out_dir / "trip_rates_p8.hdf"):
        tr8 = tr.loc[tr["p"]==8]
        tr8["sic_2_digit"] = tr8.loc[:, "e_code"].apply(lambda x: [2, 3, 55])
        tr8 = tr8.explode("sic_2_digit")
        tr8 = tr8.pivot(index = "sic_2_digit", columns="tfn_at", values="alpha")
        cb.DVector(segmentation=sic, import_data=tr8, zoning_system=tfn_at).save(out_dir / "trip_rates_p8.hdf")        
    tr_paths[8] = out_dir / "trip_rates_p8.hdf"

    hb_attraction_input_paths["trip_rates"] = tr_paths

    # Trip Rate Adjustment 
    dvec_path = out_dir / "trip_rate_adjustments_attractions_hb_fr.hdf"
    if not os.path.exists(dvec_path):
        adj = pd.read_csv(NTS_DIR / "others/trip_rate_adjustments.csv")
        adj = adj.rename(columns={"purpose": "p"}).loc[(adj["pa"]=="p") & (adj["direction"]=="hb_fr")].pivot(index=["p"], columns="gor", values="adj")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p"],
                                                            naming_order=["p"]))
        zoning_system = cb.ZoningSystem.get_zoning("gor")
        adj_dvec = cb.DVector(segmentation=segmentation, import_data=adj, zoning_system=zoning_system)
        adj_dvec.save(dvec_path)
    hb_attraction_input_paths["tr_adj"] = dvec_path

    dvec_path = out_dir / "mode_time_split_attraction_hb_fr_reg.hdf"
    if not os.path.exists(dvec_path):
        mts = pd.read_csv(NTS_DIR / "attractions/hb/mode_time_splits/mode_time_split_attraction_hb_fr_reg.csv")
        mts = mts.loc[mts["uni"]==0]
        mts = mts.rename(columns={"mode": "m", "period": "tp", "purpose": "p"}).pivot(index=["p", "m", "tp"], columns="tfn_at", values="rho")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p", "m", "tp"],
                                                            naming_order=["p", "m", "tp"]))
        zoning_system = cb.ZoningSystem.get_zoning("tfn_at")
        mts_dvec = cb.DVector(segmentation=segmentation, import_data=mts, zoning_system=zoning_system)
        mts_dvec.save(dvec_path)
    hb_attraction_input_paths["mts"] = dvec_path

    dvec_path = out_dir / "mode_time_split_adjustments.hdf"
    if not os.path.exists(dvec_path):
        adj = pd.read_csv(NTS_DIR / "others/mode_time_split_adjustments.csv")
        adj = adj.rename(columns={"purpose": "p", "period": "tp", "mode": "m"}).loc[(adj["pa"]=="a") & (adj["direction"]=="hb_fr")].pivot(index=["p", "tp", "m"], columns="gor", values="adj")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p", "tp", "m"],
                                                            naming_order=["p", "tp", "m"])) # TODO delete and rewrite adj with "a"
        zoning_system = cb.ZoningSystem.get_zoning("gor")
        adj_dvec = cb.DVector(segmentation=segmentation, import_data=adj, zoning_system=zoning_system)
        adj_dvec.save(dvec_path)
    hb_attraction_input_paths["mts_adj"] = dvec_path

    return hb_attraction_input_paths

if __name__ == "__main__":
    create_hb_production_input()
    create_hb_attraction_input()