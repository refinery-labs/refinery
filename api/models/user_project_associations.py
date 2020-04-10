from initiate_database import Base
from sqlalchemy import Column, Integer, String, func, update, Text, Binary, Boolean, BigInteger, event, select, exc, CHAR, ForeignKey, JSON, Table

users_projects_association_table = Table(
	"user_projects_association",
	Base.metadata,
	Column(
		"users",
		CHAR(36),
		ForeignKey(
			"users.id"
		)
	),
	Column(
		"projects",
		CHAR(36),
		ForeignKey(
			"projects.id"
		)
	)
)
