"""ASSUMPTIONS:
"""

"""IMPORTS REQUIRED:
"""

import os
import caf.base as cb
import pandas as pd

from .inputs import TEMExportPaths, Scenarios, Landuse
from .attraction_models import AttractionModel
from .production_models import HBProductionModel, NHBProductionModel_TP

"""VARIABLE CODING INFORMATION:
"""

"""RELEVANT FILE PATHS:
"""

"""FUNCTIONS:
"""

"""EXECUTION OF CODE:
"""


class TEM:
    """
    The Trip End Model (TEM) of caf.tem

    Attributes
    ----------
    model_years: dict[int]
        The years to run the TEM for.

    scenario: str
        The TAG Scenario. Core, High, Low, Regional, or Technology.

    output_zoning: str
        The zoning system for outputs.

    iteration_name: str
        A name for this TEM Output.

    export_home: os.PathLike
        The parent directory for exports of this TEM.

    return_segmentation: list[str]
        Segmentations to return in the output.


    Child Models
    ----------
    From this parent model class, define:
    - a Home Based (HB) Production Model
    - a HB Attraction Model
    - a non-Home Based (NHB) Production Model
    - a NHB Attraction Model


    ----------
    Run the TEM by calling the class' run() method once all child models (HB/NHB, Production/Attraction) have been set up.
    """

    def __init__(
        self,
        model_years: list[
            int
        ],  # TODO should this be an input, if so - do we want checks that all model_years are in path keys for other models?
        scenario: str,  # TODO - should this be an input, assume that scenario would be core? Scenario could go in Iteration Name?
        output_zoning: str,
        agg_zoning: str,
        iteration_name: str,
        export_home: os.PathLike,  # TODO should this be /Export as default within the directory of the terminal when run is called?
        return_segmentation: list[str],
        trans_file: os.PathLike,
    ):
        self.years = model_years
        self.scenario = Scenarios(scenario)
        self.output_zoning = cb.ZoningSystem.get_zoning(output_zoning)
        self.agg_zoning = cb.ZoningSystem.get_zoning(agg_zoning)
        self.iteration_name = iteration_name
        self.export_paths = TEMExportPaths(
            model_years, self.scenario, iteration_name, export_home, output_zoning, agg_zoning
        )
        self.return_segmentation = cb.Segmentation(
            cb.SegmentationInput(
                enum_segments=return_segmentation, naming_order=return_segmentation
            )
        )
        self.zone_trans = pd.read_csv(trans_file)

        self.hb_production_model: HBProductionModel = None
        self.hb_attraction_model: AttractionModel = None
        self.nhb_production_model: NHBProductionModel_TP = None
        self.nhb_attraction_model: AttractionModel = None

    def HBProductionModel(  # TODO default with respect to the NTS-Processing model output folder structure? - similarly for other models?
        self,
        population_paths: dict[int, Landuse],
        trip_rates_path: os.PathLike,
        mode_time_splits_path: os.PathLike,
        adjustment_path: os.PathLike = None,
        mts_adj_path: os.PathLike = None,
        pop_zoning=None,
    ) -> HBProductionModel:
        """
        The Home-Based (HB) Production Model of caf.tem

        Run the HB Production Model by calling the object's run() method.

        Attributes
        ----------
        population_paths: Dict[int, os.PathLike]:
            Dictionary of {year: land_use_employment_data} pairs. As passed
            into the constructor.

        trip_rates_path: str
            The path to the production trip rates. As passed into the constructor.

        mode_time_splits_path: str
            The path to production mode-time splits. As passed into the
            constructor.

        constraint_paths: Dict[int, os.PathLike]
            Dictionary of {year: constraint_path} pairs. As passed into the
            constructor.

        process_count: int
            The number of processes to create in the Pool. As passed into the
            constructor.

        years: List[int]
            A list of years that the model will run for. Derived from the keys of
            land_use_paths

        See HBProductionModelPaths for documentation on:
            "path_years, export_home, report_home, export_paths, report_paths"
        """
        self.hb_production_model = HBProductionModel(
            self.export_paths.hb_production,
            population_paths,
            self.zone_trans,
            pop_zoning,
            trip_rates_path,
            adjustment_path,
            mode_time_splits_path,
            mts_adj_path,
            tem_segmentation=self.return_segmentation,
        )

        return self.hb_production_model

    def HBAttractionModel(
        self,
        trip_rates_paths: dict[int, os.PathLike],
        emp_landuse: dict[int, Landuse],
        hh_landuse: dict[int, Landuse],
        mode_time_splits_path: os.PathLike,
        balance_production: bool = True,
        trip_rate_adjustment_path: os.PathLike = None,
        mode_time_splits_adjustment_path: os.PathLike = None,
        mts_uni_path: os.PathLike = None,
    ) -> AttractionModel:
        """
        The Home Based (HB) Attraction Model of caf.tem

        Run the attraction model by calling the class' run() method.

        Attributes
        ----------
        trip_rates_paths: Dict[int, os.PathLike]
            Dictionary of {purpose: trip_rates_data} pairs. As passed into the constructor.

        emp_landuse: Dict[int, os.PathLike]:
            Dictionary of {year: land_use_employment_data} pairs. As passed into the constructor.

        hh_landuse: Dict[int, os.PathLike]
            Dictionary of {year: hh_landuse_directory}. As passed into the constructor.

        hh_landuse_prefix: str
            The prefix of the household landuse data files. As passed into the constructor.
            Suffixes of household landuse data files are Government Office Region (GOR) codes
            (i.e. in ["EM", "EoE", "Lon", "NE", "NW", "SE", "SW", "Wales", "WM", "YH", "Scotland"]).

        production_balance_paths: Dict[int, os.PathLike]:
            Dictionary of {year: path_to_production_to_control_to} pairs. As passed into the constructor.

        hb_mode_time_splits_path: os.PathLike
            The path to attraction mode time splits file. As passed into the constructor.

        balance_production: bool=True
            Whether to balance the attractions to the productions.

        See HBAttractionModelPaths for documentation on:
            "path_years, export_home, report_home, export_paths, report_paths"
        """

        self.hb_attraction_model = AttractionModel(
            self.export_paths.hb_production,
            self.export_paths.hb_attraction,
            trip_rates_paths,
            trip_rate_adjustment_path,
            balance_production,
            emp_landuse,
            hh_landuse,
            mode_time_splits_path,
            mode_time_splits_adjustment_path,
            self.return_segmentation,
            mts_uni_path,
            self.output_zoning,
            self.agg_zoning,
            self.zone_trans,
        )

        # User Input Test
        for p in trip_rates_paths.keys():
            vals = cb.segmentation.SegmentsSuper("p").get_segment().int_values
            if p not in vals:
                raise KeyError(
                    f"Trip rates key {p} was passed.\nTrip rates keys must be in {vals}"
                )

        return self.hb_attraction_model

    def NHBProductionModel(
        self,
        trip_rates_path: os.PathLike,
        mode_time_splits_path: os.PathLike,
        balance_production: bool = True,
    ) -> NHBProductionModel_TP:
        self.nhb_production_model = NHBProductionModel_TP(
            self.export_paths.hb_attraction,
            self.export_paths.nhb_production,
            trip_rates_path,
            balance_production,
            mode_time_splits_path,
            self.return_segmentation,
        )

        return self.nhb_production_model

    def NHBAttractionModel(
        self,
        trip_rates_paths: dict[int, os.PathLike],  # path with respect to purpose
        emp_landuse_paths: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_dirs: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_prefix: str,
        nhb_mode_time_splits_path: os.PathLike,
        balance_production: bool = True,
    ) -> AttractionModel:
        """
        The non-Home Based (NHB) Attraction Model of caf.tem

        Run the NHB Attraction Model by calling the class' run() method.

        Attributes
        ----------
        trip_rates_paths: Dict[int, os.PathLike]
            Dictionary of {purpose: trip_rates_data} pairs. As passed into the constructor.

        emp_landuse_paths: Dict[int, os.PathLike]:
            Dictionary of {year: land_use_employment_data} pairs. As passed into the constructor.

        hh_landuse_dirs: Dict[int, os.PathLike]
            Dictionary of {year: hh_landuse_directory}. As passed into the constructor.

        hh_landuse_prefix: str
            The prefix of the household landuse data files. As passed into the constructor.
            Suffixes of household landuse data files are Government Office Region (GOR) codes
            (i.e. in ["EM", "EoE", "Lon", "NE", "NW", "SE", "SW", "Wales", "WM", "YH", "Scotland"]).

        production_balance_paths: Dict[int, os.PathLike]:
            Dictionary of {year: path_to_production_to_control_to} pairs. As passed into the constructor.

        nhb_mode_time_splits_path: os.PathLike
            The path to attraction mode time splits file. As passed into the constructor.

        balance_production: bool=True
            Whether to balance the attractions to the productions.

        See HBAttractionModelPaths for documentation on:
            "path_years, export_home, report_home, export_paths, report_paths"
        """

        self.nhb_attraction_model = AttractionModel(
            self.export_paths.nhb_production,
            self.export_paths.nhb_attraction,
            trip_rates_paths,
            balance_production,
            emp_landuse_paths,
            hh_landuse_dirs,
            hh_landuse_prefix,
            nhb_mode_time_splits_path,
            self.return_segmentation,
        )

        # User Input Test
        vals = cb.segmentation.SegmentsSuper("p_nhb").get_segment().int_values
        for p in trip_rates_paths.keys():
            if p not in vals:
                raise KeyError(
                    f"Trip rates key {p} was passed.\nTrip rates keys must be in {vals}"
                )

        return self.nhb_attraction_model

    def run(self):
        if not all(
            [
                self.hb_production_model,
                self.hb_attraction_model,
                self.nhb_production_model,
                self.nhb_attraction_model,
            ]
        ):
            self.hb_production_model.run()
            self.hb_attraction_model.run()
            self.nhb_production_model.run()
            self.nhb_attraction_model.run()
        else:
            print("All child models must be defined before running the Trip End Model.")


"""SAVE OUTPUT:
"""
