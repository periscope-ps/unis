// =============================================================================
//  periscope-ps (unis)
//
//  Copyright (c) 2012-2016, Trustees of Indiana University,
//  All rights reserved.
//
//  This software may be modified and distributed under the terms of the BSD
//  license.  See the COPYING file for details.
//
//  This software was created at the Indiana University Center for Research in
//  Extreme Scale Technologies (CREST).
// =============================================================================
var fs   = require('fs');
var http = require('http');
var WebSocket = require('ws');
var WebSocketServer = WebSocket.Server;

var server = http.createServer(function(request, response) {
	response.writeHead(200, { 'Content-Type': 'text/html' });
	response.end(fs.readFileSync(__dirname + '/index.html'));
    }).listen(8080);

var socketServer = new WebSocketServer({port: 7171});
socketServer.on('connection', function(ws) {
	ws.on('message', function(message) {
		console.log('recieved: %s', message);
	    });
	console.log('New client listening');
    });
socketServer.broadcast = function(data) {
    for (var i in this.clients) {
	this.clients[i].send(data);
    }
};

var measurementSocket = new WebSocket('ws://localhost:8888/subscribe/measurement');

measurementSocket.on('open', function(event) {
	console.log("Connected");
    });

measurementSocket.on('message', function(data) {
	console.log(data);
	socketServer.broadcast(data);
    });

measurementSocket.on('close', function(event) {
	console.log("Disconnected");
    });
