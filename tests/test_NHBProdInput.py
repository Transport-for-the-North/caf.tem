# -*- coding: utf-8 -*-
"""Tests for the HBProduction module"""
# Built-Ins
from typing import Any

# Third Party
import pytest
from pathlib import Path
import caf.base as cb
import caf.tem as ct
import caf.toolkit as ctk
import caf.space as cs

# Local Imports
# pylint: disable=import-error,wrong-import-position

# pylint: enable=import-error,wrong-import-position

# # # CONSTANTS # # #

# # # FIXTURES # # #


# # # TESTS # # #

if __name__ == "__main__":
    trip_rate = cb.DVector.load(r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\NoTEM\NTS Output\productions\nhb\trip_rates\nhb_trip_rates_production.hdf")