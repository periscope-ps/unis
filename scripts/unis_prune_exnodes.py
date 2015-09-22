from pymongo import MongoClient
import datetime

def prune_extents(removed, collection):
    for exnode in removed:
        collection.remove({"parent": exnode})
    
def prune_exnodes(collection):
    removed = []

    for exnode in collection.find({"mode": "file"}):
        do_remove = True
        for extent in exnode["extents"]:
            try:
                if datetime.datetime.strptime(extent["lifetimes"][0]["end"], "%Y-%m-%d %H:%M:%S") >= datetime.datetime.utcnow():
                    do_remove = False
                    break

            except Exception as exp:
                print("Bad extent {extent}: Removing".format(extent = extent["id"]))

        if do_remove:
            print("removing: Exnode[{uid}]".format(uid = exnode["id"]))
            removed.append(exnode["id"])
            
        
    remove_cmd = {"id": {"$in": removed}}
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
    children = collection.find({ "parent": exnode["id"] })

    for child in children:
        contains_data = contains_data | search_children(child, collection)

    if not contains_data:
        collection.remove({"id": exnode["id"]})
        print "Removing Directory: {0}".format(exnode["name"])

    return contains_data
        
        
def main():
    client = MongoClient()
    db = client["unis_db"]
    exnodes = db.exnodes
    extents = db.extents
    
    removed = prune_exnodes(exnodes)
    prune_extents(removed, extents)
    prune_directories(exnodes)

if __name__ == "__main__":
    main()
