## Pre- Requisits
import caf.base as cb
from pathlib import Path
import pandas as pd
import glob
import os
phi_factors_file_path = Path(os.path.join(self.phi_factors_path, f"phi_factors_P_p{purpose}_reg.dvec"))
from caf.tem.production_models import HBProductionModel

gor_02id = {
        1: "NE",
        2: "NW",
        3: "YH",
        4: "EM",
        5: "WM",
        6: "EoE",
        7: "London",
        8: "SE",
        9: "SW",
        10: "Wales",
        11: "Scotland",}
mode = {
        1: "Walk",
        2: "Cycle",
        3: "Car",
        4: "Van",
        5: "Bus",
        6: "Surface rail",
        7: "Light rail",}
p = {
        1: "Commuting",
        2: "Employer business",
        3: "Education",
        4: "Shopping",
        5: "Personal business",
        6: "Social",
        7: "Visit friends",
        8: "Holiday",
            }
hh = {
        1: "nca",
        2: "ca",
        3: "nca",
        4: "ca",
        5: "ca",
        6: "nca",
        7: "ca",
        8: "ca",
            }

hh_1 = {
        1: 1,
        2: 2,
        3: 1,
        4: 2,
        5: 2,
        6: 1,
        7: 2,
        8: 2,
            }

def phi_to_Dvec(input_fld,output_fld):
    pattern = os.path.join(input_fld, "phi_factors*_reg.csv")
    req_files = glob.glob(pattern)
    for files in req_files:
        df = pd.read_csv(files)
        df_reshaped = df.pivot_table(index=['purpose.fr', 'purpose', 'period.fr', 'period'], columns='tfn_at',
                                     values='phi', aggfunc='sum')
        df_reshaped.index.names = ['p', 'p_hb', 'tp', 'tp_return']
        filename = os.path.basename(files)
        new_filename = filename.replace('.csv', '.dvec')
        seg_inputs = cb.SegmentationInput(enum_segments=["p", "p_hb", "tp", "tp_return"],
                                          naming_order=['p', 'p_hb', 'tp', 'tp_return'])
        segmentation = cb.Segmentation(seg_inputs)
        dvec = cb.DVector(import_data=df_reshaped, segmentation=segmentation,
                          zoning_system=cb.ZoningSystem.get_zoning('tfn_at'))
        path = Path(os.path.join(output_fld, new_filename))
        dvec.save(path)


def return_home_trip_ends(return_home_dvec, type, agg_segments):
    trip_ends = None
    for p_val in range(1, 9):
        phi_file = rf"C:\Users\Kephale\Desktop\Alok\TFN\sample dvec\phi_factors_{type}_p{p_val}_reg.dvec"
        phi = cb.DVector.load(phi_file)

        return_home_dvec_filtered = return_home_dvec.filter_segment_value('p', p_val,keep_filtered = True)

        result = return_home_dvec_filtered * phi
        result = result.aggregate(segs=agg_segments)

        if trip_ends is None:
            trip_ends = result
        else:
            trip_ends += result

        del phi, return_home_dvec_filtered, result
        gc.collect


    return trip_ends

def print_nunique_values(df: pd.DataFrame) -> None:

    for col in df.columns :
        if col not in ['prod', 'attr']:
            unique_count = df[col].nunique()
            unique_value = df[col].unique()
            print(f"Column '{col}' has {unique_count} unique values.")
            print(f"Column '{col}' has {unique_value} unique values.")

def summarize_dataframe(df: pd.DataFrame, output_csv: str):
    summary = []

    for col in df.columns:

        unique_values = df[col].nunique()
        if df[col].dtype == 'object' or df[col].dtype.name == 'category' or (
                pd.api.types.is_integer_dtype(df[col]) and unique_values < 720):
            summary.append(
                {'Column': col, 'Type': 'Count of Category', 'Category': "Count of Category", 'Value': unique_values})
            category_counts = df[col].value_counts().to_dict()
            for category, count in category_counts.items():
                summary.append({'Column': col, 'Type': 'Categorical', 'Category': category, 'Value': count})
        elif pd.api.types.is_numeric_dtype(df[col]):
            total_sum = df[col].sum()
            mean = df[col].mean()
            max_ = df[col].max()
            summary.append({'Column': col, 'Type': 'Integer', 'Category': 'Sum', 'Value': total_sum})
            summary.append({'Column': col, 'Type': 'Integer', 'Category': 'mean', 'Value': mean})
            summary.append({'Column': col, 'Type': 'Integer', 'Category': 'max', 'Value': max_})

    path = rf"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\{output_csv}"
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(path, index=False)
    print(f"Summary saved to {output_csv}")
    return summary_df


def compare_dataframes(df1, df2):
    # df_1 = NHAN
    # df_2 = AJ
    unique_columns = df1["Column"].unique()
    discrepancy_list = []

    for col in unique_columns:
        # Filter both dataframes by the current column
        df1_filtered = df1[df1["Column"] == col]
        df2_filtered = df2[df2["Column"] == col]


        merged = pd.merge(df1_filtered, df2_filtered, on=["Column", "Category"], suffixes=('_Nhan', '_AJ'), how="outer")

        # Identify mismatched values
        mismatched = merged[merged["Value_Nhan"] != merged["Value_AJ"]]

        if not mismatched.empty:
            discrepancy_list.append(mismatched)

    # Concatenate all mismatches
    if discrepancy_list:
        return pd.concat(discrepancy_list, ignore_index=True)
    else:
        return pd.DataFrame(columns=["Column", "Category", "Value_Nhan", "Value_AJ"])

def _adjust_mts_production(
    mts_production: cb.DVector,
    adj_factors: cb.DVector,
    geo_constraint: cb.ZoningSystem = None,
) -> cb.DVector:

    if adj_factors is None:
        return mts_production


    adj_factors.fill(0, 1)
    adj = mts_production * adj_factors

    numerator = mts_production.aggregate(["p_return"])
    denominator = adj.aggregate(["p_return"])
    if geo_constraint is not None:
        if geo_constraint not in mts_production.zoning_system:
            raise ValueError("Geo constraint must be contained in the zoning system")
        numerator = numerator.aggregate_comp_zones(geo_constraint)
        denominator = denominator.aggregate_comp_zones(geo_constraint)
    adj = adj * (numerator / denominator)
    mts_production_adj = adj

    return mts_production_adj

mts_p_adj_factors = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\mts_p_adj_factors.csv")
mts_a_adj_factors = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\mts_a_adj_factors.csv")

mts_p_adj_factors_reshaped = mts_p_adj_factors.pivot_table(index=['purpose','mode','period'], columns='gor', values='adj', aggfunc='sum')
mts_p_adj_factors_reshaped.index.names = ['p_return','m','tp_return']
mts_a_adj_factors_reshaped = mts_a_adj_factors.pivot_table(index=['purpose','mode','period'], columns='gor', values='adj', aggfunc='sum')
mts_a_adj_factors_reshaped.index.names = ['p_return','m','tp_return']

seg_inputs = cb.SegmentationInput(enum_segments =["p_return","m","tp_return"], naming_order = ["p_return","m","tp_return"])
segmentation = cb.Segmentation(seg_inputs)

mts_p_adj_factors_dvec = cb.DVector(import_data = mts_p_adj_factors_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('gor'))
mts_a_adj_factors_dvec = cb.DVector(import_data = mts_a_adj_factors_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('gor'))
mts_p_adj_factors_dvec.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_return_home_prod_adj_factor.dvec")
mts_a_adj_factors_dvec.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_return_home_attr_adj_factor.dvec")
########################

# Converting PHI factors to DVEC

input_dir = r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\phi_factors"
pattern = os.path.join(input_dir,"phi_factors*_reg.csv")

all_files = glob.glob(pattern)

req_files = [f for f in all_files if "PA" not in os.path.basename(f)]
output_dir = r"C:\Users\Kephale\Desktop\Alok\TFN\sample dvec"

for files in req_files:

    df = pd.read_csv(files)
    df_reshaped = df.pivot_table(index=['purpose.fr', 'purpose','period.fr','period'], columns='tfn_at', values='phi', aggfunc='sum')
    df_reshaped.index.names = ['p','p_return','tp','tp_return']
    filename = os.path.basename(files)
    new_filename = filename.replace('.csv', '.dvec')
    seg_inputs = cb.SegmentationInput(enum_segments =["p","p_return","tp","tp_return"], naming_order = ['p','p_return','tp','tp_return'])
    segmentation = cb.Segmentation(seg_inputs)
    dvec = cb.DVector(import_data = df_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))
    path = Path(os.path.join(output_dir, new_filename))
    dvec.save(path)

# Calculating return home trip ends
P_dvec =cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_productions\hb_normits_tem_segmented_2023_dvec.h5")
A_dvec = cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_attractions\hb_normits_tem_segmented_2023_dvec.h5")

return_trip_ends_attraction = return_home_trip_ends(A_dvec,'A',['p_return','tp_return','hh_type','adult_nssec','soc','ns_sec'])
return_trip_ends_production = return_home_trip_ends(P_dvec,'P',['p_return','tp_return','hh_type','adult_nssec','soc','ns_sec'])


# Save
#return_trip_ends_attraction.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\attraction_return_home_phi_applied.dvec")
#return_trip_ends_production.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\production_return_home_phi_applied.dvec")


# Check
return_trip_ends_production.sum()-P_dvec.sum()
return_trip_ends_attraction.sum()-A_dvec.sum()


# Mode Split factors
mode_time_split_production = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\mode_time_splits\mode_time_split_production_hb_to_reg.csv")
mode_time_split_attraction = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\mode_time_splits\mode_time_split_attraction_hb_to_reg.csv")

# Production Mode Proportion
mode_time_split_production['total_trips'] = mode_time_split_production.groupby(['tfn_at','hh_type','purpose','period'])['trips.est'].transform('sum')
mode_time_split_production['Proportion'] = mode_time_split_production['trips.est']/mode_time_split_production['total_trips']
by_mode = mode_time_split_production.groupby(['tfn_at','hh_type','purpose','period','mode'])['Proportion'].sum().reset_index()
test_prd = by_mode.groupby(['tfn_at','hh_type','purpose','period'])['Proportion'].sum().reset_index()
by_mode_reshaped = by_mode.pivot_table(index=['hh_type','purpose','period','mode'], columns='tfn_at', values='Proportion', aggfunc='sum')
by_mode_reshaped.index.names = ['hh_type','p_return','tp_return','m']
seg_inputs = cb.SegmentationInput(enum_segments =['hh_type','p_return','tp_return','m'], naming_order = ['hh_type','p_return','tp_return','m'])
segmentation = cb.Segmentation(seg_inputs)
dvec_mode_production = cb.DVector(import_data = by_mode_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))

# Attraction Mode Proportion
mode_time_split_attraction['total_trips'] = mode_time_split_attraction.groupby(['tfn_at','purpose','period'])['trips.est'].transform('sum')
mode_time_split_attraction['Proportion'] = mode_time_split_attraction['trips.est']/mode_time_split_attraction['total_trips']
by_mode = mode_time_split_attraction.groupby(['tfn_at','purpose','period','mode'])['Proportion'].sum().reset_index()
test_attr = by_mode.groupby(['tfn_at','purpose','period'])['Proportion'].sum().reset_index()
by_mode_reshaped = by_mode.pivot_table(index=['purpose','period','mode'], columns=['tfn_at'], values='Proportion', aggfunc='sum')
by_mode_reshaped.index.names = ['p_return','tp_return','m']
seg_inputs = cb.SegmentationInput(enum_segments =['p_return','tp_return','m'], naming_order = ['p_return','tp_return','m'])
segmentation = cb.Segmentation(seg_inputs)
dvec_mode_attraction = cb.DVector(import_data = by_mode_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))


# Applied Mode Proportion
return_home_trip_ends_production_mode = return_trip_ends_production * dvec_mode_production
return_home_trip_ends_attraction_mode = return_trip_ends_attraction * dvec_mode_attraction

# Applying adjustment factors
return_home_trip_ends_production_mode_adj = _adjust_mts_production(return_home_trip_ends_production_mode,mts_p_adj_factors_dvec,cb.ZoningSystem.get_zoning('gor'))
return_home_trip_ends_attraction_mode_adj = _adjust_mts_production(return_home_trip_ends_attraction_mode,mts_a_adj_factors_dvec,cb.ZoningSystem.get_zoning('gor'))

#Save
#return_home_trip_ends_production_mode.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\production_return_home_phi_applied_with_mode_split.dvec")
#return_home_trip_ends_attraction_mode.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\attraction_return_home_phi_applied_with_mode_split.dvec")

# Check
#return_trip_ends_production.sum()-return_home_trip_ends_production_mode.sum()
#return_trip_ends_attraction.sum()-return_home_trip_ends_attraction_mode.sum()

#return_home_trip_ends_production_mode.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor')).data.sum()
#return_home_trip_ends_attraction_mode.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor')).data.sum()

#return_home_trip_ends_production_mode.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor')).data.sum() - return_trip_ends_production.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor')).data.sum()
#return_home_trip_ends_attraction_mode.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor')).data.sum() - return_trip_ends_attraction.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor')).data.sum()


#Production Aggregation
return_home_trip_ends_production_mode_ = return_home_trip_ends_production_mode_adj.aggregate(segs = ['p_return','tp_return','hh_type','m',])
P_agg_df = return_home_trip_ends_production_mode_.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))
P_agg_df = P_agg_df.data
P_agg_df_ = P_agg_df.stack().reset_index(name='Productions')
P_agg_df_['hh_type'] = P_agg_df_['hh_type'].map(hh_1)
P_agg_df_ = P_agg_df_.groupby(['p_return','tp_return','hh_type','m','gor_id'])['Productions'].sum().reset_index()

#Attractions Aggregation
return_home_trip_ends_attraction_mode_ = return_home_trip_ends_attraction_mode_adj.aggregate(segs = ['p_return','tp_return','hh_type','m',])
A_agg_df = return_home_trip_ends_attraction_mode_.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))
A_agg_df = A_agg_df.data
A_agg_df_ = A_agg_df.stack().reset_index(name='Attractions')
A_agg_df_['hh_type'] = A_agg_df_['hh_type'].map(hh_1)
A_agg_df_ = A_agg_df_.groupby(['p_return','tp_return','hh_type','m','gor_id'])['Attractions'].sum().reset_index()

merged_df = P_agg_df_.merge(A_agg_df_,on=['gor_id',  'p_return', 'm',  'tp_return','hh_type'],how='outer')



merged_df['gor_id'] = merged_df['gor_id'].map(gor_02id)
merged_df['m'] = merged_df['m'].map(mode)
merged_df['p_return'] = merged_df['p_return'].map(p)
merged_df = merged_df[['normits_id',  'p_return', 'm',  'tp_return','hh_type','Productions','Attractions']]

Nhan_output = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\NoTEM_2023_gor_raw.csv")
df_1 = merged_df.merge(Nhan_output,on=[  'gor_id',  'p_return', 'm',  'tp_return','hh_type'],how='outer')

df_1.to_csv(r'C:\Users\Kephale\Desktop\Alok\TFN\tem\output_AJ.csv',index=False)

stacked_data = return_home_trip_ends_production_mode_.data.groupby(level=["gor_id", "normits_id"], axis=1).sum()
stacked_data = stacked_data.stack(level=['gor_id','normits_id']).reset_index(name='pro')
stacked_data['hh_type'] = stacked_data['hh_type'].map(hh_1)
stacked_data = stacked_data.groupby(['hh_type', 'p_return', 'tp_return', 'm', 'gor_id', 'normits_id'])['pro'].sum().reset_index()
import pathlib
from typing import Union



# Calculation By Nhan Method

# Creating Phi Dvec
input_dir = r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method"
pattern = os.path.join(input_dir,"phi_factors*_reg.csv")

all_files = glob.glob(pattern)

req_files = [f for f in all_files if "PA" not in os.path.basename(f)]
output_dir = r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method"

for file in req_files:

    df = pd.read_csv(file)
    df = df.groupby(['purpose.fr', 'purpose','tfn_at'])['trips.est'].sum().reset_index()
    df_reshaped = df.pivot_table(index=['purpose.fr', 'purpose',], columns='tfn_at', values='trips.est', aggfunc='sum')
    df_reshaped = df_reshaped/df_reshaped.groupby('purpose.fr').sum()
    df_reshaped.index.names = ['p','p_return',]
    filename = os.path.basename(file)
    new_filename = filename.replace('.csv', '.dvec')
    seg_inputs = cb.SegmentationInput(enum_segments =["p","p_return",], naming_order = ['p','p_return',])
    segmentation = cb.Segmentation(seg_inputs)
    dvec = cb.DVector(import_data = df_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))
    path = Path(os.path.join(output_dir, new_filename))
    dvec.save(path)


# Multiplying Phi Factors
P_dvec =cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_productions\hb_normits_tem_segmented_2023_dvec.h5")
A_dvec = cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_attractions\hb_normits_tem_segmented_2023_dvec.h5")

def return_home_trip_ends_(return_home_dvec, type, agg_segments):
    trip_ends = None
    for p_val in range(1, 9):
        phi_file = rf"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\phi_factors_{type}_p{p_val}_reg.dvec"
        phi = cb.DVector.load(phi_file)

        return_home_dvec_filtered = return_home_dvec.filter_segment_value('p', p_val,keep_filtered = True)

        result = return_home_dvec_filtered * phi
        result = result.aggregate(segs=agg_segments)

        if trip_ends is None:
            trip_ends = result
        else:
            trip_ends += result

        del phi, return_home_dvec_filtered, result
        gc.collect


    return trip_ends

return_trip_ends_attraction_ = return_home_trip_ends_(A_dvec,'A',['p_return','hh_type','adult_nssec','soc','ns_sec'])
return_trip_ends_production_ = return_home_trip_ends_(P_dvec,'P',['p_return','hh_type','adult_nssec','soc','ns_sec'])

return_trip_ends_attraction_.sum()-A_dvec.sum()
return_trip_ends_production_.sum()-P_dvec.sum()

# Mode Split factors
mode_time_split_production = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\mode_time_splits\mode_time_split_production_hb_to_reg.csv")
mode_time_split_attraction = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\attractions\hb\mode_time_splits\mode_time_split_attraction_hb_to_reg.csv")

# Production Mode Proportion
by_mode_reshaped = mode_time_split_production.pivot_table(index=['hh_type','purpose','period','mode'], columns='tfn_at', values='rho', aggfunc='sum')
by_mode_reshaped.index.names = ['hh_type','p_return','tp_return','m']
seg_inputs = cb.SegmentationInput(enum_segments =['hh_type','p_return','tp_return','m'], naming_order = ['hh_type','p_return','tp_return','m'])
segmentation = cb.Segmentation(seg_inputs)
dvec_mode_production_ = cb.DVector(import_data = by_mode_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))
dvec_mode_production_.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_production_return_home.dvec")

# Attraction Mode Proportion
mode_time_split_attraction = mode_time_split_attraction.groupby(['tfn_at','purpose','mode','period'])['trips.est'].sum().reset_index()
mode_time_split_attraction['total'] = mode_time_split_attraction.groupby(['tfn_at','purpose'])['trips.est'].transform('sum')
mode_time_split_attraction['proportion'] = mode_time_split_attraction['trips.est']/mode_time_split_attraction['total']
by_mode_reshaped = mode_time_split_attraction.pivot_table(index=['purpose','period','mode'], columns='tfn_at', values='proportion', aggfunc='sum')
by_mode_reshaped.index.names = ['p_return','tp_return','m']
seg_inputs = cb.SegmentationInput(enum_segments =['p_return','tp_return','m'], naming_order = ['p_return','tp_return','m'])
segmentation = cb.Segmentation(seg_inputs)
dvec_mode_attraction_ = cb.DVector(import_data = by_mode_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))
dvec_mode_attraction_.save(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_attraction_return_home.dvec")

# Applied Mode Proportion
return_home_trip_ends_production_mode_ = return_trip_ends_production_ * dvec_mode_production_
return_home_trip_ends_attraction_mode_ = return_trip_ends_attraction_ * dvec_mode_attraction_

# Applying adjustment factors
return_home_trip_ends_production_mode_adj_ = _adjust_mts_production(return_home_trip_ends_production_mode_,mts_p_adj_factors_dvec,cb.ZoningSystem.get_zoning('gor'))
return_home_trip_ends_attraction_mode_adj_ = _adjust_mts_production(return_home_trip_ends_attraction_mode_,mts_a_adj_factors_dvec,cb.ZoningSystem.get_zoning('gor'))


return_trip_ends_attraction_.sum()-return_home_trip_ends_attraction_mode_adj_.sum()
return_trip_ends_production_.sum()-return_home_trip_ends_production_mode_adj_.sum()


#Production Aggregation
return_home_trip_ends_production_mode_1 = return_home_trip_ends_production_mode_adj_.aggregate(segs = ['p_return','tp_return','hh_type','m',])
P_agg_df_ = return_home_trip_ends_production_mode_1.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))
P_agg_df_ = P_agg_df_.data
P_agg_df_1 = P_agg_df_.stack().reset_index(name='Productions')
P_agg_df_1['hh_type'] = P_agg_df_1['hh_type'].map(hh_1)
P_agg_df_1 = P_agg_df_1.groupby(['p_return','tp_return','hh_type','m','gor_id'])['Productions'].sum().reset_index()

#Attractions Aggregation
return_home_trip_ends_attraction_mode_1 = return_home_trip_ends_attraction_mode_adj_.aggregate(segs = ['p_return','tp_return','hh_type','m',])
A_agg_df_ = return_home_trip_ends_attraction_mode_1.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))
A_agg_df_ = A_agg_df_.data
A_agg_df_1 = A_agg_df_.stack().reset_index(name='Attractions')
A_agg_df_1['hh_type'] = A_agg_df_1['hh_type'].map(hh_1)
A_agg_df_1 = A_agg_df_1.groupby(['p_return','tp_return','hh_type','m','gor_id'])['Attractions'].sum().reset_index()


merged_df_ = P_agg_df_1.merge(A_agg_df_1,on=['gor_id',  'p_return', 'm',  'tp_return','hh_type'],how='outer')


merged_df['gor_id'] = merged_df['gor_id'].map(gor_02id)
merged_df['m'] = merged_df['m'].map(mode)
merged_df['p_return'] = merged_df['p_return'].map(p)
merged_df = merged_df[['gor_id',  'p_return', 'm',  'tp_return','hh_type','Productions','Attractions']]

Nhan_output = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\NoTEM_2023_gor_raw.csv")
df = merged_df.merge(Nhan_output,on=[ 'gor_id',  'p_return', 'm',  'tp_return','hh_type'],how='outer')

df.to_csv(r'C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\output_AJ.csv',index=False)




# Checking
P_dvec =cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_productions\hb_normits_tem_segmented_2023_dvec.h5")
A_dvec = cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_attractions\hb_normits_tem_segmented_2023_dvec.h5")
#df = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\from home tripends.csv")

check_file_from_home = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\NorMITs_tripend_2023_hb_fr.csv.bz2")
# Updated data
#check_file = pd.read_hdf(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\updated data\NorMITs_tripend_2023_hb_fr.hdf")

check_file_from_home = check_file_from_home.groupby(['normits_v3.3_id', 'purpose', 'mode', 'period', 'hh_type'])[['prod', 'attr']].sum().reset_index()
check_file_from_home.rename(columns={
                                      'purpose':'p_return',
                                      'mode':'m',
                                      'period':'tp_return',
                                     'normits_v3.3_id': 'normits_id',
'prod':'prod_nhan',
'attr':'attr_nhan'},inplace=True)

cols_to_join_on = ['p_return', 'm', 'tp_return', 'hh_type', 'normits_id']

check_file_merged_fr_home = check_file_from_home.merge(
    stacked_data[['gor_id'] + cols_to_join_on],
    on=cols_to_join_on,
    how='outer'
)
check_file_merged_fr_home = check_file_merged_fr_home.groupby(['p_return', 'm', 'tp_return', 'hh_type', 'gor_id'])[['prod_nhan',
       'attr_nhan']].sum().reset_index()

Production_check = P_dvec.aggregate(segs= ['hh_type', 'p', 'm', 'tp',])
Attraction_check = A_dvec.aggregate(segs= ['hh_type', 'p', 'm', 'tp',])

Production_check_ = Production_check.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))
Attraction_check_ = Attraction_check.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))

Production_check_data = Production_check_.data
Attraction_check_data = Attraction_check_.data

Production_check_data = Production_check_data.stack().reset_index(name='prod_aj')
Attraction_check_data = Attraction_check_data.stack().reset_index(name='attr_aj')

Production_check_data['hh_type'] = Production_check_data['hh_type'].map(hh_1)
Attraction_check_data['hh_type'] = Attraction_check_data['hh_type'].map(hh_1)

Production_check_data = Production_check_data.groupby(['hh_type', 'p', 'm', 'tp','gor_id',])['prod_aj'].sum().reset_index()
Attraction_check_data = Attraction_check_data.groupby(['hh_type', 'p', 'm', 'tp','gor_id',])['attr_aj'].sum().reset_index()


Production_check_data.rename(columns={
                                      'p':'p_return',
                                      'm':'m',
                                      'tp':'tp_return',
                                      },inplace=True)


Attraction_check_data.rename(columns={
                                      'p':'p_return',
                                      'm':'m',
                                      'tp':'tp_return',
                                      },inplace=True)

merged = Production_check_data.merge(Attraction_check_data,on = [ 'hh_type', 'p_return', 'm', 'tp_return', 'gor_id'],how='outer')


merged['mode'] = merged['mode'].map(mode)
merged['purpose'] = merged['purpose'].map(p)
merged['gor'] = merged['gor'].map(gor_02id)

df_1 = merged.merge(check_file_merged_fr_home,on = [ 'hh_type', 'p_return', 'm', 'tp_return', 'gor_id'],how='outer')


df_1 = df_1[['gor','purpose','mode','hh_type','period','prod','attr','prod_nh','attr_nh']]
df_1['pro_diff'] = df_1['prod']-df_1['prod_aj']
df_1['attr_diff'] = df_1['attr']-df_1['attr_aj']
df_1['attr_diff'].describe()
df_1['prod_nh'].sum()
x = df_1.loc[df_1['attr_diff']>1]

df_2 = df_1.groupby(['purpose', 'mode', 'period'])[['prod_aj',
       'attr_aj', 'prod', 'attr']].sum().reset_index()


df_2['pro_diff'] = df_2['prod']-df_2['prod_aj']
df_2['attr_diff'] = df_2['attr']-df_2['attr_aj']

df_1.to_csv(r'C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\check_from_home_tripends.csv',index=False)

DF_NHAN = summarize_dataframe(check_file, 'Summarised_ProCESS_NHAN.csv')
DF_AJ = summarize_dataframe(Production_check_data, 'Summarised_ProCESS_AJ.csv')

comparison = compare_dataframes(DF_NHAN, DF_AJ)
comparison.to_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\comp.csv",index=False)



# Testing
check_file_return_home = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\NorMITs_tripend_2023_hb_to.csv.bz2")
# update data
#check_file_return_home = pd.read_hdf(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\updated data\NorMITs_tripend_2023_hb_to.hdf")

check_file_return_home = check_file_return_home.groupby(['purpose', 'mode', 'period', 'hh_type','normits_v3.3_id'])[['prod', 'attr']].sum().reset_index()

check_file_return_home.rename(columns={
                                      'purpose':'p_return',
                                      'mode':'m',
                                      'period':'tp_return',
                                     'normits_v3.3_id': 'normits_id',
'prod':'prod_nhan',
'attr':'attr_nhan'},inplace=True)

cols_to_join_on = ['p_return', 'm', 'tp_return', 'hh_type', 'normits_id']

check_file_merged = check_file_return_home.merge(
    stacked_data[['gor_id'] + cols_to_join_on],
    on=cols_to_join_on,
    how='outer'
)
check_file_merged = check_file_merged.groupby(['p_return', 'm', 'tp_return', 'hh_type', 'gor_id'])[['prod_nhan',
       'attr_nhan']].sum().reset_index()




merged_df.rename(columns={
                                      'Productions':'prod_full_phi',
'Attractions':'attr_full_phi'},inplace=True)

#merged_df_ = merged_df_.groupby(['p_return', 'm', 'tp_return', 'hh_type'])[['Productions', 'Attractions']].sum().reset_index()
#merged_df = merged_df.groupby(['p_return', 'm', 'tp_return', 'hh_type'])[['prod_full_phi', 'attr_full_phi']].sum().reset_index()

summary = check_file_merged.merge(merged_df_,on=['p_return', 'tp_return', 'hh_type', 'm','gor_id'],how= 'outer')
summary = summary.merge(merged_df,on=['p_return', 'tp_return', 'hh_type', 'm','gor_id'],how= 'outer')
summary.to_csv(r'C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\summary.csv',index=False)

summary['diff_full_phi_prod'] = summary['prod_nhan']-summary['prod_full_phi']
summary['diff_full_phi_attr'] = summary['attr_nhan']-summary['attr_full_phi']

summary['diff_prod'] = summary['prod_nhan']-summary['Productions']
summary['diff_attr'] = summary['attr_nhan']-summary['Attractions']

summary['full phi']='Full Phi applied'
summary['Aggregated with Purpose From'] = 'Aggregated with Purpose From'
summary['Nhan']='Nhan Output'

import seaborn as sns
import matplotlib.pyplot as plt
#sns.boxplot(x='Nhan', y='prod_nhan', data=summary)
sns.boxplot(x='Aggregated with Purpose From', y='diff_prod', data=summary)
sns.boxplot(x='full phi', y='diff_full_phi_prod', data=summary)
plt.title(f'Production')
plt.xlabel("Method")
plt.ylabel("value")
plt.xticks(rotation=45)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\production.png", dpi=300)

mts = cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Inputs\mts_prod.dvec")

phi = cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\Calculation By Nhan Method\phi_factors_A_p1_reg.dvec")

######################
tem_production_to_path = r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_productions\hb_normits_tem_segmented_hb_to_2023_dvec.h5"
tem_attraction_to_path = r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_attractions\hb_normits_tem_segmented_hb_to_2023_dvec.h5"

tem_production_to = cb.DVector.load(tem_production_to_path)
tem_attraction_to = cb.DVector.load(tem_attraction_to_path)

#Production Aggregation
return_home_trip_ends_production_mode_1 = tem_production_to.aggregate(segs = ['p_return','tp_return','hh_type','m',])
P_agg_df_ = return_home_trip_ends_production_mode_1.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))
P_agg_df_ = P_agg_df_.data
P_agg_df_1 = P_agg_df_.stack().reset_index(name='Productions')
P_agg_df_1['hh_type'] = P_agg_df_1['hh_type'].map(hh_1)
P_agg_df_1 = P_agg_df_1.groupby(['p_return','tp_return','hh_type','m','gor_id'])['Productions'].sum().reset_index()

#Attractions Aggregation
return_home_trip_ends_attraction_mode_1 = tem_attraction_to.aggregate(segs = ['p_return','tp_return','hh_type','m',])
A_agg_df_ = return_home_trip_ends_attraction_mode_1.aggregate_comp_zones(cb.ZoningSystem.get_zoning('gor'))
A_agg_df_ = A_agg_df_.data
A_agg_df_1 = A_agg_df_.stack().reset_index(name='Attractions')
A_agg_df_1['hh_type'] = A_agg_df_1['hh_type'].map(hh_1)
A_agg_df_1 = A_agg_df_1.groupby(['p_return','tp_return','hh_type','m','gor_id'])['Attractions'].sum().reset_index()


merged_df_ = P_agg_df_1.merge(A_agg_df_1,on=['gor_id',  'p_return', 'm',  'tp_return','hh_type'],how='outer')

merged_df_.to_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\tem_results.csv",index=False)



















