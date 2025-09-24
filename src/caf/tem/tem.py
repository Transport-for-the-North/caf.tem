"""Trip End Model (TEM) main class and interface.

This module defines the main TEM class, which coordinates the setup and execution of
the Home-Based (HB) and Non-Home-Based (NHB) production and attraction models.
It provides methods for validating input years, initializing child models, and
managing model configuration and outputs.
"""

from __future__ import annotations
import os
from typing import Literal, Any
import pandas as pd

import caf.base as cb
from caf.tem.inputs import TEMExportPaths, Scenarios, Landuse
from caf.tem.attraction_models import AttractionModel
from caf.tem.production_models import HBProductionModel, NHBProductionModel


# pylint: disable =too-many-positional-arguments,too-many-arguments
class TEM:
    """
    The Trip End Model (TEM) for the caf.tem package.

    This class manages the configuration, validation, and orchestration of the
    Home-Based (HB) and Non-Home-Based (NHB) production and attraction models.
    It provides methods to initialize and run each sub-model, and ensures that
    all input data is consistent and correctly segmented.

    Attributes
    ----------
    years : list[int]
        The years to run the TEM for.
    scenario : Scenarios
        The scenario for the model run (e.g., Core, High, Low, Regional, Technology).
    output_zoning : cb.ZoningSystem
        The zoning system for model outputs.
    agg_zoning : str
        The aggregation zoning system for reporting.
    iteration_name : str
        A name for this TEM output run.
    export_paths : TEMExportPaths
        Object managing export and report paths for all sub-models.
    return_segmentation : cb.Segmentation
        Segmentation to use for return trips and outputs.
    zone_trans : pd.DataFrame
        DataFrame mapping between different zoning systems.
    hb_production_model : HBProductionModel or None
        The Home-Based Production Model instance.
    hb_attraction_model : AttractionModel or None
        The Home-Based Attraction Model instance.
    nhb_production_model : NHBProductionModel or None
        The Non-Home-Based Production Model instance.
    nhb_attraction_model : AttractionModel or None
        The Non-Home-Based Attraction Model instance.
    attraction_model : AttractionModel or None
        The currently active Attraction Model instance.
    """

    def __init__(
        self,
        model_years: list[int],
        scenario: str,
        output_zoning: cb.ZoningSystem,
        agg_zoning: str,
        iteration_name: str,
        export_home: os.PathLike,
        return_segmentation: list[str] | cb.Segmentation,
        trans_file: os.PathLike,
    ):
        """
        Initialize the TEM class and set up configuration and paths.

        Parameters
        ----------
        model_years : list[int]
            The years to run the TEM for.
        scenario : str
            The scenario name (must match a value in Scenarios).
        output_zoning : cb.ZoningSystem
            The zoning system for model outputs.
        agg_zoning : str
            The aggregation zoning system for reporting.
        iteration_name : str
            A name for this TEM output run.
        export_home : os.PathLike
            The parent directory for exports of this TEM.
        return_segmentation : list[str] or cb.Segmentation
            Segmentation(s) to use for return trips and outputs.
        trans_file : os.PathLike
            Path to the zone translation CSV file.
        """
        self.years = model_years
        self.scenario = Scenarios(scenario)
        self.output_zoning = output_zoning
        self.agg_zoning = agg_zoning
        self.iteration_name = iteration_name
        self.export_paths = TEMExportPaths(
            model_years,
            self.scenario,
            iteration_name,
            export_home,
            output_zoning,
            agg_zoning,
        )
        if isinstance(return_segmentation, cb.Segmentation):
            self.return_segmentation = return_segmentation
        else:
            self.return_segmentation = cb.Segmentation(
                cb.SegmentationInput(
                    enum_segments=return_segmentation, naming_order=return_segmentation
                )
            )
        self.zone_trans = pd.read_csv(trans_file)

        self.hb_production_model: HBProductionModel = None
        self.hb_attraction_model: AttractionModel = None
        self.nhb_production_model: NHBProductionModel = None
        self.nhb_attraction_model: AttractionModel = None
        self.attraction_model: AttractionModel = None

    def check_years(self, to_check: dict[int, Any], dict_name: str):
        """
        Validate that the years in a provided dictionary match the model's expected years.

        Parameters
        ----------
        to_check : dict[int, Any]
            A dictionary keyed by year.
        dict_name : str
            A descriptive name of the dictionary being checked (used in error messages).

        Raises
        ------
        AttributeError
            If there are extra or missing years in the input dictionary.
        """
        years_set = set(self.years)
        dict_years_set = set(to_check.keys())
        extra = dict_years_set.difference(years_set)
        if len(extra) > 0:
            raise AttributeError(
                f"There are years in the {dict_name} input not in "
                f"expected years. Extra years are {extra}."
            )
        missing = years_set.difference(dict_years_set)
        if len(missing) > 0:
            raise AttributeError(
                f"There are years missing from {dict_name} input "
                f"Missing years are {missing}."
            )

    def HBProductionModel(
        self,
        population: dict[int, Landuse],
        trip_rates_path: os.PathLike,
        mode_time_splits_path: os.PathLike,
        phi_factors_path: os.PathLike | None = None,
        mts_return_home_path: os.PathLike | None = None,
        mts_return_home_adj_factor_path: os.PathLike | None = None,
        adjustment_path: os.PathLike = None,
        mts_adj_path: os.PathLike = None,
    ) -> HBProductionModel:
        """
        Initialize and return the Home-Based (HB) Production Model.

        This method sets up the HBProductionModel with the provided population and trip rate data,
        mode-time splits, and optional adjustment and return-home files.

        Parameters
        ----------
        population : dict[int, Landuse]
            Dictionary mapping year to Landuse objects for population.
        trip_rates_path : os.PathLike
            Path to the production trip rates file.
        mode_time_splits_path : os.PathLike
            Path to the mode-time splits file.
        phi_factors_path : os.PathLike, optional
            Path to phi factor files for return-home calculations.
        mts_return_home_path : os.PathLike, optional
            Path to MTS return-home DVector file.
        mts_return_home_adj_factor_path : os.PathLike, optional
            Path to adjustment factors for MTS return-home.
        adjustment_path : os.PathLike, optional
            Path to adjustment factors for trip rates.
        mts_adj_path : os.PathLike, optional
            Path to adjustment factors for MTS.

        Returns
        -------
        HBProductionModel
            An initialized HBProductionModel object.
        """
        self.check_years(population, "population")
        self.hb_production_model = HBProductionModel(
            self.export_paths.hb_production,
            population,
            trip_rates_path,
            adjustment_path,
            mode_time_splits_path,
            mts_adj_path,
            tem_segmentation=self.return_segmentation,
            translation=self.zone_trans,
            phi_factors_path=phi_factors_path,
            mts_return_home_path=mts_return_home_path,
            mts_return_home_adj_factor_path=mts_return_home_adj_factor_path,
        )

        return self.hb_production_model

    def AttractionModel(
        self,
        trip_rates_paths: dict[int, os.PathLike],
        emp_landuse: dict[int, Landuse],
        hh_landuse: dict[int, Landuse],
        mode_time_splits_path: os.PathLike,
        balance_production: bool = True,
        trip_rate_adjustment_path: os.PathLike = None,
        mode_time_splits_adjustment_path: os.PathLike = None,
        mts_uni_path: os.PathLike = None,
        mts_return_home_path: os.PathLike = None,
        mts_return_home_adj_factor_path: os.PathLike = None,
        phi_factors_path: os.PathLike = None,
        origin: Literal["hb", "nhb"] = "hb",
    ) -> AttractionModel:
        """
        Initialize and return the Attraction Model (HB or NHB).

        This method sets up the AttractionModel with the provided trip rates, land use data,
        mode-time splits, and optional adjustment and return-home files.

        Parameters
        ----------
        trip_rates_paths : dict[int, os.PathLike]
            Dictionary mapping purpose to trip rates file paths.
        emp_landuse : dict[int, Landuse]
            Dictionary mapping year to employment Landuse objects.
        hh_landuse : dict[int, Landuse]
            Dictionary mapping year to household Landuse objects.
        mode_time_splits_path : os.PathLike
            Path to the mode-time splits file.
        balance_production : bool, optional
            Whether to balance attractions to productions (default: True).
        trip_rate_adjustment_path : os.PathLike, optional
            Path to adjustment factors for trip rates.
        mode_time_splits_adjustment_path : os.PathLike, optional
            Path to adjustment factors for mode-time splits.
        mts_uni_path : os.PathLike, optional
            Path to university-specific MTS data.
        mts_return_home_path : os.PathLike, optional
            Path to MTS return-home DVector file.
        mts_return_home_adj_factor_path : os.PathLike, optional
            Path to adjustment factors for MTS return-home.
        phi_factors_path : os.PathLike, optional
            Path to phi factor files for return-home calculations.
        origin : Literal["hb", "nhb"], optional
            Whether this is a home-based or non-home-based model (default: "hb").

        Returns
        -------
        AttractionModel
            An initialized AttractionModel object.

        Raises
        ------
        KeyError
            If a trip rates key is not in the expected segmentation values.
        """
        self.check_years(hh_landuse, "households")
        self.check_years(emp_landuse, "employment")
        if origin == "hb":
            self.attraction_model = AttractionModel(
                production_model=self.export_paths.hb_production,
                model=self.export_paths.hb_attraction,
                trip_rates_paths=trip_rates_paths,
                trip_rate_adj_path=trip_rate_adjustment_path,
                balance_production=balance_production,
                emp_landuse=emp_landuse,
                hh_landuse=hh_landuse,
                mts_path=mode_time_splits_path,
                mts_return_home_path=mts_return_home_path,
                mts_adjustment_path=mode_time_splits_adjustment_path,
                mts_return_home_adj_factor_path=mts_return_home_adj_factor_path,
                phi_factors_path=phi_factors_path,
                tem_segmentation=self.return_segmentation,
                mts_uni_path=mts_uni_path,
                model_zoning=self.output_zoning,
                agg_zoning=self.agg_zoning,
                translation=self.zone_trans,
            )
        else:
            self.attraction_model = AttractionModel(
                production_model=self.export_paths.nhb_production,
                model=self.export_paths.nhb_attraction,
                trip_rates_paths=trip_rates_paths,
                trip_rate_adj_path=trip_rate_adjustment_path,
                balance_production=balance_production,
                emp_landuse=emp_landuse,
                hh_landuse=hh_landuse,
                mts_path=mode_time_splits_path,
                mts_return_home_path=mts_return_home_path,
                mts_adjustment_path=mode_time_splits_adjustment_path,
                mts_return_home_adj_factor_path=mts_return_home_adj_factor_path,
                phi_factors_path=phi_factors_path,
                tem_segmentation=self.return_segmentation,
                mts_uni_path=mts_uni_path,
                model_zoning=self.output_zoning,
                agg_zoning=self.agg_zoning,
                translation=self.zone_trans,
            )

        # User Input Test
        for p in trip_rates_paths.keys():
            vals = cb.segmentation.SegmentsSuper("p").get_segment().int_values
            if p not in vals:
                raise KeyError(
                    f"Trip rates key {p} was passed.\nTrip rates keys must be in {vals}"
                )

        return self.attraction_model

    def NHBProductionModel(
        self,
        trip_rates_path: os.PathLike,
        mode_time_splits_path: os.PathLike,
        balance_production: bool = True,
    ) -> NHBProductionModel:
        """
        Initialize and return the Non-Home-Based (NHB) Production Model.

        This method sets up the NHBProductionModel with the provided trip rates and mode-time splits.

        Parameters
        ----------
        trip_rates_path : os.PathLike
            Path to the NHB production trip rates file.
        mode_time_splits_path : os.PathLike
            Path to the mode-time splits file.
        balance_production : bool, optional
            Whether to balance production totals to match attractions (default: True).

        Returns
        -------
        NHBProductionModel
            An initialized NHBProductionModel object.
        """
        self.nhb_production_model = NHBProductionModel(
            self.export_paths.hb_attraction,
            self.export_paths.nhb_production,
            trip_rates_path,
            balance_production,
            mode_time_splits_path,
            self.return_segmentation,
        )

        return self.nhb_production_model


# pylint: enable =too-many-positional-arguments,too-many-arguments

# class TEMInput(BaseConfig):
#     model_years: list[int]
#     scenario: str
#     output_zoning: str
#     agg_zoning: str
#     iteration_name: str
#     export_home: os.PathLike
#     return_segmentation: list[str]
#     trans_file: os.PathLike
#     population_paths: dict[int, Landuse]
#     pop_zoning: str
#     hb_prod_trip_rates_path: os.PathLike
#     hb_prod_mode_time_splits_path: os.PathLike
#     hb_prod_adjustment_path: os.PathLike
#     hb_prod_mts_adj_path: os.PathLike
