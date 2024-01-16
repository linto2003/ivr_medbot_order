import certifi
import os

os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
