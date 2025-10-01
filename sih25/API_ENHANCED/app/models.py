from sqlalchemy import Column, Integer, Float, String, Date, Index, BigInteger
from sqlalchemy.orm import relationship
from .db import Base

class Profile(Base):
	__tablename__ = 'profiles'

	id = Column(BigInteger, primary_key=True, index=True)
	float_id = Column(String, index=True)
	lat = Column(Float, index=True)  # Changed from latitude to match DB
	lon = Column(Float, index=True)  # Changed from longitude to match DB
	depth = Column(Integer)  # Changed from Float to Integer to match DB
	temperature = Column(Float)
	salinity = Column(Float)
	month = Column(BigInteger, index=True)  # Changed from Integer to BigInteger
	year = Column(BigInteger, index=True)   # Changed from Integer to BigInteger
	date = Column(Date, nullable=True)

	# Add properties for backward compatibility
	@property
	def latitude(self):
		return self.lat
	
	@latitude.setter
	def latitude(self, value):
		self.lat = value
	
	@property
	def longitude(self):
		return self.lon
	
	@longitude.setter
	def longitude(self, value):
		self.lon = value

	__table_args__ = (
		Index('idx_profiles_lat_lon', 'lat', 'lon'),  # Updated index names
	)
