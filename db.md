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
    
* reg=  As part of filed name
  Example :
      
        http://localhost:8888/exnodes?parent=reg=123%23
        http://localhost:8888/exnodes?name=reg=abc

  Where name and parent are the field and reg= makes it a regular expression
  Escaped value can be sent to it
  
