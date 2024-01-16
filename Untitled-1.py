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
token = customiser()
key = random.randint(1,5)
print(key)
user_input = int(input("Please enter the key:: "))
if key == user_input :
    auth.sign_in_with_custom_token(token.decode("utf-8"))
else:
    print("Wrong key!!")
