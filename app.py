from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import os
from itertools import count

app = Flask(__name__)
orders_file = 'orders.json'
dismissed_orders_file = 'dismissedorders.json'

id_generator = count(start=1)

def load_json_file(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.decoder.JSONDecodeError:
            return []
    return []

def save_json_file(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4, default=str)

def load_orders():
    return load_json_file(orders_file)

def load_dismissed_orders():
    return load_json_file(dismissed_orders_file)

def assign_id(order):
    order['id'] = next(id_generator)

print_jobs = load_orders()

@app.route('/api/print', methods=['POST'])
def receive_print_job():
    items = request.json.get('items', [])
    timestamp = datetime.now().strftime("%m-%d-%y %I:%M %p")
    new_order = {
        'items': items,
        'timestamp': timestamp,
        'removed': False
    }
    assign_id(new_order)
    print_jobs.append(new_order)
    save_json_file(print_jobs, orders_file)
    return jsonify({'message': 'Print job received', 'id': new_order['id']}), 200

@app.route('/api/orders', methods=['GET'])
def get_orders():
    active_orders = [job for job in print_jobs if not job['removed']]
    return jsonify(active_orders)

@app.route('/api/remove', methods=['POST'])
def remove_order():
    order_id = request.json.get('id')
    global print_jobs
    for i, order in enumerate(print_jobs):
        if order['id'] == order_id:
            dismissal_time = datetime.now()
            duration_seconds = int((dismissal_time - datetime.strptime(order['timestamp'], "%m-%d-%y %I:%M %p")).total_seconds())
            minutes, seconds = divmod(duration_seconds, 60)
            order['duration'] = f"{minutes}m {seconds}s"
            order['dismissal_time'] = dismissal_time.strftime("%m-%d-%y %I:%M %p")
            order['removed'] = True
            dismissed_orders = load_dismissed_orders()
            dismissed_orders.append(order)
            save_json_file(dismissed_orders, dismissed_orders_file)
            del print_jobs[i]
            save_json_file(print_jobs, orders_file)
            return jsonify({'message': 'Order removed', 'duration': order['duration']}), 200
    return jsonify({'message': 'Order not found'}), 404

@app.route('/api/recall', methods=['POST'])
def recall_orders():
    order_id = request.json.get('id')
    dismissed_orders = load_dismissed_orders()
    order_to_recall = None
    for order in dismissed_orders:
        if order['id'] == order_id:
            order_to_recall = order
            break
    if order_to_recall:
        dismissed_orders.remove(order_to_recall)
        print_jobs.append(order_to_recall)
        save_json_file(print_jobs, orders_file)
        save_json_file(dismissed_orders, dismissed_orders_file)
        return jsonify({'message': 'Order recalled', 'id': order_to_recall['id']}), 200
    return jsonify({'message': 'Order not found'}), 404




@app.route('/')
def show_prints():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RaspKDS</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta name="apple-mobile-web-app-capable" content="yes">
            <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
            <meta name="apple-mobile-web-app-title" content="RaspKDS">
            <link rel="apple-touch-icon" href="/Users/mannyd/Desktop/icon.png">
        <style>
            body { 
                background-color: black;
                color: white;
                font-family: Arial, sans-serif;
                padding: 20px;
                display: flex;
                flex-direction: column;
                align-items: flex-start;
            }
            #orders-container {
                display: flex;
                flex-wrap: wrap;
                justify-content: flex-start;
                gap: 10px;
                margin-top: 50px;
                width: 100%;
            }
            .order {
                background-color: #333;
                margin: 5px;
                padding: 20px;
                border-radius: 10px;
                width: 200px;
                cursor: pointer;
            }
            .mini-header {
   		display: flex;
    		justify-content: space-between;
    		margin-bottom: 20px;
    		background-color: #505050; /* A lighter shade of grey */
    		padding: 5px; /* Add padding to distinguish the header area */
    		border-radius: 5px; /* Optional: adds rounded corners to the mini-header */
		}

	   .timestamp, .timer {
    		font-size: 0.8em; /* Smaller font size for timestamps */
    		color: #D0D0D0; /* Optional: lighter font color for better contrast */
    		pointer-events: none; /* Ensure these don't capture click events, passing them 			to the mini-header */
		}

	  .order > div:not(.mini-header) {
    		font-size: 1em; /* Bigger font size for order info */
		}



            #recall-popup {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.75);
                z-index: 2000;
                display: none;
                justify-content: center;
                align-items: center;
            }
            #recall-content {
                background-color: white;
                color: black;
                padding: 20px;
                border-radius: 5px;
                width: 80%;
                max-width: 600px;
            }
            #close-popup {
                float: right;
                font-size: 28px;
                cursor: pointer;
            }
            #recalled-orders-list .recalled-order {
                background-color: #444;
                color: white;
                padding: 5px;
                margin-bottom: 5px;
            }
            #recall-btn {
                color: black;
                background-color: red;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                position: fixed;
                top: 10px;
                right: 10px;
                z-index: 1000;
                font-size: 18px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <button id="recall-btn">Recall Orders</button>
        <div id="orders-container"></div>
        <div id="recall-popup">
            <div id="recall-content">
                <span id="close-popup">&times;</span>
                <h2>Recalled Orders</h2>
                <div id="recalled-orders-list" style="max-height: 400px; overflow-y: scroll;"></div>
            </div>
        </div>
        <script>
            function fetchOrders() {
    fetch('/api/orders')
    .then(response => response.json())
    .then(data => {
        const ordersContainer = document.getElementById('orders-container');
        ordersContainer.innerHTML = '';
        data.forEach((job, index) => {
    const orderElement = document.createElement('div');
    orderElement.classList.add('order');

    const miniHeader = document.createElement('div');
    miniHeader.classList.add('mini-header');

    // Attach the event listener to miniHeader for dismissal
    miniHeader.addEventListener('click', function() {
        removeOrder(index);
    });

    const timestampDiv = document.createElement('div');
    timestampDiv.classList.add('timestamp');
    timestampDiv.textContent = job.timestamp;

    const timerDiv = document.createElement('div');
    timerDiv.classList.add('timer');
    timerDiv.setAttribute('data-time-received', job.timestamp_raw);

    miniHeader.appendChild(timestampDiv);
    miniHeader.appendChild(timerDiv);
    orderElement.appendChild(miniHeader);

    const dataDiv = document.createElement('div');
    dataDiv.textContent = job.data;
    orderElement.appendChild(dataDiv);

    ordersContainer.appendChild(orderElement);
});

        updateTimers();
    });
}
function removeOrder(index) {
    fetch('/api/remove', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: index }),
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message); // Log the response for debugging
        fetchOrders(); // Refresh the orders to reflect the removal
    })
    .catch(error => console.error('Error removing order:', error));
}


            document.getElementById('recall-btn').addEventListener('click', function() {
    fetch('/api/recall')
    .then(response => response.json())
    .then(data => {
        const listContainer = document.getElementById('recalled-orders-list');
        listContainer.innerHTML = '';
        data.forEach(order => {
            const orderItem = document.createElement('div');
            orderItem.classList.add('recalled-order');
            const originalTime = new Date(order.timestamp_raw).toLocaleTimeString();
            // Ensure you're using backticks for template literals
            orderItem.textContent = `Time: ${originalTime}, Duration: ${order.duration} - ${order.data}`;
            // Append an event listener for recalling orders
            orderItem.addEventListener('click', () => recallOrder(order.id));
            listContainer.appendChild(orderItem);
        });
        document.getElementById('recall-popup').style.display = 'flex';
    });
});


            document.getElementById('close-popup').addEventListener('click', function() {
                document.getElementById('recall-popup').style.display = 'none';
            });

            function updateTimers() {
                document.querySelectorAll('.order').forEach(order => {
                    const orderTimestamp = new Date(order.dataset.timestamp);
                    const now = new Date();
                    const elapsed = now - orderTimestamp;
                    const minutes = Math.floor(elapsed / 60000);
                    const seconds = Math.floor((elapsed % 60000) / 1000);
                    order.querySelector('.timer').textContent = '${minutes}m ${seconds}s';
                });
            }

            	setInterval(updateTimers, 1000);
		setInterval(fetchOrders, 1000);
            document.addEventListener('DOMContentLoaded', fetchOrders);
        </script>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
