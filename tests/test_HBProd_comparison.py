# -*- coding: utf-8 -*-
"""Tests for the {} module"""
# Built-Ins
from typing import Any
import caf.base as cb
import caf.tem as ct
import pandas as pd
import os
import datetime
from pathlib import Path

# Third Party
import pytest


# Local Imports
# pylint: disable=import-error,wrong-import-position

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #


# # # FIXTURES # # #


# # # TESTS # # #
class InputSetup:

    def population_landuse_input():
        """Equivalent population data
        """
        dvec_path = r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\lu_pop_2023.hdf"
        if not os.path.exists(dvec_path):
            pop = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\lu_pop_2023.csv")
            pop = pop.set_index(["gender_3", "aws", "ns_sec", "soc", "hh_type"]).drop(columns=["adult_nssec"])
            segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["gender_3", "aws", "ns_sec", "soc", "hh_type"],
                                                    naming_order=["gender_3", "aws", "ns_sec", "soc", "hh_type"]))
            zoning_system = cb.ZoningSystem.get_zoning("lsoa_2021")
            pop_dvec = cb.DVector(segmentation=segmentation, import_data=pop, zoning_system=zoning_system)
            pop_dvec.save(dvec_path)
        else:
            pop = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\lu_pop_2023.csv")
            pop = pop.set_index(["gender_3", "aws", "ns_sec", "soc", "hh_type"]).drop(columns=["adult_nssec"])
            pop_dvec = cb.DVector.load(dvec_path)

        assert pop.sum().sum() - pop_dvec.data.sum().sum() < 0.01


    def trip_rates_input():
        """Equivalent trip rates input data
        """
        dvec_path = r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\hb_trip_rates_production.hdf"
        if not os.path.exists(dvec_path):
            tr = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\hb_trip_rates_production.csv")
            tr = tr.rename(columns={"gender": "gender_3", "ns": "ns_sec", "purpose": "p"}).pivot(index=["gender_3", "aws", "ns_sec", "soc", "hh_type", "p"], columns="tfn_at", values="beta")
            segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["gender_3", "aws", "ns_sec", "soc", "hh_type", "p"],
                                                                naming_order=["gender_3", "aws", "ns_sec", "soc", "hh_type", "p"]))
            zoning_system = cb.ZoningSystem.get_zoning("tfn_at")
            tr_dvec = cb.DVector(segmentation=segmentation, import_data=tr, zoning_system=zoning_system)
            tr_dvec.save(dvec_path)
        else:
            tr = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\hb_trip_rates_production.csv")
            tr = tr.rename(columns={"gender": "gender_3", "ns": "ns_sec", "purpose": "p"}).pivot(index=["gender_3", "aws", "ns_sec", "soc", "hh_type", "p"], columns="tfn_at", values="beta")
            tr_dvec = cb.DVector.load(dvec_path)
        assert tr.sum().sum() - tr_dvec.data.sum().sum() < 0.01


    def adjustment_input():
        """Equivalent adjustment factors
        """
        dvec_path = r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\trip_rate_adjustments_production_hb_fr.hdf"
        if not os.path.exists(dvec_path):
            adj = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\trip_rate_adjustments.csv")
            adj = adj.rename(columns={"purpose": "p"}).loc[(adj["pa"]=="p") & (adj["direction"]=="hb_fr")].pivot(index=["p"], columns="gor", values="adj")
            segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p"],
                                                                naming_order=["p"]))
            zoning_system = cb.ZoningSystem.get_zoning("gor")
            adj_dvec = cb.DVector(segmentation=segmentation, import_data=adj, zoning_system=zoning_system)
            adj_dvec.save(dvec_path)
        else:
            adj = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\trip_rate_adjustments.csv")
            adj = adj.rename(columns={"purpose": "p"}).loc[(adj["pa"]=="p") & (adj["direction"]=="hb_fr")].pivot(index=["p"], columns="gor", values="adj")
            adj_dvec = cb.DVector.load(dvec_path)
        assert adj.sum().sum() - adj_dvec.data.sum().sum() < 0.01


    def mts_input():
        """Equivalent mode time split input
        """
        dvec_path = r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\mode_time_split_production_hb_fr_reg.hdf"
        if not os.path.exists(dvec_path):
            mts = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\mode_time_split_production_hb_fr_reg.csv")
            mts = mts.rename(columns={"mode": "m", "period": "tp", "purpose": "p"}).pivot(index=["p", "m", "tp", "hh_type"], columns="tfn_at", values="rho")
            segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=["p", "m", "tp", "hh_type"],
                                                                naming_order=["p", "m", "tp", "hh_type"]))
            zoning_system = cb.ZoningSystem.get_zoning("tfn_at")
            mts_dvec = cb.DVector(segmentation=segmentation, import_data=mts, zoning_system=zoning_system)
            mts_dvec.save(dvec_path)
        else:
            mts = pd.read_csv(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input\mode_time_split_production_hb_fr_reg.csv")
            mts = mts.rename(columns={"mode": "m", "period": "tp", "purpose": "p"}).pivot(index=["p", "m", "tp", "hh_type"], columns="tfn_at", values="rho")
            mts_dvec = cb.DVector.load(dvec_path)

        assert mts.sum().sum() - mts_dvec.data.sum().sum() < 0.01

def model_setup():
    # Create TEM model
    tem = ct.TEM(
        model_years=[2023],
        scenario="Core",
        output_zoning="gor",
        iteration_name=datetime.datetime.now().ctime(),
        export_home=r"T:\ThomasPrince\TEM Input\comparison\caf.tem output",
        return_segmentation=["hh_type", "p", "m", "tp"]
    )

    # Create HBProd Model
    input_dir = Path(r"T:\ThomasPrince\TEM Input\comparison\01_HBProduction\input")
    tem.HBProductionModel(
        population_paths={2023: input_dir / "lu_pop_2023.hdf"},
        trip_rates_path=input_dir / "hb_trip_rates_production.hdf",
        mode_time_splits_path=input_dir / "mode_time_split_production_hb_fr_reg.hdf",
        adjustment_path=input_dir / "trip_rate_adjustments_production_hb_fr.hdf"
    )

    return tem

class OutputCheck:
    def check_

if __name__=="__main__":
    # Assert input sums are close
    InputSetup.population_landuse_input()
    InputSetup.trip_rates_input()
    InputSetup.adjustment_input()
    InputSetup.mts_input()

    tem = model_setup()
    tem.hb_production_model.run()

    OutputCheck