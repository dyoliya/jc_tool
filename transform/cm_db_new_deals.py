import pandas as pd


def search_ani(bottoms_up_not_exist: pd.DataFrame, phone_number_df: pd.DataFrame) -> 'tuple[pd.DataFrame, pd.DataFrame]':
    '''
    Searches the ANI Numbers to CM Database, whose numbers are not existing in Pipedrive Data.\n

    Parameters:
        `final_result_not_exist (pd.DataFrame)` - Pandas Dataframe that contains ANI Numbers that are not existing in Pipedrive Data.\n
        `phone_number_df (pd.DataFrame)` - Pandas Dataframe that contains all phone number entries and corresponding database id from CM Database.\n
    
    Return:
        `cm_db_exist (pd.DataFrame)` - Pandas DataFrame that contains ANI Numbers that is existing in CM Database.\n
        `cm_db_not_exist (pd.DataFrame)` - Pandas DataFrame that contains ANI Number that is not existing in CM Database.\n
    '''

    # Filter entries where it is not Bottoms Up
    cm_db_ani_entries = bottoms_up_not_exist
    cm_db_ani_entries = cm_db_ani_entries[(cm_db_ani_entries['ANI'] != '(blank)') & (cm_db_ani_entries['ANI']).notnull()]
    
    # Search ANI if existing in CM Database
    cm_db_check_ani = cm_db_ani_entries.merge(phone_number_df,
                                            left_on='ANI',
                                            right_on='phone_number',
                                            how='left')
    # Remove duplicates by From
    cm_db_check_ani.drop_duplicates(subset=['ANI'], inplace=True)

    # Keep only one phone_number column
    if 'phone_number_x' in cm_db_check_ani.columns and 'phone_number_y' in cm_db_check_ani.columns:
        # Prioritize the one that matched via 'From'
        cm_db_check_ani['phone_number'] = cm_db_check_ani['phone_number_x'].combine_first(cm_db_check_ani['phone_number_y'])
        cm_db_check_ani.drop(columns=['phone_number_x', 'phone_number_y'], inplace=True)
    elif 'phone_number_x' in cm_db_check_ani.columns:
        cm_db_check_ani.rename(columns={'phone_number_x': 'phone_number'}, inplace=True)
    elif 'phone_number_y' in cm_db_check_ani.columns:
        cm_db_check_ani.rename(columns={'phone_number_y': 'phone_number'}, inplace=True)

    # cm_db_check_ani.drop_duplicates(subset=['ANI'], inplace=True)
    cm_db_exist = cm_db_check_ani[cm_db_check_ani['id'].notnull()]
    cm_db_not_exist = cm_db_check_ani[cm_db_check_ani['id'].isna()][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]

    cm_db_not_exist_final = cm_db_ani_entries[
        ~cm_db_ani_entries['ANI'].isin(cm_db_exist['ANI'])
    ].copy()
    
    return cm_db_exist, cm_db_not_exist_final


def add_email_columns(cm_db_exist: pd.DataFrame, email_address_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds Email 1 to Email 17 columns to the final dataframe.\n

    Parameters:
        `cm_db_exist (pd.DataFrame)` - Pandas DataFrame that contains ANI Numbers and other details that is existing in CM Database.\n
        `email_address_df (pd.DataFrame)` - Pandas DataFrame that contains all email entries and corresponding database id from CM Database.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Final dataframe that contains all emails per ANI Number and will be added more columns based on specification.\n
    '''

    # Create Email 1 to Email 17 Columns
    email_cols = [
        'Deal - Unique Database ID',
    ] + [f'Person - Email {i}' for i in range(1, 18)]
    cm_db_email_columns = pd.DataFrame(columns=email_cols)

    # Filter Email Address Dataframe from Community Minerals Database
    filter_email_address_df = email_address_df[email_address_df['id'].isin(cm_db_exist['id'])]

    # Group by phone_number and get the grouped emails
    grouped = filter_email_address_df.groupby('id')['email_address'].apply(list).reset_index()

    # Flatten the emails for easier processing
    emails_flat = []
    for _, row in grouped.iterrows():
        id = row['id']
        emails = row['email_address'][:17]  # Take only the first 17 emails
        emails_flat.append((id, emails))

    # Fill bottoms_up_final_df with the flattened email data
    rows_to_add = []
    for id, emails in emails_flat:
        # Create a dictionary for the row data
        row_data = {'Deal - Unique Database ID': id}
        row_data.update({f'Person - Email {i+1}': email for i, email in enumerate(emails)})
        rows_to_add.append(row_data)

    # Append rows to bottoms_up_final_df using pd.concat
    email_address_final_df = pd.concat([cm_db_email_columns, pd.DataFrame(rows_to_add)], ignore_index=True).drop_duplicates()

    # Add email address dataframe to the final dataframe
    cm_db_final_df = cm_db_exist.merge(email_address_final_df,
                                        left_on='id',
                                        right_on='Deal - Unique Database ID',
                                        how='left')

    return cm_db_final_df


def add_serial_number(cm_db_final_df: pd.DataFrame, serial_numbers_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Serial Number` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added emails column.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Serial Number` column.\n
    '''

    # Merge serial numbers dataframe from CM Database to final dataframe
    cm_db_final_df = cm_db_final_df.merge(serial_numbers_df,
                                        left_on='Deal - Unique Database ID',
                                        right_on='id',
                                        how='left').rename(columns={'serial_numbers': 'Deal - Serial Number'})

    return cm_db_final_df


def add_cm_db_details(cm_db_final_df: pd.DataFrame, cm_db_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Merges the rest of the column needed from the CM Database to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with column based on specifications.\n
        `cm_db_df (pd.DataFrame)` - Pandas Dataframe equivalent of data from CM Database.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added CM Database columns.\n
    '''

    # Merge the rest of the column from CM Database to final dataframe
    cm_db_df.rename(columns={'id': 'Deal - Unique Database ID'}, inplace=True)
    cm_db_final_df = cm_db_final_df.merge(cm_db_df,
                                        on='Deal - Unique Database ID',
                                        how='left')

    return cm_db_final_df


def add_new_database_id(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Unique Database ID` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added CM Database details.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Unique Database ID` column.\n
    '''

    # Define pandas function that will add deal unique database ID
    def assign_check_id(group):
        if group['Deal - Unique Database ID'].nunique() == 0:
            return None
        elif group['Deal - Unique Database ID'].nunique() == 1:
            return group['Deal - Unique Database ID'].iloc[0]
        else:
            return 'Multiple Database ID'

    # Apply pandas function and assign to a column
    new_db_id = cm_db_final_df.groupby('phone_number').apply(assign_check_id).reset_index()
    new_db_id.columns = ['phone_number', 'new_db_id']
    cm_db_final_df = cm_db_final_df.merge(new_db_id, on='phone_number', how='left')
    cm_db_final_df.drop('Deal - Unique Database ID', axis=1, inplace=True)
    cm_db_final_df.rename(columns={'new_db_id': 'Deal - Unique Database ID'}, inplace=True)

    return cm_db_final_df


def add_deal_title(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Title` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Unique Database ID` column.\n
    
    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Title` column.\n
    '''

    # Combine first and last name and assign to column
    cm_db_final_df['first_last'] = cm_db_final_df.apply(lambda row: 
        row['first_name'].title() if pd.notna(row['first_name']) and pd.isna(row['last_name']) else 
        (row['first_name'].title() + ' ' + row['last_name'].title()) if pd.notna(row['first_name']) and pd.notna(row['last_name']) else 
        '', axis=1)

    grouped = cm_db_final_df.groupby(['phone_number', 'state'])['country'].apply(list).reset_index()

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
    grouped['formatted'] = grouped['country'].apply(format_counties)

    aggregated = grouped.groupby('phone_number').apply(
        lambda x: ' and '.join([f"{row['formatted']}, {row['state'].upper()}" for _, row in x.iterrows()])
    ).reset_index(name='formatted_result')
    final_result = cm_db_final_df[['phone_number', 'first_last']].drop_duplicates().merge(aggregated, on='phone_number', how='left')
    final_result['Deal - Title'] = final_result.apply(lambda row: f"{row['first_last']} {row['formatted_result']}", axis=1)
    cm_db_final_df = cm_db_final_df.merge(final_result[['phone_number', 'Deal - Title']], on='phone_number', how='left')

    return cm_db_final_df


def add_deal_county(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - County` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Title` column.\n
    
    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - County` column.\n
    '''

    # Define pandas function that will create deal county column
    def add_county(group):

        # if group['state'].nunique() > 1:

        country_list = group['country'].tolist()
        state_list = group['state'].tolist()

        # Create a set of unique (country, state) pairs
        unique_combinations = set((country.title(), state) for country, state in zip(country_list, state_list))

        # Join the unique combinations into a formatted string
        result = '|'.join([f"{country} County, {state}" for country, state in unique_combinations])

        return result


    # Create the "Deal - County" for unique phone numbers
    unique_deals = cm_db_final_df.groupby('phone_number').apply(add_county).reset_index()
    unique_deals.columns = ['phone_number', 'Deal - County']
    cm_db_final_df = cm_db_final_df.merge(unique_deals, on='phone_number', how='left')

    return cm_db_final_df


def add_mailing_address(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Person - Mailing Address` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - County` column.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Person - Mailing Address` column.\n
    '''

    # Define pandas function that will create person mailing address
    def add_mailing_address(row):
        def clean(val):
            if pd.isna(val) or val is None or str(val).strip() == "":
                return ""
            return str(val).strip()

        if row['address'].nunique() == 0:
            return None
        elif row['address'].nunique() == 1:
            address = clean(row['address'].iloc[0])

            if not address:
                return None

            city = clean(row['city'].iloc[0])
            state = clean(row['state_address'].iloc[0])
            postal_code = clean(row['postal_code'].iloc[0])

            parts = [address, city, state, postal_code, "USA"]
            parts = [p for p in parts if p]

            return ", ".join(parts)
        else:
            return "Multiple address entries"
    
    # Apply pandas function and assign to a column
    mailing_address = cm_db_final_df.groupby('phone_number').apply(add_mailing_address).reset_index()
    mailing_address.columns = ['phone_number', 'Person - Mailing Address']
    cm_db_final_df = cm_db_final_df.merge(mailing_address, on='phone_number', how='left')

    return cm_db_final_df


def add_note_content(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Note Content` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on specifications.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Dataframe with added `Note Content` column.\n
    '''

    # Apply pandas function and assign to a column
    cm_db_final_df['Note Content'] = cm_db_final_df.apply(
        lambda row: f"JC abandoned call from {row['ANI']} on {row['Date and Time']}",
        axis=1
    )


    return cm_db_final_df


def add_person_name(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Person - Name` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on specifications.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Dataframe with added `Person - Name` column.\n
    '''

    # Define pandas function that will create person name
    def process_names(row):
        first_name = row['first_name']
        middle_name = row['middle_name']
        last_name = row['last_name']
        
        if pd.notna(first_name) and pd.isna(last_name):
            # Split and capitalize each word in first_name
            return ' '.join([part.title() for part in first_name.split()])
        
        elif pd.notna(first_name) and pd.notna(last_name):
            if pd.notna(middle_name):
                # Capitalize first_name, middle_name, last_name and join with space
                return ' '.join([part.title() for part in [first_name, middle_name, last_name]])
            else:
                # Capitalize first_name and last_name and join with space
                return f"{first_name.title()} {last_name.title()}"
        
        else:
            return None  # or any other handling for NaN values

    # Apply the function to create the new column
    cm_db_final_df['Person - Name'] = cm_db_final_df.apply(process_names, axis=1)

    
    return cm_db_final_df


def add_marketing_medium(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Marketing Medium` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on specifications.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Dataframe with added `Deal - Marketing Medium` column.\n
    '''

    # Create pandas function that will add marketing medium column to the final dataframe
    def marketing_medium(row):
        team = row.get('Team')

        if team in ('Ringless Voicemail - LG', 'RVM - LG'):
            return 'RVM'
        elif team == 'Call Center':
            return 'Direct Mail'
        elif team in ('Lead Generation', 'LG'):
            return 'Cold Call'
        else:
            return 'Direct Mail'

    # Apply pandas function and assign to column
    cm_db_final_df['Deal - Marketing Medium'] = cm_db_final_df.apply(marketing_medium, axis=1)


    return cm_db_final_df


def add_constant_columns(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds columns to the final dataframe where values are all constants.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Final output dataframe that contains columns based on specifications.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Dataframe with added constant columns.\n
    '''

    # Define and add constant columns to the final dataframe
    cm_db_final_df['Person - Phone'] = cm_db_final_df['phone_number']
    cm_db_final_df['Person - Phone 1'] = cm_db_final_df['phone_number']
    cm_db_final_df['Person - Email'] = cm_db_final_df['Person - Email 1']
    cm_db_final_df['Deal - Label'] = ''
    cm_db_final_df['Deal - Preferred Communication Method'] = 'Phone'
    cm_db_final_df['Deal - Abandoned Call Flag'] = 'Abandoned Call - Call Center'
    cm_db_final_df['Deal - Inbound Medium'] = 'Abandoned Call'
    cm_db_final_df['Deal - Deal Summary'] = 'Completed'
    cm_db_final_df['Deal - Pipedrive Analyst Tracking Flag'] = 'PA - Joyce'
    cm_db_final_df['Deal - Phone Number Format'] = 'Complete'
    cm_db_final_df['Person - Phone 1 - Data Source'] = 'Mineral Owner'
    cm_db_final_df['Person - Mailing Address - Data Source'] = cm_db_final_df['data_source']
    cm_db_final_df['Deal - Stage'] = 'Staging - Qualifying'
    cm_db_final_df['Deal - Deal Status'] = ''
    cm_db_final_df['Person - Timezone'] = ''
    cm_db_final_df['Deal - Owner'] = 'Stephanie'
    cm_db_final_df['Deal - Marketing Medium'] = 'Text'
    cm_db_final_df.drop_duplicates(subset=['ANI'], inplace=True) # Remove duplicated ANI Numbers


    return cm_db_final_df


def filter_multiple_entries(cm_db_final_df: pd.DataFrame, cm_db_not_exist: pd.DataFrame) -> 'tuple[pd.DataFrame, pd.DataFrame]':
    '''
    Filters the final dataframe if it is a multiple entry row and combines it to the no result output file.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with all of the columns from specification.\n
        `cm_db_not_exist (pd.DataFrame)` - Reference variable of a Pandas DataFrame for ANI Numbers that is not existing in CM Database.\n
    
    Return:
        `single_entries_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame for entries that are not multiple entries.\n
        `cm_db_not_exist_final (pd.DataFrame)` - Reference variable of a Pandas DataFrame with concatenated multiple entries and not existing entries.\n
    '''
    cm_db_final_df['Deal - Unique Database ID'] = cm_db_final_df['Deal - Unique Database ID'].astype('str')

    # Filter single entries from cm_db_final_df
    single_entries_df = cm_db_final_df[~(cm_db_final_df['Deal - Title'].str.contains('Mutiple', na=False) |\
                                        cm_db_final_df['Person - Mailing Address'].str.contains('Multiple', na=False) |\
                                        cm_db_final_df['Deal - Unique Database ID'].str.contains('Multiple', na=False))]
    
    # Filter multiple entries from cm_db_final_df
    multiple_entries_df = cm_db_final_df[cm_db_final_df['Deal - Title'].str.contains('Mutiple', na=False) |\
                                        cm_db_final_df['Person - Mailing Address'].str.contains('Multiple', na=False) |\
                                        cm_db_final_df['Deal - Unique Database ID'].str.contains('Multiple', na=False)] \
                                        [['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    multiple_entries_df['Deal - Deal Summary'] = 'Common Name Error'
    
    # Add multiple entries to cm_db_not_exist
    cm_db_not_exist_final = pd.concat([cm_db_not_exist, multiple_entries_df])


    return single_entries_df, cm_db_not_exist_final


def create_new_deals_cm(bottoms_up_not_exist: pd.DataFrame,
                        phone_number_df: pd.DataFrame,
                        email_address_df: pd.DataFrame,
                        serial_numbers_df: pd.DataFrame,
                        cm_db_df: pd.DataFrame) -> 'tuple[pd.DataFrame, pd.DataFrame | None]':
    '''
    This is the main driver function of this module.\n
    Creates Pandas Dataframe of ANI Entries that is existing and not existing in Community Minerals Database.\n

    Parameters:
        `ani_not_exist (pd.DataFrame)` - Entries where ANI Number is not existing in Pipedrive Data.\n
        `phone_number_df (pd.DataFrame)` - Pandas Dataframe equivalent of `contact_phone_numbers` table from CM Database.\n
        `email_address_df (pd.DataFrame)` - Pandas Dataframe equivalent of `contact_email_addresses` table from CM Database.\n
        `serial_numbers_df (pd.DataFrame)` - Pandas DataFrame equivalent of `contact_serial_numbers` table from CM Database.\n
        `cm_db_df (pd.DataFrame)` - This Pandas Dataframe contains additional details per ANI Number like name, address, county, etc.\n

    Return:
        `cm_db_not_exist (pd.DataFrame)` - Pandas DataFrame that contains ANI Numbers that is not existing in CM Database.\n
        `cm_db_final_output_data (pd.DataFrame)` - This contains the final output data that contains multiple columns of details imported from CM Database.\n
        `pd.DataFrame()` - An empty Pandas DataFrame if `cm_db_exist` is empty.
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
        'Person - Timezone'
    ]

    if bottoms_up_not_exist.empty:
        return pd.DataFrame(columns=columns), pd.DataFrame(), pd.DataFrame() 
    
    else:
        cm_db_exist, cm_db_not_exist = search_ani(bottoms_up_not_exist, phone_number_df)
        
        if cm_db_exist.empty:
            return cm_db_not_exist, pd.DataFrame(), pd.DataFrame()
        
        cm_db_exist['Deal - Deal creation date'] = cm_db_exist['Date and Time']

        added_email_df = add_email_columns(cm_db_exist, email_address_df)
        added_serials_df = add_serial_number(added_email_df, serial_numbers_df)
        added_cm_db_details_df = add_cm_db_details(added_serials_df, cm_db_df)
        added_new_db_id_df = add_new_database_id(added_cm_db_details_df)
        added_deal_title_df = add_deal_title(added_new_db_id_df)
        added_deal_county_df = add_deal_county(added_deal_title_df)
        added_mailing_address_df = add_mailing_address(added_deal_county_df)
        added_note_content_df = add_note_content(added_mailing_address_df)
        added_person_name_df = add_person_name(added_note_content_df)
        added_marketing_medium_df = add_marketing_medium(added_person_name_df)
        added_constants_df = add_constant_columns(added_marketing_medium_df)
        cm_db_final_df, cm_db_not_exist_final = filter_multiple_entries(added_constants_df, cm_db_not_exist)


        # Select columns that will be included in the final output data
        cm_db_final_output_data = cm_db_final_df[columns]


        return cm_db_not_exist_final, cm_db_final_output_data, cm_db_final_df


if __name__ == '__main__':
    create_new_deals_cm()