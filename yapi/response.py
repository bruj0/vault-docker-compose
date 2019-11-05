import logging
from pprint import pformat
from pprint import pprint
from yapi.utils import *
from yapi.extensions import Extensions
import requests
from requests_toolbelt.utils import dump
import json

logger = logging.getLogger(__name__)

class response:
    rsp = {}
    def __init__(self,rsp):
        self.rsp=rsp

    def validate(self,expected):
        rsp = self.rsp
        logger.debug(f"Response data \n{pformat(rsp,width=1)}")
        logger.debug(f"Expected \n{pformat(expected,width=1)}")

        if rsp.status_code != int(expected['status_code']):
            logger.error(f"Received status code {rsp.status_code} != {expected['status_code']}")
            exit(1)
        else:
            logger.info(f"Received status code {rsp.status_code} == {expected['status_code']}")

        logger.debug(f"Response text\n{rsp.text}")

        for key in expected:
            try:
                func = self.get_wrapped_create_function(expected[key].pop("$ext"),rsp.text)
                logger.debug(f"Func is {func}")
            except (KeyError, TypeError, AttributeError):
                #logger.info(f"Testing func in {key}")
                pass
            else:
                func_data=func()
                logger.debug(f"Ret from func: {pformat(func_data)}")

    def get_wrapped_create_function(self,ext,data):

        logger.debug(f"ext={ext}")
        args = ext.get("extra_args") or ()
        kwargs = ext.get("extra_kwargs") or {}
        kwargs.update({ 'response_text': data})

        try:
            class_name, funcname = ext["function"].split(".")
        except ValueError as e:
            msg = f"Expected entrypoint in the form class.function: {e}"
            logger.exception(msg)

        try:
            func = self.extensions.call_method(funcname)
        except AttributeError as e:
            msg = f"No function named {funcname} in {class_name} \n {e}"
            logger.exception(msg)

        #func = import_ext_function(ext["function"])
        logger.debug(f"Adding function {func} with args:{args} and kwargs:{kwargs}")
        @functools.wraps(func)
        def inner():
            return func(*args, **kwargs)

        inner.func = func

        return inner

