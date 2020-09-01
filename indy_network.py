import argparse
import ipaddress
import os
from collections import namedtuple
import fileinput

from common.exceptions import PlenumValueError

from ledger.genesis_txn.genesis_txn_file_util import create_genesis_txn_init_ledger

from stp_core.crypto.nacl_wrappers import Signer

from plenum.common.member.member import Member
from plenum.common.member.steward import Steward

from plenum.common.keygen_utils import initNodeKeysForBothStacks, init_bls_keys
from plenum.common.constants import TRUSTEE, STEWARD
from plenum.common.config_helper import PConfigHelper, PNodeConfigHelper
from plenum.common.util import hexToFriendly, is_hostname_valid
from plenum.common.signer_did import DidSigner
from stp_core.common.util import adict

CLIENT_CONNECTIONS_LIMIT = 500


class NetworkSetup:

    @staticmethod
    def _bootstrap_args_type_node_count(nodesStrArg):
        if not nodesStrArg.isdigit():
            raise argparse.ArgumentTypeError('should be a number')
        n = int(nodesStrArg)

        if n > 100:
            raise argparse.ArgumentTypeError(
                "Cannot run {} nodes for this setup"
                "For this setup, we need node number less than 100"
                "This is not a problem with protocol but some placeholder".format(n)
                )
        if n <= 0:
            raise argparse.ArgumentTypeError("Should be > 0")

        return n

    @staticmethod
    def _bootstrap_args_type_ips_hosts(ips_hosts_str_arg):
        ips = []
        for arg in ips_hosts_str_arg.split(','):
            arg = arg.strip()
            try:
                ipaddress.ip_address(arg)
            except ValueError:
                if not is_hostname_valid(arg):
                    raise argparse.ArgumentTypeError(
                    "'{}' is not a valid IP or hostname".format(arg)
                )
                else:
                    ips.append(arg)
            else:
                ips.append(arg)

        return ips

    @staticmethod
    def _bootstrap_args_type_steward_seeds(steward_seeds_str_arg):
        steward_seeds = []
        i = 1
        for arg in steward_seeds_str_arg.split(','):
            arg = str(arg)
            arg = arg.strip()
            if len(arg) != 32:
                raise argparse.ArgumentTypeError("The lenght of Steward seed {} should be 32 digit long".format(i))
            steward_seeds.append(arg)
            i += 1

        return steward_seeds

    @staticmethod
    def _bootstrap_args_type_node_seeds(node_seeds_str_arg):
        node_seeds = []
        i = 1
        for arg in node_seeds_str_arg.split(','):
            arg = str(arg)
            arg = arg.strip()
            if len(arg) != 32:
                raise argparse.ArgumentTypeError("The lenght of Node seed {} should be 32 digit long".format(i))
            node_seeds.append(arg)
            i += 1

        return node_seeds


    @staticmethod
    def _bootstrap_args_type_trustee_seeds(trustee_seeds_str_arg):
        trustee_seeds = []
        i = 1
        for arg in trustee_seeds_str_arg.split(','):
            arg = str(arg)
            arg = arg.strip()
            if len(arg) != 32:
                raise argparse.ArgumentTypeError("The length of Trustee seed {} should be 32 digit long".format(i))
            trustee_seeds.append(arg)
            i +=1

        return trustee_seeds

    @classmethod
    def gen_defs(cls, ips, steward_seeds, node_seeds, node_count, starting_port):

        if not ips:
            ips = ['127.0.0.1'] * node_count
        else:
            if len(ips) != node_count:
                if len(ips) > node_count:
                    ips = ips[:node_count]
                else:
                    ips += ['127.0.0.1'] * (node_count - len(ips))

        if ( steward_seeds == None ):
            steward_seeds = []
            for i in range(1, node_count+1):
                    seed = "Steward" + str(i)
                    seed=('0'*(32 - len(seed)) + seed) 
                    steward_seeds.append(seed)
        
        elif len(steward_seeds) != node_count:
            if len(steward_seeds) > node_count:
                steward_seeds = steward_seeds[:node_count]
            else:
                current_steward_seeds_list_length = len(steward_seeds)
                for i in range(current_steward_seeds_list_length+1, node_count+1):
                    seed = "Steward" + str(i)
                    seed=('0'*(32 - len(seed)) + seed) 
                    steward_seeds.append(seed) 

        if ( node_seeds == None):
            node_seeds = []
            for i in range(1, node_count+1):
                seed = "Node" + str(i) 
                seed=('0'*(32 - len(seed)) + seed)
                node_seeds.append(seed)

        elif len(node_seeds) != node_count:
            if len(node_seeds) > node_count:
                node_seeds = node_seeds[:node_count] 
            else:
                current_node_seeds_list_length = len(node_seeds)
                for i in range(current_node_seeds_list_length+1, node_count+1):
                    seed = "Node" + str(i) 
                    seed=('0'*(32-len(seed)) + seed)
                    node_seeds.append(seed)         
        

        steward_defs = []
        node_defs = []
        for i in range(1, node_count + 1):
            d = adict()
            d.name = "Steward" + str(i)
            d.sigseed = cls.get_signing_seed(steward_seeds[i-1])
            s_signer = DidSigner(seed=d.sigseed)
            d.nym = s_signer.identifier
            d.verkey = s_signer.verkey
            steward_defs.append(d)

            name = "Node" + str(i)
            sigseed = cls.get_signing_seed(node_seeds[i-1])
            node_defs.append(NodeDef(
                name=name,
                ip=ips[i-1],
                port=starting_port + (i*2) - 1,
                client_port=starting_port + (i*2),
                idx=i,
                sigseed=sigseed,
                verkey=Signer(sigseed).verhex,
                steward_nym=d.nym))
        return steward_defs, node_defs    


    @staticmethod
    def get_signing_seed(name: str) -> bytes:
        return ('0'*(32 - len(name)) + name).encode()   


    @classmethod
    def gen_client_defs(cls, client_count):
        return [cls.gen_client_def(idx) for idx in range(1, client_count+1)]

    @classmethod
    def gen_client_def(cls, idx):
        d = adict()
        d.name = "Client" + str(idx)
        d.sigseed = cls.get_signing_seed(d.name)
        c_signer = DidSigner(seed=d.sigseed)
        d.nym = c_signer.identifier
        d.verkey = c_signer.verkey
        return d

    @classmethod 
    def gen_trustee_def(cls, trustee_seeds):

        if ( trustee_seeds == None ):
            trustee_seeds = []
            seed = "Trustee1" 
            seed=('0'*(32 - len(seed)) + seed)
            trustee_seeds.append(seed)

        trustee_defs = []
        for i in range(1, len(trustee_seeds)+1):
            d = adict()
            d.name = "Trustee" + str(i)
            d.sigseed = cls.get_signing_seed(trustee_seeds[i-1])
            t_signer = DidSigner(seed=d.sigseed)
            d.nym = t_signer.identifier
            d.verkey = t_signer.verkey
            trustee_defs.append(d)

        return trustee_defs 
        

    @classmethod 
    def init_pool_ledger(cls, appendToLedgers, genesis_dir, config):
        pool_txn_file = cls.pool_ledger_file_name(config)
        pool_ledger = create_genesis_txn_init_ledger(genesis_dir, pool_txn_file)
        if not appendToLedgers:
            pool_ledger.reset()
        return pool_ledger

    @classmethod
    def init_domain_ledger(cls, appendToLedgers, genesis_dir, config, domainTxnFieldOrder):
        domain_txn_file = cls.domain_ledger_file_name(config)
        domain_ledger = create_genesis_txn_init_ledger(genesis_dir, domain_txn_file)
        if not appendToLedgers:
            domain_ledger.reset()
        return domain_ledger



    @classmethod
    def pool_ledger_file_name(cls, config):
        return config.poolTransactionsFile

    @classmethod
    def domain_ledger_file_name(cls, config):
        return config.domainTransactionsFile

    @staticmethod
    def write_node_params_file(filePath, name, nIp, nPort, cIp, cPort):
        contents = [
            'NODE_NAME={}'.format(name),
            'NODE_IP={}'.format(nIp),
            'NODE_PORT={}'.format(nPort),
            'NODE_CLIENT_IP={}'.format(cIp),
            'NODE_CLIENT_PORT={}'.format(cPort),
            'CLIENT_CONNECTIONS_LIMIT={}'.format(CLIENT_CONNECTIONS_LIMIT)
        ]
        with open(filePath, 'w') as f:
            f.writelines(os.linesep.join(contents))

    
    @staticmethod
    def get_nym_from_verkey(verkey: bytes):
        return hexToFriendly(verkey)


    @classmethod
    def bootstrapNodes(cls, config, startingPort, nodeParamsFileName, domainTxnFieldOrder,
                           config_helper_class=PConfigHelper, node_config_helper_class=PNodeConfigHelper,
                           chroot: str=None):
        parser = argparse.ArgumentParser(description="Generate pool transactions")
        parser.add_argument('--nodes', required=True,
                            help='for this setup, node count should be less than 100',
                            type=cls._bootstrap_args_type_node_count)
        parser.add_argument('--clients', required=True, type=int,
                            help='client count')
        parser.add_argument('--nodeNum', type=int, nargs='+',
                            help='the number of the node that will '
                                 'run on this machine')
        parser.add_argument('--ips',
                            help='IPs/hostnames of the nodes, provide comma '
                                  'separated IPs, if no of IPS provided are less than number of nodes then the remaining'
                                  'nodes are assigned the loopback IP, '
                                  'i.e 127.0.0.1',
                            type=cls._bootstrap_args_type_ips_hosts)
        parser.add_argument('--stewardSeeds',
                            help='Stewards Seeds, provide comma separated seeds',
                            type=cls._bootstrap_args_type_steward_seeds)
        parser.add_argument('--nodeSeeds',
                            help='Node Seeds, provide comma separated seeds',
                            type=cls._bootstrap_args_type_node_seeds)
        parser.add_argument('--trusteeSeeds',
                            help='Trustee Seeds, provide comma separated seeds',
                            type=cls._bootstrap_args_type_trustee_seeds)
        parser.add_argument('--network',
                            help='Network name (default sandbox)',
                            type=str,
                            default="sandbox",
                            required=False)
        parser.add_argument(
            '--appendToLedgers',
            help="Determine if ledger files needs to be erased "
            "before writing new information or not.",
            action='store_true')

        args = parser.parse_args()


        if isinstance(args.nodeNum, int):
            if not (1 <= args.nodeNum <= args.nodes):
                raise PlenumValueError(
                    'args.nodeNum', args.nodeNum,
                    ">= 1 && <= args.nodes {}".format(args.nodes)
                )
        elif isinstance(args.nodeNum, list):
            if any([True for x in args.nodeNum if not ( 1 <= x <= args.nodes)]):
                raise PlenumValueError(
                    'some items in nodeNum list', args.nodeNum,
                    ">=1 && <= args.nodes {}".format(args.nodes)  
            )  

        node_num = [args.nodeNum, None] if args.nodeNum else [None]

        steward_defs, node_defs = cls.gen_defs(args.ips, args.stewardSeeds, args.nodeSeeds, args.nodes, startingPort)

        client_defs = cls.gen_client_defs(args.clients)

        trustee_def = cls.gen_trustee_def(args.trusteeSeeds)


        if args.nodeNum:

            for line in fileinput.input(['/etc/indy/indy_config.py'], inplace=True):
                if 'NETWORK_NAME' not in line:
                    print(line, end="")
            with open('/etc/indy/indy_config.py', 'a') as cfgfile:
                cfgfile.write("NETWORK_NAME = '{}'".format(args.network))

        for n_num in node_num:
            cls.bootstrap_nodes_core(config, args.network, args.appendToLedgers, domainTxnFieldOrder, trustee_def,
                                       steward_defs, node_defs, client_defs, n_num, nodeParamsFileName,
                                       config_helper_class, node_config_helper_class)


    @classmethod 
    def bootstrap_nodes_core(
            cls,
            config,
            network,
            appendToLedgers,
            domainTxnFieldOrder,
            trustee_def,
            steward_defs,
            node_defs,
            client_defs,
            localNodes,
            nodeParamsFileName,
            config_helper_class=PConfigHelper,
            node_config_helper_class=PNodeConfigHelper,
            chroot: str=None):
        
        if not localNodes:
            localNodes = {}

        try:
            if isinstance(localNodes, int):
                _localNodes = {localNodes}
            else:
                _localNodes = {int(_) for _ in localNodes}
        except BaseException as exc:
            raise RuntimeError('nodeNum must be an int or set of ints') from exc

        config.NETWORK_NAME = network

        config_helper = config_helper_class(config, chroot=chroot)
        os.makedirs(config_helper.genesis_dir, exist_ok=True)
        genesis_dir = config_helper.genesis_dir
        keys_dir = config_helper.keys_dir

        poolLedger = cls.init_pool_ledger(appendToLedgers, genesis_dir, config)
        domainLedger = cls.init_domain_ledger(appendToLedgers, genesis_dir,
                                              config, domainTxnFieldOrder)

        genesis_protocol_version = None

        seq_no = 1
        
        for td in trustee_def:
            trustee_txn = Member.nym_txn(td.nym, verkey=td.verkey,
                                        role=TRUSTEE, seq_no=seq_no,
                                        protocol_version=genesis_protocol_version)
            
            seq_no += 1
            domainLedger.add(trustee_txn)

        for sd in steward_defs:
            nym_txn = Member.nym_txn(sd.nym, verkey=sd.verkey, role=STEWARD, 
                                    creator= trustee_def[0].nym, seq_no=seq_no,
                                    protocol_version=genesis_protocol_version)
            seq_no += 1
            domainLedger.add(nym_txn)


        for cd in client_defs:
            txn = Member.nym_txn(cd.nym, verkey=cd.verkey, creator=trustee_def[0].nym,
                                 seq_no=seq_no,
                                 protocol_version=genesis_protocol_version)
            seq_no += 1
            domainLedger.add(txn)

        seq_no = 1
        for nd in node_defs:
            if nd.idx in _localNodes:
                _, verkey, blskey, key_proof = initNodeKeysForBothStacks(nd.name, keys_dir, 
                                                                        nd.sigseed, override=True)
                verkey = verkey.encode()
                assert verkey == nd.verkey

                if nd.ip != '127.0.0.1':
                    paramsFilePath = os.path.join(config.GENERAL_CONFIG_DIR, nodeParamsFileName)
                    print('Nodes will not run locally, so writing {}'.format(paramsFilePath))
                    NetworkSetup.write_node_params_file(paramsFilePath, nd.name,
                                                    "0.0.0.0", nd.port,
                                                    "0.0.0.0", nd.client_port)
                
                print("This node with name {} will use ports {} and {} for nodestack and clientstack respectavely"
                      .format(nd.name, nd.port, nd.client_port))

            else:
                verkey = nd.verkey
                blskey, key_proof = init_bls_keys(keys_dir, nd.name, nd.sigseed)
            node_nym = cls.get_nym_from_verkey(verkey)

            node_txn = Steward.node_txn(nd.steward_nym, nd.name, node_nym,
                                        nd.ip, nd.port, nd.client_port, blskey=blskey,
                                        bls_key_proof=key_proof,
                                        seq_no=seq_no,
                                        protocol_version=genesis_protocol_version)
            
            seq_no +=1
            poolLedger.add(node_txn)
        
        poolLedger.stop()
        domainLedger.stop()





NodeDef = namedtuple('NodeDef', ['name', 'ip', 'port', 'client_port', 'idx',
                        'sigseed', 'verkey', 'steward_nym'])