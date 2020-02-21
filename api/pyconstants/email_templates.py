import os

EMAIL_TEMPLATES = {}

def email_templates_init():
	global EMAIL_TEMPLATES
	
	# Email templates
	email_templates_folder = "./email_templates/"
	for filename in os.listdir( email_templates_folder ):
		template_name = filename.split( "." )[0]
		with open( email_templates_folder + filename, "r" ) as file_handler:
			EMAIL_TEMPLATES[ template_name ] = file_handler.read()

email_templates_init()