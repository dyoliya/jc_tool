import os, json


def reset_pipeline_values(user_designation: dict, conditions_dict: dict) -> 'tuple[dict, dict]':
    '''
    Clears all the values of all pipelines and conditions.\n

    Parameters:
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline.\n
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n

    Return:
        `user_designation (dict)` - If user returned 'y', return a default value user designation dictionary, else no change.\n
        `conditions_dict (dict)` - If user returned 'y', return a default value conditions dictionary, else no change.\n
    '''

    print(
        "\ny - YES\n"
        "n - NO\n"
    )

    reset_user_selection = input('This will remove all pipeline values, remove pipeline conditions and load the default pipelines. Are you sure?: ')

    if reset_user_selection.lower() == 'y':

        # Load default values
        user_designation = pipeline_values()
        conditions_dict = conditions_values()

        return user_designation, conditions_dict
    
    elif reset_user_selection.lower() == 'n':

        # Return dictionaries with no changes
        return user_designation, conditions_dict



def add_pipeline(user_designation: dict, conditions_dict: dict) -> None:
    '''
    Adds a new pipeline to the user designation dictionary and conditions dictionary defined by the end user.\n

    Parameters:
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline.\n
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n

    Return:
        `None`
    '''

    # Clear screen
    os.system('cls')

    print('Add Pipeline:\n')

    # Display current user designation dictionary
    for key, value in user_designation.items():
        print(f"{key:<3} {value[0]:<20}")

    new_pipeline_name = str(input('\nType in the name of the new pipeline: '))

    # Find the maximum key in both dictionaries
    max_key_user = max(user_designation.keys())
    max_key_conditions = max(conditions_dict.keys())
    
    # Increment the key to get the next available key (ensure both dictionaries have the same keys)
    new_key = max(max_key_user, max_key_conditions) + 1
    
    # Add the new values with the new key to both dictionaries
    user_designation[new_key] = [new_pipeline_name.capitalize(), 'None', 'None']
    conditions_dict[new_key] = []
    
    return user_designation, conditions_dict


def remove_pipeline(user_designation: dict, conditions_dict: dict) -> None:
    '''
    This function removes a specific pipeline from the main window, including the conditions, that is selected by the end user.\n

    Parameters:
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline.\n
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n
        
    Return:
        `None`
    '''

    # Clear screen
    os.system('cls')

    print('Remove Pipeline:\n')
    
    # Display current user designation dictionary
    for key, value in user_designation.items():
        print(f"{key:<3} {value[0]:<20}")

    key_to_remove = int(input('\nSelect the number of the pipeline you want to remove: '))

    # Remove the specified key from user_designation
    if key_to_remove in user_designation:
        del user_designation[key_to_remove]
        
        # Adjust keys for the subsequent items in user_designation
        max_key = max(user_designation.keys())
        for key in range(key_to_remove + 1, max_key + 1):
            user_designation[key - 1] = user_designation.pop(key)
    
    # Remove the specified key from conditions_dict
    if key_to_remove in conditions_dict:
        del conditions_dict[key_to_remove]
        
        # Adjust keys for the subsequent items in conditions_dict
        max_key = max(conditions_dict.keys())
        for key in range(key_to_remove + 1, max_key + 1):
            conditions_dict[key - 1] = conditions_dict.pop(key)
    
    return user_designation, conditions_dict


def pipeline_conditions(pipeline_user_selector: int, user_designation: dict, condition_dict: dict) -> None:
    '''
    This function appends a dictionary of a condition to a list of conditions per pipeline.\n

    Parameters:
        `pipeline_user_selector (int)` - Pipeline number that was selected by the end user.\n
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline.\n
        `condition_dict (dict)` - Dictionary of conditions per pipeline.\n

    Return:
        `None`
    '''

    # Clear screen
    os.system('cls')

    print('Add Condition:\n')    

    # Initialize dictionaries
    condition_follow_up = {
        1: 'CT - Abandoned Call Follow Up',
        2: 'AA - Abandoned Call Follow Up',
        3: 'CA - Abandoned Call Follow Up',
        4: 'PD - Abandoned Call Follow Up',
        5: 'Type in the follow up task'
    }
    condition_assigned_user = {
        1: 'Deal Owner',
        2: 'CA Tracking Flag',
        3: 'Type in the name of the assigned user'
    }

    # Type in the columns to check the conditions
    print(f"{user_designation[pipeline_user_selector][0]} Pipeline:")
    column_to_condition = str(input("Type in the column to check the condition to: "))

    # Type in condition
    print(f"{user_designation[pipeline_user_selector][0]} Pipeline -> {column_to_condition}:")
    condition_name = str(input("State the condition: "))


    # Select follow up
    print(
        f"{user_designation[pipeline_user_selector][0]} Pipeline -> {column_to_condition} -> {condition_name}:\n"
        f"1. {condition_follow_up[1]}\n"
        f"2. {condition_follow_up[2]}\n"
        f"3. {condition_follow_up[3]}\n"
        f"4. {condition_follow_up[4]}\n"
        f"5. {condition_follow_up[5]}\n"
    )
    follow_up_selector = int(input("Select the number of follow up type: "))

    # condition_follow_up_value = condition_follow_up[follow_up_selector]

    if follow_up_selector == 5:
        condition_follow_up_value = str(input("Type in the follow up task: "))
    elif follow_up_selector in [1, 2, 3, 4]:
        condition_follow_up_value = condition_follow_up[follow_up_selector] # Assign to follow up index of the list


    # Assign user per condition
    print(
        f"{user_designation[pipeline_user_selector][0]} Pipeline -> {column_to_condition} -> {condition_name} -> {condition_follow_up_value}: \n"
        f"1. {condition_assigned_user[1]}\n"
        f"2. {condition_assigned_user[2]}\n"
        f"3. {condition_assigned_user[3]}\n"
    )
    assigned_user_selector = int(input("Select the number of user to be assigned: "))
    if assigned_user_selector == 3:
        condition_assigned_user_value = str(input("Type in the name of the assigned user: "))
    elif assigned_user_selector == 1 or assigned_user_selector == 2:
        condition_assigned_user_value = condition_assigned_user[assigned_user_selector]


    # Display condition
    print(
        f"Adding condition:\n"
        f"{user_designation[pipeline_user_selector][0]} Pipeline -> {column_to_condition} -> {condition_name} -> {condition_follow_up_value} -> assign to {condition_assigned_user_value}\n"
    )
    input('Press enter to continue...')

    # Append condition to the pipeline list of conditions
    # Sample input: [{'Offer Ready': ['Deal - Stage', 'AA - Follow Up', 'Deal Owner']}]
    condition_dict[pipeline_user_selector].append({condition_name: [column_to_condition, condition_follow_up_value, condition_assigned_user_value]})


def display_all_pipeline_conditions(user_designation, condition_dict) -> None:
    
    # Initialize condition variable
    condition_found = False

    # Clear screen
    os.system('cls')

    # Iterate through conditions dictionary
    for key, pipeline_conditions_value in condition_dict.items():
        if len(pipeline_conditions_value) > 0:

            condition_found = True
            print("\n====================================================================================================")
            print(f"\n{user_designation[key][0]} Pipeline Condtions:\n")

            # Iterate through conditions list
            for index, conditions in enumerate(pipeline_conditions_value):
                for condition, values in conditions.items():
                    print(
                        f"    {index + 1}. {user_designation[key][0]} Pipeline -> {values[0]} -> {condition} -> {values[1]} -> assign to {values[2]}"
                    )

    if not condition_found:
        print('There are no conditions to any of the pipelines')
        input('Press enter to continue...')
    
    else:
        print("\n====================================================================================================\n")
        input('Press enter to continue...')


def display_conditions(conditions_dict: dict, user_designation: dict, pipeline_user_selector: int) -> None:
    '''
    Displays all of the conditions for the pipeline that was selected by the end user.\n

    Parameters:
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline.\n
        `pipeline_user_selector (int)` - Pipeline number that was selected by the end user.\n

    Return:
        `None`
    '''

    if len(conditions_dict[pipeline_user_selector]) == 0: # If there are no conditions per the selected pipeline
        print('There are no conditions for this pipeline')
        input('Press enter to continue...')

    else: # If there are conditions in the selected pipeline

        # Clear screen
        os.system('cls')

        print(f"{user_designation[pipeline_user_selector][0]} Pipeline Conditions:\n")
        for index, conditions in enumerate(conditions_dict[pipeline_user_selector]):
            for condition, values in conditions.items():
                print(
                    f"{index + 1}. {user_designation[pipeline_user_selector][0]} Pipeline -> {values[0]} -> {condition} -> {values[1]} -> assign to {values[2]}"
                )
        input('\nPress enter to continue...')


def remove_conditions(conditions_dict: dict, user_designation: dict, pipeline_user_selector: int) -> None:
    '''
    Removes a specific condition selected by the end user.\n

    Parameters:
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline.\n
        `pipeline_user_selector (int)` - Pipeline number that was selected by the end user.\n

    Return:
        `None`
    '''

    if len(conditions_dict[pipeline_user_selector]) == 0: # If there are no conditions per the selected pipeline
        print('There are no conditions for this pipeline')
        input('Press enter to continue...')

    else: # If there are conditions in the selected pipeline

        # Clear screen
        os.system('cls')

        print('Remove Condition:\n')

        print(f"{user_designation[pipeline_user_selector][0]} Pipeline Conditions:\n")
        for index, conditions in enumerate(conditions_dict[pipeline_user_selector]): # Iterate through list of condition dictionaries
            for condition, values in conditions.items():
                print(
                    f"{index + 1}. {user_designation[pipeline_user_selector][0]} Pipeline -> {values[0]} -> {condition} -> {values[1]} -> assign to {values[2]}"
                )

        condition_num_to_remove = int(input('\nSelect the number of the condition you want to remove: '))
        if condition_num_to_remove <= len(conditions_dict[pipeline_user_selector]):
            del conditions_dict[pipeline_user_selector][condition_num_to_remove - 1] # subtract 1 to become index
        else:
            print('Invalid input')
            input('Press enter to continue...')


def conditions_values() -> dict:
    '''
    This function contains default values of condition dictionary.\n

    Parameters:
        `None`

    Return:
        `conditions_dict (dict)` - Dictionary of conditions per pipeline with default values.\n
    '''

    # Dictionary of conditions default values
    conditions_dict = {
        1:  [],
        2:  [],
        3:  [],
        4:  [],
        5:  [],
        6:  [],
        7:  [],
        8:  [],
        9:  [],
        10: [],
    }

    return conditions_dict



def pipeline_values() -> dict:
    '''
    This functions contains default values of user designation dictionary.\n

    Parameters:
        `None`

    Return:
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline with default values.\n
    '''

    # Dictionary of follow up and assigned user default values
    user_designation = {
        1:  ['Qualifying', 'None', 'None'],
        2:  ['Conversion','None', 'None'],
        3:  ['Underwriting', 'None', 'None'],
        4:  ['Sales', 'None', 'None'],
        5:  ['Junior Sales', 'None', 'None'],
        6:  ['White Glove', 'None', 'None'],
        7:  ['Fast Close', 'None', 'None'],
        8:  ['PSA', 'None', 'None'],
        9:  ['Diligence', 'None', 'None'],
        10: ['Closing', 'None', 'None']
    }

    return user_designation


def read_conditions_designations() -> 'tuple[dict, dict]':
    '''
    Reads saved JSON Data from project directory.\n

    Parameters:
        `None`

    Return:
        `user_designations (dict)` - Dictionary equivalent of the JSON Data of assigned users and follow up per pipeline.\n
        `conditions_dict (dict)` - Dictionary equivalent of the JSON Data of conditions per pipeline.\n
    '''

    # Define path
    conditions_path = 'data/conditions_input/conditions_dict.json'
    user_designation_path = 'data/conditions_input/user_designation.json'

    # Designations
    with open(user_designation_path, 'r') as designations_json_file:
        user_designations_dict = json.load(designations_json_file)

    # Conditions
    with open(conditions_path, 'r') as conditions_json_file:
        conditions_dict = json.load(conditions_json_file)

    
    return user_designations_dict, conditions_dict


def save_conditions_designations(user_designations_dict: dict, conditions_dict: dict) -> None:
    '''
    Saves the dictionaries of data to JSON Data for data persistence.\n

    Parameters:
        `user_designations_dict (dict)` - Dictionary of assigned user and follow up per pipeline.\n
        `conditions_dict (dict)` - Dictionary of conditions per pipeline.\n

    Return:
        `None`
    '''

    # Define path
    conditions_path = 'data/conditions_input/conditions_dict.json'
    user_designation_path = 'data/conditions_input/user_designation.json'

    # Overwrite conditions_dict.json
    with open(conditions_path, 'w') as conditions_json_file:
        json.dump(conditions_dict, conditions_json_file)

    # Overwrite user_designation.json
    with open(user_designation_path, 'w') as designations_json_file:
        json.dump(user_designations_dict, designations_json_file)


def update_display(pipeline_user_selector: int, user_designation: dict, condition_dict: dict) -> None:
    '''
    This function is a window after the user selected a specific pipeline to modify and transact to.\n

    Parameters:
        `pipeline_user_selector (int)` - Pipeline number that was selected by the user from the main window.\n
        `user_designation (dict)` - Dictionary that contains follow up and assigned user per pipeline.\n
        `condition_dict (dict)` - Dictionary that contains conditions per pipeline.\n

    Return:
        `None`
    '''

    # Initialize variables
    update_selector = 1
    pipeline_name = user_designation[pipeline_user_selector][0]
    values_to_change = user_designation[pipeline_user_selector]

    while update_selector != 6:

        # Clear screen
        os.system('cls')
        
        # Display update window
        print(
            f"{user_designation[pipeline_user_selector][0]} Pipeline:\n" # Pipeline name
            f"{'1. Follow Up      ':<40}{user_designation[pipeline_user_selector][1]}\n" # Follow Up
            f"{'2. Assigned User  ':<40}{user_designation[pipeline_user_selector][2]}\n" # Assigned User
            "3. Add conditions\n"
            "4. Check all conditions\n"
            "5. Remove condition\n"
            "6. Back\n"
        )

        update_selector = int(input("Select a number to transact: "))

        if update_selector in [1, 2]:
            input_update(update_selector, pipeline_name, values_to_change)

        elif update_selector == 3:
            pipeline_conditions(pipeline_user_selector, user_designation, condition_dict)
        
        elif update_selector == 4:
            display_conditions(condition_dict, user_designation, pipeline_user_selector)

        elif update_selector == 5:
            remove_conditions(condition_dict, user_designation, pipeline_user_selector)


def input_update(update_selector: int, pipeline_name: str, dict_values: list) -> None:
    '''
    This function is a window that will update the values of follow up, assigned user, and add or remove conditions per pipeline.\n

    Parameters:
        `update_selector (int)` - Item number that was selected by the user to transact to.\n
        `pipeline_name (str)` - String name value of the pipeline that was selected by the user.\n
        `dict_values (list)` - List of values of the element from `user_designation` dictionary that was selected by the user.\n
    
    Return:
        `None`
    '''

    # Clear screen
    os.system('cls')
    
    # Follow Up
    if update_selector == 1: 

        follow_up_dict = {
            1: 'CT - Abandoned Call Follow Up',
            2: 'AA - Abandoned Call Follow Up',
            3: 'CA - Abandoned Call Follow Up',
            4: 'PD - Abandoned Call Follow Up',
            5: 'Type in the follow up task'
        }

        print(
            f"{pipeline_name} Pipeline -> Follow Up:\n"
            f"1. {follow_up_dict[1]}\n"
            f"2. {follow_up_dict[2]}\n"
            f"3. {follow_up_dict[3]}\n"
            f"4. {follow_up_dict[4]}\n"
            f"5. {follow_up_dict[5]}\n"
        )

        follow_up_selector = int(input("Select a number: "))

        if follow_up_selector == 5:
            dict_values[1] = str(input("Type in the follow up task: "))
        elif follow_up_selector in [1, 2, 3, 4]:
            dict_values[1] = follow_up_dict[follow_up_selector] # Assign to follow up index of the list

    # Assigned User
    elif update_selector == 2: 
        
        assigned_user_dict = {
            1: 'Deal Owner',
            2: 'CA Tracking Flag',
            3: 'Type in the name of the assigned user',
        }

        print(
            f"{pipeline_name} Pipeline -> Assigned User:\n"
            f"1. {assigned_user_dict[1]}\n"
            f"2. {assigned_user_dict[2]}\n"
            f"3. {assigned_user_dict[3]}\n"
        )

        assigned_user_selector = int(input("Select a number: "))

        if assigned_user_selector == 3:
            dict_values[2] = str(input("Type in the name of the assigned user: ")) # Assign to assigned user index of the list

        elif assigned_user_selector == 1 or assigned_user_selector == 2:
            dict_values[2] = assigned_user_dict[assigned_user_selector] # Assign to assigned user index of the list
    

def main_display(user_designation: dict) -> None:
    '''
    This function will display all of the pipelines, follow up and assigned user.\n

    Parameters:
        `user_designation (dict)` - Dictionary of follow up and assigned user per pipeline.\n

    Return:
        `None`
    '''

    # If there are no pipeline saved in the JSON File
    if len(user_designation) <= 0:
        print('There are currently no pipeline saved')

    else: # If there are any pipeline

        print(f"{'Follow Up':>34}{'Assigned User':>45}\n")

        for key, value in user_designation.items():
            print(f"{key:<3} {value[0]:<20} {value[1]:<40} {value[2]:<20}")

        # print(
        #     f"{'Follow Up':>34}{'Assigned User':>45}\n"
        #     f"1.  {'Qualifying':<20} {user_designation[1][1]:<40} {user_designation[1][2]:<20}\n"
        #     f"2.  {'Conversion':<20} {user_designation[2][1]:<40} {user_designation[2][2]:<20}\n"
        #     f"3.  {'Underwriting':<20} {user_designation[3][1]:<40} {user_designation[3][2]:<20}\n"
        #     f"4.  {'Sales':<20} {user_designation[4][1]:<40} {user_designation[4][2]:<20}\n"
        #     f"5.  {'Junior Sales':<20} {user_designation[5][1]:<40} {user_designation[5][2]:<20}\n"
        #     f"6.  {'White Glove':<20} {user_designation[6][1]:<40} {user_designation[6][2]:<20}\n"
        #     f"7.  {'Fast Close':<20} {user_designation[7][1]:<40} {user_designation[7][2]:<20}\n"
        #     f"8.  {'PSA':<20} {user_designation[8][1]:<40} {user_designation[8][2]:<20}\n"
        #     f"9.  {'Diligence':<20} {user_designation[9][1]:<40} {user_designation[9][2]:<20}\n"
        #     f"10. {'Closing':<20} {user_designation[10][1]:<40} {user_designation[10][2]:<20}\n"
        #     "\nr. Remove a pipeline\n"
        #     "\n0. EXECUTE THE TOOL\n\n"
        # )

        print(
            "\n\na - Add a pipeline\n"
            "c - Check all pipeline conditions\n"
            "r - Remove a pipeline\n"
            "t - Reset pipeline values\n"
            "s - Save and exit\n"
            "x - Save and Run the tool\n"
        )


def ask_user_input() -> 'tuple[dict | None, dict | None]':
    '''
    This function is the main driver function of this module.
    Displays a basic Command Line Interface to ask for users for inputs for follow up, assigned users and stages per pipeline
    and saves the data as JSON Data for data persistence.\n

    Parameters:
        `None`

    Return:
        `user_designation (dict)` - Dictionary contains follow up and assigned user per pipeline.\n
        `user_designation (dict)` - Dictionary contains stages and conditions per pipeline.\n
        `None` - If the user decided to just save the data of follow up, users and conditions, this function will return None.\n
    '''

    # Initialize variable for loop
    # user_designation = pipeline_values()
    # condition_dict = conditions_values()

    # Read JSON File and change the keys to int data type
    user_designation_raw, condition_dict_raw = read_conditions_designations()
    user_designation = {int(key): value for key, value in user_designation_raw.items()}
    condition_dict = {int(key): value for key, value in condition_dict_raw.items()}

    # Start main loop
    while True:

        # Display main window
        main_display(user_designation)
        
        try:
            pipeline_user_selector = input('Select a number or letter to transact: ')
            
            if pipeline_user_selector.isdigit():
                pipeline_user_selector = int(pipeline_user_selector)

                # Display update pipeline window
                if len(user_designation) >= pipeline_user_selector > 0:
                    update_display(pipeline_user_selector, user_designation, condition_dict)

                else:
                    print('Invalid input.')
                    input('Press enter to continue...')

            # Run and display remove pipeline window
            elif pipeline_user_selector.lower() == 'r':
                remove_pipeline(user_designation, condition_dict)

            elif pipeline_user_selector.lower() == 'c':
                display_all_pipeline_conditions(user_designation, condition_dict)

            # Run and display add pipeline window
            elif pipeline_user_selector.lower() == 'a':
                add_pipeline(user_designation, condition_dict)

            # Run and display reset pipeline window
            elif pipeline_user_selector.lower() == 't':
                user_designation, condition_dict = reset_pipeline_values(user_designation, condition_dict)

            # Save the JSON Data and exit the tool
            elif pipeline_user_selector.lower() == 's':
                save_conditions_designations(user_designation, condition_dict) # write and break
                print('Successfully saved data')
                input('Press enter to exit...')
                return None, None

            # Save the JSON Data and run the rest of the tool functions
            elif pipeline_user_selector.lower() == 'x':
                save_conditions_designations(user_designation, condition_dict) # write and execute
                return user_designation, condition_dict

        except ValueError:
            print('Invalid input.')
            input('Press enter to continue...')

        finally:
            os.system('cls')



if __name__ == '__main__':
    ask_user_input()