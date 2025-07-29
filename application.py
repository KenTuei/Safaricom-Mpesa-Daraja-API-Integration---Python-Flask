from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from static.mpesa_config import generate_access_token, register_mpesa_url, stk_push
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

application = Flask(__name__)

# Setup SQLAlchemy config from .env
db_name = os.environ.get("NAME_OF_YOUR_MYSQL_DB")
db_user = os.environ.get("YOUR_MYSQL_USERNAME")
db_pass = os.environ.get("YOUR_MYSQL_PASSWD")
db_host = os.environ.get("YOUR_MYSQL_HOST")

if not all([db_name, db_user, db_pass, db_host]):
    raise RuntimeError("One or more database environment variables are missing in .env")

application.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}"
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(application)

# Import models after db init
from static.models import client_payments_table

@application.route('/')
def home():
    return render_template('home.html')

@application.route('/mpesa_token')
def mpesa_token():
    try:
        consumer_key = os.environ.get("MPESA_CONSUMER_KEY")
        consumer_secret = os.environ.get("MPESA_CONSUMER_SECRET")

        if not consumer_key or not consumer_secret:
            raise ValueError("Missing MPESA_CONSUMER_KEY or MPESA_CONSUMER_SECRET in .env")

        print("Attempting to generate access token...")
        token = generate_access_token(consumer_key, consumer_secret)

        if not token:
            raise ValueError("Empty access token returned")

        return jsonify({'access_token': token})

    except Exception as e:
        print("Access token error:", repr(e))  # debug log
        return jsonify({'error': str(e)}), 500  # ✅ convert exception to string
@application.route('/register_mpesa_url')
def register():
    return register_mpesa_url()

@application.route('/mobile_payment')
def mobile_payment():
    phone_number = '254115728094'
    amount = 10
    account_reference = 'Ref001'
    transaction_desc = 'Test Payment'
    return stk_push(phone_number, amount, account_reference, transaction_desc)

@application.route('/validate', methods=['POST'])
def validate():
    json_data = request.get_json()
    print("Validation Request:", json_data)
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

@application.route('/confirm', methods=['POST'])
def confirm():
    json_data = request.get_json()
    try:
        payment = client_payments_table(
            TransactionType=json_data.get('TransactionType'),
            TransID=json_data.get('TransID'),
            TransTime=json_data.get('TransTime'),
            TransAmount=json_data.get('TransAmount'),
            BusinessShortCode=json_data.get('BusinessShortCode'),
            BillRefNumber=json_data.get('BillRefNumber'),
            InvoiceNumber=json_data.get('InvoiceNumber'),
            OrgAccountBalance=json_data.get('OrgAccountBalance'),
            ThirdPartyTransID=json_data.get('ThirdPartyTransID'),
            MSISDN=json_data.get('MSISDN'),
            FirstName=json_data.get('FirstName'),
            MiddleName=json_data.get('MiddleName'),
            LastName=json_data.get('LastName')
        )
        db.session.add(payment)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Error saving payment:", e)
        return jsonify({"ResultCode": 1, "ResultDesc": "Failed"}), 500
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

if __name__ == '__main__':
    application.run(debug=True)
