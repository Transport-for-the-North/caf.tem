# -*- coding: utf-8 -*-
"""
Module containing input classes and configuration utilities for trip-end models.

This module provides data containers, path management classes, and configuration
validation for the Trip End Model (TEM) framework. It supports importing and exporting
land use data, scenario management, and standardized output/reporting paths for
production and attraction models.
"""

from __future__ import annotations

# Built-Ins
# Built-Ins TODO tidy this file
import enum
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, NamedTuple, Protocol

# Third Party
import caf.base as cb
import pandas as pd
from caf.base.segments import SegmentsSuper
from caf.toolkit import config_base
from pydantic import (
    BeforeValidator,
    DirectoryPath,
    FilePath,
    dataclasses,
    model_validator,
)


# # # CLASSES # # #
def _create_segmentation(seg_list: list[str] | cb.Segmentation):
    """
    Create a :class:`cb.Segmentation` object.

    Creates a :class:`cb.Segmentation` object from a list of segment names
     or returns the input if already a Segmentation.

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


def _create_zoningsystem(
    zoning: str | cb.ZoningSystem | list[str | cb.ZoningSystem],
) -> cb.ZoningSystem | list[str | cb.ZoningSystem] | list[Any]:
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
    Data container for handling different types of land use inputs.

    Parameters
    ----------
    type : Literal["pop", "emp", "hh"]
        Specifies the type of land use ("pop", "emp", or "hh").
    land_use : Path or cb.DVector
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
    land_use: Path | cb.DVector
    trans_tag: str | None = None
    prefix: str | None = None
    segmentation: Annotated[cb.Segmentation, BeforeValidator(_create_segmentation)] | None = (
        None
    )
    geographies: str | list[str] | None = None
    out_zoning: (
        cb.ZoningSystem
        | str
        | Annotated[list[cb.ZoningSystem | str], BeforeValidator(func=_create_zoningsystem)]
        | None
    ) = None

    def _load_from_file(
        self, source_path: Path, segmentation: cb.Segmentation | None
    ) -> cb.DVector:
        """Load a DVector from a file and aggregate to `segmentation` if provided."""
        lu = cb.DVector.load(source_path)
        lu = lu.aggregate(segmentation)
        return lu

    def _load_from_folder(
        self,
        source_path: Path,
        segmentation: cb.Segmentation | None,
        init_zoning: cb.ZoningSystem | None,
    ) -> cb.DVector:
        """Load multiple DVector files from a folder for each geography and combine them."""
        if not isinstance(self.geographies, list):
            raise TypeError(
                "If landuse is given as a folder, a list of geographies must be provided, "
                "and a prefix for file names."
            )
        dvecs: list[cb.DVector] = []
        for geo in self.geographies:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                if self.prefix is None:
                    raise ValueError("Prefix must be provided if landuse is a folder.")
                dvec = cb.DVector.load(source_path / self.prefix.format(geo))
                if segmentation is None:
                    segmentation = dvec.segmentation
                dvecs.append(dvec.aggregate(segmentation))
        lu_data = pd.concat([dvec.data for dvec in dvecs], axis=1)
        # mypy
        if segmentation is None:
            raise ValueError("segmentation is required")
        return cb.DVector(
            segmentation=segmentation,
            zoning_system=init_zoning,
            import_data=lu_data,
        )

    def _apply_out_zoning(
        self,
        lu: cb.DVector,
        model_zoning: cb.ZoningSystem | None,
        translation: pd.DataFrame | None,
    ) -> cb.DVector:
        """Apply `self.out_zoning` to `lu`, supporting lists, strings or zoning objects."""
        if self.out_zoning is None:
            return lu
        if isinstance(self.out_zoning, list):
            if not isinstance(lu.zoning_system, cb.ZoningSystem):
                raise TypeError("Read in landuse must be singly zoned to be translated.")
            if model_zoning is None:
                raise ValueError("model_zoning must be provided for comp_zoned output.")
            factor_col = (
                f"{lu.zoning_system.translation_column_name(model_zoning)}_{self.type}"
            )
            return lu.trans_and_comp(self.out_zoning, translation, factor_col)
        out_z = self.out_zoning
        if isinstance(out_z, str):
            out_z = cb.ZoningSystem.get_zoning(out_z)
            self.out_zoning = out_z
        return lu.translate_zoning(out_z, trans_vector=translation)

    def read_landuse(
        self,
        translation: pd.DataFrame | None = None,
        init_zoning: cb.ZoningSystem | None = None,
        model_zoning: cb.ZoningSystem | None = None,
    ):
        """Read and process land use data from the specified source.

        Applies optional translation and aligns it with the model's zoning system if provided.
        """
        if isinstance(self.land_use, cb.DVector):
            return self.land_use

        source_path = Path(self.land_use)

        if source_path.is_file():
            lu = self._load_from_file(source_path, self.segmentation)
        else:
            lu = self._load_from_folder(source_path, self.segmentation, init_zoning)

        lu = self._apply_out_zoning(lu, model_zoning, translation)

        self.land_use = lu
        return lu


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

    home: Path
    pure_demand: dict[int, Path]
    pure_demand_adj: dict[int, Path]
    mts_demand: dict[int, Path]
    mts_demand_adj: dict[int, Path]
    tem_segmented: dict[int, Path]
    tem_segmented_return_home: dict[int, Path]
    tem_segmented_from_home: dict[int, Path]
    tem_segmented_from_home_pm: dict[int, Path]


class ExportPathsReports(NamedTuple):
    """Paths for reports to be saved to."""

    home: Path
    pure_demand: ReportPaths
    pure_demand_adj: ReportPaths
    mts_demand: ReportPaths
    mts_demand_adj: ReportPaths
    tem_segmented: ReportPaths
    tem_segmented_return_home: ReportPaths
    tem_segmented_from_home: ReportPaths


class ReportPaths(NamedTuple):
    """Lower level reports paths."""

    segment_total: dict[int, Path]
    ca_sector: dict[int, Path]
    ie_sector: dict[int, Path]
    lad_report: dict[int, Path]


class TEMModelPaths:
    """
    Base path management class for all TEM models.

    This class defines the structure and naming conventions for export and report
    paths used by all TEM models, ensuring consistency across outputs.

    Attributes
    ----------
    path_years : list[int]
        List of years for which paths are generated.
    export_home : Path
        Home directory for all exports.
    report_home : Path
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
    _tem_segmented_from_home_pm = "tem_segmented_fr_pm"

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
        *,
        path_years: list[int],
        export_home: Path,
        report_home: Path,
        model_zoning: cb.ZoningSystem,
        agg_zoning: cb.ZoningSystem,
        trip_origin: Literal["hb", "nhb"],
    ):
        """
        Initialize the TEMModelPaths and validate input directories.

        Parameters
        ----------
        path_years : list[int]
            Years for which the model will run.
        export_home : Path
            Directory for export outputs.
        report_home : Path
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
        self.export_home = Path(export_home)
        self.report_home = Path(report_home)
        self.trip_origin = trip_origin
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
        if self.trip_origin is None:
            raise ValueError(
                "When inheriting TEMModelPaths the class variable "
                "_trip_origin needs to be set. This is usually set to "
                "'hb', or 'nhb' to reflect the type of model being run."
            )

    def create_export_paths(self) -> None:
        """Create and assign export paths for all model outputs."""
        # Init
        base_fname = self._base_output_fname
        fname_parts = [self.trip_origin, self.model_zoning.name]

        pure_demand_paths: dict[int, Path] = dict()
        pure_demand_adj_paths: dict[int, Path] = dict()
        mts_demand_paths: dict[int, Path] = dict()
        mts_demand_adj_paths: dict[int, Path] = dict()
        tem_segmented_paths: dict[int, Path] = dict()
        tem_segmented_return_home_paths: dict[int, Path] = dict()
        tem_segmented_from_home_paths: dict[int, Path] = dict()
        tem_segmented_from_home_pm_paths: dict[int, Path] = dict()


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

            # TEM Segmented path from home post-me adjustment
            fname = base_fname % (*fname_parts, self._tem_segmented_from_home_pm, year)
            tem_segmented_from_home_pm_paths[year] = self.export_home / fname



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
            tem_segmented_from_home_pm=tem_segmented_from_home_pm_paths,  
        )

    def create_report_paths(self) -> None:
        """Create and assign report paths for all model outputs."""
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
        fname_parts = [self.trip_origin, report_name]

        segment_total_paths: dict[int, Path] = dict()
        ca_sector_paths: dict[int, Path] = dict()
        ie_sector_paths: dict[int, Path] = dict()
        lad_paths: dict[int, Path] = dict()

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
        super().__init__(trip_origin=_trip_origin, *args, **kwargs)

        # Generate the paths
        self.create_export_paths()
        self.create_report_paths()


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
        self.create_export_paths()
        self.create_report_paths()


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
    export_home : Path
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
        *,
        path_years: list[int],
        scenario: Scenarios,
        iteration_name: str,
        export_home: Path,
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
        export_home : Path
            Root export directory.
        model_zoning : str
            Model zoning system name.
        agg_zoning : str
            Aggregation zoning system name.
        """
        # Init
        export_home = Path(export_home)
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
            trip_origin="hb",
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
            trip_origin="nhb",
            model_zoning=model_zoning,
            agg_zoning=agg_zoning,
        )


@dataclasses.dataclass
class RunOptions:
    """
    Options for running trip end model.

    Parameters
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
    """

    run_hb_prod: bool
    run_hb_attr: bool
    run_nhb_prod: bool
    run_nhb_attr: bool
    return_home: bool = False


@dataclasses.dataclass(kw_only=True)
class SharedParams:
    """
    Parameters shared between different models.

    Parameters
    ----------
    tr_adj: Path | None = None
        Path to hb production trip rate adjustment factors, if applicable.
    mts: Path
        Path to hb prodction mode time splits.
    mts_adjustment: Path | None = None
        Path to hb produciton mode time split adjustment factors, if applicable.
    phi_factors: Path | None = None
        Path to a directory containing hb production phi (return home) factors. These must be provided
        if 'return_home' is set to True.
    mts_return: Path | None = None
        Path to hb return home mode time splits. These should be provided as trips, rather than
        factors, as they are converted to factors based on the segmentation of the phi factors.
    mts_return_adj: Path | None = None
        Path to hb return home mode time split adjustment factors.
    postme_adj: Path | None
        Path to postme adjustment factors. These are applied at the end of either the production or
        attraction model, to from home trip ends before return home (if being applied).
    """

    mts: FilePath
    tr_adj: FilePath | None = None
    mts_adj: FilePath | None = None
    phi_factors: DirectoryPath | None = None
    mts_return: FilePath | None = None
    mts_return_adj: FilePath | None = None
    postme_adj: FilePath | None = None


class SharedParamsProto(Protocol):
    """Protocol of SharedParams only for typing."""

    mts: Path
    tr_adj: Path | None = None
    mts_adj: Path | None = None
    phi_factors: Path | None = None
    mts_return: Path | None = None
    mts_return_adj: Path | None = None
    postme_adj: Path | None = None


class HBProdProto(Protocol):
    """Protocol of HBProdParams only for typing."""

    mts: Path
    tr_adj: Path | None = None
    mts_adj: Path | None = None
    phi_factors: Path | None = None
    mts_return: Path | None = None
    mts_return_adj: Path | None = None
    postme_adj: Path | None = None
    triprates: Path


class AttrProto(Protocol):
    """Protocol of AttrParams only for typing."""

    mts: Path
    tr_adj: Path | None = None
    mts_adj: Path | None = None
    phi_factors: Path | None = None
    mts_return: Path | None = None
    mts_return_adj: Path | None = None
    postme_adj: Path | None = None
    triprates: dict[int, Path]
    mts_uni: Path
    balance: cb.BalancingZones | bool = True


@dataclasses.dataclass
class HBProdParams(SharedParams):
    """
    Paramaters for home based production model.

    Parameters
    ----------
    triprates: FilePath
        Path to home based prodction trip rates.
    """

    triprates: FilePath


@dataclasses.dataclass(config={"arbitrary_types_allowed": True})
class AttrParams(SharedParams):
    """
    Paramaters for attraction model.

    Parameters
    ----------
    triprates: dict[int, Path]
        Dict of purposes to paths to nhb attraction trip rates.
    mts_uni: Path
        Path to nhb attraction uni mode time splits.
    balance: cb.BalancingZones | bool = True
        Whether to balance attractions to productions.
    """

    triprates: dict[int, FilePath]
    mts_uni: FilePath
    balance: cb.BalancingZones | bool = True


@dataclasses.dataclass
class NHBProdParams:
    """
    Paramaters for non-home base production model.

    Parameters
    ----------
    triprates: Path
        Path to nhb production trip rates.
    mts: Path
        Path to nhb production mode time splits
    """

    triprates: FilePath
    mts: FilePath


class MainConfig(config_base.BaseConfig):
    """
    Main configuration class for the TEM model.

    Stores all global and model-specific configuration options, validates consistency,
    and supports YAML import/export.

    Attributes
    ----------
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
    export_home : Path
        Root export directory.
    return_segmentation : cb.Segmentation
        Segmentation trip-ends are returned at.
    trans_file : Path
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
    hb_prod_params: HBProdParams | None = None
        Params for home based production model. See class.
    hb_attr_params: HBAttrParams | None = None
        Params for home based attraction model. See class.
    nhb_prod_params: NHBProdParams | None = None
        Params for non-home based production model. See class.
    nhb_attr_params: NHBAttrParams | None = None
        Params for non-home based production model. See class.
    """

    ### options ###
    run_options: RunOptions
    ### global ###
    model_years: list[int]
    scenario: Scenarios
    output_zoning: Annotated[cb.ZoningSystem, BeforeValidator(_create_zoningsystem)]
    agg_zoning: Annotated[cb.ZoningSystem, BeforeValidator(_create_zoningsystem)]
    iteration_name: str
    export_home: DirectoryPath
    return_segmentation: Annotated[cb.Segmentation, BeforeValidator(_create_segmentation)]
    trans_file: FilePath
    export_pure: bool = True
    export_mts: bool = True
    export_tem: bool = True
    export_reports: bool = True
    mts_geo_constraint: (
        Annotated[cb.ZoningSystem, BeforeValidator(_create_zoningsystem)] | None
    ) = None
    pop: dict[int, Landuse]
    emp: dict[int, Landuse]
    hh: dict[int, Landuse]
    hb_prod_params: HBProdParams | None = None
    hb_attr_params: AttrParams | None = None
    nhb_prod_params: NHBProdParams | None = None
    nhb_attr_params: AttrParams | None = None

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
    def _phi_factors_if_return(self):
        """
        Validate that phi factors and return-home files are provided if return_home is True.

        Raises
        ------
        ValueError
            If required files are missing for return-home trip generation.
        """
        if self.run_options.return_home:
            required = [
                "mts_return",
                "phi_factors",
            ]
            missing_prod = [
                name for name in required if getattr(self.hb_prod_params, name, None) is None
            ]
            missing_attr = [
                name for name in required if getattr(self.hb_attr_params, name, None) is None
            ]
            missing = missing_prod + missing_attr
            if missing:
                raise ValueError(
                    f"Missing required return-home files: {', '.join(missing)}. "
                    "These must be provided for return home trips to be generated."
                )
        return self

    @model_validator(mode="after")
    def _consistent_years(self):
        """
        Validate that population, employment, and household years match model_years.

        Raises
        ------
        ValueError
            If years are inconsistent.
        """
        for attr, label in (("pop", "Population"), ("emp", "Employment"), ("hh", "Household")):
            if set(getattr(self, attr).keys()) != set(self.model_years):
                raise ValueError(f"{label} years must match model_years.")
        return self

    @model_validator(mode="after")
    def _inputs_supplied(self):
        options = self.run_options
        checks = [
            ("run_hb_prod", "hb_prod_params", "hb_prod"),
            ("run_hb_attr", "hb_attr_params", "hb_attr"),
            ("run_nhb_prod", "nhb_prod_params", "nhb_prod"),
            ("run_nhb_attr", "nhb_attr_params", "nhb_attr"),
        ]
        for run_attr, param_attr, name in checks:
            if getattr(options, run_attr):
                if getattr(self, param_attr) is None:
                    raise ValueError(f"To run {name}, {param_attr} must be provided.")
        return self


# # # FUNCTIONS # # #
