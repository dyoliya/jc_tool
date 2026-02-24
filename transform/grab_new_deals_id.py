"""This module will add Deal ID to New Deals in RC Input File"""

import pandas as pd
import os
import warnings

def read_pipedrive(path):

    pipedrive_file = os.listdir(path)
    pipedrive_df = pd.read_csv(os.path.join(path, pipedrive_file[0]))
    
    return pipedrive_df

def read_rc_data(path, file):

    if file.endswith('.csv'):
        df = pd.read_csv(os.path.join(path, file))
        return df
    elif file.endswith('.xlsx'):
        df = pd.read_excel(os.path.join(path, file))
        return df
    else:
        return None

def grab_new_deals_id(abandoned_df: pd.DataFrame,
                      pipedrive_df: pd.DataFrame,
                      file_name: str) -> None:
    
    
    # # Create list of phone number columns that will be used for searching ANI
    # phone_columns = [f'Person - Phone {i}' for i in range(1, 11)]
    # phone_columns.extend(['Person - Phone - Other', 'Person - Phone - Home', 'Person - Phone - Mobile'])
    pd.options.mode.chained_assignment = None

    # # Create a reshaped phone number table where phone number per deal id is listed
    # pipedrive_melted = pd.melt(pipedrive_df,
    #                         id_vars=['Deal - ID'],
    #                         value_vars=phone_columns,
    #                         var_name='phone_type',
    #                         value_name='phone_number')

    # Select columns needed
    # pipedrive_selected_cols = pipedrive_df[['Deal - ID', 'Deal - Deal Status', 'Deal - Unique Database ID', 'Person - ID']]
    abandoned_df_selected_cols = abandoned_df[['Deal ID',
                                                'Resolved By',
                                                'Resolved on',
                                                'Note (if any)',
                                                'VM Link',
                                                'Resolved',
                                                'Caller ID from MVP',
                                                'Date and Time',
                                                'Date',
                                                'Time',
                                                'Contact ID',
                                                'ANI',
                                                'Team']]

    # Add pipedrive details per deal id
    # pipedrive_final_data = pipedrive_melted.merge(pipedrive_selected_cols,
    #                                             on='Deal - ID',
    #                                             how='left')
    # pipedrive_final_data = pipedrive_final_data.drop_duplicates(subset=['Deal - ID', 'phone_number'])
    pipedrive_df['phone_number'] = pipedrive_df['phone_number'].fillna('')
    pipedrive_df = pipedrive_df[pipedrive_df['phone_number'].str.strip() != '']
    pipedrive_df['phone_number'] = pipedrive_df['phone_number'].str.split(',')
    pipedrive_df['phone_number'] = pipedrive_df['phone_number'].apply(lambda x: sorted(set(x), key=x.index))
    pipedrive_final_data = pipedrive_df.explode('phone_number').reset_index(drop=True)

    # Search existing ANI numbers in pipedrive final data
    abandoned_df_selected_cols['ANI'] = abandoned_df_selected_cols['ANI'].astype(str)
    abandoned_df_selected_cols = abandoned_df_selected_cols[abandoned_df_selected_cols['ANI'].str.lower() != 'anonymous']
    merged_calls_pipedrive = abandoned_df_selected_cols.merge(pipedrive_final_data,
                                                    left_on='ANI',
                                                    right_on='phone_number',
                                                    how='left')

    merged_calls_pipedrive['Deal - ID'] = merged_calls_pipedrive['Deal - ID'].fillna(0)
    merged_calls_pipedrive['Deal - ID'] = merged_calls_pipedrive['Deal - ID'].astype('int64')
    merged_calls_pipedrive['Person - ID'] = merged_calls_pipedrive['Person - ID'].fillna(0)
    merged_calls_pipedrive['Person - ID'] = merged_calls_pipedrive['Person - ID'].astype('int64')
    merged_calls_pipedrive['Deal ID'] = merged_calls_pipedrive.groupby('phone_number')['Deal - ID'].transform(
        lambda row: " | ".join(row.astype(str).unique()) if row.nunique() > 1 else str(row.iloc[0])
    )
    merged_calls_pipedrive.drop_duplicates(subset=['ANI', 'Time'], inplace=True)

    # Select not follow up entries
    merged_calls_pipedrive = merged_calls_pipedrive[merged_calls_pipedrive['Note (if any)'] != 'F/U']

    # For import
    filtered_df = merged_calls_pipedrive[merged_calls_pipedrive['phone_number'].notnull()]
    grab_new_deals_df = filtered_df[['Deal - Unique Database ID',
                                    'Deal ID',
                                    'Deal - Deal Status',
                                    'Person - ID']]
    grab_new_deals_df['contact_id'] = grab_new_deals_df['Deal - Unique Database ID'].apply(
        lambda x: [i.strip() for i in str(x).split("|")] if pd.notnull(x) else None)
    new_deal_id_exploded = grab_new_deals_df.explode('contact_id')
    new_deal_id_output = new_deal_id_exploded[new_deal_id_exploded['contact_id'].notnull()]
    new_deal_id_output.rename(columns={
        'Deal ID': 'deal_id',
        'Deal - Deal Status': 'deal_status',
        'Person - ID': 'person_id'}, inplace=True)
    
    # Export dataframe for import
    new_deal_id_output[[
        'contact_id', 'deal_id', 'deal_status', 'person_id'
    ]].to_excel(f'output/new_deals_deal_id/ (For Import) {file_name}.xlsx', index=False)

    # Export RC Data
    merged_calls_pipedrive.drop(columns=[
        'Deal - Deal Status',
        'Deal - Unique Database ID',
        'phone_number',
        'Deal - ID',
        'Person - ID'], axis=1, inplace=True)
    # merged_calls_pipedrive.rename(columns={
    #     'Deal - Deal Status_rc': 'Deal - Deal Status',
    #     'Deal - Unique Database ID_rc': 'Deal - Unique Database ID'}, inplace=True)
    
    merged_calls_pipedrive[['Deal ID',
                            'Resolved By',
                            'Resolved on',
                            'Note (if any)',
                            'VM Link',
                            'Resolved',
                            'Caller ID from MVP',
                            'Date and Time',
                            'Date',
                            'Time',
                            'Contact ID',
                            'ANI',
                            'Team']].to_excel(
        f"output/rc_data/(New Deals with Deal ID) {file_name}",
        index=False) # Export rc data

def main():

    print("Processing New Deals Deal IDs")

    warnings.filterwarnings("ignore", category=FutureWarning)

    abandoned_calls_path = 'data/abandoned_calls'
    abandoned_calls_files = os.listdir(abandoned_calls_path)

    # If empty RC Files folder
    if len(abandoned_calls_files) == 0:
        return 'rc_empty_grab'

    # Iterate through RC Input Files
    for file in abandoned_calls_files:
        pipedrive_df = read_pipedrive('data/pipedrive')
        rc_df = read_rc_data(abandoned_calls_path, file)
        if not rc_df.empty:
            grab_new_deals_id(rc_df, pipedrive_df, file)

    print("Process Complete")


if __name__ == "__main__":
    main()
