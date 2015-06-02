from pymongo import MongoClient
import datetime

def prune_extents(collection):
    to_remove = []
    extents = collection.find()
    now = datetime.datetime.utcnow()

    for extent in extents:
        expires = now
        try:
            expires = extent["lifetimes"][0]["end"]
            expires = datetime.datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
        except Exception as exp:
            print "Removing {0} - Extent has no lifetimes".format(extent["_id"])
            to_remove.append(extent["_id"])
        
        if expires < now:
            to_remove.append(extent["_id"])
            print "Removing {0}".format(extent["_id"])
    
    remove_cmd = {"_id": {"$in": to_remove}}
    collection.remove(remove_cmd)

def prune_exnodes(collection, extent_collection):
    to_remove = []
    exnodes = collection.find({"mode": "file"})
    exnodes = list(exnodes)

    for exnode in exnodes:
        extents = list(extent_collection.find({"parent": exnode["id"]}))
        print "%s: %s extents" % (exnode["id"], len(extents))
        if len(extents) == 0:
            to_remove.append(exnode["id"])
            print "Removing Exnode {0}".format(exnode["id"])
        
    remove_cmd = {"id": {"$in": to_remove}}
    collection.remove(remove_cmd)

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
    
    prune_extents(extents)
    prune_exnodes(exnodes, extents)
    prune_directories(exnodes)

if __name__ == "__main__":
    main()
