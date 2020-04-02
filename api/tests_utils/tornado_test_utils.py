from tornado.concurrent import Future


def create_future( result=None ):
	future = Future()
	future.set_result(result)
	return future
