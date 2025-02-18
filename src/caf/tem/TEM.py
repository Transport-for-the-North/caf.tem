import os
import caf.base as cb

from .inputs import TEMExportPaths, Scenarios
from .attraction_models import AttractionModel_TP
from .production_models import HBProductionModel_TP, NHBProductionModel_TP

hb_prod_seg = cb.Segmentation(
    cb.SegmentationInput(
        enum_segments=["p", "aws", "soc", "ns_sec", "hh_type", "gender_3", "adult_nssec"],
        naming_order=["p", "aws", "soc", "ns_sec", "hh_type", "gender_3", "adult_nssec"],
    )
)


class TEMModel:

    def __init__(
        self,
        model_years: list[int],
        scenario: Scenarios,
        output_zoning: str,
        iteration_name: str,
        export_home: os.PathLike,
    ):
        self.years = model_years
        self.scenario = scenario
        self.output_zoning = output_zoning
        self.iteration_name = iteration_name
        self.export_paths = TEMExportPaths(model_years, scenario, iteration_name, export_home)


    def HBProductionModel(
        self,
        population_paths: dict[int, os.PathLike],
        trip_rates_path: os.PathLike,
        mode_time_splits_path: os.PathLike,
        # return_segmentation: cb.Segmentations --> is this supposed to be a user input?
    ):
        self.hb_production_model = HBProductionModel_TP(
            self.export_paths.hb_production.export_paths.pure_demand,
            population_paths,
            trip_rates_path,
            mode_time_splits_path,
            export_home=self.export_paths.hb_production.export_home,
            return_segmentation=hb_prod_seg,  # tbc --> should it be user input or given as defined?
            model_zoning=cb.ZoningSystem.get_zoning(
                self.export_paths.hb_production._zoning_system
            ),
            #process_count=1
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
        balance_production: bool,
        emp_landuse_paths: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_dirs: dict[int, os.PathLike],  # path with respect to year
        hh_landuse_prefix: str,
        hb_mts_path: os.PathLike
    ):
        
        self.hb_attraction_model = AttractionModel_TP(  # to rename AttractionModel
            self.export_paths.hb_production,
            self.hb_attraction_model,
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
    
    def run(self):
        self.hb_production_model.run()
        self.nhb_production_model.run()
        self.hb_attraction_model.run()
        self.nhb_attraction_model.run()