from pymongo import MongoClient
import datetime

def prune_extents(removed, collection):
    for exnode in removed["refs"]:
        collection.remove({"parent.href": exnode})
    
def prune_exnodes(collection, extcoll):
    removed = {"refs": [],
               "ids": []}
    
    for exnode in collection.find({"mode": "file"}):
        do_remove = True
        
        if "extents" not in exnode:
            exnode["extents"] = []
            extents = extcoll.find({"parent.href": exnode["selfRef"]})
            for e in extents:
                exnode["extents"].append(e)

        if not len(exnode["extents"]):
            print("Skipping exnode with no extents! [{uid} {name}]".format(uid=exnode["id"], name=exnode["name"]))
            continue
            
        for extent in exnode["extents"]:
            try:
                if datetime.datetime.strptime(extent["lifetimes"][0]["end"], "%Y-%m-%d %H:%M:%S") >= datetime.datetime.utcnow():
                    do_remove = False
                    break

            except Exception as exp:
                print("Bad extent {extent}: Removing".format(extent = extent["id"]))

        if do_remove:
            print("removing: Exnode[{uid} {name}]".format(uid=exnode["id"], name=exnode["name"]))
            removed["refs"].append(exnode["selfRef"])
            removed["ids"].append(exnode["id"])
            
        
    remove_cmd = {"id": {"$in": removed["ids"]}}
    collection.remove(remove_cmd)
    return removed

def prune_directories(collection):
    root = collection.find({"parent": None})

    for exnode in root:
        children = search_children(exnode, collection)


def search_children(exnode, collection):
    if exnode["mode"] == "file":
        return True

    contains_data = False
    children = collection.find({ "parent.href": exnode["selfRef"] })

    for child in children:
        contains_data = contains_data | search_children(child, collection)

    if not contains_data:
        collection.remove({"id": exnode["id"]})
        print "Removing Directory: {0}".format(exnode["name"])

    return contains_data
        
        
def main():
    client = MongoClient()
    db = client["exnode_db"]
    exnodes = db.exnodes
    extents = db.extents
    
    removed = prune_exnodes(exnodes, extents)
    prune_extents(removed, extents)
    prune_directories(exnodes)

if __name__ == "__main__":
    main()
