from types import SimpleNamespace
from pathlib import Path
import importlib
import builtins

import caf.tem.__main__ as cli_mod
from caf.tem.inputs import MainConfig


def test_cli_loads_config_and_invokes_models(monkeypatch, tmp_path):
    # Prepare a fake MainConfig instance with minimal attributes used by the runner
    run_opts = SimpleNamespace(
        run_hb_prod=True,
        run_hb_attr=True,
        run_nhb_prod=True,
        run_nhb_attr=True,
        return_home=True,
    )

    fake_config = SimpleNamespace(
        model_years=[2023],
        scenario=SimpleNamespace(value="Core"),
        output_zoning=SimpleNamespace(name="model_zoning"),
        agg_zoning=SimpleNamespace(name="agg_zoning", column_name="agg_col"),
        iteration_name="it1",
        export_home=tmp_path,  # ensure this exists and is writable
        return_segmentation=SimpleNamespace(),
        trans_file=tmp_path / "trans.csv",
        run_options=run_opts,
        pop={},
        emp={},
        hh={},
        hb_prod_params=SimpleNamespace(),
        hb_attr_params=SimpleNamespace(),
        nhb_prod_params=SimpleNamespace(),
        nhb_attr_params=SimpleNamespace(),
        export_pure=True,
        export_mts=True,
        export_tem=True,
        export_reports=True,
        mts_geo_constraint=None,
    )

    # Capture calls to load_yaml
    load_args = []

    def fake_load_yaml(path_str):
        load_args.append(path_str)
        return fake_config

    monkeypatch.setattr(MainConfig, "load_yaml", staticmethod(fake_load_yaml))

    # Replace CAF TEM orchestrator with a fake that returns stubs for submodels
    created = {}

    class FakeTEM:
        def __init__(self, *args, **kwargs):
            created["inst"] = self

        def hb_production_model(self, population, params):
            self.hb_prod = SimpleNamespace()
            self.hb_prod.run = lambda *a, **k: None
            return self.hb_prod

        def attraction_model(self, emp_landuse, hh_landuse, params, origin="hb"):
            if origin == "hb":
                self.hb_attr = SimpleNamespace(); self.hb_attr.run = lambda *a, **k: None
                return self.hb_attr
            else:
                self.nhb_attr = SimpleNamespace(); self.nhb_attr.run = lambda *a, **k: None
                return self.nhb_attr

        def nhb_production_model(self, params):
            self.nhb_prod = SimpleNamespace(); self.nhb_prod.run = lambda *a, **k: None
            return self.nhb_prod

    monkeypatch.setattr(cli_mod.ct, "TEM", FakeTEM)

    # Call CLI entry with a dummy path (string)
    cli_mod.main("someconfig.yml")

    # Assertions
    assert load_args and load_args[0] == "someconfig.yml"
    inst = created.get("inst")
    assert inst is not None, "TEM instance should be created"
    assert hasattr(inst, "hb_prod"), "hb production model should have been requested"
    assert hasattr(inst, "hb_attr"), "hb attraction model should have been requested"
    assert hasattr(inst, "nhb_prod"), "nhb production model should have been requested"
    assert hasattr(inst, "nhb_attr"), "nhb attraction model should have been requested"