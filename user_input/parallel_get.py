import os
import sys
import concurrent.futures
import requests
import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv('misc/.env')
PIPEDRIVE_API = os.environ['API_KEY']

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
            contact_person = row['person_id']['name']
            all_phones = {phone['value'].strip() for phone in row['person_id']['phone']}
            phone_numbers = ", ".join(all_phones) if all_phones else None

            # Create up to 10 individual phone number columns
            person_phones = []
            for idx, phone in enumerate(all_phones):
                if idx < 10:
                    person_phones.append(phone)
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
