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
import numpy as np
import sqlite3
import os
import warnings
from urllib.parse import quote

warnings.simplefilter(action='ignore', category=FutureWarning)
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

        print(f"Reading Bottoms Up Database: {os.path.basename(bottoms_up_db)}")

        # Execute query and fetch the data into a Pandas Dataframe
        df = pd.read_sql_query('SELECT * FROM bottoms_up', connection)
        # df['id'] = df.index
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
            'Category': 'bu_category',
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

        # ✅ Convert phone1–phone5 to Int64 safely
        for col in ['phone1', 'phone2', 'phone3', 'phone4', 'phone5']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

        return df
    
    except Exception as e:
        print(f'Error occured during reading of database: {e}')
        return None

    finally:
        connection.close()

def normalize_ntm_contact_group_id(value):
    """
    Preserve numeric and alphanumeric NTM contact-group IDs as strings.

    Multiple pipe-separated IDs are retained, with blanks and duplicates
    removed while preserving their original order.
    """
    if pd.isna(value):
        return pd.NA

    unique_group_ids = []

    for item in str(value).split('|'):
        item = item.strip()

        if not item or item.lower() in {'nan', 'none', 'nat'}:
            continue

        # Normalize Excel-style numeric strings such as 116627.0.
        # Alphanumeric values such as ABC123 remain unchanged.
        try:
            numeric_value = float(item)

            if numeric_value.is_integer():
                normalized_id = str(int(numeric_value))
            else:
                normalized_id = item
        except (ValueError, TypeError):
            normalized_id = item

        if normalized_id not in unique_group_ids:
            unique_group_ids.append(normalized_id)

    if not unique_group_ids:
        return pd.NA

    return ' | '.join(unique_group_ids)

def reshape_ntm_contacts(ntm_contacts_df: pd.DataFrame) -> 'tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]':
    '''
    Reshape the flat ntm_contacts table into the DataFrames expected by the
    existing abandoned-calls workflow.
    '''

    phone_columns = [f'phone{i}' for i in range(1, 7)]
    phone_number_df = (
        ntm_contacts_df[['ntm_id', *phone_columns]]
        .melt(id_vars='ntm_id', value_vars=phone_columns, value_name='phone_number')
        .drop(columns='variable')
        .dropna(subset=['phone_number'])
    )
    phone_number_df['phone_number'] = pd.to_numeric(
        phone_number_df['phone_number'], errors='coerce'
    ).astype('Int64')
    phone_number_df.dropna(subset=['phone_number'], inplace=True)
    phone_number_df.drop_duplicates(subset=['ntm_id', 'phone_number'], inplace=True)

    email_columns = [f'email{i}' for i in range(1, 7)]
    email_address_df = (
        ntm_contacts_df[['ntm_id', *email_columns]]
        .melt(id_vars='ntm_id', value_vars=email_columns, value_name='email_address')
        .drop(columns='variable')
        .dropna(subset=['email_address'])
    )
    email_address_df['email_address'] = email_address_df['email_address'].astype(str).str.strip()
    email_address_df = email_address_df[
        email_address_df['email_address'].ne('')
    ].drop_duplicates(subset=['ntm_id', 'email_address'])

    serial_numbers_df = ntm_contacts_df[
        ['ntm_id', 'serial_number', 'old_serial_number']
    ].copy()
    current_serial = serial_numbers_df['serial_number'].fillna('').astype(str).str.strip()
    old_serial = serial_numbers_df['old_serial_number'].fillna('').astype(str).str.strip()

    serial_numbers_df['serial_numbers'] = current_serial
    only_old_serial = current_serial.eq('') & old_serial.ne('')
    different_serials = (
        current_serial.ne('')
        & old_serial.ne('')
        & current_serial.ne(old_serial)
    )
    serial_numbers_df.loc[only_old_serial, 'serial_numbers'] = old_serial[only_old_serial]
    serial_numbers_df.loc[different_serials, 'serial_numbers'] = (
        current_serial[different_serials] + ' | ' + old_serial[different_serials]
    )
    serial_numbers_df = serial_numbers_df[['ntm_id', 'serial_numbers']]
    serial_numbers_df.loc[
        serial_numbers_df['serial_numbers'].eq(''), 'serial_numbers'
    ] = pd.NA

    ntm_contacts_df = ntm_contacts_df.copy()

    ntm_contacts_df['ntm_contact_group_id'] = (
        ntm_contacts_df['ntm_contact_group_id']
        .apply(normalize_ntm_contact_group_id)
        .astype('string')
    )

    cm_db_df = ntm_contacts_df[[
        'ntm_id', 'first_name', 'middle_name', 'last_name', 'deal_id',
        'budb_id', 'ntm_contact_group_id',
        'address', 'city', 'state_address', 'postal_code',
        'address2', 'city2', 'state_address2', 'postal_code2',
        'data_source', 'country', 'state'
    ]].copy()

    return phone_number_df, email_address_df, serial_numbers_df, cm_db_df


def read_cm_live_db(host: str,
                    port: str,
                    user: str,
                    password: str,
                    name: str) -> 'tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]':

    try:

        # Create database engine
        engine = create_engine(f'mysql+pymysql://{user}:{quote(password)}@{host}:{port}/{name}')

        print('Reading NTM contacts table.')

        # Read the flat NTM table once, then reshape its repeated phone/email
        # columns into the same DataFrames expected by the existing workflow.
        ntm_contacts_df = pd.read_sql_query(ntm_contacts_query, engine)

        phone_number_df, email_address_df, serial_numbers_df, cm_db_df = (
            reshape_ntm_contacts(ntm_contacts_df)
        )
        
        phone_number_df.to_csv('./data/database/ntm_db/phone_number.csv', index=False)
        email_address_df.to_csv('./data/database/ntm_db/email_address.csv', index=False)
        serial_numbers_df.to_csv('./data/database/ntm_db/serial_number.csv', index=False)
        cm_db_df.to_csv('./data/database/ntm_db/ntm_db.csv', index=False)

        return phone_number_df, email_address_df, serial_numbers_df, cm_db_df

    except Exception as e:
        import traceback

        print('\n[ERROR read_ntm_live_db]')
        print(f'{type(e).__name__}: {e}')
        traceback.print_exc()

        return None, None, None, None

    finally:
        if 'engine' in locals():
            engine.dispose()

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
        'Deal - Offer Generated Date',
        'Deal - Title',
        'Deal - Category',
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
        'Person - Timezone',
        'Deal - BU Database ID',
        'Deal - Contact Group ID'
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

    # to ensure no error if there are 0 follow-ups
    for col in columns:
        if col not in rc_data_ouput.columns:
            rc_data_ouput[col] = ""
            
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
    cm_db_exist = cm_db_check_ani[cm_db_check_ani['ntm_id'].notnull()]
    cm_db_not_exist = cm_db_check_ani[cm_db_check_ani['ntm_id'].isna()][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    cm_db_not_exist['Deal - Deal Summary'] = 'No Information in Email'

    # Filter all contacts that has deal id
    search_deal_id_df = cm_db_df[cm_db_df['deal_id'].notnull()][['ntm_id', 'deal_id']]

    # Add Deal ID Column to existing ANI Numbers
    get_deal_id_df = cm_db_exist.merge(search_deal_id_df,
                                    on='ntm_id',
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
    merge_pd_deal_id_df.drop(columns=['ntm_id', 'deal_id'], axis=1, inplace=True)
    merge_pd_deal_id_df.rename(columns={'Deal - ID': 'Deal ID'}, inplace=True)

    # Concat FU and CM Deal ID FU
    fu_final_df = pd.concat([fu_df, merge_pd_deal_id_df])

    # Revert ANI to string dtype
    final_result_not_exist['ANI'] = final_result_not_exist['ANI'].astype(str)

    return fu_final_df, no_deal_id_final, cm_db_not_exist

def log_step(step_name, **dfs):
    print(f"\n=== {step_name} ===")
    for name, df in dfs.items():
        if df is None:
            print(f"{name}: 0 rows")
        else:
            try:
                print(f"{name}: {len(df)} rows")
            except Exception:
                print(f"{name}: {type(df)} (no len available)")

def normalize_phone(phone):
    if pd.isna(phone): return None
    phone = str(phone)
    phone = phone.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
    if phone.startswith('1') and len(phone) == 11:
        phone = phone[1:]
    return phone.strip()


def decode_phone_number_list(value):
    """Convert Excel-safe CSV phone text into the format used by search_ani."""
    if pd.isna(value):
        return ''

    text = str(value).strip()
    if text.startswith('="') and text.endswith('"'):
        text = text[2:-1].replace('""', '"')

    phone_values = []
    for phone in text.split(','):
        normalized = normalize_phone(phone.strip())
        if normalized and normalized not in phone_values:
            phone_values.append(normalized)

    # search_ani splits on commas without trimming, so keep this space-free.
    return ','.join(phone_values)


def add_related_bottoms_up_phones_to_pipedrive(
        pipedrive_df: pd.DataFrame,
        bottoms_up_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add BUDB sibling phones to the in-memory Pipedrive search data.

    If any phone from one BUDB row is already associated with a Pipedrive
    deal, all other nonblank phones from that same BUDB row are treated as
    related to that deal for this run. The actual pipedrive_data.csv file is
    not changed.
    """

    result_df = pipedrive_df.copy()
    phone_columns = [
        column
        for column in [f'phone{i}' for i in range(1, 6)]
        if column in bottoms_up_df.columns
    ]

    if (
        result_df.empty
        or bottoms_up_df.empty
        or not phone_columns
        or 'phone_number' not in result_df.columns
    ):
        return result_df

    # Always use the untouched Pipedrive phone list as the anchor. This avoids
    # allowing a phone inferred from another database to trigger this fallback.
    actual_phone_column = (
        'Person - Phone - Work'
        if 'Person - Phone - Work' in result_df.columns
        else 'phone_number'
    )

    # Map every actual Pipedrive phone to the deal row(s) containing it.
    pipedrive_phone_to_rows = {}
    for row_index, phone_list in result_df[actual_phone_column].items():
        for phone in str(phone_list or '').split(','):
            normalized_phone = normalize_phone(phone)
            if normalized_phone:
                pipedrive_phone_to_rows.setdefault(
                    normalized_phone, set()
                ).add(row_index)

    if not pipedrive_phone_to_rows:
        return result_df

    # BUDB phone1-phone5 were converted to Int64 in read_bottoms_up().
    # Filter first so we only iterate through BUDB rows having at least one
    # phone that is already present in the Pipedrive export.
    numeric_pipedrive_phones = {
        int(phone)
        for phone in pipedrive_phone_to_rows
        if phone.isdigit()
    }
    if not numeric_pipedrive_phones:
        return result_df

    matched_bottoms_up_rows = bottoms_up_df.loc[
        bottoms_up_df[phone_columns]
        .isin(numeric_pipedrive_phones)
        .any(axis=1),
        phone_columns
    ]

    related_phones_by_deal_row = {}
    for _, bottoms_up_row in matched_bottoms_up_rows.iterrows():
        related_phones = []
        for value in bottoms_up_row:
            normalized_phone = normalize_phone(value)
            if normalized_phone and normalized_phone not in related_phones:
                related_phones.append(normalized_phone)

        matched_deal_rows = set()
        for phone in related_phones:
            matched_deal_rows.update(pipedrive_phone_to_rows.get(phone, set()))

        for row_index in matched_deal_rows:
            related_phones_by_deal_row.setdefault(row_index, set()).update(
                related_phones
            )

    added_phone_associations = 0
    affected_deal_rows = 0

    for row_index, related_phones in related_phones_by_deal_row.items():
        existing_phones = [
            normalize_phone(phone)
            for phone in str(result_df.at[row_index, 'phone_number'] or '').split(',')
        ]
        existing_phones = [phone for phone in existing_phones if phone]

        combined_phones = list(existing_phones)
        for phone in sorted(related_phones):
            if phone not in combined_phones:
                combined_phones.append(phone)
                added_phone_associations += 1

        if len(combined_phones) > len(existing_phones):
            affected_deal_rows += 1
            result_df.at[row_index, 'phone_number'] = ','.join(combined_phones)

    print(
        "Related BUDB phone fallback: "
        f"added {added_phone_associations} phone association(s) across "
        f"{affected_deal_rows} Pipedrive deal row(s)."
    )

    return result_df


def add_related_ntm_phones_to_pipedrive(
        pipedrive_df: pd.DataFrame,
        phone_number_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add NTM sibling phones to the in-memory Pipedrive search data.

    The long phone_number_df contains phone1-phone6 grouped by the same NTM
    contact id. If one phone for an id is actually present on a Pipedrive deal,
    the other phones for that same id are treated as related to that deal for
    this run. The actual pipedrive_data.csv file is not changed.
    """

    result_df = pipedrive_df.copy()
    required_ntm_columns = {'ntm_id', 'phone_number'}

    if (
        result_df.empty
        or phone_number_df.empty
        or not required_ntm_columns.issubset(phone_number_df.columns)
        or 'phone_number' not in result_df.columns
    ):
        return result_df

    # Person - Phone - Work was saved before either database fallback runs,
    # so it represents only the phones actually exported from Pipedrive.
    actual_phone_column = (
        'Person - Phone - Work'
        if 'Person - Phone - Work' in result_df.columns
        else 'phone_number'
    )

    pipedrive_phone_to_rows = {}
    for row_index, phone_list in result_df[actual_phone_column].items():
        for phone in str(phone_list or '').split(','):
            normalized_phone = normalize_phone(phone)
            if normalized_phone:
                pipedrive_phone_to_rows.setdefault(
                    normalized_phone, set()
                ).add(row_index)

    numeric_pipedrive_phones = {
        int(phone)
        for phone in pipedrive_phone_to_rows
        if phone.isdigit()
    }
    if not numeric_pipedrive_phones:
        return result_df

    ntm_phones = phone_number_df[['ntm_id', 'phone_number']].dropna().copy()
    matched_ntm_ids = ntm_phones.loc[
        ntm_phones['phone_number'].isin(numeric_pipedrive_phones),
        'ntm_id'
    ].drop_duplicates()

    if matched_ntm_ids.empty:
        print(
            "Related NTM phone fallback: added 0 phone association(s) "
            "across 0 Pipedrive deal row(s)."
        )
        return result_df

    matched_ntm_phones = ntm_phones[
        ntm_phones['ntm_id'].isin(matched_ntm_ids)
    ]

    related_phones_by_deal_row = {}
    for _, contact_phones in matched_ntm_phones.groupby('ntm_id', sort=False):
        related_phones = []
        for value in contact_phones['phone_number']:
            normalized_phone = normalize_phone(value)
            if normalized_phone and normalized_phone not in related_phones:
                related_phones.append(normalized_phone)

        matched_deal_rows = set()
        for phone in related_phones:
            matched_deal_rows.update(pipedrive_phone_to_rows.get(phone, set()))

        for row_index in matched_deal_rows:
            related_phones_by_deal_row.setdefault(row_index, set()).update(
                related_phones
            )

    added_phone_associations = 0
    affected_deal_rows = 0

    for row_index, related_phones in related_phones_by_deal_row.items():
        existing_phones = [
            normalize_phone(phone)
            for phone in str(result_df.at[row_index, 'phone_number'] or '').split(',')
        ]
        existing_phones = [phone for phone in existing_phones if phone]

        combined_phones = list(existing_phones)
        for phone in sorted(related_phones):
            if phone not in combined_phones:
                combined_phones.append(phone)
                added_phone_associations += 1

        if len(combined_phones) > len(existing_phones):
            affected_deal_rows += 1
            result_df.at[row_index, 'phone_number'] = ','.join(combined_phones)

    print(
        "Related NTM phone fallback: "
        f"added {added_phone_associations} phone association(s) across "
        f"{affected_deal_rows} Pipedrive deal row(s)."
    )

    return result_df



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
        cm_db_path = 'data/database/ntm_db'

        # Ensure the NTM cache folder exists.
        os.makedirs(cm_db_path, exist_ok=True)
        db_host, db_port, db_user, db_password, db_name = extract_config_info()

        # Read all input files
        abandoned_calls_file_list, pipedrive_file_list = get_input_files()

        # Return error if RC File folder is empty
        if len(abandoned_calls_file_list) == 0:
            return 'rc_empty_main'

        bottoms_up_db, cm_db = get_db_files(bottoms_up_path), get_db_files(cm_db_path) # Read and get database files
        bottoms_up_df = read_bottoms_up(bottoms_up_db) # Bottoms Up Dataframe

        # Comment out if not for testing
        # ----------- start here -----------        
        phone_number_df, email_address_df, serial_numbers_df, cm_db_df = read_cm_live_db(db_host,
                                                                                            db_port,
                                                                                            db_user,
                                                                                            db_password,
                                                                                            db_name) # Live CM Database 
        # If database credentials is wrong
        if phone_number_df is None:
            print('NTM database reading failed. Check the error above.')
            return 'db_wrong'
        # ----------- end here -----------   

        # # Comment out for testing purposes only
        # # ✅ Skip live CM DB read — use latest saved CSVs
        # # ----------- start here -----------  
        # print("Skipping live CM DB read. Loading from saved CSVs instead...")

        # cm_db_path = 'data/database/ntm_db'

        # phone_number_df = pd.read_csv(os.path.join(cm_db_path, 'phone_number.csv'), low_memory=False)
        # email_address_df = pd.read_csv(os.path.join(cm_db_path, 'email_address.csv'), low_memory=False)
        # serial_numbers_df = pd.read_csv(os.path.join(cm_db_path, 'serial_number.csv'), low_memory=False)
        # cm_db_df = pd.read_csv(os.path.join(cm_db_path, 'cm_db.csv'), low_memory=False)
        # # ----------- end here -----------   
        
        file_count = 1 # Counter for Abandoned Calls File
        user_designation, condition_dict = read_json_data()

        # comment out for testing:
        update_pipedrive_data()

        # Read single pipedrive file
        for pipedrive_file in pipedrive_file_list:
            pipedrive_df = pd.read_csv(
                pipedrive_file,
                low_memory=False,
                dtype={'phone_number': 'string'}
            )
            pipedrive_df['phone_number'] = pipedrive_df['phone_number'].apply(
                decode_phone_number_list
            )
            pipedrive_df['Person - Phone - Work'] = pipedrive_df['phone_number']

            # Keep pipedrive_data.csv unchanged, but allow a BUDB phone to
            # inherit a Pipedrive match from another phone on the same BUDB row.
            pipedrive_df = add_related_bottoms_up_phones_to_pipedrive(
                pipedrive_df,
                bottoms_up_df
            )

            # Apply the same related-phone fallback to phone1-phone6 from the
            # same NTM contact row.
            pipedrive_df = add_related_ntm_phones_to_pipedrive(
                pipedrive_df,
                phone_number_df
            )


        # Iterate through list of abandoned_calls files
        for abandoned_calls_file in abandoned_calls_file_list:
            
            warnings.filterwarnings("ignore", category=FutureWarning)

            calls_file_name = abandoned_calls_file.split('\\')[-1]
            print(f'Reading {calls_file_name}.')
            abandoned_calls_df = pd.read_excel(abandoned_calls_file)
            abandoned_calls_df['Contact ID'] = abandoned_calls_df.index

            # Create Follow Up output file
            ani_exist, ani_not_exist, df_exploded = search_ani(abandoned_calls_df, pipedrive_df)
            log_step("Checking if PN exists in Pipedrive",
                **{"PN Exist": ani_exist, "PN Not Exist": ani_not_exist})

            # Get Deal ID from cm database
            fu_final_df, cm_exist_df, cm_not_exist_df = get_cm_deal_id(ani_exist,
                                                                    ani_not_exist,
                                                                    phone_number_df,
                                                                    df_exploded,
                                                                    cm_db_df)
            log_step("Get Deal ID from cm database", **{"Deals exist": fu_final_df})

            # Create FU Output
            rc_df = create_follow_up(fu_final_df, file_count, user_designation, condition_dict)
            log_step("create_follow_up", **{"Follow-up": rc_df})
            
            # Search in Bottoms Up Database
            print("Creating new deals from BU")            
            bottoms_up_not_exist, bottoms_up_output, bottom_up_final_df = create_new_deals_bottoms_up(ani_not_exist,
                                                                                    bottoms_up_df,
                                                                                    file_count)
            log_step("New deals found in BUDB", **{"PN From BUDB": bottoms_up_output})

            # Search in Community Minerals Database
            print("Creating new deals from NTM")
            cm_db_not_exist, cm_db_output, cm_db_final_df = create_new_deals_cm(
                                                                bottoms_up_not_exist,
                                                                phone_number_df,
                                                                email_address_df,
                                                                serial_numbers_df,
                                                                cm_db_df,
                                                                bottoms_up_df,
                                                                file_count)
            log_step("New deals found in NTM", **{"PN From NTM": cm_db_output})

            # Concatenate Bottoms Up and CM then create New Deals output file
            rc_added_new_deals_df = export_new_deals(bottoms_up_output,
                                                        cm_db_output,
                                                        rc_df,
                                                        bottom_up_final_df,
                                                        cm_db_final_df,
                                                        file_count)
            
            # Create No Result output file
            no_result_df = create_no_result(cm_db_not_exist,
                                abandoned_calls_df,
                                file_count)
            log_step("No results", **{"No results from all db": no_result_df})

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