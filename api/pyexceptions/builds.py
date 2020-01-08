
class BuildException(Exception):
    def __init__( self, input_dict ):
    	self.msg = input_dict[ "msg" ]
    	self.build_output = input_dict[ "build_output" ]