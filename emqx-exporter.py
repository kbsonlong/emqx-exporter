# -*- coding: utf-8 -*-
# @Time    : 2019-11-11 11:34
# @Author  : kbsonlong
# @Email   : kbsonlong@gmail.com
# @Blog    : www.alongparty.cn
# @File    : push01.py
# @Software: PyCharm
# @Readme  : emqx指标采集

import requests
import argparse
import socket
import prometheus_client
from prometheus_client.core import CollectorRegistry
from prometheus_client import Gauge
from flask import Response, Flask



class Emq_Api(object):
    def __init__(self,url,username,password):
        self.__url = url
        self.__username = username
        self.__password = password
        self.session = requests.Session()


    def get_info(self,info):
        response = self.session.get(self.__url + "/api/v3/{}".format(info), auth=(self.__username, self.__password))
        return response.json()["data"]


    def aggre_group(self):
        stats = self.get_info('stats')
        metrics = self.get_info('metrics')
        nodes = []
        for stat in stats:
            for metric in metrics:
                if stat["node"] == metric["node"]:
                    node = self.get_info("nodes/{}".format(stat["node"]))
                    if node["node_status"] == "Running":
                        node_status = 0
                    else:
                        node_status = 1
                    new_nodes = {
                        "connections": node["connections"],
                        "load1": float(node["load1"]),
                        "load15": float(node["load5"]),
                        "load5": float(node["load15"]),
                        "max_fds": node["max_fds"],
                        "memory_total": node["memory_total"],
                        "memory_used": node["memory_used"],
                        "node_status": int(node_status),
                        "process_available": node["process_available"],
                        "process_used": node["process_used"]
                    }
                    new_metrics = metric['metrics']
                    new_metrics.update(stat)
                    new_metrics.update(new_nodes)
                    nodes.append(new_metrics)
        return nodes

app = Flask(__name__)

@app.route("/metrics")
def collection_metrics():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    metrics = emq.aggre_group()
    for item in metrics:
        names = locals()
        for k,v in item.items():
            name = k.replace('/', '_')
            if  not names.get(name):
                names[name] = Gauge(name, 'node', ['name', 'instance','hostname','job'], registry=REGISTRY)
            else:
                names[name] = names.get(name)
            if k != "node":
                names[name].labels(name=name, instance=item["node"],hostname=hostname,job="{}:{}".format(ip,args.port)).inc(v)
    return Response(prometheus_client.generate_latest(REGISTRY),
                    mimetype="text/plain")



@app.route('/')
def index():

    return '''<h1> EMQX exporter</h1>
    <a href="/metrics" class="sidebar-toggle" data-toggle="push-menu" role="button">/metrics</a>'''

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EMQX exporter")
    parser.add_argument('--verbose', '-v', action='store_true', help='verbose mode')
    parser.add_argument('--config', '-c', default="config.yaml" , help="配置文件")
    parser.add_argument('--host', default="127.0.0.1",  help="服务监听地址")
    parser.add_argument('--port', '-p', default=5001,  help="服务监听端口")
    parser.add_argument('--debug', '-d', default=False,  help="开启debug模式,默认关闭")
    parser.add_argument('--model', '-m', default="dashboard",  help="""两种认证模式:
    dashboard \n
        --appid  用户名，默认为admin \n
        --app_secret 用户密码,默认为public; \n
    management \n
        --appid  APPID  必填 \n
        --app_secret APP秘钥 必填 \n
    默认为dashboard"""
                        )
    parser.add_argument('--emqx_url', default="http://127.0.0.1:18083",  help="""默认为http://127.0.0.1:18083""")
    if parser.parse_args().model == "management":
        parser.add_argument('--appid', required=True, help="AppID,默认admin")
        parser.add_argument('--app_secret', required=True, help="App秘钥,默认public")
    elif parser.parse_args().model == "dashboard":
        parser.add_argument('--appid', default="admin", help="AppID,默认admin")
        parser.add_argument('--app_secret', default="public", help="App秘钥,默认public")

    args = parser.parse_args()
    emq = Emq_Api(args.emqx_url, args.appid, args.app_secret)

    REGISTRY = CollectorRegistry(auto_describe=False)
    app.run(host=args.host,debug=args.debug,port=args.port)