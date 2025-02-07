import os
import caf.base as cb

from .inputs import TEMExportPaths, Scenarios
from .attraction_models import AttractionModel_TP
from .production_models import HBProductionModel_TP

hb_prod_seg = cb.Segmentation(
    cb.SegmentationInput(enum_segments=['p', 'aws', 'soc', 'ns_sec', 'hh_type', 'gender_3', 'adult_nssec'],
                         naming_order=['p', 'aws', 'soc', 'ns_sec', 'hh_type', 'gender_3', 'adult_nssec'])
)

class TEMModel:

    def __init__(
        self,
        path_years: list[int],
        scenario: Scenarios,
        iteration_name: str,
        export_home: os.PathLike
    ):
        self.years = path_years
        self.scenario = scenario
        self.iteration_name = iteration_name
        self.export_paths = TEMExportPaths(path_years, scenario, iteration_name, export_home)
        

    def HBProductionModel(
            self,
            population_paths: dict[int, os.PathLike],
            trip_rates_path: os.PathLike,
            mode_time_splits_path: os.PathLike
            #return_segmentation: cb.Segmentations --> is this supposed to be a user input?
    ):
        return HBProductionModel_TP(
            self.export_paths.hb_production,
            population_paths,
            trip_rates_path,
            mode_time_splits_path,
            export_home=self.export_paths.hb_production.export_home,
            return_segmentation=hb_prod_seg, # tbc --> should it be user input or given as defined?
            model_zoning=cb.ZoningSystem.get_zoning(self.export_paths.hb_production._zoning_system),
            process_count=1
        )


    def NHBProductionModel():
        pass


    def HBAttractionModel(
            self,
            trip_rates_paths: dict[int, os.PathLike],
            emp_landuse_path: os.PathLike, # Question: does emp land use change with respect to year?
            hh_landuse_dir: os.PathLike, # Question: does hh land use change with respect to year?
            hh_landuse_prefix: str
    ):
        return AttractionModel_TP( # to rename AttractionModel
            self.export_paths.hb_attraction,
            trip_rates_paths,
            emp_landuse_path,
            hh_landuse_dir,
            hh_landuse_prefix
        )


    def NHBAttractionModel(
            self,
            trip_rates_paths: dict[int, os.PathLike],
            emp_landuse_path: os.PathLike, # Question: does emp land use change with respect to year?
            hh_landuse_dir: os.PathLike, # Question: does hh land use change with respect to year?
            hh_landuse_prefix: str
    ):
        return AttractionModel_TP( # to rename AttractionModel
            self.export_paths.nhb_attraction,
            trip_rates_paths,
            emp_landuse_path,
            hh_landuse_dir,
            hh_landuse_prefix
        )