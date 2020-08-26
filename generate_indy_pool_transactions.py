import logging
from indy_network import NetworkSetup

from indy_common.config_util import getConfig
from indy_common.config_helper import ConfigHelper, NodeConfigHelper
from indy_common.txn_util import getTxnOrderedFields

portsStart = 9700
nodeParamsFileName = 'indy.env'


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.disabled = True
    NetworkSetup.bootstrapNodes(getConfig(), portsStart, nodeParamsFileName,
                                getTxnOrderedFields(), ConfigHelper, NodeConfigHelper)
