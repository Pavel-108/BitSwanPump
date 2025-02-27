import csv
import logging
import os

from ..abc.sink import Sink

#

L = logging.getLogger(__file__)


#

class FileCSVSink(Sink):
	"""
	Description:

	** Default Config**

	path : ''

	dialect : 'excel'

	delimiter : ','

	doublequote : True

	escapechar : ""

	lineterminator : os.linesep

	quotechar : '"'

	quoting : csv.QUOTE_MINIMAL

	skipinitialspace : False

	strict : False

	"""
	ConfigDefaults = {
		'path': '',
		'dialect': 'excel',
		'delimiter': ',',
		'doublequote': True,
		'escapechar': "",
		'lineterminator': os.linesep,
		'quotechar': '"',
		'quoting': csv.QUOTE_MINIMAL,  # 0 - 3 for [QUOTE_MINIMAL, QUOTE_ALL, QUOTE_NONNUMERIC, QUOTE_NONE]
		'skipinitialspace': False,
		'strict': False,
	}

	def __init__(self, app, pipeline, id=None, config=None):
		"""
		Description:

		"""
		super().__init__(app, pipeline, id=id, config=config)
		self.Dialect = csv.get_dialect(self.Config['dialect'])
		self._csv_writer = None

	def get_file_name(self, context, event):
		"""
		Description: Override this method to gain control over output file name.

		**Parameters**

		context :

		event :

		:return: path of context and config

		|

		"""
		# Here we are able to modify the sink behavior from outside using context.
		# If provided, the filename (and path) is taken from the context instead of the config
		return context.get("path", self.Config["path"])

	def writer(self, f, fieldnames):
		"""
		Description:

		**Parameters**

		f :

		fieldnames : file
			Name of the file.

		:return: dialect and fieldnames

		|

		"""
		kwargs = dict()

		kwargs['delimiter'] = self.Config.get('delimiter')
		kwargs['doublequote'] = bool(self.Config.get('doublequote'))

		escape_char = self.Config.get('escapechar')
		escape_char = None if escape_char == "" else escape_char
		kwargs['escapechar'] = escape_char

		kwargs['lineterminator'] = self.Config.get('lineterminator')
		kwargs['quotechar'] = self.Config.get('quotechar')
		kwargs['quoting'] = int(self.Config.get('quoting'))
		kwargs['skipinitialspace'] = bool(self.Config.get('skipinitialspace'))
		kwargs['strict'] = bool(self.Config.get('strict'))

		return csv.DictWriter(
			f,
			dialect=self.Dialect,
			fieldnames=fieldnames,
			**kwargs
		)

	def process(self, context, event):
		"""
		Description:

		**Parameters**

		context :

		event : any data type
			Information with timestamp.

		"""
		if self._csv_writer is None:
			# Open CSV file if needed
			fieldnames = event.keys()
			fname = self.get_file_name(context, event)
			self.fd = open(fname, 'w', newline='')
			self._csv_writer = self.writer(self.fd, fieldnames)
			self._csv_writer.writeheader()

		self._csv_writer.writerow(event)
		self.fd.flush()

	def rotate(self):
		"""
		Description: Call this to close the currently open file.

		"""
		del self._csv_writer
		self._csv_writer = None
