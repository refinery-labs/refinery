import os
import tornado
import requests

from tornado.concurrent import run_on_executor, futures
from utils.general import logit
from tornado import gen

from utils.base_spawner import BaseSpawner

class EmailSpawner(BaseSpawner):
	@run_on_executor
	def send_email( self, to_email_string, subject_string, message_text_string, message_html_string ):
		"""
		to_email_string: "example@refinery.io"
		subject_string: "Your important email"
		message_text_string: "You have an important email here!"
		message_html_string: "<h1>ITS IMPORTANT AF!</h1>"
		"""
		return EmailSpawner._send_email(
			to_email_string,
			subject_string,
			message_text_string,
			message_html_string
		)
		
	@staticmethod
	def _send_email( to_email_string, subject_string, message_text_string, message_html_string ):
		logit( "Sending email to '" + to_email_string + "' with subject '" + subject_string + "'..." )
		
		requests_options = {
			"auth": ( "api", os.environ.get( "mailgun_api_key" ) ),
			"data": {
				"from": os.environ.get( "from_email" ),
				"h:Reply-To": "support@refinery.io",
				"to": [
					to_email_string
				],
				"subject": subject_string,
			}
		}
		
		if message_text_string:
			requests_options[ "data" ][ "text" ] = message_text_string
			
		if message_html_string:
			requests_options[ "data" ][ "html" ] = message_html_string
		
		response = requests.post(
			"https://api.mailgun.net/v3/mail.refinery.io/messages",
			**requests_options
		)
		
		return response.text

email_spawner = EmailSpawner()