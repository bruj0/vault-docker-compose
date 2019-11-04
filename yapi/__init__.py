
from args import ArgParser
import logging
from logging import getLogger
from logging.config import dictConfig
import sys, os, getopt
from pprint import pprint

def get_config():
    args, remaining = ArgParser().parse_known_args()
    vargs = vars(args)
    return {
        'log_file': vargs.pop("log_to_file"),
        'in_file' : vargs.pop("in_file"),
        'global_cfg' : vargs.pop("global_cfg", {}),
        'debug': vargs.pop("debug")
    }

__version__ = "0.1"
cfg = get_config()

if "debug" in cfg:
    log_level = "DEBUG"
else:
    log_level = "INFO"

# Basic logging config that will print out useful information
log_cfg = {
    "version": 1,
    'disable_existing_loggers': False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] (%(name)s:%(lineno)d): %(message)s",
            "style": "%",
        }
    },
    "handlers": {
        "to_stdout": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "nothing": {"class": "logging.NullHandler"},
    },
    "loggers": {
        "yapi": {"handlers": ["to_stdout"], "level": log_level},
        "__main__": {"handlers": ["to_stdout"], "level": log_level},
        #"": {"handlers": ["to_stdout"], "level": log_level}
    }#,
    #'root': {"handlers": ["to_stdout"], "level": log_level}
}

if "log_to_file" in cfg:
    log_cfg["handlers"].update(
        {
            "to_file": {
                "class": "logging.FileHandler",
                "filename": cfg["log_file"],
                "formatter": "default",
            }
        }
    )
    log_cfg["loggers"]["yapi"]["handlers"].append("to_file")
else:
    log_cfg["loggers"]["yapi"]["handlers"].append("to_stdout")


dictConfig(log_cfg)
