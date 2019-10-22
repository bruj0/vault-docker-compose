import json


def save_response(response, filename):
    try:
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
