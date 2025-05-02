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

    def hb_prod(self, input_dir, population_paths):
        self.hb_production_model = self.tem_model.HBProductionModel(
            population_paths=population_paths,
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
        
    def hb_attr(self, input_dir, emp_landuse_paths, hh_landuse_dirs):
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
            emp_landuse_paths=emp_landuse_paths,
            hh_landuse_dirs=hh_landuse_dirs,
            hh_landuse_prefix="dlog_hh", 
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
        
    def nhb_attr(self, input_dir, emp_landuse_paths, hh_landuse_dirs):
        self.nhb_attracttion_model = self.tem_model.NHBAttractionModel(
            trip_rates_paths={
                    11: input_dir / "nhb_attraction_triprates_p11.dvec",
                    12: input_dir / "nhb_attraction_triprates_p12.dvec",
                    13: input_dir / "nhb_attraction_triprates_p13.dvec",
                    14: input_dir / "nhb_attraction_triprates_p14.dvec",
                    15: input_dir / "nhb_attraction_triprates_p15.dvec",
                    16: input_dir / "nhb_attraction_triprates_p16.dvec",
                    18: input_dir / "nhb_attraction_triprates_p18.dvec"},
            emp_landuse_paths=emp_landuse_paths,
            hh_landuse_dirs=hh_landuse_dirs,
            hh_landuse_prefix="dlog_hh", 
            nhb_mode_time_splits_path=input_dir / "nhb_mode_time_split_attraction.dvec",
            balance_production=True
            )
        
        return self.nhb_attracttion_model
    
    def run_nhb_attracttion_model(self):
        if self.nhb_attracttion_model:
            self.nhb_attracttion_model.run()
            return self.nhb_attracttion_model
        else:
            raise RuntimeError("NHB Attraction Model is not set up.")
        
class TEMProcessing:
    def __init__(self, hb_model, export_home):
        self.hb_model = hb_model
        self.export_home = export_home

    def process_output_hb(self, model, years):
        file_template = "hb_normits_tem_segmented_{}_dvec.h5"
        
        processed_dataframes = []

        for year in years:
            file_path = os.path.join(self.export_home, file_template.format(year))

            df = pd.read_hdf(file_path, key="data")

            df.reset_index(inplace=True)

            df = df[~df['tp'].isin([5, 6])]
            df = df[df['m'] != 7]
            df['m'] = df['m'].replace(4, 3)
            df = df.drop(columns=['hh_type' , 'tp'])

            df = df.groupby(['p', 'm']).sum().reset_index()

            id_vars = ['p', 'm']
            value_vars = [col for col in df.columns if col not in id_vars]
            df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='zone', value_name='value')
            df['value'] = df['value']/5

            df['year'] = year

            processed_dataframes.append(df)

        combined_df = pd.concat(processed_dataframes, axis=0)

        combined_df = combined_df.pivot_table(index=['zone', 'p', 'm'], columns='year', values='value').reset_index()

        combined_file_path = os.path.join(self.export_home, f"{model}_hb_normits_tem_segmented.csv")
        combined_df.to_csv(combined_file_path, index=False)

        print(f"Processed data saved to {combined_file_path}")

    def process_output_nhb(self, model, years):
        file_template = "nhb_normits_tem_segmented_{}_dvec.h5"
        
        processed_dataframes = []

        for year in years:
            file_path = os.path.join(self.export_home, file_template.format(year))

            df = pd.read_hdf(file_path, key="data")

            df.reset_index(inplace=True)

            df = df[~df['tp'].isin([5, 6])]
            df = df[df['m'] != 7]
            df['m'] = df['m'].replace(4, 3)
            df = df.drop(columns=['hh_type' , 'tp'])

            df = df.groupby(['p', 'm']).sum().reset_index()

            id_vars = ['p', 'm']
            value_vars = [col for col in df.columns if col not in id_vars]
            df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='zone', value_name='value')
            df['value'] = df['value']/5

            df['year'] = year

            processed_dataframes.append(df)

        combined_df = pd.concat(processed_dataframes, axis=0)

        combined_df = combined_df.pivot_table(index=['zone', 'p', 'm'], columns='year', values='value').reset_index()

        combined_file_path = os.path.join(self.export_home, f"{model}_nhb_normits_tem_segmented.csv")
        combined_df.to_csv(combined_file_path, index=False)

        print(f"Processed data saved to {combined_file_path}")

if __name__ == "__main__":
    scenarios = {
        "All": {
            "model_years": [2023],
            "iteration_name": "01052025_All",
            "population_paths": {2023: "dlog_tt_pop_2023.dvec"},
            "emp_landuse_paths": {2023: "dlog_soc_sic_emp_2023.dvec"},
            "hh_landuse_dirs": {2023: "dlog_hh_2023.dvec"},
            "years": [2023]
        },
        "Large": {
            "model_years": [2023],
            "iteration_name": "01052025_Large",
            "population_paths": {2023: "dlog_tt_pop_2023_large.dvec"},
            "emp_landuse_paths": {2023: "dlog_soc_sic_emp_2023_large.dvec"},
            "hh_landuse_dirs": {2023: "dlog_hh_2023_large.dvec"},
            "years": [2023]
        }
    }

    for scenario_name, config in scenarios.items():
        tem = TEM(
            model_years=config["model_years"],
            scenario="dlog",
            output_zoning="normits",
            iteration_name=config["iteration_name"],
            export_home=r"T:\Yan_Kavana\TEM DLOG\Outputs",
            return_segmentation=["p", "m", "tp", "hh_type"]
        )

        input_dir_prod = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\01-HBProduction")
        input_dir_attr = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\02-HBAttraction")
        input_dir_prod_nhb = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\03-NHBProduction")
        input_dir_attr_nhb = Path(r"T:\ThomasPrince\TEM I-Drive Comparison\Inputs\04_NHBAttractionModel")

        dlog_pop = Path(r"I:\Data\D-Log\DLIT\Outputs\Test18_DLog24_v0.15_rnn\05_normits\dlog_tt_pop\tt_pop")
        dlog_soc_sic = Path(r"I:\Data\D-Log\DLIT\Outputs\Test18_DLog24_v0.15_rnn\05_normits\dlog_soc_sic_emp\soc_sic_emp")
        dlog_hh = Path(r"I:\Data\D-Log\DLIT\Outputs\Test18_DLog24_v0.15_rnn\05_normits\dlog_hh\hh")

        # Update paths with full paths
        population_paths = {year: dlog_pop / path for year, path in config["population_paths"].items()}
        emp_landuse_paths = {year: dlog_soc_sic / path for year, path in config["emp_landuse_paths"].items()}
        hh_landuse_dirs = {year: dlog_hh / path for year, path in config["hh_landuse_dirs"].items()}

        hb_production_model = tem.hb_prod(input_dir_prod, population_paths)
        tem.run_hb_production_model()

        hb_attraction_model = tem.hb_attr(input_dir_attr, emp_landuse_paths, hh_landuse_dirs)
        tem.run_hb_attracttion_model()

        nhb_production_model = tem.nhb_prod(input_dir_prod_nhb)
        tem.run_nhb_production_model()

        nhb_attracttion_model = tem.nhb_attr(input_dir_attr_nhb, emp_landuse_paths, hh_landuse_dirs)
        tem.run_nhb_attracttion_model()
      
        output = Path(r"T:\Yan_Kavana\TEM DLOG\Outputs") / config["iteration_name"] / "dlog"

        out_prod = output / "hb_productions"
        out_attr = output / "hb_attractions"
        out_prod_nhb = output / "nhb_productions"
        out_attr_nhb = output / "nhb_attractions"

        tem_processing = TEMProcessing(hb_production_model, out_prod)
        tem_processing.process_output_hb('prod', config["years"])

        tem_processing = TEMProcessing(hb_attraction_model, out_attr)
        tem_processing.process_output_hb('attr', config["years"])

        tem_processing = TEMProcessing(nhb_production_model, out_prod_nhb)
        tem_processing.process_output_nhb('prod', config["years"])

        tem_processing = TEMProcessing(nhb_attracttion_model, out_attr_nhb)
        tem_processing.process_output_nhb('attr', config["years"])