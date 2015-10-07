from pymongo import MongoClient
from protocol import factory
from protocol.exceptions import AllocationException
import datetime


def remove_allocation(alloc, allocs):
    allocs.remove({ "id": alloc["id"] })
    print("removing: Allocation[{uid}]".format(uid = alloc["id"]))    
    

def clean_exnode(exnode, allocs):
    contains_data = False
    
    for allocation in exnode["extents"]:
        try:
            alloc = factory.buildAllocation(allocation)
            if alloc:
                print("Found live allocation: {alloc}".format(alloc = allocation["id"]))
                contains_data = True
            else:
                remove_allocation(allocation, allocs)
        except Exception as exp:
            print("Could not confirm allocation: {alloc} - {exp}".format(alloc = allocation["id"], exp = exp))
            remove_allocation(allocation, allocs)
    
    return contains_data


def prune_directories(collection, allocs):
    root = collection.find({"parent": None})
    
    for exnode in root:
        search_children(exnode, collection, allocs)


def search_children(exnode, collection, allocs):
    contains_data = False

    if exnode["mode"] == "file":
        contains_data = clean_exnode(exnode, allocs)
        if not contains_data:
            print("removing: Exnode[{exnode}]".format(exnode = exnode["id"]))
            collection.remove({ "id": exnode["id"] })
        return contains_data

    children = collection.find({ "parent": exnode["id"] })

    for child in children:
        contains_data = contains_data | search_children(child, collection, allocs)

    if not contains_data:
        collection.remove({"id": exnode["id"]})
        print "Removing Directory: {0}".format(exnode["name"])

    return contains_data
        
        
def main():
    client = MongoClient()
    db = client["unis_db"]
    exnodes = db.exnodes
    allocs = db.extents
    
    prune_directories(exnodes, allocs)

if __name__ == "__main__":
    main()
