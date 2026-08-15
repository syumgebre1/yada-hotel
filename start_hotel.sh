#!/bin/bash

echo "🏨 Starting YADA HOTEL..."

# Start backend
cd ~/yada_hotel_backend
python app.py &
echo "✅ Backend started on port 5000"

# Start frontend
cd ~/storage/shared/YADA-HOTEL
python -m http.server 8159 &
echo "✅ Frontend started on port 8159"

echo "🌐 Open: http://127.0.0.1:8159"
echo "🛑 To stop: pkill -f python"
