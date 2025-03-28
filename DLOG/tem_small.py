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
                2035: input_dir / "dlog_tt_pop_2035_small.dvec",
                2045: input_dir / "dlog_tt_pop_2045_small.dvec",
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
        
    def hb_attr(self, input_dir):
        self.hb_attracttion_model = self.tem_model.HBAttractionModel(
            trip_rates_paths={
                1: input_dir / "trip_rates_p1.hdf",
                2: input_dir / "trip_rates_p2.hdf",
                3: input_dir / "trip_rates_p3.hdf",
                4: input_dir / "trip_rates_p4.hdf",
                5: input_dir / "trip_rates_p5.hdf",
                6: input_dir / "trip_rates_p6.hdf",
                7: input_dir / "trip_rates_p7.hdf",
                8: input_dir / "trip_rates_p8.hdf"
                },
            emp_landuse_paths = {2024: input_dir / "dlog_soc_sic_emp_2024_small.dvec",
                                 2025: input_dir / "dlog_soc_sic_emp_2025_small.dvec",
                                 2035: input_dir / "dlog_soc_sic_emp_2035_small.dvec",
                                 2045: input_dir / "dlog_soc_sic_emp_2045_small.dvec"}, 
            hh_landuse_dirs = {2024: input_dir / "dlog_hh_2024_small.dvec",
                               2025: input_dir / "dlog_hh_2025_small.dvec",
                               2035: input_dir / "dlog_hh_2035_small.dvec",
                               2045: input_dir / "dlog_hh_2045_small.dvec"}, 
            hh_landuse_prefix = "dlog_hh", 
            mode_time_splits_path=input_dir / "mode_time_split_attraction_hb_fr_reg.hdf",
            balance_production=True,
            trip_rate_adjustment_path=input_dir / "trip_rate_adjustments_attractions_hb_fr.hdf",
            emp_translation_path=None,
            hh_translation_path=None,
            mode_time_splits_adjustment_path=input_dir / "mode_time_split_adjustments.hdf"
            )
        
        return self.hb_attracttion_model

    def run_hb_attracttion_model(self):
        if self.hb_attracttion_model:
            self.hb_attracttion_model.run()
            return self.hb_attracttion_model
        else:
            raise RuntimeError("HB Attraction Model is not set up.")
        
    def nhb_prod(self, input_dir):
        self.nhb_production_model = self.tem_model.NHBProductionModel(
            trip_rates_path= input_dir / "nhb_trip_rates_production.hdf",
            mode_time_splits_path= input_dir / "mts_fixed.dvec"
            )
        
        return self.nhb_production_model

    def run_nhb_production_model(self):
        if self.nhb_production_model:
            self.nhb_production_model.run()
            return self.nhb_production_model
        else:
            raise RuntimeError("NHB Production Model is not set up.")

class TEMProcessing:
    def __init__(self, hb_model, export_home):
        self.hb_model = hb_model
        self.export_home = export_home

    def process_output(self):
        years = [2024, 2025, 2035, 2045] 

        file_template = "nhb_normits_tem_segmented_{}_dvec.h5"
        
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

        combined_file_path = os.path.join(self.export_home, "nhb_normits_tem_segmented_small_prod.csv.bz2")
        combined_df.to_csv(combined_file_path, index=False, compression='bz2')

        print(f"Processed data saved to {combined_file_path}")


if __name__ == "__main__":

    tem = TEM(
        model_years=[2024, 2025, 2035, 2045],
        scenario="Core",
        output_zoning="normits",
        iteration_name="27032025_small",
        export_home=r"T:\Yan_Kavana\TEM DLOG\Outputs",
        return_segmentation=["p", "m", "tp", "hh_type"]
    )

    input_dir_prod = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")
    input_dir_attr = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction")
    input_dir_prod_nhb = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\03-NHBProduction")

    # hb_production_model = tem.hb_prod(input_dir_prod)
    # tem.run_hb_production_model()

    hb_attraction_model = tem.hb_attr(input_dir_attr)
    tem.run_hb_attracttion_model()

    nhb_production_model = tem.nhb_prod(input_dir_prod_nhb)
    tem.run_nhb_production_model()
  
    output = Path(r"T:\Yan_Kavana\TEM DLOG\Outputs\27032025_small\Core")

    out_prod = output / "hb_productions"
    out_attr = output / "hb_attractions"
    out_prod_nhb = output / "nhb_productions"

    # tem_processing = TEMProcessing(hb_production_model, output)
    # tem_processing.process_output()

    tem_processing = TEMProcessing(nhb_production_model, out_prod_nhb)
    tem_processing.process_output()