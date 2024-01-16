from flask import Flask, request
from twilio.twiml.voice_response import Gather, VoiceResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from word2number import w2n
import pyodbc as db
from ast import literal_eval
from itertools import zip_longest
from twilio.http.http_client import TwilioHttpClient
import requests
import certifi
import uuid
import datetime
import firebase_admin
from firebase_admin import credentials,auth
from firebase_admin import firestore
cred = credentials.Certificate("./ivrapp-a8748-firebase-adminsdk-oktco-0f76968c07.json")
defaultApp = firebase_admin.initialize_app(cred)
from twilio.twiml.messaging_response import MessagingResponse

db_fire = firestore.client()



conn = db.connect('DRIVER={ODBC Driver 11 for SQL Server};SERVER=JARVIS\SQLEXPRESS;DATABASE=medicine;UID=sa;PWD=linto123')
conn.setdecoding(db.SQL_CHAR, encoding='latin1')
conn.setencoding('latin1')

app = Flask(__name__)
ca_bundle_path = certifi.where()
session = requests.Session()
session.verify = ca_bundle_path

# Create the Twilio client with the custom session
account_sid='ACd4c9688df25b355c3a08ee142066a2c0'
token = '2ce57dd57ca2385ca74eeca7fd99bf23'
twilio_client = Client(http_client=requests.Session())

order_bot = None  
user_name = None
phone_number = None

class OrderChatbot:
    def __init__(self):
        self.order = []
        self.current_order = {}
        self.order_number = 1
        self.current_item = None
        self.current_quantity = None
        self.available  = None
        self.total_cost = 0

    def start_chat(self):
        print("Welcome to the Order Chatbot!")
        print("You can order items by typing 'order <item> <quantity>'.")
        print("Type 'done' when you are finished with your order.")
        
        while True:
            user_input = input("User: ")
            response = self.process_input(user_input)
            print("Bot:", response)
            
            if user_input.lower() == 'done':
                break

    def process_input(self, user_input):
       
        if user_input.lower() == 'done':# Order final
            return self.finalize_order()
        elif user_input.lower() == 'status': #Know about order details
            return self.check_order_status()
        elif user_input.startswith('order'): #Order command
            return self.add_to_order(user_input)
        elif user_input.isdigit() and int(user_input)<3: # User choice
            return self.handle_user_choice(user_input)
        elif user_input.isdigit() and 4>=int(user_input)>2:# select quantity available or alternative
            return self.handle_order(user_input)
        elif user_input.isdigit() and int(user_input)==5:
            return self.handle_alternative(user_input)
        elif user_input.isdigit() and int(user_input)==6:
            return self.add_to_order(user_input)
        else:
            return "Sorry, I didn't understand that. Please use the format 'order firstmedicinename quantity' or say 'status' to check your order."

    def add_to_order(self, user_input):
        try:
            _, item, quantity = user_input.split()

            if quantity.isdigit():
             quantity = int(quantity)
            else:
             quantity = w2n.word_to_num(quantity) 


            # Check if there are multiple options for the item
            options = self.get_item_options(item)
            if options:
                self.current_item = item
                self.current_quantity = quantity
                return self.ask_user_for_choice(item, options)
                
            if item in self.order:
                available = self.check_inventory(item,quantity)
                if available == 'yes':
                    self.current_order = {'medicine':item,'quantity':quantity}
                    if self.order:
                        for i in range(1,len(self.order)):
                          if self.order[i]['medicine'] == item:
                              self.order[i]['quantity'] +=quantity
                              

                elif available!='yes'or'no':
                    return self.ask_order(item,quantity,available)    
                else:
                    return self.find_alternative(item,quantity)    
            else:
                 if self.check_inventory(item,quantity)=='yes':
                    self.order.append({'medicine':item,'quantity':quantity})
                    print('adding new item')
                    self.order_number += 1
                    return f"Added {quantity} {item}(s) to your order."
                 else:
                     return "Sorry we don't have the required medicine try saying only the first name of the medicine"    
                
           
        except ValueError:
            return "Invalid input. Please use the format 'order <item> <quantity>'."

    
    def ask_order(self,item,available):
        self.available = available
        prompt =f"Inventory only have {available} quantity of {item} if you want to proceed press 3 for alternative press 4"
        return prompt

    def handle_order(self,choice):
          choice = int(choice)
          if choice == 3:
                self.current_order = {'medicine':self.current_item,'quantity':self.available}
                order_present = -1
                if self.order:
                    for key , order in enumerate(self.order):
                      if order['medicine'] == self.current_item:
                          order_present = key
                              
                if order_present>=0:  
                   self.order[order_present]['quantity'] += self.available

                else:
                  self.order.append(self.current_order)
                  self.order_number +=1
                return f"Added {self.available} {self.current_item}(s) to your order."       
          else :
            return self.find_alternative(self.current_item, self.current_quantity)



    def check_inventory(self,item,quant):
        cursor = conn.cursor()
        print(item)
        cursor.execute("""SELECT quantity, prescription FROM inventory 
                       join medicines on inventory.med_key = medicines.med_key
                       join prescription on inventory.med_key = prescription.med_key
                        where name = ? """,f'{item}')
        rows = cursor.fetchall()
        print(rows)
        print('checking inventory....')
        try:
            prescription = (rows[0][1])
            quantity = (rows[0][0])
            print(rows)
        except:
            quantity = 0    
        if quantity>0 and quantity>quant and prescription == 0:
            return 'yes'
        elif quantity>0 and quantity<quant and prescription == 0:
            return quantity
        elif prescription == 1:
            return 'prescription'
        else:
            return'no'

    def find_alternative(self,item,quantity):
        cursor = conn.cursor()
        cursor.execute("select use_key,comp_id from medicines where name = ?",item)
        print(item)
        rows = cursor.fetchall()
        print(rows)
        cursor.execute("""
                SELECT m.name ,s.side_effects
                FROM medicines m
                JOIN prescription p ON p.med_key = m.med_key       
                JOIN uses u ON m.use_key = u.use_id
                JOIN inventory i ON i.med_key = m.med_key
                JOIN side_effect s ON s.side_effect_id = m.side_effect_id      
                WHERE u.use_id = ? AND m.comp_id = ? AND i.quantity > ? AND p.prescription = 0""", (rows[0][0], rows[0][1], quantity)  )
        rows = cursor.fetchall()
        
        if rows:
            self.current_item = rows[1][0]
            se_list = literal_eval(rows[1][1])
            se_prompt =', '.join(str(se) for se in se_list) 
        else :
            return 'We have no alternative for this medicine in the provided quantity'   
        print(self.current_item)
 
        return f'You can have a alternative to {item} as inventory have no {item} for the provided quantity-->alternative is {self.current_item} and it have may cause {se_prompt} .Press 5 for ordering else Press 6 for dropping the order'
       

    def handle_alternative(self,choice):
        choice = int(choice)
        if choice == 5 :
            order_present = -1
            self.current_order = {'medicine':self.current_item,'quantity':self.current_quantity}
            if self.order:
                  for key , order in enumerate(self.order):
                      if order['medicine'] == self.current_item:
                          order_present = key

                              
            if order_present>=0:
                self.order[order_present]['quantity'] += self.current_quantity
            else:
                self.order.append(self.current_order)
                self.order_number+=1
                print(self.order_number)
            return f"Added {self.current_quantity} {self.current_item}(s) to your order."
        else:
            return 'As you have not pressed any key or pressed a wrong key continue with your order'
                    

    def ask_user_for_choice(self, item, options):
       
        options_prompt = "\n".join(f"Press {i+1} for {option}" for i, option in enumerate(options))
        options_list = " or ".join(f"{option}" for option in options)
        prompt = f"By saying {item} did you mean {options_list}? {options_prompt}"
        return prompt
    
    def handle_user_choice(self, choice):
        options = self.get_item_options(self.current_item)
      
        choice = int(choice)
      
        if choice < 0 or choice > len(options):
            options_prompt = "\n".join(f"Press {i+1} for {option}" for i, option in enumerate(options))
            return f"Invalid choice. Please try again.{options_prompt}"
        
        item = options[choice-1]
        self.current_item = item
        available = self.check_inventory(item,self.current_quantity)
              
        if self.check_inventory(item,self.current_quantity) =='yes':
            print(self.check_inventory(item,self.current_quantity) =='yes')
            order_present = -1
            self.current_order = {'medicine':self.current_item,'quantity':self.current_quantity}
           
            if self.order :
                 for key , order in enumerate(self.order):
                      print(key , order)
                      if str(order['medicine']) == str(self.current_item):
                          order_present = key

            print(order_present)
            if order_present>=0:
                self.order[order_present]['quantity'] += self.current_quantity
            
            else:
                print('debug')
                self.order.append(self.current_order)
                self.order_number += 1
            return f"Added {self.current_quantity} {item} to your order."
        
        elif available not in ['yes', 'no', 'prescription']:
                print('ask')
                print(available)
                return self.ask_order(item,available)   
        elif available == 'prescription':
            return f'{self.current_item} needs prescription for ordering use our application for buying medicines using prescription'
        else:
            print('alternative')
            return  self.find_alternative(item,available)  
        


    def finalize_order(self):
        if not self.order:
            return "Your order is empty. Goodbye!"
        items = []
        quants = []
       
        total_cost = sum(self.calculate_cost(data['medicine'], data['quantity']) for data in self.order)
       
        for order in self.order:
            quants.append(order['quantity'])
            items.append(order['medicine'])
            quantity_prompt = "\n".join(f"{quants[i]} quantity of {item}" for i, item in enumerate(items))    
        self.total_cost = total_cost
        order = {'id':str(uuid.uuid4()) ,'medicineName':[]}
      
        
        query = db_fire.collection("users").where("phoneNumber", "==", '9324309587')

        docs = query.get()
        if docs:
            userid = docs[0].id
        else:
            user = {'address':'','email':'','id':str(uuid.uuid4()),'phoneNumber':'9324309587','username':''}
            db_fire.collection("users").document(user['id']).set(user)
            userid = user['id']

      
        order['medicineName'] = items
        order['quantity'] = quants
        order['totalCost'] =self.total_cost
        order['userid'] = userid
        order['orderTitle'] = 'Linto'
        now = datetime.datetime.now()
        order['orderDate'] = now.strftime("%Y-%m-%d %H:%M:%S")
        print(order)
        db_fire.collection("orders").document(order['id']).set(order)
        return f"Thank you for your order! You ordered {quantity_prompt} with a total cost of ${self.total_cost:.2f}. Goodbye!"

    def calculate_cost(self, item, quantity):
        
        item_price = 5
        return item_price * quantity


    def check_order_status(self):
        if not self.order:
            return "Your order is empty."
        else:
            return f"Your current order: {self.order}"
        
    def get_item_options(self, item):
        cursor = conn.cursor()
        cursor.execute(f"SELECT TOP 2 name FROM medicines where name like '{item}%'  ")
        rows = cursor.fetchall()
        print(rows[0][0])
        options_map = {
            
        }
        lst = []
        
        try:
         if len(rows) > 0:
            lst.append(rows[0][0])

         if len(rows) > 1 and rows[1][0]:
            lst.append(rows[1][0])
        except IndexError:
         pass
        options_map[item] = lst
        print(options_map)
        return options_map.get(item, [])
    

@app.route("/welcome", methods=['GET', 'POST'])
def welcome():
    response = VoiceResponse()
    print(f'Incoming call from {request.form["From"]}')
    phone_number = request.form["From"]
    print(phone_number)
    response.say('Welcome to medicine ordering chatbot.')
    response.redirect('/voice')
    return str(response)


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()
    
    response = VoiceResponse()
    gather = Gather(action='/handle-order', method='POST', input='speech',enhanced = True,speechModel = 'phone_call',language= 'en-IN',speech_timeout='auto')
    gather.say('Please say your order or "status" to know about your order')
    response.append(gather)
    return str(response)

@app.route('/add_more', methods=['POST'])
def add_items():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()

    response = VoiceResponse()

    gather = Gather(action='/handle-order', method='POST',language= 'en-IN',enhanced = True,speechModel = 'phone_call', input='speech',speech_timeout='auto')
    gather.say("Please say your order to add more items or say 'status' to check your order. If you are done then say done")
    response.append(gather)
    return str(response)

@app.route("/handle-order", methods=['GET', 'POST'])
def handle_order():
    global order_bot

    order_details = request.values.get('SpeechResult', None)
    print('User: ',order_details)
    if order_details:
        order_bot_response = order_bot.process_input(order_details)
        response = VoiceResponse()
        response.say(order_bot_response)
        print('Bot: ',order_bot_response)
        if any(word in order_bot_response.lower() for word in ('invalid input', 'sorry', 'wrong input')):
            response.redirect('/voice')
        elif 'Added' in order_bot_response:
            response.redirect('/add_more')
        elif any(word.lower() in order_bot_response.lower() for word in ('Which', 'Press')):
            response.redirect('/get_user_choice')  # Redirect to ask for user's choice
        elif  any(word.lower() in order_bot_response.lower() for word in ()):
            response.hangup() 
            return
    else:
        response = VoiceResponse()
        response.say("Sorry, I didn't catch that. Please try again.")

    return str(response)

@app.route("/get_user_choice", methods=['GET', 'POST'])
def get_user_choice():
    global order_bot

    response = VoiceResponse()

    gather = Gather( action="/handle-user-choice",method="POST",input='dtmf', timeout=10) 
    gather.say("Please press the number corresponding to your choice.")
    response.append(gather)
    return str(response)

@app.route("/handle-user-choice", methods=['GET', 'POST'])
def handle_user_choice():
    global order_bot
    response = VoiceResponse()
    response.say('Please wait till we process your order')
    c =1
    choice = request.values.get('Digits', None)
    print(choice)
    print(choice.isdigit())
    if choice and choice.isdigit():
        c == int(choice)
        print(c)
        if c<3:
            choice = c - 1 
            order_bot_response = order_bot.handle_user_choice(choice)
        elif 2<c<=4:
            order_bot_response = order_bot.handle_order(choice)   
        elif c == 5:
            order_bot_response = order_bot.handle_alternative(choice)   
        elif c ==6:
            response.redirect('/add_more')   
        
        response.say(order_bot_response)

        if 'Added' in order_bot_response:
            response.redirect('/add_more')  # Redirect to add more items
        elif 'prescription' in order_bot_response:
            resp = MessagingResponse()
            resp.message('hellooo')
        else:
            response.redirect('/voice')  # Redirect to continue the conversation
    else:
        response = VoiceResponse()
        response.say("Invalid choice. Please try again.")
        response.redirect('/get_user_choice')  # Redirect to ask for user's choice

    return str(response)




if __name__ == '__main__':
    # from pyngrok import ngrok
    # port = 5000
    # public_url = ngrok.connect(port, bind_tls=True).public_url
    # print(public_url)

    # number = twilio_client.incoming_phone_numbers.list()[0]

    # number.update(voice_url=public_url + '/welcome')
   
    # print(f'Waiting for calls on {number.phone_number}')
    # app.run(port=port)

    order_bot = OrderChatbot()
    order_bot.start_chat()