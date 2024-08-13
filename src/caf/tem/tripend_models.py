# -*- coding: utf-8 -*-
"""
Module containing trip_end models.
"""
# Built-Ins
import os

# Local Imports
# pylint: disable=import-error,wrong-import-position
# Local imports here
from inputs import (
    Scenarios,
    TEMExportPaths,
    HBProdInput,
    NHBProdInput,
    AttrInput,
    TEMSegmentations,
)
from production_models import HBProductionModel, NHBProductionModel
from attraction_models import AttractionModel


# pylint: enable=import-error,wrong-import-position
class TEM(TEMExportPaths):
    def __init__(
        self,
        years: list[int],
        scenario: Scenarios,
        iteration_name: str,
        export_home: os.PathLike,
        tem_segs: TEMSegmentations,
        hbprodinput: HBProdInput = None,
        nhbprodinput: NHBProdInput = None,
        hbattrinput: AttrInput = None,
        nhbattrinput: AttrInput = None,
        process_count: int = 1,
    ):
        # Assign
        self.years = years
        self.process_count = process_count
        self.hb_prod_input = hbprodinput
        self.nhb_prod_input = nhbprodinput
        self.hb_attr_input = hbattrinput
        self.nhb_attr_input = nhbattrinput
        self.tem_segs = tem_segs
        pass

        super().__init__(
            export_home=export_home,
            path_years=self.years,
            scenario=scenario,
            iteration_name=iteration_name,
        )

    def _generate_hb_production(self):
        if self.hb_prod_input is None:
            raise ValueError("hbprodinput must be provided to generate hb production.")
        hb_prod = HBProductionModel(
            population_paths=self.hb_prod_input.population_paths,
            trip_rates_path=self.hb_prod_input.trip_rates_path,
            mode_time_splits_path=self.hb_prod_input.mode_time_splits_path,
            export_home=self.export_home,
            tem_segs=self.tem_segs,
            process_count=self.process_count,
        )
        hb_prod.run(True, True, True)

    def _generate_hb_attraction(self):
        if self.hb_attr_input is None:
            raise ValueError("hb_attr_input not provided.")

        hb_attr = AttractionModel(
            trip_rates_paths=self.hb_attr_input.triprates,
            landuse_paths=self.hb_attr_input.landuse,
            tem_segs=self.tem_segs,
            production_balance_paths=self.hb_attr_input.balance_paths,
            export_home=self.export_home,
            balance_zoning=self.hb_attr_input.balance_zoning,
            process_count=self.process_count,
        )
        hb_attr.run(True, True, True, True)

    def _generate_nhb_production(self):
        if self.nhb_prod_input is None:
            raise ValueError("nhb_prod_input not provided.")

        nhb_prod = NHBProductionModel(
            tem_segs=self.tem_segs,
            hb_attraction_paths=self.nhb_prod_input.hb_attraction_paths,
            trip_rates_path=self.nhb_prod_input.trip_rates_path,
            time_splits_path=self.nhb_prod_input.time_splits_path,
            process_count=self.process_count,
        )

        nhb_prod.run(True, True, True, True)

    def _generate_nhb_attraction(self):
        if self.nhb_attr_input is None:
            raise ValueError("nhb_attr_input not provided.")

        nhb_attr = AttractionModel(
            trip_rates_paths=self.nhb_attr_input.triprates,
            landuse_paths=self.nhb_attr_input.landuse,
            tem_segs=self.tem_segs,
            production_balance_paths=self.nhb_attr_input.balance_paths,
            export_home=self.export_home,
            balance_zoning=self.nhb_attr_input.balance_zoning,
            process_count=self.process_count,
        )
        nhb_attr.run()

    def run(
        self,
        generate_all: bool = False,
        generate_hb: bool = False,
        generate_hb_production: bool = False,
        generate_hb_attraction: bool = False,
        generate_nhb: bool = False,
        generate_nhb_production: bool = False,
        generate_nhb_attraction: bool = False,
    ) -> None:

        # Determine which models to run
        if generate_all:
            generate_hb = True
            generate_nhb = True

        if generate_hb:
            generate_hb_production = True
            generate_hb_attraction = True

        if generate_nhb:
            generate_nhb_production = True
            generate_nhb_attraction = True

        if generate_hb_production:
            self._generate_hb_production()

        if generate_hb_attraction:
            self._generate_hb_attraction()

        if generate_nhb_production:
            self._generate_nhb_production()

        if generate_nhb_attraction:
            self._generate_nhb_attraction()


# # # FUNCTIONS # # #


