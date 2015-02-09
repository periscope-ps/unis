## Simple query
Normally for any field a simple query would work for exact match
Also you can use `not` for reverse

For numbers , you can use `lte , gte , gt , lt , eq`
**You have to use `eq` for numbers because of bug due to which we need to expliciity specify**

Example :

    http://localhost:8888/exnodes?extents.size=lte=1
    http://localhost:8888/exnodes?extents.size=eq=111

Also reg is supported

* reg=  As part of filed name
  Example :
      
        http://localhost:8888/exnodes?parent=reg=123%23
        http://localhost:8888/exnodes?name=reg=abc

  Where name and parent are the field and reg= makes it a regular expression
  Escaped value can be sent to it

## Null Query
You need to use `null=` after the field. ** Don't forget the `=` after the null.
Example :

    http://localhost:8888/exnodes?extents.size=null=

## DB Query Urls

Following parameters can be passed to UNIS query

* fields  : Projection
  Example : 

        http://localhost:8888/exnodes?fields=name,parent

    Where name and parent are the fields to be shown
* sort  : Possibly not working - Bug
  Example :
      
        http://localhost:8888/exnodes?sort=name:1,parent:-1

    Syntax :
    
        <fieldname>:<1/-1>
    Where 1 for increasing and -1 for decreasing order. This takes in comma separated list
    
* skip
  Example :
  
        http://localhost:8888/exnodes?skip=1

    Specifies number of fields to be skipped - Meant for pagination. Supposed to be used in conjuction with `limit` and `X-count` header to achieve pagination
    
* limit
  Example :

        http://localhost:8888/exnodes?limit=10

    Limits number of items displayed for query, Check skip doc to use it for pagination
      
## Query child

You can query children using dot notation.

Example :

    http://localhost:8888/exnodes?extents.mapping.read=reg=709

This queries
    { "extents" : [
		{
			"mapping" : {
				"read" : "ibp://depot5.loc1.ufl.reddnet.org:6714/719#Bd+NG8YmY1jtpZGaUaIIvo1gnYWwFxoT/3862277/READ",
				"write" : "ibp://depot5.loc1.ufl.reddnet.org:6714/719#qTT50RySoQnz7ryEoftbyCGm0iujN0Sv/3862277/WRITE",
				"manage" : "ibp://depot5.loc1.ufl.reddnet.org:6714/719#PpDDrXnyu3dLAcn717sgfHmenEBSqRvE/3862277/MANAGE"
			},
			"location" : "ibp://",
		},{..}],
        "blahb":1}

