from transform.bottoms_up_new_deals import create_new_deals_bottoms_up
from transform.follow_up import create_follow_up, search_ani
from transform.cm_db_new_deals import create_new_deals_cm
from transform.no_results import create_no_result
from misc.parse_config import extract_config_info
from misc.sql_queries import *
from user_input.parallel_get import main as update_pipedrive_data
import json
from sqlalchemy import create_engine
import pandas as pd
import sqlite3
import os
import warnings
from urllib.parse import quote

# Helper functions
def get_input_files() -> 'tuple[list, list]':
    '''
    Iterate through the input data folder and create a list of files to read and transformed.

    Parameters:
        `None`

    Return:
        `abandoned_calls_file_list (list)` - List of file names from abandoned calls file folder.\n
        `pipedrive_file_list (list)` - List of file names from pipedrive data file folder.\n
    '''

    # Paths for input data
    pipedrive_path = 'data/pipedrive'
    abandoned_calls_path = 'data/abandoned_calls'

    # Get list of files to be read and transformed
    pipedrive_file_list = [os.path.join(pipedrive_path, file) for file in os.listdir(pipedrive_path) if file.endswith('.csv')]
    abandoned_calls_file_list = [os.path.join(abandoned_calls_path, file) for file in os.listdir(abandoned_calls_path) if file.endswith('.xlsx')]

    return abandoned_calls_file_list, pipedrive_file_list


def get_db_files(path: str) -> str:
    '''
    Parse through the database folder and get the database filename.

    Parameters:
        `path (str)` - File path of the data that is currently being processed.\n

    Return:
        `db_files (str)` - File name of the database file that was parsed from the folder.\n
    '''

    # Filter all database files from the folder
    db_files = [file for file in os.listdir(path) if file.endswith('.db')]

    return os.path.join(path, db_files[0]) if db_files else None


def read_bottoms_up(bottoms_up_db: str) -> pd.DataFrame:
    '''
    Read and extract data from Bottoms Up Database.

    Parameters:
        `bottoms_up_db` - File name of Bottoms Up Database file.\n

    Return:
        `df (pd.DataFrame)` - Pandas Dataframe that contains all neccessary columns from Bottoms Up Database.\n
    '''

    try:
        # Connect to SQLite Database
        connection = sqlite3.connect(bottoms_up_db)

        print(f'Reading Bottoms Up Database.')

        # Execute query and fetch the data into a Pandas Dataframe
        df = pd.read_sql_query('SELECT * FROM bottoms_up', connection)
        df['id'] = df.index
        df.rename(columns={
            'Owner': 'owner',
            'First Name': 'first_name',
            'Middle Name': 'middle_name',
            'Last Name': 'last_name',
            'Input: Address': 'address',
            'Input: City': 'city',
            'Input: State': 'state',
            'Input: Zip Code': 'postal_code',
            'County': 'target_county',
            'State': 'target_state',
            'Contact Type': 'contact_type',
            'ATTN': 'attn',
            '# of Interests': 'no_of_interest',
            'Category': 'category',
            'PDP Value ($)': 'offer_amount',
            'Total Value - Low ($)': 'value_low',
            'Total Value - High ($)': 'value_high',
            'Address Changed': 'address_changed',
            'Serial Number': 'serial_number',
            'md_address': 'address2',
            'md_city': 'city2',
            'md_state': 'state2',
            'md_postalcode': 'postal_code2'
        }, inplace=True)
        
        return df
    
    except Exception as e:
        print(f'Error occured during reading of database: {e}')
        return None

    finally:
        connection.close()


def read_cm_live_db(host: str,
                    port: str,
                    user: str,
                    password: str,
                    name: str) -> 'tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]':

    try:

        # Create database engine
        engine = create_engine(f'mysql+pymysql://{user}:{quote(password)}@{host}:{port}/{name}')

        print(f'Reading Community Minerals Database.')

        # Execute query and fetch the data into a Pandas Dataframe
        phone_number_df = pd.read_sql_query(phone_number_query, engine)
        emaiL_address_df = pd.read_sql_query(email_address_query, engine)
        serial_numbers_df = pd.read_sql_query(serial_numbers_query_mysql, engine)
        cm_db_df = pd.read_sql_query(cm_db_query, engine)

        # Change data type of phone number to int
        phone_number_df['phone_number'] = phone_number_df[phone_number_df['phone_number'] \
                                                          .str.contains(r'^[0-9]+$', na=False)] \
                                                            ['phone_number'].astype('Int64')
        
        phone_number_df.to_csv('./data/database/cm_db/phone_number.csv', index=False)
        emaiL_address_df.to_csv('./data/database/cm_db/email_address.csv', index=False)
        serial_numbers_df.to_csv('./data/database/cm_db/serial_number.csv', index=False)
        cm_db_df.to_csv('./data/database/cm_db/cm_db.csv', index=False)

        return phone_number_df, emaiL_address_df, serial_numbers_df, cm_db_df

    except Exception as e:
        return None,None,None,None

    finally:
        engine.dispose()


def read_cm_db(cm_db: str) -> 'tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]':
    '''
    Read and extract data from Community Minerals Database.

    Parameters:
        `cm_db` - File name of CM Database file.\n

    Return:
        `phone_number_df (pd.DataFrame)` - Pandas DataFrame that contains all phone numbers with corresponding database id.\n
        `email_address_df (pd.DataFrame)` - Pandas DataFrame that contains all emaill addresses with corresponding database id.\n
        `serial_numbers_df (pd.DataFrame)` - Pandas DataFrame that contains all serial numbers with corresponding database id.\n
        `cm_db_df (pd.DataFrame)` - Pandas DataFrame that contains all other columns needed for the final output file.\n
    '''

    try:
        # Connect to SQLite Database
        connection = sqlite3.connect(cm_db)

        print(f'Reading Community Minerals Database.')

        # Execute query and fetch the data into a Pandas Dataframe
        phone_number_df = pd.read_sql_query(phone_number_query, connection)
        emaiL_address_df = pd.read_sql_query(email_address_query, connection)
        serial_numbers_df = pd.read_sql_query(serial_numbers_query, connection)
        cm_db_df = pd.read_sql_query(cm_db_query, connection)

        # Change data type of phone number to int
        phone_number_df['phone_number'] = phone_number_df[phone_number_df['phone_number'] \
                                                          .str.contains(r'^[0-9]+$', na=False)] \
                                                            ['phone_number'].astype('Int64')

        return phone_number_df, emaiL_address_df, serial_numbers_df, cm_db_df
    
    except Exception as e:
        print(f'Error occured during reading of database: {e}')
        return None

    finally:
        connection.close()

def read_json_data():

    # Define path
    conditions_path = 'data/conditions_input/conditions_dict.json'
    user_designation_path = 'data/conditions_input/user_designation.json'

    # Designations
    with open(user_designation_path, 'r', encoding='utf-8') as designations_json_file:
        user_designation_raw = json.load(designations_json_file)

    # Conditions
    with open(conditions_path, 'r', encoding='utf-8') as conditions_json_file:
        condition_dict_raw = json.load(conditions_json_file)

    user_designation = {int(key): value for key, value in user_designation_raw.items()}
    condition_dict = {int(key): value for key, value in condition_dict_raw.items()}

    return user_designation, condition_dict

def get_timezone(row, tz_dict: dict):
    phone_number = row.get('Person - Phone 1')
    
    # Ensure the phone number is not null and convert it to a string if needed
    if pd.notna(phone_number):
        phone_number = str(phone_number)  # Convert to string if it's not already
        
        if len(phone_number) >= 3:
            area_code = phone_number[:3]  # Get the first 3 digits
            if area_code in tz_dict:
                return tz_dict[area_code]
    
    return None  # Return None if conditions aren't met

def get_timezone_dict() -> dict:

    timezone_df = pd.read_csv(f"./data/tz_file/Time Zones.csv", low_memory=False)
    timezone_df['area_code'] = timezone_df['area_code'].astype('string')
    timezone_dict = timezone_df.set_index('area_code')['pipedrive_eq'].to_dict()

    return timezone_dict


def export_new_deals(bottoms_up_output: pd.DataFrame,
                     cm_db_output: pd.DataFrame,
                     rc_df: pd.DataFrame,
                     bottoms_up_final: pd.DataFrame,
                     cm_db_final: pd.DataFrame,
                     file_count: int) -> pd.DataFrame:
    '''
    Concatenates all non existing ANI Number from both Bottoms Up and CM Database and exports as excel file.\n

    Parameters:
        `bottoms_up_output (pd.DataFrame)` - Pandas DataFrame of ANI Numbers that is not existing in Bottoms Up Database.\n
        `cm_db_output (pd.DataFrame)` - Pandas DataFrame of ANI Numbers that is not existing in CM Database.\n
        `file_count (int)` - Current file count of abandoned calls file that is being processed.\n

    Return:
        `None`
    '''

    columns = [
        'Deal - Deal creation date',
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
        'Deal - Title',
        'Deal - Label',
        'Deal - Stage',
        'Deal - Owner',
        'Deal - County',
        'Deal - Preferred Communication Method',
        'Deal - Abandoned Call Flag',
        'Deal - Inbound Medium',
        'Deal - Serial Number',
        'Deal - Unique Database ID',
        'Deal - Marketing Medium',
        'Deal - Deal Summary',
        'Deal - Deal Status',
        'Deal - Pipedrive Analyst Tracking Flag',
        'Deal - Phone Number Format',
        'Person - Name',
        'Person - Mailing Address',
        'Person - Email',
        'Person - Email 1',
        'Person - Email 2',
        'Person - Email 3',
        'Person - Email 4',
        'Person - Email 5',
        'Person - Email 6',
        'Person - Email 7',
        'Person - Email 8',
        'Person - Email 9',
        'Person - Email 10',
        'Person - Email 11',
        'Person - Email 12',
        'Person - Email 13',
        'Person - Email 14',
        'Person - Email 15',
        'Person - Email 16',
        'Person - Email 17',
        'Person - Phone',
        'Person - Phone 1',
        'Note Content',
        'Person - Mailing Address - Data Source',
        'Person - Phone 1 - Data Source',
        'Activity Note',
        'Assigned to user',
        'Done',
        'Subject',
        'Type',
        'Person - Timezone'
    ]

    if cm_db_final.empty and bottoms_up_final.empty:
        return pd.concat([rc_df, pd.DataFrame(columns=columns)])

    # Concatenate non existing bottoms up and non existing cm database
    new_deals_output = pd.concat([bottoms_up_output, cm_db_output])
    timezone_dict = get_timezone_dict()
    new_deals_output['Person - Timezone'] = new_deals_output.apply(get_timezone,
                                                                   tz_dict=timezone_dict,
                                                                   axis=1)

    print(f"Creating {file_count}. NEW DEALS.xlsx file.")
    
    # Export dataframe as excel
    new_deals_output.to_excel(f'output/new_deals/{file_count}. PIPEDRIVE IMPORT - NEW DEALS.xlsx', index=False)

    # New deals in RC Data
    new_deal_df = pd.concat([bottoms_up_final, cm_db_final])
    new_deal_df['Note (if any)'] = 'New Deal'
    rc_data_ouput = pd.concat([new_deal_df, rc_df])
    rc_final_output = rc_data_ouput[columns]

    return rc_final_output

def multiple_or_no_result(row):
    
    if row['Deal - Deal Summary'] == 'Common Name Error':
        return 'Multiple Result'
    elif row['Deal - Deal Summary'] == 'No Information in Email':
        return 'No Result'


def export_rc_data(rc_df,
                   added_constant_columns_df,
                   file_name):
    
    

    added_constant_columns_df['Note (if any)'] = added_constant_columns_df.apply(multiple_or_no_result, axis=1)
    rc_data_ouput = pd.concat([added_constant_columns_df, rc_df])
    rc_final_output = rc_data_ouput[[
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
        'Deal - Title',
        'Deal - Label',
        'Deal - Stage',
        'Deal - County',
        'Deal - Preferred Communication Method',
        'Deal - Abandoned Call Flag',
        'Deal - Inbound Medium',
        'Deal - Serial Number',
        'Deal - Unique Database ID',
        'Deal - Marketing Medium',
        'Deal - Deal Summary',
        'Deal - Deal Status',
        'Deal - Pipedrive Analyst Tracking Flag',
        'Deal - Phone Number Format',
        'Person - Name',
        'Person - Mailing Address',
        'Person - Email',
        'Person - Email 1',
        'Person - Email 2',
        'Person - Email 3',
        'Person - Email 4',
        'Person - Email 5',
        'Person - Email 6',
        'Person - Email 7',
        'Person - Email 8',
        'Person - Email 9',
        'Person - Email 10',
        'Person - Email 11',
        'Person - Email 12',
        'Person - Email 13',
        'Person - Email 14',
        'Person - Email 15',
        'Person - Email 16',
        'Person - Email 17',
        'Person - Phone',
        'Person - Phone 1',
        'Note Content',
        'Person - Mailing Address - Data Source',
        'Person - Phone 1 - Data Source',
        'Activity Note',
        'Assigned to user',
        'Done',
        'Subject',
        'Type'
    ]]

    rc_final_output.sort_values(by='Contact ID', inplace=True)
    rc_final_output.to_excel(f"output/rc_data/(Added New Deals) {file_name}", index=False)


def get_cm_deal_id(
        fu_df: pd.DataFrame,
        final_result_not_exist: pd.DataFrame,
        phone_number_df: pd.DataFrame,
        pipedrive_df: pd.DataFrame,
        cm_db_df: pd.DataFrame):
    
    columns = [
        'Deal - Deal creation date',
        'Deal - Title',
        'Deal - Label',
        'Deal - Stage',
        'Deal - County',
        'Deal - Preferred Communication Method',
        'Deal - Abandoned Call Flag',
        'Deal - Inbound Medium',
        'Deal - Serial Number',
        'Deal - Unique Database ID',
        'Deal - Marketing Medium',
        'Deal - Deal Summary',
        'Deal - Deal Status',
        'Deal - Pipedrive Analyst Tracking Flag',
        'Deal - Phone Number Format',
        'Person - Name',
        'Person - Mailing Address',
        'Person - Email',
        'Person - Email 1',
        'Person - Email 2',
        'Person - Email 3',
        'Person - Email 4',
        'Person - Email 5',
        'Person - Email 6',
        'Person - Email 7',
        'Person - Email 8',
        'Person - Email 9',
        'Person - Email 10',
        'Person - Email 11',
        'Person - Email 12',
        'Person - Email 13',
        'Person - Email 14',
        'Person - Email 15',
        'Person - Email 16',
        'Person - Email 17',
        'Person - Phone',
        'Person - Phone 1',
        'Note Content',
        'Person - Mailing Address - Data Source',
        'Person - Phone 1 - Data Source'
    ]
    
    if final_result_not_exist.empty:
        return fu_df, pd.DataFrame(), pd.DataFrame(columns=columns)
    
    final_result_not_exist['ANI'] = final_result_not_exist[final_result_not_exist['ANI']\
                                                           .str.contains(r'^[0-9]+$', na=False)]\
                                                            ['ANI'].astype('Int64')
    
    cm_db_ani_entries = final_result_not_exist[~final_result_not_exist['Team'].str.contains('Reuben', na=False)][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    cm_db_ani_entries = cm_db_ani_entries[(cm_db_ani_entries['ANI'] != '(blank)') & (cm_db_ani_entries['ANI']).notnull()]
    # phone_number_df['phone_number'] = phone_number_df[phone_number_df['phone_number'] \
    #                                                   .str.contains(r'^[0-9]+$', na=False)] \
    #                                                     ['phone_number'].astype('Int64')

    # Search ANI if existing in CM Database
    cm_db_check_ani = cm_db_ani_entries.merge(phone_number_df,
                                            left_on='ANI',
                                            right_on='phone_number',
                                            how='left')
    # cm_db_check_ani.drop_duplicates(subset=['ANI'], inplace=True)
    cm_db_exist = cm_db_check_ani[cm_db_check_ani['id'].notnull()]
    cm_db_not_exist = cm_db_check_ani[cm_db_check_ani['id'].isna()][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    cm_db_not_exist['Deal - Deal Summary'] = 'No Information in Email'

    # Filter all contacts that has deal id
    search_deal_id_df = cm_db_df[cm_db_df['deal_id'].notnull()][['id', 'deal_id']]

    # Add Deal ID Column to existing ANI Numbers
    get_deal_id_df = cm_db_exist.merge(search_deal_id_df,
                                    on='id',
                                    how='left')

    # Filter ANI Numbers that has Deal ID
    deal_id_exist = get_deal_id_df[get_deal_id_df['deal_id'].notnull()]
    deal_id_exist['deal_id'] = deal_id_exist['deal_id'].astype('int64')
    deal_id_exist_final = deal_id_exist[deal_id_exist['deal_id'].isin(pipedrive_df['Deal - ID'])]
    no_deal_id = get_deal_id_df[get_deal_id_df['deal_id'].isna()].drop(columns='deal_id', axis=1)
    no_deal_id_final = no_deal_id[~no_deal_id['ANI'].isin(deal_id_exist_final['ANI'])]

    # Modify pipedrive df
    pipedrive_drop_df = pipedrive_df.drop(columns=['phone_number', 'all_deal_id'], axis=1)

    # Merge pipedrive data to existing CM Deal ID
    merge_pd_deal_id_df = deal_id_exist_final.merge(pipedrive_drop_df,
                                            left_on='deal_id',
                                            right_on='Deal - ID',
                                            how='left')
    merge_pd_deal_id_df['all_deal_id'] = merge_pd_deal_id_df.groupby('phone_number')['deal_id'].transform(
        lambda x: " | ".join(x.astype(str).unique()) if x.nunique() > 1 else str(x.iloc[0])
    )
    merge_pd_deal_id_df.drop(columns=['id', 'deal_id'], axis=1, inplace=True)
    merge_pd_deal_id_df.rename(columns={'Deal - ID': 'Deal ID'}, inplace=True)

    # Concat FU and CM Deal ID FU
    fu_final_df = pd.concat([fu_df, merge_pd_deal_id_df])

    # Revert ANI to string dtype
    final_result_not_exist['ANI'] = final_result_not_exist['ANI'].astype(str)

    return fu_final_df, no_deal_id_final, cm_db_not_exist



def main():
    '''
    Main driver function of this tool that will read database files, search if ANI Numbers is existing and export
    excel files with columns based upon specifications.\n

    Parameters:
        `None`

    Return:
        `None`
    '''

    # Run dynamic input setting
    # user_designation, condition_dict = ask_user_input()

    try:
        # Define path of database file
        bottoms_up_path = 'data/database/bottoms_up'
        cm_db_path = 'data/database/cm_db'
        db_host, db_port, db_user, db_password, db_name = extract_config_info()

        # Read all input files
        abandoned_calls_file_list, pipedrive_file_list = get_input_files()

        # Return error if RC File folder is empty
        if len(abandoned_calls_file_list) == 0:
            return 'rc_empty_main'

        bottoms_up_db, cm_db = get_db_files(bottoms_up_path), get_db_files(cm_db_path) # Read and get database files
        bottoms_up_df = read_bottoms_up(bottoms_up_db) # Bottoms Up Dataframe
        phone_number_df, email_address_df, serial_numbers_df, cm_db_df = read_cm_live_db(db_host,
                                                                                            db_port,
                                                                                            db_user,
                                                                                            db_password,
                                                                                            db_name) # Live CM Database
        
        # If database credentials is wrong
        if phone_number_df is None:
            return 'db_wrong'
        
        file_count = 1 # Counter for Abandoned Calls File
        user_designation, condition_dict = read_json_data()

        update_pipedrive_data()

        # Read single pipedrive file
        for pipedrive_file in pipedrive_file_list:
            pipedrive_df = pd.read_csv(pipedrive_file, low_memory=False)
            pipedrive_df['Person - Phone - Work'] = pipedrive_df['phone_number']

        # Iterate through list of abandoned_calls files
        for abandoned_calls_file in abandoned_calls_file_list:
            
            warnings.filterwarnings("ignore", category=FutureWarning)

            calls_file_name = abandoned_calls_file.split('\\')[-1]
            print(f'Reading {calls_file_name}.')
            abandoned_calls_df = pd.read_excel(abandoned_calls_file)
            abandoned_calls_df['Contact ID'] = abandoned_calls_df.index

            # Create Follow Up output file
            ani_exist, ani_not_exist, df_exploded = search_ani(abandoned_calls_df, pipedrive_df)

            # Get Deal ID from cm database
            fu_final_df, cm_exist_df, cm_not_exist_df = get_cm_deal_id(ani_exist,
                                                                    ani_not_exist,
                                                                    phone_number_df,
                                                                    df_exploded,
                                                                    cm_db_df)

            # Create FU Output
            rc_df = create_follow_up(fu_final_df, file_count, user_designation, condition_dict)

            # Search in Bottoms Up Database
            bottoms_up_not_exist, bottoms_up_output, bottom_up_final_df = create_new_deals_bottoms_up(ani_not_exist,
                                                                                    bottoms_up_df,
                                                                                    file_count)
            
            # Search in Community Minerals Database
            cm_db_not_exist, cm_db_output, cm_db_final_df = create_new_deals_cm(
                                                                cm_exist_df,
                                                                cm_not_exist_df,
                                                                email_address_df,
                                                                serial_numbers_df,
                                                                cm_db_df)
            
            # Concatenate Bottoms Up and CM then create New Deals output file
            rc_added_new_deals_df = export_new_deals(bottoms_up_output,
                                                        cm_db_output,
                                                        rc_df,
                                                        bottom_up_final_df,
                                                        cm_db_final_df,
                                                        file_count)
            
            # Create No Result output file
            no_result_df = create_no_result(cm_db_not_exist,
                                bottoms_up_not_exist,
                                file_count)
            
            # Export all combined dataframes as RC Data
            export_rc_data(rc_added_new_deals_df, no_result_df, calls_file_name)

            # Increment file count
            file_count += 1
        
        # Pass true to user interface to create successful run window
        return 'pass'
    
    except Exception as e:
        print(f"Error occured: {e}")
    

if __name__ == '__main__':
    main()