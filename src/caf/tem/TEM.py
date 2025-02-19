import os
import caf.base as cb

from .inputs import TEMExportPaths, Scenarios
from .attraction_models import AttractionModel_TP
from .production_models import HBProductionModel_TP, NHBProductionModel_TP


class TEMModel:

    def __init__(
        self,
        model_years: list[int],
        scenario: Scenarios,
        output_zoning: str,
        iteration_name: str,
        export_home: os.PathLike,
        return_segmentation: list[str]
    ):
        self.years = model_years
        self.scenario = scenario
        self.output_zoning = output_zoning
        self.iteration_name = iteration_name
        self.export_paths = TEMExportPaths(model_years, scenario, iteration_name, export_home)
        self.return_segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=return_segmentation, naming_order=return_segmentation))
        self.hb_production_model: HBProductionModel_TP = None
        self.hb_attraction_model: AttractionModel_TP = None
        self.nhb_production_model: NHBProductionModel_TP = None
        self.nhb_attraction_model: AttractionModel_TP = None
        

    def HBProductionModel(
        self,
        population_paths: dict[int, os.PathLike],
        trip_rates_path: os.PathLike,
        mode_time_splits_path: os.PathLike
    ):
        self.hb_production_model = HBProductionModel_TP(
            self.export_paths.hb_production,
            population_paths,
            trip_rates_path,
            mode_time_splits_path,
            export_home=self.export_paths.hb_production.export_home,
            return_segmentation=self.return_segmentation,
            model_zoning=cb.ZoningSystem.get_zoning(
                self.export_paths.hb_production._zoning_system
            )
        )

        return self.hb_production_model

    def NHBProductionModel(
            self,

        ):
        self.nhb_production_model = NHBProductionModel_TP()

        return self.nhb_production_model

    def HBAttractionModel(
        self,
        trip_rates_paths: dict[int, os.PathLike],  # path with respect to purpose
        emp_landuse_paths: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_dirs: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_prefix: str,
        hb_mts_path: os.PathLike,
        balance_production: bool=True,
    ):
        """
        The Home-Based Attraction Model of caf.tem

        Run the attraction model by calling the class' run() method.

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

        hb_mts_path: os.PathLike
            The path to attraction mode time splits file. As passed into the constructor.

        balance_production: bool=True
            Whether to balance the attractions to the productions.
        
        See HBAttractionModelPaths for documentation on:
            "path_years, export_home, report_home, export_paths, report_paths"
        """

        self.hb_attraction_model = AttractionModel_TP(  # to rename AttractionModel
            self.export_paths.hb_production,
            self.export_paths.hb_attraction,
            trip_rates_paths,
            balance_production,
            self.export_paths.hb_production.export_paths.tem_segmented,
            emp_landuse_paths,
            hh_landuse_dirs,
            hh_landuse_prefix,
            hb_mts_path
        )

        return self.hb_attraction_model

    def NHBAttractionModel(
        self,
        trip_rates_paths: dict[int, os.PathLike],  # path with respect to purpose
        emp_landuse_paths: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_dirs: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_prefix: str,
        nhb_mts_split_path: os.PathLike
    ):
        self.nhb_attraction_model = AttractionModel_TP(  # to rename AttractionModel
            self.export_paths.nhb_attraction,
            trip_rates_paths,
            emp_landuse_paths,
            hh_landuse_dirs,
            hh_landuse_prefix,
            nhb_mts_split_path
        )

        return self.nhb_attraction_model
    
    def run(self): # assumes that all models are defined and setup.
        self.hb_production_model.run()
        self.nhb_production_model.run()
        self.hb_attraction_model.run()
        self.nhb_attraction_model.run()