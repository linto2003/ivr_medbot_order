import firebase_admin
from firebase_admin import credentials,auth

cred = credentials.Certificate("./ordinal-verbena-410615-firebase-adminsdk-3w2tt-994f856bc8.json")
defaultApp = firebase_admin.initialize_app(cred)

uid= ''

def customiser(uid_name):
    uid = f'{uid_name}'
    print(uid)
    custom_token = auth.create_custom_token(uid)

    return custom_token
