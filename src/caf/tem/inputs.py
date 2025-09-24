# -*- coding: utf-8 -*-
"""
Module containing input classes for trip-end models, mainly around imports and
exports.
"""
from __future__ import annotations

# Built-Ins TODO tidy this file
import enum
import os
import pathlib
import collections
import warnings
from dataclasses import dataclass
from typing import Literal, Annotated
import pandas as pd

# Third Party
import caf.base as cb
import caf.toolkit as ctk
from caf.toolkit import config_base
from pydantic import BeforeValidator, model_validator


# pylint: disable =too-many-positional-arguments,too-few-public-methods
# # # CLASSES # # #
def create_segmentation(seg_list: list[str] | cb.Segmentation):
    if isinstance(seg_list, cb.Segmentation):
        return seg_list
    inp = cb.SegmentationInput(enum_segments=seg_list, naming_order=seg_list)
    return cb.Segmentation(inp)

def create_zoningsystem(zoning: str | cb.ZoningSystem | list[str, cb.ZoningSystem]):
    if isinstance(zoning, cb.ZoningSystem):
        return zoning
    if isinstance(zoning, list):
        validated_zoning = []
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
    A data container for handling different types of land use inputs (e.g., population, employment, households)
    along with associated metadata for processing and transformation.

    Attributes:
        type (Literal["pop", "emp", "hh"]):
            Specifies the type of land use. Must be one of:
            - "pop": Population
            - "emp": Employment
            - "hh": Households

        land_use (os.PathLike | cb.DVector):
            The actual land use data. Can be either:
            - A path to a file containing land use data
            - A `cb.DVector` object (custom data vector used internally)

        trans_tag (str, optional):
            An optional tag used for transformation processes. Can help distinguish different data processing steps.

        prefix (str, optional):
            An optional prefix used when naming output fields or files. Helps to avoid naming collisions in outputs.

        segmentation (cb.Segmentation, optional):
            An optional segmentation object that splits the land use data based on predefined segments,
            such as income levels, activity types, etc.

        geographies (str, optional):
            The name of the geographical unit associated with the land use data (e.g., zone ID, MSOA, LSOA, etc.).

        out_zoning (cb.ZoningSystem | str | list[cb.ZoningSystem | str] | None, optional):
            Defines the zoning system(s) to which the land use data should be mapped or output.
            This can be:
            - A single `cb.ZoningSystem` object
            - A string representing a known zoning system
            - A list of such zoning system objects or strings
            - Or left as `None` if no output zoning conversion is required
    """

    type: Literal["pop", "emp", "hh"]
    land_use: os.PathLike | cb.DVector
    trans_tag: str = None
    prefix: str = None
    segmentation: Annotated[cb.Segmentation, BeforeValidator(create_segmentation)] = None
    geographies: str | list[str] | None = None
    out_zoning: cb.ZoningSystem | str | Annotated[list[cb.ZoningSystem | str], BeforeValidator(func=create_zoningsystem)] | None = None

        

    def read_landuse(
        self, translation: pd.DataFrame | None = None, init_zoning: cb.ZoningSystem | None = None, model_zoning: cb.ZoningSystem | None = None, 
    ):
        """
        Reads and processes land use data from the specified source, applying optional translation and
        aligning it with the model's zoning system if provided.

        Parameters:
            translation (pd.DataFrame | None, optional):
                A translation table (typically a pandas DataFrame)

            model_zoning (cb.ZoningSystem, optional)

        Returns:
            None
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
            for geo in self.geographies:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    dvec = cb.DVector.load(source_path / self.prefix.format(geo))
                    if segmentation is None:
                        segmentation = dvec.segmentation
                    dvecs.append(dvec.aggregate(segmentation))
            lu_data = pd.concat([dvec.data for dvec in dvecs], axis=1)
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


@enum.unique
class Scenarios(enum.Enum):
    """Define different Scenario."""

    CORE = "Core"
    HIGH = "High"
    LOW = "Low"
    REGIONAL = "Regional"
    TECHNOLOGY = "Technology"


class TEMModelPaths:
    """Base Path Class for all TEM models.

    This class forms the base path class that all TEM model path classes
    are built off of. It defines a number of constants to ensure all
    TEM models follow the same output structure and naming conventions.

    Attributes
    ----------
    path_years: list[int]
        A list of years that paths will be generated for.

    export_home: os.PathLike
        The home directory of all exports. Is used as a basis for
        all export path building.

    report_home: os.PathLike
        The home directory of all reports. Is used as a basis for
        all report path building.
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

    # Output Path Classes
    ExportPaths = collections.namedtuple(
        typename="ExportPaths",
        field_names="home, pure_demand, pure_demand_adj, mts_demand, mts_demand_adj, tem_segmented,tem_segmented_return_home,tem_segmented_from_home",
    )

    ReportPaths = collections.namedtuple(
        typename="ReportPaths",
        field_names="segment_total, ca_sector, ie_sector, lad_report",
    )

    # Define output fnames
    _base_output_fname = "%s_%s_%s_%d.dvec"
    _base_report_fname = "%s_%s_%d_%s.csv"

    def __init__(
        self,
        path_years: list[int],
        export_home: os.PathLike,
        report_home: os.PathLike,
        model_zoning: str,
        agg_zoning: str,
        _trip_origin,
    ):
        """Validates input attributes and builds class

        Parameters
        ----------
        path_years:
            A list of the years the models are running for.

        export_home:
            The home directory of all the export paths.

        report_home:
            The home directory of all the model reports paths.
        """
        # Assign attributes
        self.path_years = path_years
        self.export_home = pathlib.Path(export_home)
        self.report_home = pathlib.Path(report_home)
        self._trip_origin = _trip_origin
        self.model_zoning = model_zoning
        self.agg_zoning = agg_zoning
        self.export_paths = None
        self.report_paths = None

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
        Creates self.export_paths
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
        self.export_paths = self.ExportPaths(
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
        Creates self.report_paths
        """
        self.report_paths = self.ExportPaths(
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
    ) -> tuple[dict[int, str], dict[int, str], dict[int, str]]:
        """
        Creates report file paths for each of years

        Parameters
        ----------
        report_name:
            The name to use in the report filename. Filenames will be named
            as: [report_name, year, report_type], joined with '_'.

        Returns
        -------
        segment_total_paths:
            A dictionary of paths where the key is the year and the value is
            the path to the segment total reports for year.

        ca_sector_total_paths:
            A dictionary of paths where the key is the year and the value is
            the path to the ca sector segment total reports for year.

        ie_sector_total_paths:
            A dictionary of paths where the key is the year and the value is
            the path to the IE sector segment total reports for year.
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

        return self.ReportPaths(
            segment_total=segment_total_paths,
            ca_sector=ca_sector_paths,
            ie_sector=ie_sector_paths,
            lad_report=lad_paths,
        )


class ProductionModelPaths(TEMModelPaths):
    """Path Class for the TEM HB Production Model.

    This class defines and builds the export and reporting paths for
    the TEMModelPaths. If the outputs of HBProductionModel are needed,
    create an instance of this class to generate all paths.

    Attributes
    ----------
    export_paths: os.PathLike
        A namedtuple object (TEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A dictionary of export paths for pure_demand DVectors
        - tem_segmented: A dictionary of export paths for tem_segmented DVectors

    report_paths: os.PathLike
        A namedtuple object (TEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A TEMModelPaths.ReportPaths object
        - tem_segmented: A TEMModelPaths.ReportPaths object

    See TEMModelPaths for documentation on:
    path_years, export_home, report_home
    """

    def __init__(self, _trip_origin, *args, **kwargs):
        """Generates the export and report paths

        See super for more detail
        """
        # Set up superclass
        super().__init__(_trip_origin=_trip_origin, *args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()


class AttractionModelPaths(TEMModelPaths):
    """Path Class for the TEM NHB Attraction Model.

    This class defines and builds the export and reporting paths for
    the TEMModelPaths. If the outputs of NHBAttractionModel are needed,
    create an instance of this class to generate all paths.

    Attributes
    ----------
    export_paths: os.PathLike
        A namedtuple object (TEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A dictionary of export paths for pure_demand DVectors
        - tem_segmented: A dictionary of export paths for tem_segmented DVectors

    report_paths: os.PathLike
        A namedtuple object (TEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A TEMModelPaths.ReportPaths object

        - tem_segmented: A TEMModelPaths.ReportPaths object

    See TEMModelPaths for documentation on:
    path_years, export_home, report_home
    """

    def __init__(self, *args, **kwargs):
        """Generates the export and report paths

        See super for more detail
        """
        # Set up superclass
        super().__init__(*args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()


class TEMExportPaths:
    """Path Class for the TEM Model.

    This class defines and builds the export and reporting paths for
    all TEM sub-models. It creates and stores an instance of:
    HBProductionModelPaths, NHBProductionModelPaths,
    HBAttractionModelPaths, NHBAttractionModelPaths.
    If the outputs of TEM are needed, create an instance of this
    class to generate all paths.

    Attributes
    ----------
    path_years:
        A list of the years the models are running for. As passed into the
        constructor.

    scenario:
        The name of the scenario to run for. As passed in to the constructor.

    iteration_name:
        The name of this iteration of the TEM models. Constructor argument
        of the same name will have 'iter' prepended to create this name.
        e.g. if '3i' was passed in, this would become 'iter3i'.

    export_home:
        The home directory of all the export paths. Nested folder of the
        passed in export_home, iteration_name, and scenario

    hb_production:
        An instance of HBProductionModelPaths. See docs for more info on how
        to access paths.

    nhb_production:
        An instance of NHBProductionModelPaths. See docs for more info on how
        to access paths.

    hb_attraction:
        An instance of HBAttractionModelPaths. See docs for more info on how
        to access paths.

    nhb_attraction:
        An instance of NHBAttractionModelPaths. See docs for more info on how
        to access paths.
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
        model_zoning: str,
        agg_zoning: str,
    ):
        """
        Builds the export paths for all the TEM sub-models

        Parameters
        ----------
        path_years:
            A list of the years the models are running for.

        scenario:
            The scenario to run for.

        iteration_name:
            The name of this iteration of the TEM models. Will have 'iter'
            prepended to create the folder name. e.g. if iteration_name was
            set to '3i' the iteration folder would be called 'iter3i'.

        export_home:
            The home directory of all the export paths. A sub-directory will
            be made for each of the TEM sub models.
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
    mts_geo_constraint: Annotated[cb.ZoningSystem, BeforeValidator(create_zoningsystem)] | None = None
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

        arbitrary_types_allowed=True
        json_encoders={cb.ZoningSystem: lambda z: z.name,
                       cb.Segmentation: lambda z: z.naming_order if hasattr(z, "naming_order") else list(z) if isinstance(z, list) else str}

    @model_validator(mode="after")
    def phi_factors_if_return(self):
        if self.return_home:
            if self.hb_prod_phi_factors is None:
                raise ValueError("hb_prod_phi_factors must be provided for return home trips to be generated.")
            if self.hb_prod_mts_return is None:
                raise ValueError("hb_prod_mts_return must be provided for return home trips to be generated.")
            if self.hb_attr_phi_factors is None:
                raise ValueError("hb_attr_phi_factors must be provided for return home trips to be generated.")
            if self.hb_attr_mts_return is None:
                raise ValueError("hb_attr_mts_return must be provided for return home trips to be generated.")
        return self

    @model_validator(mode="after")
    def consistent_years(self):
        if set(self.pop.keys()) != set(self.model_years):
            raise ValueError("Population years must match model_years.")
        if set(self.emp.keys()) != set(self.model_years):
            raise ValueError("Employment years must match model_years.")
        if set(self.hh.keys()) != set(self.model_years):
            raise ValueError("Household years must match model_years.")
        return self

    


# pylint: enable =too-many-positional-arguments,too-few-public-methods

# # # FUNCTIONS # # #
if __name__ == "__main__":
    from pathlib import Path

    # --- Extracted from run.py ---
    model_years = [2023]
    scenario = "Core"
    output_zoning = "normits"
    agg_zoning = "tfn_at"
    iteration_name = "full_test_aj_1"
    export_home = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs")
    return_segmentation = ["p", "m", "tp", "hh_type", "soc"]
    trans_file = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\normits_lsoa21_trans.csv")
    mts_geo_constraint = cb.ZoningSystem.get_zoning("gor")

    pop = {
        2023: Landuse(
            land_use=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\landuse\pop.dvec",
            type="pop",
            segmentation=["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"],
            out_zoning=[output_zoning, agg_zoning, mts_geo_constraint],
        )
    }
    emp = {
        2023: Landuse(
            land_use=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\landuse\emp.dvec",
            type="emp",
            segmentation=["soc", "sic_1_digit", "sic_2_digit"],
            out_zoning=[output_zoning, agg_zoning, "uni", mts_geo_constraint],
            trans_tag="uni",
        )
    }
    hh = {
        2023: Landuse(
            type="pop",
            land_use=r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\landuse",
            prefix=r"Output P14.1_{}.hdf",
            geographies=("EM", "EoE", "Lon", "NE", "NW", "SE", "SW", "Wales", "WM", "YH", "Scotland"),
            out_zoning=[output_zoning, agg_zoning, "uni", mts_geo_constraint],
        )
    }

    # --- File paths for trip rates, adjustments, etc. ---
    hb_prod_triprates = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\trip_rates\hb_trip_rates_production_trip_rates.dvec")
    hb_prod_mts = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\mode_time_splits\mode_time_split_production_hb_fr_reg_rho.dvec")
    hb_prod_phi_factors = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\phi_factors")
    hb_prod_mts_return = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\mode_time_splits\mode_time_split_production_hb_to_reg_trips.est.dvec")
    hb_prod_mts_return_adj = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\mode_time_split_adjustments_p_hb_to_adj.dvec")
    hb_prod_tr_adj = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\trip_rate_adjustments_p_hb_fr_adj.dvec")
    hb_prod_mts_adjustment = Path(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\others\mode_time_split_adjustments_p_hb_fr_adj.dvec")

    hb_attr_triprates = {
        1: Path(r"..."),  # Fill in all 8 paths as in run.py
        # ...
    }
    hb_attr_mts = Path(r"...")  # Fill in as in run.py
    hb_attr_mts_adj = Path(r"...")
    hb_attr_mts_uni = Path(r"...")
    hb_attr_tr_adj = Path(r"...")
    hb_attr_phi_factors = Path(r"...")
    hb_attr_mts_return = Path(r"...")
    hb_attr_mts_return_adj = Path(r"...")

    # Similarly for nhb_prod and nhb_attr...

    # --- Create MainConfig instance ---
    config = MainConfig(
        run_hb_prod=True,
        run_hb_attr=True,
        run_nhb_prod=True,
        run_nhb_attr=True,
        return_home=True,
        model_years=model_years,
        scenario=scenario,
        output_zoning=output_zoning,
        agg_zoning=agg_zoning,
        iteration_name=iteration_name,
        export_home=export_home,
        return_segmentation=return_segmentation,
        trans_file=trans_file,
        export_pure=True,
        export_mts=True,
        export_tem=True,
        export_reports=True,
        mts_geo_constraint=mts_geo_constraint,
        pop=pop,
        emp=emp,
        hh=hh,
        hb_prod_triprates=hb_prod_triprates,
        hb_prod_tr_adj=hb_prod_tr_adj,
        hb_prod_mts=hb_prod_mts,
        hb_prod_mts_adjustment=hb_prod_mts_adjustment,
        hb_prod_phi_factors=hb_prod_phi_factors,
        hb_prod_mts_return=hb_prod_mts_return,
        hb_prod_mts_return_adj=hb_prod_mts_return_adj,
        hb_attr_triprates=hb_attr_triprates,
        hb_attr_tr_adj=hb_attr_tr_adj,
        hb_attr_mts=hb_attr_mts,
        hb_attr_mts_adj=hb_attr_mts_adj,
        hb_attr_mts_uni=hb_attr_mts_uni,
        balance_hb=True,
        hb_attr_phi_factors=hb_attr_phi_factors,
        hb_attr_mts_return=hb_attr_mts_return,
        hb_attr_mts_return_adj=hb_attr_mts_return_adj,
        nhb_prod_triprates=Path(r"..."),
        nhb_prod_mts=Path(r"..."),
        balance_nhb=True,
        nhb_attr_triprates={},
        nhb_attr_tr_adj=Path(r"..."),
        nhb_attr_mts=Path(r"..."),
        nhb_attr_mts_adj=Path(r"..."),
        nhb_attr_mts_uni=Path(r"..."),
    )
    with open('test.yml', "rt") as file:
            text = file.read()
    test = MainConfig.load_yaml('test.yml')
    config.to_yaml()

    print("deb ugging")