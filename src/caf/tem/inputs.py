# -*- coding: utf-8 -*-
"""
Created on: 29/05/2024
Updated on:

Original author: Ben Taylor
Last update made by:
Other updates made by:

File purpose:

"""
# Built-Ins
import enum
import os
import pathlib
import collections
# Third Party

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # CLASSES # # #
@enum.unique
class Scenarios(enum.Enum):

    CORE = "Core"
    HIGH = "High"
    LOW = "Low"
    REGIONAL = "Regional"
    TECHNOLOGY = "Technology"

class NoTEMModelPaths:
    """Base Path Class for all NoTEM models.

    This class forms the base path class that all NoTEM model path classes
    are built off of. It defines a number of constants to ensure all
    NoTEM models follow the same output structure and naming conventions

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
    # Export fname params
    _trip_origin = None
    _zoning_system = 'msoa'

    # Segmentation names
    _pure_demand = 'pure_demand'
    _fully_segmented = 'fully_segmented'
    _notem_segmented = 'notem_segmented'

    # Report names
    _segment_totals_report_name = "segment_totals"
    _ca_sector_report_name = "ca_sector_totals"
    _ie_sector_report_name = "ie_sector_totals"
    _lad_report_name = "lad_totals"

    # Output Path Classes
    ExportPaths = collections.namedtuple(
        typename='ExportPaths',
        field_names='home, pure_demand, fully_segmented, notem_segmented',
    )

    ReportPaths = collections.namedtuple(
        typename='ReportPaths',
        field_names='segment_total, ca_sector, ie_sector, lad_report',
    )

    # Define output fnames
    _base_output_fname = '%s_%s_%s_%d_dvec.h5'
    _base_report_fname = '%s_%s_%d_%s.csv'

    def __init__(self,
                 path_years: list[int],
                 export_home: os.PathLike,
                 report_home: os.PathLike,
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

        # Make sure paths exist
        if not self.export_home.is_dir():
            raise FileNotFoundError(f"{export_home} is not a valid dir.")
        if not self.report_home.is_dir():
            raise FileNotFoundError(f"{report_home} is not a valid dir.")


        # Make sure variables that need to be overwritten, are
        if self._trip_origin is None:
            raise ValueError(
                "When inheriting NoTEMModelPaths the class variable "
                "_trip_origin needs to be set. This is usually set to "
                "'hb', or 'nhb' to reflect the type of model being run."
            )

    def _create_export_paths(self) -> None:
        """
        Creates self.export_paths
        """
        # Init
        base_fname = self._base_output_fname
        fname_parts = [self._trip_origin, self._zoning_system]

        pure_demand_paths = dict()
        fully_segmented_paths = dict()
        notem_segmented_paths = dict()

        for year in self.path_years:
            # Pure demand path
            fname = base_fname % (*fname_parts, self._pure_demand, year)
            pure_demand_paths[year] = self.export_home / fname

            # Fully Segmented path
            fname = base_fname % (*fname_parts, self._fully_segmented, year)
            fully_segmented_paths[year] = self.export_home / fname

            # NoTEM Segmented path
            fname = base_fname % (*fname_parts, self._notem_segmented, year)
            notem_segmented_paths[year] = self.export_home / fname

        # Create the export_paths class
        self.export_paths = self.ExportPaths(
            home=self.export_home,
            pure_demand=pure_demand_paths,
            fully_segmented=fully_segmented_paths,
            notem_segmented=notem_segmented_paths,
        )

    def _create_report_paths(self) -> None:
        """
        Creates self.report_paths
        """
        self.report_paths = self.ExportPaths(
            home=self.report_home,
            pure_demand=self._generate_report_paths(self._pure_demand),
            fully_segmented=None,
            notem_segmented=self._generate_report_paths(self._notem_segmented),
        )

    def _generate_report_paths(self,
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

        segment_total_paths = dict()
        ca_sector_paths = dict()
        ie_sector_paths = dict()
        lad_paths = dict()

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

class HBProductionModelPaths(NoTEMModelPaths):
    """Path Class for the NoTEM HB Production Model.

    This class defines and builds the export and reporting paths for
    the NoTEMModelPaths. If the outputs of HBProductionModel are needed,
    create an instance of this class to generate all paths.

    Attributes
    ----------
    export_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A dictionary of export paths for pure_demand DVectors
        - fully_segmented: A dictionary of export paths for fully_segmented DVectors
        - notem_segmented: A dictionary of export paths for notem_segmented DVectors

    report_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A NoTEMModelPaths.ReportPaths object
        - fully_segmented: A NoTEMModelPaths.ReportPaths object
        - notem_segmented: A NoTEMModelPaths.ReportPaths object

    See NoTEMModelPaths for documentation on:
    path_years, export_home, report_home
    """
    # Export fname params
    _trip_origin = 'hb'

    def __init__(self, *args, **kwargs):
        """Generates the export and report paths

        See super for more detail
        """
        # Set up superclass
        super().__init__(*args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()

class HBAttractionModelPaths(NoTEMModelPaths):
    """Path Class for the NoTEM HB Attraction Model.

    This class defines and builds the export and reporting paths for
    the NoTEMModelPaths. If the outputs of HBAttractionModel are needed,
    create an instance of this class to generate all paths.

    Attributes
    ----------
    export_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A dictionary of export paths for pure_demand DVectors
        - fully_segmented: A dictionary of export paths for fully_segmented DVectors
        - notem_segmented: A dictionary of export paths for notem_segmented DVectors

    report_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A NoTEMModelPaths.ReportPaths object
        - fully_segmented: A NoTEMModelPaths.ReportPaths object
        - notem_segmented: A NoTEMModelPaths.ReportPaths object

    See NoTEMModelPaths for documentation on:
    path_years, export_home, report_home
    """
    # Export fname params
    _trip_origin = 'hb'

    def __init__(self, *args, **kwargs):
        """Generates the export and report paths

        See super for more detail
        """
        # Set up superclass
        super().__init__(*args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()


class NHBProductionModelPaths(NoTEMModelPaths):
    """Path Class for the NoTEM NHB Production Model.

    This class defines and builds the export and reporting paths for
    the NoTEMModelPaths. If the outputs of NHBProductionModel are needed,
    create an instance of this class to generate all paths.

    Attributes
    ----------
    export_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A dictionary of export paths for pure_demand DVectors
        - fully_segmented: A dictionary of export paths for fully_segmented DVectors
        - notem_segmented: A dictionary of export paths for notem_segmented DVectors

    report_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A NoTEMModelPaths.ReportPaths object
        - fully_segmented: A NoTEMModelPaths.ReportPaths object
        - notem_segmented: A NoTEMModelPaths.ReportPaths object

    See NoTEMModelPaths for documentation on:
    path_years, export_home, report_home
    """
    # Export fname params
    _trip_origin = 'nhb'

    def __init__(self, *args, **kwargs):
        """Generates the export and report paths

        See super for more detail
        """
        # Set up superclass
        super().__init__(*args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()


class NHBAttractionModelPaths(NoTEMModelPaths):
    """Path Class for the NoTEM NHB Attraction Model.

    This class defines and builds the export and reporting paths for
    the NoTEMModelPaths. If the outputs of NHBAttractionModel are needed,
    create an instance of this class to generate all paths.

    Attributes
    ----------
    export_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A dictionary of export paths for pure_demand DVectors
        - fully_segmented: A dictionary of export paths for fully_segmented DVectors
        - notem_segmented: A dictionary of export paths for notem_segmented DVectors

    report_paths: os.PathLike
        A namedtuple object (NoTEMModelPaths.ExportPaths) with the following
        attributes (dictionary keys are path_years):
        - home: The home directory of all exports
        - pure_demand: A NoTEMModelPaths.ReportPaths object
        - fully_segmented: A NoTEMModelPaths.ReportPaths object
        - notem_segmented: A NoTEMModelPaths.ReportPaths object

    See NoTEMModelPaths for documentation on:
    path_years, export_home, report_home
    """
    # Export fname params
    _trip_origin = 'nhb'

    def __init__(self, *args, **kwargs):
        """Generates the export and report paths

        See super for more detail
        """
        # Set up superclass
        super().__init__(*args, **kwargs)

        # Generate the paths
        self._create_export_paths()
        self._create_report_paths()


class NoTEMExportPaths:
    """Path Class for the NoTEM Model.

    This class defines and builds the export and reporting paths for
    all NoTEM sub-models. It creates and stores an instance of:
    HBProductionModelPaths, NHBProductionModelPaths,
    HBAttractionModelPaths, NHBAttractionModelPaths.
    If the outputs of NoTEM are needed, create an instance of this
    class to generate all paths.

    Attributes
    ----------
    path_years:
        A list of the years the models are running for. As passed into the
        constructor.

    scenario:
        The name of the scenario to run for. As passed in to the constructor.

    iteration_name:
        The name of this iteration of the NoTEM models. Constructor argument
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
    _hb_productions_dir = 'hb_productions'
    _nhb_productions_dir = 'nhb_productions'
    _hb_attractions_dir = 'hb_attractions'
    _nhb_attractions_dir = 'nhb_attractions'

    _reports_dir = 'reports'

    def __init__(self,
                 path_years: list[int],
                 scenario: Scenarios,
                 iteration_name: str,
                 export_home: os.PathLike,
                 ):
        """
        Builds the export paths for all the NoTEM sub-models

        Parameters
        ----------
        path_years:
            A list of the years the models are running for.

        scenario:
            The scenario to run for.

        iteration_name:
            The name of this iteration of the NoTEM models. Will have 'iter'
            prepended to create the folder name. e.g. if iteration_name was
            set to '3i' the iteration folder would be called 'iter3i'.

        export_home:
            The home directory of all the export paths. A sub-directory will
            be made for each of the NoTEM sub models.
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

        self.hb_production = HBProductionModelPaths(
            path_years=path_years,
            export_home=hb_p_export_home,
            report_home=hb_p_report_home,
        )

        # nhb productions
        nhb_p_export_home = self.export_home / self._nhb_productions_dir
        nhb_p_report_home = nhb_p_export_home / self._reports_dir

        nhb_p_report_home.mkdir(exist_ok=True, parents=True)

        self.nhb_production = NHBProductionModelPaths(
            path_years=path_years,
            export_home=nhb_p_export_home,
            report_home=nhb_p_report_home,
        )

        # hb attractions
        hb_a_export_home = self.export_home / self._hb_attractions_dir
        hb_a_report_home = hb_a_export_home / self._reports_dir

        hb_a_report_home.mkdir(exist_ok=True, parents=True)

        self.hb_attraction = HBAttractionModelPaths(
            path_years=path_years,
            export_home=hb_a_export_home,
            report_home=hb_a_report_home,
        )

        # nhb attractions
        nhb_a_export_home = self.export_home / self._nhb_attractions_dir
        nhb_a_report_home = nhb_a_export_home / self._reports_dir
    
        nhb_a_report_home.mkdir(exist_ok=True, parents=True)

        self.nhb_attraction = NHBAttractionModelPaths(
            path_years=path_years,
            export_home=nhb_a_export_home,
            report_home=nhb_a_report_home,
        )

# # # FUNCTIONS # # #
