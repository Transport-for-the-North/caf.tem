# -*- coding: utf-8 -*-
"""
Utility functions and constants for the Trip End Model (TEM).

This module provides helper functions for data transformation, file I/O, report writing,
and DVector/segmentation operations used throughout the TEM framework.
"""

from __future__ import annotations

# Built-Ins
import copy
import gc
import logging

# Built-in
import math
import warnings
from typing import TYPE_CHECKING, Generic, Sequence, TypeVar

# Third Party
# Local
import caf.base as cb
from caf.base.segmentation import SegmentationError, SegmentationWarning

# Third-party
from caf.base.segments import SegmentsSuper

# Local Imports
from caf.tem.inputs import SharedParamsProto

if TYPE_CHECKING:
    # Local Imports
    from caf.tem.attraction_models import AttractionModel
    from caf.tem.production_models import HBProductionModel


# # # CONSTANTS # # #
_TT_ENUM = ["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"]
TT = cb.SegmentationInput(
    enum_segments=[SegmentsSuper(i) for i in _TT_ENUM],
    naming_order=_TT_ENUM,
)

_LAD_SEG = ["p", "m", "tp"]
LAD_REPORT_SEG: cb.SegmentationInput = cb.SegmentationInput(
    enum_segments=[SegmentsSuper(i) for i in _LAD_SEG],
    naming_order=_LAD_SEG,
    subsets={"tp": [1, 2, 3, 4, 5, 6]},
)

PARAMS = TypeVar("PARAMS", bound=SharedParamsProto)

LOG = logging.getLogger(__name__)

# # # CLASSES # # #


# # # FUNCTIONS # # #
def lu_to_tt(dvec: cb.DVector) -> cb.DVector:
    """
    Convert a land-use segmented DVector to a travel-type segmented DVector.

    This function aggregates and transforms the input DVector to match the segmentation
    required for travel-type modelling. It checks for conservation of totals and warns
    if the sum changes.

    Parameters
    ----------
    dvec : cb.DVector
        The input DVector containing land-use-based segmentation.

    Returns
    -------
    cb.DVector
        A new DVector segmented and aggregated for travel-type modelling.

    """
    out_dvec = dvec.aggregate(
        [
            "age_9",
            "g",
            "ns_sec",
            "soc",
            "pop_emp",
            "adults",
            "adult_nssec",
            "car_availability",
        ]
    )
    out_dvec = out_dvec.trans_seg_from_lookup("ag_g")
    out_dvec = out_dvec.trans_seg_from_lookup("apopemp_aws", drop_old=True)

    out_dvec = out_dvec.add_segments(["hh_type"]).aggregate(
        ["adult_nssec", "gender_3", "ns_sec", "soc", "aws", "hh_type"]
    )

    if not math.isclose(out_dvec.sum(), dvec.sum()):
        warnings.warn(
            f"The total has changed during conversion. Sum before = {dvec.sum()}, "
            f"sum after = {out_dvec.sum()}."
        )

    return out_dvec


def write_reports(dvec: cb.DVector, report_path, year: int) -> None:
    """
    Write sector and LAD reports for a DVector.

    Calls the DVector's write_sector_reports() method to generate and save reports
    for the specified year and report path.

    Parameters
    ----------
    dvec : cb.DVector
        The DVector to report on.
    report_path : object
        Object containing paths for various report types (must have .segment_total, .ca_sector,
        .ie_sector, .lad_report attributes, each indexed by year).
    year : int
        The year for which to write reports.

    Returns
    -------
    None
    """
    dvec.write_sector_reports(
        segment_totals_path=report_path.segment_total[year],
        ca_sector_path=report_path.ca_sector[year],
        ie_sector_path=report_path.ie_sector[year],
        lad_report_path=report_path.lad_report[year],
        lad_report_seg=cb.Segmentation(LAD_REPORT_SEG),
    )


def filter_segments(custom_seg_list, df) -> list:
    """
    Filter segment objects by keeping only values present in a DataFrame.

    Parameters
    ----------
    custom_seg_list : list
        List of segment objects (each having .name and .values attributes).
    df : pd.DataFrame
        DataFrame to filter categories against.

    Returns
    -------
    list
        List of filtered segment copies.
    """
    filtered_seg_list = []
    for seg in custom_seg_list:
        seg_copy = copy.deepcopy(seg)
        col_name = seg_copy.name
        seg_unique = set(df[col_name].unique())
        seg_copy.values = {i: j for i, j in seg_copy.values.items() if i in seg_unique}
        filtered_seg_list.append(seg_copy)

    return filtered_seg_list


class SharedProdAttrMethods(Generic[PARAMS]):
    """Class for methods shared between production and attraction models."""

    def __init__(self, params: PARAMS, tem_segmentation: cb.Segmentation):
        self.params: PARAMS = params
        self.tem_segmentation = tem_segmentation

    def _read_mts_return_home(self, mts_segs: list[str]) -> cb.DVector:
        """
        Read the mode-time split DVector for return-home trips and normalize it.

        Parameters
        ----------
        mts_segs : list[str]
            Segments to normalize over.

        Returns
        -------
        cb.DVector
            Normalized mode-time splits reshaped by tfn_at.
        """
        # Load the raw DVector
        LOG.info(f"Loading return home mode time splits from {self.params.mts_return}.")
        if self.params.mts_return is None:
            raise TypeError("MTS return_home must be provided.")
        trips: cb.DVector = cb.DVector.load(self.params.mts_return)
        full_seg = trips.segmentation.naming_order
        agg_segs = [i for i in full_seg if i not in mts_segs]

        mts = trips / trips.aggregate(agg_segs)
        return mts

    def _read_phi_factor_dvec(self, p: int, log: bool = True):
        """
        Read a phi factor DVector file for the given purpose segment.

        Parameters
        ----------
        p : int
            Purpose segment value (e.g., 1 to 8).

        Returns
        -------
        cb.DVector
            Loaded phi factor DVector.

        Raises
        ------
        FileNotFoundError
            If the phi factor file does not exist.
        """
        if self.params.phi_factors is None:
            raise TypeError("A path to phi_factors must be provided for return home trips.")
        phi_factors_file_path = self.params.phi_factors / f"phi_factors_P_p{p}_reg_phi.dvec"
        if log:
            LOG.info(f"Loading phi factors from {phi_factors_file_path}")

        if not phi_factors_file_path.exists():
            raise FileNotFoundError(
                f"[ERROR] Phi factor file not found: {phi_factors_file_path}"
            )

        phi_factor = cb.DVector.load(phi_factors_file_path)
        return phi_factor

    def _adjust_mts_return_home(
        self,
        mts: cb.DVector,
        adj_factors: cb.DVector | None = None,
        geo_constraint: cb.ZoningSystem | None = None,
    ) -> cb.DVector:
        """
        Adjust MTS for return-home trips using adjustment factors.

        Parameters
        ----------
        mts : cb.DVector
            MTS vector for return-home trips.
        adj_factors : cb.DVector or None
            Adjustment factors.
        geo_constraint : cb.ZoningSystem, optional
            Zoning system for constraining adjustment.

        Returns
        -------
        cb.DVector
            Adjusted MTS vector for return-home trips.
        """
        if adj_factors is None:
            return mts
        agg_seg = [
            i
            for i in mts.segmentation.naming_order
            if i not in ["m", "tp", "tp_return", "m_return"]
        ]
        LOG.info(" Adjusting mode time split")
        adj_factors.fill(0, 1)
        adj = mts * adj_factors

        numerator = mts.aggregate(agg_seg)
        denominator = adj.aggregate(agg_seg)
        if geo_constraint is not None:
            if isinstance(mts.zoning_system, Sequence):
                if geo_constraint not in mts.zoning_system:
                    raise ValueError("Geo constraint must be contained in the zoning system")
            else:
                raise TypeError("For a geo_constraint to work, there must be multi-zoning.")
            numerator = numerator.aggregate_comp_zones(geo_constraint)
            denominator = denominator.aggregate_comp_zones(geo_constraint)
        adj = adj * (numerator / denominator)
        mts_adj = adj

        return mts_adj

    def return_home_trip_ends(self, tem_fr: cb.DVector, agg_segments: list[str]):
        """
        Compute return-home trip ends.

        Applies phi factors to filtered production vectors, then aggregates over
        the specified segment groups.

        Parameters
        ----------
        tem_fr : cb.DVector
            The attraction DVector containing 'p' as a segment.

        agg_segments : list[str]
            List of segment names to aggregate over (e.g., ['p_return', 'tp_return']).

        Returns
        -------
        cb.DVector
            Aggregated return-home trip ends across all purpose segments.
        """
        trip_ends = None

        for p_val in range(1, 9):
            # Load phi factor for this purpose
            phi = self._read_phi_factor_dvec(p_val)

            # Filter production DVector by current purpose value, keep 'p' segment
            tem_filtered = tem_fr.filter_segment_value("p", p_val, keep_filtered=True)

            # Multiply and aggregate
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SegmentationWarning)
                result = tem_filtered * phi
            result = result.aggregate(segs=agg_segments)

            # Accumulate results
            if trip_ends is None:
                trip_ends = result
            else:
                trip_ends += result

            # Clean up memory
            del phi, tem_filtered, result
            gc.collect()

        return trip_ends

    def _read_mts_return_home_adjustment(self):
        """
        Read MTS adjustment factors for return-home trips.

        Returns
        -------
        cb.DVector or None
            Adjustment factors or None if not provided.
        """
        if self.params.mts_return_adj is None:
            return None

        adj_factors = cb.DVector.load(self.params.mts_return_adj)

        return adj_factors

    def create_tem_return_home(self, tem: cb.DVector, geo_constraint: cb.ZoningSystem | None):
        """
        Create TEM-segmented return-home vector.

        Parameters
        ----------
        tem : cb.DVector
            TEM-segmented vector.

        Returns
        -------
        cb.DVector
            Adjusted return-home vector.
        """
        LOG.info("Processing return home trips")

        # Reading one Phi factor Dvec to get its segmentation
        phi_segmentation = self._read_phi_factor_dvec(1, log=False).segmentation.naming_order

        aggregation_segments = list(
            s
            for s in (set(self.tem_segmentation) ^ set(phi_segmentation))
            if s
            not in {
                "m",
                "tp",
            }
        )

        tem_return_home_tripends = self.return_home_trip_ends(tem, aggregation_segments)
        mts_segs = [
            i
            for i in ["m", "tp_return"]
            if i not in tem_return_home_tripends.segmentation.names
        ]
        if len(mts_segs) > 0:
            mts_return_home = self._read_mts_return_home(mts_segs)

            # Check if 'tp_return' exists in either segmentation
            tp_in_tem = "tp_return" in tem.segmentation.naming_order
            tp_in_mts = "tp_return" in mts_return_home.segmentation.naming_order

            if not (tp_in_tem or tp_in_mts):
                raise SegmentationError(
                    "Segment 'tp_return' (Return Time Period) must be present in either the phi factor DVector or the mode-time split DVector."
                )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=SegmentationWarning)
                tem_return_home_tripends_mts = tem_return_home_tripends * mts_return_home
        else:
            tem_return_home_tripends_mts = tem_return_home_tripends
        mts_return_home_adj = self._read_mts_return_home_adjustment()

        tem_return_home_tripends_adj = self._adjust_mts_return_home(
            mts=tem_return_home_tripends_mts,
            adj_factors=mts_return_home_adj,
            geo_constraint=geo_constraint,
        )

        return tem_return_home_tripends_adj
