#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run TEM model with configuration file."""
from pathlib import Path
from caf.tem.__main__ import main

# Option A: Pass path as string
config_path = Path(r"C:\Github\NorMITs\YZ\caf.tem.yz\test_config.yml")
main(config_path)