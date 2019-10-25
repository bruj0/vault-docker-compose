import json


def save_response(response, filename,mydir=None):
    try:
        if mydir is not None:
            filename= f"{mydir}/{filename}"        
        file = open(filename, 'w')
        json.dump(response.json(), file)
        file.close()
    except FileNotFoundError:
        print(filename + " not found. ")


def save_response_part(response, filename, part):
    try:
        file = open(filename, 'w')
        json.dump(response.json()[part], file)
        file.close()
    except FileNotFoundError:
        print(filename + " not found. ")

def read_init(filename,mydir=None):
    try:
        if mydir is not None:
            filename= f"{mydir}/{filename}"        
        file = open(filename, 'r')
        data = json.load(file)
        file.close()
        return { 'key': data['keys'][0] }
    except FileNotFoundError:
        print(filename + " not found. ")
