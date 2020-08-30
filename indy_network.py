import argparse
import ipaddress
import os
from collections import namedtuple

from stp_core.crypto.nacl_wrappers import Signer

from plenum.common.config_helper import PConfigHelper, PNodeConfigHelper
from plenum.common.util import is_hostname_valid
from plenum.common.signer_did import DidSigner
from stp_core.common.util import adict


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


NodeDef = namedtuple('NodeDef', ['name', 'ip', 'port', 'client_port', 'idx',
                        'sigseed', 'verkey', 'steward_nym'])