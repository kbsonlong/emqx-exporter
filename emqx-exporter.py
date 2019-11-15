#!/usr/bin/python

import time
import requests
import argparse
import socket
import os
from sys import exit
from pprint import pprint
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY


hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)
DEBUG = int(os.environ.get('DEBUG', '0'))
COLLECTION_TIME = Summary('emqx_collector_collect_seconds', 'Time spent to collect metrics from Emqx')

class MqttCollector(object):
    # The build statuses we want to export about.
    statuses = [  'node_status','process_available','process_used','max_fds','connections','load1','load5','load15',
                'subscriptions/shared/max', 'subscriptions/max', 'subscribers/max', 'resources/max',
                'topics/count', 'subscriptions/count', 'suboptions/max', 'topics/max', 'sessions/persistent/max',
                'connections/max', 'subscriptions/shared/count', 'sessions/persistent/count', 'actions/count',
                'retained/count', 'rules/count', 'routes/count', 'suboptions/count', 'sessions/count',
                'actions/max', 'retained/max', 'sessions/max', 'rules/max', 'routes/max', 'resources/count',
                'subscribers/count', 'connections/count', 'packets/pubcomp/received', 'packets/unsuback',
                'packets/pingreq', 'packets/disconnect/received', 'messages/qos0/received', 'packets/pubrel/missed',
                'packets/puback/missed', 'messages/qos2/dropped', 'packets/subscribe', 'packets/pubrel/sent',
                'packets/auth', 'packets/unsubscribe', 'messages/forward', 'packets/received', 'packets/disconnect/sent',
                'bytes/received', 'messages/qos2/received', 'packets/puback/sent', 'messages/dropped', 'packets/connect',
                'packets/suback', 'bytes/sent', 'messages/qos2/expired', 'packets/puback/received', 'messages/qos2/sent',
                'packets/pubrel/received', 'messages/expired', 'packets/pingresp', 'messages/qos1/sent',
                'packets/pubcomp/missed', 'messages/qos1/received', 'packets/pubrec/sent', 'packets/connack',
                'packets/pubrec/missed', 'packets/publish/received', 'packets/publish/sent', 'packets/sent',
                'messages/sent', 'messages/received', 'messages/retained', 'packets/pubcomp/sent',
                'messages/qos0/sent', 'packets/pubrec/received'
                ]

    def __init__(self, target, user, password):
        self._target = target.rstrip("/")
        self._user = user
        self._password = password
        self.session = requests.Session()

    def collect(self):

        # Request data from Jenkins
        nodes = self._request_data("nodes")

        self._setup_empty_prometheus_metrics()
        for node in nodes.keys():
            if DEBUG:
                print("Found Job: {}".format(node))
                pprint(nodes[node])
            self._get_metrics(node, nodes[node])

        for status in self.statuses:
            for metric in self._prometheus_metrics[status].values():
                yield metric


    def _request_data(self,info):
        # Request exactly the information we need from Jenkins
        url = '{}/api/v3/{}'.format(self._target,info)

        def get_info(myurl):
            try:
                response = self.session.get(myurl, auth=(self._user, self._password), timeout=10)
            except  :
                raise Exception("Call to url %s failed with status: %s" % (myurl, 500))
            if DEBUG:
                pprint(response.text)
            if response.status_code != requests.codes.ok:
                raise Exception("Call to url %s failed with status: %s" % (myurl, response.status_code))
            result = response.json()
            if DEBUG:
                pprint(result)
            return result


        def parsenodes(node_url):
            # params = tree: jobs[name,lastBuild[number,timestamp,duration,actions[queuingDurationMillis...

            result = get_info(node_url)
            nodes = {}
            for node in result['data']:
                stat_url = "{}/api/v3/nodes/{}/stats".format(self._target,node["node"])
                metric_url = "{}/api/v3/nodes/{}/metrics".format(self._target,node["node"])
                node_stats = get_info(stat_url)["data"]
                node_metrics = get_info(metric_url)["data"]
                node.update(node_stats)
                node.update(node_metrics)
                nodes[node["node"]]=node
            if DEBUG:
                print(nodes)
            return nodes


        return parsenodes(url)

    def _setup_empty_prometheus_metrics(self):
        # The metrics we want to export.
        self._prometheus_metrics = {}
        for status in self.statuses:
            snake_case = status.replace("/","_").lower()
            self._prometheus_metrics[status] = {
                'number':
                    GaugeMetricFamily('emq_{0}'.format(snake_case),
                                      'EMQX Cluster Metric for  {0}'.format(status), labels=["cluster_node","instance","hostname"]),
            }

    def _get_metrics(self, name, job):
        for status in self.statuses:
            if status in job.keys():
                status_data = job[status] or 0
                if status == "node_status" and status_data == "Running":
                    self._prometheus_metrics[status]["number"].add_metric([name,ip,hostname], 0)
                elif  status == "node_status":
                    self._prometheus_metrics[status]["number"].add_metric([name,ip,hostname], 1)
                else:
                    self._prometheus_metrics[status]["number"].add_metric([name,ip,hostname],status_data)




def parse_args():
    parser = argparse.ArgumentParser(
        description='emqx exporter args emqx address and port'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='verbose mode')
    parser.add_argument(
         '--emqx_url',
        metavar='emqx',
        required=False,
        help='EMQX集群服务地址，默认为http://127.0.0.1:18083',
        default=os.environ.get('EMQX_URL', 'http://127.0.0.1:18083')
    )
    parser.add_argument(
        '--model', '-m', default="dashboard",
        help="""两种认证模式:
dashboard
--appid  用户名，默认为admin \n
--app_secret 用户密码,默认为public; \n
management \n
--appid  APPID  必填 \n
--app_secret APP秘钥 必填 \n
默认为dashboard"""
    )
    parser.add_argument(
        '-p', '--port',
        metavar='port',
        required=False,
        type=int,
        help='Listen to this port',
        default=int(os.environ.get('PORT', '9118'))
    )
    parser.add_argument(
        '-i', '--host',
        dest='host',
        required=False,
        help='Listen to this addr',
        default="127.0.0.1"
    )
    if parser.parse_args().model == "management":
        parser.add_argument(
            '--appid',
            metavar='appid',
            required=True,
            help='Emqx集群appid,可以通过设置环境变量APPID',
            default=os.environ.get('APPID')
        )
        parser.add_argument(
            '--app_secret',
            metavar='app_secret',
            required=True,
            help='EMQX集群秘钥,可以通过设置环境变量APP_SECRET',
            default=os.environ.get('APP_SECRET')
        )
    elif parser.parse_args().model == "dashboard":
        parser.add_argument(
            '--appid',
            metavar='appid',
            required=False,
            help='Emqx集群appid,默认为admin',
            default=os.environ.get('APPID','admin')
        )
        parser.add_argument(
            '--app_secret',
            metavar='app_secret',
            required=False,
            help='EMQX集群秘钥,默认为public',
            default=os.environ.get('APP_SECRET','public')
        )

    return parser.parse_args()


def main():
    try:
        args = parse_args()
        port = int(args.port)
        REGISTRY.register(MqttCollector(args.emqx_url, args.appid, args.app_secret))
        start_http_server(port)
        print("Polling {}. Serving at {}:{}".format(args.emqx_url, args.host,port))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" Interrupted")
        exit(0)


if __name__ == "__main__":
    main()