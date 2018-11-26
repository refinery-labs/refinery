echo "Starting nginx..."
/etc/init.d/nginx restart
echo "Starting API server..."
/usr/bin/python -u /work/api/server.py
