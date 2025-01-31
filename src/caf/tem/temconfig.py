import os
from .mdlfunction import mkdir
from pathlib import Path

# Update to your machine specific R installation directory
os.environ["R_HOME"] = r"C:\Users\uktjp008\AppData\Local\Programs\R\R-4.3.3"


class Config:
    """
    Builds paths and arguments based on a given out folder. # make this one specific to TEM?
    """

    def __init__(self, nts_fldr: Path):
        # specs
        self.nts_dtype = int
        self.def_years = [yr for yr in range(2002, 9999)]
        self.tfn_atype = "tfn"  # ntem (8), ruc2011 (5), or tfn (20)
        self.def_ttype = "tfn"  # ntem (88) or tfn (712)
        self.tfn_ttype = (
            ["gender", "aws", "hh_type"]
            if self.def_ttype == "ntem"
            else ["gender", "aws", "hh_type", "soc", "ns"]
        )
        # mode: 1-walk, 2-cycle, 3-car, 4-lgv, 5-bus, 6-national rail, 7-light rail
        self.min_trip = 1000
        self.tfn_modes = [1, 2, 3, 4, 5, 6, 7]
        self.m2k_fact = 1.6093
        self.csv_cbuild = "cb_tfn"
        self.out_fldr = nts_fldr

        # main directory
        self.dir_import = self.out_fldr / "imports"
        self.dir_cbuild = self.out_fldr / "classified builds"
        self.dir_output = self.out_fldr / "outputs"

        # sub-folders
        self.fld_dbase = "database"
        self.fld_report = "reports"
        self.fld_lookup = "lookups"
        self.fld_prod = "productions"
        self.fld_attr = "attractions"
        self.fld_tour = "tour"
        self.fld_tlds = "tld"
        self.fld_hbase = "hb"
        self.fld_rates = "trip_rates"
        self.fld_split = "mode_time_splits"
        self.fld_phis = "phi_factors"
        self.fld_nhbase = "nhb"
        self.fld_occs = "occs"
        self.fld_graph = "graphs"
        self.fld_stage = "stage"
        self.fld_other = "others"
        self.fld_input = "inputs"
        self.fld_tripend = "tripend"

        # create directory
        self._setup_directory()

    def _setup_directory(self):
        # classified build
        mkdir(self.dir_cbuild / self.fld_report)
        # lookups
        mkdir(self.dir_cbuild / self.fld_lookup)
        # production
        mkdir(self.dir_output / self.fld_prod / self.fld_dbase)
        mkdir(self.dir_output / self.fld_prod / self.fld_hbase / self.fld_phis)
        mkdir(self.dir_output / self.fld_prod / self.fld_hbase / self.fld_rates)
        mkdir(self.dir_output / self.fld_prod / self.fld_hbase / self.fld_split)
        mkdir(self.dir_output / self.fld_prod / self.fld_nhbase)
        # attraction
        mkdir(self.dir_output / self.fld_attr)
        # tour model
        mkdir(self.dir_output / self.fld_tour / self.fld_report)
        # occupancy
        mkdir(self.dir_output / self.fld_occs)
        # tlds
        mkdir(self.dir_output / self.fld_tlds)
        # stage
        mkdir(self.dir_output / self.fld_stage)
        # others
        mkdir(self.dir_output / self.fld_other)
