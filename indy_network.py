


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
