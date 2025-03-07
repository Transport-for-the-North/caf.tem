import caf.base as cb
import pandas as pd
import os
from typing import Union, Dict

from pathlib import Path

# # # HB PRODUCTION # # #
def create_hb_production_input() -> dict[str, Path]:

    hb_production_input_paths: dict[str, Path]

    NTS_dir = Path(r"I:\NTS\outputs")
    out_dir = Path(r"T:\Yan_Kavana\TEM DLOG\Inputs\01-HBProduction")

    # Trip Rates
    dvec_path = out_dir / "hb_trip_rates_production.hdf"
    hb_production_input_paths["trip_rates"] = dvec_path
    if not os.path.exists(dvec_path):
        tr = pd.read_csv(NTS_dir / "productions/hb/trip_rates/hb_trip_rates_production.csv")
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
        adj = pd.read_csv(NTS_dir / "others/trip_rate_adjustments.csv")
        adj = adj.rename(columns={"purpose": "p"}).loc[(adj["pa"]=="p") & (adj["direction"]=="hb_fr")].pivot(index=["p"], columns="gor", values="adj")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p"],
                                                            naming_order=["p"]))
        zoning_system = cb.ZoningSystem.get_zoning("gor")
        adj_dvec = cb.DVector(segmentation=segmentation, import_data=adj, zoning_system=zoning_system)
        adj_dvec.save(dvec_path)

    # Mode Time Split
    dvec_path = out_dir / "hb_mode_time_split_production_fr_reg.hdf"
    hb_production_input_paths["mode_time_splits"] = dvec_path
    if not os.path.exists(dvec_path):
        mts = pd.read_csv(NTS_dir / "productions/hb/mode_time_splits/hb_mode_time_split_production_fr_reg.csv")
        mts = mts.rename(columns={"mode": "m", "period": "tp", "purpose": "p"}).pivot(index=["p", "m", "tp", "hh_type"], columns="tfn_at", values="rho")
        segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p", "m", "tp", "hh_type"],
                                                            naming_order=["p", "m", "tp", "hh_type"]))
        zoning_system = cb.ZoningSystem.get_zoning("tfn_at")
        mts_dvec = cb.DVector(segmentation=segmentation, import_data=mts, zoning_system=zoning_system)
        mts_dvec.save(dvec_path)

    return hb_production_input_paths

# # # HB ATTRACTION # # #
def create_hb_attraction_input() -> dict:

    hb_attraction_input_paths = {}

    

    return hb_attraction_input_paths