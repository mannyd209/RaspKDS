import socket
from threading import Thread
import requests

HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 9999       # Port to listen on

def handle_client_connection(client_socket):
    try:
        request = client_socket.recv(1024)
        if not request:
            # No data received, close connection
            print("No data received.")
            client_socket.close()
            return

        # Decode received data
        text_content = request.decode('utf-8', errors='ignore')
        print(f"Received: {text_content}")  # Confirm reception in terminal

        # Forward the received data to the Flask app
        try:
            response = requests.post('http://127.0.0.1:5000/api/print', json={'data': text_content}, timeout=5)
            # Confirm successful forwarding
            print(f"Forwarded to Flask app, response: {response.status_code}, {response.text}")
        except requests.exceptions.RequestException as e:
            # Handle errors in forwarding data to Flask app
            print(f"Error forwarding data to Flask app: {e}")

    except Exception as e:
        print(f"Error handling client connection: {e}")
    finally:
        client_socket.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"Listening on {HOST}:{PORT}")

        try:
            while True:
                client_sock, address = server.accept()
                print(f"Accepted connection from {address[0]}:{address[1]}")
                client_handler = Thread(target=handle_client_connection, args=(client_sock,))
                client_handler.start()
        except KeyboardInterrupt:
            print("Server stopping...")
        except Exception as e:
            print(f"Error in server main loop: {e}")

if __name__ == "__main__":
    start_server()

