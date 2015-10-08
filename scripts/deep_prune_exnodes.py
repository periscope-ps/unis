from pymongo import MongoClient
from protocol import factory
from protocol.exceptions import AllocationException
import datetime
import concurrent.futures



class Search(object):
    def __init__(self, exnodes, allocs):
        self._exnodes = exnodes
        self._allocs = allocs
    
    def remove_allocation(self, alloc):
        self._allocs.remove({ "id": alloc["id"] })
        print("removing: Allocation[{uid}]".format(uid = alloc["id"]))    


    def test_allocation(self, allocation):
        print("  Testing Allocation[{alloc}]".format(alloc = allocation["id"]))
        try:
            alloc = factory.buildAllocation(allocation)
            if alloc:
                print("Found live allocation: {alloc}".format(alloc = allocation["id"]))
                return True
            else:
                remove_allocation(allocation)
                return False
        except Exception as exp:
            print("Could not confirm allocation: {alloc} - {exp}".format(alloc = allocation["id"], exp = exp))
            remove_allocation(allocation, allocs)
            return False
                
    def clean_exnode(self, exnode):
        contains_data = False

        with concurrent.futures.ThreadPoolExecutor(max_workers = 15) as executor:
            for result in executor.map(self.test_allocation, exnode["extents"]):
                contains_data = contains_data | result
        return contains_data


    def prune_directories(self):
        root = self._exnodes.find({"parent": None})
        
        with concurrent.futures.ThreadPoolExecutor(max_workers = 15) as executor:
            for result in executor.map(self.search_children, root):
                pass


    def search_children(self, exnode):
        contains_data = False

        print("Checking Exnode[{exnode}]".format(exnode = exnode["id"]))
        if exnode["mode"] == "file":
            contains_data = self.clean_exnode(exnode)
            if not contains_data:
                print("removing: Exnode[{exnode}]".format(exnode = exnode["id"]))
                self._exnodes.remove({ "id": exnode["id"] })
                
            return contains_data

        children = collection.find({ "parent": exnode["id"] })
    
        with concurrent.futures.ThreadPoolExecutor(max_workers = 15) as executor:
            for result in executor.map(search_children, children):
                contains_data = contains_data | result

        if not contains_data:
            collection.remove({"id": exnode["id"]})
            print "Removing Directory: {0}".format(exnode["name"])
        
        return contains_data


def main():
    client = MongoClient()
    db = client["unis_db"]
    search = Search(db.exnodes, db.extents)

    print("Starting prune....")
    search.prune_directories()

    
if __name__ == "__main__":
    main()
