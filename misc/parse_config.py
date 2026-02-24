import configparser, os

def extract_config_info():

    # Define path to config file
    file_path = os.path.join('misc', 'database_config.cfg')

    # Parse the config file to extract sensitive information
    reader = configparser.ConfigParser()
    reader.read(file_path)

    # extract info and assign to variables
    db_host = reader['database']['db_host']
    db_port = reader['database']['db_port']
    db_user = reader['database']['db_user']
    db_password = reader['database']['db_password']
    db_name = reader['database']['db_name']

    return db_host, db_port, db_user, db_password, db_name

if __name__ == "__main__":
    print(extract_config_info())
