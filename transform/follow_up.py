import os, sys
from datetime import datetime

# This line will enable us to import python scripts from other folders
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd


def search_ani_old(abandoned_df: pd.DataFrame, pipedrive_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Search ANI Number from Abandoned Calls Dataframe if it is exisitng in Pipedrive Dataframe.
    This function will return ONLY EXISTING entries.\n

    Parameters:
        `abandoned_df` - Reference variable for abandoned_calls Pandas Dataframe\n
        `pipedrive_df` - Reference variable for pipedrive Pandas Dataframe\n

    Return:
        `deal_id_seach_result` - Reference variable for Pandas Dataframe of entries of ANI that is existing in
        pipedrive dataframe.\n
    '''

    
    # Split and Explode the multiple `phone numbers` of user per abandoned call
    # and assign it to new column `phone_list`
    pipedrive_df['phone_list'] = pipedrive_df['Person - Phone - Work'].str.split(', ')
    phone_list_exploded = pipedrive_df.explode('phone_list')
    abandoned_df['ANI'] = abandoned_df['ANI'].astype(str)
    number_search_result = abandoned_df[abandoned_df['ANI'].isin(phone_list_exploded['phone_list'])] # search ANI in pipedrive dataframe
    pd.options.mode.chained_assignment = None


    # Split and Explode the multiple `deal id` of user per abandoned call
    # and assign it to new column `deal_id_list`
    number_search_result['Deal ID'] = number_search_result['Deal ID'].astype(str)
    number_search_result['new_deal_id'] = number_search_result[number_search_result['Deal ID'].str.contains(r'^[0-9\s|]+$')][['Deal ID']]
    number_search_result['new_deal_id'] = number_search_result['new_deal_id'].str.split('|')
    deal_list_exploded = number_search_result.explode('new_deal_id')
    deal_list_exploded['new_deal_id'] = deal_list_exploded['new_deal_id'].str.strip() # remove leading and trailing whitespaces


    #Extract needed columns and merge two dataframe on `deal_id` column
    phone_list_exploded['Deal - ID'] = phone_list_exploded['Deal - ID'].astype(str)
    pipedrive_final_data = phone_list_exploded[['Deal - ID', 'Deal - Owner', 'Deal - Pipeline', 'Deal - Stage', 'Deal - CA Tracking Flag']]
    calls_final_data = deal_list_exploded[['new_deal_id', 'ANI', 'Date and Time', 'Date']]
    deal_id_search_result = pipedrive_final_data.merge(calls_final_data,
                                                    left_on='Deal - ID',
                                                    right_on='new_deal_id',
                                                    how='right') # search existing Deal ID in pipedrive dataframe
    
    # Rename `Deal - ID` to `Deal ID`
    deal_id_search_result.rename(columns={'Deal - ID': 'Deal ID'}, inplace=True)

    return deal_id_search_result


def search_ani(abandoned_df: pd.DataFrame, pipedrive_df: pd.DataFrame) -> 'tuple[pd.DataFrame, pd.DataFrame]':
    '''
    Search ANI Number from Abandoned Calls Dataframe if it is exisitng in Pipedrive Dataframe.
    This function will return ONLY EXISTING entries.\n

    Parameters:
        `abandoned_df` - Reference variable for abandoned_calls Pandas Dataframe\n
        `pipedrive_df` - Reference variable for pipedrive Pandas Dataframe\n

    Return:
        `final_result` - Reference variable for Pandas Dataframe of entries of ANI that is existing in
        pipedrive dataframe.\n
        `final_result_not_exist` - Reference variable for Pandas Dataframe of entries of ANI that is NOT existing in
        pipedrive dataframe.\n
    '''

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

    # phone_columns = [f'Person - Phone {i}' for i in range(1, 11)]
    # phone_columns.extend(['Person - Phone - Other', 'Person - Phone - Home', 'Person - Phone - Mobile', 'Person - Phone - Work'])

    # pipedrive_df[phone_columns] = pipedrive_df[phone_columns].applymap(lambda x: x.replace(' ', '').strip() if isinstance(x, str) else '')

    # pipedrive_df['phone_number'] = pipedrive_df[phone_columns].apply(lambda row: ','.join(filter(None, row)), axis=1)
    pipedrive_df['phone_number'] = pipedrive_df['phone_number'].fillna('')
    pipedrive_df = pipedrive_df[pipedrive_df['phone_number'].str.strip() != '']
    pipedrive_df['phone_number'] = pipedrive_df['phone_number'].str.split(',')
    pipedrive_df['phone_number'] = pipedrive_df['phone_number'].apply(lambda x: sorted(set(x), key=x.index))
    df_exploded = pipedrive_df.explode('phone_number').reset_index(drop=True)

    # Select columns needed
    # pipedrive_selected_cols = pipedrive_df # [['Deal - ID', 'Deal - Owner', 'Deal - Pipeline', 'Deal - Stage', 'Deal - CA Tracking Flag']]
    abandoned_df_selected_cols = abandoned_df[['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    
    # # Add pipedrive details per deal id
    # pipedrive_final_data = pipedrive_melted.merge(pipedrive_selected_cols,
    #                                             on='Deal - ID',
    #                                             how='left')
    # pipedrive_final_data = pipedrive_final_data.drop_duplicates(subset=['Deal - ID', 'phone_number'])

    # Group by 'phone_number' and aggregate 'Deal - ID' into a single string with unique IDs
    deal_ids = df_exploded.groupby('phone_number')['Deal - ID']\
        .agg(lambda x: " | ".join(map(str, pd.unique(x))))

    # Map the aggregated deal IDs back to the original DataFrame
    df_exploded['all_deal_id'] = df_exploded['phone_number'].map(deal_ids)

    
    # Search existing ANI numbers in pipedrive final data
    abandoned_df_selected_cols['ANI'] = abandoned_df_selected_cols['ANI'].astype(str)
    merged_calls_pipedrive = abandoned_df_selected_cols.merge(df_exploded,
                                                    left_on='ANI',
                                                    right_on='phone_number',
                                                    how='left').rename(columns={'Deal - ID': 'Deal ID'})

    # Select existing ANI and non-existing and assign to variables
    final_result = merged_calls_pipedrive[(merged_calls_pipedrive['phone_number'].notnull()) & (merged_calls_pipedrive['phone_number'] != 'Anonymous')]
    final_result_not_exist = merged_calls_pipedrive[(merged_calls_pipedrive['phone_number'].isna()) | (merged_calls_pipedrive['phone_number'] == 'Anonymous')]
    

    return final_result, final_result_not_exist, df_exploded


def add_activity_note_column(deal_id_search_result: pd.DataFrame) -> pd.DataFrame:
    '''
    Add new column `Activity Note` which contains ANI Number of abandoned call
    and its data and time of call.\n

    Parameter:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe that contains searched and filtered entries\n

    Return:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe with added `Activity Note` column.\n
    '''

    # Adding `Activity Note` column
    deal_id_search_result['Activity Note'] = deal_id_search_result.apply(
        lambda row: f"MO called, please call back. JC abandoned call from {row['ANI']} on {row['Date and Time']}",
        axis = 1)
    
    return deal_id_search_result


def add_subject_column(deal_id_search_result: pd.DataFrame) -> pd.DataFrame:
    '''
    Add new column `Subject` which contains pipeline and stages.\n

    Parameter:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe with added `Activity Note` column.\n

    Return:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe with added `Subject` column.\n
    '''

    # Create function that will assign stage to follow up calls
    def subject_col(row):
        if pd.isna(row['Deal - Pipeline']):
            return None

        ct_keywords = {"Qualifying", "Conversion",}
        aa_keywords = {"Sales", "White Glove", "Fast Close", "PSA"}
        ca_keywords = {"Diligence"}

        pipeline = row['Deal - Pipeline']

        if any(keyword in pipeline for keyword in ct_keywords):
            return 'CT - Abandoned Call Follow Up'
        elif any(keyword in pipeline for keyword in aa_keywords):
            return 'AA - Abandoned Call Follow Up'
        elif any(keyword in pipeline for keyword in ca_keywords):
            return 'CA - Abandoned Call Follow Up'
        elif "Underwriting" in pipeline:
            if row['Deal - Stage'] == 'Offer Ready':
                return 'PD - Abandoned Call Follow Up'
            else:
                return 'CT - Abandoned Call Follow Up'
        elif "Closing" in pipeline:
            if row['Deal - Stage'] == 'Re-engage MO':
                return 'AA - Abandoned Call Follow Up'
            else:
                return 'CA - Abandoned Call Follow Up'
        else:
            return None

    # Adding `Subject` column and apply the function
    deal_id_search_result['Subject'] = deal_id_search_result.apply(subject_col, axis=1)

    return deal_id_search_result

def new_add_subject_column(deal_id_search_result: pd.DataFrame, user_designation: dict, conditions_dict: dict) -> pd.DataFrame:
    '''
    Adds `Subject` column to the final dataframe that contains the follow up type of the phone number.\n

    Parameters:
        `deal_id_search_result (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Activity Note` column.\n
        `user_designation (dict)` - Dictionary of designated follow up and user per pipeline.\n
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n

    Return:
        `deal_id_search_result (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Subject` column.\n
    '''

    # Dictionary that will contain converted Deal - Pipeline to int counterpart
    pipeline_conversion = {}

    # Date today for offer ready conditions
    date_today = datetime.today()

    # Assign pipeline name as key and int counter part as value
    for key, value in user_designation.items():
        pipeline_conversion[value[0]] = key

    def format_date(row):

        date_object = datetime.strptime(row, '%Y-%m-%d')

        return date_object

    def check_deal_pipeline(key, pipeline_value):
        if 'sales' in key.lower():
            return f"{key.lower()} pipeline" == pipeline_value.lower()
        else:
            return key.lower() in pipeline_value.lower()

    # Pandas function that will execute dynamic input setting
    def assign_subject(row):
        for key in pipeline_conversion:
            if check_deal_pipeline(key, row['Deal - Pipeline']):
                value = pipeline_conversion[key] # number equivalent of pipeline

                if len(conditions_dict[value]) > 0: # if there are conditions

                    found_value = False # Set initial condition
                    initial_value = ''

                    for conditions in conditions_dict[value]: # find the conditions for specific pipeline
                        for condition, list_values in conditions.items(): # iterate through all pipeline conditions list
                            if ' > ' in condition and condition.split(' > ')[0].lower() == row[list_values[0]].lower():

                                column_name = condition.split(' > ')[0].title()
                                days_count = condition.split(' > ')[1]

                                if pd.notna(row[f"Deal - {column_name} Date"]) and row[f"Deal - {column_name} Date"] != '':
                                    if (date_today - format_date(row[f"Deal - {column_name} Date"])).days > int(days_count):
                                        found_value = True
                                        return list_values[1]

                            elif ' < ' in condition and condition.split(' < ')[0].lower() == row[list_values[0]].lower():

                                column_name = condition.split(' < ')[0].title()
                                days_count = condition.split(' < ')[1]

                                if pd.notna(row[f"Deal - {column_name} Date"]) and row[f"Deal - {column_name} Date"] != '':
                                    if (date_today - format_date(row[f"Deal - {column_name} Date"])).days < int(days_count):
                                        found_value = True
                                        return list_values[1]

                            elif row[list_values[0]].lower() == condition.lower(): # if column is equal to condition

                                found_value = True
                                initial_value = list_values[1]
                                continue
                                
                    if not found_value:
                        # if all conditions are not satisfied, return default setting value
                        return user_designation[value][1] if user_designation[value][1] != 'None' else None # follow up
                    else:
                        return initial_value
                
                else: # if there are no conditions for pipeline, return default setting value
                    return user_designation[value][1] if user_designation[value][1] != 'None' else None # follow up
            
        return None # If pipeline was not in tool, return Blank
         
                    
    deal_id_search_result['Subject'] = deal_id_search_result.apply(assign_subject, axis=1)

    return deal_id_search_result


def add_assigned_user(deal_id_search_result: pd.DataFrame) -> pd.DataFrame:
    '''
    Add new column `Assigned to user` which contains users that is assigned of a follow up.\n

    Parameter:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe with added `Subject` column.\n

    Return:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe with added `Assigned to user` column.\n
    '''

    # Create function that will assign users per follow up call
    def assigned_user_col(row):
        if pd.isna(row['Deal - Pipeline']):
            return None

        lovelyn_keywords = {"Qualifying", "Conversion"}
        deal_owner_keywords = {"Sales", "White Glove", "Fast Close", "PSA", "Closing"}
        tracking_flag_keywords = {"Diligence"}

        pipeline = row['Deal - Pipeline']

        if any(keyword in pipeline for keyword in lovelyn_keywords):
            return 'Lovelyn Valeriano'
        elif any(keyword in pipeline for keyword in deal_owner_keywords):
            return row['Deal - Owner']
        elif any(keyword in pipeline for keyword in tracking_flag_keywords):
            return row['Deal - CA Tracking Flag']
        elif "Underwriting" in pipeline:
            if row['Deal - Stage'] == 'Offer Ready':
                return 'Ira'
            elif row['Deal - Stage'] == 'Offer Ready - Small':
                return 'Darl Kevin Sopena'
            else:
                return 'Lovelyn Valeriano'
        else:
            return None
        
    # Adding `assigned_to_user` column and apply function
    deal_id_search_result['Assigned to user'] = deal_id_search_result.apply(assigned_user_col, axis=1)

    return deal_id_search_result


def new_add_assigned_user(deal_id_search_result: pd.DataFrame, user_designation: dict, conditions_dict: dict) -> pd.DataFrame:
    '''
    Adds `Assigned to user` column to final dataframe which contains the assigned user to specific pipeline or stage.\n

    Parameters:
        `deal_id_search_result (pd.DataFrame)` - Reference Variable of a Pandas Dataframe with added `Subject` column.\n
        `user_designation (dict)` - Dictionary of designated follow up and user per pipeline.\n
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n

    Return:
        `deal_id_search_result (pd.DataFrame)` - Reference Variable of a Pandas Dataframe with added `Assigned to user` column.\n
    '''

    # Dictionary that will contain converted Deal - Pipeline to int counterpart
    pipeline_conversion = {}

    # Date today for offer ready conditions
    date_today = datetime.today()

    # Assign pipeline name as key and int counter part as value
    for key, value in user_designation.items():
        pipeline_conversion[value[0]] = key

    # Helper function
    def assigned_user_default_value(values, row):
        if values == 'Deal Owner':
            return row['Deal - Owner']
        elif values == 'CA Tracking Flag':
            return row['Deal - CA Tracking Flag']
        else:
            return values if values != 'None' else None # Type in name by the user
        
    def format_date(row):

        date_object = datetime.strptime(row, '%Y-%m-%d')

        return date_object
    
    def check_deal_pipeline(key, pipeline_value):
        if 'sales' in key.lower():
            return f"{key.lower()} pipeline" == pipeline_value.lower()
        else:
            return key.lower() in pipeline_value.lower()


    # Pandas function that will execute dynamic input setting
    def assign_user(row):
        for key in pipeline_conversion:
            if check_deal_pipeline(key, row['Deal - Pipeline']):
                value = pipeline_conversion[key] # number equivalent of pipeline

                if len(conditions_dict[value]) > 0: # if there are conditions

                    found_value = False # Set initial condition
                    initial_value = ''

                    for conditions in conditions_dict[value]: # find the conditions for specific pipeline
                        for condition, list_values in conditions.items(): # iterate through all pipeline conditions list
                            if ' > ' in condition and condition.split(' > ')[0].lower() == row[list_values[0]].lower():

                                column_name = condition.split(' > ')[0].title()
                                days_count = condition.split(' > ')[1]

                                if pd.notna(row[f"Deal - {column_name} Date"]) and row[f"Deal - {column_name} Date"] != '':
                                    if (date_today - format_date(row[f"Deal - {column_name} Date"])).days > int(days_count):
                                        found_value = True
                                        return assigned_user_default_value(list_values[2], row)

                            elif ' < ' in condition and condition.split(' < ')[0].lower() == row[list_values[0]].lower():

                                column_name = condition.split(' < ')[0].title()
                                days_count = condition.split(' < ')[1]

                                if pd.notna(row[f"Deal - {column_name} Date"]) and row[f"Deal - {column_name} Date"] != '':
                                    if (date_today - format_date(row[f"Deal - {column_name} Date"])).days < int(days_count):
                                        found_value = True
                                        return assigned_user_default_value(list_values[2], row)

                            elif row[list_values[0]].lower() == condition.lower(): # if column is equal to condition

                                found_value = True
                                initial_value = assigned_user_default_value(list_values[2], row)
                                continue
                                
                    if not found_value:
                        # if all conditions are not satisfied, return default
                        return assigned_user_default_value(user_designation[value][2], row)
                    else:
                        return initial_value

                
                else: # if there are no conditions for pipeline, return default setting value
                    return assigned_user_default_value(user_designation[value][2], row)

        return None
         
                    
    deal_id_search_result['Assigned to user'] = deal_id_search_result.apply(assign_user, axis=1)

    return deal_id_search_result


def add_constant_column(deal_id_search_result: pd.DataFrame) -> pd.DataFrame:
    '''
    Add columns `Done` and `Type` with constant row values.\n

    Parameter:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe with added `Assigned to user` column.\n

    Return:
        `deal_id_search_result` - Reference Variable of a Pandas Dataframe with added constant values columns.\n
    '''

    # Adding constant columns `Done` and `Type`
    deal_id_search_result['Done'] = 'To do'
    deal_id_search_result['Type'] = 'Call'

    return deal_id_search_result


def export_to_excel(deal_id_search_result: pd.DataFrame, count: int) -> pd.DataFrame:
    '''
    Selects required columns and export Pandas Dataframe into Excel File Format.\n

    Parameter:
        `deal_id_search_result` - Dataframe that contains all columns after search and modification.\n

    Return:
        `final_output_data` - Output selected columns and save the dataframe as excel file format.\n
    '''

    # Select output columns
    # deal_id_search_result.drop_duplicates(subset=['ANI', 'Time'], inplace=True)

    rename_cols = deal_id_search_result.rename(columns={
        'Deal ID': 'Deal - ID',
        'Activity Note': 'Activity - Note',
        'Subject': 'Activity - Subject',
        'Type': 'Activity - Type',
        'Date and Time': 'Activity creation date'}).drop_duplicates(subset=['Contact ID', 'Deal - ID'])
    
    
    
    bu_small_mask = rename_cols['Team'] == 'Bottoms Up - Small'
    stage_mask = rename_cols['Deal - Stage'].isin(['Staging - Junior Sales', 'Updated Offer'])
    final_mask = (bu_small_mask) & (stage_mask)
    bu_small_update_df = rename_cols[final_mask]
    bu_small_update_df['Deal - Stage'] = 'Follow Up - Junior Sales'
    bu_small_update_df['Assigned to user'] = 'Reuben'
    final_bu_small_df = bu_small_update_df[[
        'Activity creation date',
        'Deal - ID',
        'Deal - Stage',
        'Activity - Type',
        'Activity - Subject',
        'Activity - Note',
        'Done',
        'Assigned to user'
        ]]
    
    final_output_data = rename_cols[~final_mask][[
        'Activity creation date',
        'Deal - ID',
        'Activity - Type',
        'Activity - Subject',
        'Activity - Note',
        'Done',
        'Assigned to user'
        ]]

    # Set output filename
    final_output_file_name = f'{count}. PIPEDRIVE IMPORT - FOLLOWUP.xlsx'
    bu_final_output_file_name = f'{count}. PIPEDRIVE IMPORT - FOLLOWUP (BU Small).xlsx'

    # Export dataframe to excel file
    final_output_data.to_excel(f'output/follow_up/{final_output_file_name}', index=False)
    final_bu_small_df.to_excel(f'output/follow_up/{bu_final_output_file_name}', index=False)

    # Add new phone number to pipedrive
    phone_columns = [f'Person - Phone {i}' for i in range(1, 11)]
    phone_not_exist_mask = ~rename_cols.apply(lambda row: row['ANI'] in row[phone_columns].values, axis=1)
    ani_add_df = rename_cols[phone_not_exist_mask].copy()

    def add_ani_and_record(row):
        for col in phone_columns:
            if pd.isna(row[col]) or row[col] == '':
                row[col] = row['ANI']
                current = row.get('Person - Phone - Work', '')

                # Handle NaN and non-string values
                if pd.isna(current):
                    current = ''
                else:
                    current = str(current)

                # Append ANI with a comma separator
                row['Person - Phone - Work'] = current + ', ' + str(row['ANI'])
                break
        return row

    if phone_not_exist_mask.any():
        ani_add_df = ani_add_df.apply(add_ani_and_record, axis=1)
        ani_add_df.rename(columns={'Deal ID': 'Deal - ID'}, inplace=True)
        ani_add_df['Deal - ID'] = ani_add_df['Deal - ID'].astype('Int64')
        phone_columns = ['Deal - ID', 'Person - ID', 'Person - Phone - Work'] + [f'Person - Phone {i}' for i in range(1, 11)]
        ani_add_df[phone_columns].to_excel(f'output/follow_up/{count}. PIPEDRIVE IMPORT - FOLLOW UP (Added Phones).xlsx', index=False)

def modify_rc_data(follow_up_df:pd.DataFrame) -> None:

    rc_data_df = follow_up_df.copy()
    rc_data_df['Note (if any)'] = 'F/U'
    new_columns = ['Resolved By',
                'Resolved on',
                'VM Link',
                'Resolved',
                'Caller ID from MVP']
    for col in new_columns:
        rc_data_df[col] = pd.NA

    rc_data_df['Deal ID'] = rc_data_df['all_deal_id']
    rc_data_df.drop_duplicates(subset=['ANI', 'Contact ID'], inplace=True)

    final_output_data = rc_data_df[[
        'Deal ID',
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
        'Team',
        'Activity Note',
        'Assigned to user',
        'Done',
        'Subject',
        'Type'
    ]]
    # final_output_data.drop_duplicates(subset=['ANI', 'Time'], inplace=True)

    return final_output_data


def create_follow_up(search_result: pd.DataFrame,
                     file_count: int,
                     user_designation: dict,
                     condition_dict: dict) -> pd.DataFrame:
    '''
    Main driver function of follow_up.py that will read, search and create `PIPEDRIVE IMPORT - FOLLOWUP.xlsx`.\n

    Parameters:
        `search_result (pd.DataFrame)` - Reference variable of Pandas Dataframe that contains ONLY existing ANI Numbers in pipedrive data.\n
        `file_count (int)` - Current count of the abandoned call file that is being processed.\n
        `user_designation (dict)` - Dictionary of designated user and follow up per pipeline.\n
        `condition_dict (dict)` - Dictionary of conditions defined by user per pipeline.\n

    Return:
        `final_output` - Pandas Dataframe of final output of follow ups.\n
    '''

    # # Read input files and assign output to variables
    # abandoned_calls_df, pipedrive_df = input_files(calls_data='RC 27.xlsx',
    #                                                pipedrive_data='Pipedrive.xlsx')
    
    # print('Creating PIPEDRIVE IMPORT - FOLLOWUP.xlsx...')
    
    # Search ANI Number from abandoned calls in pipedrive data
    # search_result = search_ani(abandoned_df=abandoned_calls_df,
    #                            pipedrive_df=pipedrive_df)

    if search_result.empty:
        return None
    
    print(f"Creating {file_count}. FOLLOW UP.xlsx file.")

    # Add columns based on the specification
    added_activity_note = add_activity_note_column(search_result)
    # added_subject = add_subject_column(added_activity_note)
    added_subject = new_add_subject_column(added_activity_note, user_designation, condition_dict)
    # added_assigned_user = add_assigned_user(added_subject)
    added_assigned_user = new_add_assigned_user(added_subject, user_designation, condition_dict)
    added_constant_column = add_constant_column(added_assigned_user)

    # Add columns to RC Data
    rc_data_output = modify_rc_data(added_constant_column)

    # Select required columns and export to excel file format
    export_to_excel(added_constant_column, file_count)

    return rc_data_output


if __name__ == '__main__':
    create_follow_up()