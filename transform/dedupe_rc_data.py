import os
import pandas as pd

def get_rc_input(file_path):
    rc_file_list = os.listdir(file_path)
    return rc_file_list

def remove_rc_duplicates():
    
    rc_path = 'data/abandoned_calls'
    rc_file_list = get_rc_input(rc_path)

    for file in rc_file_list:

        df = pd.read_excel(os.path.join(rc_path, file))
        df['Date and Time'] = pd.to_datetime(df['Date and Time'], format='mixed', dayfirst=False)
        df.sort_values(by=['Date and Time'], inplace=True)
        df_duplicates = df[df.duplicated(subset='ANI', keep='first')]
        df_remove_duplicates = df.drop_duplicates(subset='ANI', keep='first')

        # Save removed duplicates RC Data
        df_remove_duplicates.to_excel(f"output/abandoned_calls_no_dupe/(No Duplicates) {file}", index=False)

        if not df_duplicates.empty:
            df_duplicates.to_excel(f"output/abandoned_calls_dupe/(Duplicates) {file}", index=False)


if __name__ == "__main__":
    remove_rc_duplicates()