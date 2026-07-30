import os
import sys
import concurrent.futures
import json
import requests
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv('misc/.env')
PIPEDRIVE_API = os.environ['API_KEY']
PERSON_IDS_PER_REQUEST = 100
PERSON_REQUEST_WORKERS = 5

# Reused across deal pages so each linked Person is retrieved only once.
person_phone_cache = {}
person_phone_field_keys = None


def unique_phone_values(phone_entries):
    """Return nonblank phone values once while preserving their order."""
    phones = []
    seen = set()

    for phone in phone_entries or []:
        value = phone.get('value') if isinstance(phone, dict) else phone
        if value is None:
            continue

        value = str(value).strip()
        if value and value not in seen:
            seen.add(value)
            phones.append(value)

    return phones


def excel_safe_phone_list(phone_values):
    """Display a comma-separated phone list as text when opened in Excel."""
    if not phone_values:
        return None

    display_value = ", ".join(phone_values).replace('"', '""')
    return f'="{display_value}"'


def get_person_phone_field_keys():
    """Return the Pipedrive keys for custom Person fields Phone 1 to Phone 10."""
    global person_phone_field_keys

    if person_phone_field_keys is not None:
        return person_phone_field_keys

    fields_by_name = {}
    start = 0
    while True:
        response = requests.get(
            "https://communityminerals-f099fc.pipedrive.com/api/v1/personFields",
            params={
                'api_token': PIPEDRIVE_API,
                'start': start,
                'limit': 500
            },
            timeout=60
        )
        response.raise_for_status()
        payload = response.json()

        for field in payload.get('data') or []:
            field_name = str(field.get('name') or '').strip()
            field_key = field.get('key')
            if field_name and field_key:
                fields_by_name[field_name] = str(field_key)

        pagination = (payload.get('additional_data') or {}).get('pagination') or {}
        if not pagination.get('more_items_in_collection'):
            break
        start = int(pagination.get('next_start') or (start + 500))

    person_phone_field_keys = [
        fields_by_name[f"Phone {number}"]
        for number in range(1, 11)
        if f"Phone {number}" in fields_by_name
    ]
    print(
        f"Found {len(person_phone_field_keys)} custom Person phone field(s) "
        "for the export."
    )
    return person_phone_field_keys


def custom_phone_values(raw_value):
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return unique_phone_values(raw_value)
    if isinstance(raw_value, dict):
        return unique_phone_values([raw_value.get('value')])
    return unique_phone_values([raw_value])


def extract_complete_person_phones(person, phone_field_keys):
    """Merge standard phones with custom Phone 1 through Phone 10 values."""
    phones = unique_phone_values(person.get('phones') or person.get('phone') or [])
    custom_fields = person.get('custom_fields') or {}

    for field_key in phone_field_keys:
        raw_value = custom_fields.get(field_key, person.get(field_key))
        phones = unique_phone_values(phones + custom_phone_values(raw_value))

    return phones


def fetch_person_batch(person_ids, phone_field_keys):
    """Retrieve up to 100 linked Person records in one Pipedrive request."""
    params = {
        'api_token': PIPEDRIVE_API,
        'ids': ','.join(person_ids),
        'limit': len(person_ids)
    }
    if phone_field_keys:
        params['custom_fields'] = ','.join(phone_field_keys)

    response = requests.get(
        "https://communityminerals-f099fc.pipedrive.com/api/v2/persons",
        params=params,
        timeout=60
    )
    response.raise_for_status()

    people = {}
    for person in response.json().get('data') or []:
        person_id = person.get('id')
        if person_id is None:
            continue
        people[str(person_id)] = {
            'name': person.get('name'),
            'phones': extract_complete_person_phones(person, phone_field_keys)
        }
    return people


def get_people_for_deal_rows(rows):
    """Load only uncached people linked to the current page of deals."""
    phone_field_keys = get_person_phone_field_keys()
    person_ids = []

    for row in rows:
        person_info = row.get('person_id')
        if isinstance(person_info, dict):
            person_id = person_info.get('value') or person_info.get('id')
        else:
            person_id = person_info

        if person_id is not None:
            person_id = str(person_id)
            if person_id not in person_phone_cache and person_id not in person_ids:
                person_ids.append(person_id)

    batches = [
        person_ids[index:index + PERSON_IDS_PER_REQUEST]
        for index in range(0, len(person_ids), PERSON_IDS_PER_REQUEST)
    ]

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=PERSON_REQUEST_WORKERS
    ) as executor:
        futures = [
            executor.submit(fetch_person_batch, batch, phone_field_keys)
            for batch in batches
        ]
        for future in concurrent.futures.as_completed(futures):
            person_phone_cache.update(future.result())

    return person_phone_cache

def get_deal_fields(endpoint):

    url = f"https://communityminerals-f099fc.pipedrive.com/{endpoint}?api_token={PIPEDRIVE_API}"
    params = {'start': 0, 'limit': 500}

    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        dict = response.json()
        ca_tracking_flag_dict = {}
        deal_status_dict = {}

        for field in dict['data']:
            if field['id'] == 12560:
                for option in field['options']:
                    ca_tracking_flag_dict[str(option['id'])] = option['label']

            elif field['id'] == 12496:
                for option in field['options']:
                    deal_status_dict[str(option['id'])] = option['label']

        ca_tracking_flag_dict[None] = None
        deal_status_dict[None] = None

        return ca_tracking_flag_dict, deal_status_dict

    else:
        print("Connection Failed")

        return None, None
    
def get_pipelines(endpoint):

    url = f"https://communityminerals-f099fc.pipedrive.com/{endpoint}?api_token={PIPEDRIVE_API}"
    params = {'start': 0, 'limit': 500}

    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        dict = response.json()
        pipeline_dict = {}

        for pipeline in dict['data']:
            pipeline_dict[pipeline['id']] = pipeline['name']

        return pipeline_dict
            
    else:
        print("Connection Failed")

        return None
    
def get_deal_stages(endpoint):

    url = f"https://communityminerals-f099fc.pipedrive.com/{endpoint}?api_token={PIPEDRIVE_API}"
    params = {'start': 0, 'limit': 500}

    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        dict = response.json()
        stages_dict = {}

        for stage in dict['data']:
            stages_dict[stage['id']] = stage['name']

        return stages_dict

    else:
        print("Connection Failed")

        return None

def process_data(data):

    row_data_list = []
    complete_people = get_people_for_deal_rows(data.get('data') or [])

    for row in data['data']:

        deal_status_final = None
        deal_status = row['a8b479cb304320c246021ded79cb84243dd67b6f']
        if deal_status is not None:
            deal_status_list = deal_status.split(',')
            deal_status_final = ", ".join(deal_status_dict[id] for id in deal_status_list if id in deal_status_dict)

        ca_tracking_final = None
        ca_tracking = row['1ed94338f4ab22269018b9b3f37b0967172c0c20']
        if ca_tracking is not None:
            ca_tracking_list = ca_tracking.split(',')
            ca_tracking_final = ", ".join(ca_tracking_flag_dict[id] for id in ca_tracking_list if id in ca_tracking_flag_dict)
        
        person_info = row.get('person_id')

        if person_info:
            person_id = row['person_id']['value']
            complete_person = complete_people.get(str(person_id), {})
            contact_person = complete_person.get('name') or row['person_id']['name']

            embedded_phones = unique_phone_values(row['person_id'].get('phone') or [])
            all_phones = unique_phone_values(
                (complete_person.get('phones') or []) + embedded_phones
            )
            # CSV has no text type. The ="..." wrapper prevents Excel from
            # converting several phone numbers into one huge numeric value.
            phone_numbers = excel_safe_phone_list(all_phones)

            # Create up to 10 individual phone number columns
            person_phones = all_phones[:10]
            # Fill up to 10 slots (pad with None if less than 10)
            while len(person_phones) < 10:
                person_phones.append(None)
        else:
            person_id = contact_person = phone_numbers = None
            person_phones = [None] * 10  # 10 empty phone slots if no person_info

        # Create the row data
        row_data = [
            row['id'],
            row['title'],
            person_id,
            contact_person,
            phone_numbers,
            *person_phones,
            row['user_id']['name'],
            stages_dict[row['stage_id']],
            pipeline_dict[row['pipeline_id']],
            ca_tracking_final,
            row['cf55ab58ba9377b340fe91a7886591cac6cafabd'],
            deal_status_final,
            row['9303acb9715bc55f1641f24266d13133b05f8c5d'],
            row['de5b9ae6977eac029ca827c10722948055d982e3']
        ]

        row_data_list.append(row_data)

        columns = [
            'Deal - ID',
            'Deal - Title',
            'Person - ID',
            'Deal - Contact person',
            'phone_number',
            'Person - Phone 1',
            'Person - Phone 2',
            'Person - Phone 3',
            'Person - Phone 4',
            'Person - Phone 5',
            'Person - Phone 6',
            'Person - Phone 7',
            'Person - Phone 8',
            'Person - Phone 9',
            'Person - Phone 10',
            'Deal - Owner',
            'Deal - Stage',
            'Deal - Pipeline',
            'Deal - CA Tracking Flag',
            'Deal - Unique Database ID',
            'Deal - Deal Status',
            'Deal - Offer Ready Date',
            'Deal - Offer Ready - Small Date'
        ]

    pipedrive_df = pd.DataFrame(row_data_list, columns=columns)

    return pipedrive_df

def fetch_data_from_api(next_start=0):
    try:
        all_deals_endpoint =  "api/v1/deals"
        url = f"https://communityminerals-f099fc.pipedrive.com/{all_deals_endpoint}?api_token={PIPEDRIVE_API}"
        params = {'start': next_start, 'limit': 500}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()  # Assuming the response is in JSON format
    except requests.RequestException as e:
        print(f"Request failed for start {next_start}: {e}")
        return None

def gather_paginated_data_parallel_batch(batch_size=5):
    data = []
    more_items = True
    step = 500
    next_start = 0

    with concurrent.futures.ThreadPoolExecutor() as executor:
        while more_items:
            futures = []
            # Fetch 'batch_size' pages concurrently
            for _ in range(batch_size):
                futures.append(executor.submit(fetch_data_from_api, next_start))
                next_start += step

            # Wait for all the current batch of requests to complete
            results = [future.result() for future in futures]

            for result in results:
                if result:
                    data.append(process_data(result))
                    more_items = result['additional_data']['pagination']['more_items_in_collection']
                    if not more_items:
                        break
                else:
                    more_items = False  # Stop if the request fails
    
    # Combine all the data into a single DataFrame
    if data:
        df = pd.concat(data, ignore_index=True)
        return df        

def main():

    print("Extracting Pipedrive Data")

    global ca_tracking_flag_dict, deal_status_dict, pipeline_dict, stages_dict

    ca_tracking_flag_dict, deal_status_dict = get_deal_fields("api/v1/dealFields")
    pipeline_dict = get_pipelines("api/v1/pipelines")
    stages_dict = get_deal_stages("api/v1/stages")
    df_combined = gather_paginated_data_parallel_batch(5)
    df_combined.to_csv('./data/pipedrive/pipedrive_data.csv', index=False)

if __name__ == "__main__":
    main()
