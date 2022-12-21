import json
import sys
import subprocess
from arango import ArangoClient
from . import add_route

# Query DB for a path that avoids a given country and return srv6 SID
def ds_calc(src, dst, user, pw, dbname, ctr, intf):

    client = ArangoClient(hosts='http://52.11.224.254:30852')
    db = client.db(dbname, username=user, password=pw)

    aql = db.aql
    cursor = db.aql.execute("""for u in unicast_prefix_v4 filter u.prefix == """  + '"%s"' % src +  """ \
        return { id: u._id, src_peer: u.peer_ip } """)
    src_dict = [doc for doc in cursor]
    print(src_dict)

    # Get destination prefix ID to end graph traversal
    aql = db.aql
    cursor = db.aql.execute("""for u in unicast_prefix_v4 filter u.prefix == """  + '"%s"' % dst +  """ \
        return { id: u._id, dst_peer: u.peer_ip } """)
    dst_dict = [doc for doc in cursor]
    print(dst_dict)

    id = "id"
    src_peer = "src_peer"
    dst_peer = "dst_peer"

    s = src_dict[0]
    d = dst_dict[0]

    if s[src_peer] == d[dst_peer]:
        print(""" 
        Source and destination are reachable via the same router, no optimization available
        
        """)

    aql = db.aql
    cursor = db.aql.execute("""for p in outbound k_shortest_paths \
        """ + '"%s"' % s[id] + """ TO """ + '"%s"' % d[id] + """ sr_topology \
            options {uniqueVertices: "path", bfs: true} \
            filter p.edges[*].country_codes !like "%"""+'%s' % ctr +"""%" limit 1 \
                return { path: p.edges[*].remote_node_name, sid: p.edges[*].srv6_sid, \
                    countries_traversed: p.edges[*].country_codes[*], latency: sum(p.edges[*].latency), \
                        percent_util_out: avg(p.edges[*].percent_util_out)} """)

    path = [doc for doc in cursor]
    print("path: ", path)


    id = "id"
    dest_peer = "dest_peer"
    dest_id = [a_dict[id] for a_dict in dst_dict]

    s = src_dict[0]
    d = dst_dict[0]
    print("d: ", d)

    aql = db.aql
    cursor = db.aql.execute("""for p in outbound k_shortest_paths \
        """ + '"%s"' % s[id] + """ TO """ + '"%s"' % d[id] + """ sr_topology \
            options {uniqueVertices: "path", bfs: true} \
            filter p.edges[*].country_codes !like "%"""+'%s' % ctr +"""%" limit 1 \
                return { path: p.edges[*].remote_node_name, sid: p.edges[*].srv6_sid, \
                    countries_traversed: p.edges[*].country_codes[*], latency: sum(p.edges[*].latency), \
                        percent_util_out: avg(p.edges[*].percent_util_out)} """)

    path = [doc for doc in cursor]
    print("path: ", path)

    pdict = path[0]
    sids = pdict['sid']
    usid_block = 'fc00:0:'
    print("sids: ", sids)

    for sid in list(sids):
        if sid == None:
            sids.remove(sid)

    usid = []
    for s in sids:
        if s != None and usid_block in s:
            usid_list = s.split(usid_block)
            sid = usid_list[1]
            usid_int = sid.split(':')
            u = int(usid_int[0])
            usid.append(u)

    ipv6_separator = ":"

    sidlist = ""
    for word in usid:
        sidlist += str(word) + ":"

    srv6_sid = usid_block + sidlist + ipv6_separator
    print("srv6 sid: ", srv6_sid)
    #print("path: ", path)

    siddict = {}
    siddict['srv6_sid'] = srv6_sid
    path.append(siddict)

    pathdict = {
            'statusCode': 200,
            'source': src,
            'destination': dst,
            'sid': srv6_sid,
            'path': path
        }

    pathobj = json.dumps(pathdict, indent=4)
    with open('log/data_sovereignty_log.json', 'w') as f:
        sys.stdout = f 
        print(pathobj)

    route = add_route.add_linux_route(dst, srv6_sid, intf)
    print("adding linux route: ", route)