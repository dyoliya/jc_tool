import pandas as pd
import numpy as np
from tabulate import tabulate


'''
This module contains functions that will verify if an ANI Number is existing in Bottoms Up Database\n
and create output files that will contain details of ANI Numbers existing in Bottoms Up Database\n
and ANI Numbers that is not existing in Bottoms Up Database.\n
'''

def search_ani_bottoms_up(final_result_not_exist: pd.DataFrame, bottoms_up_df: pd.DataFrame) -> 'tuple[pd.DataFrame, pd.DataFrame]':
    '''
    Searches From Numbers if it is existing in Bottoms Up Database and outputs a Dataframe of existing records and non existing records.\n

    Parameters:
        `final_result_not_exist (pd.DataFrame)` - Dataframe that contains From Numbers that is not existing in Pipedrive Data.\n
        `bottoms_up_df (pd.DataFrame)` - Pandas Dataframe equivalent of Bottoms Up Database.\n

    Return:
        `bottoms_up_exist (pd.DataFrame)` - This contains From Numbers that is existing in Bottoms Up Database.\n
        `bottoms_up_not_exist (pd.DataFrame)` - This contains From Numbers that is not existing in Bottoms Up Database.\n
    '''

    # from_to_dict = (
    #     final_result_not_exist
    #     .dropna(subset=['From', 'To'])
    #     .set_index('From')['To']
    #     .to_dict()
    # )

    # print(from_to_dict)

    ANI_not_number = final_result_not_exist[~final_result_not_exist['ANI'].str.contains(r'^[0-9]+$', na=False)][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]

    # print("final_result_not_exist table")
    # print(final_result_not_exist.columns.tolist())
    # Filter From Numbers where it only contains numbers and change data type to Int64
    final_result_not_exist['ANI'] = final_result_not_exist[final_result_not_exist['ANI']\
                                                           .str.contains(r'^[0-9]+$', na=False)]\
                                                            ['ANI'].astype('Int64')
    
    
    # Filter entries where it is in Bottoms Up
    bottoms_up_ani_entries = final_result_not_exist[final_result_not_exist['Team'].str.contains('', na=False)][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    
    # print("bottoms_up_ani_entries table")
    # print(bottoms_up_ani_entries.columns.tolist())    
    # Get columns phone1 to phone6 from Bottoms Up Database
    bottoms_up_phone_columns = [f'phone{i}' for i in range(1, 6)]

    # Melt phone numbers per id
    bottoms_up_melted = pd.melt(bottoms_up_df,
                                id_vars=['id'],
                                value_vars=bottoms_up_phone_columns,
                                var_name='phone_type',
                                value_name='phone_number')

    # Check existing From in bottoms_up
    bottoms_up_check_ani = bottoms_up_ani_entries.merge(bottoms_up_melted,
                                                left_on='ANI',
                                                right_on='phone_number',
                                                how='left')
    bottoms_up_check_ani.drop_duplicates(subset=['id', 'ANI'], inplace=True) # Only unique From Number to be checked

    # Add bottoms_up details per id
    bottoms_up_check_ani = bottoms_up_check_ani.merge(bottoms_up_df,
                                                    on='id',
                                                    how='left')
    bottoms_up_exist = bottoms_up_check_ani[bottoms_up_check_ani['phone_number'].notnull()]
    bottoms_up_not_exist = bottoms_up_check_ani[bottoms_up_check_ani['phone_number'].isnull()][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    bottoms_up_not_exist_final = pd.concat([bottoms_up_not_exist, ANI_not_number])
    bottoms_up_not_exist_final['Deal - Deal Summary'] = 'No Information in Email'


    return bottoms_up_exist, bottoms_up_not_exist_final

def add_email_columns(bottoms_up_exist: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Person - Email 1` to `Person - Email 17` columns to final dataframe.\n

    Parameters:
        `bottoms_up_exist (pd.DataFrame)` - This contains ANI Values that is existing in Bottoms Up Database.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added `Person - Email 1` to `Person - Email 17` columns.\n
    '''

    # Melt emails from database
    bottoms_email_columns = [f'email{i}' for i in range(1, 6)]
    bottoms_email_melted = pd.melt(bottoms_up_exist,
                                id_vars=['phone_number'],
                                value_vars=bottoms_email_columns,
                                var_name='email_type',
                                value_name='email')
    bottoms_email_melted.drop_duplicates(subset=['phone_number', 'email'], inplace=True)
    bottoms_email_melted = bottoms_email_melted[(bottoms_email_melted['email'] != '')]

    # Create Email 1 to Email 17 Columns
    bottoms_up_final_column = [
        'Person - Phone',
    ] + [f'Person - Email {i}' for i in range(1, 18)]

    # Create Final Output Dataframe
    bottoms_up_final_df = pd.DataFrame(columns=bottoms_up_final_column)

    # Group by phone_number and get the grouped emails
    grouped = bottoms_email_melted.groupby('phone_number')['email'].apply(list).reset_index()

    # Flatten the emails for easier processing
    emails_flat = []
    for _, row in grouped.iterrows():
        phone_number = row['phone_number']
        emails = row['email'][:17]  # Take only the first 17 emails
        emails_flat.append((phone_number, emails))

    # Fill bottoms_up_final_df with the flattened email data
    rows_to_add = []
    for phone_number, emails in emails_flat:
        # Create a dictionary for the row data
        row_data = {'Person - Phone': phone_number}
        row_data.update({f'Person - Email {i+1}': email for i, email in enumerate(emails)})
        rows_to_add.append(row_data)

    # Append rows to bottoms_up_final_df using pd.concat
    bottoms_up_final_df = pd.concat([bottoms_up_final_df, pd.DataFrame(rows_to_add)], ignore_index=True).drop_duplicates()
    

    return bottoms_up_final_df


def add_serial_number(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Serial Number` column to final dataframe.\n

    Parameters:
        `bottoms_up_exist (pd.DataFrame)` - This contains ANI Values that is existing in Bottoms Up Database.\n
        `bottoms_up_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on spefications.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added `Deal - Serial Number` column.\n
    '''

    # Join all serial numbers per phone number
    added_serials_df = bottoms_up_exist.groupby('phone_number').agg(
        combined_serials = ('serial_number', lambda x: ' | '.join(filter(None, x)))
    ).reset_index()

    # Add Serial Numbers to final dataframe
    bottoms_up_final_df = added_serials_df.merge(bottoms_up_final_df,
                                                left_on='phone_number',
                                                right_on='Person - Phone',
                                                how='left')
    bottoms_up_final_df.rename(columns={'combined_serials': 'Deal - Serial Number'}, inplace=True)


    return bottoms_up_final_df

#JULIA
def add_serial_group_fields(bottoms_up_exist: pd.DataFrame, bottoms_up_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each phone_number in bottoms_up_exist:
      - serial_group_ids: concatenate ALL 'id' values for ALL serials found for that phone (in serial order),
        unique (no duplicates), joined by "|".
      - serial_group_contact_group_ids: use the contact_group_id from the FIRST serial only (first non-null).
      - serial_group_sum_of_all_offers: computed for the FIRST serial only (distinct contact_group_id sums to avoid double-counting).
    Returns one row per phone_number.
    """
    # Normalize serial strings coming from bottoms_up_exist (preserve order, remove blanks)
    serials_by_phone = bottoms_up_exist.groupby('phone_number')['serial_number'] \
        .apply(lambda seq: [s.strip() for s in seq if pd.notna(s) and str(s).strip() != ""]) \
        .reset_index(name='serials')

    rows = []
    for _, r in serials_by_phone.iterrows():
        phone = r['phone_number']
        serials = r['serials']  # ordered unique-ish list from bottoms_up_exist order

        # --- Part A: collect ids per serial preserving serial order and avoid duplicates
        ids_seen = []
        per_serial_ids = []  # for debug
        for s in serials:
            # match using trimmed string to be robust to whitespace
            matches_for_serial = bottoms_up_df[bottoms_up_df['serial_number'].astype(str).str.strip() == str(s).strip()]
            ids_for_s = matches_for_serial['id'].dropna().astype(str).tolist()
            # keep order, avoid duplicates across serials
            new_ids = []
            for _id in ids_for_s:
                if _id not in ids_seen:
                    ids_seen.append(_id)
                    new_ids.append(_id)
            per_serial_ids.append((s, ids_for_s))
        serial_group_ids = " | ".join(ids_seen) if ids_seen else ""

        # --- Part B: first serial only for contact_group_id and offers
        if serials:
            first_serial = serials[0]
            matches_first = bottoms_up_df[bottoms_up_df['serial_number'].astype(str).str.strip() == str(first_serial).strip()]

            # contact_group_id: take FIRST non-null unique value (as string)
            cg_vals = matches_first['contact_group_id'].dropna().unique().tolist()
            serial_group_contact_group_ids = (
                str(int(cg_vals[0])) if cg_vals and isinstance(cg_vals[0], (float, int)) else str(cg_vals[0]) if cg_vals else ""
            )
            # offers (first serial only): same logic as before
            if matches_first['contact_group_id'].dropna().empty:
                serial_group_sum_of_all_offers = matches_first['sum_of_all_offers'].sum()
            else:
                serial_group_sum_of_all_offers = matches_first.drop_duplicates('contact_group_id')['sum_of_all_offers'].sum()
        else:
            serial_group_contact_group_ids = ""
            serial_group_sum_of_all_offers = 0.0

        rows.append({
            'phone_number': phone,
            'serial_group_ids': serial_group_ids,
            'serial_group_contact_group_ids': serial_group_contact_group_ids,
            'serial_group_sum_of_all_offers': serial_group_sum_of_all_offers
        })

    serial_group_df = pd.DataFrame(rows)

    return serial_group_df

def add_deal_title(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Title` column to final dataframe.\n

    Parameters:
        `bottoms_up_exist (pd.DataFrame)` - This contains ANI Values that is existing in Bottoms Up Database.\n
        `bottoms_up_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on spefications.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added `Deal - Title` column.\n
    '''

    # Combine first and last name column
    # bottoms_up_exist['first_last'] = bottoms_up_exist['first_name'].str.title() + ' ' + bottoms_up_exist['last_name'].str.title()
    bottoms_up_exist['first_last'] = bottoms_up_exist.apply(lambda row: 
        row['first_name'].title() if pd.notna(row['first_name']) and pd.isna(row['last_name']) else 
        (row['first_name'].title() + ' ' + row['last_name'].title()) if pd.notna(row['first_name']) and pd.notna(row['last_name']) else 
        '', axis=1)
    
    grouped = bottoms_up_exist.groupby(['phone_number', 'target_state'])['target_county'].apply(list).reset_index()

    # Function to format the county names
    def format_counties(counties):
        unique_counties = list(set(counties))
        n = len(unique_counties)
        if n == 1:
            return unique_counties[0].title() + " County"
        elif n == 2:
            return unique_counties[0].title() + " and " + unique_counties[1].title() + " County"
        elif n > 2:
            return ', '.join([county.title() for county in unique_counties[:-1]]) + " and " + unique_counties[-1].title() + " County"

    # Apply the formatting function to the grouped data
    grouped['formatted'] = grouped['target_county'].apply(format_counties)

    aggregated = grouped.groupby('phone_number').apply(
        lambda x: ' and '.join([f"{row['formatted']}, {row['target_state'].upper()}" for _, row in x.iterrows()])
    ).reset_index(name='formatted_result')
    final_result = bottoms_up_exist[['phone_number', 'first_last']].drop_duplicates().merge(aggregated, on='phone_number', how='left')
    final_result['Deal - Title'] = final_result.apply(lambda row: f"{row['first_last']} {row['formatted_result']}", axis=1)

    # Create pandas function to add Deal - Deal Title
    def check_name_address(row):
        if row['first_last'].nunique() == 0:
            return None
        elif row['first_last'].nunique() == 1:
            counties = row['target_county'].unique()
            state = row['target_state'].iloc[0]
            if len(counties) == 1:
                return f"{row['first_last'].iloc[0]} {counties[0].title()} County, {state}"
            elif len(counties) == 2:
                return f"{row['first_last'].iloc[0]} {counties[0].title()} and {counties[1].title()} County, {state}"
            else:
                # counties_list = ', '.join(counties[:-1])
                counties_list = ', '.join([county.title() for county in counties[:-1]])
                return f"{row['first_last'].iloc[0]} {counties_list}, and {counties[-1].title()} County, {state}"
        else:
            return f"Multiple entries {row['phone_number'].iloc[0]}"

    # Add Deal - Title column to final dataframe
    # deal_title_column = bottoms_up_exist.groupby('phone_number').apply(check_name_address).reset_index()
    bottoms_up_final_df = bottoms_up_final_df.merge(final_result[['phone_number', 'Deal - Title']], on='phone_number', how='left')
    # bottoms_up_final_df.rename(columns={0: 'Deal - Title'}, inplace=True)
    # deal_title_column = None


    return bottoms_up_final_df


def add_deal_stage(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:

    # Bring in Team + date/time fields (avoid dupes exploding rows)
    deal_stage_cols = bottoms_up_exist[
        ['ANI', 'Team', 'Date and Time', 'Date', 'Time', 'Contact ID']
    ].drop_duplicates(subset=['ANI'])

    bottoms_up_final_df = bottoms_up_final_df.merge(
        deal_stage_cols,
        left_on='phone_number',
        right_on='ANI',
        how='left'
    )

    # Default stage
    bottoms_up_final_df['Deal - Stage'] = 'Follow Up - Bottoms Up (White Glove Pipeline)'

    # Override for BU Small
    small_mask = bottoms_up_final_df['Team'].isin(['Bottoms Up - Small', 'Bottoms Up - Sml'])
    bottoms_up_final_df.loc[small_mask, 'Deal - Stage'] = 'Follow Up - Junior Sales (Junior Sales Team Pipeline)'


    return bottoms_up_final_df


def add_deal_county(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - County` column to final dataframe.\n

    Parameters:
        `bottoms_up_exist (pd.DataFrame)` - This contains ANI Values that is existing in Bottoms Up Database.\n
        `bottoms_up_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on spefications.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added `Deal - County` column.\n
    '''

    def add_county(group):

        # if group['state'].nunique() > 1:

        country_list = group['target_county'].tolist()
        state_list = group['target_state'].tolist()

        # Create a set of unique (country, state) pairs
        unique_combinations = set((country.title(), state) for country, state in zip(country_list, state_list))

        # Join the unique combinations into a formatted string
        result = '|'.join([f"{country} County, {state}" for country, state in unique_combinations])

        return result

    # Add Deal - County to final dataframe
    deal_county_column = bottoms_up_exist.groupby('phone_number').apply(add_county).reset_index()
    bottoms_up_final_df = bottoms_up_final_df.merge(deal_county_column, on='phone_number', how='left')
    bottoms_up_final_df.drop_duplicates(subset='phone_number', inplace=True)
    bottoms_up_final_df.rename(columns={0: 'Deal - County'}, inplace=True)
    deal_county_column = None
    

    return bottoms_up_final_df


def add_mailing_address(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Person - Mailing Address` column to final dataframe.\n

    Parameters:
        `bottoms_up_exist (pd.DataFrame)` - This contains ANI Values that is existing in Bottoms Up Database.\n
        `bottoms_up_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on spefications.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added `Person - Mailing Address` column.\n
    '''

    # Define pandas function to add Deal - Mailing Address
    def add_mailing_address(row):
        # Filter out blank addresses
        non_blank_row = row[row['address'] != '']
        def clean(val):
            if pd.isna(val) or val is None or str(val).strip() == "":
                return ""
            return str(val).strip()

        # Check for unique addresses after filtering
        if non_blank_row['address'].nunique() == 0:
            return None
        elif non_blank_row['address'].nunique() == 1:
            address = clean(non_blank_row['address'].iloc[0])
            city = clean(non_blank_row['city'].iloc[0])
            state = clean(non_blank_row['state'].iloc[0])
            postal_code = clean(non_blank_row['postal_code'].iloc[0])

            parts = [address, city, state, postal_code, "USA"]
            parts = [p for p in parts if p]  # remove empty values

            return ", ".join(parts)

        else:
            return 'Multiple address entries'
    
    # Add Person - Mailing Address to final dataframe
    mailing_address_column = bottoms_up_exist.groupby('phone_number').apply(add_mailing_address).reset_index(name='Person - Mailing Address')
    bottoms_up_final_df = bottoms_up_final_df.merge(mailing_address_column, on='phone_number', how='left')
    bottoms_up_final_df.rename(columns={0: 'Person - Mailing Address'}, inplace=True)
    mailing_address_column = None

    
    return bottoms_up_final_df


def add_note_content(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Note Content` column to final dataframe.\n

    Parameters:
        `bottoms_up_exist (pd.DataFrame)` - This contains ANI Values that is existing in Bottoms Up Database.\n
        `bottoms_up_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on spefications.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added `Note Content` column.\n
    '''

    # Define needed columns and add to final dataframe
    date_time_column = bottoms_up_exist[['ANI']]
    bottoms_up_final_df = bottoms_up_final_df.merge(date_time_column, left_on='phone_number', right_on='ANI', how='left')
    bottoms_up_final_df.drop_duplicates(subset='phone_number', inplace=True)
    bottoms_up_final_df['Note Content'] = bottoms_up_final_df.apply(
        lambda row: f"JC abandoned call from {row['phone_number']} on {row['Date and Time']}",
        axis=1
    )


    return bottoms_up_final_df


def add_person_name(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Person - Name` column to final dataframe.\n

    Parameters:
        `bottoms_up_exist (pd.DataFrame)` - This contains ANI Values that is existing in Bottoms Up Database.\n
        `bottoms_up_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on spefications.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added `Person - Name` column.\n
    '''

    # Define needed columns and add to final dataframe
    names_column = bottoms_up_exist[['phone_number', 'first_name', 'middle_name', 'last_name']]
    bottoms_up_final_df = bottoms_up_final_df.merge(names_column, on='phone_number', how='left')
    bottoms_up_final_df.drop_duplicates('phone_number', inplace=True)

    def process_names(row):
        first_name = '' if pd.isna(row['first_name']) else row['first_name']
        middle_name = '' if pd.isna(row['middle_name']) else row['middle_name']
        last_name = '' if pd.isna(row['last_name']) else row['last_name']
        
        if first_name != '' and last_name == '':
            # Split and title each word in first_name
            return ' '.join([part.title() for part in first_name.split()])
        
        elif first_name != '' and last_name != '':
            if middle_name != '':
                # Capitalize first_name, middle_name, last_name and join with space
                return ' '.join([part.title() for part in [first_name, middle_name, last_name]])
            else:
                # Capitalize first_name and last_name and join with space
                return f"{first_name.title()} {last_name.title()}"
        
        else:
            return None  # or any other handling for NaN values

    bottoms_up_final_df['Person - Name'] = bottoms_up_final_df.apply(process_names, axis=1)

    return bottoms_up_final_df



def add_constant_columns(bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds columns to the final dataframe where values are all constants.\n

    Parameters:
        `bottoms_up_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on spefications.\n

    Return:
        `bottoms_up_final_df (pd.DataFrame)` - Dataframe with added constant columns.\n
    '''

    # Define constant values columns
    bottoms_up_final_df['Person - Phone'] = bottoms_up_final_df['phone_number']
    bottoms_up_final_df['Person - Phone 1'] = bottoms_up_final_df['phone_number']
    bottoms_up_final_df['Person - Email'] = bottoms_up_final_df['Person - Email 1']
    bottoms_up_final_df['Deal - Label'] = 'TARGETED MARKETING'
    bottoms_up_final_df['Deal - Preferred Communication Method'] = 'Phone'
    bottoms_up_final_df['Deal - Abandoned Call Flag'] = 'Abandoned Call - Call Center'
    bottoms_up_final_df['Deal - Inbound Medium'] = 'Abandoned Call'
    bottoms_up_final_df['Deal - Unique Database ID'] = ''
    bottoms_up_final_df['Deal - Deal Summary'] = 'Completed'
    bottoms_up_final_df['Deal - Pipedrive Analyst Tracking Flag'] = 'PA - Joyce'
    bottoms_up_final_df['Deal - Phone Number Format'] = 'Complete'
    bottoms_up_final_df['Person - Phone 1 - Data Source'] = 'Mineral Owner'
    bottoms_up_final_df['Person - Mailing Address - Data Source'] = 'MineralHolders - Bottoms Up'
    bottoms_up_final_df['Deal - Marketing Medium'] = 'Text'
    bottoms_up_final_df['Deal - Deal Status'] = ''
    bottoms_up_final_df['Deal - Deal creation date'] = bottoms_up_final_df['Date and Time']
    bottoms_up_final_df['Person - Timezone'] = ''
    bottoms_up_final_df['Deal - Owner'] = 'Stephanie'


    return bottoms_up_final_df



def filter_multiple_entries(bottoms_up_final_df, bottoms_up_not_exist):

    # Filter single entries from bottoms_up_final_df
    single_entries_df = bottoms_up_final_df[~(bottoms_up_final_df['Deal - Title'].str.contains('Multiple', na=False) |\
                                        bottoms_up_final_df['Person - Mailing Address'].str.contains('Multiple', na=False))]
       
    # Filter multiple entries from bottoms_up_final_df
    multiple_entries_df = bottoms_up_final_df[bottoms_up_final_df['Deal - Title'].str.contains('Multiple', na=False) |\
                                        bottoms_up_final_df['Person - Mailing Address'].str.contains('Multiple', na=False)] \
                                        [['phone_number', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    multiple_entries_df['Deal - Deal Summary'] = 'Common Name Error'
    multiple_entries_df.rename(columns={'phone_number': 'ANI'}, inplace=True)
    
    # Add multiple entries to bottoms_up_not_exist
    bottoms_up_not_exist_final = pd.concat([bottoms_up_not_exist, multiple_entries_df])

    print("end filter_multiple_entries\n")
    return single_entries_df, bottoms_up_not_exist_final



def create_new_deals_bottoms_up(ani_not_exist: pd.DataFrame, bottoms_up_df: pd.DataFrame, file_count: int) -> 'tuple[pd.DataFrame, pd.DataFrame | None]':
    '''
    This is the main driver function of this module.\n
    Creates Pandas Dataframe of ANI Entries that is existing and not existing in Bottoms Up Database.\n

    Parameters:
        `ani_not_exist (pd.DataFrame)` - Entries where ANI Number is not existing in Pipedrive Data.\n
        `bottoms_up_df (pd.DataFrame)` - Pandas Dataframe equivalent of Bottoms Up Database.\n
        `file_count (int)` - Counter of abandoned call files being processed.\n

    Return:
        `bottoms_up_not_exist` - Pandas DataFrame that contains ANI Numbers that is not existing in Bottoms Up Database.\n
        `bottoms_up_final_output_data` - This contains the final output data that contains multiple columns of details imported from Bottoms Up Database.\n
        `pd.DataFrame()` - An empty Pandas DataFrame if `bottoms_up_exist` is empty.
    '''
    columns = [
        'Deal - Deal creation date',
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
        'Person - Timezone',
                #JULIA
        'Deal - BU Database ID',
        'Deal - Contact Group ID',
        'Deal - Value'
    ]

    if ani_not_exist.empty:
        return pd.DataFrame(columns=columns), pd.DataFrame(), pd.DataFrame()

    # Search ANI Numbers in Bottoms Up Database
    # bottoms_up_exist, bottoms_up_not_exist = search_ani(ani_not_exist, bottoms_up_df)

    bottoms_up_exist, bottoms_up_not_exist = search_ani_bottoms_up(ani_not_exist, bottoms_up_df)

    if bottoms_up_exist.empty:
        return bottoms_up_not_exist, pd.DataFrame(), pd.DataFrame() # Return empty dataframe if bottoms_up_exist is empty

    else:
        
        # Run all functions that creates columns
        bottoms_up_final_df = add_email_columns(bottoms_up_exist)
        added_serial_df = add_serial_number(bottoms_up_exist, bottoms_up_final_df)
        
        # Get the serial group fields per phone_number
        serial_group_df = add_serial_group_fields(bottoms_up_exist, bottoms_up_df)

        # Merge them safely on phone_number
        added_serial_df = added_serial_df.merge(
            serial_group_df[['phone_number', 'serial_group_ids', 'serial_group_contact_group_ids', 'serial_group_sum_of_all_offers']],
            on='phone_number',
            how='left'
        )
        # Rename to your final schema
        added_serial_df.rename(columns={
            'serial_group_ids': 'Deal - BU Database ID',
            'serial_group_contact_group_ids': 'Deal - Contact Group ID',
            'serial_group_sum_of_all_offers': 'Deal - Value'
        }, inplace=True)

        added_deal_title_df = add_deal_title(bottoms_up_exist, added_serial_df)
        added_deal_stage_df = add_deal_stage(bottoms_up_exist, added_deal_title_df)
        added_deal_county_df = add_deal_county(bottoms_up_exist, added_deal_stage_df)
        added_mailing_address_df = add_mailing_address(bottoms_up_exist, added_deal_county_df)
        added_note_content_df = add_note_content(bottoms_up_exist, added_mailing_address_df)
        added_person_name_df = add_person_name(bottoms_up_exist, added_note_content_df)
        added_constants_df = add_constant_columns(added_person_name_df)
        bottoms_up_final_df, bottoms_up_not_exist_final = filter_multiple_entries(added_constants_df, bottoms_up_not_exist)
        
        # Select columns that will be included in the final output data
        bottoms_up_final_output_data = bottoms_up_final_df[columns]
        

        return bottoms_up_not_exist_final, bottoms_up_final_output_data, bottoms_up_final_df