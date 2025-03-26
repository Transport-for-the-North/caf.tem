# -*- coding: utf-8 -*-
from __future__ import annotations

"""ASSUMPTIONS:
"""

"""IMPORTS REQUIRED:
"""



# Builtins
import dataclasses # TODO check if needed
import os
import pathlib
import warnings
import logging

from typing import Dict, List, Optional, Literal # TODO check if needed

# Third party imports
import pandas as pd
import caf.base as cb
import caf.toolkit as ctk

from pathlib import Path
from caf.tem.inputs import ProductionModelPaths

from .inputs import ProductionModelPaths, AttractionModelPaths

import caf.tem.utils as utils


"""VARIABLE CODING INFORMATION:
"""

"""RELEVANT FILE PATHS:
"""

"""FUNCTIONS:
"""

"""EXECUTION OF CODE:
"""

class HBProductionModel_TP:
    """
    The Home-Based (HB) Production Model class of caf.tem

    Paramaters
    ----------
    model : caf.tem.ProductionModelPaths
        The HB Production Model paths for exporting data.
        These are automatically created in the Trip End Model (TEM), of which this HB Production Model is a child.

    population_paths : Dict[int, os.PathLike]
        Dictionary of {year: population_data_path} pairs.
        Population data should be in DVector format with either .dvec or .hdf extension.

    pop_trans_path : os.Pathlike
        The path to the translation vector between the zoning of the input population DVector and the Trip End Model's Output Zoning.
        The translation vector should be a .csv file.

    trip_rates_path : os.PathLike
        The path to the production trip rates.
        Trip rates data should be in DVector format with either .dvec or .hdf extension.

    trip_rates_adjustment_path : os.PathLike
        TODO

    mts_path : os.PathLike
        The path to HB production mode-time splits (MTS).
        MTS data should be in DVector format with either .dvec or .hdf extension.

    mts_adjustment_path : os.PathLike
        TODO

    tem_segmentation : list[str]
        TODO

    
    """
    def __init__(
        self,
        model: ProductionModelPaths,
        population_paths: dict[int, os.PathLike],
        pop_trans_path: os.PathLike,
        trip_rates_path: os.PathLike,
        hb_fr_adjustment_path: os.PathLike,
        mts_path: os.PathLike,
        mts_adjustment_path: os.PathLike,
        tem_segmentation: cb.Segmentation,
    ):
        """
        - Assigns class attributes
        """
        self.model = model
        self.population_paths, self.trip_rates_path, self.mts_path = self._format_init_paths(population_paths, trip_rates_path, mts_path)
        self.years = list(self.population_paths.keys())
        self.tem_segmentation = tem_segmentation
        self.path_years = self.years
        self.hb_fr_adjustment_path = hb_fr_adjustment_path
        self.pop_trans = pd.read_csv(pop_trans_path) if pop_trans_path is not None else None
        self.mts_adjust_path = mts_adjustment_path

        _log_fname = "HBProductionModel_log.log"
        logger_name = "%s.%s" % ("placeholder", self.__class__.__name__)
        log_file_path = Path(self.model.export_home) / _log_fname
        self._logger = logging.getLogger(logger_name)


    def _format_init_paths(self, population_paths: dict[int, os.PathLike], trip_rates_path: os.PathLike, mts_path: os.PathLike) -> tuple[dict[int, Path], Path, Path]:
        """
        - Ensures all paths in population_paths, trip_rates_path, and mts_path
        """
        # 
        population_paths = {i: Path(j) for i, j in population_paths.items()} # Turns the os.PathLike input into Path types
        trip_rates_path = Path(trip_rates_path)
        mts_path = Path(mts_path)

        # Raises error if paths given in the constructor are invalid. # TODO use utils and add mts_adj + tr_adj
        for key, pop_path in population_paths.items():
            if not pop_path.is_file():
                raise FileNotFoundError(f"{pop_path} is not a valid file.")
        if not trip_rates_path.is_file():
            raise FileNotFoundError(f"{trip_rates_path} not a valid file.")
        if not mts_path.is_file():
            raise FileNotFoundError(f"{mts_path} is not a valid file.")
        # TODO test hb_fr_adjustment_path

        return population_paths, trip_rates_path, mts_path
    

    def run(
        self,
        export_pure_production: bool = True,
        export_mts_production: bool = False,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
    ) -> None:
        """
        Runs the HB Production model.

        Completes the following steps for each year:
            - Reads in the land use population data given in the constructor.
            - Reads in the trip rates data given in the constructor.
            - Multiplies the population and trip rates on relevant segments,
              producing "pure demand".
            - Optionally writes out a pickled DVector of "pure demand" at
              self.export_paths.pure_production[year]
            - Optionally writes out a number of "pure demand" reports, if
              reports is True.
            - Reads in the mode-time splits given in the constructor.
            - Multiplies the "pure demand" and mode-time splits on relevant
              segments, producing "fully segmented demand".
            - Optionally writes out a pickled DVector of "fully segmented demand"
              at self.export_paths.fully_segmented[year] if export_fully_segmented
              is True.
            - Aggregates this demand into self._tem_segmentation_name segmentation,
              producing "notem segmented demand".
            - Optionally writes out a number of "notem segmented demand"
              reports, if reports is True.
            - Optionally writes out a pickled DVector of "notem segmented demand"
              at self.export_paths.notem_segmented[year] if export_notem_segmentation
              is True.
            - Finally, returns "notem segmented demand" as a DVector.

        Parameters
        ----------
        export_pure_production:
            Whether to export the pure demand to disk or not.
            Will be written out to: self.export_paths.pure_production[year]

        export_mts_production:
            TODO

        export_tem_segmentation:
            Whether to export the notem segmented demand to disk or not.
            Will be written out to: self.export_paths.notem_segmented[year]

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home.

        Returns
        -------
        None
        """

        # ## START ## #
        start_time = ctk.timing.current_milli_time()
        self._logger.info("Starting HB Production Model")

        # ## READ INPUTS ## #
        # Read in the trip rates DVector file. Trip rates are not year dependent.
        trip_rates: cb.DVector = self._read_trip_rates()
        # Read in the MTS dvec file. MTS is not year dependent.
        mts: cb.DVector = self._read_mts()
        # Read in the adjustment factors, if passed
        adj_factors: cb.DVector = self._read_adj_factors()
        mts_adj_factors: cb.DVector = self._read_mts_adj_factors()

        # If all exports are False, then the function is redundant
        if not (export_pure_production or export_tem_segmentation or export_reports):
            return None

        # Generate the productions for each year
        for year in self.population_paths.keys():
            year_start_time = ctk.timing.current_milli_time()
            # ## READ INPUTS ## #
            # Read in the population land use for the given year
            population = self._read_population(year)

            # ## PURE PRODUCTION ## #
            # Creat pure productions
            pure_production = self._create_pure_production(population, trip_rates)
            # Adjust rate
            pure_production_adj = self._adjust_production(pure_production, adj_factors)
            # Export pure productions DVectors
            if export_pure_production:  # TODO tidier to put in function - probably one for both reports and pure
                pure_production.save(self.model.export_paths.pure_demand[year])
                pure_production_adj.save(self.model.export_paths.pure_demand_adj[year])
            #Export pure productions reports
            if export_reports: # TODO tidier to put in function
                utils.write_reports(pure_production, self.model.report_paths.pure_demand, year)
                utils.write_reports(pure_production_adj, self.model.report_paths.pure_demand_adj, year)

            # ## MODE TIME SPLIT ## #
            mts_production = self._create_mts_production(pure_production_adj, mts) # Only carry on adj from here TODO confirm w Isaac
            mts_production_adj = self._adjust_mts_production(mts_production, mts_adj_factors) # TODO check if HB Prod has mts adj. -> create function for this
            # Export mts production TODO tidier to put in function - probably one for both reports and pure - combine to one function, don't need duplicate func for pure and mts etc.
            if export_mts_production:
                mts_production.save(self.model.export_paths.mts_demand[year])
                mts_production_adj.save(self.model.export_paths.mts_demand_adj[year])
            if export_reports: # TODO tidier to put in function
                utils.write_reports(mts_production, self.model.report_paths.mts_demand, year)
                utils.write_reports(mts_production_adj, self.model.report_paths.mts_demand_adj, year)
            # No longer need Pure Production
            del pure_production, pure_production_adj

            # ## TEM SEGMENTATION ## #
            tem_production = self._create_tem_production(mts_production_adj)
            # Adjust rate
            #tem_production_adj = self._adjust_production(tem_production, adj_factors)
            # Export tem productions
            if export_tem_segmentation:
                tem_production.save(self.model.export_paths.tem_segmented[year])

            year_end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
            self._logger.info("HB Productions in year %s took: %s\n" % (year, time_taken))
        
        # End timing
        end_time = ctk.timing.current_milli_time()
        time_taken = ctk.timing.time_taken(start_time, end_time)
        self._logger.info("HB Production Model took:%s" % time_taken)
        self._logger.info("HB Production Model Finished")

        return None


    # # # FUNCTIONS # # #

    def _read_trip_rates(self) -> cb.DVector:
        trip_rates = cb.DVector.load(self.trip_rates_path)
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system) # TODO - have as global var / pass as zoning so it doesn't get read multiple times. Not urgent.
        trip_rates = trip_rates.translate_zoning(zoning_system, check_totals=False, no_factors=True)

        return trip_rates
    

    def _read_mts(self) -> cb.DVector:
        """
        - Reads the mode-time split (MTS) DVector, from the path given in the constructor
        - Translates the MTS DVector zoning system to the TEM Model zoning system
        """
        mts = cb.DVector.load(self.mts_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        mts = mts.translate_zoning(zoning_system, check_totals=False, no_factors=True)
        mts = mts.add_segments(['adult_nssec'])
        
        return mts
    
    def _read_adj_factors(self):
        """Reads in trip rates adjustment factors
        """
        if self.hb_fr_adjustment_path is None:
            return None
        
        self._logger.info("Loading the trip rates adjustment factors")
        adj_factors = cb.DVector.load(self.hb_fr_adjustment_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        adj_factors = adj_factors.translate_zoning(zoning_system, check_totals=False, no_factors=True)
        # adj_factors = adj_factors.add_segments(['adult_nssec'])

        return adj_factors
    

    def _read_mts_adj_factors(self):
        """Reads in MTS adjustment factors
        """
        if self.mts_adjust_path is None:
            return None
        
        self._logger.info("Loading the MTS adjustment factors")
        adj_factors = cb.DVector.load(self.mts_adjust_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        adj_factors = adj_factors.translate_zoning(zoning_system, check_totals=False, no_factors=True)
        # adj_factors = adj_factors.add_segments(['adult_nssec'])

        return adj_factors
    

    def _read_population(self, year: int):
        """Reads in the Population Landuse DVector
        - Reads the population land use DVector, for one given year, from the path given in the constructor
        - Translates the population landuse DVector zoning system to the TEM Model zoning system
        """

        self._logger.info(f"Year {year}:\n  Loading the population data")
        population = cb.DVector.load(self.population_paths[year])
        # Ensure zoning system of mts matches the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        population = population.translate_zoning(zoning_system, trans_vector=self.pop_trans, check_totals=True, no_factors=False)
        
        return population


    def _create_pure_production(self, population: cb.DVector, trip_rates: cb.DVector) -> cb.DVector:
        """Creates Pure Production
        - Multiplies the population landuse by the trip rates, creating pure production
        """
        self._logger.info(" Calculating pure production")
        pure_production = population * trip_rates

        return pure_production


    def _adjust_production(self, production, adj_factors):
        """Adjusts the Pure Production
        - 
        """
        self._logger.info(" Calculating pure production")
        if adj_factors is not None:
            production_adj = production * adj_factors
        else:
            production_adj = production
        
        return production_adj
        

    def _create_mts_production(self, pure_production: cb.DVector, mts: cb.DVector) -> cb.DVector:
        """
        - Multiplies the Pure Production by the mode-time split DVector, as passed into the constructor
        """
        self._logger.info(" Applying mode time split")
        mts_production = pure_production * mts

        return mts_production
    

    def _adjust_mts_production(self, mts_production: cb.DVector, adj_factors: cb.DVector) -> dict[int, cb.DVector]:
        if adj_factors is not None:
            self._logger.info(" Adjusting mode time split")
            mts = mts_production
            #if "total" not in mts.segmentation.names:
            #    mts = mts.add_segments([cb.segmentation.SegmentsSuper("total").get_segment()])
            adj_factors.fill(0,1)
            adj = mts * adj_factors
            numerator = mts.aggregate(["p"]).translate_zoning(cb.ZoningSystem.get_zoning("gor")).translate_zoning(cb.ZoningSystem.get_zoning(self.model._zoning_system), check_totals=False, no_factors=True)
            denomenator = adj.aggregate(["p"]).translate_zoning(cb.ZoningSystem.get_zoning("gor")).translate_zoning(cb.ZoningSystem.get_zoning(self.model._zoning_system), check_totals=False, no_factors=True)
            adj = adj * (numerator/denomenator)
            mts_production_adj = adj
        else:
            mts_production_adj = mts_production
        
        return mts_production_adj


    def _create_tem_production(self, mts_production: cb.DVector) -> cb.DVector:
        """TEM Production
        - Aggregates MTS Production to TEM Segmentation
        """
        self._logger.info(" Aggregating to TEM Output Segmentation")
        tem_production = mts_production.aggregate(self.tem_segmentation)

        return tem_production


class NHBProductionModel_TP:
    _log_fname = "HBProductionModel_log.log"
    """The Home-Based Production Model of NoTEM

    The production model can be ran by calling the class run() method.

    Attributes
    ----------
    population_paths: Dict[int, os.PathLike]:
        Dictionary of {year: land_use_employment_data} pairs. As passed
        into the constructor.

    trip_rates_path: str
        The path to the production trip rates. As passed into the constructor.

    mts_path: str
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

    def __init__(
        self,
        hb_attraction_model: AttractionModelPaths, # HB Attraction Paths for balancing - not user input - assume these are pure attraction.
        model: ProductionModelPaths,
        trip_rates_path: os.PathLike,
        balance_production,
        mts_path: str,
        return_segmentation
    ) -> None:
        """
        Sets up and validates arguments for the NHB Production model.

        Parameters
        ----------
        hb_attraction_paths:
            Dictionary of {year: notem_segmented_HB_attractions_data} pairs.
            These paths should come from nd.HBAttraction model and should
            be pickled Dvector paths.

        population_paths:
            Dictionary of {year: land_use_population_data} pairs.

        trip_rates_path:
            The path to the NHB production trip rates.
            Should have the columns as defined in:
            NHBProductionModel._target_cols['nhb_trip_rate']

        mts_path:
            The path to NHB production time split.
            Should have the columns as defined in:
            NHBProductionModel._target_cols['tp']

        export_home:
            Path to export NHB Production outputs.

        constraint_paths:
            Dictionary of {year: constraint_path} pairs.
            Must contain the same keys as land_use_paths, but it can contain
            more (any extras will be ignored).
            If set - will be used to constrain the productions - a report will
            be written before and after.

        process_count:
            The number of processes to create in the Pool. Typically this
            should not exceed the number of cores available.
            Defaults to consts.PROCESS_COUNT.
        """

        ## Assign
        self.hb_attraction_model = hb_attraction_model
        self.hb_attraction_paths = hb_attraction_model.export_paths.fully_segmented
        self.trip_rates_path = trip_rates_path
        self.mts_path = mts_path
        self.balance_production = balance_production
        self.years = list(self.hb_attraction_paths.keys())
        self.model = model
        self.return_segmentation = return_segmentation
#
    def run(
        self,
        export_nhb_pure_demand: bool = True,
        export_fully_segmented: bool = False,
        export_notem_segmentation: bool = True,
        export_reports: bool = True,
    ) -> None:
        """
        Runs the NHB Production model.

        Completes the following steps for each year:
            - Reads in the notem segmented HB attractions compressed pickle
              given in the constructor.
            - Removes time period segmentation from the above data.
            - Reads in the land use population data given in the constructor,
              extracts the mapping of msoa_zone_id to tfn_at.
            - Reads in the NHB trip rates data given in the constructor.
            - Multiplies the HB attractions and NHB trip rates on relevant segments,
              producing "pure NHB demand".
            - Optionally writes out a pickled DVector of "pure NHB demand" at
              self.export_paths.pure_demand[year]
            - Optionally writes out a number of "pure demand" reports, if
              reports is True.
            - Reads in the time splits given in the constructor.
            - Multiplies the "pure NHB demand" and time splits on relevant
              segments, producing "fully segmented demand".
            - Optionally writes out a pickled DVector of "fully segmented demand"
              at self.export_paths.fully_segmented[year] if export_fully_segmented
              is True.
            - Renames nhb_p and nhb_m as p and m respectively,
              producing "notem segmented demand".
            - Optionally writes out a number of "notem segmented demand"
              reports, if reports is True.
            - Optionally writes out a pickled DVector of "notem segmented demand"
              at self.export_paths.notem_segmented[year] if export_notem_segmentation
              is True.

        Parameters
        ----------
        export_nhb_pure_demand:
            Whether to export the pure NHB demand to disk or not.
            Will be written out to: self.export_paths.pure_demand[year]

        export_fully_segmented:
            Whether to export the fully segmented demand to disk or not.
            Will be written out to: self.export_paths.fully_segmented[year]

        export_notem_segmentation:
            Whether to export the notem segmented demand to disk or not.
            Will be written out to: self.export_paths.notem_segmented[year]

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home.

        Returns
        -------
        None
        """

        # ## START ## #

        # ## READ INPUTS ## #
        # TODO
        trip_rates = self._read_trip_rates()
        # TODO
        mts = self._read_mts()

        # Generate the nhb productions for each year
        for year in self.years:

            # ## GENERATE PURE DEMAND ## #
            # TODO
            hbattr = self._read_HB_attraction(year)

            # ## PURE PRODUCTION ## #
            # TODO
            pure_production = self._create_pure_production(hbattr, trip_rates)
            # TODO
            if export_nhb_pure_demand:
                pure_production.save(self.model.export_paths.pure_demand[year])
            if export_reports:
                pass # self._write_reports(pure_production) # TODO this should be a utils function
            
            # ## MODE TIME SPLIT ## #
            # TODO
            mts_production = self._create_mts_production(pure_production, mts)

            # ## TEM SEGMENTATION ## #
            # TODO
            tem_production = self._create_tem_production(mts_production)
            
            if export_notem_segmentation:
                tem_production.save(self.model.export_paths.tem_segmented[year])


    # # # FUNCTIONS # # #

    def _read_trip_rates(self) -> cb.DVector:
        """
        - TODO
        """
        # self._logger.info("Loading the trip rates data")
        trip_rates = cb.DVector.load(self.trip_rates_path)
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system) # TODO - have as global var / pass as zoning so it doesn't get read multiple times. Not urgent. - possibly change to utils func "read dvec" from path input
        trip_rates = trip_rates.translate_zoning(zoning_system, check_totals=False, no_factors=True)

        return trip_rates
    

    def _read_mts(self) -> cb.DVector:
        """
        - Reads the mode-time split (MTS) DVector, from the path given in the constructor
        - Translates the MTS DVector zoning system to the TEM Model zoning system
        """
        self._logger.info("Loading the mode time split data")
        mts = cb.DVector.load(self.mts_path)
        # Ensure zoning system of mts matches the TEM Model zoning system
        zoning_system = cb.ZoningSystem.get_zoning(self.model._zoning_system)
        mts = mts.translate_zoning(zoning_system, check_totals=False, no_factors=True)
        
        return mts
    

    def _read_HB_attraction(self, year: int) -> cb.DVector: # TODO tidy. Perhaps use segment translation method.
        """
        - Reads the TEM Segmented HB Attraction file, as written by the HB Attraction model
        - Removes time period from the HB Attraction DVector segmentation
        - Changes the purpose and mode segmentations, to explicit home-based purpose and home-based mode segmentations
        """
        hbattr =  cb.DVector.load(self.hb_attraction_model.export_paths.tem_segmented[year])
        segs = hbattr.segmentation.names
        if "tp" in segs:
            segs.remove("tp")
            hbattr = hbattr.aggregate(segs)
        # hbattr.translate_segment("p", "p_hb") TODO something like this could be possible and tidier
        hbattr_data = hbattr.data.reset_index().rename(columns={"p": "p_hb", "m": "m_hb"})
        segs = hbattr.segmentation.names
        segs.remove("p")
        segs.remove("m")
        segs.append("p_hb")
        segs.append("m_hb")
        hbattr_data = hbattr_data.set_index(segs)
        hbattr = cb.DVector(segmentation=cb.Segmentation(cb.SegmentationInput(enum_segments=segs, naming_order=segs)),
                            import_data=hbattr_data,
                            zoning_system=hbattr.zoning_system)
        
        return hbattr


    def _create_pure_production(self, hbattr: cb.DVector, trip_rates: cb.DVector) -> cb.DVector:
        """
        - TODO
        """
        pure_production = hbattr * trip_rates

        return pure_production
    

    def _create_mts_production(self, pure_production: cb.DVector, mts: cb.DVector) -> cb.DVector:
        mts_production = pure_production * mts
        segs = mts_production.segmentation.names
        segs.remove("p_hb")
        segs.remove("m_hb")
        mts_production = mts_production.aggregate(segs)
        mts_production_data = mts_production.data.reset_index().rename(columns={"m_nhb": "m", "p_nhb": "p"})
        segs.remove("p_nhb")
        segs.remove("m_nhb")
        segs.append("p")
        segs.append("m")
        mts_production_data = mts_production_data.set_index(segs)
        mts_production = cb.DVector(segmentation = cb.Segmentation(cb.SegmentationInput(enum_segments=segs,
                                                                    naming_order=segs)),
            import_data=mts_production_data,
            zoning_system=mts_production.zoning_system)
        
        return mts_production
    

    def _create_tem_production(self, mts_production: cb.DVector) -> cb.DVector:
        """
        - Aggregates the mode-time split productions to the TEM segmentation
        """
        tem_production = mts_production.aggregate(self.return_segmentation)
        

    def _generate_nhb_productions(
        self,
        hb_attractions: cb.DVector,
    ) -> cb.DVector:
        """
        - 
        Applies NHB trip rates to hb_attractions

        Parameters
        ----------
        hb_attractions:
            Dvector containing the data to apply the trip rates to.

        Returns
        -------
        pure_NHB_demand:
            Returns the product of HB attractions and NHB trip rate Dvector
            ie., pure NHB demand
        """

        # Define the zoning and segmentations we want to use
        nhb_trip_rate_seg = cb.Segmentation(self.tem_segs.trip_rates)
        pure_seg = cb.Segmentation(self.tem_segs.prod_pure)

        # Reading NHB trip rates
        trip_rates_dvec = cb.DVector.load(self.trip_rates_path)
        if trip_rates_dvec.segmentation != nhb_trip_rate_seg:
            raise cb.segmentation.SegmentationError(
                "Unexpected segmentation in trip rates DVector."
            )

        # Multiply
        return (hb_attractions * trip_rates_dvec).aggregate(pure_seg)


class HBProductionModel(ProductionModelPaths):

    _log_fname = "HBProductionModel_log.log"

    """The Home-Based Production Model of NoTEM

    The production model can be ran by calling the class run() method.

    Attributes
    ----------
    population_paths: Dict[int, os.PathLike]:
        Dictionary of {year: land_use_employment_data} pairs. As passed
        into the constructor.

    trip_rates_path: str
        The path to the production trip rates. As passed into the constructor.

    mts_path: str
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
    # TRANS_PATH = pathlib.Path(r"E:\tem\lsoa_at_lookup.csv")

    def __init__(
        self,
        population_paths: dict[int, os.PathLike],
        trip_rates_path: os.PathLike,
        mode_time_splits_path: os.PathLike,
        export_home: os.PathLike,
        return_segmentation: cb.Segmentation,
        model_zoning: cb.ZoningSystem,
        process_count: int = 1,
    ) -> None:
        """
        Sets up and validates arguments for the Production model.

        Parameters
        ----------
        population_paths:
            Dictionary of {year: population_data} pairs.
            HBProductionModel._target_col_dtypes['pop']

        trip_rates_path:
            The path to the production trip rates.
            Should have the columns as defined in:
            HBProductionModel._target_col_dtypes['trip_rate']

        mode_time_splits_path:
            The path to production mode-time splits.
            Should have the columns as defined in:
            HBProductionModel._target_col_dtypes['m_tp']

        export_home:
            Path to export production outputs.

        constraint_paths:
            Dictionary of {year: constraint_path} pairs.
            Must contain the same keys as land_use_paths, but it can contain
            more (any extras will be ignored).
            If set - will be used to constrain the productions - a report will
            be written before and after.

        process_count:
            The number of processes to create in the Pool. Typically this
            should not exceed the number of cores available.
            Defaults to consts.PROCESS_COUNT.

        trip_end_adjustments: List[TripEndAdjustmentFactors], optional
            List of all adjustment factors to apply to the trip ends. Adjustments
            are applied one after another at to the productions in the output
            segmentation.
        """
        # Check that the paths we need exist!

        # Validate that we have data for all the years we're running for

        # Assign
        self.population_paths = {i: pathlib.Path(j) for i, j in population_paths.items()}
        self.trip_rates_path = pathlib.Path(trip_rates_path)
        self.mode_time_splits_path = pathlib.Path(mode_time_splits_path)
        self.process_count = process_count
        self.years = list(self.population_paths.keys())
        self.trans = None
        self.return_segmentation = return_segmentation
        self.model_zoning = model_zoning

        for key, pop_path in self.population_paths.items():
            if (not pop_path.is_file()) and (not pop_path.is_dir()):
                raise FileNotFoundError(f"{pop_path} is not a valid file.")

        if not self.trip_rates_path.is_file():
            raise FileNotFoundError(f"{trip_rates_path} not a valid file.")
        if not self.mode_time_splits_path.is_file():
            raise FileNotFoundError(f"{mode_time_splits_path} is not a valid file.")

        # Make sure the reports paths exists
        report_home = pathlib.Path(export_home) / "Reports"
        report_home.mkdir(exist_ok=True, parents=True)

        # Build the output paths
        super().__init__(
            path_years=self.years,
            export_home=export_home,
            report_home=report_home,
            zoning_system=self.model_zoning.name,
            _trip_origin="hb",
        )
        # TODO sort loggers
        logger_name = "%s.%s" % ("placeholder", self.__class__.__name__)
        log_file_path = self.export_home / self._log_fname
        self._logger = logging.getLogger(logger_name)

    def run(
        self,
        export_pure_demand: bool = True,
        export_tem_segmentation: bool = True,
        export_reports: bool = True,
    ) -> None:
        """
        Runs the HB Production model.

        Completes the following steps for each year:
            - Reads in the land use population data given in the constructor.
            - Reads in the trip rates data given in the constructor.
            - Multiplies the population and trip rates on relevant segments,
              producing "pure demand".
            - Optionally writes out a pickled DVector of "pure demand" at
              self.export_paths.pure_demand[year]
            - Optionally writes out a number of "pure demand" reports, if
              reports is True.
            - Reads in the mode-time splits given in the constructor.
            - Multiplies the "pure demand" and mode-time splits on relevant
              segments, producing "fully segmented demand".
            - Optionally writes out a pickled DVector of "fully segmented demand"
              at self.export_paths.fully_segmented[year] if export_fully_segmented
              is True.
            - Aggregates this demand into self._return_segmentation_name segmentation,
              producing "notem segmented demand".
            - Optionally writes out a number of "notem segmented demand"
              reports, if reports is True.
            - Optionally writes out a pickled DVector of "notem segmented demand"
              at self.export_paths.notem_segmented[year] if export_notem_segmentation
              is True.
            - Finally, returns "notem segmented demand" as a DVector.

        Parameters
        ----------
        export_pure_demand:
            Whether to export the pure demand to disk or not.
            Will be written out to: self.export_paths.pure_demand[year]

        export_tem_segmentation:
            Whether to export the notem segmented demand to disk or not.
            Will be written out to: self.export_paths.notem_segmented[year]

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home.

        Returns
        -------
        None
        """
        # Initialise timing

        start_time = ctk.timing.current_milli_time()
        self._logger.info("Starting HB Production Model")

        # Generate the productions for each year
        for year in self.years:
            year_start_time = ctk.timing.current_milli_time()
            # ## GENERATE PURE DEMAND ## #
            self._logger.info("Loading the population data")
            if os.path.isdir(self.pop_dvec_paths[year]):
                # TODO this file name shouldn't be hard coded
                pop_dvec, self.trans = read_pop_lu(
                    self.pop_dvec_paths[year],
                    "Output P11_{}.hdf",
                    out_zoning=self.model_zoning,
                )
                pop_dvec.save(self.export_paths.home / f"pop_{year}.dvec")

            else:
                pop_dvec = cb.DVector.load(self.pop_dvec_paths[year])
                if pop_dvec.zoning_system != self.model_zoning:
                    self.trans = pop_dvec.zoning_system.translate(self.model_zoning)
                    pop_dvec = pop_dvec.translate_zoning(
                        self.model_zoning, trans_vector=self.trans
                    )

            self._logger.info("Applying trip rates")
            pure_demand = self._generate_productions(pop_dvec)

            if export_pure_demand:
                self._logger.info("Exporting pure demand to disk")
                pure_demand.save(self.export_paths.pure_demand[year])

            if export_reports:
                self._logger.info("Exporting pure demand reports to disk")
                pure_demand_paths = self.report_paths.pure_demand
                pure_demand.write_sector_reports(
                    segment_totals_path=pure_demand_paths.segment_total[year],
                    ca_sector_path=pure_demand_paths.ca_sector[year],
                    ie_sector_path=pure_demand_paths.ie_sector[year],
                )

            # ## SPLIT PURE DEMAND BY MODE AND TIME ## #
            self._logger.info("Splitting by mode and time")
            fully_segmented, fully_segmented_sum = self._split_by_tp_and_mode(
                pure_demand, year
            )

            # ## PRODUCTIONS TOTAL CHECK ## #
            if not pure_demand.sum_is_close(fully_segmented_sum, 0.01, 100):
                msg = (
                    "The production totals before and after mode time split are not same.\n"
                    "Expected %f\n"
                    "Got %f" % (pure_demand.sum(), fully_segmented_sum)
                )
                self._logger.warning(msg)
                warnings.warn(msg)

            # ## AGGREGATE INTO RETURN SEGMENTATION ## #
            return_seg = self.return_segmentation
            productions = cb.DVector.concat_from_dir(
                folder=fully_segmented, segmentation=return_seg
            )

            if export_tem_segmentation:
                self._logger.info("Exporting tem segmented demand to disk")
                productions.save(self.export_paths.tem_segmented[year])

            if export_reports:
                # TODO possible save segmentations/subsets somewhere standard
                self._logger.info("Exporting notem segmented reports to disk")
                tem_segmented_paths = self.report_paths.tem_segmented
                productions.write_sector_reports(
                    segment_totals_path=tem_segmented_paths.segment_total[year],
                    ca_sector_path=tem_segmented_paths.ca_sector[year],
                    ie_sector_path=tem_segmented_paths.ie_sector[year],
                )

            # Print timing stats for the year
            year_end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
            self._logger.info("HB Productions in year %s took: %s\n" % (year, time_taken))

        # End timing
        end_time = ctk.timing.current_milli_time()
        time_taken = ctk.timing.time_taken(start_time, end_time)
        self._logger.info("HB Production Model took:%s" % time_taken)
        self._logger.info("HB Production Model Finished")

    def _generate_productions(
        self,
        population: cb.DVector,
    ) -> cb.DVector:
        """
        Applies trip rate split on the given HB productions

        Parameters
        ----------
        population:
            DVector containing the population.

        Returns
        -------
        pure_demand:
            Returns the product of population and trip rate Dvector
            ie., pure demand
        """
        # Reading trip rates
        trip_rates = cb.DVector.load(self.trip_rates_path)
        # ## MULTIPLY TOGETHER ## #
        if trip_rates.zoning_system == self.model_zoning:
            prod = population * trip_rates
        else:
            if self.trans is None:
                self.trans: pd.DataFrame = trip_rates.zoning_system.translate(
                    other=population.zoning_system
                )
            trip_rates_disag: cb.DVector = trip_rates.translate_zoning(
                new_zoning=population.zoning_system,
                trans_vector=self.trans,
                check_totals=False,
                no_factors=True,
            )
            prod: cb.DVector = population * trip_rates_disag
        return prod

    def _split_by_tp_and_mode(self, pure_demand: cb.DVector, year: int) -> cb.DVector:
        """
        Applies time period and mode splits to the given pure demand.

        Parameters
        ----------
        pure_demand:
            Dvector containing the pure demand to split.

        Returns
        -------
        full_segmented_demand:
            A DVector containing pure_demand split by mode and time.
        """
        mode_time_splits = cb.DVector.load(self.mode_time_splits_path)
        total = 0
        # TODO probably needs to be more flexible --> NB. that if the zoning system is the same, pure_demand won't be a dict hence won't have attr. items.
        if mode_time_splits.zoning_system != pure_demand.zoning_system:
            pure_demand = pure_demand.split_by_agg_zoning(
                mode_time_splits.zoning_system, trans=self.trans
            )
        for zone, dvec in pure_demand.items():
            mts = mode_time_splits.select_zone(zone)
            dvec *= mts
            out_path = self.export_paths.fully_segmented[year]
            out_path.mkdir(exist_ok=True, parents=False)
            dvec.save(out_path / f"at_{zone}.hdf")
            total += dvec.sum()
        return out_path, total

    def _trip_end_adjustment(self, trip_ends: cb.DVector) -> cb.DVector:
        """Multiply `trip_ends` by `adjustment_factors`.

        Trip ends are multiplied by all adjustment factors in
        the list one after another.

        Parameters
        ----------
        trip_ends : cb.DVector
            Productions trip ends for adjustment.

        Returns
        -------
        cb.DVector
            Productions trip ends after applying all adjustments.
        """
        for adjustment in self.adjustment_factors:
            self._logger.info("adjusting trip ends with %s", adjustment.file)

            adjust_dvec = adjustment.dvector
            if adjustment.zoning != trip_ends.zoning_system:
                adjust_dvec = adjustment.dvector.translate_zoning(
                    trip_ends.zoning_system, weighting="no_weight"
                )

            trip_ends = trip_ends * adjust_dvec

        return trip_ends


class NHBProductionModel(ProductionModelPaths):
    _log_fname = "NHBProductionModel_log.log"
    """The Non Home-Based Production Model of NoTEM

        The production model can be ran by calling the class run() method.

        Attributes
        ----------
        hb_attraction_paths:
            Dictionary of {year: notem_segmented_HB_attractions_data} pairs.
            As passed into the constructor.

        population_paths: Dict[int, os.PathLike]:
            Dictionary of {year: land_use_employment_data} pairs. As passed
            into the constructor.

        trip_rates_path: str
            The path to the NHB production trip rates. As passed into the constructor.

        time_splits_path: str
            The path to the NHB production time splits. As passed into the
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

        See NHBProductionModelPaths for documentation on:
            "path_years, export_home, report_home, export_paths, report_paths"
        """

    def __init__(
        self,
        tem_segs: TEMSegmentations,
        hb_attraction_paths: Dict[int, os.PathLike],
        trip_rates_path: str,
        time_splits_path: str,
        export_home: str,
        constraint_paths: Dict[int, os.PathLike] = None,
        process_count: int = 1,
    ) -> None:
        """
        Sets up and validates arguments for the NHB Production model.

        Parameters
        ----------
        hb_attraction_paths:
            Dictionary of {year: notem_segmented_HB_attractions_data} pairs.
            These paths should come from nd.HBAttraction model and should
            be pickled Dvector paths.

        population_paths:
            Dictionary of {year: land_use_population_data} pairs.

        trip_rates_path:
            The path to the NHB production trip rates.
            Should have the columns as defined in:
            NHBProductionModel._target_cols['nhb_trip_rate']

        time_splits_path:
            The path to NHB production time split.
            Should have the columns as defined in:
            NHBProductionModel._target_cols['tp']

        export_home:
            Path to export NHB Production outputs.

        constraint_paths:
            Dictionary of {year: constraint_path} pairs.
            Must contain the same keys as land_use_paths, but it can contain
            more (any extras will be ignored).
            If set - will be used to constrain the productions - a report will
            be written before and after.

        process_count:
            The number of processes to create in the Pool. Typically this
            should not exceed the number of cores available.
            Defaults to consts.PROCESS_COUNT.
        """
        # Check that the paths we need exist! --> turn into some function e.g. validate input.
        [check_file_exists(x) for x in hb_attraction_paths.values()]
        check_file_exists(trip_rates_path)
        check_file_exists(time_splits_path)

        if constraint_paths is not None:
            [check_file_exists(x) for x in constraint_paths.values()]

        ## Assign
        self.tem_segs = tem_segs
        self.hb_attraction_paths = hb_attraction_paths
        self.trip_rates_path = trip_rates_path
        self.time_splits_path = time_splits_path
        self.process_count = process_count
        self.years = list(self.hb_attraction_paths.keys())

        # Make sure the reports paths exists
        export_home = Path(export_home)
        report_home = export_home / "Reports"
        report_home.mkdir(exist_ok=True, parents=True)

        # Build the output paths
        super().__init__(
            path_years=self.years,
            export_home=export_home,
            report_home=report_home,
        )
        # Create a logger
        logger_name = "%s.%s" % (nd.get_package_logger_name(), self.__class__.__name__)
        log_file_path = os.path.join(self.export_home, self._log_fname)
        self._logger = nd.get_logger(
            logger_name=logger_name,
            log_file_path=log_file_path,
            instantiate_msg="Initialised NHB Production Model",
        )

    """def _production_nhb(self, hbf_attr: Dict) -> Dict:
        fun.log_stderr('\nProduction trip-end (NHB)')
        # not yet possible to implement multiprocessing
        nhb_fldr = self.nts_fldr / self.fld_prod / self.fld_nhbase
        nhb_rate = fun.csv_to_dfr(nhb_fldr / self.fld_rates / 'nhb_trip_rates_production.csv')
        nhb_rate.drop(columns=['trips', 'trips.hb'], inplace=True)
        col_grby = [col for col in self.seg_spec if col != 'period']
        nhb_prod = {pp: pd.DataFrame() for pp in hbf_attr}
        for pp in hbf_attr:
            out = hbf_attr[pp].groupby(col_grby)[['trips']].sum().reset_index()
            out = out.rename(columns={col: f'{col}.hb' for col in ['mode', 'purpose']})
            fac = nhb_rate.loc[nhb_rate['purpose.hb'] == pp]
            out = out.merge(fac, how='left', on=['tfn_at', 'mode.hb', 'purpose.hb'])
            out['trips'] = out['trips'].mul(out['gamma'])
            out = out.groupby(col_grby)[['trips']].sum().reset_index()
            # add trips to nhb_prod[px]
            for px in out['purpose'].unique():
                _list = [nhb_prod[px], out.loc[out['purpose'] == px]]
                nhb_prod[px] = (pd.concat(_list, axis=0).groupby(col_grby)[['trips']]
                                .sum().reset_index())

        # apply nhb time split: mts[at, p, m](t)
        fun.log_stderr(' .. apply mode-time split')
        mts_grby = [col for col in self.mts_incl if col not in ["period", "rho"]]
        mts_fact = fun.csv_to_dfr(nhb_fldr / self.fld_split /
                                  f"mode_time_split_production_nhb{self.rho_type}.csv",
                                  self.mts_incl)

        pool = mp.Pool(self.num_cpus)
        nhb_prod = {pp: pool.apply_async(self._fn_prod_nhb_mts,
                                         [pp, itm, col_grby, mts_fact, mts_grby])
                    for pp, itm in nhb_prod.items()}
        pool.close()
        pool.join()
        nhb_prod = {pp: itm.get() for pp, itm in nhb_prod.items()}

        return nhb_prod"""

    def run(
        self,
        export_nhb_pure_demand: bool = False,
        export_fully_segmented: bool = False,
        export_notem_segmentation: bool = True,
        export_reports: bool = True,
    ) -> None:
        """
        Runs the NHB Production model.

        Completes the following steps for each year:
            - Reads in the notem segmented HB attractions compressed pickle
              given in the constructor.
            - Removes time period segmentation from the above data.
            - Reads in the land use population data given in the constructor,
              extracts the mapping of msoa_zone_id to tfn_at.
            - Reads in the NHB trip rates data given in the constructor.
            - Multiplies the HB attractions and NHB trip rates on relevant segments,
              producing "pure NHB demand".
            - Optionally writes out a pickled DVector of "pure NHB demand" at
              self.export_paths.pure_demand[year]
            - Optionally writes out a number of "pure demand" reports, if
              reports is True.
            - Reads in the time splits given in the constructor.
            - Multiplies the "pure NHB demand" and time splits on relevant
              segments, producing "fully segmented demand".
            - Optionally writes out a pickled DVector of "fully segmented demand"
              at self.export_paths.fully_segmented[year] if export_fully_segmented
              is True.
            - Renames nhb_p and nhb_m as p and m respectively,
              producing "notem segmented demand".
            - Optionally writes out a number of "notem segmented demand"
              reports, if reports is True.
            - Optionally writes out a pickled DVector of "notem segmented demand"
              at self.export_paths.notem_segmented[year] if export_notem_segmentation
              is True.

        Parameters
        ----------
        export_nhb_pure_demand:
            Whether to export the pure NHB demand to disk or not.
            Will be written out to: self.export_paths.pure_demand[year]

        export_fully_segmented:
            Whether to export the fully segmented demand to disk or not.
            Will be written out to: self.export_paths.fully_segmented[year]

        export_notem_segmentation:
            Whether to export the notem segmented demand to disk or not.
            Will be written out to: self.export_paths.notem_segmented[year]

        export_reports:
            Whether to output reports while running. All reports will be
            written out to self.report_home.

        Returns
        -------
        None
        """
        # Initialise timing

        start_time = ctk.timing.current_milli_time()
        self._logger.info("Starting NHB Production Model")

        # Generate the nhb productions for each year
        for year in self.years:
            year_start_time = ctk.timing.current_milli_time()

            # ## GENERATE PURE DEMAND ## #
            self._logger.info("Loading the HB attraction data")
            hb_attr_dvec = self._transform_attractions(year)

            self._logger.info("Applying trip rates")
            pure_nhb_demand = self._generate_nhb_productions(hb_attr_dvec)

            if export_nhb_pure_demand:
                self._logger.info("Exporting NHB pure demand to disk")
                pure_nhb_demand.save(self.export_paths.pure_demand[year])

            if export_reports:
                self._logger.info("Exporting NHB pure demand reports to disk")
                report_seg = cb.Segmentation(self.tem_segs.prod_pure_report)
                pure_demand_paths = self.report_paths.pure_demand
                pure_nhb_demand.aggregate(report_seg).write_sector_reports(
                    segment_totals_path=pure_demand_paths.segment_total[year],
                    ca_sector_path=pure_demand_paths.ca_sector[year],
                    ie_sector_path=pure_demand_paths.ie_sector[year],
                )

            # ## SPLIT NHB PURE DEMAND BY TIME ## #
            self._logger.info("Splitting by time")
            fully_segmented = self._split_by_tp(pure_nhb_demand)

            # ## PRODUCTIONS TOTAL CHECK ## #
            if not pure_nhb_demand.sum_is_close(fully_segmented):
                msg = (
                    "The NHB production totals before and after time split are not same.\n"
                    "Expected %f\n"
                    "Got %f" % (pure_nhb_demand.sum(), fully_segmented.sum())
                )
                self._logger.warning(msg)
                warnings.warn(msg)

            if export_fully_segmented:
                self._logger.info("Exporting fully segmented demand to disk")
                fully_segmented.save(self.export_paths.fully_segmented[year])

            # Renaming
            tem_segmented = fully_segmented.aggregate(cb.Segmentation(self.tem_segs.nhb_prod))

            # ## PRODUCTIONS TOTAL CHECK ## #
            if not fully_segmented.sum_is_close(tem_segmented):
                msg = (
                    "The NHB production totals before and after rename to "
                    "output segmentation are not same.\n"
                    "Expected %f\n"
                    "Got %f" % (pure_nhb_demand.sum(), fully_segmented.sum())
                )
                self._logger.warning(msg)
                warnings.warn(msg)

            if export_notem_segmentation:
                self._logger.info("Exporting notem segmented demand to disk")
                tem_segmented.save(self.export_paths.notem_segmented[year])

            if export_reports:
                self._logger.info("Exporting notem segmented reports to disk\n")
                tem_segmented_paths = self.report_paths.tem_segmented
                tem_segmented.write_sector_reports(
                    segment_totals_path=tem_segmented_paths.segment_total[year],
                    ca_sector_path=tem_segmented_paths.ca_sector[year],
                    ie_sector_path=tem_segmented_paths.ie_sector[year],
                    lad_report_path=tem_segmented_paths.lad_report[year],
                    lad_report_seg=cb.Segmentation(self.tem_segs.lad_report_seg),
                )

            # Print timing stats for the year
            year_end_time = ctk.timing.current_milli_time()
            time_taken = ctk.timing.time_taken(year_start_time, year_end_time)
            self._logger.info("NHB Productions in year %s took: %s\n" % (year, time_taken))

        # End timing
        end_time = ctk.timing.current_milli_time()
        time_taken = ctk.timing.time_taken(start_time, end_time)
        self._logger.info("NHB Production Model took:%s" % time_taken)
        self._logger.info("NHB Production Model Finished")

    def _transform_attractions(
        self,
        year: int,
    ) -> cb.DVector:
        """
        Removes time period and adds tfn_at to HB attraction DVector

        - Reads the HB attractions compressed pickle.
        - Removes time period from segmentation.
        - Extracts the mapping of msoa_zone_id to tfn_at from land use.
        - Adds tfn_at to the HB attraction and returns its DVector.

        Parameters
        ----------
        year:
            The year to get HB attractions data for.

        Returns
        -------
        hb_attr_dvec:
            Returns the HB attraction Dvector with tfn_at.
        """
        # Define the zoning and segmentations we want to use
        # TODO this function is probably unnecessary
        tem_no_tp_seg = cb.Segmentation(self.tem_segs.output_no_tp)
        tem_output_seg = cb.Segmentation(self.tem_segs.output)
        hb_attr_notem = cb.DVector.load(self.hb_attraction_paths[year])
        if hb_attr_notem.segmentation != tem_output_seg:
            raise cb.segmentation.SegmentationError(
                "Unexpected segmentation. This DVector should be "
                f"{tem_output_seg.names}, but is actually {hb_attr_notem.segmentation.names}."
            )
        # Remove time period
        hb_attr = hb_attr_notem.aggregate(tem_no_tp_seg)
        return hb_attr.add_segment(
            cb.segments.SegmentsSuper("at").get_segment(), split_method="duplicate"
        )

    def _generate_nhb_productions(
        self,
        hb_attractions: cb.DVector,
    ) -> cb.DVector:
        """
        Applies NHB trip rates to hb_attractions

        Parameters
        ----------
        hb_attractions:
            Dvector containing the data to apply the trip rates to.

        Returns
        -------
        pure_NHB_demand:
            Returns the product of HB attractions and NHB trip rate Dvector
            ie., pure NHB demand
        """

        # Define the zoning and segmentations we want to use
        nhb_trip_rate_seg = cb.Segmentation(self.tem_segs.trip_rates)
        pure_seg = cb.Segmentation(self.tem_segs.prod_pure)

        # Reading NHB trip rates
        trip_rates_dvec = cb.DVector.load(self.trip_rates_path)
        if trip_rates_dvec.segmentation != nhb_trip_rate_seg:
            raise cb.segmentation.SegmentationError(
                "Unexpected segmentation in trip rates DVector."
            )

        # Multiply
        return (hb_attractions * trip_rates_dvec).aggregate(pure_seg)

    def _split_by_tp(
        self,
        pure_nhb_demand: cb.DVector,
    ) -> cb.DVector:
        """
        Applies time period splits to the given pure nhb demand.

        Parameters
        ----------
        pure_nhb_demand:
            Dvector containing the pure nhb demand to split.

        Returns
        -------
        full_segmented_demand:
            A DVector containing pure_demand split by time.
        """
        # Define the segmentation we want to use
        # nhb_time_splits_seg = nd.get_segmentation_level('notem_nhb_tfnat_p_m_tp')
        full_seg = cb.Segmentation(self.tem_segs.prod_full)

        # Read the time splits factor
        time_splits_dvec = cb.DVector.load(self.time_splits_path)

        # Multiply together #
        return (pure_nhb_demand * time_splits_dvec).aggregate(full_seg)


if __name__ == "__main__":
    return_seg = cb.SegmentationInput(
        enum_segments=["p", "m", "gender_3", "soc", "ns_sec", "tp"],
        naming_order=["p", "m", "gender_3", "soc", "ns_sec", "tp"],
        subsets={"p": [1, 2, 3, 4, 5, 6, 7, 8]},
    )

    normits = cb.ZoningSystem.get_zoning("normits")

    hb_prod = HBProductionModel(
        population_paths={2023: pathlib.Path(r"E:\tem\outputs\pop_2021.dvec")},
        export_home=pathlib.Path(r"E:\tem\outputs"),
        mode_time_splits_path=pathlib.Path(
            r"E:\NTS\outputs_is\productions\hb\mode_time_splits\hb_mode_time_split_production_hb_fr.dvec"
        ),
        trip_rates_path=pathlib.Path(
            r"E:\NTS\outputs\productions\hb\trip_rates\hb_trip_rates_production_dvector.dvec"
        ),
        return_segmentation=cb.Segmentation(return_seg),
        model_zoning=normits,
    )
    hb_prod.run(True, True, True)

    print("debugging")
