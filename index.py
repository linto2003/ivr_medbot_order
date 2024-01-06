from flask import Flask, request
from twilio.twiml.voice_response import Gather, VoiceResponse
from twilio.rest import Client
from word2number import w2n
import pyodbc as db


conn = db.connect('DRIVER={ODBC Driver 11 for SQL Server};SERVER=JARVIS\SQLEXPRESS;DATABASE=medicine;UID=sa;PWD=linto123')
conn.setdecoding(db.SQL_CHAR, encoding='latin1')
conn.setencoding('latin1')

app = Flask(__name__)
twilio_client = Client()
order_bot = None  # Initialize OrderChatbot globally

class OrderChatbot:
    def __init__(self):
        self.order = {}
        self.current_item = None
        self.current_quantity = None
        self.available  = None

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
        else:
            return "Sorry, I didn't understand that. Please use the format 'order <medicine_name_first> <quantity>' or say 'status' to check your order."

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
                    self.order[item] += quantity
                elif available!='yes'or'no':
                    return self.ask_order(item,quantity,available)    
                else:
                    return self.find_alternative(item,quantity)    
            else:
                 if self.check_inventory(item,quantity)=='yes':
                    self.order[item] = quantity
                    return f"Added {quantity} {item}(s) to your order."
                 else:
                     return "Sorry we don't have the required medicine try saying only the first name of the medicine"    
                
           
        except ValueError:
            return "Invalid input. Please use the format 'order <item> <quantity>'."

    
    def ask_order(self,item,available):
        self.available = available
        prompt =f"Inventory only have {available} number of {item} if you want to proceed press 3 for alternative press 4"
        return prompt

    def handle_order(self,choice):
          choice = int(choice)
          if choice == 3:
              if self.current_item in self.order:  
                 self.order[self.current_item] += self.available
              else:
                  self.order[self.current_item] = self.available
              return f"Added {self.available} {self.current_item}(s) to your order."       
          else :
            return self.find_alternative(self.current_item, self.current_quantity)
          
    def check_inventory(self,item,quant):
        cursor = conn.cursor()
        cursor.execute(f"SELECT quantity FROM inventory join medicines on inventory.med_key = medicines.med_key where name = ?",f'{item}')
        rows = cursor.fetchall()
        try:
            quantity = (rows[0][0])
        except:
            quantity = 0    
        if quantity>0 and quantity>quant:
            return 'yes'
        elif quantity>0 and quantity<quant:
            return quantity
        else:
            return'no'

    def find_alternative(self,item,quantity):
        cursor = conn.cursor()
        cursor.execute("select use_key,comp_id from medicines where name = ?",item)
        print(item)
        rows = cursor.fetchall()
        cursor.execute("""
                SELECT m.name
                FROM medicines m
                JOIN uses u ON m.use_key = u.use_id
                JOIN inventory i ON i.med_key = m.med_key
                WHERE u.use_id = ? AND m.comp_id = ? AND i.quantity > ? """, (rows[0][0], rows[0][1], quantity)  )
        rows = cursor.fetchall()
       
        if rows:
            self.current_item = rows[1][0]
        else :
            return 'We have no alternative for this medicine in the provided quantity'   
        print(self.current_item)

        return f'You can have a alternative to {item} as inventory have no {item} for the provided quantity-->alternative is {self.current_item} Press 5 for ordering else press 6 for dropping the order'
       

    def handle_alternative(self,choice):
        choice = int(choice)
        if choice == 5 :
            if self.current_item in self.order:
                self.order[self.current_item] += self.current_quantity
            else:
                self.order[self.current_item] = self.current_quantity
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
      
        if choice < 0 or choice >= len(options):
            options_prompt = "\n".join(f"Press {i+1} for {option}" for i, option in enumerate(options))
            return f"Invalid choice. Please try again.{options_prompt}"
        
        item = options[choice-1]
        self.current_item = item
        available = self.check_inventory(item,self.current_quantity)
              
        if self.check_inventory(item,self.current_quantity) =='yes':
            if item in self.order:
                self.order[item] += self.current_quantity
            else:
                self.order[item] = self.current_quantity
                
            return f"Added {self.current_quantity} {item} to your order."
        
        elif available!='yes'or'no':
                    return self.ask_order(item,available)   

        else:
            return  self.find_alternative(item,available)  
        


    def finalize_order(self):
        if not self.order:
            return "Your order is empty. Goodbye!"
        items = []
        quants = []
       
        total_cost = sum(self.calculate_cost(item, quantity) for item, quantity in self.order.items())
        for item,quant in self.order.items():
            items.append(item)
            quants.append(quant) 
            quantity_prompt = "\n".join(f"{quants[i]} quantity of {item}" for i, item in enumerate(items))    
       
        return f"Thank you for your order! You ordered {quantity_prompt} with a total cost of ${total_cost:.2f}. Goodbye!"

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

        options_map = {
            
        }
        lst = []
        cursor = conn.cursor()
        try:
         lst = [rows[0][0],rows[1][0]]
        except:
            pass
        options_map[item] = lst
        return options_map.get(item, [])

@app.route("/voice", methods=['GET', 'POST'])
def voice():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()

    response = VoiceResponse()

    with response.gather(input='speech', action="/handle-order", method="POST", language='en-IN', speech_timeout='auto', timeout=5) as gather:
        gather.say("Welcome to the Order Chatbot. Please say your order or say 'status' to check your order.")

    return str(response)

@app.route('/add_more', methods=['POST'])
def add_items():
    global order_bot

    if not order_bot:
        order_bot = OrderChatbot()

    response = VoiceResponse()

    with response.gather(input='speech', action="/handle-order", method="POST", language='en-IN', speech_timeout='auto', timeout=5) as gather:
        gather.say("Please say your order to add more items or say 'status' to check your order. If you are done then say done")

    return str(response)

@app.route("/handle-order", methods=['GET', 'POST'])
def handle_order():
    global order_bot

    order_details = request.values.get('SpeechResult', None)
    print(order_details)
    if order_details:
        order_bot_response = order_bot.process_input(order_details)
        response = VoiceResponse()
        response.say(order_bot_response)
        
        if 'Invalid input' in order_bot_response or 'Sorry' or 'wrong input' in order_bot_response:
            response.redirect('/voice')
        elif 'Added' in order_bot_response:
            response.redirect('/add_more')
        elif 'Which' in order_bot_response:
            response.redirect('/get_user_choice')  # Redirect to ask for user's choice
    
    else:
        response = VoiceResponse()
        response.say("Sorry, I didn't catch that. Please try again.")

    return str(response)

@app.route("/get_user_choice", methods=['GET', 'POST'])
def get_user_choice():
    global order_bot

    response = VoiceResponse()

    with response.gather(input='dtmf', action="/handle-user-choice", method="POST", timeout=2) as gather:
        gather.say("Please press the number corresponding to your choice.")

    return str(response)

@app.route("/handle-user-choice", methods=['GET', 'POST'])
def handle_user_choice():
    global order_bot

    choice = request.values.get('Digits', None)
    print(choice)
    print(choice.isdigit())
    if choice and choice.isdigit():
        choice == int(choice)
        if choice<3:
            choice = choice - 1 
            order_bot_response = order_bot.handle_user_choice(choice)
        elif 2<choice<=4:
            order_bot_response = order_bot.handle_order(choice)   
        elif choice == 5:
            order_bot_response = order_bot.handle_alternative(choice)    
        response = VoiceResponse()
        response.say(order_bot_response)

        if 'Added' in order_bot_response:
            response.redirect('/add_more')  # Redirect to add more items
        else:
            response.redirect('/voice')  # Redirect to continue the conversation
    else:
        response = VoiceResponse()
        response.say("Invalid choice. Please try again.")
        response.redirect('/get_user_choice')  # Redirect to ask for user's choice

    return str(response)

if __name__ == '__main__':
    from pyngrok import ngrok
    port = 5000
    public_url = ngrok.connect(port, bind_tls=True).public_url
    print(public_url)
    number = twilio_client.incoming_phone_numbers.list()[0]
    number.update(voice_url=public_url + '/voice')
    print(f'Waiting for calls on {number.phone_number}')

    app.run(port=port)



