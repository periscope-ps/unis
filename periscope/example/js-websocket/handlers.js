tab = "&nbsp;&nbsp;&nbsp;&nbsp;";

$(document).ready(init);

function init() {
    open_websocket("measurement");
    open_websocket("service");
    open_websocket("measurement", "2");
}


/*
open_websocket is a factory function that encapsulates all of the
necessary steps to open a websocket and include handlers
*/
function open_websocket(resource, id, callback) {
    // status_message, show_message, and add_line are feedback functions
    // which print messages to the user.
    function status_message(message, resource) {
	var messageBox = $( "<span>" );
	if (!(typeof(resource) === 'undefined')) {
	    messageBox.addClass(resource);
	    messageBox.addClass('highlight');
	}
	messageBox.html(message);
	$("#connectionStatus").append(messageBox);
    }
    
    function show_message(message, resource) {
	var messageBox = $( "<span>" );
	if (!(typeof(resource) === 'undefined'))
	    messageBox.addClass(resource);
	messageBox.html(message);
	$("#output").append(messageBox);
    }
    function add_line(field) {
	if (field == "status") {
	    $("#connectionStatus").append($("<div class='break'/>"));
	}
	else {
	    $("#output").append($("<div class='break'/>"));
	}
    }

    var fullResource = resource;
    if (typeof(resource) === 'undefined') return;
    if (!(typeof(id) === 'undefined')) {
	fullResource = resource + '/' + id;
	resource = resource + '-' + id;
    }
    
    // Initialize the host as the location of the unis instance.
    // In order to make a subscription, the path MUST begin with
    // the 'subcribe' node.
    var hostURL = "ws://localhost:8888/subscribe/";
    var socket = new WebSocket(hostURL + fullResource);
    
    // Setup the callback functions for opening a connection, closing
    // a connection, and when a message is recieved.
    socket.onopen = function(event) {
	status_message(tab + "Subscribed to ");
	status_message("&nbsp;" + fullResource + "&nbsp;", resource);   
	add_line("status");
    };
    
    if (typeof(callback) === 'undefined') {
	// onmessage is the function most likely implemented on a pubsub
	// interface, it handles incoming published messages.
	socket.onmessage = function(event) {
	    show_message("&nbsp;" + event.data + "&nbsp;", resource);
	    add_line();
	};
    }
    else {
	socket.onmessage = calllback;
    }
    
    socket.onclose = function() {
	add_line("status");
	status_message("Connection to " + fullResource + " closed.");
	add_line("status");
    };
    
    return socket;
}
