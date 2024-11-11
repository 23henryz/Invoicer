import os
from intuitlib.client import AuthClient
from intuitlib.exceptions import AuthClientError
from intuitlib.enums import Scopes
import json
import requests

# pip install requests intuit-oauth
client_id = 'ABsJ5NfiAjWetVBqEjxaJJNiMPfXwQqyk5mYZhvBwG2bIPJcCY'
client_secret = 'brR1DzsIMwEw3JqAjC9uX1H0mqcCQuaVnWqzjsJr'

redirect_uri = "http://localhost:5000/callback"
environment = 'sandbox'  


auth_client = AuthClient(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    environment=environment,
)

# authorization_url = auth_client.get_authorization_url([Scopes.ACCOUNTING])
# print(f"URL: {authorization_url}")



def save_tokens_to_file(tokens):
    with open('tokens.json', 'w') as token_file:
        json.dump(tokens, token_file)



def refresh_access_token():
    tokens = get_tokens_from_file()
    if not tokens:
        return None

    refresh_token = tokens['refresh_token']

    try:

        auth_client.refresh(refresh_token)


        new_tokens = {
            'access_token': auth_client.access_token,
            'refresh_token': auth_client.refresh_token,
            'realm_id': tokens['realm_id']
        }
        save_tokens_to_file(new_tokens)
        print("Access token refreshed.")
        return new_tokens

    except AuthClientError as e:
        print(f"Token refresh failed: {e}")
        return None



def get_tokens_from_file():
    try:
        with open('tokens.json', 'r') as token_file:
            tokens = json.load(token_file)
        return tokens
    except FileNotFoundError:
        print("Token file does not exist")
        return None


def send_invoice(access_token, realm_id, invoice_id):
    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/invoice/{invoice_id}/send"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    # Send POST request to send the invoice
    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        print("Invoice sent successfully!")
        return response.json()
    else:
        print(f"request url: {url}")
        print(f"Failed to send invoice: {response.status_code}")
        print(response.json())
        return None


def create_invoice(price, item, email, customer):
    tokens = get_tokens_from_file()
    if not tokens:
        return

    access_token = tokens['access_token']
    realm_id = tokens['realm_id'] 


    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }


    invoice_data = {
        "Line": [{
            "Amount": price,
            "DetailType": "SalesItemLineDetail",
            "SalesItemLineDetail": {
                "ItemRef": {
                    "value": item
                }
            }
        }],
        "CustomerRef": {
            "value": customer  
        },
        "BillEmail": {
            "Address": email  
        },
        "EmailStatus": "NeedToSend",
        "AllowOnlinePayment": True,
        "AllowOnlineCreditCardPayment": True,
        "AllowOnlineACHPayment": True
    }


    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{realm_id}/invoice"


    response = requests.post(url, headers=headers, json=invoice_data)
    print('send request ', invoice_data)


    if response.status_code == 200:
        print("Invoice sent successfully!")
        print("Response info:", response.json())
        invoice_id = response.json()['Invoice']['Id']
        send_invoice(access_token, realm_id, invoice_id)
    elif response.status_code == 401:  
        print("Access token failing，attempting to refresh token...")
        tokens = refresh_access_token()
        if tokens:

            create_invoice(price, item, email, customer)
        else:
            print("Cannot refresh token, failing")
    else:
        print(f"Invoice failed to sent, status: {response.status_code}")
        print("Error information:", response.text)

if __name__ == "__main__":
    # tokens = get_tokens_from_file()
    #
    # access_token = tokens['access_token']
    # realm_id = tokens['realm_id']  # 公司 ID
    #
    # send_invoice(access_token, realm_id, '151')

    authorization_url = auth_client.get_authorization_url([Scopes.ACCOUNTING])
    print(f"Please visit the following URL to authenticate: {authorization_url}")