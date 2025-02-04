import os

from typing import Union, List, Dict, Tuple
from pathlib import Path
import caf.base as cb
import caf.tem as ct
import pandas as pd
import numpy as np
from . import mdlconfig, mdlfunction as fun, mdllookup as luk

class NoTEM:
    """ produce trip-end from TfN LU pop and emp data
        LSOA21: 33,755 England, 1,917 Wales, 6,976 Scotland (DZ11), total 42,648
        MSOA21: 6,856 England, 410 Wales, 1,279 Scotland (IZ11), total 8,543
    """

    def __init__(self, nts_fldr: str, tem_fldr: str, sub_fldr: str, bal_geos: str, run_code: bool = True):
        fun.log_stderr('\n***** TRIP-END MODEL (NOTEM) *****')
        # read config
        self.cfg = mdlconfig.Config(nts_fldr)
        self.luk = luk.Lookup.load_yaml(Path("lookup.yml"))
        self.tfn_ttype, self.tfn_atype = self.cfg.tfn_ttype, self.cfg.tfn_atype
        self.tvt_list = self.luk.tt_to_dfr(self.tfn_ttype, self.cfg.def_ttype)
        self.fld_hbase, self.fld_nhbase = self.cfg.fld_hbase, self.cfg.fld_nhbase
        self.fld_rates, self.fld_split = self.cfg.fld_rates, self.cfg.fld_split
        self.rep_fldr, self.ted_fldr = self.cfg.fld_report, self.cfg.fld_tripend
        self.ins_fldr, self.nts_fldr = self.cfg.fld_input, self.cfg.dir_output
        self.fld_phis, self.fld_occs = self.cfg.fld_phis, self.cfg.fld_occs
        self.fld_prod, self.fld_attr = self.cfg.fld_prod, self.cfg.fld_attr
        self.tfn_mode, self.tem_fldr = self.cfg.tfn_modes, Path(tem_fldr)

        # read in cb data
        if run_code:
            fun.mkdir(self.tem_fldr / self.ins_fldr)
            self.out_fldr = fun.mkdir(self.tem_fldr / sub_fldr)
            self.lus_fldr = "landuse"

            # lu population
            self.pop_fldr = r'F:\Deliverables\Land-Use\241123_Population rebase\02_Final Outputs'
            # lu employment (previous)
            # self.emp_fldr = (r'F:\Working\Land-Use\OUTPUTS_base_employment_bres_approach_'
            #                  r'a_weighting_2_level_check\02_Final Outputs')
            self.emp_fldr = (r'F:\Working\Land-Use\OUTPUTS_base_employment_bres_2022_approach_'
                             r'a_weighting_3\02_Final Outputs')

            # zone translation
            # requires lsoa_id, zone_id, gor, tfn_at, lsoa_to_zone_pop, lsoa_to_zone_emp, or lsoa_to_zone.
            self.csv_zone = self.tem_fldr / self.ins_fldr / "normits_v3.3_lsoa21_trans.csv"
            self.col_lsoa, self.col_zone = "lsoa21_id", "normits_v3.3_id"
            self.col_report, self.seg_xtra = "gor", None
            self.seg_spec = ([self.col_zone] + list({self.col_report, "gor", "tfn_at", "hh_type"}) +
                             fun.val_to_list(self.seg_xtra) + ["purpose", "mode", "period"])
            self.mts_incl = ["tfn_at", "purpose", "mode", "period", "rho"]
            self.out_year, self.ted_ctrl = 2023, False

            # nts data for rho and phi: "_reg" - regression model, "" traditional method
            self.rho_type, self.phi_type = "_reg", "_reg"

            # normits zone system
            self._zone_system()

            # rebase adjustments
            self._apply_rebase()

            # hb prod[z,p,seg*,m,t]
            hbf_prod = self._production_hb('P13', True, False)

            # hb/nhb attr[z,p,soc*,m,t]
            emp_name = 'E5' if sub_fldr.lower().startswith('bres') else 'E6'
            hbf_attr, nhb_attr = self._attraction_all(emp_name, 'P11.1', True)

            # disaggregate hb attr[z,p,seg*,m,t]
            hbf_attr = self._attraction_segment(hbf_attr, hbf_prod)

            # balance trip-ends: by segmentation
            seg_2adj = ["purpose", "mode", "period"]
            # by gor: 1-ne, 2-nw, 3-yh, 4-em, 5-wm, 6-eoe, 7-lon, 8-se, 9-sw, 10-wales, 11-scotland
            geo_2adj = ({'geo': 'gor', 'bal': [1, 2, 3, 4, 5, [6, 7, 8], 9, 10, 11]}
                        if bal_geos.strip().lower() == 'gor' else {})

            # balance prod/attr at [gb,p,seg*,m,t]
            hbf_prod, hbf_attr = (self._balance('HB_fr P/A', hbf_prod, hbf_attr, 'P', seg_2adj, geo_2adj)
                                  if self.ted_ctrl else (hbf_prod, hbf_attr))

            # hb return (PA format) [z,p,seg*,m,t]
            hbr_prod, hbr_attr = self._hb_return(hbf_prod, hbf_attr)
            hbr_prod, hbr_attr = (self._balance('HB_to P/A', hbr_prod, hbr_attr, 'P', seg_2adj, geo_2adj)
                                  if self.ted_ctrl else (hbr_prod, hbr_attr))

            # nhb prod[z,p,seg*,m,t]
            nhb_prod = self._production_nhb(hbf_attr)

            # disaggregate nhb attr[z,p,seg*,m,t]
            nhb_attr = self._attraction_segment(nhb_attr, nhb_prod)
            nhb_prod, nhb_attr = (self._balance('NHB O/D', nhb_prod, nhb_attr, 'O', seg_2adj, geo_2adj)
                                  if self.ted_ctrl else (nhb_prod, nhb_attr))

            # finally, aggregate hh_type to ca/nca
            fun.log_stderr('\nAggregate to CA/NCA')
            hbf_prod = self._finalise(hbf_prod, "HB prod (fr)")
            hbf_attr = self._finalise(hbf_attr, "HB attr (fr)")
            hbr_prod = self._finalise(hbr_prod, "HB prod (to)")
            hbr_attr = self._finalise(hbr_attr, "HB attr (to)")
            nhb_prod = self._finalise(nhb_prod, "NHB prod")
            nhb_attr = self._finalise(nhb_attr, "NHB attr")

            # summary: PA for hb and OD for nhb
            fun.log_stderr('\nNoTEM summary')
            _frp = self._summary(hbf_prod, 'hb_fr', 'prod')
            _fra = self._summary(hbf_attr, 'hb_fr', 'attr')
            _top = self._summary(hbr_prod, 'hb_to', 'prod')
            _toa = self._summary(hbr_attr, 'hb_to', 'attr')
            _nho = self._summary(nhb_prod, 'nhb', 'prod')
            _nhd = self._summary(nhb_attr, 'nhb', 'attr')

            # write report
            self._report([_frp, _nho, _top], [_fra, _nhd, _toa])

            # car demand by pcu (hourly)
            self._write_veh_hr([hbf_prod, nhb_prod, hbr_prod], [hbf_attr, nhb_attr, hbr_attr],
                               [3, 4, 6], ['hb_fr', 'nhb', 'hb_to'], False)

            # write PA trip-end data (period)
            self._write_ted([hbf_prod, nhb_prod, hbr_prod], [hbf_attr, nhb_attr, hbr_attr],
                            ['hb_fr', 'nhb', 'hb_to'], self.ted_ctrl)

        else:
            fun.log_stderr(f' .. skipped!')

    def _apply_rebase(self, run_code: bool = True):
        # apply adjustments to reflect rebase
        fun.log_stderr(f'\nRebase adjustment')
        if run_code:
            csv_fldr = fr"{self.nts_fldr}\{self.cfg.fld_other}"
            # trip-rates (.csv: gor, pa, purpose, direction, ave, byr)
            self.adj_rate = fun.csv_to_dfr(fr"{csv_fldr}\trip_rate_adjustments.csv")
            # mts (.csv: gor, pa, direction, purpose, mode, period, ave, byr)
            self.adj_mtss = fun.csv_to_dfr(fr"{csv_fldr}\mode_time_split_adjustments.csv") # can't be done in nts-processing 
        else:
            dfr = {"gor": [], "pa": [], "purpose": [], "direction": [], "ave": [], "byr": []}
            self.adj_rate = pd.DataFrame(dfr)
            dfr.update({"mode": [], "period": []})
            self.adj_mtss = pd.DataFrame(dfr)

    def _zone_system(self, get_uniq: bool = False):
        fun.log_stderr('Import NorMITs zone system')
        col_sett, ruc_aggr = 'ruc11cd', self.luk.settlement()
        self.sys_zone = fun.csv_to_dfr(self.csv_zone)
        col_type = [self.col_zone] + list({self.col_report, 'gor', 'tfn_at'})
        self.sys_zone = self._as_type(self.sys_zone, col_type)
        self.sys_zone[self.col_lsoa] = self.sys_zone[self.col_lsoa].str.upper()
        self.sys_zone[col_sett] = self.sys_zone[col_sett].str.lower()

        # checking purpose
        out = (self.sys_zone.set_index(col_sett).rename(index=ruc_aggr['val'])
               .rename(index=ruc_aggr['out']).reset_index())
        if get_uniq:
            col_calc = f'{self.col_lsoa.replace("_id", "")}_to_{self.col_zone.replace("_id", "")}_spatial'
            out = out.groupby([self.col_zone, self.col_report, col_sett])[col_calc].sum().reset_index()
            out = fun.dfr_duplicates(out, col_calc, self.col_zone, 'max').drop(columns=col_calc)
        fun.dfr_to_csv(out, Path(self.out_fldr), 'NorMITs_zone', False)

    def _write_veh_hr(self, pro_list: List, att_list: List, out_mode: List, out_type: List,
                      run_code: bool = False):
        if not run_code:
            return

        # collapse columns
        def _col_name(x, _col: List):
            return ".".join([f"{cx}{cv}" for cx, cv in zip([''] + _col, x)])

        fun.log_stderr('\nConvert to vehicle trips')
        # read vehicle occupancy
        fld_occs = self.nts_fldr / self.fld_occs
        occ_fact = fun.csv_to_dfr(fld_occs / 'vehicle_occupancy_sum.csv')
        occ_fact = occ_fact.drop(columns=['driver', 'passenger', 'total'], errors='ignore')
        dct_w2hr = self.luk.week_to_hour()

        out_data, col_spec = [], ['mode', 'period']
        dct_mode = self.luk.mode()['out']
        for typ, pro, att in zip(out_type, pro_list, att_list):
            col_name = ['dest', 'orig'] if typ == 'hb_to' else ['orig', 'dest']
            occ = occ_fact.loc[occ_fact['direction'] == typ].drop(columns='direction')
            out = [pd.concat(dfr.values(), axis=0).rename(columns={'trips': col})
                   for dfr, col in zip([pro, att], col_name)]
            out = pd.concat(out, axis=1).reset_index().drop(columns=[self.col_report, 'tfn_at'])
            out = out.loc[out['mode'].isin(out_mode)].reset_index(drop=True)
            out = out.merge(occ, how='left', on=['mode', 'purpose', 'period']).fillna(1)
            for col in col_name:
                out[col] = out[col].div(out['occs'])
            out = out.groupby([self.col_zone] + col_spec)[col_name].sum().reset_index()
            for ts in dct_w2hr:
                for col in col_name:
                    tmp = out[col].div(dct_w2hr[ts][0]).div(dct_w2hr[ts][1])
                    out.loc[(out['period'] == ts), col] = tmp
            out_data.append(out.set_index([self.col_zone] + col_spec))

        # print totals
        out_data = pd.concat(out_data, axis=0).reset_index()

        # output by segmentation
        for md in out_mode:
            col_zone = self.col_zone.replace('_id', '').split("_")[0]
            out = out_data.loc[out_data['mode'] == md]
            out = pd.pivot_table(out, index=self.col_zone, columns='period', values=['orig', 'dest'],
                                 aggfunc='sum').fillna(0)
            out.columns = out.columns.map(lambda x: _col_name(x, ['ts']))
            out_file = f'NoTEM_{self.out_year}_{dct_mode[md]}_OD_{col_zone}'
            fun.dfr_to_csv(out, self.out_fldr / self.ted_fldr, out_file)

    def _hb_return(self, hbf_prod: Dict, hbf_attr: Dict) -> Tuple:
        # produce HB return  trip-ends (PA format)
        fun.log_stderr('\nProd/attr trip-end (HB return)')
        hbp_fldr = self.nts_fldr / self.fld_prod / self.fld_hbase / self.fld_phis
        _col = {col: f'{col}.fr' for col in ['purpose', 'period']}
        dct_trip = {}
        col_grby = [col for col in self.seg_spec if col not in ['mode']]
        for pa, dct in zip(['p', 'a'], [hbf_prod, hbf_attr]):
            dct_trip[pa] = {}
            for pp in dct:
                phi_fact = fun.csv_to_dfr(hbp_fldr / f'phi_factors_{pa.upper()}_p{pp}{self.phi_type}.csv')
                phi_fact = phi_fact.drop(columns=['trips.fr', 'trips', 'trips.ave', "trips.est"],
                                         errors='ignore')
                out = dct[pp].index.get_level_values(level='purpose') == pp
                out = dct[pp][out].groupby(col_grby).sum().reset_index().rename(columns=_col)
                out = out.merge(phi_fact, how='left', on=['tfn_at'] + list(_col.values()))
                out = self._as_type(out, list(_col), int)
                out['trips'] = out['trips'].mul(out['phi'])
                out = out.groupby(col_grby)[['trips']].sum().reset_index()
                # sum trips to hb mode/purpose
                for p2 in out['purpose'].unique():
                    dct_trip[pa][p2] = [] if p2 not in dct_trip[pa] else dct_trip[pa][p2]
                    dct_trip[pa][p2].append(out.loc[out['purpose'] == p2])

            for pp in dct_trip[pa]:
                out = pd.concat(dct_trip[pa][pp], axis=0)
                dct_trip[pa][pp] = out.groupby(col_grby)[['trips']].sum()

        # apply mode-time split: [at, p, m] (t)
        fun.log_stderr(' .. apply mode-time split')
        ppx_list = list(self.luk.purpose()['out'])
        for pa in ['p', 'a']:
            mts_from = ['hh_type'] if pa == 'p' else []
            mts_grby = [col for col in self.mts_incl if col not in ['mode', 'rho']] + mts_from
            hbp_fldr = self.nts_fldr / (self.fld_prod if pa == "p" else self.fld_attr) / self.fld_hbase
            ted_type = 'production' if pa == "p" else 'attraction'
            mts_fact = fun.csv_to_dfr(hbp_fldr / self.fld_split /
                                      f"mode_time_split_{ted_type}_hb_to{self.rho_type}.csv",
                                      self.mts_incl + mts_from)
            for pp in ppx_list:
                out = dct_trip[pa][pp].rename(columns={pp: 'trips'}).reset_index()
                mts = mts_fact.loc[mts_fact['purpose'] == pp].reset_index(drop=True)
                mts['rho'] = mts['rho'].div(mts.groupby(mts_grby)['rho'].transform('sum'))
                out = out.merge(mts, how='left', on=mts_grby)
                out['trips'] = out['trips'].mul(out['rho'])
                # mts adjustment
                out = self._adj_mtss(out, pa, pp, "hb_to", "gor")
                # final output
                out = out.groupby(self.seg_spec)[['trips']].sum()
                dct_trip[pa][pp] = out

        # prod.to -> dest, attr.to -> orig when convert to od
        return dct_trip["p"], dct_trip["a"]

    def _write_ted(self, pro_list: List, att_list: List, out_type: List,
                   run_code: bool = True):
        if not run_code:
            return

        fun.log_stderr('\nWrite trip-end to csv')
        for typ, pro, att in zip(out_type, pro_list, att_list):
            out = [pd.concat(dfr.values(), axis=0).rename(columns={'trips': col})
                   for dfr, col in zip([pro, att], ['prod', 'attr'])]
            out = pd.concat(out, axis=1).reset_index().drop(columns=[self.col_report, 'tfn_at'])
            out_file = f'NorMITs_tripend_{self.out_year}_{typ}'
            fun.dfr_to_csv(out, self.out_fldr / self.ted_fldr, out_file, False)

    def _report(self, pro_list: List, att_list: List, out_type: Union[str, None] = None):
        # report trip-ends
        out = [pd.concat(pro_list, axis=0), pd.concat(att_list, axis=0)]
        out = pd.concat(out, axis=1)
        out_type = f'_{out_type}' if out_type is not None else ''
        fun.dfr_to_csv(out, self.out_fldr / self.rep_fldr,
                       f'NoTEM_{self.out_year}_{self.col_report}{out_type}')

    def _summary(self, dct_trip: Dict, dir_name: str, out_name: str,
                 int_2str: bool = True, out_type: Union[str, None] = None,
                 agg_purp: bool = False, out_2csv: bool = False) -> pd.DataFrame:
        """
        dct_trip: trip-end data stored in dictionary {p: dfr}
        dir_name: name of trip direction
        out_name: rename trips to either prod or attr
        int_2str: True if output as description, else code
        out_type: hb_fr, hb_to, nhb
        agg_purp: True if aggregate purposes, else as is
        out_2csv: True output to csv, else no
        """
        out: Union[pd.DataFrame, List] = []
        seg_spec = {self.col_zone, self.col_report, 'gor', 'tfn_at'}
        seg_spec = [col for col in self.seg_spec if col not in seg_spec]
        for pp, dfr in dct_trip.items():
            dfr = (dfr.groupby(seg_spec + [self.col_report])[['trips']].sum()
                   .rename(columns={'trips': out_name}))
            out.append(dfr)
        out = pd.concat(out, axis=0).reset_index()

        out = self._as_name(out, 'purpose_tag') if agg_purp else out
        out = (self._as_name(out, ['hh_type', 'mode', 'purpose', self.col_report])
               if int_2str else out)
        out['direction'] = dir_name
        out = out.groupby([self.col_report, 'direction'] + seg_spec)[[out_name]].sum()
        if out_2csv:
            out_type = f'_{out_type}' if out_type is not None else ''
            fun.dfr_to_csv(out, self.out_fldr,
                           f'{dir_name}_{out_name}_mts_{self.col_report}{out_type}')
        return out

    def _production_hb(self, pop_name: str = "P13", to_model: bool = False, seg_byca: bool = True) -> Dict:
        fun.log_stderr('\nProduction trip-end (HB)')
        pop = self._import_lu_pop(self.pop_fldr, pop_name, f'lu_pop_{self.out_year}')
        hbp_fldr = self.nts_fldr / self.fld_prod / self.fld_hbase
        hbp_rate = fun.csv_to_dfr(hbp_fldr / self.fld_rates / 'hb_trip_rates_production.csv')
        # process data
        pop_spec = {'gender_3': 'gender', 'aws': 'aws', 'hh_type': 'hh_type',
                    'soc': 'soc', 'ns_sec': 'ns'}
        pop = self._process_lu(pop, ['adult_nssec'], pop_spec, 'pop')

        tvt_spec = list(pop_spec.values())
        ppx_list = list(self.luk.purpose()['out'])
        hbp_rate = hbp_rate.pivot_table(index=tvt_spec + ['tfn_at'], columns='purpose',
                                        values='beta').reset_index()

        pop = pop.merge(hbp_rate, how='left', on=tvt_spec + ['tfn_at'])
        pop[ppx_list] = pop[ppx_list].multiply(pop['pop'], axis='index')
        pop['trips'] = pop[ppx_list].sum(axis=1)

        # write hb outputs
        out = pop.groupby([self.col_report] + tvt_spec)[['pop']].sum()
        out = self._as_name(out.reset_index(), self.col_report)
        fun.dfr_to_csv(out, self.out_fldr / self.rep_fldr,
                       f'pop_{self.out_year}_{self.col_report}', False)

        # write to model zone
        if to_model:
            col_zone = self.col_zone.replace('_id', '').split("_")[0]
            out_grby = ([self.col_zone] + (["hh_type"] if seg_byca else []) +
                        list({self.col_report, 'gor', 'tfn_at'}))
            out = pop.groupby(out_grby)[['pop', "trips"] + ppx_list].sum().reset_index()
            out = self._as_name(self._hh_to_ca(out), 'hh_type') if 'hh_type' in out.columns else out
            out = out.groupby(out_grby)[['pop', "trips"] + ppx_list].sum()
            fun.dfr_to_csv(out, self.out_fldr / self.rep_fldr, f'pop_{self.out_year}_{col_zone}')

        # apply hb production mts[at, hh, p](m/t)
        mts_fact = fun.csv_to_dfr(hbp_fldr / self.fld_split /
                                  f"mode_time_split_production_hb_fr{self.rho_type}.csv",
                                  self.mts_incl + ["hh_type"])
        fun.log_stderr(' .. apply mode-time split')
        col_excl = ('hh_type', 'purpose', 'mode', 'period')
        col_grby = [col for col in self.seg_spec if col not in col_excl]
        pop = pop.groupby(col_grby + ['hh_type'])[['pop'] + ppx_list].sum()
        dct_trip = {}
        for pp in ppx_list:
            out = pop[[pp]].rename(columns={pp: 'trips'}).reset_index()
            # firstly, apply trip-rate adjustment
            out = self._adj_rate(out, "p", pp, "hb_fr", "gor")

            # secondly, apply mode-time split
            mts = mts_fact.loc[mts_fact['purpose'] == pp]
            out = out.merge(mts, how='left', on=['tfn_at', 'hh_type'])
            out['trips'] = out['trips'].mul(out['adj']).mul(out['rho'])

            # thirdly, apply mts adjustment
            out = self._adj_mtss(out, "p", pp, "hb_fr", "gor")

            # finally, output
            dct_trip[pp] = out.groupby(self.seg_spec)[['trips']].sum()

        return dct_trip

    def _attraction_all(self, emp_name: str, hoh_name: str, to_model: bool = False) -> Tuple:
        # hb attraction
        fun.log_stderr('\nAttraction trip-end (HB & NHB)')
        fld_attr = self.nts_fldr / self.fld_attr

        # read employment: E5 - BRES-based, E6 - VOA-based
        emp = self._import_lu_emp(self.emp_fldr, emp_name, f'lu_emp_{self.out_year}_{emp_name}')
        emp_spec = {'soc': 'soc', 'sic_2_digit': 'sic'}
        emp = self._process_lu(emp, ['sic_1_digit'], emp_spec, 'emp')
        sic = self._sic_to_ecode(sorted(emp['sic'].unique()))

        out = emp.groupby([self.col_report, 'soc'])[['emp']].sum()
        out = self._as_name(out.reset_index(), self.col_report)
        fun.dfr_to_csv(out, self.out_fldr / self.rep_fldr,
                       f'emp_{self.out_year}_{self.col_report}', False)

        # household data
        hhd = self._import_lu_hh(self.pop_fldr, hoh_name, f'lu_hh_{self.out_year}')
        hhd = self._process_lu(hhd, ['car_availability'], {}, 'hh')
        hhd['soc'], hhd['e_code'] = 0, sic[7]['hh']

        # attraction trip-rates
        hba_rate = fun.csv_to_dfr(fld_attr / self.fld_hbase / self.fld_rates /
                                  'trip_rates_attraction.csv')
        hba_rate['soc'] = hba_rate['soc'].astype(str).str.replace('all', '0').astype(int)

        # hb attraction trip-ends
        att_grby, ppx_list = ['tfn_at', 'soc', 'e_code'], list(self.luk.purpose()['out'])
        hba_rate = (hba_rate.pivot_table(index=['dir'] + att_grby, columns='p', values='alpha'
                                         ).fillna(0).reset_index())
        dct_trip, sum_jobs = {}, []
        col_excl = ('tfn_at', 'gender', 'hh_type', 'soc', 'ns', 'purpose', 'mode', 'period')
        col_grby = [col for col in self.seg_spec if col not in col_excl] + att_grby
        for di in ['hb', 'nhb']:
            dct_trip[di] = {}
            fun.log_stderr(f' {di.upper()} trip-end')
            hbr = hba_rate.loc[hba_rate['dir'] == di].drop(columns='dir')
            mts_fldr = fld_attr / (self.fld_hbase if di == 'hb' else self.fld_nhbase) / self.fld_split
            dir_type = f"{di}_fr" if di == "hb" else di
            mts_fact = f'mode_time_split_attraction_{dir_type}{self.rho_type}.csv'
            mts_fact = fun.csv_to_dfr(mts_fldr / mts_fact, self.mts_incl)
            # apply mode time split: mts[at, p] (m/t)
            fun.log_stderr(f' .. apply mode-time split')
            for pp in ppx_list:
                if pp != 7:
                    emp['e_code'], col_name = emp['sic'], 'emp'
                    out = emp.set_index('e_code').rename(index=sic[pp]).reset_index()
                    out = out.groupby(col_grby)[[col_name]].sum().reset_index()
                    if pp not in [1, 2]:  # non commute/business
                        out['soc'] = 0
                        out = out.groupby(col_grby)[[col_name]].sum().reset_index()
                else:  # p7 - visit friends
                    out, col_name = hhd.copy(), 'hh'

                out = out.merge(hbr[att_grby + [pp]], how='left', on=att_grby).fillna(0)
                out[pp] = out[pp].mul(out[col_name])

                # collate emp data
                if di == 'hb':
                    tmp_grby = [self.col_zone] + list({self.col_report, 'gor', 'tfn_at'})
                    tmp = out.groupby(tmp_grby + ['e_code'])[[col_name]].sum().reset_index()
                    tmp = tmp.loc[tmp['e_code'].isin(set(sic[pp].values()))]
                    tmp = tmp.pivot_table(index=tmp_grby, columns='e_code', values=col_name)
                    sum_jobs.append(tmp)

                # aggregate to purposes
                out_grby = [col for col in col_grby if col != 'e_code']
                out = out.groupby(out_grby)[[pp]].sum().reset_index()
                # firstly, apply trip-rate adjustment (use prod)
                out = self._adj_rate(out, "p", pp, dir_type, "gor")

                # secondly, apply mode-time split
                mts = mts_fact.loc[mts_fact['purpose'] == pp]
                out = out.merge(mts, how='left', on='tfn_at')
                out[pp] = out[pp].mul(out['adj']).mul(out['rho'])
                out_grby = [col for col in self.seg_spec if col in out.columns]
                out = out.groupby(out_grby)[[pp]].sum().rename(columns={pp: 'trips'})

                # thirdly, apply mts adjustment
                out = self._adj_mtss(out.reset_index(), "a", pp, dir_type, "gor")

                # finally, output
                dct_trip[di][pp] = out.groupby(out_grby)[["trips"]].sum()

        # write emp summary
        sum_jobs = pd.concat(sum_jobs, axis=1)
        sum_jobs = sum_jobs.loc[:, ~sum_jobs.columns.duplicated()].copy()
        sum_jobs = self._as_name(sum_jobs.reset_index(), self.col_report)
        out = sum_jobs.groupby(self.col_report).sum().drop(columns=[self.col_zone, 'tfn_at'])
        fun.dfr_to_csv(out, self.out_fldr / self.rep_fldr,
                       f'emp_{self.out_year}_{self.col_report}_ecode')

        # write to model zone
        if to_model:
            col_zone = self.col_zone.replace('_id', '').split("_")[0]
            out_grby = [self.col_zone] + list({self.col_report, 'gor', 'tfn_at'})
            out = pd.concat(list(dct_trip['hb'].values()), axis=0).reset_index()
            out = out.groupby(out_grby + ['purpose'])[['trips']].sum()
            out = pd.pivot_table(out, index=out_grby, columns='purpose', values='trips')
            out = pd.merge(emp.groupby(out_grby)[['emp']].sum(), out, how='right',
                           left_index=True, right_index=True)
            fun.dfr_to_csv(out, self.out_fldr / self.rep_fldr, f'emp_{self.out_year}_{col_zone}')
            fun.dfr_to_csv(sum_jobs, self.out_fldr / self.rep_fldr,
                           f'emp_{self.out_year}_{col_zone}_ecode', False)

        return dct_trip['hb'], dct_trip['nhb']

    def _attraction_segment(self, dct_attr: Dict[int, pd.DataFrame],
                            dct_prod: Dict[int, pd.DataFrame]) -> Dict[int, pd.DataFrame]:
        # further segment attraction trip-ends
        soc = self.luk.soc()['out']
        soc = pd.DataFrame(data={'soc': [0] * len(soc), 'out': list(soc)})
        col_grby = [self.col_report, 'purpose', 'mode', 'period']
        ppx_list = list(self.luk.purpose()['out'])
        min_trip = 6 * self.cfg.min_trip

        for pp in ppx_list:
            out = dct_attr[pp].reset_index()
            for key in ['hh_type', 'gender', 'soc', 'ns']:
                if key in self.seg_spec:
                    if key == 'soc':  # for soc only as soc is included in attraction
                        out = out.merge(soc, how='left', on=key)
                        out.loc[~out['out'].isna(), key] = out['out']
                        out = out.drop(columns='out')

                    nme = f'{key}_split'
                    tmp = dct_prod[pp].groupby(col_grby + [key]).sum().reset_index()
                    tmp[nme] = np.nan
                    for idx, _ in enumerate(col_grby):
                        col = col_grby[:-idx] if idx > 0 else col_grby
                        num = tmp.groupby(col + [key])['trips'].transform('sum')
                        den = tmp.groupby(col)['trips'].transform('sum')
                        tmp.loc[tmp[nme].isna() & (den > min_trip), nme] = num.div(den)
                    tmp = tmp.drop(columns='trips')
                    tmp[nme] = 1 if key == 'soc' and pp in [1, 2] else tmp[nme]
                    out = out.merge(tmp, how='left', on=col_grby + ([key] if key in out.columns else []))
                    out['trips'] = out['trips'].mul(out[nme])
            dct_attr[pp] = out.groupby(self.seg_spec)[['trips']].sum()
        return dct_attr

    @staticmethod
    def _balance(bal_type: str, dct_prod: Dict, dct_attr: Dict, ted_ctrl: str,
                 seg_2adj: Union[List, str] = 'purpose', geo_2adj: Dict = None) -> Union[List, Tuple]:
        """ balance attraction and production trip-ends at GB level
            ted_ctrl: P/O - prod constraint, A/D - dest constraint, PA/OD - doubly-constrained
            seg_2adj: segmentation balance, e.g. [purpose, mode, time, hh_type]
            geo_2adj: geography balance, e.g. {'geo': 'gor', 'bal': [gor1, [gor2, gor3], gor4]}
        """
        def _prep(dfr: pd.DataFrame) -> List:
            idx, dfr = list(dfr.index.names), dfr.reset_index()
            dfr['bal'] = dfr[geo_2adj['geo']] if 'geo' in geo_2adj else 1
            dfr = (dfr.set_index('bal').rename(index=geo_list).reset_index()
                   if len(geo_list) > 0 else dfr)
            return [dfr, idx]

        def _calc(dfr: pd.DataFrame) -> pd.DataFrame:
            return dfr.groupby(seg_2adj + ['bal'])[['trips']].sum().rename(columns={'trips': 'fac'})

        def _apply(dfr: pd.DataFrame, fac: pd.DataFrame, idx_list: List) -> pd.DataFrame:
            dfr = pd.merge(dfr, fac, how='left', on=['bal'] + seg_2adj)
            dfr['trips'] = dfr['trips'].mul(dfr['fac'])
            dfr = dfr.set_index(idx_list).drop(columns=['bal', 'fac'])
            return dfr

        fun.log_stderr(f'\nBalance {bal_type}')
        geo_2adj = {} if geo_2adj is None else geo_2adj
        geo_name = [geo_2adj['geo'] if 'geo' in geo_2adj else 'gb']
        seg_2adj, ted_ctrl = fun.val_to_list(seg_2adj), ted_ctrl.strip().lower()
        fun.log_stderr(f' .. controlled to {ted_ctrl.upper()}, by {geo_name + seg_2adj}')
        geo_list = (fun.itm_to_key({key: val for key, val in enumerate(geo_2adj['bal'], 1)})
                    if 'bal' in geo_2adj else {})
        for pp in dct_attr:
            dct_prod[pp], idx_prod = _prep(dct_prod[pp])
            dct_attr[pp], idx_attr = _prep(dct_attr[pp])

            # calculate factors
            _pro, _att = _calc(dct_prod[pp]), _calc(dct_attr[pp])
            _fac = (_pro if ted_ctrl in ['p', 'o', 'prod', 'orig'] else
                    _att if ted_ctrl in ['a', 'd', 'attr', 'dest'] else _pro.add(_att).div(2))
            _pro = _fac.div(_pro).fillna(1).reset_index()
            _att = _fac.div(_att).fillna(1).reset_index()

            # apply factors
            dct_prod[pp] = _apply(dct_prod[pp], _pro, idx_prod)
            dct_attr[pp] = _apply(dct_attr[pp], _att, idx_attr)

        return dct_prod, dct_attr

    def _production_nhb(self, hbf_attr: Dict) -> Dict:
        fun.log_stderr('\nProduction trip-end (NHB)')
        nhb_fldr = self.nts_fldr / self.fld_prod / self.fld_nhbase
        nhb_rate = fun.csv_to_dfr(nhb_fldr / self.fld_rates / 'nhb_trip_rates_production.csv')
        nhb_rate.drop(columns=['trips', 'trips.hb'], inplace=True)

        nhb_prod = {}
        col_grby = [col for col in self.seg_spec if col != 'period']
        for pp in hbf_attr:
            out = hbf_attr[pp].groupby(col_grby)[['trips']].sum().reset_index()
            out = out.rename(columns={col: f'{col}.hb' for col in ['mode', 'purpose']})
            fac = nhb_rate.loc[nhb_rate['purpose.hb'] == pp]
            out = out.merge(fac, how='left', on=['tfn_at', 'mode.hb', 'purpose.hb'])
            out['trips'] = out['trips'].mul(out['gamma'])
            out = out.groupby(col_grby)[['trips']].sum().reset_index()
            # sum trips to nhb mode/purpose
            for p2 in out['purpose'].unique():
                nhb_prod[p2]: Union[pd.DataFrame, List] = [] if p2 not in nhb_prod else nhb_prod[p2]
                nhb_prod[p2].append(out.loc[out['purpose'] == p2])

        # apply nhb time split: mts[at, p, m](t)
        fun.log_stderr(' .. apply mode-time split')
        mts_grby = [col for col in self.mts_incl if col not in ["period", "rho"]]
        mts_fact = fun.csv_to_dfr(nhb_fldr / self.fld_split /
                                  f"mode_time_split_production_nhb{self.rho_type}.csv",
                                  self.mts_incl)
        for pp in nhb_prod:
            out = pd.concat(nhb_prod[pp], axis=0)
            out = out.groupby(col_grby)[['trips']].sum().reset_index()
            mts = mts_fact.loc[mts_fact['purpose'] == pp]
            out = out.merge(mts, how='left', on=mts_grby).fillna(0)
            out['trips'] = out['trips'].mul(out['rho'])
            out = out.groupby(self.seg_spec)[['trips']].sum()
            nhb_prod[pp] = out

        return nhb_prod

    def _import_lu_pop(self, pop_fldr: Union[Path, str], pop_name: str, out_name: Union[Path, str],
                       out_zone: Union[str, None] = None, over_write: bool = False):
        _exist = os.path.isfile(self.out_fldr / self.lus_fldr / f"{out_name}.csv")
        fun.log_stderr(f' .. read population data ({pop_name})')
        if over_write or not _exist:
            dvec, _ = ct.utils.read_lu_pop(dir=pop_fldr,
                                           file_name=f'Output {pop_name}_{"{}"}.hdf',
                                           out_zoning=(None if out_zone is None else
                                                       cb.ZoningSystem.get_zoning(out_zone))
                                           )
            name_to_id = dvec.zoning_system.zones_data['zone_name'].to_dict()
            out = dvec.data.rename(columns=name_to_id)
            # write output
            fun.dfr_to_csv(out, self.out_fldr / self.lus_fldr, out_name)
            out = out.reset_index().rename_axis(None, axis=1)
        else:
            out = fun.csv_to_dfr(self.out_fldr / self.lus_fldr / f"{out_name}.csv")

        return out

    def _import_lu_emp(self, emp_fldr: Union[Path, str], emp_name: str, out_name: Union[Path, str],
                       out_zone: Union[str, None] = None, over_write: bool = False):
        _exist = os.path.isfile(self.out_fldr / self.lus_fldr / f"{out_name}.csv")
        fun.log_stderr(f' .. read employment data ({emp_name})')
        if over_write or not _exist:
            dvec, _ = ct.utils.read_lu_emp(dir=emp_fldr,
                                           file_name=f'Output {emp_name}.hdf',
                                           out_zoning=(None if out_zone is None else
                                                       cb.ZoningSystem.get_zoning(out_zone))
                                           )
            name_to_id = dvec.zoning_system.zones_data['zone_name'].to_dict()
            out = dvec.data.rename(columns=name_to_id)
            # write outputs
            fun.dfr_to_csv(out, self.out_fldr / self.lus_fldr, out_name)
            out = out.reset_index().rename_axis(None, axis=1)
        else:
            out = fun.csv_to_dfr(self.out_fldr / self.lus_fldr / f"{out_name}.csv")

        return out

    def _import_lu_hh(self, pop_fldr: Union[Path, str], hhs_name: str, out_name: Union[Path, str],
                      out_zone: Union[str, None] = None, over_write: bool = False):
        _exist = os.path.isfile(self.out_fldr / self.lus_fldr / f"{out_name}.csv")
        fun.log_stderr(f' .. read household data ({hhs_name})')
        if over_write or not _exist:
            dvec, _ = ct.utils.read_lu_hh(dir=pop_fldr,
                                          file_name=f'Output {hhs_name}_{"{}"}.hdf',
                                          out_zoning=(None if out_zone is None else
                                                      cb.ZoningSystem.get_zoning(out_zone)),
                                          )
            name_to_id = dvec.zoning_system.zones_data['zone_name'].to_dict()
            out = dvec.data.rename(columns=name_to_id)
            # write output
            fun.dfr_to_csv(out, self.out_fldr / self.lus_fldr, out_name)
            out = out.reset_index().rename_axis(None, axis=1)
        else:
            out = fun.csv_to_dfr(self.out_fldr / self.lus_fldr / f"{out_name}.csv")

        return out

    def _process_lu(self, dfr: pd.DataFrame, col_drop: Union[List, str], col_index: Dict,
                    col_name: str) -> pd.DataFrame:
        # process lu data to output zone system
        col_drop = fun.val_to_list(col_drop)
        dfr = dfr.drop(columns=col_drop) if len(col_drop) > 0 else dfr
        if len(col_index) > 0:
            dfr = (dfr.set_index(list(col_index)).stack().reset_index(name=col_name)
                   .rename(columns=col_index | {f'level_{len(col_index)}': self.col_lsoa}))
        else:
            dfr = (pd.DataFrame(dfr.sum(axis=0).reset_index(name=col_name))
                   .rename(columns={'index': self.col_lsoa}))

        dfr[self.col_lsoa] = dfr[self.col_lsoa].str.upper()

        # translation from: {col_lsoa}, to: {col_zone}
        col_grby = [self.col_zone] + list({self.col_report, 'tfn_at', 'gor'})
        col_lsoa, col_zone = self.col_lsoa.replace("_id", ""), self.col_zone.replace("_id", "")
        col_tran = f'{col_lsoa}_to_{col_zone}_{"pop" if col_name == "hh" else col_name}'
        col_tran = f'{col_lsoa}_to_{col_zone}_spatial' if col_tran not in self.sys_zone else col_tran
        tfn_zone = self.sys_zone[col_grby + [self.col_lsoa, col_tran]].copy()
        _den = tfn_zone.groupby(self.col_lsoa)[col_tran].transform('sum')
        tfn_zone[col_tran] = tfn_zone[col_tran].div(_den).fillna(0)
        dfr = dfr.merge(tfn_zone, how='left', on=self.col_lsoa)
        dfr[col_name] = dfr[col_name].mul(dfr[col_tran]).fillna(0)
        dfr = dfr.groupby(col_grby + list(col_index.values()))[[col_name]].sum()
        return dfr.reset_index()

    def _adj_rate(self, dfr: pd.DataFrame, pa: str, pp: int, di: str, level: Union[List, str]) -> pd.DataFrame:
        level = fun.val_to_list(level)
        adj = ((self.adj_rate["pa"] == pa) & (self.adj_rate['purpose'] == pp) &
               (self.adj_rate["direction"] == di))
        adj = self.adj_rate.loc[adj].reset_index(drop=True)
        if len(adj) > 0:
            adj["adj"] = adj["byr"].div(adj["ave"]).fillna(1)
            adj.loc[adj["adj"] == 0, "adj"] = 1
            dfr = pd.merge(dfr, adj[level + ['adj']], how="left", on=level)
        else:
            dfr["adj"] = 1
        return dfr

    def _adj_mtss(self, dfr: pd.DataFrame, pa: str, pp: int, di: str, level: Union[List, str]) -> pd.DataFrame:
        level = fun.val_to_list(level)
        adj = ((self.adj_mtss["pa"] == pa) & (self.adj_mtss['purpose'] == pp) &
               (self.adj_mtss["direction"] == di))
        adj = self.adj_mtss.loc[adj].reset_index(drop=True)
        if len(adj) > 0:
            adj["adj"] = adj["byr"].div(adj["ave"]).fillna(1)
            adj.loc[adj["adj"] == 0, "adj"] = 1
            dfr = pd.merge(dfr.drop(columns="adj", errors="ignore"), adj[level + ["mode", "period", "adj"]],
                           how="left", on=level + ["mode", "period"])
            dfr["adj"] = dfr["adj"].mul(dfr["trips"])
            dfr["trips"] = (dfr["adj"].div(dfr.groupby(level)["adj"].transform("sum"))
                            .mul(dfr.groupby(level)["trips"].transform("sum")))
        return dfr.drop(columns="adj", errors="ignore")

    def _finalise(self, dct_trip: Dict, str_name: str) -> Dict:
        fun.log_stderr(f' .. {str_name}')
        for pp in dct_trip:
            dct_trip[pp] = self._hh_to_ca(dct_trip[pp].reset_index())
            dct_trip[pp] = dct_trip[pp].groupby(self.seg_spec)[['trips']].sum()

        return dct_trip

    def _hh_to_ca(self, dfr: pd.DataFrame) -> pd.DataFrame:
        dct = self.luk.hh_to_ca()
        dfr[dct['col']] = dfr[dct['col']].apply(lambda x: dct['val'][x])
        return dfr

    def _as_name(self, dfr: pd.DataFrame, col_list: Union[List, str]) -> pd.DataFrame:
        # change code to names
        def lookup(col):
            return (self.luk.mode()['out'] if col == 'mode' else
                    self.luk.purpose()['out'] if col == 'purpose' else
                    self.luk.purpose_tag() if col == 'purpose_tag' else
                    self.luk.hh_to_ca()['out'] if col == 'hh_type' else
                    self.luk.at_tfn('')['out'] if col == 'tfn_at' else
                    self.luk.gor_02id if col == 'gor' else
                    {})

        col_list = fun.val_to_list(col_list)
        val_list = [lookup(col) for col in col_list]

        for col, dct in zip(col_list, val_list):
            dfr = (dfr.set_index(col.split('_')[0] if col in ['purpose_tag'] else col)
                   .rename(index=dct).reset_index())

        return dfr

    @staticmethod
    def _as_type(dfr: pd.DataFrame, col_name: Union[List, str], col_type: type = object) -> pd.DataFrame:
        dfr[col_name] = dfr[col_name].astype(col_type)
        return dfr

    def _sic_to_ecode(self, sic_list: List) -> Dict:
        _dct = self.luk.sic_to_ecode()
        _dct = {pp: {key.lower(): [val.lower().replace('s', '') for val in fun.val_to_list(itm)]
                     for key, itm in dct.items() if key != 'exc'}
                for pp, dct in _dct.items()}
        _dct = {pp: {key: ([fun.str_to_value(val) for val in itm] if itm[0] != 'all' else sic_list)
                     for key, itm in dct.items()} for pp, dct in _dct.items()}
        return {pp: fun.itm_to_key(itm) for pp, itm in _dct.items()}


if __name__ == "__main__":
    NoTEM(r"D:\NorMITs Demand\NTS Processing", r"D:\NorMITs Demand\NoTEM", "voa_gb_2023", "gb")
