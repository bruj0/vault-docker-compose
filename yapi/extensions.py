import logging
from pprint import pprint

logger = logging.getLogger(__name__)


class Extensions:
    def call_method(self, method_name):
        return getattr(self, method_name)

    #reads a json file and returns a dictionary
    def read_file(self,*args,**kwargs):
        logger.debug(f"Called read_file with {args} and {kwargs}")
        return { 'file_key1': 'val1' ,'file_key2': 'val2'}

    def save_response(self,args,kwargs):
        logger.debug(f"Called save_response with {args} and {kwargs}")
        return True
