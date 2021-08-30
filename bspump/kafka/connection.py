import logging
import re

import aiokafka

from ..abc.connection import Connection

#

L = logging.getLogger(__name__)

#


class KafkaConnection(Connection):
	"""
	KafkaConnection serves to connect BSPump application with an instance of Apache Kafka messaging system.
	It can later be used by processors to consume or provide user-defined messages.

.. code:: python

	config = {"compression_type": "gzip"}
	app = bspump.BSPumpApplication()
	svc = app.get_service("bspump.PumpService")
	svc.add_connection(
		bspump.kafka.KafkaConnection(app, "KafkaConnection", config)
	)

..


	``ConfigDefaults`` options:

		compression_type (str): Kafka supports several compression types: ``gzip``, ``snappy`` and ``lz4``.
			This option needs to be specified in Kafka Producer only, Consumer will decompress automatically.
		security_protocol (str): Protocol used to communicate with brokers.
			Valid values are: PLAINTEXT, SSL. Default: PLAINTEXT.
		sasl_mechanism (str): Authentication mechanism when security_protocol
			is configured for SASL_PLAINTEXT or SASL_SSL. Valid values are:
			PLAIN, GSSAPI, SCRAM-SHA-256, SCRAM-SHA-512. Default: PLAIN
		sasl_plain_username (str): username for sasl PLAIN authentication.
			Default: None
		sasl_plain_password (str): password for sasl PLAIN authentication.
			Default: None
	"""

	ConfigDefaults = {
		'bootstrap_servers': 'localhost:9092',  # One or more URLs separated by whitespace or semicolon
		'compression_type': '',
		'security_protocol': 'PLAINTEXT',
		'sasl_mechanism': 'PLAIN',
		'sasl_plain_username': '',
		'sasl_plain_password': '',
	}

	def __init__(self, app, id=None, config=None):
		"""
		initializes variables

		**Parameters**

		app : Application
			Name of the `Application <https://asab.readthedocs.io/en/latest/asab/application.html#>`_.

		id :  , default = None
			ID information.

		config : JSON or txt, default= None
			Configuration file of any supported type.

		"""
		super().__init__(app, id=id, config=config)
		self.Loop = app.Loop

	async def create_producer(self, **kwargs):
		"""
		Creates a Producer.

		**Parameters**

		**kwargs :
			Additional information can be passed to this method.

		:returns: producer

		|

		"""
		producer = aiokafka.AIOKafkaProducer(
			loop=self.Loop,
			bootstrap_servers=self.get_bootstrap_servers(),
			compression_type=self.get_compression(),
			security_protocol=self.Config.get('security_protocol'),
			sasl_mechanism=self.Config.get('sasl_mechanism'),
			sasl_plain_username=self.Config.get('sasl_plain_username') or None,
			sasl_plain_password=self.Config.get('sasl_plain_password') or None,
			**kwargs
		)
		return producer

	def create_consumer(self, *topics, **kwargs):
		"""
		Creates a consumer.

		**Parameters**

		*topics :
			any number of topics can be passed to this method.

		**kwargs :
			additional information can be passed to this method.


		:returns: consumer

		|

		"""
		consumer = aiokafka.AIOKafkaConsumer(
			*topics,
			loop=self.Loop,
			bootstrap_servers=self.get_bootstrap_servers(),
			enable_auto_commit=False,
			security_protocol=self.Config.get('security_protocol'),
			sasl_mechanism=self.Config.get('sasl_mechanism'),
			sasl_plain_username=self.Config.get('sasl_plain_username') or None,
			sasl_plain_password=self.Config.get('sasl_plain_password') or None,
			**kwargs
		)
		return consumer

	def get_bootstrap_servers(self):
		"""
		Returns parsed bootstrap servers found in config.

		:returns: list of url

		|

		"""
		return [
			url for url
			in re.split(r"[\s;]+", self.Config['bootstrap_servers'])
			if url
		]

	def get_compression(self):
		"""
		Returns compression type to use in connection

		:returns: compression_type

		|

		"""
		compression_type = self.Config.get("compression_type")
		if compression_type in ("", "none", "None"):
			compression_type = None
		return compression_type
