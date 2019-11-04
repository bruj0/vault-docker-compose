#!/usr/bin/env python

from yapi.request import request as RestRequest
from yapi.loader import yaml_loader as YamlLoader
from box import Box
import logging
from logging import getLogger

import sys, os, getopt
from pprint import pprint
from . import cfg
from . import __version__


logger = getLogger(__name__)

logger.info(f"Starting  {__version__}")

def main():
    yl = YamlLoader()
    variables = {
        'env_vars': dict(os.environ)
    }
    data = yl.load(cfg['in_file'])
    logger.info(f"Run with file {cfg['in_file']}")


    #logger.debug(pprint(data))

    for stage in data['stages']:
        rr = RestRequest(stage['request'],variables)
        rr.send()

if __name__== "__main__":
  main()