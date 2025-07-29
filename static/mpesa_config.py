from requests.auth import HTTPBasicAuth
from static.mpesa_exceptions import *
from requests import Response
import time
import os
import json
import base64
from datetime import datetime

mpesa_environment = 'production'  # "sandbox" if development, "production" if live
base_url = 'https://example.com'  # your app's domain prefix

sandbox_paybill = '123456'        # sandbox shortcode for simulation
mpesa_paybill = '654321'          # production shortcode

consumer_key = os.environ.get("MPESA_CONSUMER_KEY")
consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET")

if mpesa_environment == 'sandbox':
    business_short_code = sandbox_paybill
else:
    business_short_code = mpesa_paybill


def api_base_url():
    if mpesa_environment == 'sandbox':
        return 'https://sandbox.safaricom.co.ke/'
    elif mpesa_environment == 'production':
        return 'https://api.safaricom.co.ke/'


def format_phone_number(phone_number):
    if len(phone_number) < 9:
        return 'Phone number too short'
    else:
        return '254' + phone_number[-9:]


def generate_access_token(consumer_key, consumer_secret):
    url = api_base_url() + 'oauth/v1/generate?grant_type=client_credentials'

    try:
        r = requests.get(url, auth=HTTPBasicAuth(consumer_key, consumer_secret)).json()
        token = r['access_token']
    except Exception as ex:
        print("Could not generate access code")
        return ex
    return token


def register_mpesa_url():
    mpesa_endpoint = api_base_url() + 'mpesa/c2b/v1/registerurl'
    headers = {
        'Authorization': 'Bearer ' + generate_access_token(consumer_key, consumer_secret),
        'Content-Type': 'application/json'
    }
    req_body = {
        'ShortCode': business_short_code,
        'ResponseType': 'Completed',
        'ConfirmationURL': base_url + '/confirm',
        'ValidationURL': base_url + '/validate'
    }

    response_data = requests.post(mpesa_endpoint, json=req_body, headers=headers)
    return response_data.json()


def stk_push(phone_number, amount, account_reference, transaction_desc):
    if str(account_reference).strip() == '':
        raise MpesaInvalidParameterException('Account reference cannot be blank')
    if str(transaction_desc).strip() == '':
        raise MpesaInvalidParameterException('Transaction description cannot be blank')
    if not isinstance(amount, int):
        raise MpesaInvalidParameterException('Amount must be an integer')

    callback_url = base_url + '/confirm'
    phone_number = format_phone_number(phone_number)
    url = api_base_url() + 'mpesa/stkpush/v1/processrequest'
    passkey = os.environ.get('MPESA_PASSKEY')

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((business_short_code + passkey + timestamp).encode('ascii')).decode('utf-8')
    transaction_type = 'CustomerPayBillOnline'
    party_a = phone_number
    party_b = business_short_code

    data = {
        'BusinessShortCode': business_short_code,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': transaction_type,
        'Amount': amount,
        'PartyA': party_a,
        'PartyB': party_b,
        'PhoneNumber': phone_number,
        'CallBackURL': callback_url,
        'AccountReference': account_reference,
        'TransactionDesc': transaction_desc
    }

    headers = {
        'Authorization': 'Bearer ' + generate_access_token(consumer_key, consumer_secret),
        'Content-Type': 'application/json'
    }

    try:
        r = requests.post(url, json=data, headers=headers)
        response = r.json()
        return response
    except requests.exceptions.ConnectionError:
        raise MpesaConnectionError('Connection failed')
    except Exception as ex:
        raise MpesaConnectionError(str(ex))
