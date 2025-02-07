# Configure the folder structure
#   Where inputs are, where outputs will go, etc.
#   Ensure folder structure exists, mkdir if not.


# Zone translation requires lsoa_id, zone_id, gor, tfn_at, lsoa_to_zone_pop, lsoa_to_zone_emp, or lsoa_to_zone.



ct.inputs.TEMSegmentations():
    prod_pure_report: cb.SegmentationInput
    prod_full_tfnat: cb.SegmentationInput
    prod_full: cb.SegmentationInput
    prod_return_seg: cb.SegmentationInput
    lad_report_seg = cb.SegmentationInput(
        enum_segments=["p", "m", "tp"],
        naming_order=["p", "m", "tp"],
        subsets={"tp": [1, 2, 3, 4, 5, 6]},
    )
    output: cb.SegmentationInput
    area_type: cb.SegmentationInput
    trip_rates: cb.SegmentationInput
    trip_weights: cb.SegmentationInput
    employment: cb.SegmentationInput
    attr_pure: cb.SegmentationInput