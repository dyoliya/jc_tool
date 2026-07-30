import pandas as pd
import os


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
    cm_db_check_ani.drop_duplicates(subset=['ANI', 'ntm_id'], inplace=True)

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
    cm_db_exist = cm_db_check_ani[cm_db_check_ani['ntm_id'].notnull()]
    cm_db_not_exist = cm_db_check_ani[cm_db_check_ani['ntm_id'].isna()][['ANI', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]

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
    filter_email_address_df = email_address_df[email_address_df['ntm_id'].isin(cm_db_exist['ntm_id'])]

    # Group by phone_number and get the grouped emails
    grouped = filter_email_address_df.groupby('ntm_id')['email_address'].apply(list).reset_index()

    # Flatten the emails for easier processing
    emails_flat = []
    for _, row in grouped.iterrows():
        ntm_id = row['ntm_id']
        emails = row['email_address'][:17]  # Take only the first 17 emails
        emails_flat.append((ntm_id, emails))

    # Fill cm_db_final_df with the flattened email data
    rows_to_add = []
    for ntm_id, emails in emails_flat:
        # Create a dictionary for the row data
        row_data = {'Deal - Unique Database ID': ntm_id}
        row_data.update({f'Person - Email {i+1}': email for i, email in enumerate(emails)})
        rows_to_add.append(row_data)

    # Append rows to cm_db_final_df using pd.concat
    email_address_final_df = pd.concat([cm_db_email_columns, pd.DataFrame(rows_to_add)], ignore_index=True).drop_duplicates()

    # Add email address dataframe to the final dataframe
    cm_db_final_df = cm_db_exist.merge(email_address_final_df,
                                        left_on='ntm_id',
                                        right_on='Deal - Unique Database ID',
                                        how='left')

    # The matched phone record is the source of truth for the database ID.
    # `ntm_id` contains ntm_contacts.new_contact_id (aliased in the SQL query),
    # so the ntm_id must still be populated even when the contact has no email.
    cm_db_final_df['Deal - Unique Database ID'] = cm_db_final_df['ntm_id']

    return cm_db_final_df

def normalize_database_id(value):
    """Convert a possible numeric ID such as 123.0 into '123'."""
    if pd.isna(value):
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return str(int(float(value)))
    except (ValueError, TypeError):
        return value


def split_pipe_values(value):
    """Split pipe-separated values and remove blanks."""
    if pd.isna(value):
        return []

    values = []

    for item in str(value).split('|'):
        item = item.strip()

        if item and item not in values:
            values.append(item)

    return values

def add_serial_number(cm_db_final_df: pd.DataFrame, serial_numbers_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Deal - Serial Number` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added emails column.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - Serial Number` column.\n
    '''

    # Merge serial numbers dataframe from CM Database to final dataframe
    serial_lookup_df = serial_numbers_df[
        ['ntm_id', 'serial_numbers']
    ].rename(
        columns={
            'ntm_id': 'Deal - Unique Database ID',
            'serial_numbers': 'Deal - Serial Number'
        }
    )

    cm_db_final_df = cm_db_final_df.merge(
        serial_lookup_df,
        on='Deal - Unique Database ID',
        how='left'
    )

    return cm_db_final_df

def add_bottoms_up_serial_numbers(
        cm_db_final_df: pd.DataFrame,
        bottoms_up_df: pd.DataFrame
) -> pd.DataFrame:

    if (
        cm_db_final_df.empty
        or bottoms_up_df.empty
        or 'budb_id' not in cm_db_final_df.columns
        or 'id' not in bottoms_up_df.columns
        or 'serial_number' not in bottoms_up_df.columns
    ):
        return cm_db_final_df

    # Build: BUDB ID -> list of Serial Numbers
    budb_serial_lookup = {}

    lookup_df = bottoms_up_df[
        ['id', 'serial_number']
    ].dropna(subset=['id', 'serial_number']).copy()

    for _, row in lookup_df.iterrows():
        budb_id = normalize_database_id(row['id'])

        if not budb_id:
            continue

        serials = split_pipe_values(row['serial_number'])

        for serial in serials:
            if serial not in budb_serial_lookup.setdefault(budb_id, []):
                budb_serial_lookup[budb_id].append(serial)

    def combine_serial_numbers(row):
        combined_serials = split_pipe_values(
            row.get('Deal - Serial Number')
        )

        for raw_budb_id in split_pipe_values(row.get('budb_id')):
            normalized_budb_id = normalize_database_id(raw_budb_id)

            for serial in budb_serial_lookup.get(
                normalized_budb_id, []
            ):
                if serial not in combined_serials:
                    combined_serials.append(serial)

        return ' | '.join(combined_serials) if combined_serials else pd.NA

    cm_db_final_df['Deal - Serial Number'] = (
        cm_db_final_df.apply(combine_serial_numbers, axis=1)
    )

    return cm_db_final_df

def add_deal_value_from_budb_ids(
        cm_db_final_df: pd.DataFrame,
        bottoms_up_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Add Deal - Value using only Bottoms Up serial numbers connected
    to Deal - BU Database ID.

    Rules:
        1. Retrieve the BU serial numbers from the BUDB IDs.
        2. Use only the first valid Bottoms Up serial.
        3. Find all BUDB rows belonging to that serial.
        4. If contact_group_id is blank for all matched rows, sum all
           sum_of_all_offers values.
        5. Otherwise, keep one row per contact_group_id before summing
           sum_of_all_offers.
    """

    result_df = cm_db_final_df.copy()
    result_df['Deal - Value'] = pd.NA

    required_columns = {
        'id',
        'serial_number',
        'contact_group_id',
        'sum_of_all_offers'
    }

    if (
        result_df.empty
        or bottoms_up_df.empty
        or 'Deal - BU Database ID' not in result_df.columns
        or not required_columns.issubset(bottoms_up_df.columns)
    ):
        return result_df

    # Prepare normalized BUDB IDs once.
    budb_lookup_df = bottoms_up_df[
        [
            'id',
            'serial_number',
            'contact_group_id',
            'sum_of_all_offers'
        ]
    ].copy()

    budb_lookup_df['_normalized_id'] = (
        budb_lookup_df['id']
        .astype(str)
        .str.strip()
        .str.replace(r'\.0$', '', regex=True)
    )

    def clean_serial(value):
        if pd.isna(value):
            return ''

        value = str(value).strip()

        if value.lower() in {'', 'nan', 'none', 'nat'}:
            return ''

        return value

    def calculate_deal_value(row):
        budb_ids = split_pipe_values(
            row.get('Deal - BU Database ID')
        )

        if not budb_ids:
            return pd.NA

        # Collect only BU serial numbers, preserving BUDB ID order.
        bu_serials = []

        for raw_budb_id in budb_ids:
            normalized_budb_id = normalize_database_id(raw_budb_id)

            matched_id_rows = budb_lookup_df[
                budb_lookup_df['_normalized_id'].eq(
                    normalized_budb_id
                )
            ]

            for serial_value in matched_id_rows['serial_number']:
                serial = clean_serial(serial_value)

                if serial and serial not in bu_serials:
                    bu_serials.append(serial)

        # No Bottoms Up serial was found.
        if not bu_serials:
            return pd.NA

        # Same rule as bottoms_up_new_deals:
        # use the first Bottoms Up serial only.
        first_bu_serial = bu_serials[0]

        serial_matches = budb_lookup_df[
            budb_lookup_df['serial_number']
            .astype(str)
            .str.strip()
            .eq(first_bu_serial)
        ].copy()

        if serial_matches.empty:
            return pd.NA

        serial_matches['sum_of_all_offers'] = pd.to_numeric(
            serial_matches['sum_of_all_offers'],
            errors='coerce'
        )

        # If every matched BUDB row has no contact_group_id,
        # sum all offer values.
        if serial_matches['contact_group_id'].dropna().empty:
            deal_value = serial_matches[
                'sum_of_all_offers'
            ].sum(min_count=1)

        else:
            # Avoid counting the same contact group more than once.
            deal_value = (
                serial_matches
                .drop_duplicates(subset=['contact_group_id'])
                ['sum_of_all_offers']
                .sum(min_count=1)
            )

        return deal_value if pd.notna(deal_value) else pd.NA

    result_df['Deal - Value'] = result_df.apply(
        calculate_deal_value,
        axis=1
    )

    return result_df

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
    cm_db_details_df = cm_db_df.rename(columns={'ntm_id': 'Deal - Unique Database ID'})
    cm_db_final_df = cm_db_final_df.merge(
        cm_db_details_df,
        on='Deal - Unique Database ID',
        how='left'
    )
    cm_db_final_df['Deal - BU Database ID'] = (
        cm_db_final_df['budb_id']
    )

    cm_db_final_df['Deal - Contact Group ID'] = (
        cm_db_final_df['ntm_contact_group_id']
    )

    return cm_db_final_df


def add_new_database_id(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Deal - Unique Database ID per phone number.

    If a phone matches multiple NTM IDs, preserve all unique IDs in
    database order. Multiple IDs alone do not make the record ambiguous.
    Name and mailing-address ambiguity are checked separately.
    """

    result_df = cm_db_final_df.copy()

    def clean_id(value):
        if pd.isna(value):
            return ''

        value = str(value).strip()

        if value.lower() in {'', 'nan', 'none', 'nat'}:
            return ''

        try:
            return str(int(float(value)))
        except (ValueError, TypeError):
            return value

    def combine_database_ids(group):
        unique_ids = []

        for value in group['Deal - Unique Database ID']:
            database_id = clean_id(value)

            if database_id and database_id not in unique_ids:
                unique_ids.append(database_id)

        return ' | '.join(unique_ids) if unique_ids else pd.NA

    database_id_rows = []

    for phone_number, group in result_df.groupby(
            'phone_number',
            dropna=False,
            sort=False):

        database_id_rows.append({
            'phone_number': phone_number,
            'new_database_id': combine_database_ids(group)
        })

    database_id_df = pd.DataFrame(database_id_rows)

    result_df.drop(
        columns=['Deal - Unique Database ID'],
        inplace=True
    )

    result_df = result_df.merge(
        database_id_df,
        on='phone_number',
        how='left'
    )

    result_df.rename(
        columns={
            'new_database_id': 'Deal - Unique Database ID'
        },
        inplace=True
    )

    return result_df

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

def add_deal_county_from_budb_ids(
        cm_db_final_df: pd.DataFrame,
        bottoms_up_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Override Deal - County using the County and State of each matching BUDB ID.

    If there are multiple BUDB IDs, combine unique county/state results
    using " | " while preserving the BUDB ID order.

    If budb_id is blank, keep the existing Deal - County value.
    """

    result_df = cm_db_final_df.copy()

    def clean_text(value):
        if pd.isna(value):
            return ''

        value = str(value).strip()

        if value.lower() in {'', 'nan', 'none', 'nat'}:
            return ''

        return value

    # Prepare the BUDB lookup table.
    budb_lookup_df = bottoms_up_df[
        ['id', 'target_county', 'target_state']
    ].copy()

    budb_lookup_df['_normalized_id'] = (
        budb_lookup_df['id']
        .astype(str)
        .str.strip()
        .str.replace(r'\.0$', '', regex=True)
    )

    def get_budb_counties(row):
        combined_ids = clean_text(row.get('Deal - BU Database ID'))
        # No BUDB match: retain the county created from the NTM data.
        if not combined_ids:
            return row.get('Deal - County')

        budb_ids = [
            normalize_database_id(value)
            for value in combined_ids.split('|')
            if clean_text(value)
        ]

        # Retain the county or counties already created from the CM/NTM record.
        county_results = []

        existing_deal_county = clean_text(row.get('Deal - County'))

        if existing_deal_county:
            for existing_county in existing_deal_county.split('|'):
                existing_county = clean_text(existing_county)

                if existing_county and existing_county not in county_results:
                    county_results.append(existing_county)

        for budb_id in budb_ids:
            matched_rows = budb_lookup_df[
                budb_lookup_df['_normalized_id'].eq(budb_id)
            ]

            if matched_rows.empty:
                continue

            for _, matched_row in matched_rows.iterrows():
                county = clean_text(matched_row['target_county'])
                state = clean_text(matched_row['target_state'])

                if county and state:
                    formatted_county = f"{county.title()} County, {state.upper()}"
                elif county:
                    formatted_county = f"{county.title()} County"
                elif state:
                    formatted_county = state.upper()
                else:
                    continue

                if formatted_county not in county_results:
                    county_results.append(formatted_county)

        # BUDB ID exists but no valid County/State was found.
        if not county_results:
            return pd.NA

        return ' | '.join(county_results)

    result_df['Deal - County'] = result_df.apply(
        get_budb_counties,
        axis=1
    )

    return result_df

def get_unique_ntm_contact_group_ids(group: pd.DataFrame) -> list:
    """
    Return all unique, nonblank NTM contact-group IDs for a phone group.

    Numeric and alphanumeric IDs are supported. Pipe-separated IDs within
    one database record are checked individually.
    """
    unique_group_ids = []

    if 'ntm_contact_group_id' not in group.columns:
        return unique_group_ids

    for raw_value in group['ntm_contact_group_id']:
        if pd.isna(raw_value):
            continue

        for item in str(raw_value).split('|'):
            item = item.strip()

            if not item or item.lower() in {'nan', 'none', 'nat'}:
                continue

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

    return unique_group_ids

def combine_serial_numbers_for_same_ntm_group(
        cm_db_final_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Combine serial numbers from all matching NTM rows when the phone belongs
    to one distinct non-null NTM contact group.

    If the phone belongs to different non-null NTM contact groups, leave the
    row-level serial numbers unchanged because it will be treated as a
    Common Name Error.
    """
    result_df = cm_db_final_df.copy()

    if (
        result_df.empty
        or 'phone_number' not in result_df.columns
        or 'Deal - Serial Number' not in result_df.columns
        or 'ntm_contact_group_id' not in result_df.columns
    ):
        return result_df

    serial_rows = []

    for phone_number, group in result_df.groupby(
            'phone_number',
            dropna=False,
            sort=False):

        unique_ntm_group_ids = get_unique_ntm_contact_group_ids(group)

        # Only combine all serials when there is exactly one known
        # non-null NTM contact-group ID.
        if len(unique_ntm_group_ids) == 1:
            combined_serials = []

            for serial_value in group['Deal - Serial Number']:
                for serial in split_pipe_values(serial_value):
                    if serial not in combined_serials:
                        combined_serials.append(serial)

            combined_value = (
                ' | '.join(combined_serials)
                if combined_serials
                else pd.NA
            )

        else:
            # Different groups or all group IDs are NULL:
            # do not combine across the rows.
            combined_value = None

        serial_rows.append({
            'phone_number': phone_number,
            '_combined_group_serials': combined_value
        })

    serial_group_df = pd.DataFrame(serial_rows)

    result_df = result_df.merge(
        serial_group_df,
        on='phone_number',
        how='left'
    )

    same_group_mask = result_df['_combined_group_serials'].notna()

    result_df.loc[
        same_group_mask,
        'Deal - Serial Number'
    ] = result_df.loc[
        same_group_mask,
        '_combined_group_serials'
    ]

    result_df.drop(
        columns=['_combined_group_serials'],
        inplace=True
    )

    return result_df

def add_deal_title(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Deal - Title using the same multiple-name rule as
    bottoms_up_new_deals.

    Rules:
        1. Group all matching NTM records by phone number.
        2. Build the name from first_name and last_name.
        3. If more than one distinct name exists, return:
               Multiple entries <phone>
        4. Multiple IDs with the same name are allowed.
        5. Combine unique counties by state.
        6. Use Oxford-comma formatting.
    """

    source_df = cm_db_final_df.copy()
    result_df = cm_db_final_df.copy()

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
            county = clean_text(county).title()

            if county and county not in unique_counties:
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
        unique_names = []

        # Check the NTM contact groups before selecting any result.
        unique_ntm_group_ids = get_unique_ntm_contact_group_ids(group)

        # Count actual distinct NTM records instead of raw merged dataframe rows.
        unique_ntm_record_count = (
            group['ntm_id']
            .dropna()
            .astype(str)
            .str.strip()
            .replace('', pd.NA)
            .dropna()
            .nunique()
        )

        # Common Name Error when:
        # 1. There are multiple different non-null contact-group IDs, or
        # 2. There are multiple distinct NTM records and all group IDs are NULL.
        is_multiple_ntm_result = (
            len(unique_ntm_group_ids) > 1
            or (
                unique_ntm_record_count > 1
                and len(unique_ntm_group_ids) == 0
            )
        )

        if is_multiple_ntm_result:
            return (
                f"Multiple entries "
                f"{group['phone_number'].iloc[0]}"
            )

        # One known group, or one single NTM record with no group ID:
        # treat the result as one contact.
        for _, row in group.iterrows():
            person_name = build_name(row)

            if person_name and person_name not in unique_names:
                unique_names.append(person_name)

        person_name = (
            unique_names[0]
            if unique_names
            else ''
        )

        counties_by_state = {}

        # Collect all counties from every matching NTM row.
        for deal_county in group['Deal - County']:
            deal_county = clean_text(deal_county)

            if not deal_county:
                continue

            for county_entry in deal_county.split('|'):
                county_entry = clean_text(county_entry)

                if not county_entry:
                    continue

                if ',' in county_entry:
                    county_part, state_part = (
                        county_entry.rsplit(',', 1)
                    )

                    county_name = clean_text(county_part)
                    state = clean_text(state_part).upper()
                else:
                    county_name = county_entry
                    state = ''

                if county_name.lower().endswith(' county'):
                    county_name = county_name[:-7].strip()

                county_name = county_name.title()

                if state not in counties_by_state:
                    counties_by_state[state] = []

                if (
                    county_name
                    and county_name
                    not in counties_by_state[state]
                ):
                    counties_by_state[state].append(
                        county_name
                    )

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

        formatted_counties_and_states = (
            format_state_groups(
                formatted_state_groups
            )
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

    # Remove any existing row-level title before merging
    # the phone-level title.
    result_df.drop(
        columns=['Deal - Title'],
        inplace=True,
        errors='ignore'
    )

    result_df = result_df.merge(
        title_df,
        on='phone_number',
        how='left'
    )

    return result_df


def add_deal_county(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add Deal - County per phone number.

    Rules:
        1. If all matching rows belong to exactly one non-null
           ntm_contact_group_id, combine all unique counties.
        2. If matching rows have different non-null contact-group IDs,
           do not combine counties because the phone is ambiguous.
        3. If every contact-group ID is NULL, use only the first valid county.
        4. Preserve database order and remove duplicate counties.
    """
    result_df = cm_db_final_df.copy()

    def clean_text(value):
        if pd.isna(value):
            return ''

        value = str(value).strip()

        if value.lower() in {'', 'nan', 'none', 'nat'}:
            return ''

        return value

    def format_county(country, state):
        country = clean_text(country)
        state = clean_text(state).upper()

        if country and state:
            return f"{country.title()} County, {state}"

        if country:
            return f"{country.title()} County"

        if state:
            return state

        return ''

    county_rows = []

    for phone_number, group in result_df.groupby(
            'phone_number',
            dropna=False,
            sort=False):

        unique_ntm_group_ids = get_unique_ntm_contact_group_ids(group)

        counties = []

        for _, row in group.iterrows():
            formatted_county = format_county(
                row.get('country'),
                row.get('state')
            )

            if formatted_county and formatted_county not in counties:
                counties.append(formatted_county)

        if len(unique_ntm_group_ids) == 1:
            # The rows belong to the same known NTM contact group.
            # Use every unique county from all matching rows.
            deal_county = (
                ' | '.join(counties)
                if counties
                else pd.NA
            )

        elif len(unique_ntm_group_ids) > 1:
            # The phone belongs to different known NTM contact groups.
            # The record will later be classified as Common Name Error.
            deal_county = (
                counties[0]
                if counties
                else pd.NA
            )

        else:
            # All contact-group IDs are NULL. We cannot safely assume
            # that all rows belong to one contact.
            deal_county = (
                counties[0]
                if counties
                else pd.NA
            )

        county_rows.append({
            'phone_number': phone_number,
            'Deal - County': deal_county
        })

    county_df = pd.DataFrame(county_rows)

    result_df.drop(
        columns=['Deal - County'],
        inplace=True,
        errors='ignore'
    )

    result_df = result_df.merge(
        county_df,
        on='phone_number',
        how='left'
    )

    return result_df


def add_mailing_address(cm_db_final_df: pd.DataFrame) -> pd.DataFrame:
    '''
    Adds `Person - Mailing Address` column to the final dataframe.\n

    Parameters:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Deal - County` column.\n

    Return:
        `cm_db_final_df (pd.DataFrame)` - Reference variable of a Pandas DataFrame with added `Person - Mailing Address` column.\n
    '''

    # Define pandas function that will create person mailing address
    def build_mailing_address(group_df):
        def clean(value):
            if pd.isna(value) or value is None:
                return ''

            value = str(value).strip()

            if value.lower() in {'', 'nan', 'none', 'nat'}:
                return ''

            return value

        mailing_addresses = []

        for _, record in group_df.iterrows():

            # First choice: md_address fields
            address = clean(record.get('address'))
            city = clean(record.get('city'))
            state = clean(record.get('state_address'))
            postal_code = clean(record.get('postal_code'))

            # Fallback: input_address fields
            if not address:
                address = clean(record.get('address2'))
                city = clean(record.get('city2'))
                state = clean(record.get('state_address2'))
                postal_code = clean(record.get('postal_code2'))

            # Neither primary nor fallback address exists
            if not address:
                continue

            parts = [
                address,
                city,
                state,
                postal_code,
                'USA'
            ]

            mailing_address = ', '.join(
                part for part in parts if part
            )

            if mailing_address not in mailing_addresses:
                mailing_addresses.append(mailing_address)

        if not mailing_addresses:
            return None

        if len(mailing_addresses) == 1:
            return mailing_addresses[0]

        unique_ntm_group_ids = get_unique_ntm_contact_group_ids(group_df)

        # Multiple addresses belonging to different non-NULL NTM groups
        # represent genuinely ambiguous contacts.
        if len(unique_ntm_group_ids) > 1:
            return 'Multiple address entries'

        # The addresses belong to zero or one distinct non-NULL NTM group.
        # Treat them as one valid contact and use the first available address.
        return mailing_addresses[0]

    mailing_address_rows = []

    for phone_number, group_df in cm_db_final_df.groupby('phone_number', dropna=False):
        mailing_address_rows.append({
            'phone_number': phone_number,
            'Person - Mailing Address': build_mailing_address(group_df)
        })

    mailing_address_df = pd.DataFrame(mailing_address_rows, columns=['phone_number', 'Person - Mailing Address'])
    cm_db_final_df = cm_db_final_df.merge(mailing_address_df, on='phone_number', how='left')

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
    cm_db_final_df['Deal - Label'] = cm_db_final_df['budb_id'].apply(
        lambda x: 'TARGETED MARKETING' if pd.notna(x) and str(x).strip() else ''
    )
    cm_db_final_df['Deal - Preferred Communication Method'] = 'Phone'
    cm_db_final_df['Deal - Abandoned Call Flag'] = 'Abandoned Call - Call Center'
    cm_db_final_df['Deal - Inbound Medium'] = 'Abandoned Call'
    cm_db_final_df['Deal - Deal Summary'] = 'Completed'
    cm_db_final_df['Deal - Pipedrive Analyst Tracking Flag'] = 'PA - Joyce'
    cm_db_final_df['Deal - Phone Number Format'] = 'Complete'
    cm_db_final_df['Person - Phone 1 - Data Source'] = 'Mineral Owner'
    cm_db_final_df['Person - Mailing Address - Data Source'] = cm_db_final_df['data_source']
    cm_db_final_df['Deal - Stage'] = cm_db_final_df['budb_id'].apply(
        lambda x: 'Follow Up - Bottoms Up (White Glove Pipeline)'
        if pd.notna(x) and str(x).strip()
        else 'Staging Qualifying'
    )
    cm_db_final_df['Deal - Deal Status'] = ''
    cm_db_final_df['Person - Timezone'] = ''
    cm_db_final_df['Deal - Owner'] = 'Stephanie'
    cm_db_final_df['Deal - Marketing Medium'] = 'Text'
    cm_db_final_df.drop_duplicates(subset=['ANI'], inplace=True) # Remove duplicated ANI Numbers


    return cm_db_final_df

def filter_multiple_entries(cm_db_final_df, cm_db_not_exist):
    # Filter single entries from cm_db_final_df
    single_entries_df = cm_db_final_df[~(cm_db_final_df['Deal - Title'].str.contains('Multiple', na=False) |\
                                        cm_db_final_df['Person - Mailing Address'].str.contains('Multiple', na=False))]
       
    # Filter multiple entries from cm_db_final_df
    multiple_entries_df = cm_db_final_df[cm_db_final_df['Deal - Title'].str.contains('Multiple', na=False) |\
                                        cm_db_final_df['Person - Mailing Address'].str.contains('Multiple', na=False)] \
                                        [['phone_number', 'Date and Time', 'Team', 'Date', 'Time', 'Contact ID']]
    multiple_entries_df['Deal - Deal Summary'] = 'Common Name Error'
    multiple_entries_df.rename(columns={'phone_number': 'ANI'}, inplace=True)
    # Add multiple entries to cm_db_not_exist
    cm_db_not_exist_final = pd.concat([cm_db_not_exist, multiple_entries_df])


    return single_entries_df, cm_db_not_exist_final

def add_offer_generated_date(cm_db_final_df: pd.DataFrame,
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
        result_df = cm_db_final_df.copy()
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
    result_df = cm_db_final_df.copy()
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

    for _, output_row in cm_db_final_df.iterrows():
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
            f'\n{len(diagnostic_df):,} CM new-deal output row(s) '
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
            '\nAll eligible CM new-deal output rows with BU ID received an '
            'Offer Generated Date.'
        )

    return result_df

def create_new_deals_cm(bottoms_up_not_exist: pd.DataFrame,
                        phone_number_df: pd.DataFrame,
                        email_address_df: pd.DataFrame,
                        serial_numbers_df: pd.DataFrame,
                        cm_db_df: pd.DataFrame,
                        bottoms_up_df: pd.DataFrame,
                        file_count: int):
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
        'Deal - BU Database ID',
        'Deal - Contact Group ID',
        'Deal - Value'
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
        added_deal_category_df = add_deal_category_from_budb_ids(added_cm_db_details_df, bottoms_up_df)
        added_budb_serials_df = add_bottoms_up_serial_numbers(added_deal_category_df, bottoms_up_df)
        combined_group_serials_df = combine_serial_numbers_for_same_ntm_group(added_budb_serials_df)
        added_deal_value_df = add_deal_value_from_budb_ids(combined_group_serials_df, bottoms_up_df)
        added_new_db_id_df = add_new_database_id(added_deal_value_df)
        added_deal_county_df = add_deal_county(added_new_db_id_df)
        added_budb_county_df = add_deal_county_from_budb_ids(added_deal_county_df, bottoms_up_df)
        added_deal_title_df = add_deal_title(added_budb_county_df)
        added_mailing_address_df = add_mailing_address(added_deal_title_df)
        added_note_content_df = add_note_content(added_mailing_address_df)
        added_person_name_df = add_person_name(added_note_content_df)
        added_marketing_medium_df = add_marketing_medium(added_person_name_df)
        added_constants_df = add_constant_columns(added_marketing_medium_df)
        added_offer_generated_date_df = add_offer_generated_date(added_constants_df, bottoms_up_df, file_count)
        cm_db_final_df, cm_db_not_exist_final = filter_multiple_entries(added_offer_generated_date_df, cm_db_not_exist)


        # Select columns that will be included in the final output data
        cm_db_final_output_data = cm_db_final_df[columns]


        return cm_db_not_exist_final, cm_db_final_output_data, cm_db_final_df


if __name__ == '__main__':
    create_new_deals_cm()