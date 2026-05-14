# Network Backgammon Game

Network Backgammon Game is a desktop backgammon application developed with Python. The project uses a client-server architecture, allowing two players to connect and play the game over a network.

The main focus of this project is not only to create a playable game, but also to apply basic computer networks concepts in a real desktop application. Socket programming is used to manage the communication between the server and the client, while the user interface is built with PyQt and Qt Designer.

## About the Project

This project demonstrates how two separate programs can communicate with each other through a network connection.

In the application, one side runs the server and waits for a connection. The other side runs the client and connects to the server. After the connection is established, players can interact with the game through the graphical interface. Moves and game-related data are transferred between the client and server during the game.

## Key Features

- Desktop-based backgammon game
- Client-server communication
- Network-based two-player gameplay
- Graphical user interface developed with PyQt
- Interface screens designed with Qt Designer
- Separate start, game, and end screens
- Move data transfer between server and client
- Basic socket programming implementation

## How It Works

The application works with two main parts: the server and the client.

First, the server program must be started. The server opens a connection and waits for the client. Then, the client program is started and connects to the server. Once the connection is successful, the game can begin.

During the game, player actions are handled through the interface. The necessary game data is sent between the client and server using sockets. This allows both sides to follow the game flow through the network connection.

## How to Run

First, start the server:

    python run_server.py

Then, open a second terminal window and start the client:

    python run_client.py

The server should always be started before the client.

## Technologies Used

The project was developed with Python and uses the following main components:

- Python
- PyQt
- Qt Designer
- Socket Programming
- Client-Server Architecture

## Project Purpose

The purpose of this project is to practice the main topics of computer networks through a working application. Instead of only learning the theory of client-server communication, this project applies that structure inside a playable desktop game.

By developing this project, practical experience was gained in establishing a connection between two programs, sending and receiving data, managing the game flow, and combining network communication with a graphical user interface.
