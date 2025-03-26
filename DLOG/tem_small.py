import caf.tem as ct
from pathlib import Path
import pandas as pd
import os

class TEM:
    def __init__(self, model_years, scenario, output_zoning, iteration_name, export_home, return_segmentation):
        self.tem_model = ct.TEM(
            model_years=model_years,
            scenario=scenario,
            output_zoning=output_zoning,
            iteration_name=iteration_name,
            export_home=export_home,
            return_segmentation=return_segmentation
        )
        self.export_home = export_home
        self.iteration_name = iteration_name
        self.scenario = scenario

    def hb_prod(self, input_dir):
        self.hb_production_model = self.tem_model.HBProductionModel(
            population_paths={
                2024: input_dir / "dlog_tt_pop_2024_small.dvec",
                2025: input_dir / "dlog_tt_pop_2025_small.dvec",
                2026: input_dir / "dlog_tt_pop_2026_small.dvec",
                2027: input_dir / "dlog_tt_pop_2027_small.dvec",
                2028: input_dir / "dlog_tt_pop_2028_small.dvec",
                2029: input_dir / "dlog_tt_pop_2029_small.dvec",
                2030: input_dir / "dlog_tt_pop_2030_small.dvec",
                2031: input_dir / "dlog_tt_pop_2031_small.dvec",
                2032: input_dir / "dlog_tt_pop_2032_small.dvec",
                2033: input_dir / "dlog_tt_pop_2033_small.dvec",
                2034: input_dir / "dlog_tt_pop_2034_small.dvec",
                2035: input_dir / "dlog_tt_pop_2035_small.dvec",
                2036: input_dir / "dlog_tt_pop_2036_small.dvec",
                2037: input_dir / "dlog_tt_pop_2037_small.dvec",
                2038: input_dir / "dlog_tt_pop_2038_small.dvec",
                2039: input_dir / "dlog_tt_pop_2039_small.dvec",
                2040: input_dir / "dlog_tt_pop_2040_small.dvec",
                2041: input_dir / "dlog_tt_pop_2041_small.dvec",
                2042: input_dir / "dlog_tt_pop_2042_small.dvec",
                2043: input_dir / "dlog_tt_pop_2043_small.dvec",
                2044: input_dir / "dlog_tt_pop_2044_small.dvec",
                2045: input_dir / "dlog_tt_pop_2045_small.dvec",
                2046: input_dir / "dlog_tt_pop_2046_small.dvec",
                2047: input_dir / "dlog_tt_pop_2047_small.dvec",
                2048: input_dir / "dlog_tt_pop_2048_small.dvec",
                2049: input_dir / "dlog_tt_pop_2049_small.dvec",
                2050: input_dir / "dlog_tt_pop_2050_small.dvec",
                2051: input_dir / "dlog_tt_pop_2051_small.dvec",
                2052: input_dir / "dlog_tt_pop_2052_small.dvec",
                2053: input_dir / "dlog_tt_pop_2053_small.dvec",
                2054: input_dir / "dlog_tt_pop_2054_small.dvec",
                2055: input_dir / "dlog_tt_pop_2055_small.dvec",
                2056: input_dir / "dlog_tt_pop_2056_small.dvec",
                2057: input_dir / "dlog_tt_pop_2057_small.dvec",
                2058: input_dir / "dlog_tt_pop_2058_small.dvec",
                2059: input_dir / "dlog_tt_pop_2059_small.dvec",
                2060: input_dir / "dlog_tt_pop_2060_small.dvec",
                2061: input_dir / "dlog_tt_pop_2061_small.dvec",
                2062: input_dir / "dlog_tt_pop_2062_small.dvec",
                2063: input_dir / "dlog_tt_pop_2063_small.dvec",
                2064: input_dir / "dlog_tt_pop_2064_small.dvec",
                2065: input_dir / "dlog_tt_pop_2065_small.dvec",
                2066: input_dir / "dlog_tt_pop_2066_small.dvec",
            },
            trip_rates_path=input_dir / "triprates.dvec",
            mode_time_splits_path=input_dir / "mts.dvec",
            adjustment_path=input_dir / "trip_rate_adjustments_production_hb_fr.hdf",
            mts_adj_path=input_dir / "mode_time_split_adjustments.hdf"
        )
        return self.hb_production_model

    def run_hb_production_model(self):
        if self.hb_production_model:
            self.hb_production_model.run()
            return self.hb_production_model
        else:
            raise RuntimeError("HB Production Model is not set up.")

class TEMProcessing:
    def __init__(self, hb_production_model, export_home):
        self.hb_production_model = hb_production_model
        self.export_home = export_home

    def process_output(self):
        years = [2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036,
                2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049,
                2050, 2051, 2052, 2053, 2054, 2055, 2056, 2057, 2058, 2059, 2060, 2061, 2062,
                2063, 2064, 2065, 2066]
        
        file_template = "hb_normits_tem_segmented_{}_dvec.h5"
        
        processed_dataframes = []

        for year in years:
            file_path = os.path.join(self.export_home, file_template.format(year))

            df = pd.read_hdf(file_path, key="data")

            df.reset_index(inplace=True)
            
            df = df.drop(columns=['hh_type'])

            df = df[~df['tp'].isin([5, 6])]

            df['tp'] = df['tp'].replace([1, 2, 3, 4], 7)
            df = df.groupby(['p', 'm', 'tp']).sum().reset_index()
  
            df = df[df['m'] != 7]
 
            df['m'] = df['m'].replace(4, 3)
            df = df.groupby(['p', 'm']).sum().reset_index()
            
            df = df.drop(columns=['tp'])


            id_vars = ['p', 'm']
            value_vars = [col for col in df.columns if col not in id_vars]
            df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='zone', value_name='value')

            df['year'] = year

            processed_dataframes.append(df)

        combined_df = pd.concat(processed_dataframes, axis=0)

        combined_df = combined_df.pivot_table(index=['zone', 'p', 'm'], columns='year', values='value').reset_index()

        combined_file_path = os.path.join(self.export_home, "hb_normits_tem_segmented.csv.bz2")
        combined_df.to_csv(combined_file_path, index=False, compression='bz2')

        print(f"Processed data saved to {combined_file_path}")


if __name__ == "__main__":

    tem = TEM(
        model_years=[2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036,
                    2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049,
                    2050, 2051, 2052, 2053, 2054, 2055, 2056, 2057, 2058, 2059, 2060, 2061, 2062,
                    2063, 2064, 2065, 2066],
        scenario="Core",
        output_zoning="normits",
        iteration_name="26032025_small",
        export_home=r"T:\Yan_Kavana\TEM DLOG\Outputs",
        return_segmentation=["p", "m", "tp", "hh_type"]
    )

    input_dir = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")
    hb_production_model = tem.hb_prod(input_dir)
    tem.run_hb_production_model()

    output = r"T:\Yan_Kavana\TEM DLOG\Outputs\25032025_test_2\Core\hb_productions"

    tem_processing = TEMProcessing(hb_production_model, output)
    tem_processing.process_output()