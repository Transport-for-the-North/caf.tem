#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run TEM model with configuration file."""

# Built-Ins
from pathlib import Path

# Third Party
import caf.base as cb
import pandas as pd

if __name__ == '__main__':
    # Option A: Pass path as string
    output_path = Path(r"C:\Users\YanZhu\caf_tem\Outputs\post_me_adj_9\Core")
    hbp_pure_dmd = output_path / "hb_productions" / "hb_normits_pure_demand_2023.dvec"
    hbp_pure_dmd_aj = (
        output_path / "hb_productions" / "hb_normits_pure_demand_adj_2023.dvec"
    )
    hbp_mts_dmd = output_path / "hb_productions" / "hb_normits_mts_demand_2023.dvec"
    hbp_mts_dmd_aj = output_path / "hb_productions" / "hb_normits_mts_demand_adj_2023.dvec"
    hbp_fr = output_path / "hb_productions" / "hb_normits_tem_segmented_fr_2023.dvec"
    hbp_fr_pm = output_path / "hb_productions" / "hb_normits_tem_segmented_fr_pm_2023.dvec"
    hbp_to = output_path / "hb_productions" / "hb_normits_tem_segmented_to_2023.dvec"
    hbp_to_pm = output_path / "hb_productions" / "hb_normits_tem_segmented_to_pm_2023.dvec"
    hba_pure_dmd = output_path / "hb_attractions" / "hb_normits_pure_demand_2023.dvec"
    hba_pure_dmd_aj = (
        output_path / "hb_attractions" / "hb_normits_pure_demand_adj_2023.dvec"
    )
    hba_mts_dmd = output_path / "hb_attractions" / "hb_normits_mts_demand_2023.dvec"
    hba_mts_dmd_aj = output_path / "hb_attractions" / "hb_normits_mts_demand_adj_2023.dvec"
    hba_fr = output_path / "hb_attractions" / "hb_normits_tem_segmented_fr_2023.dvec"
    hba_fr_pm = output_path / "hb_attractions" / "hb_normits_tem_segmented_fr_pm_2023.dvec"
    hba_to = output_path / "hb_attractions" / "hb_normits_tem_segmented_to_2023.dvec"
    hba_to_pm = output_path / "hb_attractions" / "hb_normits_tem_segmented_to_pm_2023.dvec"

    nhbp_pure_dmd = output_path / "nhb_productions" / "nhb_normits_pure_demand_2023.dvec"
    nhbp_fr = output_path / "nhb_productions" / "nhb_normits_tem_segmented_fr_2023.dvec"
    nhbp_fr_pm = (
        output_path / "nhb_productions" / "nhb_normits_tem_segmented_fr_pm_2023.dvec"
    )

    nhba_pure_dmd = output_path / "nhb_attractions" / "nhb_normits_pure_demand_2023.dvec"
    nhba_pure_dmd_aj = (
        output_path / "nhb_attractions" / "nhb_normits_pure_demand_adj_2023.dvec"
    )
    nhba_mts_dmd = output_path / "nhb_attractions" / "nhb_normits_mts_demand_2023.dvec"
    nhba_mts_dmd_aj = (
        output_path / "nhb_attractions" / "nhb_normits_mts_demand_adj_2023.dvec"
    )
    nhba_fr = output_path / "nhb_attractions" / "nhb_normits_tem_segmented_fr_2023.dvec"
    nhba_fr_pm = (
        output_path / "nhb_attractions" / "nhb_normits_tem_segmented_fr_pm_2023.dvec"
    )


    # Load all DVectors
    hb_p_pure_dmd = cb.DVector.load(hbp_pure_dmd)
    hb_p_pure_dmd_aj = cb.DVector.load(hbp_pure_dmd_aj)
    hb_p_mts_dmd = cb.DVector.load(hbp_mts_dmd)
    hb_p_mts_dmd_aj = cb.DVector.load(hbp_mts_dmd_aj)
    hb_p_fr = cb.DVector.load(hbp_fr)
    hb_p_fr_pm = cb.DVector.load(hbp_fr_pm)
    hb_p_to = cb.DVector.load(hbp_to)
    hb_p_to_pm = cb.DVector.load(hbp_to_pm)

    hb_a_pure_dmd = cb.DVector.load(hba_pure_dmd)
    hb_a_pure_dmd_aj = cb.DVector.load(hba_pure_dmd_aj)
    hb_a_mts_dmd = cb.DVector.load(hba_mts_dmd)
    hb_a_mts_dmd_aj = cb.DVector.load(hba_mts_dmd_aj)
    hb_a_fr = cb.DVector.load(hba_fr)
    hb_a_fr_pm = cb.DVector.load(hba_fr_pm)
    hb_a_to = cb.DVector.load(hba_to)
    hb_a_to_pm = cb.DVector.load(hba_to_pm)

    nhb_p_pure_dmd = cb.DVector.load(nhbp_pure_dmd)
    nhb_p_fr = cb.DVector.load(nhbp_fr)
    nhb_p_fr_pm = cb.DVector.load(nhbp_fr_pm)
    nhb_a_pure_dmd = cb.DVector.load(nhba_pure_dmd)
    nhb_a_pure_dmd_aj = cb.DVector.load(nhba_pure_dmd_aj)
    nhb_a_mts_dmd = cb.DVector.load(nhba_mts_dmd)
    nhb_a_mts_dmd_aj = cb.DVector.load(nhba_mts_dmd_aj)
    nhb_a_fr = cb.DVector.load(nhba_fr)
    nhb_a_fr_pm = cb.DVector.load(nhba_fr_pm)

    # Extract data
    hb_p_pure_dmd_df = hb_p_pure_dmd.data
    hb_p_pure_dmd_aj_df = hb_p_pure_dmd_aj.data
    hb_p_mts_dmd_df = hb_p_mts_dmd.data
    hb_p_mts_dmd_aj_df = hb_p_mts_dmd_aj.data
    hb_p_fr_df = hb_p_fr.data
    hb_p_fr_pm_df = hb_p_fr_pm.data
    hb_p_to_df = hb_p_to.data
    hb_p_to_pm_df = hb_p_to_pm.data

    hb_a_pure_dmd_df = hb_a_pure_dmd.data
    hb_a_pure_dmd_aj_df = hb_a_pure_dmd_aj.data
    hb_a_mts_dmd_df = hb_a_mts_dmd.data
    hb_a_mts_dmd_aj_df = hb_a_mts_dmd_aj.data
    hb_a_fr_df = hb_a_fr.data
    hb_a_fr_pm_df = hb_a_fr_pm.data
    hb_a_to_df = hb_a_to.data
    hb_a_to_pm_df = hb_a_to_pm.data

    nhb_p_pure_dmd_df = nhb_p_pure_dmd.data
    nhb_p_fr_df = nhb_p_fr.data
    nhb_p_fr_pm_df = nhb_p_fr_pm.data
    nhb_a_pure_dmd_df = nhb_a_pure_dmd.data
    nhb_a_pure_dmd_aj_df = nhb_a_pure_dmd_aj.data
    nhb_a_mts_dmd_df = nhb_a_mts_dmd.data
    nhb_a_mts_dmd_aj_df = nhb_a_mts_dmd_aj.data
    nhb_a_fr_df = nhb_a_fr.data
    nhb_a_fr_pm_df = nhb_a_fr_pm.data

    # Extract totals
    hb_p_pure_dmd_tot = hb_p_pure_dmd.total
    hb_p_pure_dmd_aj_tot = hb_p_pure_dmd_aj.total
    hb_p_mts_dmd_tot = hb_p_mts_dmd.total
    hb_p_mts_dmd_aj_tot = hb_p_mts_dmd_aj.total
    hb_p_fr_tot = hb_p_fr.total
    hb_p_to_tot = hb_p_to.total
    hb_p_fr_pm_tot = hb_p_fr_pm.total
    hb_p_to_pm_tot = hb_p_to_pm.total


    hb_a_pure_dmd_tot = hb_a_pure_dmd.total
    hb_a_pure_dmd_aj_tot = hb_a_pure_dmd_aj.total
    hb_a_mts_dmd_tot = hb_a_mts_dmd.total
    hb_a_mts_dmd_aj_tot = hb_a_mts_dmd_aj.total
    hb_a_fr_tot = hb_a_fr.total
    hb_a_to_tot = hb_a_to.total
    hb_a_fr_pm_tot = hb_a_fr_pm.total
    hb_a_to_pm_tot = hb_a_to_pm.total

    nhb_p_pure_dmd_tot = nhb_p_pure_dmd.total
    nhb_p_fr_tot = nhb_p_fr.total
    nhb_p_fr_pm_tot = nhb_p_fr_pm.total
    nhb_a_pure_dmd_tot = nhb_a_pure_dmd.total
    nhb_a_pure_dmd_aj_tot = nhb_a_pure_dmd_aj.total
    nhb_a_mts_dmd_tot = nhb_a_mts_dmd.total
    nhb_a_mts_dmd_aj_tot = nhb_a_mts_dmd_aj.total
    nhb_a_fr_tot = nhb_a_fr.total
    nhb_a_fr_pm_tot = nhb_a_fr_pm.total

    # Print detailed data
    print("=" * 60)
    print("HOME-BASED PURE DEMAND:")
    print("=" * 60)
    print(hb_p_pure_dmd_df)
    print(f"\nTotal: {hb_p_pure_dmd.total:,.2f}\n")

    print("=" * 60)
    print("HOME-BASED PURE DEMAND ADJUSTED:")
    print("=" * 60)
    print(hb_p_pure_dmd_aj_df)
    print(f"\nTotal: {hb_p_pure_dmd_aj.total:,.2f}\n")

    print("=" * 60)
    print("HOME-BASED MTS DEMAND:")
    print("=" * 60)
    print(hb_p_mts_dmd_df)
    print(f"\nTotal: {hb_p_mts_dmd.total:,.2f}\n")

    print("=" * 60)
    print("HOME-BASED MTS DEMAND ADJUSTED:")
    print("=" * 60)
    print(hb_p_mts_dmd_aj_df)
    print(f"\nTotal: {hb_p_mts_dmd_aj.total:,.2f}\n")

    print("=" * 60)
    print("HOME-BASED TE FROM:")
    print("=" * 60)
    print(hb_p_fr_df)
    print(f"\nTotal: {hb_p_fr.total:,.2f}\n")

    print("=" * 60)
    print("HOME-BASED TE FROM PM ADJUSTED:")
    print("=" * 60)
    print(hb_p_fr_pm_df)
    print(f"\nTotal: {hb_p_fr_pm.total:,.2f}\n")

    print("=" * 60)
    print("HOME-BASED TE TO:")
    print("=" * 60)
    print(hb_p_to_df)
    print(f"\nTotal: {hb_p_to.total:,.2f}\n")

    print("=" * 60)
    print("HOME-BASED TE FROM:")
    print("=" * 60)
    print(hb_p_to_pm_df)
    print(f"\nTotal: {hb_p_to_pm.total:,.2f}\n")


    # Print detailed data for nhb
    print("=" * 60)
    print("NON HOME-BASED PURE DEMAND:")
    print("=" * 60)
    print(nhb_a_pure_dmd_df)
    print(f"\nTotal: {nhb_a_pure_dmd.total:,.2f}\n")

    print("=" * 60)
    print("NON HOME-BASED PURE DEMAND ADJUSTED:")
    print("=" * 60)
    print(nhb_a_pure_dmd_aj_df)
    print(f"\nTotal: {nhb_a_pure_dmd_aj.total:,.2f}\n")

    print("=" * 60)
    print("NON HOME-BASED MTS DEMAND:")
    print("=" * 60)
    print(nhb_a_mts_dmd_df)
    print(f"\nTotal: {nhb_a_mts_dmd.total:,.2f}\n")

    print("=" * 60)
    print("NON HOME-BASED MTS DEMAND ADJUSTED:")
    print("=" * 60)
    print(nhb_a_mts_dmd_aj_df)
    print(f"\nTotal: {nhb_a_mts_dmd_aj.total:,.2f}\n")

    print("=" * 60)
    print("NON HOME-BASED ATTRACTIONS FROM:")
    print("=" * 60)
    print(nhb_a_fr_df)
    print(f"\nTotal: {nhb_a_fr.total:,.2f}\n")


    # Create summary tables
    print("=" * 60)
    print("CREATING SUMMARY TABLES:")
    print("=" * 60)


    # Combined Summary Table
    combined_summary = pd.DataFrame(
        {
            "Metric": [
                "Pure Demand",
                "Pure Demand Adjusted",
                "MTS Demand",
                "MTS Demand Adjusted",
                "From",
                "To",
                "From PostME",
                "To PostME",
            ],
            "Productions": [
                hb_p_pure_dmd_tot,
                hb_p_pure_dmd_aj_tot,
                hb_p_mts_dmd_tot,
                hb_p_mts_dmd_aj_tot,
                hb_p_fr_tot,
                hb_p_to_tot,
                hb_p_fr_pm_tot,
                hb_p_to_pm_tot,
            ],
            "Attractions": [
                hb_a_pure_dmd_tot,
                hb_a_pure_dmd_aj_tot,
                hb_a_mts_dmd_tot,
                hb_a_mts_dmd_aj_tot,
                hb_a_fr_tot,
                hb_a_to_tot,
                hb_a_fr_pm_tot,
                hb_a_to_pm_tot,
            ],
        }
    )

    nhb_combined_summary = pd.DataFrame(
        {
            "Metric": [
                "Pure Demand",
                "Pure Demand Adjusted",
                "MTS Demand",
                "MTS Demand Adjusted",
                "From",
                "From PostME",
            ],
            "Productions": [
                nhb_p_pure_dmd_tot,
                None,
                None,
                None,
                nhb_p_fr_tot,
                nhb_p_fr_pm_tot,
            ],
            "Attractions": [
                nhb_a_pure_dmd_tot,
                nhb_a_pure_dmd_aj_tot,
                nhb_a_mts_dmd_tot,
                nhb_a_mts_dmd_aj_tot,
                nhb_a_fr_tot,
                nhb_a_fr_pm_tot,
            ],
        }
    )

    # Display summary tables

    print("\n\nCOMBINED SUMMARY:")
    print(combined_summary.to_string(index=False))


    # # zonal total from production from
    # prod_fr_zone_tot = hb_p_fr_pm.data.sum(axis=0)
    # prod_to_zone_tot = hb_p_to_pm.data.sum(axis=0)

    # pm_dvec = hb_p_to_pm.filter_segment_value("tp", [1,2,3], keep_filtered=True).filter_segment_value("m", 3, keep_filtered=True)
    # prod_to_zone_tot_pm = pm_dvec.data.sum(axis=0)
    # m3 = hb_p_to_pm.filter_segment_value("m",3, keep_filtered=True)
    # non_m3 = hb_p_to_pm.filter_segment_value("m", [1,2,4,5,6,7], keep_filtered=True)
    # non_m3_zone_tot = non_m3.data.sum(axis=0)
    # m3_tp_kept = m3.filter_segment_value("tp", [4,5,6], keep_filtered=True)
    # m3_tp_kept_zone_tot = m3_tp_kept.data.sum(axis=0)
    # prod_to_zone_tot_non_pm = non_m3_zone_tot + m3_tp_kept_zone_tot

    # # non_pm_dvec = non_m3.concat(m3_tp_kept)

    # # prod_to_zone_tot_non_pm = non_pm_dvec.data.sum(axis=0)
    # prod_to_sum_combined = prod_to_zone_tot_pm.sum() + prod_to_zone_tot_non_pm.sum()
    # print(f"Total from 'to' (combined): {prod_to_sum_combined:,.2f} (should match total from DVector: {hb_p_to_pm.total:,.2f})")
    # targ_zone_tot_non_pm = prod_fr_zone_tot - prod_to_zone_tot_pm
    # adj_factor_non_pm = targ_zone_tot_non_pm / prod_to_zone_tot_non_pm


    # # Create a mask for rows to EXCLUDE from factor application (m==3 AND tp in [1,2,3])
    # mask_exclude = (
    #     hb_p_to_pm.data.index.get_level_values("m") == 3
    # ) & (
    #     hb_p_to_pm.data.index.get_level_values("tp").isin([1, 2, 3])
    # )

    # # Apply factor to all rows EXCEPT the excluded ones
    # # Factor is aligned on normits_id (column level in df, index level in adj_factor_non_pm)
    # hb_p_to_pm_adj = hb_p_to_pm.copy()
    # hb_p_to_pm_adj.data.loc[~mask_exclude] = hb_p_to_pm_adj.data.loc[~mask_exclude].mul(
    #     adj_factor_non_pm, axis="columns", level="normits_id"
    # )
    # print(f"Total after adjustment: {hb_p_to_pm_adj.data.sum().sum():,.2f} (should match total from DVector: {hb_p_fr_pm.total:,.2f})")
    # pm_dvec_adj = hb_p_to_pm_adj.filter_segment_value("tp", [1,2,3], keep_filtered=True).filter_segment_value("m", 3, keep_filtered=True)
    # prod_to_zone_tot_pm_adj = pm_dvec_adj.data.sum(axis=0)

    # # compare the adjusted pm part to the original pm part to confirm it has not changed
    # per_diff_pm = (prod_to_zone_tot_pm_adj - prod_to_zone_tot_pm) / prod_to_zone_tot_pm * 100
    # print(f"Percentage difference in PM part after adjustment (should be 0%): {per_diff_pm.sum():.6f}%")


    def get_zone_totals(dvec):
        """Get zone totals from a DVector, handling both single and composite zoning."""
        # Sum across all segments (rows) to get totals for each zone (column)
        return dvec.data.sum(axis=0)


    # Get zone totals for each DVector
    print("\n" + "=" * 60)
    print("CALCULATING ZONE TOTALS:")
    print("=" * 60)

    productions_pure_dmd_zones = get_zone_totals(hb_p_pure_dmd)
    productions_pure_dmd_adj_zones = get_zone_totals(hb_p_pure_dmd_aj)
    productions_mts_dmd_zones = get_zone_totals(hb_p_mts_dmd)
    productions_mts_dmd_adj_zones = get_zone_totals(hb_p_mts_dmd_aj)
    productions_fr_zones = get_zone_totals(hb_p_fr)
    productions_fr_pm_zones = get_zone_totals(hb_p_fr_pm)
    productions_to_zones = get_zone_totals(hb_p_to)
    productions_to_pm_zones = get_zone_totals(hb_p_to_pm)

    attractions_pure_dmd_zones = get_zone_totals(hb_a_pure_dmd)
    attractions_pure_dmd_adj_zones = get_zone_totals(hb_a_pure_dmd_aj)
    attractions_mts_dmd_zones = get_zone_totals(hb_a_mts_dmd)
    attractions_mts_dmd_adj_zones = get_zone_totals(hb_a_mts_dmd_aj)
    attractions_fr_zones = get_zone_totals(hb_a_fr)
    attractions_fr_pm_zones = get_zone_totals(hb_a_fr_pm)
    attractions_to_zones = get_zone_totals(hb_a_to)
    attractions_to_pm_zones = get_zone_totals(hb_a_to_pm)

    print("Zone totals calculated successfully.")


    # Compare productions fr and to
    print("\n" + "=" * 60)
    print("COMPARING PRODUCTIONS FR AND TO:")
    print("=" * 60)


    def get_zone_code(idx):
        """Extract the actual zone ID — usually the last (or 4th) element if tuple"""
        if isinstance(idx, tuple):
            # Most likely case: last element is the zone code
            code = idx[-1]
        else:
            code = idx

        # Convert to int — fail loudly if impossible
        try:
            return int(code)
        except (ValueError, TypeError) as e:
            print(f"Cannot convert to int: {idx!r} → {code!r}")
            raise e


    # ────────────────────────────────
    # FR side: map to zone code + aggregate duplicates
    # ────────────────────────────────
    p_fr_clean = pd.Series(
        data=productions_fr_pm_zones.values,
        index=productions_fr_pm_zones.index.map(get_zone_code),
    )
    # Important: sum values that map to the same zone code
    p_fr_by_zone = p_fr_clean.groupby(p_fr_clean.index).sum().reset_index()
    p_fr_by_zone.columns = ["normits_id", "fr_value"]  # rename for clarity

    # ────────────────────────────────
    # TO side: usually already flat integers, but make sure
    # ────────────────────────────────
    p_to_clean = pd.Series(
        data=productions_to_pm_zones.values,
        index=productions_to_pm_zones.index.map(get_zone_code),
    )
    # Important: sum values that map to the same zone code
    p_to_by_zone = p_to_clean.groupby(p_to_clean.index).sum().reset_index()
    p_to_by_zone.columns = ["normits_id", "to_value"]

    # ── Merge the two DataFrames on normits_id ─────────────────────────
    prod_comp_df = pd.merge(
        p_fr_by_zone,
        p_to_by_zone,
        on="normits_id",
        how="outer",  # keep all zones from both sides
    ).fillna(0)


    prod_comp_df["difference"] = prod_comp_df["to_value"] - prod_comp_df["fr_value"]
    prod_comp_df["perc_diff"] = 0.0
    mask = prod_comp_df["fr_value"] != 0
    prod_comp_df.loc[mask, "perc_diff"] = (
        prod_comp_df.loc[mask, "difference"] / prod_comp_df.loc[mask, "fr_value"]
    ) * 100
    mask_inf = (prod_comp_df["fr_value"] == 0) & (prod_comp_df["to_value"] != 0)
    prod_comp_df.loc[mask_inf, "perc_diff"] = float("inf")
    count_prod = (abs(prod_comp_df["perc_diff"]) > 0.1).sum()
    print(prod_comp_df)
    print(f"\nNumber of zones with percentage difference above 0.1%: {count_prod}")

    # Compare attractions fr and to
    print("\n" + "=" * 60)
    print("COMPARING ATTRACTIONS FR AND TO:")
    print("=" * 60)

    # ────────────────────────────────
    # FR side: map to zone code + aggregate duplicates
    # ────────────────────────────────
    a_fr_clean = pd.Series(
        data=attractions_fr_pm_zones.values,
        index=attractions_fr_pm_zones.index.map(get_zone_code),
    )

    # Important: sum values that map to the same zone code
    a_fr_by_zone = a_fr_clean.groupby(a_fr_clean.index).sum().reset_index()
    a_fr_by_zone.columns = ["normits_id", "fr_value"]  # rename for clarity

    # ────────────────────────────────
    # TO side: usually already flat integers, but make sure
    # ────────────────────────────────
    a_to_clean = pd.Series(
        data=attractions_to_pm_zones.values,
        index=attractions_to_pm_zones.index.map(get_zone_code),
    )

    a_to_by_zone = a_to_clean.groupby(a_to_clean.index).sum().reset_index()
    a_to_by_zone.columns = ["normits_id", "to_value"]


    # ── Merge the two DataFrames on normits_id ─────────────────────────
    attr_comp_df = pd.merge(
        a_fr_by_zone,
        a_to_by_zone,
        on="normits_id",
        how="outer",  # keep all zones from both sides
    ).fillna(0)

    attr_comp_df["difference"] = attr_comp_df["to_value"] - attr_comp_df["fr_value"]

    attr_comp_df["perc_diff"] = 0.0
    mask = attr_comp_df["fr_value"] != 0
    attr_comp_df.loc[mask, "perc_diff"] = (
        attr_comp_df.loc[mask, "difference"] / attr_comp_df.loc[mask, "fr_value"]
    ) * 100
    mask_inf = (attr_comp_df["fr_value"] == 0) & (attr_comp_df["to_value"] != 0)
    attr_comp_df.loc[mask_inf, "perc_diff"] = float("inf")
    count_attr = (abs(attr_comp_df["perc_diff"]) > 0.1).sum()
    print(attr_comp_df)
    print(f"\nNumber of zones with percentage difference above 0.1%: {count_attr}")

    # Create export directory
    export_path = output_path / "csv_exports"
    export_path.mkdir(exist_ok=True)


    # Export summary tables to CSV

    combined_summary.to_csv(export_path / "summary_combined_2023.csv", index=False)

    nhb_combined_summary.to_csv(export_path / "summary_nhb_combined_2023.csv", index=False)

    # Export zone totals to separate CSV files
    productions_pure_dmd_zones.to_csv(
        export_path / "zone_totals_productions_pure_demand.csv"
    )
    productions_pure_dmd_adj_zones.to_csv(
        export_path / "zone_totals_productions_pure_demand_adj.csv"
    )
    productions_mts_dmd_zones.to_csv(export_path / "zone_totals_productions_mts_demand.csv")
    productions_mts_dmd_adj_zones.to_csv(
        export_path / "zone_totals_productions_mts_demand_adj.csv"
    )
    productions_fr_zones.to_csv(export_path / "zone_totals_productions_from.csv")
    productions_to_zones.to_csv(export_path / "zone_totals_productions_to.csv")

    attractions_pure_dmd_zones.to_csv(
        export_path / "zone_totals_attractions_pure_demand.csv"
    )
    attractions_pure_dmd_adj_zones.to_csv(
        export_path / "zone_totals_attractions_pure_demand_adj.csv"
    )
    attractions_mts_dmd_zones.to_csv(export_path / "zone_totals_attractions_mts_demand.csv")
    attractions_mts_dmd_adj_zones.to_csv(
        export_path / "zone_totals_attractions_mts_demand_adj.csv"
    )
    attractions_fr_zones.to_csv(export_path / "zone_totals_attractions_from.csv")
    attractions_to_zones.to_csv(export_path / "zone_totals_attractions_to.csv")

    # Export comparison tables
    prod_comp_df.to_csv(export_path / "productions_fr_to_comparison.csv", index=False)
    attr_comp_df.to_csv(export_path / "attractions_fr_to_comparison.csv", index=False)

    print("\n" + "=" * 60)
    print("CSV FILES EXPORTED TO:", export_path)
    print("=" * 60)

    # print("\nDetailed Data Files:")
    # print("  - hb_productions_from_2023.csv")
    # print("  - hb_productions_to_2023.csv")
    # print("  - hb_attractions_from_2023.csv")
    # print("  - hb_attractions_to_2023.csv")

    print("\nSummary Files:")
    print("  - summary_productions_2023.csv")
    print("  - summary_attractions_2023.csv")
    print("  - summary_combined_2023.csv")

    print("\nZone Total Files (Productions):")
    print("  - zone_totals_productions_pure_demand.csv")
    print("  - zone_totals_productions_pure_demand_adj.csv")
    print("  - zone_totals_productions_mts_demand.csv")
    print("  - zone_totals_productions_mts_demand_adj.csv")
    print("  - zone_totals_productions_from.csv")
    print("  - zone_totals_productions_to.csv")

    print("\nZone Total Files (Attractions):")
    print("  - zone_totals_attractions_pure_demand.csv")
    print("  - zone_totals_attractions_pure_demand_adj.csv")
    print("  - zone_totals_attractions_mts_demand.csv")
    print("  - zone_totals_attractions_mts_demand_adj.csv")
    print("  - zone_totals_attractions_from.csv")
    print("  - zone_totals_attractions_to.csv")

    print("\n" + "=" * 60)
    print("EXPORT COMPLETE!")
    print("=" * 60)
