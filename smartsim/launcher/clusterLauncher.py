
import os
import time
from rediscluster import RedisCluster
from rediscluster.exceptions import ClusterDownError

from .shell import execute_cmd
from ..error import ClusterLauncherError

from .launcherUtil import get_ip_from_host
from ..utils import get_logger, get_env
logger = get_logger(__name__)

def create_cluster(nodes, ports):
    """Create a KeyDB cluster on the specifed nodes at port. This method
        is called using the KeyDB-cli tool and is called after all of the
        database nodes have been launched.

        :param nodes: the nodes the database instances were launched on
        :type nodes: list of strings
        :param ports: ports the database nodes were launched on
        :type ports: list of ints
        :raises: SmartSimError if cluster creation fails
    """
    cluster_str = ""
    for node in nodes:
        node_ip = get_ip_from_host(node)
        for port in ports:
            full_ip = ":".join((node_ip, str(port) + " "))
            cluster_str += full_ip

    # call cluster command
    smartsimhome = get_env("SMARTSIMHOME")
    keydb_cli = os.path.join(smartsimhome, "third-party/KeyDB/src/keydb-cli")
    cmd = " ".join((keydb_cli, "--cluster create",
                    cluster_str, "--cluster-replicas", "0"))
    returncode, out, err = execute_cmd([cmd], proc_input="yes", shell=True)

    if returncode != 0:
        logger.error(err)
        raise ClusterLauncherError("KeyDB '--cluster create' command failed")
    else:
        logger.debug(out)
        logger.info("KeyDB Cluster has been created with %s nodes" % str(len(nodes)))


def check_cluster_status(nodes, ports):
    """Check that the cluster has been launched successfully using
       the redis library. Attempt a number of trials before issuing
       an error.

    :param nodes: hostnames the cluster was launched on
    :type nodes: list of str
    :param ports: ports of each database per node
    :type ports: list of ints
    :raises ClusterLauncherError: if cluster check fails
    """
    node_list = []
    for node in nodes:
        for port in ports:
            node_dict = dict()
            node_dict["host"] = node
            node_dict["port"] = port
            node_list.append(node_dict)

    trials = 10
    while trials > 0:
        try:
            redis_tester = RedisCluster(startup_nodes=node_list)
            redis_tester.set("__test__", "__test__")
            redis_tester.delete("__test__")
            break
        except ClusterDownError:
            logger.debug("Caught a cluster down error")
            time.sleep(5)
            trials -= 1
    if trials == 0:
        raise ClusterLauncherError("Cluster setup could not be verified")