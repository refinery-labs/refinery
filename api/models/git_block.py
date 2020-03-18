from initiate_database import *
import uuid

class GitBlock( Base ):
	__tablename__ = "git_blocks"

	id = Column(Text(), primary_key=True)

	repo_id = Column(
		CHAR(36),
		ForeignKey(
			"git_repos.id"
		)
	)

	saved_block_id = Column(
		CHAR(36),
		ForeignKey(
			"saved_blocks.id"
		)
	)

	def __init__( self, repo_id, saved_block_id ):
		self.id = str( uuid.uuid4() )
		self.repo_id = repo_id
		self.saved_block_id = saved_block_id

	def __str__( self ):
		return self.id
