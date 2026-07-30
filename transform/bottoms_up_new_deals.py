import pandas as pd
import numpy as np
from tabulate import tabulate
import os


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


def enrich_missing_names_from_contact_group(
        bottoms_up_exist: pd.DataFrame,
        bottoms_up_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Fill a matched BUDB row whose first and last names are both blank.

    Priority:
      1. Use first, middle, and last name from another row with the same
         contact_group_id where both first and last name are populated.
      2. If no complete parsed name exists in the group, use Owner as the
         name while preserving the original matched row and its other fields.

    This only updates the working dataframe used by this workflow. It does not
    overwrite the Bottoms Up database dataframe.
    '''

    enriched_df = bottoms_up_exist.copy()

    # These columns can be inferred as float when every value is NULL. Convert
    # them to object so text fallbacks can be assigned safely.
    for column in ['first_name', 'middle_name', 'last_name']:
        enriched_df[column] = enriched_df[column].astype('object')

    def clean_text(value):
        if pd.isna(value):
            return None
        value = str(value).strip()
        return value if value else None

    def first_non_blank(series):
        for value in series:
            cleaned_value = clean_text(value)
            if cleaned_value is not None:
                return cleaned_value
        return None

    for index, row in enriched_df.iterrows():
        current_first_name = clean_text(row.get('first_name'))
        current_last_name = clean_text(row.get('last_name'))

        # Apply the fallback only when BOTH parsed name fields are blank.
        if current_first_name is not None or current_last_name is not None:
            continue

        contact_group_id = row.get('contact_group_id')
        if pd.notna(contact_group_id) and str(contact_group_id).strip():
            group_rows = bottoms_up_df[
                bottoms_up_df['contact_group_id'].eq(contact_group_id)
            ]
        else:
            group_rows = bottoms_up_df.iloc[0:0]

        if not group_rows.empty:
            complete_name_mask = (
                group_rows['first_name'].map(clean_text).notna()
                & group_rows['last_name'].map(clean_text).notna()
            )
            complete_name_rows = group_rows[complete_name_mask]
        else:
            complete_name_rows = group_rows

        if not complete_name_rows.empty:
            # Use the first complete parsed name in the existing BUDB order.
            name_source = complete_name_rows.iloc[0]
            enriched_df.at[index, 'first_name'] = clean_text(
                name_source.get('first_name')
            )
            enriched_df.at[index, 'middle_name'] = clean_text(
                name_source.get('middle_name')
            )
            enriched_df.at[index, 'last_name'] = clean_text(
                name_source.get('last_name')
            )
            continue

        # No complete parsed name exists in the contact group. Prefer Owner
        # from the matched row, then try another nonblank Owner in the group.
        owner_name = clean_text(row.get('owner'))
        if owner_name is None and not group_rows.empty:
            owner_name = first_non_blank(group_rows['owner'])

        if owner_name is not None:
            enriched_df.at[index, 'first_name'] = owner_name
            enriched_df.at[index, 'middle_name'] = None
            enriched_df.at[index, 'last_name'] = None

    return enriched_df



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

        # --- Part A: collect IDs for all serials associated with the phone
        # Preserve serial order and avoid duplicate BUDB IDs.
        ids_seen = []

        for serial in serials:
            matches_for_serial = bottoms_up_df[
                bottoms_up_df['serial_number']
                .astype(str)
                .str.strip()
                .eq(str(serial).strip())
            ]

            ids_for_serial = (
                matches_for_serial['id']
                .dropna()
                .astype(str)
                .tolist()
            )

            for budb_id in ids_for_serial:
                if budb_id not in ids_seen:
                    ids_seen.append(budb_id)

        # --- Part B: first serial only for Contact Group ID and offers
        if serials:
            first_serial = serials[0]

            matches_first = bottoms_up_df[
                bottoms_up_df['serial_number']
                .astype(str)
                .str.strip()
                .eq(str(first_serial).strip())
            ]

            # Retain the existing Contact Group ID rule:
            # take the first nonblank unique contact_group_id.
            cg_vals = (
                matches_first['contact_group_id']
                .dropna()
                .unique()
                .tolist()
            )

            selected_contact_group_id = cg_vals[0] if cg_vals else None

            serial_group_contact_group_ids = (
                str(int(selected_contact_group_id))
                if isinstance(selected_contact_group_id, (float, int))
                else str(selected_contact_group_id)
                if selected_contact_group_id is not None
                else ""
            )

            # Expand Deal - BU Database ID:
            # append every BUDB ID belonging to the selected Contact Group ID.
            if selected_contact_group_id is not None:
                contact_group_rows = bottoms_up_df[
                    bottoms_up_df['contact_group_id'].eq(
                        selected_contact_group_id
                    )
                ]

                contact_group_ids = (
                    contact_group_rows['id']
                    .dropna()
                    .astype(str)
                    .tolist()
                )

                for budb_id in contact_group_ids:
                    if budb_id not in ids_seen:
                        ids_seen.append(budb_id)

            # offers: retain the existing first-serial-only logic
            if matches_first['contact_group_id'].dropna().empty:
                serial_group_sum_of_all_offers = (
                    matches_first['sum_of_all_offers'].sum()
                )
            else:
                serial_group_sum_of_all_offers = (
                    matches_first
                    .drop_duplicates('contact_group_id')
                    ['sum_of_all_offers']
                    .sum()
                )

        else:
            serial_group_contact_group_ids = ""
            serial_group_sum_of_all_offers = 0.0

        # Final unique list:
        # serial-based IDs first, then additional Contact Group IDs.
        serial_group_ids = (
            " | ".join(ids_seen)
            if ids_seen
            else ""
        )

        rows.append({
            'phone_number': phone,
            'serial_group_ids': serial_group_ids,
            'serial_group_contact_group_ids': serial_group_contact_group_ids,
            'serial_group_sum_of_all_offers': serial_group_sum_of_all_offers
        })
    serial_group_df = pd.DataFrame(rows)

    return serial_group_df

def add_deal_category_from_budb_ids(
        bottoms_up_final_df: pd.DataFrame,
        bottoms_up_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Deal - Category based on the Bottoms Up records whose IDs
    appear in Deal - BU Database ID.

    If multiple IDs have different nonblank categories, combine the
    unique categories using " | " while preserving BU Database ID order.
    """

    result_df = bottoms_up_final_df.copy()

    def clean_text(value):
        if pd.isna(value):
            return ''

        value = str(value).strip()

        if value.lower() in {'nan', 'none', 'nat'}:
            return ''

        return value

    # Prepare a normalized ID column once instead of repeatedly converting
    # the entire Bottoms Up dataframe for every output row.
    budb_lookup_df = bottoms_up_df[['id', 'bu_category']].copy()

    budb_lookup_df['_normalized_id'] = (
        budb_lookup_df['id']
        .astype(str)
        .str.strip()
        .str.replace(r'\.0$', '', regex=True)
    )

    def get_categories(output_row):
        combined_ids = clean_text(
            output_row.get('Deal - BU Database ID')
        )

        if not combined_ids:
            return pd.NA

        id_values = [
            value.strip()
            for value in combined_ids.split('|')
            if value.strip()
        ]

        # Normalize values such as "123.0" to "123".
        normalized_ids = [
            value[:-2] if value.endswith('.0') else value
            for value in id_values
        ]

        categories = []

        # Follow the same order in which the IDs appear in
        # Deal - BU Database ID.
        for normalized_id in normalized_ids:
            matched_rows = budb_lookup_df[
                budb_lookup_df['_normalized_id'].eq(normalized_id)
            ]

            if matched_rows.empty:
                continue

            for category_value in matched_rows['bu_category']:
                category = clean_text(category_value)

                if category and category not in categories:
                    categories.append(category)

        return ' | '.join(categories) if categories else pd.NA

    result_df['Deal - Category'] = result_df.apply(
        get_categories,
        axis=1
    )

    return result_df

def add_deal_title(bottoms_up_exist: pd.DataFrame, bottoms_up_final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Deal - Title using the person's name and Bottoms Up counties.

    Rules:
        1. Use first and last name when both are available.
        2. Use first name only when last name is unavailable.
        3. Group counties by state.
        4. Use "and" before the final county within each state.
        5. Use "and" before the final state group.
        6. Use an Oxford comma for three or more counties or states.
    """

    source_df = bottoms_up_exist.copy()
    result_df = bottoms_up_final_df.copy()

    def clean_text(value):
        if pd.isna(value):
            return ''

        value = str(value).strip()

        if value.lower() in {'', 'nan', 'none', 'nat'}:
            return ''

        return value

    def build_name(row):
        first_name = clean_text(row.get('first_name'))
        last_name = clean_text(row.get('last_name'))

        if first_name and last_name:
            return f"{first_name.title()} {last_name.title()}"

        if first_name:
            return first_name.title()

        if last_name:
            return last_name.title()

        return ''

    def format_counties(counties):
        unique_counties = []

        for county in counties:
            county = clean_text(county)

            if not county:
                continue

            county = county.title()

            if county not in unique_counties:
                unique_counties.append(county)

        county_count = len(unique_counties)

        if county_count == 0:
            return ''

        if county_count == 1:
            return f"{unique_counties[0]} County"

        if county_count == 2:
            return (
                f"{unique_counties[0]} and "
                f"{unique_counties[1]} County"
            )

        return (
            ', '.join(unique_counties[:-1])
            + f", and {unique_counties[-1]} County"
        )

    def format_state_groups(state_groups):
        group_count = len(state_groups)

        if group_count == 0:
            return ''

        if group_count == 1:
            return state_groups[0]

        if group_count == 2:
            return (
                f"{state_groups[0]} and "
                f"{state_groups[1]}"
            )

        return (
            ', '.join(state_groups[:-1])
            + f", and {state_groups[-1]}"
        )

    def build_title(group):
        # Preserve names in their original database order.
        unique_names = []

        for _, row in group.iterrows():
            person_name = build_name(row)

            if person_name and person_name not in unique_names:
                unique_names.append(person_name)

        if len(unique_names) > 1:
            return f"Multiple entries {group['phone_number'].iloc[0]}"

        person_name = unique_names[0] if unique_names else ''

        counties_by_state = {}

        for _, row in group.iterrows():
            county = clean_text(row.get('target_county'))
            state = clean_text(row.get('target_state')).upper()

            if not county:
                continue

            if state not in counties_by_state:
                counties_by_state[state] = []

            county = county.title()

            if county not in counties_by_state[state]:
                counties_by_state[state].append(county)

        formatted_state_groups = []

        for state, counties in counties_by_state.items():
            formatted_counties = format_counties(counties)

            if not formatted_counties:
                continue

            if state:
                formatted_state_groups.append(
                    f"{formatted_counties}, {state}"
                )
            else:
                formatted_state_groups.append(
                    formatted_counties
                )

        formatted_counties_and_states = format_state_groups(
            formatted_state_groups
        )

        return ' '.join(
            part
            for part in [
                person_name,
                formatted_counties_and_states
            ]
            if part
        )

    title_rows = []

    for phone_number, group in source_df.groupby(
            'phone_number',
            dropna=False,
            sort=False):

        title_rows.append({
            'phone_number': phone_number,
            'Deal - Title': build_title(group)
        })

    title_df = pd.DataFrame(title_rows)

    result_df = result_df.merge(
        title_df,
        on='phone_number',
        how='left'
    )

    return result_df


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
    def build_mailing_address(row):
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

            if not address:
                address = clean(non_blank_row['address2'].iloc[0])
                city = clean(non_blank_row['city2'].iloc[0])
                state = clean(non_blank_row['state2'].iloc[0])
                postal_code = clean(non_blank_row['postal_code2'].iloc[0])

            parts = [address, city, state, postal_code, "USA"]
            parts = [p for p in parts if p]  # remove empty values

            return ", ".join(parts)

        else:
            return 'Multiple address entries'
    
    # Add Person - Mailing Address to final dataframe
    mailing_address_rows = []

    for phone_number, group_df in bottoms_up_exist.groupby('phone_number'):
        mailing_address_rows.append({
            'phone_number': phone_number,
            'Person - Mailing Address': build_mailing_address(group_df)
        })

    mailing_address_column = pd.DataFrame(mailing_address_rows)
    bottoms_up_final_df = bottoms_up_final_df.merge(mailing_address_column, on='phone_number', how='left')
    # bottoms_up_final_df.rename(columns={0: 'Person - Mailing Address'}, inplace=True)
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

def add_offer_generated_date(bottoms_up_exist: pd.DataFrame,
                             bottoms_up_final_df: pd.DataFrame,
                             bottoms_up_df: pd.DataFrame,
                             file_count: int) -> pd.DataFrame:
    """
    Add Deal - Offer Generated Date using only the Bottoms Up counties
    connected to Deal - BU Database ID.

    Matching:
        Bottoms Up target_county + target_state
        Google Sheet County + State

    If multiple Bottoms Up counties have valid dates, use the oldest
    Offer Generated Date.

    Rows without a BUDB ID remain blank and are included in the
    diagnostic review file.
    """

    output_column = 'Deal - Offer Generated Date'

    sheet_url = (
        'https://docs.google.com/spreadsheets/d/'
        '13nigHtk4KCveWiANDYjNar2gFd-8q08HaGAFMkEzHzY/'
        'export?format=csv&gid=476072450'
    )

    required_sheet_columns = [
        'County',
        'State',
        'Offer Generated Date'
    ]

    diagnostics = []

    def clean_text(value):
        """Return a cleaned string or an empty string."""
        if pd.isna(value):
            return ''

        value = str(value).strip()

        if value.lower() in {'nan', 'none', 'nat'}:
            return ''

        return value

    def normalize_county(value):
        """
        Normalize county names for matching.

        Examples:
            'Tarrant County' -> 'TARRANT'
            ' tarrant '      -> 'TARRANT'
        """
        value = clean_text(value).upper()

        if value.endswith(' COUNTY'):
            value = value[:-7].strip()

        return ' '.join(value.split())

    def normalize_state(value):
        """Normalize state values for matching."""
        return ' '.join(clean_text(value).upper().split())

    def format_date(value):
        """
        Convert a Google Sheet date to yyyy-mm-dd.

        Returns:
            formatted_date, error_reason
        """
        cleaned_value = clean_text(value)

        if not cleaned_value:
            return pd.NA, 'Selected Google Sheet date is empty'

        parsed_date = pd.to_datetime(
            cleaned_value,
            format='%m/%d/%Y',
            errors='coerce'
        )

        # This fallback also supports Google Sheets values returned as
        # timestamps or other recognizable date values.
        if pd.isna(parsed_date):
            parsed_date = pd.to_datetime(
                cleaned_value,
                errors='coerce'
            )

        if pd.isna(parsed_date):
            return (
                pd.NA,
                f'Invalid date format in Google Sheet: {cleaned_value}'
            )

        return parsed_date.strftime('%Y-%m-%d'), ''

    def add_all_rows_as_issue(reason):
        """
        Use when the sheet itself cannot be read or validated.
        Every Bottoms Up output row remains blank but receives a diagnostic.
        """
        result_df = bottoms_up_final_df.copy()
        result_df[output_column] = pd.NA

        for _, output_row in result_df.iterrows():
            diagnostics.append({
                'Person - Phone': output_row.get('Person - Phone'),
                'Deal - County': output_row.get('Deal - County'),
                output_column: '',
                'Reason Offer Generated Date Is Blank': reason
            })

        return result_df

    # Always create the output column first so later output selection
    # cannot fail even when the Google Sheet is unavailable.
    result_df = bottoms_up_final_df.copy()
    result_df[output_column] = pd.NA

    try:
        # Row 2 is the header, so use header=1.
        counties_sheet_df = pd.read_csv(
            sheet_url,
            header=1,
            dtype=object
        )

    except Exception as error:
        result_df = add_all_rows_as_issue(
            f'Unable to read Counties Google Sheet: {error}'
        )

        diagnostic_df = pd.DataFrame(diagnostics)
        diagnostic_folder = 'output/offer_generated_date_review'
        os.makedirs(diagnostic_folder, exist_ok=True)

        diagnostic_df.to_csv(
            os.path.join(
                diagnostic_folder,
                f'{file_count}. OFFER GENERATED DATE REVIEW.csv'
            ),
            index=False
        )

        print(
            '\n[OFFER GENERATED DATE WARNING] '
            'The Counties Google Sheet could not be read. '
            'Offer generated dates were left blank.'
        )

        return result_df

    # Strip accidental spaces from the Google Sheet headers.
    counties_sheet_df.columns = [
        clean_text(column)
        for column in counties_sheet_df.columns
    ]

    missing_sheet_columns = [
        column
        for column in required_sheet_columns
        if column not in counties_sheet_df.columns
    ]

    if missing_sheet_columns:
        result_df = add_all_rows_as_issue(
            'Missing required Google Sheet column(s): '
            + ', '.join(missing_sheet_columns)
        )

        diagnostic_df = pd.DataFrame(diagnostics)
        diagnostic_folder = 'output/offer_generated_date_review'
        os.makedirs(diagnostic_folder, exist_ok=True)

        diagnostic_df.to_csv(
            os.path.join(
                diagnostic_folder,
                f'{file_count}. OFFER GENERATED DATE REVIEW.csv'
            ),
            index=False
        )

        print(
            '\n[OFFER GENERATED DATE WARNING] '
            'Required Google Sheet columns are missing: '
            + ', '.join(missing_sheet_columns)
        )

        return result_df

    # Prepare normalized match fields from the Google Sheet.
    counties_sheet_df['_normalized_county'] = (
        counties_sheet_df['County'].map(normalize_county)
    )
    counties_sheet_df['_normalized_state'] = (
        counties_sheet_df['State'].map(normalize_state)
    )

    # Remove rows that have neither a usable county nor a usable state.
    counties_sheet_df = counties_sheet_df[
        counties_sheet_df['_normalized_county'].ne('')
        | counties_sheet_df['_normalized_state'].ne('')
    ].copy()

    # Build county/state records from the exact BUDB IDs written into
    # Deal - BU Database ID.
    phone_county_rows = []

    for _, output_row in bottoms_up_final_df.iterrows():
        phone_number = output_row.get('phone_number')
        combined_ids = clean_text(output_row.get('Deal - BU Database ID'))

        if not combined_ids:
            phone_county_rows.append({
                'phone_number': phone_number,
                'target_county': '',
                'target_state': '',
                '_id_issue': 'Deal - BU Database ID is empty'
            })
            continue

        # Deal - BU Database ID uses | as the separator.
        id_values = [
            value.strip()
            for value in combined_ids.split('|')
            if value.strip()
        ]

        # Convert both sides to strings so IDs such as 123 and 123.0
        # can still be compared safely.
        normalized_ids = {
            value[:-2] if value.endswith('.0') else value
            for value in id_values
        }

        matched_id_rows = bottoms_up_df[
            bottoms_up_df['id']
            .astype(str)
            .str.strip()
            .str.replace(r'\.0$', '', regex=True)
            .isin(normalized_ids)
        ]

        if matched_id_rows.empty:
            phone_county_rows.append({
                'phone_number': phone_number,
                'target_county': '',
                'target_state': '',
                '_id_issue': (
                    'No Bottoms Up records were found for '
                    f'Deal - BU Database ID: {combined_ids}'
                )
            })
            continue

        for _, id_row in matched_id_rows.iterrows():
            phone_county_rows.append({
                'phone_number': phone_number,
                'target_county': id_row.get('target_county'),
                'target_state': id_row.get('target_state'),
                '_id_issue': ''
            })

    phone_counties_df = (
        pd.DataFrame(phone_county_rows)
        .drop_duplicates(
            subset=['phone_number', 'target_county', 'target_state']
        )
    )

    phone_counties_df['_normalized_county'] = (
        phone_counties_df['target_county'].map(normalize_county)
    )

    phone_counties_df['_normalized_state'] = (
        phone_counties_df['target_state'].map(normalize_state)
    )

    date_rows = []

    for phone_number, phone_group in phone_counties_df.groupby(
            'phone_number',
            dropna=False):

        selected_dates = []
        phone_reasons = []

        for _, county_row in phone_group.iterrows():
            id_issue = clean_text(county_row.get('_id_issue'))

            if id_issue:
                phone_reasons.append(id_issue)
                continue
            original_county = clean_text(county_row.get('target_county'))
            original_state = clean_text(county_row.get('target_state'))

            normalized_county = county_row['_normalized_county']
            normalized_state = county_row['_normalized_state']

            if not normalized_county and not normalized_state:
                phone_reasons.append(
                    'Bottoms Up county and state are both empty'
                )
                continue

            if not normalized_county:
                phone_reasons.append(
                    f'Bottoms Up county is empty; state: {original_state}'
                )
                continue

            if not normalized_state:
                phone_reasons.append(
                    f'Bottoms Up state is empty; county: {original_county}'
                )
                continue

            sheet_matches = counties_sheet_df[
                counties_sheet_df['_normalized_county'].eq(
                    normalized_county
                )
                & counties_sheet_df['_normalized_state'].eq(
                    normalized_state
                )
            ]

            if sheet_matches.empty:
                phone_reasons.append(
                    f'County/state not found in Counties tab: '
                    f'{original_county} County, {original_state}'
                )
                continue

            # Use the first matching sheet row. Duplicate matching rows
            # are reported so the user knows that the sheet needs review.
            sheet_row = sheet_matches.iloc[0]

            if len(sheet_matches) > 1:
                print(
                    '[OFFER GENERATED DATE WARNING] '
                    f'Multiple Counties-tab rows matched '
                    f'{original_county} County, {original_state}. '
                    'The first matching row was used.'
                )

            selected_raw_date = clean_text(
                sheet_row.get('Offer Generated Date')
            )
            selected_source = 'Offer Generated Date'

            formatted_date, date_error = format_date(selected_raw_date)

            if date_error:
                phone_reasons.append(
                    f'{original_county} County, {original_state} — '
                    f'{selected_source}: {date_error}'
                )
                continue

            selected_dates.append({
                'date': formatted_date,
                'parsed_date': pd.to_datetime(
                    formatted_date,
                    errors='coerce'
                ),
                'county': original_county,
                'state': original_state,
                'source': selected_source
            })

        if selected_dates:
            # A phone can be tied to more than one BUDB county.
            # Compare all valid county dates and use the oldest one.
            selected_dates.sort(
                key=lambda item: item['parsed_date']
            )

            chosen_date = selected_dates[0]['date']
            blank_reason = ''

        else:
            chosen_date = pd.NA
            blank_reason = ' | '.join(dict.fromkeys(phone_reasons))

            if not blank_reason:
                blank_reason = (
                    'No usable county/state/date combination was found'
                )

        date_rows.append({
            'phone_number': phone_number,
            output_column: chosen_date,
            '_offer_generated_date_reason': blank_reason
        })

    phone_date_df = pd.DataFrame(date_rows)

    # Replace the initially blank date column with the matched result.
    result_df.drop(columns=[output_column], inplace=True)

    result_df = result_df.merge(
        phone_date_df,
        on='phone_number',
        how='left'
    )

    result_df[output_column] = result_df[output_column].astype('string')

    blank_date_mask = (
        result_df[output_column].isna()
        | result_df[output_column].str.strip().eq('')
    )

    for _, output_row in result_df[blank_date_mask].iterrows():
        diagnostics.append({
            'Person - Phone': output_row.get(
                'Person - Phone',
                output_row.get('phone_number')
            ),
            'Deal - County': output_row.get('Deal - County'),
            output_column: '',
            'Reason Offer Generated Date Is Blank': (
                output_row.get('_offer_generated_date_reason')
                or 'No matching date result was produced'
            )
        })

    # The reason column is only for the diagnostic file, not the
    # Pipedrive import output.
    result_df.drop(
        columns=['_offer_generated_date_reason'],
        inplace=True,
        errors='ignore'
    )

    diagnostic_folder = 'output/offer_generated_date_review'
    os.makedirs(diagnostic_folder, exist_ok=True)

    diagnostic_file = os.path.join(
        diagnostic_folder,
        f'{file_count}. OFFER GENERATED DATE REVIEW.csv'
    )

    if diagnostics:
        diagnostic_df = pd.DataFrame(diagnostics)
        diagnostic_df.to_csv(diagnostic_file, index=False)

        print(
            '\n[OFFER GENERATED DATE REVIEW]'
            f'\n{len(diagnostic_df):,} Bottoms Up output row(s) '
            'have no Offer Generated Date.'
            f'\nReview: {diagnostic_file}'
        )
    else:
        # Delete an old diagnostic for the same file_count so it cannot
        # be mistaken for the current run.
        if os.path.exists(diagnostic_file):
            os.remove(diagnostic_file)

        print(
            '\n[OFFER GENERATED DATE]'
            '\nAll Bottoms Up output rows received an '
            'Offer Generated Date.'
        )

    return result_df


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
        # Resolve missing parsed names before Deal - Title and Person - Name
        # are created. The matched row stays the same; only its working name
        # fields can be filled from its contact group or Owner.
        bottoms_up_exist = enrich_missing_names_from_contact_group(
            bottoms_up_exist,
            bottoms_up_df
        )

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
        added_offer_date_df = add_offer_generated_date(bottoms_up_exist, added_deal_county_df, bottoms_up_df, file_count)
        added_deal_category_df = add_deal_category_from_budb_ids(added_offer_date_df, bottoms_up_df)
        added_mailing_address_df = add_mailing_address(bottoms_up_exist, added_deal_category_df)
        added_note_content_df = add_note_content(bottoms_up_exist, added_mailing_address_df)
        added_person_name_df = add_person_name(bottoms_up_exist, added_note_content_df)
        added_constants_df = add_constant_columns(added_person_name_df)
        bottoms_up_final_df, bottoms_up_not_exist_final = filter_multiple_entries(added_constants_df, bottoms_up_not_exist)
        
        # Select columns that will be included in the final output data
        bottoms_up_final_output_data = bottoms_up_final_df[columns]
        

        return bottoms_up_not_exist_final, bottoms_up_final_output_data, bottoms_up_final_df