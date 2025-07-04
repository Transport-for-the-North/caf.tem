import caf.base as cb
from pathlib import Path
import pandas as pd
import glob
import os
import gc

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

        return_home_dvec_filtered = return_home_dvec.filter_segment_value('p', p_val)

        result = return_home_dvec_filtered * phi
        result = result.aggregate(segs=agg_segments)

        if trip_ends is None:
            trip_ends = result
        else:
            trip_ends += result

        del phi, return_home_dvec_filtered, result
        gc.collect

    return trip_ends

def mode_proportion_dvec(mode_time_split_df):
    mode_time_split_df['total_trips'] = mode_time_split_df.groupby(['tfn_at', 'hh_type', 'purpose', 'period'])[
        'trips.est'].transform('sum')

    mode_time_split_df['Proportion'] = mode_time_split_df['trips.est'] / mode_time_split_df['total_trips']

    by_mode = mode_time_split_df.groupby(['tfn_at', 'hh_type', 'purpose', 'period', 'mode'])[
        'Proportion'].sum().reset_index()

    by_mode_reshaped = by_mode.pivot_table(index=['hh_type', 'purpose', 'period', 'mode'], columns='tfn_at',
                                           values='Proportion', aggfunc='sum')

    by_mode_reshaped.index.names = ['hh_type', 'p_hb', 'tp_return', 'm']

    seg_inputs = cb.SegmentationInput(enum_segments=['hh_type', 'p_hb', 'tp_return', 'm'],
                                      naming_order=['hh_type', 'p_hb', 'tp_return', 'm'])
    segmentation = cb.Segmentation(seg_inputs)
    dvec_mode = cb.DVector(import_data=by_mode_reshaped, segmentation=segmentation,
                           zoning_system=cb.ZoningSystem.get_zoning('tfn_at'))

    return dvec_mode


# Converting PHI factors to DVEC

input_dir = r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\phi_factors"
pattern = os.path.join(input_dir,"phi_factors*_reg.csv")

all_files = glob.glob(pattern)

req_files = [f for f in all_files if "PA" not in os.path.basename(f)]
output_dir = r"C:\Users\Kephale\Desktop\Alok\TFN\sample dvec"

for files in req_files:

    df = pd.read_csv(files)
    df_reshaped = df.pivot_table(index=['purpose.fr', 'purpose','period.fr','period'], columns='tfn_at', values='phi', aggfunc='sum')
    df_reshaped.index.names = ['p','p_hb','tp','tp_return']
    filename = os.path.basename(files)
    new_filename = filename.replace('.csv', '.dvec')
    seg_inputs = cb.SegmentationInput(enum_segments =["p","p_hb","tp","tp_return"], naming_order = ['p','p_hb','tp','tp_return'])
    segmentation = cb.Segmentation(seg_inputs)
    dvec = cb.DVector(import_data = df_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))
    path = Path(os.path.join(output_dir, new_filename))
    dvec.save(path)

# Calculating return home trip ends
P_dvec =cb.DVector.load(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Outputs\full_test\Core\hb_productions\hb_normits_tem_segmented_2023_dvec.h5")

return_trip_ends_attraction = return_home_trip_ends(P_dvec,'A',['p_hb','tp_return','hh_type','adult_nssec','soc','ns_sec'])
return_trip_ends_production = return_home_trip_ends(P_dvec,'P',['p_hb','tp_return','hh_type','adult_nssec','soc','ns_sec'])


return_trip_ends_production.sum()-P_dvec.sum()
return_trip_ends_attraction.sum()-P_dvec.sum()

#P_dvec_filtered = P_dvec.filter_segment_value('p', 1)
#P_dvec_filtered.data.index
#P_dvec_filtered.sum()
#phi_file = r"C:\Users\Kephale\Desktop\Alok\TFN\sample dvec\phi_factors_P_p1_reg.dvec"
#phi = cb.DVector.load(phi_file)
#dvec = P_dvec_filtered*phi
#dvec.sum()
return_home_trip_ends = None

for p_val in range(1, 9):
    phi_file = rf"C:\Users\Kephale\Desktop\Alok\TFN\sample dvec\phi_factors_P_p{p_val}_reg.dvec"
    phi = cb.DVector.load(phi_file)

    P_dvec_filtered = P_dvec.filter_segment_value('p', p_val)

    result = P_dvec_filtered * phi
    result = result.aggregate(segs = ['p_hb','tp_return','hh_type','adult_nssec','soc','ns_sec'])

    if return_home_trip_ends is None:
        return_home_trip_ends = result
    else:
        return_home_trip_ends += result

    del phi, P_dvec_filtered, result
    gc.collect


# Mode Split factors

mode_time_split = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\NTS Processing Outputs\outputs\productions\hb\mode_time_splits\mode_time_split_production_hb_to_reg.csv")

mode_time_split['total_trips'] = mode_time_split.groupby(['tfn_at','hh_type','purpose','period'])['trips.est'].transform('sum')

mode_time_split['Proportion'] = mode_time_split['trips.est']/mode_time_split['total_trips']

by_mode = mode_time_split.groupby(['tfn_at','hh_type','purpose','period','mode'])['Proportion'].sum().reset_index()

test = by_mode.groupby(['tfn_at','hh_type','purpose','period'])['Proportion'].sum().reset_index()

by_mode_reshaped = by_mode.pivot_table(index=['hh_type','purpose','period','mode'], columns='tfn_at', values='Proportion', aggfunc='sum')

by_mode_reshaped.index.names = ['hh_type','p_hb','tp_return','m']

seg_inputs = cb.SegmentationInput(enum_segments =['hh_type','p_hb','tp_return','m'], naming_order = ['hh_type','p_hb','tp_return','m'])
segmentation = cb.Segmentation(seg_inputs)
dvec_mode = cb.DVector(import_data = by_mode_reshaped, segmentation = segmentation, zoning_system = cb.ZoningSystem.get_zoning('tfn_at'))




# Applied Mode Proportion
return_home_trip_ends_production_mode = return_trip_ends_production * dvec_mode
return_home_trip_ends_attraction_mode = return_trip_ends_attraction * dvec_mode


# Check
return_trip_ends_production.sum()-return_home_trip_ends_production_mode.sum()
return_trip_ends_attraction.sum()-return_home_trip_ends_attraction_mode.sum()



#Production
return_home_trip_ends_production_mode_ = return_home_trip_ends_production_mode.aggregate(segs = ['p_hb','tp_return','hh_type','m',])
Production = return_home_trip_ends_production_mode_.data
P_agg_df = Production.groupby(axis=1, level=1).sum()
P_agg_df_ = P_agg_df.stack().reset_index(name='Productions')
P_agg_df_['hh_type'] = P_agg_df_['hh_type'].map(hh)
P_agg_df_ = P_agg_df_.groupby(['p_hb','tp_return','hh_type','m','gor_id'])['Productions'].sum().reset_index()


#Attractions
return_home_trip_ends_attraction_mode_ = return_home_trip_ends_attraction_mode.aggregate(segs = ['p_hb','tp_return','hh_type','m',])
Attraction = return_home_trip_ends_attraction_mode_.data
A_agg_df = Attraction.groupby(axis=1, level=1).sum()
A_agg_df_ = A_agg_df.stack().reset_index(name='Attractions')
A_agg_df_['hh_type'] = A_agg_df_['hh_type'].map(hh)
A_agg_df_ = A_agg_df_.groupby(['p_hb','tp_return','hh_type','m','gor_id'])['Attractions'].sum().reset_index()


merged_df = P_agg_df_.merge(A_agg_df_,on=[  'gor_id',  'p_hb', 'm',  'tp_return','hh_type'],how='outer')


merged_df['gor_id'] = merged_df['gor_id'].map(gor_02id)
merged_df['m'] = merged_df['m'].map(mode)
merged_df['p_hb'] = merged_df['p_hb'].map(p)
merged_df = merged_df[['gor_id',  'p_hb', 'm',  'tp_return','hh_type','Productions','Attractions']]

Nhan_output = pd.read_csv(r"C:\Users\Kephale\Desktop\Alok\TFN\tem\Nhan_output.csv")
df = merged_df.merge(Nhan_output,on=[  'gor_id',  'p_hb', 'm',  'tp_return','hh_type'],how='outer')

df.to_csv(r'C:\Users\Kephale\Desktop\Alok\TFN\tem\output_AJ.csv',index=False)
