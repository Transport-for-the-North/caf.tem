#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import caf.base as cb

NOHAM = cb.ZoningSystem.get_zoning("noham_v3.8")
NORMITS = cb.ZoningSystem.get_zoning("normits")
NOHAM_SECTOR = cb.ZoningSystem.get_zoning("noham_sector")
normits_noham_sector = pd.read_csv(
    r"I:\Data\Zone Translations\cache\noham_sector_normits\noham_sector_to_normits_spatial.csv"
)
normits_noham_sector.columns = [
    "noham_sector_id",
    "normits_id",
    "noham_sector_to_normits",
    "normits_to_noham_sector",
]
normits_noham_sector["noham_sector_id"] = normits_noham_sector[
    "noham_sector_id"
].replace(NOHAM_SECTOR.name_to_id)


# load trip ends data
prod_fr = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_productions\hb_normits_tem_segmented_fr_2023.dvec"
    )
)
prod_to = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_productions\hb_normits_tem_segmented_to_2023.dvec"
    )
)
attr_fr = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_attractions\hb_normits_tem_segmented_fr_2023.dvec"
    )
)
attr_to = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_attractions\hb_normits_tem_segmented_to_2023.dvec"
    )
)
nhb_prod = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\nhb_productions\nhb_normits_tem_segmented_fr_2023.dvec"
    )
)
nhb_attr = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\nhb_attractions\nhb_normits_tem_segmented_fr_2023.dvec"
    )
)

pm_prod_fr = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_productions\hb_normits_tem_segmented_fr_pm_2023.dvec"
    )
)
pm_prod_to = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_productions\hb_normits_tem_segmented_to_pm_2023.dvec"
    )
)
pm_attr_fr = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_attractions\hb_normits_tem_segmented_fr_pm_2023.dvec"
    )
)
pm_attr_to = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\hb_attractions\hb_normits_tem_segmented_to_pm_2023.dvec"
    )
)
pm_nhb_prod = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\nhb_productions\nhb_normits_tem_segmented_fr_pm_2023.dvec"
    )
)
pm_nhb_attr = cb.DVector.load(
    Path(
        r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\nhb_attractions\nhb_normits_tem_segmented_fr_pm_2023.dvec"
    )
)

# Original post-me trip ends with direction_od segment, which can be used to compare with the adjusted trip ends by direction (fr/to/nhb)
post_me_o = cb.DVector.load(Path(r"I:\Prior adjustment\posme_tripends\postme_o.dvec"))
post_me_d = cb.DVector.load(Path(r"I:\Prior adjustment\posme_tripends\postme_d.dvec"))

post_me_inter_p = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\postme_inter_p.dvec")
)
post_me_inter_a = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\postme_inter_a.dvec")
)

post_me_p = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\postme_p.dvec")
)
post_me_a = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\postme_a.dvec")
)

# Factors calculated
factor_hbp_fr = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\post_me_adj_fr_O.dvec")
)
factor_hbp_to = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\post_me_adj_to_O.dvec")
)
factor_hba_fr = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\post_me_adj_fr_D.dvec")
)
factor_hba_to = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\post_me_adj_to_D.dvec")
)
factor_nhb_p = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\post_me_adj_nhb_O.dvec")
)
factor_nhb_a = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\post_me_adj_nhb_D.dvec")
)

f_pm_prior_p = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_pm_prior_p.dvec")
)
f_pm_prior_a = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_pm_prior_a.dvec")
)
f_prior_te_fr_p = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_prior_te_fr_p.dvec")
)
f_prior_te_fr_a = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_prior_te_fr_a.dvec")
)
f_prior_te_to_p = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_prior_te_to_p.dvec")
)
f_prior_te_to_a = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_prior_te_to_a.dvec")
)
f_prior_te_nhb_p = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_prior_te_nhb_p.dvec")
)
f_prior_te_nhb_a = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_7\f_prior_te_nhb_a.dvec")
)


postme_o_fr = post_me_o.filter_segment_value("direction_od", 1)
postme_d_fr = post_me_d.filter_segment_value("direction_od", 1)

postme_o_to = post_me_o.filter_segment_value("direction_od", 2)
postme_d_to = post_me_d.filter_segment_value("direction_od", 2)

postme_o_nhb = post_me_o.filter_segment_value("direction_od", 0)
postme_d_nhb = post_me_d.filter_segment_value("direction_od", 0)

postme_inter_p_fr = post_me_inter_p.filter_segment_value("direction_od", 1)
postme_inter_a_fr = post_me_inter_a.filter_segment_value("direction_od", 1)
postme_p_fr = post_me_p.filter_segment_value("direction_od", 1)
postme_a_fr = post_me_a.filter_segment_value("direction_od", 1)

postme_inter_p_to = post_me_inter_p.filter_segment_value("direction_od", 2)
postme_inter_a_to = post_me_inter_a.filter_segment_value("direction_od", 2)
postme_p_to = post_me_p.filter_segment_value("direction_od", 2)
postme_a_to = post_me_a.filter_segment_value("direction_od", 2)

postme_inter_p_nhb = post_me_inter_p.filter_segment_value("direction_od", 0)
postme_inter_a_nhb = post_me_inter_a.filter_segment_value("direction_od", 0)
postme_p_nhb = post_me_p.filter_segment_value("direction_od", 0)
postme_a_nhb = post_me_a.filter_segment_value("direction_od", 0)


f_pm_prior_fr_p = f_pm_prior_p.filter_segment_value("direction_od", 1)
f_pm_prior_fr_a = f_pm_prior_a.filter_segment_value("direction_od", 1)
f_pm_prior_to_p = f_pm_prior_p.filter_segment_value("direction_od", 2)
f_pm_prior_to_a = f_pm_prior_a.filter_segment_value("direction_od", 2)
f_pm_prior_nhb_p = f_pm_prior_p.filter_segment_value("direction_od", 0)
f_pm_prior_nhb_a = f_pm_prior_a.filter_segment_value("direction_od", 0)


output = Path(r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_7\Core\tem_comp")
output.mkdir(exist_ok=True)
dvec_names = {
    "hb_prod_fr": prod_fr,
    "hb_prod_to": prod_to,
    "hb_attr_fr": attr_fr,
    "hb_attr_to": attr_to,
    "nhb_prod": nhb_prod,
    "nhb_attr": nhb_attr,
    "hb_pm_prod_fr": pm_prod_fr,
    "hb_pm_prod_to": pm_prod_to,
    "hb_pm_attr_fr": pm_attr_fr,
    "hb_pm_attr_to": pm_attr_to,
    "nhb_pm_prod": pm_nhb_prod,
    "nhb_pm_attr": pm_nhb_attr,
}
tem_dvecs = {}
for name, dvec in dvec_names.items():
    agg = (
        dvec.filter_segment_value("m", 3)
        .filter_segment_value("tp", [1, 2, 3, 4])
        .aggregate_comp_zones(NORMITS)
        .translate_zoning(NOHAM_SECTOR, trans_vector=normits_noham_sector)
        .add_segments(["userclass"])
        .aggregate(["tp", "userclass"])
    )
    agg.data.to_csv(output / f"{name}_agg.csv")
    # create dictionary for output filtered and aggregated dvecs for later use
    tem_dvecs[name] = agg

pm_dvec_names = {
    "postme_o_fr": postme_o_fr,
    "postme_o_to": postme_o_to,
    "postme_d_fr": postme_d_fr,
    "postme_d_to": postme_d_to,
    "postme_o_nhb": postme_o_nhb,
    "postme_d_nhb": postme_d_nhb,
    "postme_inter_p_fr": postme_inter_p_fr,
    "postme_inter_a_fr": postme_inter_a_fr,
    "postme_p_fr": postme_p_fr,
    "postme_a_fr": postme_a_fr,
    "postme_inter_p_to": postme_inter_p_to,
    "postme_inter_a_to": postme_inter_a_to,
    "postme_p_to": postme_p_to,
    "postme_a_to": postme_a_to,
    "postme_inter_p_nhb": postme_inter_p_nhb,
    "postme_inter_a_nhb": postme_inter_a_nhb,
    "postme_p_nhb": postme_p_nhb,
    "postme_a_nhb": postme_a_nhb,
}
pm_dvecs = {}
for name, dvec in pm_dvec_names.items():
    dvec_df = dvec.data
    dvec_df.to_csv(output / f"{name}_target.csv")
    pm_dvecs[name] = dvec_df


pm_factor_names = {
    "factor_hbp_fr": factor_hbp_fr,
    "factor_hbp_to": factor_hbp_to,
    "factor_hba_fr": factor_hba_fr,
    "factor_hba_to": factor_hba_to,
    "factor_nhb_p": factor_nhb_p,
    "factor_nhb_a": factor_nhb_a,
    "f_pm_prior_fr_p": f_pm_prior_fr_p,
    "f_pm_prior_fr_a": f_pm_prior_fr_a,
    "f_pm_prior_to_p": f_pm_prior_to_p,
    "f_pm_prior_to_a": f_pm_prior_to_a,
    "f_pm_prior_nhb_p": f_pm_prior_nhb_p,
    "f_pm_prior_nhb_a": f_pm_prior_nhb_a,
    "f_prior_te_fr_p": f_prior_te_fr_p,
    "f_prior_te_fr_a": f_prior_te_fr_a,
    "f_prior_te_to_p": f_prior_te_to_p,
    "f_prior_te_to_a": f_prior_te_to_a,
    "f_prior_te_nhb_p": f_prior_te_nhb_p,
    "f_prior_te_nhb_a": f_prior_te_nhb_a,
}

pm_factors = {}
for name, dvec in pm_factor_names.items():
    pm_factors[name] = dvec.data
    pm_factors[name].to_csv(output / f"{name}.csv")


print("=" * 60)
print("Production from home _ prior pm:")
print(tem_dvecs["hb_prod_fr"].data.head())
print(f"\nTotal: {tem_dvecs['hb_prod_fr'].total:,.2f}\n")

print("=" * 60)
print("\nProds return home _ prior pm:")
print(tem_dvecs["hb_prod_to"].data.head())
print(f"\nTotal: {tem_dvecs['hb_prod_to'].total:,.2f}\n")

print("=" * 60)
print("\nAttrs from home _ prior pm:")
print(tem_dvecs["hb_attr_fr"].data.head())
print(f"\nTotal: {tem_dvecs['hb_attr_fr'].total:,.2f}\n")

print("=" * 60)
print("\nAttrs return home _ prior pm:")
print(tem_dvecs["hb_attr_to"].data.head())
print(f"\nTotal: {tem_dvecs['hb_attr_to'].total:,.2f}\n")

print("=" * 60)
print("Production from home _ post pm:")
print(tem_dvecs["hb_pm_prod_fr"].data.head())
print(f"\nTotal: {tem_dvecs['hb_pm_prod_fr'].total:,.2f}\n")

print("=" * 60)
print("\nProds return home _ post pm:")
print(tem_dvecs["hb_pm_prod_to"].data.head())
print(f"\nTotal: {tem_dvecs['hb_pm_prod_to'].total:,.2f}\n")

print("=" * 60)
print("\nAttrs from home _ post pm:")
print(tem_dvecs["hb_pm_attr_fr"].data.head())
print(f"\nTotal: {tem_dvecs['hb_pm_attr_fr'].total:,.2f}\n")

print("=" * 60)
print("\nAttrs return home _ post pm:")
print(tem_dvecs["hb_pm_attr_to"].data.head())
print(f"\nTotal: {tem_dvecs['hb_pm_attr_to'].total:,.2f}\n")
