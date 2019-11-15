docker run --rm -ti --name emqx-exporter  registry.cn-hangzhou.aliyuncs.com/seam/emqx-exporter:[version]

docker run --rm --net host -ti --name emqx-exporter -e PARAMS="--emqx_url http://192.168.17.154:18083 -i 0.0.0.0" registry.cn-hangzhou.aliyuncs.com/seam/emqx-exporter:1.0.3