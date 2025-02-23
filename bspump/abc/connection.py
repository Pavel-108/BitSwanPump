import abc
from asab import Configurable


class Connection(abc.ABC, Configurable):
	"""
	Connection class is responsible for creating a connection between items or services within the infrastructure of BSPump.
	Their main use is to create connection with the main components of BSPump: source, :meth:`processor <bspump.Processor()>` and sink.

	|

	"""

	def __init__(self, app, id=None, config=None):
		"""
		Description:


		**Parameters**

		app : Application
				Specification of an `Application <https://asab.readthedocs.io/en/latest/asab/application.html#>`_.

		id : default None

		config : JSON or other compatible format, default None
				It contains important information and data responsible for creating a connection.

		"""

		_id = id if id is not None else self.__class__.__name__
		super().__init__("connection:{}".format(_id), config=config)

		self.App = app
		self.Loop = app.Loop

		self.Id = _id


	def time(self):
		"""
		Returns accurate time of the asynchronous process.

		:hint: More information in the ASAB documentation in `UTC Time <https://asab.readthedocs.io/en/latest/asab/application.html#utc-time>`_.

		|

		"""
		return self.App.time()


	@classmethod
	def construct(cls, app, definition: dict):
		"""
		Creates a connection based on a specific definition. For example, a JSON file.

		**Parameters**

		app : Application
				ID of the `Application <https://asab.readthedocs.io/en/latest/asab/application.html#>_`.

		definition : definition format
				Defines instructions for the method that can be used to create a connection.


		:return: cls(app, newid, config)

		|

		"""
		newid = definition.get('id')
		config = definition.get('config')
		return cls(app, newid, config)
