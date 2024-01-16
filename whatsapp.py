from flask import Flask, request
from twilio.twiml.voice_response import Gather, VoiceResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from ast import literal_eval
from itertools import zip_longest
from twilio.http.http_client import TwilioHttpClient
import requests
import certifi
import pyrebase
from token_gen import customiser
import random

firebaseConfig = {
  'apiKey': "AIzaSyCuIOvwxtuROuABnbnfvFY7IH-oSNgF2Jo",
  'authDomain': "ordinal-verbena-410615.firebaseapp.com",
  'projectId': "ordinal-verbena-410615",
  "databaseURL" : "",
  'storageBucket': "ordinal-verbena-410615.appspot.com",
  'messagingSenderId': "671346019365",
  'appId': "1:671346019365:web:2e35d8b9fb5b6978d083cc",
  'measurementId': "G-NJCFMZ0J6E"

}


firbase = pyrebase.initialize_app(firebaseConfig)


#db = firbase.database()
auth = firbase.auth()
#storage = firbase.storage()



app = Flask(__name__)
ca_bundle_path = certifi.where()
session = requests.Session()
session.verify = ca_bundle_path

# Create the Twilio client with the custom session
twilio_client = Client(http_client=requests.Session())


class Verifybot:
    def __init__(self):
        self.order = []
     
    def process_input(self, user_input):
       
        if user_input.lower() == 'Hello':# Order final
            return self.finalize_order()
        elif user_input.lower() == 'status': #Know about order details
            return self.check_order_status()
        else:
            return "Sorry, I didn't understand that. Please use the format 'order firstmedicinename quantity' or say 'status' to check your order."

    def greetings(self):
      
        return 'Hello, Please provide your name'
    
    def user_account(self,user_input):
        user_input 



@app.route('/chat',methods=['POST'])
def bot():
    incoming_msg = request.values.get('Body','').strip()
    print(incoming_msg)

    resp = MessagingResponse()
    resp.message('hellooo')
    key = 'linto'
    resp.message('Write your name')
    
    token = customiser(incoming_msg.lower())
    if key == incoming_msg.lower() :
        auth.sign_in_with_custom_token(token.decode("utf-8"))
    else:
        print("Wrong key!!")

    
    return str(resp)



if __name__ == '__main__':
    from pyngrok import ngrok
    port = 5000
    public_url = ngrok.connect(port, bind_tls=True).public_url
    print(public_url)
    
    number = twilio_client.incoming_phone_numbers.list()[0]
    number.update(voice_url=public_url + '/voice',sms_url = public_url+'/chat')
   
    print(f'Waiting for calls on {number.phone_number}')
    app.run(port=port)
