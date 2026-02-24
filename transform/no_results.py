import pandas as pd


def add_deal_title(no_result_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Title` column to the final dataframe.\n
    
    Parameters:
        `no_result_final_df (pd.DataFrame)` - Reference variable for a Pandas DataFrame that contains ANI Numbers with no result from CM Database and Bottoms Up Database.\n

    Return:
        `no_result_final_df (pd.DataFrame)` - Reference variable for a Pandas DataFrame with added `Deal - Title` column.\n
    '''

    # Apply lambda function and assign to a column
    no_result_final_df['Deal - Title'] = no_result_final_df.apply(
        lambda row: f"No Name {row['ANI']}",
        axis=1
    )

    return no_result_final_df


def add_deal_label(no_result_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Label` column to the final dataframe.\n

    Parameters:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Title` column.\n

    Return:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Label` column.\n
    '''

    # no_result_final_df['Deal - Label'] = no_result_final_df.apply(
    #     lambda row: 'BOTTOM UP OFFER' if 'Bottoms Up' in row['Team'] else '',
    #     axis=1
    # )

    # return no_result_final_df

    # no_result_final_df['Deal - Label'] = no_result_final_df.apply(
    #     lambda row: 'BOTTOM UP OFFER' if row['Team'] in ['Bottoms Up - Mid',
    #                                                     'Bottoms Up - Small',
    #                                                     'Bottoms Up - RVM',
    #                                                     'Bottoms Up - Sml'] else None, axis=1)

    # Apply function lambda function that will filter data from Bottoms Up and CM Database
    no_result_final_df['Deal - Label'] = no_result_final_df['Team'].apply(
        lambda x: 'TARGETED MARKETING' if pd.notnull(x) and 'Bottoms Up' in x else None
    )

    return no_result_final_df


def add_deal_stage(no_result_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Stage` column to the final dataframe.\n

    Parameters:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Label` column.\n
    
    Return:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Stage` column.\n
    '''

    # Define pandas function that will add deal stage
    def deal_stage(row):
        if row['Team'] == 'Reuben':
            return 'Follow Up - Junior Sales'
        else:
            return 'Staging - Qualifying'

    # Apply function and assign to a column
    no_result_final_df['Deal - Stage'] = no_result_final_df.apply(deal_stage, axis=1)

    return no_result_final_df


def add_marketing_medium(no_result_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Marketing Medium` column to the final dataframe.\n

    Parameters:
        `no_result_final_df (pd.DataFrame)` - Reference variable for a Pandas DataFrame with added `Deal - Stage` column.\n

    Return:
        `no_result_final_df (pd.DataFrame)` - Reference variable for a Pandas DataFrame with added `Deal - Marketing Medium` column.\n
    '''

    # Define pandas function will add marketing medium value
    def marketing_medium(row):
        if row['Team'] == 'Ringless Voicemail - LG':
            return 'RVM'
        elif row['Team'] == 'Call Center':
            return 'Direct Mail'
        elif row['Team'] == 'Lead Generation':
            return 'Cold Call'
        else:
            return 'Direct Mail'

    # Apply pandas function and assign to column
    no_result_final_df['Deal - Marketing Medium'] = no_result_final_df.apply(marketing_medium, axis=1)

    return no_result_final_df


def add_person_name(no_result_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Person - Name` column to the final dataframe.\n

    Parameters:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Marketing Medium` column.\n

    Return:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas Dataframe with added `Person - Name` column.\n
    '''

    # Apply lambda function and assign to a column
    no_result_final_df['Person - Name'] = no_result_final_df.apply(
        lambda row: f"No Name {row['ANI']}",
        axis=1
    )

    return no_result_final_df


def add_note_content(no_result_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Note Content` column to the final dataframe.\n

    Parameters:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Person - Name` column.\n
    
    Return:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Note Content` column.\n
    '''

    # Apply lambda function and assign to a column
    no_result_final_df['Note Content'] = no_result_final_df.apply(
        lambda row: f"JC abandoned call from {row['ANI']} on {row['Date and Time']}",
        axis=1
    )

    return no_result_final_df


def add_constant_columns(no_result_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds constant value columns to the final dataframe.\n

    Parameters:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Note Content column.\n`
    
    Return:
        `no_result_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added constant value columns.\n
    '''

    # Assign constant value to respective columns
    no_result_final_df['Deal - Preferred Communication Method'] = 'Phone'
    no_result_final_df['Deal - Abandoned Call Flag'] = 'Abandoned Call - Call Center'
    no_result_final_df['Deal - Inbound Medium'] = 'Abandoned Call'
    no_result_final_df['Deal - Deal Summary'] = no_result_final_df['Deal - Deal Summary']
    no_result_final_df['Deal - Pipedrive Analyst Tracking Flag'] = 'PA - Joyce'
    no_result_final_df['Deal - Phone Number Format'] = 'Complete'
    no_result_final_df['Person - Phone'] = no_result_final_df['ANI']
    no_result_final_df['Person - Phone 1'] = no_result_final_df['ANI']
    no_result_final_df['Person - Phone 1 - Data Source'] = 'Mineral Owner'
    no_result_final_df['Person - Timezone'] = ''
    no_result_final_df['Deal - Marketing Medium'] = 'Text'
    no_result_final_df['Deal - Owner'] = no_result_final_df['Team'].apply(lambda x: 'Stephanie' if x == 'Reuben' else 'Stephanie')

    return no_result_final_df

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


def multiple_or_no_result(row):

    if row['Deal - Deal Summary'] == 'Common Name Error':
        return 'Multiple Result'
    elif row['Deal - Deal Summary'] == 'No Information in Email':
        return 'No Result'


def create_no_result(cm_db_no_result: pd.DataFrame,
                     bottoms_up_no_result: pd.DataFrame,
                     file_count: int) -> None:
    '''
    This is the main driver function of this module.
    Creates no result output excel output file after creating and adding columns based on specifications.\n

    Parameters:
        `cm_db_no_result (pd.DataFrame)` - Reference variable for a Pandas DataFrame that contains values of ANI Numbers that are not existing in CM Database.\n
        `bottoms_up_no_result (pd.DataFrame)` - Reference variable for a Pandas DataFrame that contains values of ANI Numbers that are not existing in Bottoms Up Database.\n
        `file_count (int)` - Current count of the abandoned calls file that is being processed.\n

    Return:
        `None`
    '''

    columns = [
        'Deal - Deal creation date',
        'Deal - Title',
        'Deal - Label',
        'Deal - Stage',
        'Deal - Owner',
        'Deal - Preferred Communication Method',
        'Deal - Abandoned Call Flag',
        'Deal - Inbound Medium',
        'Deal - Marketing Medium',
        'Deal - Deal Summary',
        'Deal - Pipedrive Analyst Tracking Flag',
        'Deal - Phone Number Format',
        'Person - Name',
        'Person - Phone',
        'Person - Phone 1',
        'Note Content',
        'Person - Phone 1 - Data Source',
        'Person - Timezone'
    ]

    if cm_db_no_result.empty and bottoms_up_no_result.empty:
        return pd.DataFrame(columns=columns)

    print(f'Creating {file_count}. NO RESULT.xlsx file.')

    # Run functions to create columns
    no_result_final_df = pd.concat([cm_db_no_result, bottoms_up_no_result])

    no_result_final_df['Deal - Deal creation date'] = no_result_final_df['Date and Time']

    added_deal_title_df = add_deal_title(no_result_final_df)
    added_deal_label_df =  add_deal_label(added_deal_title_df)
    added_deal_stage_df = add_deal_stage(added_deal_label_df)
    added_marketing_medium_df = add_marketing_medium(added_deal_stage_df)
    added_person_name_df = add_person_name(added_marketing_medium_df)
    added_note_content_df = add_note_content(added_person_name_df)
    added_constant_columns_df = add_constant_columns(added_note_content_df)
    
    # Define columns that will be selected
    no_result_final_output = added_constant_columns_df[columns]
    timezone_dict = get_timezone_dict()
    no_result_final_output['Person - Timezone'] = no_result_final_output.apply(get_timezone,
                                                                               tz_dict=timezone_dict,
                                                                               axis=1)

    # Export the dataframe to excel file format
    no_result_final_output.to_excel(f'output/no_result/{file_count}. PIPEDRIVE IMPORT - NO RESULT.xlsx', index=False)

    return added_constant_columns_df
