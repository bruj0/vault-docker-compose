
import logging
import os.path
import yaml

logger = logging.getLogger(__name__)


class yaml_loader():
    def load(self,filename):
        """
        Load a yaml file and expect only one document

        Args:
            filename (str): path to document

        Returns:
            dict: content of file
        """

        with open(filename, "r") as fileobj:
            try:
                contents = yaml.load(fileobj, Loader=yaml.BaseLoader)
            except yaml.composer.ComposerError as e:
                logger.exception(e)

        return contents