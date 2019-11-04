import argparse
from argparse import ArgumentParser
from textwrap import dedent



class ArgParser(ArgumentParser):
    def __init__(self):
        description = """Parse yaml + make requests against an API"""

        super(ArgParser, self).__init__(
            description=dedent(description),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        self.add_argument("in_file", help="Input file with yaml in")

        self.add_argument(
            "--log-to-file",
            help="Log output to a file (yapi.log if no argument is given)",
            nargs="?",
            const="yapi.log",
        )

        self.add_argument(
            "--stdout", help="Log output stdout", action="store_true", default=False
        )

        self.add_argument(
            "--debug",
            help="Log debug information (only relevant if --stdout or --log-to-file is passed)",
            action="store_true",
            default=False,
        )

