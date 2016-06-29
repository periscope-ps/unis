// remove any service entries that have expired
// i.e.: timestamp + time-to-live is less than now
function swapRef(entry) {
    if (typeof entry.parent == "string") {
	var parent = entry.selfRef.substring(0, entry.selfRef.lastIndexOf("/"));
	parent = parent.substring(0, parent.lastIndexOf("/"));
	collection.update( { "id": entry.id },
			   { "$set": {
			       "parent": {
				   "href": parent + "/exnodes/" + entry.parent,
				   "rel": "full"
			       }
			   }});
    }
}

conn = new Mongo()
db = conn.getDB("unis_db")

// get all services
collection = db.exnodes;
cur = collection.find();
cur.forEach(swapRef);

collection = db.extents;
cur = collection.find();
cur.forEach(swapRef);
