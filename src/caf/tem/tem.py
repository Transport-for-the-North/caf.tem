"""Trip End Model (TEM) main class and interface.

This module defines the main TEM class, which coordinates the setup and execution of
the Home-Based (HB) and Non-Home-Based (NHB) production and attraction models.
It provides methods for validating input years, initializing child models, and
managing model configuration and outputs.
"""

from __future__ import annotations

# Built-Ins
import os
from pathlib import Path
from typing import Any, Literal

# Third Party
import caf.base as cb
import pandas as pd
from caf.base.segments import SegmentsSuper

# Local Imports
from caf.tem.attraction_models import AttractionModel
from caf.tem.inputs import (
    Landuse,
    Scenarios,
    TEMExportPaths,
    HBProdParams,
    AttrParams,
    NHBProdParams,
)
from caf.tem.production_models import HBProductionModel, NHBProductionModel


class TEM:
    """
    The Trip End Model (TEM) for the caf.tem package.

    This class manages the configuration, validation, and orchestration of the
    Home-Based (HB) and Non-Home-Based (NHB) production and attraction models.
    It provides methods to initialize and run each sub-model, and ensures that
    all input data is consistent and correctly segmented.

    Attributes
    ----------
    model_years: dict[int]
        The years to run the TEM for.
    scenario : Scenarios
        The scenario for the model run (e.g., Core, High, Low, Regional, Technology).
    output_zoning : cb.ZoningSystem
        The zoning system for model outputs.
    agg_zoning : str
        The aggregation zoning system for trip rate etc. application.
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
        scenario: Scenarios,
        output_zoning: cb.ZoningSystem,
        agg_zoning: cb.ZoningSystem,
        iteration_name: str,
        export_home: Path,
        return_segmentation: list[str] | cb.Segmentation,
        trans_file: Path,
    ):
        self.years = model_years
        self._scenario = Scenarios(scenario)
        self._output_zoning = output_zoning
        self._agg_zoning = agg_zoning
        self._iteration_name = iteration_name
        self._export_paths = TEMExportPaths(
            model_years,
            self._scenario,
            iteration_name,
            export_home,
            output_zoning,
            agg_zoning,
        )
        if isinstance(return_segmentation, cb.Segmentation):
            self._return_segmentation = return_segmentation
        else:
            self._return_segmentation = cb.Segmentation(
                cb.SegmentationInput(
                    enum_segments=[SegmentsSuper(i) for i in return_segmentation],
                    naming_order=return_segmentation,
                )
            )
        self._zone_trans = pd.read_csv(trans_file)

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
        ValueError
            If there are extra or missing years in the input dictionary.
        """
        years_set = set(self.years)
        dict_years_set = set(to_check.keys())
        extra = dict_years_set.difference(years_set)
        if len(extra) > 0:
            raise ValueError(
                f"There are years in the {dict_name} input not in "
                f"expected years. Extra years are {extra}."
            )
        missing = years_set.difference(dict_years_set)
        if len(missing) > 0:
            raise ValueError(
                f"There are years missing from {dict_name} input "
                f"Missing years are {missing}."
            )

    def hb_production_model(
        self, population: dict[int, Landuse], params: HBProdParams
    ) -> HBProductionModel:
        """
        Initialize and return the Home-Based (HB) Production Model.

        This method sets up the HBProductionModel with the provided population and trip rate data,
        mode-time splits, and optional adjustment and return-home files.

        Parameters
        ----------
        population : dict[int, Landuse]
            Dictionary mapping year to Landuse objects for population.
        trip_rates_path : Path
            Path to the production trip rates file.
        mode_time_splits_path : Path
            Path to the mode-time splits file.
        phi_factors_path : Path, optional
            Path to phi factor files for return-home calculations.
        mts_return_home_path : Path, optional
            Path to MTS return-home DVector file.
        mts_return_home_adj_factor_path : Path, optional
            Path to adjustment factors for MTS return-home.
        adjustment_path : Path, optional
            Path to adjustment factors for trip rates.
        mts_adj_path : Path, optional
            Path to adjustment factors for MTS.

        Returns
        -------
        HBProductionModel
            An initialized HBProductionModel object.
        """
        self.check_years(population, "population")
        self.hb_prod_model = HBProductionModel(
            params=params,
            model=self._export_paths.hb_production,
            population=population,
            tem_segmentation=self._return_segmentation,
            translation=self._zone_trans,
        )

        return self.hb_prod_model

    def attraction_model(
        self,
        emp_landuse: dict[int, Landuse],
        hh_landuse: dict[int, Landuse],
        params: AttrParams,
        origin: Literal["hb", "nhb"] = "hb",
    ) -> AttractionModel:
        """
        Initialize and return the Attraction Model (HB or NHB).

        This method sets up the AttractionModel with the provided trip rates, land use data,
        mode-time splits, and optional adjustment and return-home files.

        Parameters
        ----------
        trip_rates_paths : dict[int, Path]
            Dictionary mapping purpose to trip rates file paths.
        emp_landuse : dict[int, Landuse]
            Dictionary mapping year to employment Landuse objects.
        hh_landuse : dict[int, Landuse]
            Dictionary mapping year to household Landuse objects.
        mode_time_splits_path : Path
            Path to the mode-time splits file.
        balance_production : bool, optional
            Whether to balance attractions to productions (default: True).
        trip_rate_adjustment_path : Path, optional
            Path to adjustment factors for trip rates.
        mode_time_splits_adjustment_path : Path, optional
            Path to adjustment factors for mode-time splits.
        mts_uni_path : Path, optional
            Path to university-specific MTS data.
        mts_return_home_path : Path, optional
            Path to MTS return-home DVector file.
        mts_return_home_adj_factor_path : Path, optional
            Path to adjustment factors for MTS return-home.
        phi_factors_path : Path, optional
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
        self.attr_model = AttractionModel(
            production_model=(
                self._export_paths.hb_production
                if origin == "hb"
                else self._export_paths.nhb_production
            ),
            model=(
                self._export_paths.hb_attraction
                if origin == "hb"
                else self._export_paths.nhb_attraction
            ),
            params=params,
            emp_landuse=emp_landuse,
            hh_landuse=hh_landuse,
            tem_segmentation=self._return_segmentation,
            model_zoning=self._output_zoning,
            agg_zoning=self._agg_zoning,
            translation=self._zone_trans,
        )

        return self.attr_model

    def nhb_production_model(
        self,
        params: NHBProdParams,
    ) -> NHBProductionModel:
        """
        Initialize and return the Non-Home-Based (NHB) Production Model.

        This method sets up the NHBProductionModel with the provided trip rates and mode-time splits.

        Parameters
        ----------
        trip_rates_path : Path
            Path to the NHB production trip rates file.
        mode_time_splits_path : Path
            Path to the mode-time splits file.
        balance_production : bool, optional
            Whether to balance production totals to match attractions (default: True).

        Returns
        -------
        NHBProductionModel
            An initialized NHBProductionModel object.
        """
        return NHBProductionModel(
            hb_attraction_model=self._export_paths.hb_attraction,
            model=self._export_paths.nhb_production,
            params=params,
            return_segmentation=self._return_segmentation,
        )
