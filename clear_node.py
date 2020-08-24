import shutil
import argparse
from indy_common.config_helper import ConfigHelper
from indy_common.config_util import getConfig



def clean(config, full, network_name):
    if network_name:
        config.NETWORK_NAME = network_name
    config_helper = ConfigHelper(config)

    shutil.rmtree(config_helper.log_dir)
    shutil.rmtree(config_helper.keys_dir)
    shutil.rmtree(config_helper.genesis_dir)

    if full:
        shutil.rmtree(config_helper.ledger_base_dir)
        shutil.rmtree(config_helper.log_base_dir)
