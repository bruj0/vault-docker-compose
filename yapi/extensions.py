import logging
import json
from flatten_json import flatten
from pprint import pprint

logger = logging.getLogger(__name__)


class Extensions:
    def call_method(self, method_name):
        return getattr(self, method_name)

    #reads a json file and returns a dictionary
    def read_json(self,*args,**kwargs):
        try:
            logger.info(f"Reading {kwargs['path']} , sub_vars: {kwargs['sub_vars']}")
            f = open(f"{kwargs['path']}", 'r')
            data = json.load(f)
            #logger.debug(f"Loaded {data}")
            f.close()
            if 'sub_vars' in kwargs:
                return { 'ext': flatten(data) }
            else:
                return data
        except FileNotFoundError:
            logger.exception(f"File not found: {kwargs['path']}")

    def save_response(self,*args,**kwargs):
        #logger.debug(f"Called save_response with {args} and {kwargs}")
        try:
            logger.info(f"Writting to {kwargs['path']} , key: {kwargs['key']}")
            f = open(f"{kwargs['path']}", 'w')
            if 'key' in kwargs:
                data = json.loads(kwargs['response_text'])
                if kwargs['key'] in data:
                    json.dump(data[kwargs['key']],f)
                else:
                    logger.error(f"Key {kwargs['key']} not found in return text")
                    return False
            else:
                f.write(kwargs['response_text'])
            f.close()
            return True
        except Exception as e:
            logger.exception(f"Couldnt write to : {kwargs['path']} {e}")     

    
