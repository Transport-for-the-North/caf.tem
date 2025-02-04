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
    #TestProductionModels.test_HBProduction(None)
    a = ct.inputs.NHBProdInput.load_yaml(r"C:\Users\Spiral\Documents\Thomas Prince\Common Analytical Framework\caf.tem\tests\test_NHBProdInput.yaml")
    print(a)