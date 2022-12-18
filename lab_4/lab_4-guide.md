### Exploring Jalapeno, Kafka, ArangoDB

#### Continue on the Jalapeno VM

Kafka:
1. List Kafka topics
2. Listen to Kafka topics
```
kubectl exec -it kafka-0 /bin/bash -n jalapeno

cd bin
unset JMX_PORT

./kafka-topics.sh --list  --bootstrap-server localhost:9092
./kafka-console-consumer.sh --bootstrap-server localhost:9092  --topic gobmp.parsed.ls_node
./kafka-console-consumer.sh --bootstrap-server localhost:9092  --topic gobmp.parsed.ls_link
./kafka-console-consumer.sh --bootstrap-server localhost:9092  --topic gobmp.parsed.l3vpn_v4

./kafka-console-consumer.sh --bootstrap-server localhost:9092  --topic jalapeno.telemetry

```

Switch to web browser and connect to Jalapeno's Arango GraphDB
```
http://198.18.1.101:30852/

user: root
password: jalapeno
DB: jalapeno

```
Explore data collections

Run DB Queries:
```
for l in ls_node return l
```
Note: after running a query comment it out before running the next query. 

Example:

<img src="arango-query.png" width="600">

More sample queries:
```
for l in ls_link return l

for l in ls_link filter l.mt_id_tlv.mt_id !=2 return l

for l in ls_link filter l.mt_id_tlv.mt_id !=2 return { key: l._key, router_id: l.router_id, igp_id: l.igp_router_id, local_ip: l.local_link_ip, remote_ip: l.remote_link_ip }

for l in ls_node_edge return l

for l in sr_topology return l

for l in sr_node return { node: l.router_id, name: l.name, prefix_sid: l.prefix_attr_tlvs.ls_prefix_sid, srv6sid: l.srv6_sid }
```

Return to the Jalapeno VM ssh session and add some synthetic meta data to the DB:
```
cd ~/SRv6_dCloud_Lab/lab_4/
python3 add_meta_data.py
```
Validate meta data with ArangoDB query:
```
for l in sr_topology return { key: l._key, from: l._from, to: l._to, latency: l.latency, utilization: l.percent_util_out, country_codes: l.country_codes }
```

Run the get_nodes.py script:
```
python3 get_nodes.py
cat nodes.json
```
Return to the ArangoDB browser UI and run some more queries:
```
for v, e in outbound shortest_path 'sr_node/2_0_0_0000.0000.0001' TO 'unicast_prefix_v4/10.107.1.0_24_10.0.0.7' sr_topology return  { name: v.name, sid: e.srv6_sid, latency: e.latency }


```