function removeExnodes(e) {
    files = db.exnodes.find({$and: [{mode: "file", parent: e.id}]})
    files.forEach(function(f) { 
	extents = db.extents.remove({parent: f.id})
	print("removing file: " + f.name); db.exnodes.remove(f)
    })
    sdirs = db.exnodes.find({$and: [{mode: "directory"}, {parent: e.id}]})
    sdirs.forEach(removeExnodes)
    print("removing dir: " + e.name)
    db.exnodes.remove(e)
}

REMOVE_DIR = null

conn = new Mongo()
db = conn.getDB("unis_db")
now = new Date().getTime()*1000

// find the top-level directory to recursively remove                                                                                           
dir = db.exnodes.find({$and: [{name: REMOVE_DIR},
                              {mode: "file"},
                              {parent: null}]})
dir.forEach(removeExnodes)
