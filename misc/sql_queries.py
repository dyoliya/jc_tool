phone_number_query = '''
    SELECT
        c.id,
        n.phone_number
    FROM contacts c
    LEFT JOIN contact_phone_numbers n ON c.id = n.contact_id
    WHERE
        c.deleted_at IS NULL AND
        n.deleted_at IS NULL;
'''

email_address_query = '''
    SELECT
        c.id,
        e.email_address
    FROM contacts c
    LEFT JOIN contact_email_addresses e ON c.id = e.contact_id
    WHERE
        c.deleted_at IS NULL AND
        e.deleted_at IS NULL;
'''

serial_numbers_query = '''
    SELECT
        c.id,
        GROUP_CONCAT(s.serial_number, ' | ') AS serial_numbers
    FROM contacts c
    LEFT JOIN contact_serial_numbers s ON c.id = s.contact_id
    WHERE
        c.deleted_at IS NULL AND
        s.deleted_at IS NULL
    GROUP BY c.id;
'''

serial_numbers_query_mysql = '''
    SELECT
        c.id,
        GROUP_CONCAT(s.serial_number SEPARATOR ' | ') AS serial_numbers
    FROM contacts c
    LEFT JOIN contact_serial_numbers s ON c.id = s.contact_id
    WHERE
        c.deleted_at IS NULL AND
        s.deleted_at IS NULL
    GROUP BY c.id;
'''

cm_db_query = '''
    SELECT
        c.id, c.first_name, c.middle_name, c.last_name, c.deal_id,
        a.address, a.city, a.state AS state_address, a.postal_code, a.data_source,
        t.country, t.state
    FROM contacts c
    LEFT JOIN contact_skip_traced_addresses a ON c.id = a.contact_id AND a.deleted_at IS NULL
    LEFT JOIN contact_targets t ON c.id = t.contact_id AND t.deleted_at IS NULL
    WHERE
        c.deleted_at IS NULL;
'''