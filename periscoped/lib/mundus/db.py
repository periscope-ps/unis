import pymongo, time

from bson import ObjectId
from pymongo.collection import Collection

from mundus.utils import getLogger

class DatabaseError(Exception): pass
class AccessError(DatabaseError): pass

log = getLogger("db")
class DBLayer(object):
    def __init__(self, db:Collection, id_field:str="id", ts_field:str="ts"):
        self.db, self.id, self.ts = db, id_field, ts_field

    def _user_query(self, sb, prefix=None):
        prefix = "" if prefix is None else f"{prefix}."
        return {"$or": [
            {"$and": [{prefix + "permissions": {"$bitsAnySet": 256}},
                      {prefix + "user": sb['id']}]},
            {"$and": [{prefix + "permissions": {"$bitsAnySet": 32}},
                      {prefix + "group": {"$in": sb['groups']}}]},
            {prefix + "permissions": {"$bitsAnySet": 4}}
        ]}

    def get_superblock(self, rid:str) -> dict:
        """
        :param rid: ID for the record in question
        :type rid: int

        :return: record superblock or None if no record exists
        :rtype: dict
        
        Retrieve the record superblock for a record.  If not superblock exists,
        return a defualt record.
        """
        return self.db.find_one({f"v.{self.id}": rid}, {'v': 0, '_id': 0}) or None

    def get_user(self, username:str) -> dict:
        """
        :param username: user to retrieve permission block for
        :type username: str
        
        :return: Returns the information for the user
        :rtype: dict
        
        Retrieves the user information from the database.
        """
        c = self.db.database.users
        user = c.find_one({'name': username})
        if not user:
            user = {
                "id": str(ObjectId()),
                "name": username,
                "passwd": "",
                "groups": [],
                "created": int(time.time() * 1000000)
            }
            c.insert_one(user)
        return user

    def find(self, f:dict, proj:dict, loc:str, sort:dict=None,
             skip:int=0, limit:int=None, user:dict=None,
             archived:bool=False, history:bool=False) -> list:
        """
        :param f: Filter for records, all returned records must match f. ``f`` is a mongodb formatted query.
        :type f: dict
        
        :param proj: Projection of included fields. ``proj`` is a mongodb formatted projection.
        :type proj: dict
        
        :param loc: The partial url describing the location of he record.  This is used to generate selfRef fields.
        :type loc: str
        
        :param sort: A sort dictionary as described by mongodb, dictates the order of the returned records.
        :type sort: dict
        
        :param skip: Skips the first ``skip`` records in the the returned set.
        :type skip: int
        
        :param limit: Limits results to ``limit`` number of results.  This operation is performed after all other filters.
        :type limit: int
        
        :param user: User information block with permission information.  This further filters returned records by permission.
        :type user: dict
        
        :param archived: If true, returns records flagged as deleted in addition to active records.
        :type archived: bool
        
        :param history: If true, returns all instances of each matching records.  Otherwise, return only the most recent record for each id.
        
        :return: Returns a list of records
        :rtype: list[dict]
        
        Find records in the collection with a provided set of properties and expresed
        with a provided projection.
        """
        sort = {f"{self.ts}": -1} if sort is None else {k:s for k,s in sort}

        filter_users = [{"$match": self._user_query(user)}]
        if not archived:
            filter_users[0]["$match"] = {"$and": [{"status": {"$ne": "deleted"}}, filter_users[0]["$match"]]}
        is_unique = [{"$sort": {f"v.{self.ts}": -1}}]
        if not history:
            is_unique.append({"$group": {"_id": f"$v.{self.id}", "v": {"$first": "$v"}}})
        filter_result = [{"$replaceWith": "$v"}]
        if f:
            filter_result.append({"$match": f})
        if skip:
            filter_result.append({"$skip": skip})
        if limit is not None:
            filter_result.append({"$limit": limit})
        filter_result.append({"$sort": sort})
        if proj:
            if 'selfRef' in proj:
                proj[self.id] = 1
            filter_result.append({"$project": proj})
        if proj is None or 'selfRef' in proj:
            filter_result.append({"$addFields": {"selfRef": {"$concat": [loc, f"${self.id}"]}}})

        log.debug(f"Executing query - {filter_users + is_unique + filter_result}")
        return list(self.db.aggregate(filter_users + is_unique + filter_result))

    def find_one(self, f:dict, proj:dict, loc:str, user:int=None, history:bool=False, limit:int=None) -> list:
        """
        Returns a list of records for a filter from the collection.  All arguments are described in
        :meth:`DBLayer.find <mundus.db.DBLayer.find>`.
        """
        if history:
            return list(self.find(f, proj, loc, None, 0, limit, user, False, True))
        else:
            try:
                return list(self.find(f, proj, loc, None, 0, 1, user, False, False))
            except IndexError:
                return None

    def left_join(self, d:str, col: str, rid:str, f:dict, proj:dict, loc:str,
                  user:int=None, sort:dict=None, **kwargs) -> list:
        """
        Returns a left-join of a set of relations.  All arguments are described in
        :meth:`DBLayer.find <mundus.db.DBLayer.find>`.
        """
        reverse = "target" if d == "subject" else "subject"
        sort = {f"{self.ts}": -1} if sort is None else {k:s for k,s in sort}
        user_block = self._user_query(user)
        origin = {"$and": [
            {"status": {"$ne": "deleted"}},
            {f"v.{reverse}": {"$regex": f".+{col}\/{rid}\/?"}},
            user_block
        ]}
        view = {d: {"$slice": [{"$split": [f"$v.{d}", "/"]}, -2]}, "raw": f"$v.{d}"}
        facets = {}
        cols = list({r[d][0] for r in self.db.find(origin, view)})
        if not cols:
            log.debug(f"Found no matching records in '{self.db.name}'")
            return []
        
        for v in cols:
            facets[v] = [
                {"$match": {"c": v}},
                {"$lookup": {
                    "from": v,
                    "let": { "raw": "$raw", "rid": "$rid"},
                    "pipeline": [
                        {"$match":
                         {"$and": [{"$expr":
                                    {"$and": [{"$ne": ["$status", "deleted"]},
                                              {"$eq": [f"$v.{self.id}","$$rid"]}]}},
                                   user_block]}},
                        {"$sort": {f"v.{self.ts}": -1}},
                        {"$group": {"_id": f"$v.{self.id}", "v": {"$first": "$v"}}},
                        {"$replaceWith": "$v"}
                    ],
                    "as": "foreign"
                }},
            ]

        build_join = [
            {"$match": origin},
            {"$project": view},
            {"$project": {"raw": 1, "c": {"$arrayElemAt": [f"${d}", 0]}, "rid": {"$arrayElemAt": [f"${d}", 1]}}},
            {"$facet": facets},
            {"$project": {"v": {"$setUnion": [f"${c}" for c in cols]}}},
            {"$unwind": "$v"},
            {"$replaceWith": {"$arrayElemAt": ["$v.foreign", 0]}}
        ]
        if f:
            build_join.append({"$match": f})
        build_join.append({"$sort": sort})
        if proj:
            if 'selfRef' in proj:
                proj[self.id] = 1
            build_join.append({"$project": proj})
        if proj is None or 'selfRef' in proj:
            build_join.append({"$addFields": {"selfRef": {"$concat": [loc, f"${self.id}"]}}})
        log.debug(f"Executing query - {build_join}")
        return list(self.db.aggregate(build_join))
        
    def insert(self, records:list, loc:str):
        """
        :param records: Contains a list of records to be inserted into the database.
        :type records: list

        :param auth: Contains the auth block used to determine record permissions.
        :type auth: dict

        :return: Returns the new record
        :rtype: dict

        Insert a record into the database with an authentication block.
        """
        for r in records:
            r['_id'] = f"{r['v'][self.id]}:{r['v'][self.ts]}"
            r['v']['selfRef'] = f"{loc}{r['v'][self.id]}"
        self.db.insert_many(records)
        return records

    def update(self, rid:str, data:dict, loc:str, many:bool=False):
        """
        :param rid: Record ID to update
        :type rid: str
        
        :param data: Contains update data for the record
        :type data: dict

        :return: Returns the updated record if many is ``False``, otherwise the number of updated records
        :rtype: dict

        Updating an existing record's contents.

        .. warning::
        This function overrites the existing content in the record.
        Unless specifically needed, use :meth:`DBLayer.insert <mundus.db.DBLayer.insert>`
        instead.
        """
        data = {"$set": {"v":  data}}
        f = {f"v.{self.id}": rid}
        hint = [(f"v.{self.ts}", pymongo.DESCENDING)]
        if many:
            res = self.db.update_many(f, data, hint=hint).matched_count
        else:
            res = self.db.find_one_and_update(f, data, hint=hint)
        if not res:
            raise AccessError(f"Attempting to modify unknown record '{rid}' from '{self.db.name}'")
        return res

    def delete(self, rid:str):
        data = {"$set": {"status": "deleted"}}
        f = {f"v.{self.id}": rid}
        res = self.db.update_many(f, data)

        if res.matched_count <= 0:
            raise AccessError(f"Attmpting to delete unknown record '{rid}' from '{self.db.name}'")

