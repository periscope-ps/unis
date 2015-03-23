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
            print extent
            to_remove.append(extent["_id"])
            print "Removing {0}".format(extent["_id"])
    
    remove_cmd = {"_id": {"$in": to_remove}}
    collection.remove(remove_cmd)

def prune_exnodes(collection, extent_collection):
    to_remove = []
    exnodes = collection.find({"mode": "file"})
    
    for exnode in exnodes:
        if "extents" not in exnode or len(exnode["extents"]) == 0:
            to_remove.append(exnode["_id"])
            print "Removing Exnode {0}".format(exnode["_id"])
        
    remove_cmd = {"_id": {"$in": to_remove}}
    collection.remove(remove_cmd)

def main():
    client = MongoClient()
    db = client["unis_db"]
    exnodes = db.exnodes
    extents = db.extents
    
    prune_extents(extents)
    prune_exnodes(exnodes, extents)

if __name__ == "__main__":
    main()
