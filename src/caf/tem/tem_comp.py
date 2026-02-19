#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import caf.base as cb


NOHAM = cb.ZoningSystem.get_zoning('noham_v3.8')
NORMITS = cb.ZoningSystem.get_zoning('normits')
NOHAM_SECTOR = cb.ZoningSystem.get_zoning('noham_sector')
normits_noham_sector = pd.read_csv(r"I:\Data\Zone Translations\cache\noham_sector_normits_v3_3\noham_sector_to_normits_v3_3_spatial.csv")
normits_noham_sector.columns = ['noham_sector_id','normits_id','noham_sector_to_normits','normits_to_noham_sector']
normits_noham_sector['noham_sector_id'] = normits_noham_sector['noham_sector_id'].replace(NOHAM_SECTOR.name_to_id)


# load trip ends
prod_fr = cb.DVector.load(
    Path(r"I:\Prior adjustment\outputs_17_02\tripends\post_me_adj\Core\hb_productions\hb_normits_tem_segmented_fr_2023.dvec")
)
attr_fr = cb.DVector.load(
    Path(r"I:\Prior adjustment\outputs_18_02\tripends\post_me_adj\Core\hb_attractions\hb_normits_tem_segmented_fr_2023.dvec")
)
pm_prod_fr = cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_5\Core\hb_productions\hb_normits_tem_segmented_fr_pm_2023.dvec")
)

pm_attr_fr=cb.DVector.load(
    Path(r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_5\Core\hb_attractions\hb_normits_tem_segmented_fr_pm_2023.dvec")
)

post_me_o =cb.DVector.load(
    Path(r"I:\Prior adjustment\posme_tripends\postme_o.dvec")
)
post_me_d =cb.DVector.load(
    Path(r"I:\Prior adjustment\posme_tripends\postme_d.dvec")
)



# pm_factor_o = cb.DVector.load(
#     Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_4\post_me_adj_O.dvec")
# )
# pm_factor_d = cb.DVector.load(
#     Path(r"C:\Users\YanZhu\caf_mat\postme_adj\output_4\post_me_adj_D.dvec")
# )


postme_o_fr=post_me_o.filter_segment_value('direction_od', 1)
postme_d_fr=post_me_d.filter_segment_value('direction_od', 1)



prod_fr_filtered = prod_fr.filter_segment_value('m', 3)
prod_fr_filtered = prod_fr_filtered.filter_segment_value('tp', [1,2,3,4])
attr_fr_filtered = attr_fr.filter_segment_value('m', 3)
attr_fr_filtered = attr_fr_filtered.filter_segment_value('tp', [1,2,3,4])
pm_prod_fr_filtered = pm_prod_fr.filter_segment_value('m', 3)
pm_prod_fr_filtered = pm_prod_fr_filtered.filter_segment_value('tp', [1,2,3,4])
pm_attr_fr_filtered = pm_attr_fr.filter_segment_value('m', 3)
pm_attr_fr_filtered = pm_attr_fr_filtered.filter_segment_value('tp', [1,2,3,4])


prod_fr_agg = prod_fr_filtered.aggregate_comp_zones(NORMITS).translate_zoning(NOHAM_SECTOR, trans_vector=normits_noham_sector).add_segments(['userclass']).aggregate(['tp','userclass'])
attr_fr_agg = attr_fr_filtered.aggregate_comp_zones(NORMITS).translate_zoning(NOHAM_SECTOR, trans_vector=normits_noham_sector).add_segments(['userclass']).aggregate(['tp', 'userclass'])

pm_prod_fr_agg = pm_prod_fr_filtered.aggregate_comp_zones(NORMITS).translate_zoning(NOHAM_SECTOR, trans_vector=normits_noham_sector).add_segments(['userclass']).aggregate(['tp','userclass'])
pm_attr_fr_agg = pm_attr_fr_filtered.aggregate_comp_zones(NORMITS).translate_zoning(NOHAM_SECTOR, trans_vector=normits_noham_sector).add_segments(['userclass']).aggregate(['tp', 'userclass'])



prod_fr_agg_df = prod_fr_agg.data
attr_fr_agg_df = attr_fr_agg.data
pm_prod_fr_filtered_df = pm_prod_fr_filtered.data
pm_attr_fr_filtered_df = pm_attr_fr_filtered.data


pm_prod_fr_agg_df = pm_prod_fr_agg.data
post_me_o_fr_df = postme_o_fr.data




pm_attr_fr_agg_df = pm_attr_fr_agg.data
post_me_d_fr_df = postme_d_fr.data



# pm_pm_factor_o_df = pm_factor_o.data
# pm_pm_factor_d_df = pm_factor_d.data


# export to csv for checking
output = Path(r"I:\Prior adjustment\outputs_17_02\comp_3")
output.mkdir(exist_ok=True)
prod_fr_agg_df.to_csv(output / "prod_fr_2023_agg.csv")
attr_fr_agg_df.to_csv(output / "attr_fr_2023_agg.csv")
pm_prod_fr_agg_df.to_csv(output / "prod_fr_pm_2023_agg.csv")
post_me_o_fr_df.to_csv(output / "prod_fr_2023_agg_postme.csv")

pm_attr_fr_agg_df.to_csv(output / "attr_fr_pm_2023_agg.csv")

post_me_d_fr_df.to_csv(output / "attr_fr_2023_agg_postme.csv")


# pm_pm_factor_o_df.to_csv(output / "pm_pm_factor_o.csv")
# pm_pm_factor_d_df.to_csv(output / "pm_pm_factor_d.csv")


print("=" * 60)
print("Production from Home (PM):")
print(pm_prod_fr_filtered_df.head())
print(f"\nTotal: {pm_prod_fr_filtered.total:,.2f}\n")


print("=" * 60)
print("Attrs from Home (PM):")
print(pm_attr_fr_filtered_df.head())
print(f"\nTotal: {pm_attr_fr_filtered.total:,.2f}\n")

print("=" * 60)
print("\nProds from Home (PM) - Aggregated, Filtered:")
print(pm_prod_fr_agg_df.head())
print(f"\nTotal: {pm_prod_fr_agg.total:,.2f}\n")

print("=" * 60)
print("\nPost-ME Adjusted Prods from Home (PM):")
print(post_me_o_fr_df.head())
print(f"\nTotal: {postme_o_fr.total:,.2f}\n")


print("=" * 60)
print("\nAttrs from Home (PM) - Aggregated:")
print(pm_attr_fr_agg_df.head())
print(f"\nTotal: {pm_attr_fr_agg.total:,.2f}\n")

print("=" * 60)
print("\nPost-ME Adjusted Attrs from Home (PM):")
print(post_me_d_fr_df.head())
print(f"\nTotal: {postme_d_fr.total:,.2f}\n")
