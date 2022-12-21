import json
import sys
from arango import ArangoClient

# Query DB for least utilized path parameters and return srv6 SID
def gp_calc(src, dst, user, pw, dbname):

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
    else:
        aql = db.aql
        cursor = db.aql.execute("""for v, e, p in 1..6 outbound """ + '"%s"' % s[id] + """ \
                sr_topology OPTIONS {uniqueVertices: "path", bfs: true} \
                    filter v._id == """ + '"%s"' % d[id] + """ \
                        return { path: p.edges[*].remote_node_name, sid: p.edges[*].srv6_sid, \
                            latency: sum(p.edges[*].latency), \
                                percent_util_out: avg(p.edges[*].percent_util_out)} """)

        path = [doc for doc in cursor]
        #print(path)
        for index in range(len(path)):
            for key in path[index]:
                #print(key, ":", path[index][key])
                if key == "sid":
                    #print("sid: ", path[index][key])
                    sids = path[index][key]
                    usid_block = 'fc00:0:'
                    #print("sids: ", sids)
                    for sid in list(sids):
                        if sid == None:
                            sids.remove(sid)
                    #print("sids: ", sids)
                    usid = []
                    for s in sids:
                        if s != None and usid_block in s:
                            usid_list = s.split(usid_block)
                            #print(usid_list)
                            sid = usid_list[1]
                            usid_int = sid.split(':')
                            u = int(usid_int[0])
                            usid.append(u)
                
                    ipv6_separator = ":"

                    sidlist = ""
                    for word in usid:
                        sidlist += str(word) + ":"
                    #print(sidlist)

                    srv6_sid = usid_block + sidlist + ipv6_separator
                    #print("srv6 sid: ", srv6_sid)
                    siddict = {}
                    siddict['srv6_sid'] = srv6_sid
                    path[index][key].append(siddict)

        pathdict = path
            
        pathdict = {
                'statusCode': 200,
                'source': src,
                'destination': dst,
                'sid': srv6_sid,
                'path': path
            }

        pathobj = json.dumps(pathdict, indent=4)
        with open('log/get_paths.json', 'w') as f:
            sys.stdout = f 
            print(pathobj)