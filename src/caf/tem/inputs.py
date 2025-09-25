# -*- coding: utf-8 -*-
"""
Module containing input classes and configuration utilities for trip-end models.

This module provides data containers, path management classes, and configuration
validation for the Trip End Model (TEM) framework. It supports importing and exporting
land use data, scenario management, and standardized output/reporting paths for
production and attraction models.
"""

from __future__ import annotations

import collections
# Built-Ins TODO tidy this file
import enum
import os
import pathlib
import warnings
from dataclasses import dataclass
from typing import Annotated, Literal, NamedTuple

# Third Party
import caf.base as cb
import caf.toolkit as ctk
import pandas as pd
from caf.base.segments import SegmentsSuper
from caf.toolkit import config_base
from pydantic import BeforeValidator, model_validator


# pylint: disable =too-many-positional-arguments,too-few-public-methods
# # # CLASSES # # #
def create_segmentation(seg_list: list[str] | cb.Segmentation):
    """
    Create a cb.Segmentation object from a list of segment names or return the input if already a Segmentation.

    Parameters
    ----------
    seg_list : list[str] or cb.Segmentation
        List of segment names or an existing Segmentation object.

    Returns
    -------
    cb.Segmentation
        The resulting segmentation object.
    """
    if isinstance(seg_list, cb.Segmentation):
        return seg_list
    inp = cb.SegmentationInput(
        enum_segments=[SegmentsSuper(i) for i in seg_list], naming_order=seg_list
    )
    return cb.Segmentation(inp)


def create_zoningsystem(zoning: str | cb.ZoningSystem | list[str | cb.ZoningSystem]):
    """
    Create a cb.ZoningSystem object (or list of them) from a string, existing ZoningSystem, or list.

    Parameters
    ----------
    zoning : str, cb.ZoningSystem, or list[str, cb.ZoningSystem]
        Zoning system name(s) or object(s).

    Returns
    -------
    cb.ZoningSystem or list[cb.ZoningSystem]
        The resulting zoning system(s).
    """
    if isinstance(zoning, cb.ZoningSystem):
        return zoning
    if isinstance(zoning, list):
        validated_zoning: list[str | cb.ZoningSystem] = []
        for zone in zoning:
            if isinstance(zone, cb.ZoningSystem):
                validated_zoning.append(zone)
            else:
                try:
                    validated_zoning.append(cb.ZoningSystem.get_zoning(zone))
                except FileNotFoundError:
                    validated_zoning.append(zone)
        return validated_zoning
    return cb.ZoningSystem.get_zoning(zoning)


@dataclass
class Landuse:
    """
    Data container for handling different types of land use inputs (e.g., population, employment, households)
    along with associated metadata for processing and transformation.

    Parameters
    ----------
    type : Literal["pop", "emp", "hh"]
        Specifies the type of land use ("pop", "emp", or "hh").
    land_use : os.PathLike or cb.DVector
        Path to land use data or a DVector object.
    trans_tag : str, optional
        Optional tag for transformation processes.
    prefix : str, optional
        Optional prefix for output fields or files.
    segmentation : cb.Segmentation, optional
        Segmentation object for splitting land use data.
    geographies : str or list[str], optional
        Name(s) of the geographical unit(s) for the land use data.
    out_zoning : cb.ZoningSystem, str, list, or None, optional
        Zoning system(s) for mapping or output.
    """

    type: Literal["pop", "emp", "hh"]
    land_use: os.PathLike | cb.DVector
    trans_tag: str | None = None
    prefix: str | None = None
    segmentation: Annotated[cb.Segmentation, BeforeValidator(create_segmentation)] | None = (
        None
    )
    geographies: str | list[str] | None = None
    out_zoning: (
        cb.ZoningSystem
        | str
        | Annotated[list[cb.ZoningSystem | str], BeforeValidator(func=create_zoningsystem)]
        | None
    ) = None
    # pylint: disable = too-many-branches
    def read_landuse(
        self,
        translation: pd.DataFrame | None = None,
        init_zoning: cb.ZoningSystem | None = None,
        model_zoning: cb.ZoningSystem | None = None,
    ):
        """
        Read and process land use data from the specified source, applying optional translation and
        aligning it with the model's zoning system if provided.

        Parameters
        ----------
        translation : pd.DataFrame or None, optional
            Translation table for mapping zones.
        init_zoning : cb.ZoningSystem or None, optional
            Initial zoning system for the data.
        model_zoning : cb.ZoningSystem or None, optional
            Model zoning system for alignment.

        Returns
        -------
        cb.DVector
            The processed land use data as a DVector.
        """
        if isinstance(self.land_use, cb.DVector):
            return self.land_use
        source_path = pathlib.Path(self.land_use)
        if isinstance(self.segmentation, list):
            self.segmentation = cb.Segmentation(
                cb.SegmentationInput(
                    enum_segments=self.segmentation, naming_order=self.segmentation
                )
            )
        if source_path.is_file():
            lu = cb.DVector.load(source_path)
            lu = lu.aggregate(self.segmentation)
        else:
            dvecs = []
            segmentation = self.segmentation
            if isinstance(self.geographies, list):
                for geo in self.geographies:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=UserWarning)
                        if self.prefix is not None:
                            dvec = cb.DVector.load(source_path / self.prefix.format(geo))
                        else:
                            raise ValueError("Prefix must be provided if landuse is a folder.")
                        if segmentation is None:
                            segmentation = dvec.segmentation
                        dvecs.append(dvec.aggregate(segmentation))
            else:
                raise TypeError(
                    "If landuse is given as a folder, a list of geographies must be provided, "
                    "and a prefix for file names."
                )
            lu_data = pd.concat([dvec.data for dvec in dvecs], axis=1)
            # mypy
            assert segmentation is not None
            lu = cb.DVector(
                segmentation=segmentation,
                zoning_system=init_zoning,
                import_data=lu_data,
            )
        if self.out_zoning is not None:
            if isinstance(self.out_zoning, list):
                factor_col = (
                    f"{lu.zoning_system.translation_column_name(model_zoning)}_{self.type}"
                )
                lu = lu.trans_and_comp(self.out_zoning, translation, factor_col)
            else:
                if isinstance(self.out_zoning, str):
                    self.out_zoning = cb.ZoningSystem.get_zoning(self.out_zoning)
                lu = lu.translate_zoning(self.out_zoning, trans_vector=translation)
        self.land_use = lu
        return lu
    # pylint: enable = too-many-branches


@enum.unique
class Scenarios(enum.Enum):
    """
    Enumeration of scenario names for model runs.

    Members
    -------
    CORE : str
        Core scenario.
    HIGH : str
        High growth scenario.
    LOW : str
        Low growth scenario.
    REGIONAL : str
        Regional scenario.
    TECHNOLOGY : str
        Technology scenario.
    """

    CORE = "Core"
    HIGH = "High"
    LOW = "Low"
    REGIONAL = "Regional"
    TECHNOLOGY = "Technology"


class ExportPathsOutputs(NamedTuple):
    """Paths for outputs to be saved to."""
    home: pathlib.Path
    pure_demand: dict[int, os.PathLike]
    pure_demand_adj: dict[int, os.PathLike]
    mts_demand: dict[int, os.PathLike]
    mts_demand_adj: dict[int, os.PathLike]
    tem_segmented: dict[int, os.PathLike]
    tem_segmented_return_home: dict[int, os.PathLike]
    tem_segmented_from_home: dict[int, os.PathLike]


class ExportPathsReports(NamedTuple):
    """Paths for reports to be saved to."""
    home: pathlib.Path
    pure_demand: ReportPaths
    pure_demand_adj: ReportPaths
    mts_demand: ReportPaths
    mts_demand_adj: ReportPaths
    tem_segmented: ReportPaths
    tem_segmented_return_home: ReportPaths
    tem_segmented_from_home: ReportPaths


class ReportPaths(NamedTuple):
    """Lower level reports paths."""
    segment_total: dict[int, os.PathLike]
    ca_sector: dict[int, os.PathLike]
    ie_sector: dict[int, os.PathLike]
    lad_report: dict[int, os.PathLike]


class TEMModelPaths:
    """
    Base path management class for all TEM models.

    This class defines the structure and naming conventions for export and report
    paths used by all TEM models, ensuring consistency across outputs.

    Attributes
    ----------
    path_years : list[int]
        List of years for which paths are generated.
    export_home : os.PathLike
        Home directory for all exports.
    report_home : os.PathLike
        Home directory for all reports.
    export_paths : namedtuple
        Named tuple of export paths for various outputs.
    report_paths : namedtuple
        Named tuple of report paths for various outputs.
    """

    # Segmentation names
    _pure_demand = "pure_demand"
    _pure_demand_adj = "pure_demand_adj"
    _mts_demand = "mts_demand"
    _mts_demand_adj = "mts_demand_adj"
    _tem_segmented = "tem_segmented"
    _tem_segmented_return_home = "tem_segmented_to"
    _tem_segmented_from_home = "tem_segmented_fr"

    # Report names
    _segment_totals_report_name = "segment_totals"
    _ca_sector_report_name = "ca_sector_totals"
    _ie_sector_report_name = "ie_sector_totals"
    _lad_report_name = "lad_totals"

    # Define output fnames
    _base_output_fname = "%s_%s_%s_%d.dvec"
    _base_report_fname = "%s_%s_%d_%s.csv"

    def __init__(
        self,
        path_years: list[int],
        export_home: os.PathLike,
        report_home: os.PathLike,
        model_zoning: cb.ZoningSystem,
        agg_zoning: cb.ZoningSystem,
        _trip_origin,
    ):
        """
        Initialize the TEMModelPaths and validate input directories.

        Parameters
        ----------
        path_years : list[int]
            Years for which the model will run.
        export_home : os.PathLike
            Directory for export outputs.
        report_home : os.PathLike
            Directory for report outputs.
        model_zoning : str
            Name of the model zoning system.
        agg_zoning : str
            Name of the aggregation zoning system.
        _trip_origin : str
            Trip origin type (e.g., 'hb' or 'nhb').
        """
        # Assign attributes
        self.path_years = path_years
        self.export_home = pathlib.Path(export_home)
        self.report_home = pathlib.Path(report_home)
        self._trip_origin = _trip_origin
        self.model_zoning = model_zoning
        self.agg_zoning = agg_zoning
        self.export_paths: ExportPathsOutputs | None = None
        self.report_paths: ExportPathsReports | None = None

        # Make sure paths exist
        if not self.export_home.is_dir():
            raise FileNotFoundError(f"{export_home} is not a valid dir.")
        if not self.report_home.is_dir():
            raise FileNotFoundError(f"{report_home} is not a valid dir.")

        # Make sure variables that need to be overwritten, are
        if self._trip_origin is None:
            raise ValueError(
                "When inheriting TEMModelPaths the class variable "
                "_trip_origin needs to be set. This is usually set to "
                "'hb', or 'nhb' to reflect the type of model being run."
            )

    def _create_export_paths(self) -> None:
        """
        Create and assign export paths for all model outputs.

        Returns
        -------
        None
        """
        # Init
        base_fname = self._base_output_fname
        fname_parts = [self._trip_origin, self.model_zoning.name]

        pure_demand_paths: dict[int, os.PathLike] = dict()
        pure_demand_adj_paths: dict[int, os.PathLike] = dict()
        mts_demand_paths: dict[int, os.PathLike] = dict()
        mts_demand_adj_paths: dict[int, os.PathLike] = dict()
        tem_segmented_paths: dict[int, os.PathLike] = dict()
        tem_segmented_return_home_paths: dict[int, os.PathLike] = dict()
        tem_segmented_from_home_paths: dict[int, os.PathLike] = dict()

        for year in self.path_years:
            # Pure demand path
            fname = base_fname % (*fname_parts, self._pure_demand, year)
            pure_demand_paths[year] = self.export_home / fname

            # Pure demand path adj
            fname = base_fname % (*fname_parts, self._pure_demand_adj, year)
            pure_demand_adj_paths[year] = self.export_home / fname

            # MTS demand path
            fname = base_fname % (*fname_parts, self._mts_demand, year)
            mts_demand_paths[year] = self.export_home / fname

            # MTS demand path adj
            fname = base_fname % (*fname_parts, self._mts_demand_adj, year)
            mts_demand_adj_paths[year] = self.export_home / fname

            # TEM Segmented path
            fname = base_fname % (*fname_parts, self._tem_segmented, year)
            tem_segmented_paths[year] = self.export_home / fname

            # TEM Segmented path return home
            fname = base_fname % (*fname_parts, self._tem_segmented_return_home, year)
            tem_segmented_return_home_paths[year] = self.export_home / fname

            # TEM Segmented path from home
            fname = base_fname % (*fname_parts, self._tem_segmented_from_home, year)
            tem_segmented_from_home_paths[year] = self.export_home / fname

        # Create the export_paths class
        self.export_paths = ExportPathsOutputs(
            home=self.export_home,
            pure_demand=pure_demand_paths,
            pure_demand_adj=pure_demand_adj_paths,
            mts_demand=mts_demand_paths,
            mts_demand_adj=mts_demand_adj_paths,
            tem_segmented=tem_segmented_paths,
            tem_segmented_return_home=tem_segmented_return_home_paths,
            tem_segmented_from_home=tem_segmented_from_home_paths,
        )

    def _create_report_paths(self) -> None:
        """
        Create and assign report paths for all model outputs.

        Returns
        -------
        None
        """
        self.report_paths = ExportPathsReports(
            home=self.report_home,
            pure_demand=self._generate_report_paths(self._pure_demand),
            pure_demand_adj=self._generate_report_paths(self._pure_demand_adj),
            mts_demand=self._generate_report_paths(self._mts_demand),
            mts_demand_adj=self._generate_report_paths(self._mts_demand_adj),
            tem_segmented=self._generate_report_paths(self._tem_segmented),
            tem_segmented_return_home=self._generate_report_paths(
                self._tem_segmented_return_home
            ),
            tem_segmented_from_home=self._generate_report_paths(self._tem_segmented_from_home),
        )

    def _generate_report_paths(
        self,
        report_name: str,
    ) -> ReportPaths:
        """
        Generate report file paths for each year and report type.

        Parameters
        ----------
        report_name : str
            Name to use in the report filename.

        Returns
        -------
        ReportPaths
            Named tuple of dictionaries mapping years to report file paths.
        """
        # Init
        base_fname = self._base_report_fname
        fname_parts = [self._trip_origin, report_name]

        segment_total_paths: dict[int, os.PathLike] = dict()
        ca_sector_paths: dict[int, os.PathLike] = dict()
        ie_sector_paths: dict[int, os.PathLike] = dict()
        lad_paths: dict[int, os.PathLike] = dict()

        # Create the paths for each year
        for year in self.path_years:
            # Segment totals
            fname = base_fname % (*fname_parts, year, self._segment_totals_report_name)
            segment_total_paths[year] = self.report_home / fname

            # CA sector totals
            fname = base_fname % (*fname_parts, year, self._ca_sector_report_name)
            ca_sector_paths[year] = self.report_home / fname

            # IE sector totals
            fname = base_fname % (*fname_parts, year, self._ie_sector_report_name)
            ie_sector_paths[year] = self.report_home / fname

            # LAD Reports
            fname = base_fname % (*fname_parts, year, self._lad_report_name)
            lad_paths[year] = self.report_home / fname

        return ReportPaths(
            segment_total=segment_total_paths,
            ca_sector=ca_sector_paths,
            ie_sector=ie_sector_paths,
            lad_report=lad_paths,
        )


class ProductionModelPaths(TEMModelPaths):
    """
    Path management class for the TEM HB Production Model.

    Generates export and report paths for the Home-Based Production Model.

    Attributes
    ----------
    export_paths : namedtuple
        Export paths for model outputs.
    report_paths : namedtuple
        Report paths for model outputs.
    """

    def __init__(self, _trip_origin, *args, **kwargs):
        """
        Initialize and generate export and report paths.

        Parameters
        ----------
        _trip_origin : str
            Trip origin type (e.g., 'hb').
        *args, **kwargs :
            Passed to TEMModelPaths.
        """
        # Set up superclass
        super().__init__(_trip_origin=_trip_origin, *args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()


class AttractionModelPaths(TEMModelPaths):
    """
    Path management class for the TEM NHB Attraction Model.

    Generates export and report paths for the Non-Home-Based Attraction Model.

    Attributes
    ----------
    export_paths : namedtuple
        Export paths for model outputs.
    report_paths : namedtuple
        Report paths for model outputs.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize and generate export and report paths.

        Parameters
        ----------
        *args, **kwargs :
            Passed to TEMModelPaths.
        """
        # Set up superclass
        super().__init__(*args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()


class TEMExportPaths:
    """
    Path management class for all TEM sub-models.

    Builds and stores export and report paths for all sub-models (HB/NHB production and attraction).

    Attributes
    ----------
    path_years : list[int]
        Years for which the model will run.
    scenario : Scenarios
        Scenario name.
    iteration_name : str
        Name of the model iteration.
    export_home : os.PathLike
        Root export directory.
    hb_production : ProductionModelPaths
        Paths for HB production model.
    nhb_production : ProductionModelPaths
        Paths for NHB production model.
    hb_attraction : AttractionModelPaths
        Paths for HB attraction model.
    nhb_attraction : AttractionModelPaths
        Paths for NHB attraction model.
    """

    # Define the names of the export dirs
    _hb_productions_dir = "hb_productions"
    _nhb_productions_dir = "nhb_productions"
    _hb_attractions_dir = "hb_attractions"
    _nhb_attractions_dir = "nhb_attractions"

    _reports_dir = "reports"

    def __init__(
        self,
        path_years: list[int],
        scenario: Scenarios,
        iteration_name: str,
        export_home: os.PathLike,
        model_zoning: cb.ZoningSystem,
        agg_zoning: cb.ZoningSystem,
    ):
        """
        Build export and report paths for all TEM sub-models.

        Parameters
        ----------
        path_years : list[int]
            Years for which the model will run.
        scenario : Scenarios
            Scenario name.
        iteration_name : str
            Name of the model iteration.
        export_home : os.PathLike
            Root export directory.
        model_zoning : str
            Model zoning system name.
        agg_zoning : str
            Aggregation zoning system name.
        """
        # Init
        export_home = pathlib.Path(export_home)
        if not export_home.is_dir():
            raise FileExistsError(f"{export_home} is not a valid directory.")

        self.path_years = path_years
        self.scenario = scenario
        self.iteration_name = iteration_name
        self.export_home = export_home / self.iteration_name / self.scenario.value

        # ## BUILD ALL MODEL PATHS ## #
        # hb productions
        hb_p_export_home = self.export_home / self._hb_productions_dir
        hb_p_report_home = hb_p_export_home / self._reports_dir
        # This creates the parents too so only needed for the lowest level
        hb_p_report_home.mkdir(exist_ok=True, parents=True)

        self.hb_production = ProductionModelPaths(
            path_years=path_years,
            export_home=hb_p_export_home,
            report_home=hb_p_report_home,
            _trip_origin="hb",
            model_zoning=model_zoning,
            agg_zoning=agg_zoning,
        )

        # nhb productions
        nhb_p_export_home = self.export_home / self._nhb_productions_dir
        nhb_p_report_home = nhb_p_export_home / self._reports_dir

        nhb_p_report_home.mkdir(exist_ok=True, parents=True)

        self.nhb_production = ProductionModelPaths(
            path_years=path_years,
            export_home=nhb_p_export_home,
            report_home=nhb_p_report_home,
            _trip_origin="nhb",
            model_zoning=model_zoning,
            agg_zoning=agg_zoning,
        )

        # hb attractions
        hb_a_export_home = self.export_home / self._hb_attractions_dir
        hb_a_report_home = hb_a_export_home / self._reports_dir

        hb_a_report_home.mkdir(exist_ok=True, parents=True)

        self.hb_attraction = AttractionModelPaths(
            path_years=path_years,
            export_home=hb_a_export_home,
            report_home=hb_a_report_home,
            _trip_origin="hb",
            model_zoning=model_zoning,
            agg_zoning=agg_zoning,
        )

        # nhb attractions
        nhb_a_export_home = self.export_home / self._nhb_attractions_dir
        nhb_a_report_home = nhb_a_export_home / self._reports_dir

        nhb_a_report_home.mkdir(exist_ok=True, parents=True)

        self.nhb_attraction = AttractionModelPaths(
            path_years=path_years,
            export_home=nhb_a_export_home,
            report_home=nhb_a_report_home,
            _trip_origin="nhb",
            model_zoning=model_zoning,
            agg_zoning=agg_zoning,
        )


class MainConfig(config_base.BaseConfig):
    """
    Main configuration class for the TEM model.

    Stores all global and model-specific configuration options, validates consistency,
    and supports YAML import/export.

    Attributes
    ----------
    run_hb_prod : bool
        Whether to run the HB production model.
    run_hb_attr : bool
        Whether to run the HB attraction model.
    run_nhb_prod : bool
        Whether to run the NHB production model.
    run_nhb_attr : bool
        Whether to run the NHB attraction model.
    return_home : bool
        Whether to generate return-home trips.
    model_years : list[int]
        List of years for the model run.
    scenario : str
        Scenario name.
    output_zoning : cb.ZoningSystem
        Output zoning system.
    agg_zoning : cb.ZoningSystem
        Aggregation zoning system.
    iteration_name : str
        Model iteration name.
    export_home : pathlib.Path
        Root export directory.
    return_segmentation : cb.Segmentation
        Segmentation for return trips.
    trans_file : pathlib.Path
        Path to translation file.
    export_pure : bool
        Whether to export pure demand.
    export_mts : bool
        Whether to export MTS demand.
    export_tem : bool
        Whether to export TEM-segmented demand.
    export_reports : bool
        Whether to export reports.
    mts_geo_constraint : cb.ZoningSystem or None
        Optional MTS geographic constraint.
    pop : dict[int, Landuse]
        Population land use data by year.
    emp : dict[int, Landuse]
        Employment land use data by year.
    hh : dict[int, Landuse]
        Household land use data by year.
    (plus all model-specific file paths)
    """

    ### options ###
    run_hb_prod: bool
    run_hb_attr: bool
    run_nhb_prod: bool
    run_nhb_attr: bool
    return_home: bool = False
    ### global ###
    model_years: list[int]
    scenario: str
    output_zoning: Annotated[cb.ZoningSystem, BeforeValidator(create_zoningsystem)]
    agg_zoning: Annotated[cb.ZoningSystem, BeforeValidator(create_zoningsystem)]
    iteration_name: str
    export_home: pathlib.Path
    return_segmentation: Annotated[cb.Segmentation, BeforeValidator(create_segmentation)]
    trans_file: pathlib.Path
    export_pure: bool = True
    export_mts: bool = True
    export_tem: bool = True
    export_reports: bool = True
    mts_geo_constraint: (
        Annotated[cb.ZoningSystem, BeforeValidator(create_zoningsystem)] | None
    ) = None
    pop: dict[int, Landuse]
    emp: dict[int, Landuse]
    hh: dict[int, Landuse]
    ### hb_prod ###
    hb_prod_triprates: pathlib.Path
    hb_prod_tr_adj: pathlib.Path | None = None
    hb_prod_mts: pathlib.Path
    hb_prod_mts_adjustment: pathlib.Path | None = None
    hb_prod_phi_factors: pathlib.Path | None = None
    hb_prod_mts_return: pathlib.Path | None = None
    hb_prod_mts_return_adj: pathlib.Path | None = None
    ### hb_attr ###
    hb_attr_triprates: dict[int, pathlib.Path]
    hb_attr_tr_adj: pathlib.Path | None = None
    hb_attr_mts: pathlib.Path
    hb_attr_mts_adj: pathlib.Path | None = None
    hb_attr_mts_uni: pathlib.Path
    balance_hb: bool = True
    hb_attr_phi_factors: pathlib.Path | None = None
    hb_attr_mts_return: pathlib.Path | None = None
    hb_attr_mts_return_adj: pathlib.Path | None = None
    ### nhb_prod ###
    nhb_prod_triprates: pathlib.Path
    nhb_prod_mts: pathlib.Path
    balance_nhb: bool = True
    ### nhb_attr ###
    nhb_attr_triprates: dict[int, pathlib.Path]
    nhb_attr_tr_adj: pathlib.Path | None = None
    nhb_attr_mts: pathlib.Path
    nhb_attr_mts_adj: pathlib.Path | None = None
    nhb_attr_mts_uni: pathlib.Path

    class Config:
        """
        Pydantic configuration for MainConfig.

        Allows arbitrary types and defines JSON encoders for custom objects.
        """

        arbitrary_types_allowed = True
        json_encoders = {
            cb.ZoningSystem: lambda z: z.name,
            cb.Segmentation: lambda z: (
                z.naming_order
                if hasattr(z, "naming_order")
                else list(z) if isinstance(z, list) else str
            ),
        }

    @model_validator(mode="after")
    def phi_factors_if_return(self):
        """
        Validate that phi factors and return-home files are provided if return_home is True.

        Raises
        ------
        ValueError
            If required files are missing for return-home trip generation.
        """
        if self.return_home:
            if self.hb_prod_phi_factors is None:
                raise ValueError(
                    "hb_prod_phi_factors must be provided for return home trips to be generated."
                )
            if self.hb_prod_mts_return is None:
                raise ValueError(
                    "hb_prod_mts_return must be provided for return home trips to be generated."
                )
            if self.hb_attr_phi_factors is None:
                raise ValueError(
                    "hb_attr_phi_factors must be provided for return home trips to be generated."
                )
            if self.hb_attr_mts_return is None:
                raise ValueError(
                    "hb_attr_mts_return must be provided for return home trips to be generated."
                )
        return self

    @model_validator(mode="after")
    def consistent_years(self):
        """
        Validate that population, employment, and household years match model_years.

        Raises
        ------
        ValueError
            If years are inconsistent.
        """
        if set(self.pop.keys()) != set(self.model_years):
            raise ValueError("Population years must match model_years.")
        if set(self.emp.keys()) != set(self.model_years):
            raise ValueError("Employment years must match model_years.")
        if set(self.hh.keys()) != set(self.model_years):
            raise ValueError("Household years must match model_years.")
        return self


# pylint: enable =too-many-positional-arguments,too-few-public-methods

# # # FUNCTIONS # # #
