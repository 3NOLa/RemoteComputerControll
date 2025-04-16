Remote Network Control Suite

A Python-based tool designed to discover devices on a local network, redirect them to a specified site for code download, and enable remote control functionalities upon execution.

Features
	•	Network Discovery: Scans the local network to identify connected devices.
	•	Redirection Mechanism: Redirects identified devices to a specified site for code download.
	•	Remote Control: Allows the administrator to connect and control devices that have executed the downloaded code.
	•	Modular Design: Structured with separate modules for GUI, networking, and control functionalities.

Installation
	1.	Clone the repository: ￼

git clone https://github.com/3NOLa/RemoteComputerControll.git


	2.	Navigate to the project directory:

cd RemoteComputerControll


	3.	Install the required dependencies:

pip install -r requirements.txt



Usage
	1.	Run the AdminGui.py script to launch the administrator interface.

python AdminGui.py


	2.	Use the interface to scan the network and redirect devices.
	3.	Monitor connected devices and initiate remote control sessions as needed.

Modules Overview
	•	AdminGui.py: Graphical user interface for the administrator.
	•	AdminNetwork.py: Handles network scanning and device redirection.
	•	ClientNetwork.py: Manages client-side network communications.
	•	Connecting_server.py: Establishes connections between the administrator and clients.
	•	ControlKeyboard.py: Enables keyboard control functionalities.
	•	ScreenShareFrame.py: Facilitates screen sharing between administrator and clients.
	•	Myprotocol.py: Defines custom communication protocols.
	•	StopAbleThread.py: Implements threads that can be stopped gracefully.

Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

License

This project is licensed under the MIT License. See the LICENSE file for details.

Image of the GUI:

![image](https://github.com/user-attachments/assets/449eee84-b822-4b6c-abb5-f1584bbcedf5)
