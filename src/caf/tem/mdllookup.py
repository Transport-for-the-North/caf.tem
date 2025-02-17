from typing import Dict, List
from . import mdlfunction as fun
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Union
from caf.toolkit import BaseConfig


class Lookup(BaseConfig):
    mmd_11id: dict[str, dict[int, str]]
    tpp_01id: dict[str, dict[int, str]]
    wkd_01id: dict[str, dict[int, str]]
    ttp_01id: dict[str, dict[int, str]]
    age_01id: dict[str, dict[int, str]]
    sex_01id: dict[str, dict[int, str]]
    eco_01id: dict[str, dict[int, str]]
    soc_02id: dict[str, dict[int, str]]
    sec_03id: dict[str, dict[int, str]]
    wfh_01id: dict[float, dict[int, str]]
    i02_01id: dict[int, dict[int, str]]
    i02_02id: dict[str, dict[int, Union[str, int]]]
    hrp_01id: dict[int, dict[int, str]]
    s92_02id: dict[str, dict[int, str]]
    s07_02id: dict[str, dict[int, str]]
    set_01id: dict[str, dict[str, str]]
    at2_01id: dict[int, dict[int, str]]
    esc_trip: dict[str, dict[int, str]]
    vp1_01id: dict[int, dict[int, str]]
    vp2_01id: dict[int, dict[int, str]]
    tld_aggr: dict[int, dict[int, dict[str, Union[List[int], int]]]]
    gor_02id: dict[int, str]
    col_type: type = int

    @property
    def nts_dtype(self):
        return self.col_type

    @property
    def inc_purp(self):
        return [
            val
            for key in self.tpp_01id
            for val in self.tpp_01id[key]
            if key not in ["hom", "esc"]
        ]

    @property
    def age_01id_edu(self):
        return self.dct_to_specs(
            {
                "child": self.age_01id["child"],
                "higher": self.age_01id["higher"],
                "adult": {**self.age_01id["adult"], **self.age_01id["elder"]},
            },
            self.col_type,
        )

    @property
    def age_01id_pop(self):
        return self.dct_to_specs(
            {
                "child": self.age_01id["child"],
                "adult": {**self.age_01id["higher"], **self.age_01id["adult"]},
                "elder": self.age_01id["elder"],
            },
            self.col_type,
        )

    @property
    def gender(self) -> Dict:
        # gender
        age_01id, sex_01id = self.age_01id_pop, self.dct_to_specs(self.sex_01id)
        out_dict = {
            "col": ["sex_b01id", "age_b01id"],
            "typ": [self.nts_dtype, self.nts_dtype],
            "log": "gender",
            "val": {
                1: fun.product(
                    sex_01id["male"] + sex_01id["female"], age_01id["child"]
                ),  # child
                2: fun.product(
                    sex_01id["male"], age_01id["adult"] + age_01id["elder"]
                ),  # male
                3: fun.product(
                    sex_01id["female"], age_01id["adult"] + age_01id["elder"]
                ),  # female
            },
            "out": {1: "Child", 2: "Male", 3: "Female"},  # for output
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    @property
    def edu_level(self) -> Dict:
        out_dict = {
            "col": "age_b01id",
            "typ": self.nts_dtype,
            "log": " age (education)",
            "val": {
                1: self.age_01id_edu["child"],  # child
                2: self.age_01id_edu["higher"],  # higher education
                3: self.age_01id_edu["adult"],  # adult
            },
            "out": {1: "Child", 2: "Higher", 3: "Adult"},  # for output
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    @property
    def hh_type(self) -> Dict:
        # household type
        out_dict = {
            "col": ["hholdnumadults", "numcarvan"],
            "typ": [int, int],
            "log": "hh_type",
            "val": {
                1: [(1, 0)],  # 1 adult with 0 car
                2: fun.product([1], range(1, 10)),  # 1 adult with 1+ cars
                3: [(2, 0)],  # 2 adults with 0 car
                4: [(2, 1)],  # 2 adults with 1 car
                5: fun.product([2], range(2, 10)),  # 2 adults with 2+ cars
                6: fun.product(range(3, 11), [0]),  # 3+ adults with 0 car
                7: fun.product(range(3, 11), [1]),  # 3+ adults with 1 car
                8: fun.product(range(3, 11), range(2, 10)),  # 3+ adults with 2+ cars
            },
            "out": {
                1: "1 adult with 0 car",
                2: "1 adult with 1+ cars",
                3: "2 adults with 0 car",
                4: "2 adults with 1 car",
                5: "2 adults with 2+ cars",
                6: "3+ adults with 0 car",
                7: "3+ adults with 1 car",
                8: "3+ adults with 2+ cars",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    @property
    def hh_child(self) -> Dict:
        # number of children in a household
        out_dict = {
            "col": "hholdnumchildren",
            "typ": int,
            "log": "hh_children",
            "val": {0: [0], 1: list(range(1, 20))},
            "out": {0: "no children", 1: "with children"},
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    @property
    def aws(self) -> Dict:
        # age, work, status
        eco_01id, age_01id = self.dct_to_specs(self.eco_01id), self.age_01id_pop
        eco_over = eco_01id["fte"] + eco_01id["pte"] + eco_01id["unm"] + eco_01id["dna"]
        out_dict = {
            "col": ["age_b01id", "ecostat_b01id"],
            "typ": [self.nts_dtype, self.nts_dtype],
            "log": "aws",
            "val": {
                1: fun.product(age_01id["child"], eco_01id["dna"]),  # child
                2: fun.product(age_01id["adult"], eco_01id["fte"]),  # fte
                3: fun.product(age_01id["adult"], eco_01id["pte"]),  # pte
                4: fun.product(
                    age_01id["adult"] + age_01id["elder"], eco_01id["stu"]
                ),  # student
                5: fun.product(age_01id["adult"], eco_01id["unm"] + eco_01id["dna"]),  # neet
                6: fun.product(age_01id["elder"], eco_over),  # over 75
            },
            "out": {
                1: "Child",
                2: "FTE",
                3: "PTE",
                4: "Student",
                5: "NEET",
                6: "Over 75",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def soc(self, soc_year: int = 2020) -> Dict:
        # soc
        soc_02id, age_01id, eco_01id = (
            self.dct_to_specs(self.soc_02id),
            self.age_01id_pop,
            self.dct_to_specs(self.eco_01id),
        )
        all_xsoc = soc_02id["hig"] + soc_02id["med"] + soc_02id["low"] + soc_02id["dna"]
        all_ages = age_01id["child"] + age_01id["adult"] + age_01id["elder"]
        emp_ecos = eco_01id["fte"] + eco_01id["pte"]
        all_ecos = emp_ecos + eco_01id["stu"] + eco_01id["unm"] + eco_01id["dna"]
        out_dict = {
            "col": [f"xsoc{soc_year}_b02id", "age_b01id", "ecostat_b01id"],
            "typ": [self.nts_dtype, self.nts_dtype, self.nts_dtype],
            "log": "soc",
            "val": {
                1: fun.product(soc_02id["hig"], age_01id["adult"], emp_ecos),  # high skill
                2: fun.product(soc_02id["med"], age_01id["adult"], emp_ecos),  # med skill
                3: fun.product(soc_02id["low"], age_01id["adult"], emp_ecos),  # low skill
                4: (
                    fun.product(all_xsoc, all_ages, eco_01id["stu"])  # FT students
                    + fun.product(
                        all_xsoc, age_01id["adult"], eco_01id["unm"] + eco_01id["dna"]
                    )
                    + fun.product(all_xsoc, age_01id["child"], all_ecos)  # children
                    + fun.product(all_xsoc, age_01id["elder"], all_ecos)  # over 75
                ),
            },
            "out": {
                1: "High skilled",
                2: "Medium skilled",
                3: "Low skilled",
                4: "Other",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    @property
    def ns_sec(self) -> Dict:
        # ns-sec
        sec_03id = self.dct_to_specs(self.sec_03id)
        out_dict = {
            "col": "nssec_b03id",
            "typ": self.nts_dtype,
            "log": "ns-sec",
            "val": {
                1: sec_03id["ns1"],  # manager & professional
                2: sec_03id["ns2"],  # intermediate
                3: sec_03id["ns3"],  # manual & routine
                4: sec_03id["ns4"],  # unemployed
                5: sec_03id["ns5"] + sec_03id["dna"],  # not classified + students
            },
            "out": {
                1: "Manager & professional",
                2: "Intermediate & small employers",
                3: "Routine & manual",
                4: "Unemployed",
                5: "Not classified (inc. students)",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    @property
    def hrp(self) -> Dict:
        # hrp
        out_dict = {
            "col": "hrprelation_b01id",
            "typ": self.nts_dtype,
            "log": "hrp",
            "val": {1: self.dct_to_specs(self.hrp_01id)[1]},
            "out": {1: "household reference person", 0: "other"},
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def income(self, col_name: str, lev_name: str = "01") -> Dict:
        # household or individual income: {ind/hh}income2002_b{01/02}id
        col_name = f"{col_name}income2002_b01id"
        out_dict = {
            "col": col_name,
            "typ": self.nts_dtype,
            "log": f"income {lev_name}",
            "val": self.dct_to_specs(eval(f"self.i02_{lev_name}id")),
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def wfh(self, col_name: str) -> Dict:
        # number of day wfh
        out_dict = {
            "col": col_name,
            "typ": int,
            "log": "work from home",
            "val": self.dct_to_specs(self.wfh_01id),
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def sic(self, sic_year: str = "2007") -> Dict:
        out_dict = {
            "col": f"sic{sic_year}_b02id",
            "typ": self.nts_dtype,
            "log": f"sic{sic_year}",
            "val": self.dct_to_specs(eval(f"self.s{sic_year[2:]}_02id")),
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def tt_tfn(self, col_list: List, out_type: str = "tfn") -> Dict:
        # tfn traveller type
        def _dct_value(idx: int) -> List:
            try:
                key = col_list[idx]
                return list(set(par_dict[key]["val"].values()))
            except IndexError:
                return [None, None, None, None]

        def _dct_update(*args) -> Dict:
            args = (fun.val_to_list(col) for col in args)
            args = (col for col in args if all(itm is not None for itm in col))
            if len(par_dict) == 0:
                return {idx: val for idx, val in enumerate(fun.product(*args), 1)}
            else:
                idx_init = len(par_dict) + 1
                par_dict.update(
                    {idx: val for idx, val in enumerate(fun.product(*args), idx_init)}
                )
                return par_dict

        # tt = [gender, aws, hh_type, soc, ns]
        par_dict: Dict = {
            "gender": self.gender,
            "aws": self.aws,
            "hh_type": self.hh_type,
            "soc": self.soc(),
            "ns": self.ns_sec,
        }
        gen, aws, hh = _dct_value(0), _dct_value(1), _dct_value(2)
        soc, sec = _dct_value(3), _dct_value(4)

        # child: gender=1, aws=1, hh=1-8, soc=4, ns=1-5
        par_dict = {}
        par_dict = _dct_update(gen[0], aws[0], hh, soc[-1], sec)
        if out_type == "tfn":
            # gender = 2-3
            for g in gen[1:]:
                # fte/pte: aws=2-3, (hh=1-2, soc=1-3, ns=1-3,5) & (hh=3-8, soc=1-3, ns=1-5)
                for w in [2, 3]:
                    par_dict = _dct_update(
                        g, w, hh[:2], [1, 2], [1, 2, 3, 5]
                    )  # no unem for soc1-2
                    par_dict = _dct_update(
                        g, w, hh[:2], 3, [2, 3, 5]
                    )  # no unem & ns-sec 1 for soc 3
                    par_dict = _dct_update(g, w, hh[2:], [1, 2, 3], sec)
                # student: aws=4, (hh=1-2, soc=4, ns=5) & (hh=3-8, soc=4, ns=1-5)
                par_dict = _dct_update(g, 4, hh[:2], 4, 5)
                par_dict = _dct_update(g, 4, hh[2:], 4, sec)
                # unemployed: aws=5, (hh=1-8, soc=4, ns=1-5)
                par_dict = _dct_update(g, 5, hh, 4, sec)
                # over 75 aws=6, hh=1-8, soc=4, ns=1-5
                par_dict = _dct_update(g, 6, hh, 4, sec)
        else:
            # fte/pte: gender=2-3, aws=2-6, hh=1-8
            par_dict = _dct_update(gen[1:], aws[1:], hh)

        return fun.itm_to_key(par_dict)

    def tt_to_dfr(self, tfn_type: List, out_type: str = "tfn") -> pd.DataFrame:
        dfr = self.tt_tfn(tfn_type, out_type)
        dfr = pd.DataFrame.from_dict({val: key for key, val in dfr.items()}, orient="index")
        dfr.rename(columns={key: val for key, val in enumerate(tfn_type)}, inplace=True)
        dfr = dfr.reset_index(drop=False).rename(columns={"index": "tt"})
        return dfr

    def at_ntem(self, col_name: str) -> Dict:
        # ntem area type
        out_dict = {
            "col": f"{col_name}areatype_b01id",
            "typ": self.nts_dtype,
            "log": "ntem_at",
            "val": self.dct_to_specs(self.at2_01id),
            "out": {
                1: "Inner London",
                2: "Outer London",
                3: "Metropolitan",
                4: "Urban big",
                5: "Urban large",
                6: "Urban medium",
                7: "Urban small",
                8: "Rural",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def at_tfn(self, col_type: str) -> Dict:
        # col_type: hhold, triporig, tripdest
        # 1: 'north east', 2: 'north-west', 3: 'yorkshire and the humber', 4: 'east midlands',
        # 5: 'west midlands', 6: 'east of england', 7: 'london', 8: 'south-east', 9: 'south west',
        # 10: 'wales', 11: 'scotland', -8: 'na', -9: 'dna'
        set_01id, at2_01id = self.dct_to_specs(self.set_01id), self.dct_to_specs(self.at2_01id)
        cty_list = [-8, -9, -10, 0] + list(range(10, 99))
        gor_rest = [1, 2, 3, 4, 5, 9, 10, 11, -8, -9, -10, 0]

        set_list = [val for key in set_01id for val in set_01id[key]]
        at2_list = [val for key in at2_01id for val in at2_01id[key]]
        at2_xlon = [
            val for val in at2_list if val not in at2_01id[1]
        ]  # outer london + rest GB
        out_dict = {
            "col": [
                f"{col_type}gor_b02id",
                f"{col_type}county_b01id",
                f"{col_type}areatype_b01id",
                f"{col_type}ruc2011_b01id",
            ],
            "typ": [self.nts_dtype, self.nts_dtype, self.nts_dtype, str],
            "log": f"tfn_at ({col_type})",
            "val": {
                1: fun.product([7], cty_list, at2_01id[1], set_list),  # inner london
                2: fun.product([7], cty_list, at2_xlon, set_list),  # outer london
                # major
                3: fun.product([6, 8], cty_list, at2_list, set_01id["major"]),  # east + se
                4: fun.product([5], cty_list, at2_list, set_01id["major"]),  # wm
                5: fun.product([2, 4], cty_list, at2_list, set_01id["major"]),  # nw + em
                6: fun.product([1], cty_list, at2_list, set_01id["major"]),  # ne
                7: fun.product([3], cty_list, at2_list, set_01id["major"]),  # yh
                # minor
                8: fun.product([4, 3], cty_list, at2_list, set_01id["minor"]),  # em + yh
                # city
                9: fun.product([6], cty_list, at2_list, set_01id["city"]),  # east
                10: fun.product([8], cty_list, at2_list, set_01id["city"]),  # se
                11: (
                    fun.product([9], cty_list, at2_list, set_01id["city"])
                    + fun.product([10], [62, 64, 66, 67], at2_list, set_01id["city"])
                ),  # south wales
                12: (
                    fun.product([5], cty_list, at2_list, set_01id["city"])
                    + fun.product([10], [61, 65], at2_list, set_01id["city"])  # wm
                ),  # mid-wales
                13: fun.product([4], cty_list, at2_list, set_01id["city"]),  # em
                14: (
                    fun.product([2], cty_list, at2_list, set_01id["city"])
                    + fun.product([10], [60, 63, -8], at2_list, set_01id["city"])  # nw
                ),  # north wales
                15: fun.product([1, 3], cty_list, at2_list, set_01id["city"]),  # ne + yh
                # town
                16: fun.product([6, 8], cty_list, at2_list, set_01id["town"]),
                17: fun.product(gor_rest, cty_list, at2_list, set_01id["town"]),
                # village
                18: fun.product([6, 8], cty_list, at2_list, set_01id["village"]),
                19: fun.product(gor_rest, cty_list, at2_list, set_01id["village"]),
                # scotland urban
                20: fun.product(
                    [11], cty_list, at2_list, set_01id["minor"] + set_01id["city"]
                ),
            },
            "out": {
                1: "Inner London",
                2: "Outer London",
                3: "Major (EoE + SE)",
                4: "Major (WM)",
                5: "Major (NW + EM)",
                6: "Major (NE)",
                7: "Major (YH)",
                8: "Minor (EM + YH)",
                9: "City (EoE)",
                10: "City (SE)",
                11: "City (SW + S.Wales)",
                12: "City (WM + M.Wales)",
                13: "City (EM)",
                14: "City (NW + N.Wales)",
                15: "City (NE + YH)",
                16: "Town (EoE + SE)",
                17: "Town (rest of GB)",
                18: "Village (EoE + SE)",
                19: "Village (rest of GB)",
                20: "Scotland (Urban)",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def settlement(self, col_type: str = "hhold") -> Dict:
        # ruc 2011 to area type
        set_01id = self.dct_to_specs(self.set_01id)
        out_dict = {
            "col": f"{col_type}ruc2011_b01id",
            "typ": str,
            "log": f"{col_type}ruc_2011",
            "val": {
                1: set_01id["major"],
                2: set_01id["minor"],
                3: set_01id["city"],
                4: set_01id["town"],
                5: set_01id["village"],
            },
            "out": {
                1: "Major",
                2: "Minor",
                3: "City",
                4: "Town",
                5: "Village",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def occupant(self, col_mode: str = "main") -> Dict:
        # occupant
        mmd_11id = self.dct_to_specs(self.mmd_11id)
        if "bus_d" not in mmd_11id:
            mmd_11id["bus_d"] = []
        out_dict = {
            "col": [f"{col_mode}mode_b11id"],
            "typ": [self.nts_dtype],
            "log": f"occupancy ({col_mode})",
            "val": {
                "driver": (
                    mmd_11id["swak"]
                    + mmd_11id["walk"]
                    + mmd_11id["bike"]
                    + mmd_11id["car_d"]
                    + mmd_11id["van_d"]
                    + mmd_11id["bus_d"]
                ),
                "passenger": (
                    mmd_11id["car_p"]
                    + mmd_11id["van_p"]
                    + mmd_11id["bus_p"]
                    + mmd_11id["rail_s"]
                    + mmd_11id["rail_l"]
                    + mmd_11id["air"]
                ),
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def mode(self, col_mode: str = "main") -> Dict:
        # main mode
        mmd_11id = self.dct_to_specs(self.mmd_11id)
        if "bus_d" not in mmd_11id:
            mmd_11id["bus_d"] = []
        out_dict = {
            "col": [f"{col_mode}mode_b11id"],
            "typ": [self.nts_dtype],
            "log": f"{col_mode} mode",
            "val": {
                1: mmd_11id["swak"] + mmd_11id["walk"],  # walk
                2: mmd_11id["bike"],  # cycle
                3: mmd_11id["car_d"] + mmd_11id["car_p"],
                4: mmd_11id["van_d"] + mmd_11id["van_p"],  #
                5: mmd_11id["bus_d"] + mmd_11id["bus_p"],  # bus
                6: mmd_11id["rail_s"],  # surface rail
                7: mmd_11id["rail_l"],  # light rail/underground
                8: mmd_11id["air"],  # air
            },
            "out": {
                1: "Walk",
                2: "Cycle",
                3: "Car",
                4: "Van",
                5: "Bus",
                6: "Surface rail",
                7: "Light rail",
                8: "Air",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def purpose(self) -> Dict:
        # trip purpose
        tpp_01id, mmd_11id = self.dct_to_specs(self.tpp_01id), self.dct_to_specs(self.mmd_11id)
        end_home = tpp_01id["hom"]
        try:
            tpp_from = self.inc_purp + tpp_01id["esc"] + end_home
        except KeyError:
            tpp_from = self.inc_purp + end_home
        all_mode = [val for key in mmd_11id for val in mmd_11id[key] if key != "na"]
        wak_long = [
            val
            for key in mmd_11id
            for val in mmd_11id[key]
            if key not in ["na", "swak"]  # , "walk"]
        ]  # exclude walk less than 1 mile
        out_dict = {
            "col": ["mainmode_b11id", "trippurpfrom_b01id", "trippurpto_b01id"],
            "typ": [self.nts_dtype, self.nts_dtype, self.nts_dtype],
            "log": "purpose",
            "val": {
                1: (
                    fun.product(all_mode, tpp_from, tpp_01id["com"])  # hb_fr + nhb
                    + fun.product(all_mode, tpp_01id["com"], end_home)  # hb_to
                ),
                2: (
                    fun.product(all_mode, tpp_from, tpp_01id["emb"])
                    + fun.product(all_mode, tpp_01id["emb"], end_home)
                ),
                3: (
                    fun.product(all_mode, tpp_from, tpp_01id["edu"])
                    + fun.product(all_mode, tpp_01id["edu"], end_home)
                ),
                4: (
                    fun.product(all_mode, tpp_from, tpp_01id["shp"])
                    + fun.product(all_mode, tpp_01id["shp"], end_home)
                ),
                5: (
                    fun.product(all_mode, tpp_from, tpp_01id["peb"])
                    + fun.product(all_mode, tpp_01id["peb"], end_home)
                ),
                6: (
                    fun.product(all_mode, tpp_from, tpp_01id["soc"])
                    + fun.product(all_mode, tpp_01id["soc"], end_home)
                ),
                7: (
                    fun.product(all_mode, tpp_from, tpp_01id["vis"])
                    + fun.product(all_mode, tpp_01id["vis"], end_home)
                ),
                8: (
                    fun.product(all_mode, tpp_from, tpp_01id["hol"])
                    + fun.product(all_mode, tpp_01id["hol"], end_home)
                    + fun.product(wak_long, tpp_from, tpp_01id["jwk"])
                    + fun.product(wak_long, tpp_01id["jwk"], end_home)
                ),
            },
            "out": {
                1: "Commuting",
                2: "Employer business",
                3: "Education",
                4: "Shopping",
                5: "Personal business",
                6: "Social",
                7: "Visit friends",
                8: "Holiday",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def escort(self) -> Dict:
        # trip purpose
        tpp_01id, esc_trip = self.dct_to_specs(self.tpp_01id), self.dct_to_specs(self.esc_trip)
        end_home = tpp_01id["hom"]
        try:
            tpp_from = self.inc_purp + tpp_01id["esc"] + end_home
        except KeyError:
            tpp_from = self.inc_purp + end_home

        out_dict = {
            "col": ["trippurpfrom_b01id", "trippurpto_b01id"],
            "typ": [self.nts_dtype, self.nts_dtype],
            "log": "escort trip",
            "val": {
                "esc": (
                    fun.product(tpp_from, esc_trip["esc"])
                    + fun.product(esc_trip["esc"], end_home)
                ),  # from home + return home
                "main": [],
            },
            "out": {
                "esc": "Escort",
                "main": "Main purpose",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def period(self, tse_type: str = "start") -> Dict:
        # trip start/end time
        wkd_01id, ttp_01id = (
            self.dct_to_specs(self.wkd_01id),
            self.dct_to_specs(self.ttp_01id),
        )
        all_24hr = (
            ttp_01id["am"] + ttp_01id["ip"] + ttp_01id["pm"] + ttp_01id["op"] + ttp_01id["na"]
        )
        out_dict = {
            "col": ["travelweekday_b01id", f"trip{tse_type}_b01id"],
            "typ": [self.nts_dtype, self.nts_dtype],
            "log": f"{tse_type} time",
            "val": {
                1: fun.product(wkd_01id["wkd"], ttp_01id["am"]),
                2: fun.product(wkd_01id["wkd"], ttp_01id["ip"]),
                3: fun.product(wkd_01id["wkd"], ttp_01id["pm"]),
                4: fun.product(wkd_01id["wkd"], ttp_01id["op"]),
                5: fun.product(wkd_01id["sat"], all_24hr),
                6: fun.product(wkd_01id["sun"], all_24hr),
            },
            "out": {
                1: "AM peak",
                2: "Inter-peak",
                3: "PM peak",
                4: "Off-peak",
                5: "Saturday",
                6: "Sunday",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def direction(self) -> Dict:
        # direction of travel, hb_fr, hb_to, nhb
        tpp_01id = self.dct_to_specs(self.tpp_01id)
        try:
            nhb_purp = self.inc_purp + tpp_01id["esc"]
        except KeyError:
            nhb_purp = self.inc_purp
        out_dict = {
            "col": ["trippurpfrom_b01id", "trippurpto_b01id"],
            "typ": [self.nts_dtype, self.nts_dtype],
            "log": "direction",
            "val": {
                "hb_fr": fun.product(tpp_01id["hom"], nhb_purp),
                "hb_to": fun.product(nhb_purp, tpp_01id["hom"]),
                "nhb": fun.product(nhb_purp, nhb_purp),
            },
            "out": {
                "hb_fr": "From Home",
                "hb_to": "Return Home",
                "nhb": "Non Home-Based",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    def fuel_type(self, col_name: str) -> Dict:
        # vehicle fuel type: vehproptype_b01id, vehproptypen_b01id
        vpx_01id = self.dct_to_specs(
            self.vp1_01id if col_name == "vehproptype_b01id" else self.vp2_01id
        )
        out_dict = {
            "col": col_name,
            "typ": self.nts_dtype,
            "log": "fuel type",
            "val": vpx_01id,
            "out": {
                1: "Petrol",
                2: "Diesel",
                3: "Electric",
                4: "Hybrid",
                5: "P-hybrid",
                6: "LPG",
                7: "Bi-fuel",
                8: "Other",
                0: "Passenger",
            },
        }
        out_dict["val"] = fun.itm_to_key(out_dict["val"])
        return out_dict

    @staticmethod
    def sic_to_ecode():
        out_dict = {
            1: {"E01": "All", "exc": ["HH", "0-15", "16+"]},  # commuting
            2: {"E01": "All", "exc": ["HH", "0-15", "16+"]},  # e.business
            3: {"E03/04/05": "S85"},  # 'Child': '0-15', 'Adult': '16+'},  # education
            4: {"E07": ["S46", "S47"]},  # shopping: retail
            # p.business: E08 (86/87) - health, E09 (64-69/75-81/95-96) - services, E11 (56) - food
            # 5: {'E08/09/11': ['S86', 'S87', 'S64', 'S65', 'S66', 'S68', 'S69', 'S75',
            #                   'S77', 'S79', 'S80', 'S81', 'S95', 'S96', 'S56']},
            5: {
                "E08": ["S86"],  # health
                "E09": [
                    "S64",
                    "S65",
                    "S66",
                    "S68",
                    "S69",
                    "S75",
                    "S77",
                    "S79",
                    "S80",
                    "S95",
                    "S96",
                ],
                "E11": ["S56"],
            },
            6: {"E12": ["S90", "S91", "S92", "S93", "S94"]},  # social
            7: {"E02": "HH"},  # visit friends
            # holiday: E06 (55) - accommodation, E13 (S2-3) - fishing
            8: {"E06/13": ["S55", "S02", "S03"]},
        }
        return out_dict

    @staticmethod
    def dct_to_specs(dct: Dict, out: type = int) -> Dict:
        # create lookup specs
        return {key: list(dct[key].keys() if out is int else dct[key].values()) for key in dct}

    @staticmethod
    def lev_to_name(level: Union[List, str] = None) -> Dict:
        # get column names from level: tfn_at, ua, county, gor, ruc2011, areatype -> dict {h/o/d: []}
        if level is not None:
            level = [level] if isinstance(level, str) else level
            out_dict = {key: [] for key in ["h", "o", "d"]}
            for col in level:
                if col.lower() in ["ua", "county", "gor", "ruc2011", "areatype"]:
                    home = f"hhold{col}_b02id" if col.lower() == "gor" else f"hhold{col}_b01id"
                    orig = (
                        f"triporig{col}_b02id"
                        if col.lower() == "gor"
                        else f"triporig{col}_b01id"
                    )
                    dest = (
                        f"tripdest{col}_b02id"
                        if col.lower() == "gor"
                        else f"tripdest{col}_b01id"
                    )
                else:
                    home, orig, dest = col, f"{col}_o", f"{col}_d"
                out_dict["h"].append(home)
                out_dict["o"].append(orig)
                out_dict["d"].append(dest)
        else:
            out_dict = {key: [] for key in ["h", "o", "d"]}
        return out_dict

    @staticmethod
    def nhb_renumber(dfr: pd.DataFrame, col_type: type = int) -> np.ndarray:
        # TODO: to be updated once finalised
        # return np.where(dfr['direction'] == 'xxx', (10 if col_type is int else 'n') + dfr['purpose'],
        #                 dfr['purpose'])
        return dfr["purpose"] if col_type is int else dfr["purpose"]

    @staticmethod
    def week_to_hour() -> Dict:
        # weekly to time period and hourly demand {ts: [week to day, period to hour]}
        dct = {
            1: [5, 3],  # weekday AM
            2: [5, 6],  # weekday IP
            3: [5, 3],  # weekday PM
            4: [5, 12],  # weekday OP
            5: [1, 24],  # saturday
            6: [1, 24],  # sunday
        }
        return dct

    @staticmethod
    def hh_to_ca() -> Dict:
        # household type to car availability
        dct = {
            "col": "hh_type",
            "val": {
                1: [1, 3, 6],  # nca with 1/2/3+ adults
                2: [2, 4, 5, 7, 8],
            },  # ca with 1/2/3+ adults
            "out": {1: "nca", 2: "ca"},
        }
        dct["val"] = fun.itm_to_key(dct["val"])
        return dct

    @staticmethod
    def purpose_tag() -> Dict:
        # aggregate purposes to TAG
        dct = {"Business": [1], "Commuting": [2], "Other": [3, 4, 5, 6, 7, 8]}
        return fun.itm_to_key(dct, False)

    @staticmethod
    def purpose_to_luti() -> Dict:
        # aggregate purposes to LUTI
        dct = {
            "val": {1: [2], 2: [1], 3: [3, 4, 5, 6, 7, 8]},  # business  # commuting  # other
            "out": {1: "Business", 2: "Commuting", 3: "Other"},
        }
        dct["val"] = fun.itm_to_key(dct["val"], False)
        return dct

    @staticmethod
    def purpose_to_normits() -> Dict:
        # aggregate purposes to normits
        dct = {
            "val": {1: [2], 2: [1], 3: [3, 4, 5, 6, 7, 8]},  # business  # commuting  # other
            "out": {1: "Business", 2: "Commuting", 3: "Other"},
        }
        dct["val"] = fun.itm_to_key(dct["val"], False)
        return dct

    @staticmethod
    def purpose_to_noham() -> Dict:
        # aggregate purposes to NoHAM
        dct = {
            "val": {1: [2], 2: [1], 3: [3, 4, 5, 6, 7, 8]},  # business  # commuting  # other
            "out": {1: "Business", 2: "Commuting", 3: "Other"},
        }
        dct["val"] = fun.itm_to_key(dct["val"], False)
        return dct

    @staticmethod
    def purpose_to_norms() -> Dict:
        # aggregate purposes to NoRMS
        dct = {
            "val": {1: [2], 2: [1], 3: [3, 4, 5, 6, 7, 8]},  # business  # commuting  # other
            "out": {1: "Business", 2: "Commuting", 3: "Other"},
        }
        dct["val"] = fun.itm_to_key(dct["val"], False)
        return dct


if __name__ == "__main__":
    # Lookup file created below, but easier to edit the file directly if any
    # changes are needed.
    luk = Lookup(
        mmd_11id={
            "swak": {1: "walk, less than 1 mile"},
            "walk": {2: "walk, 1 mile or more"},
            "bike": {
                3: "pedal bicycle",
                26: "eBike",
                27: "eScooter",
                28: "Mobility scooter",
            },
            "car_d": {
                5: "private car: driver",
                7: "motorcycle / scooter / moped: driver",
                11: "other private transport",
            },
            "car_p": {
                6: "private car: passenger",
                8: "motorcycle / scooter / moped: passenger",
                20: "taxi",
                21: "minicab",
            },
            "van_d": {9: "van / lorry: driver"},
            "van_p": {10: "van / lorry: passenger"},
            "bus_d": {},
            "bus_p": {
                4: "private (hire) bus",
                12: "london stage bus",
                13: "other stage bus",
                14: "coach / express bus",
                15: "excursion / tour bus",
                22: "other public transport",
            },
            "rail_l": {16: "london underground", 18: "light rail"},
            "rail_s": {17: "surface rail"},
            "air": {19: "air"},
            "ferry": {29: "ferry"},
            "nas": {23: "na (public)", 24: "na (private)", 25: "na", -8: "na", 0: "0"},
        },
        # trip purpose: trippurp{from/to}_b01id
        tpp_01id={
            "com": {1: "work", 18: "escort work"},
            "emb": {2: "in course of work", 19: "escort in course of work"},
            "edu": {3: "education", 20: "escort education"},
            "shp": {
                4: "food shopping",
                5: "non food shopping",
                21: "escort shopping / personal business",
            },
            "peb": {
                6: "personal business medical",
                7: "personal business eat / drink",
                8: "personal business other",
                16: "other non-escort",
            },
            "soc": {
                9: "eat / drink with friends",
                11: "other social",
                12: "entertain /  public activity",
                13: "sport: participate",
                22: "other escort",
            },
            "vis": {10: "visit friends", 17: "escort home"},
            "hol": {14: "holiday: base"},
            "jwk": {15: "day trip / just walk"},
            "esc": {},
            "hom": {23: "home"},
        },
        # escort trips
        esc_trip={
            "esc": {
                18: "escort work",
                19: "escort in course of work",
                20: "escort education",
                21: "escort shopping / personal business",
                16: "other non-escort",  # learning to drive, taking part in community service
                22: "other escort",  # escort social/visit friends/holiday
                17: "escort home",
            },
            "non": {},
        },
        # weekday & weekend
        wkd_01id={
            "wkd": {
                1: "monday",
                2: "tuesday",
                3: "wednesday",
                4: "thursday",
                5: "friday",
            },
            "sat": {6: "saturday"},
            "sun": {7: "sunday"},
        },
        # hours to periods
        ttp_01id={
            "am": {8: "0700 - 0759", 9: "0800 - 0859", 10: "0900 - 0959"},
            "ip": {
                11: "1000 - 1059",
                12: "1100 - 1159",
                13: "1200 - 1259",
                14: "1300 - 1359",
                15: "1400 - 1459",
                16: "1500 - 1559",
            },
            "pm": {17: "1600 - 1659", 18: "1700 - 1759", 19: "1800 - 1859"},
            "op": {
                1: "0000 - 0059",
                2: "0100 - 0159",
                3: "0200 - 0259",
                4: "0300 - 0359",
                5: "0400 - 0459",
                6: "0500 - 0559",
                7: "0600 - 0659",
                20: "1900 - 1959",
                21: "2000 - 2059",
                22: "2100 - 2159",
                23: "2200 - 2259",
                24: "2300 - 2359",
            },
            "na": {-8: "na", -10: "dead", 0: "0", "0": "0"},
        },
        # age profile
        age_01id={
            "child": {
                1: "less than 1 year",
                2: "1 - 2 years",
                3: "3 - 4 years",
                4: "5 - 10 years",
                5: "11 - 15 years",
            },
            "higher": {6: "16 years", 7: "17 years"},
            "adult": {
                8: "18 years",
                9: "19 years",
                10: "20 years",
                11: "21 - 25 years",
                12: "26 - 29 years",
                13: "30 - 39 years",
                14: "40 - 49 years",
                15: "50 - 59 years",
                16: "60 - 64 years",
                17: "65 - 69 years",
                18: "70 - 74 years",
            },
            "elder": {19: "75 - 79 years", 20: "80 - 84 years", 21: "85 years +"},
        },
        # gender
        sex_01id={"male": {1: "male"}, "female": {2: "female"}},
        # work status
        eco_01id={
            "fte": {1: "Employees: full-time", 3: "Self-employed: full-time"},
            "pte": {2: "Employees: part-time", 4: "Self-employed: part-time"},
            "stu": {7: "Economically inactive: student"},
            "unm": {
                5: "ILO unemployed",
                6: "Economically inactive: retired",
                8: "Economically inactive: looking after family / home",
                9: "Economically inactive: permanently sick / disabled",
                10: "Economically inactive: temporarily sick / injured",
                11: "Economically inactive: other",
            },
            "dna": {-8: "na", -9: "dna", -10: "dead", 0: "0"},
        },
        # standard occupational classification (individual)
        soc_02id={
            "hig": {
                1: "managers and senior officials",
                2: "professional occupations",
                3: "associate professional and technical occupations",
            },
            "med": {
                4: "administrative and secretarial occupations",
                5: "skilled trades occupations",
                6: "personal service occupations",
                7: "sales and customer service occupations",
            },
            "low": {
                8: "process, plant and machine operatives",
                9: "elementary occupations",
            },
            "dna": {-8: "na", -9: "dna"},
        },
        # national statistics - social economic classification (individual)
        sec_03id={
            "ns1": {1: "managerial and professional occupations"},
            "ns2": {2: "intermediate occupations and small employers"},
            "ns3": {3: "routine and manual occupations"},
            "ns4": {4: "never worked and long-term unemployed"},
            "ns5": {5: "not classified (including students)"},
            "dna": {-9: "dna"},
        },
        # wfh frequency
        wfh_01id={
            3.000: {1: "3 or more times a week"},  # 3
            1.500: {2: "once or twice a week"},  # 1.5
            0.750: {3: "less than once a week more than twice a month"},  # 0.75
            0.375: {4: "once or twice a month"},  # 0.375
            0.100: {5: "less than one a month more than twice a year"},  # 0.10
            0.030: {6: "once or twice a year"},  # 0.03
            0.015: {7: "less than once a year or never"},  # 0.015
            0.000: {-8: "na", -9: "dna"},
        },
        # individual/household income 2002
        i02_01id={
            500: {1: "Less than £1,000"},
            1500: {2: "£1,000 - £1,999"},
            2500: {3: "£2,000 - £2,999"},
            3500: {4: "£3,000 - £3,999"},
            4500: {5: "£4,000 - £4,999"},
            5500: {6: "£5,000 - £5,999"},
            6500: {7: "£6,000 - £6,999"},
            7500: {8: "£7,000 - £7,999"},
            8500: {9: "£8,000 - £8,999"},
            9500: {10: "£9,000 - £9,999"},
            11250: {11: "£10,000 - £12,499"},
            13750: {12: "£12,500 - £14,999"},
            16250: {13: "£15,000 - £17,499"},
            18750: {14: "£17,500 - £19,999"},
            22500: {15: "£20,000 - £24,999"},
            27500: {16: "£25,000 - £29,999"},
            32500: {17: "£30,000 - £34,999"},
            37500: {18: "£35,000 - £39,999"},
            45000: {19: "£40,000 - £49,999"},
            55000: {20: "£50,000 - £59,999"},
            65000: {21: "£60,000 - £69,999"},
            72500: {22: "£70,000 - £74,999"},
            87500: {23: "£75,000 to £99,999"},
            112500: {24: "£100,000 to £124,999"},
            137500: {25: "£125,000 to £149,999"},
            150000: {26: "£150,000 or more"},
            -1: {-8: "NA", 0: "NA"},
            0: {-9: "DNA (under 16)"},
        },
        # aggregate income
        i02_02id={
            "£0k-£25k": {key: key for key in range(1, 16)},  # Less than £25,000
            "£25k-£50k": {key: key for key in range(16, 20)},  # £25,000 to £49,999
            "£50k+": {key: key for key in range(20, 28)},  # £50,000 and over
            "nas": {-8: "na", 0: "na"},
        },
        # household reference person
        hrp_01id={
            1: {99: "Household reference person"},
            0: {
                1: "Spouse",
                2: "Cohabitee",
                3: "Son/daughter",
                4: "Step-son/daughter",
                5: "Foster child",
                6: "Son/daughter-in-law",
                7: "Parent/guardian",
                8: "Step-parent",
                9: "Foster parent",
                10: "Parent-in-law",
                11: "Brother/sister",
                12: "Step-brother/sister",
                13: "Foster brother/sister",
                14: "Brother/sister-in-law",
                15: "Grand-child",
                16: "Grand-parent",
                17: "Other relative",
                18: "Other non-relative",
                19: "Civil partner",
                -8: "NA",
                -9: "DNA",
            },
        },
        # SIC1992 codes
        s92_02id={
            "A": {1: "A - Agriculture, hunting and forestry", 2: "B - Fishing"},
            "B": {3: "C - Mining and quarrying"},
            "C": {4: "D - Manufacturing"},
            "D/E": {5: "E - Electricity, gas and water supply"},
            "F": {6: "F - Construction"},
            "G": {
                7: "G - Wholesale and retail trade; repair of motor vehicles, "
                "motorcycles and personal and household goods"
            },
            "I": {8: "H - Hotels and restaurants"},
            "H/J": {9: "I - Transport, storage and communication"},
            "K": {10: "J - Financial intermediation"},
            "L/M/N": {11: "K - Real estate, renting and business activities"},
            "O": {12: "L - Public administration and defence; compulsory social security"},
            "P": {13: "M - Education"},
            "Q": {14: "N - Health and social work"},
            "R/S": {15: "O - Other community, social and personal service activities"},
            "T/U": {
                16: "P - Private households with employed persons",
                17: "Q - Extra-territorial organisations and bodies",
            },
            "NAS": {-8: "na", 18: "Workplace outside UK (Pre 2002)"},
            "DNA": {-9: "dna"},
        },
        # SIC2007 codes
        s07_02id={
            "A": {1: "A - Agriculture, forestry and fishing"},
            "B": {2: "B - Mining and quarrying"},
            "C": {3: "C - Manufacturing"},
            "D/E": {
                4: "D - Electricity, gas, steam and air conditioning supply",
                5: "E - Water supply; sewerage, waste management and remediation activities",
            },
            "F": {6: "F - Construction"},
            "G": {
                7: "G - Wholesale and retail trade; repair of motor vehicles and motorcycles"
            },
            "H/J": {
                8: "H - Transportation and storage",
                10: "J - Information and communication",
            },
            "I": {9: "I - Accommodation and food service activities"},
            "K": {11: "K - Financial and insurance activities"},
            "L/M/N": {
                12: "L - Real estate activities",
                13: "M - Professional, scientific and technical activities",
                14: "N - Administrative and support service activities",
            },
            "O": {15: "O - Public administration and defence; compulsory social security"},
            "P": {16: "P - Education"},
            "Q": {17: "Q - Human health and social work activities"},
            "R/S": {
                18: "R - Arts, entertainment and recreation",
                19: "S - Other service activities",
            },
            "T/U": {
                20: "T - Activities of households as employers",
                21: "U - Activities of extraterritorial organisations and bodies",
            },
            "NAS": {-8: "na"},
            "DNA": {-9: "dna"},
        },
        # settlement ruc 2011
        set_01id={
            "major": {"a1": "Urban - major conurbation"},
            "minor": {
                "b1": "Urban - minor conurbation",
                "1": "Large urban area - scotland",
            },
            "city": {
                "c1": "Urban - city and town",
                "c2": "Urban - city and town in a sparse setting",
                "2": "Other urban area - scotland",
            },
            "town": {
                "d1": "Rural - town and fringe",
                "d2": "Rural - town and fringe in a sparse setting",
                "3": "Accessible small town - Scotland",
                "4": "Remote small town - Scotland",
                "5": "Very remote small town - Scotland",
            },
            "village": {
                "e1": "Rural - village",
                "e2": "rural - village in a sparse setting",
                "f1": "Rural - hamlets and isolated dwellings",
                "f2": "Rural - hamlets and isolated dwellings in a sparse setting",
                "6": "Accessible rural area - Scotland",
                "7": "Remote rural area - Scotland",
                "8": "Very remote rural area - Scotland",
            },
        },
        # ntem area type2: {hhold/triporig/tripdest}areatype2_b01id
        at2_01id={
            1: {1: "inner london"},
            2: {2: "outer london built-up areas"},
            3: {
                3: "west midlands built-up areas",
                4: "greater manchester built-up areas",
                5: "west yorkshire built-up areas",
                6: "glasgow built-up areas",
                7: "liverpool built-up areas",
                8: "tyneside built-up areas",
                9: "south yorkshire built-up areas",
            },
            4: {10: "other urban areas - over 250k population"},
            5: {11: "other urban areas - 100k to 250k population"},
            6: {
                12: "other urban areas - 50k to 100k population",
                13: "other urban areas - 25k to 50k population",
            },
            7: {
                14: "other urban areas - 10k to 25k population",
                15: "other urban areas - 3k to 10k population",
            },
            8: {16: "rural"},
            0: {-8: "na", -9: "dna", -10: "dead"},
        },
        # tld aggregate: {lev: {gor: {'ruc': [int], 'out': int}}
        tld_aggr={
            # 1: {1: {'ruc': [4, 5], 'out': 4},  # NE: village to town
            #     4: {'ruc': [1, 2], 'out': 2},  # EM: major to minor
            #     5: {'ruc': [4, 5], 'out': 5},  # WM: town to village
            #     6: {'ruc': [1, 3], 'out': 3},  # EoE: major to city
            #     7: {'ruc': [1, 2, 3, 4, 5], 'out': 1},  # London: all to major
            #     8: {'ruc': [1, 3], 'out': 3},  # SE: major to city
            #     9: {'ruc': [4, 5], 'out': 5},  # SW: town to village
            #     10: {'ruc': [4, 5], 'out': 4},  # Wales: village to town
            #     11: {'ruc': [4, 5], 'out': 4}  # Scotland: village to town
            #     },
            # 2: {6: {'ruc': [4, 5], 'out': 4},  # EoE: village to town
            #     8: {'ruc': [4, 5], 'out': 4}  # SE: village to town
            #     }
            # urban and rural only for external
            1: {
                1: {"ruc": [4, 5], "out": 4},
                7: {"ruc": [1, 2, 3, 4, 5], "out": 1},
            }  # NE: village to town
            | {key: {"ruc": [1, 2, 3], "out": 3} for key in (4, 5, 6, 8, 9, 10, 11)},
            2: {key: {"ruc": [4, 5], "out": 4} for key in (4, 5, 6, 8, 9, 10, 11)},
        },
        # gor: {hhold/triporig/tripdest}gor_b02id
        gor_02id={
            1: "NE",
            2: "NW",
            3: "YH",
            4: "EM",
            5: "WM",
            6: "EoE",
            7: "London",
            8: "SE",
            9: "SW",
            10: "Wales",
            11: "Scotland",
            -8: "NA",
            -9: "DNA",
            -10: "DEAD",
        },
        # vehicle fuel type: vehproptype_b01id
        vp1_01id={
            1: {
                1: "unleaded petrol",
                94: "unleaded petrol and lead replacement petrol (LRP)",
                95: "lead replacement petrol (LRP)",
                96: "leaded (classic cars)",
            },
            2: {2: "diesel"},
            3: {3: "electric"},
            4: {},
            5: {},
            6: {4: "liquefied petroleum gas (LPG)"},
            7: {5: "bi-fuel"},
            8: {97: "other", -8: "na", -9: "dna"},
            0: {0: ""},
            -10: {-10: "dead"},
        },
        # vehicle fuel type: vehproptypen_b01id
        vp2_01id={
            1: {1: "petrol"},
            2: {2: "diesel"},
            3: {3: "electric/battery only"},
            4: {4: "hybrid"},
            5: {5: "plug-in hybrid"},
            6: {6: "liquefied petroleum gas (LPG)"},
            7: {7: "bi-fuel"},
            8: {97: "other", -8: "na", -9: "dna"},
            0: {0: ""},
            -10: {-10: "dead"},
        },
    )

    luk.save_yaml(Path("lookup.yml"))
    print("debugging")
