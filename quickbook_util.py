import requests
import json
from quickbook_service import refresh_access_token


def get_tokens_from_file():
    with open('tokens.json', 'r') as token_file:
        return json.load(token_file)



def get_items():
    tokens = get_tokens_from_file()
    access_token = tokens['access_token']
    realm_id = tokens['realm_id']

    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/query"
    query = "SELECT * FROM Item"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/text'
    }

    response = requests.post(url, headers=headers, data=query)

    if response.status_code == 200:
        items = response.json()['QueryResponse']['Item']
        # for item in items:
        #     print(f"Item: {item['Name']}, ID: {item['Id']}")
        return items
    else:
        print(f"Failed to get item: {response.status_code}")
        print(response.text)


def get_customers():
    tokens = get_tokens_from_file()
    access_token = tokens['access_token']
    realm_id = tokens['realm_id']

    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/query"
    query = "SELECT * FROM Customer"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/text'
    }

    response = requests.post(url, headers=headers, data=query)

    if response.status_code == 200:
        customers = response.json()['QueryResponse']['Customer']
        # for customer in customers:
        #     print(f"Customer: {customer['DisplayName']}, ID: {customer['Id']}")
        return customers
    else:
        print(f"Failed to get customer info: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    refresh_access_token()
    # get_items()
    get_customers()



