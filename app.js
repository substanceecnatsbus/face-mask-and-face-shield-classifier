/*
    SERVER SETUP
        NET: socket server
        APP: web server (express/http)
        IO: socketio server
*/
const NET = require('net');
const EXPRESS = require('express');
const APP = EXPRESS();
const HTTP = require('http').Server(APP);
const IO = require('socket.io')(HTTP);
const BODY_PARSER = require('body-parser');
const CORS = require('cors');
const { send } = require('process');
const { type } = require('os');
APP.use(EXPRESS.static("view"))
APP.use(BODY_PARSER.json());
APP.use(CORS());

// CONSTANTS
const WEB_SERVER_PORT = 3001
const SOCKET_PORT = 3000;
const HEADER_LENGTH = 7;
const TEMPERATURE_EVENT = "temperature";
const CLASSIFICATION_EVENT = "classification";
const USER_INFO_EVENT = "user_info";
const CONFIDENCE_LEVEL_EVENT = "confidence_level";

// SERVER STATE
let client_socket = null;
let queue = [];

// encapsulates data with a proper header, type, and sends it to the socket client (maixduino)
// THIS IS ONLY A ONE-TO-ONE CONNECTION 
function send_data(data, type) {
    let data_length = data.length;
    let header = String(data_length).padEnd(HEADER_LENGTH, " ");
    let payload = header + type + data;
    client_socket.write(payload);
}

// creates the socket server and sets the callback for recieving data from the maixduino
let socket_server = NET.createServer(socket => {
    socket.setEncoding("utf-8");
    socket.on("data", data => {
        let header = data.substring(0, HEADER_LENGTH).trim();
        let type = data[HEADER_LENGTH];
        let message = data.substring(HEADER_LENGTH+1);
        if (type === "0") {
            if (queue.length < 1) {
                // send a ping to maixduino to let it know it is still connected
                send_data("", 0);
            } else {
                // pop user info from queue and send it to maix
                user_info = queue.shift();
                send_data(JSON.stringify(user_info), 3);
            }
        } else if (type === "1") {
            // temperature
            IO.emit(TEMPERATURE_EVENT, message);
        } else if (type === "2") {
            // classification
            IO.emit(CLASSIFICATION_EVENT, message);
        } else if (type === "4") {
            // confidence level
            console.log(message);
            IO.emit(CONFIDENCE_LEVEL_EVENT, message);
        }
    });
});

// log connections to the socket server
socket_server.on("connection", socket => {
    console.log(`Socket Server\nConnection Established with ${socket.remoteAddress}.\n`);
    client_socket = socket;
});

// log connections to the socketIO server
IO.on('connection', (socket) => {
    console.log(`SocketIO Server\nConnection Established with ${socket.id}.\n`);

    // callback for when form is submitted 
    socket.on(USER_INFO_EVENT, user_info => {
        user_info_csv = "";

        // convert user_info json into a csv row
        for (let i in user_info) {
            if (typeof(user_info[i]) === "object") {
                // user_info[i] is json
                for (let j in user_info[i]) {
                    user_info_csv += `${user_info[i][j]},`;
                }
            } else {
                // user_info[i] is string
                user_info_csv += `${user_info[i]},`;
            }
        }
        user_info_csv = user_info_csv.substring(0, user_info_csv.length-1)
        queue.push(user_info_csv);
    });
});

// serve index.html to web browsers
APP.get('/', (req, res) => {
    res.sendFile("./view/index.html");
})

// let web server and socketIO server listen on WEB_SERVER_PORT
// used to communicate with browsers
HTTP.listen(WEB_SERVER_PORT, () => {
  console.log(`Web server listening on http://localhost:${WEB_SERVER_PORT}...\n`);
});

// let socket server listen on SOCKET_PORT
// used to communicate with the maixduino
socket_server.listen(SOCKET_PORT, function() {
  console.log(`Socket server listening on port ${SOCKET_PORT}...\n`);
});



