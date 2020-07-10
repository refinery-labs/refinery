# Pidgeon
## Block return data management API
### Set up
```
virtualenv -p `which pypy3` .env
source .env/bin/activate
pip install -r requirements.txt
```
### Starting the server

Run the following command:

```
./bin/pidgeon
```

A similar log line should print, indicating that the server is online:

```
2020-07-10 15:01:30,979 [INFO] HTTP server listening on: 0.0.0.0:8080
```

Check that http requests to the server is working:

```
curl localhost:8080/health
```

The command should receive the following response:

```
{"success": true, "data": {"alive": true}}
```
