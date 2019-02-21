import abc
import os
import logging
import asyncio
import asab

from ..abc.source import TriggerSource
from .. import ProcessingError

from .globscan import _glob_scan, _file_check

#

L = logging.getLogger(__file__)

#

class FileABCSource(TriggerSource):


	ConfigDefaults = {
		'path': '',
		'mode': 'rb',
		'newline': None,
		'post': 'move', # one of 'delete', 'noop' and 'move'
		'exclude': '', # glob of filenames that should be excluded (has precedence over 'include')
		'include': '', # glob of filenames that should be included
		'encoding': '',
		'processed_period': 5*60
	}


	def __init__(self, app, pipeline, id=None, config=None):
		super().__init__(app, pipeline, id=id, config=config)

		self.path = self.Config['path']
		self.mode = self.Config['mode']
		self.newline = self.Config['newline']
		self.post = self.Config['post']
		if self.post not in ['delete', 'noop', 'move']:
			L.warning("Incorrect/unknown 'post' configuration value '{}' - defaulting to 'move'".format(self.post))
			self.post = 'move'
		self.include = self.Config['include']
		self.exclude = self.Config['exclude']
		self.encoding = self.Config['encoding']

		metrics_service = app.get_service('asab.MetricsService')

		self.Gauge = metrics_service.create_gauge("processed_files_percentage",
			tags = {
				'pipeline': pipeline.Id,
			},
			init_values = {
				"processed": 0,
				"failed" : 0,
				"locked": 0,
				"unprocessed": 0,
				"all_files" : 0,
			}
		)
		# 
		self.Timer = asab.Timer(app, self.on_tick, autorestart=True)
		self.Timer.start(self.Config['processed_period'])

	
	async def on_tick(self):
		file_count = {
			"processed": 0,
			"unprocessed": 0,
			"failed": 0, 
			"locked" : 0,
			"all_files": 0
		}

		for path in self.path.split(os.pathsep):
			_file_check(path, file_count)

		if file_count["all_files"] == 0:
			return

		self.Gauge.set("processed", file_count["processed"])
		self.Gauge.set("failed", file_count["failed"])
		self.Gauge.set("locked", file_count["locked"])
		self.Gauge.set("unprocessed", file_count["unprocessed"])
		self.Gauge.set("all_files", file_count["all_files"])
		


	async def cycle(self):
		filename = None

		for path in self.path.split(os.pathsep):
			filename = _glob_scan(path, exclude=self.exclude, include=self.include)
			if filename is not None:
				break

		if filename is None:
			self.Pipeline.PubSub.publish("bspump.file_source.no_files!")
			return  # No file to read

		await self.Pipeline.ready()

		# Lock the file
		L.debug("Locking file '{}'".format(filename))
		locked_filename = filename + '-locked'
		try:
			os.rename(filename, locked_filename)
		except FileNotFoundError:
			return
		except BaseException as e:
			L.exception("Error when locking the file '{}'".format(filename))
			self.Pipeline.set_error(None, None, e)
			return

		try:
			if filename.endswith(".gz"):
				import gzip
				f = gzip.open(locked_filename, self.mode)

			elif filename.endswith(".bz2"):
				import bz2
				f = bz2.open(locked_filename, self.mode)

			elif filename.endswith(".xz") or filename.endswith(".lzma"):
				import lzma
				f = lzma.open(locked_filename, self.mode)

			else:
				f = open(locked_filename, self.mode, newline=self.newline,
						encoding=self.encoding if len(self.encoding) > 0 else None)

		except BaseException as e:
			L.exception("Error when opening the file '{}'".format(filename))
			self.Pipeline.set_error(None, None, e)
			return

		L.debug("Processing file '{}'".format(filename))

		try:
			await self.read(filename, f)
		except Exception as e:
			try:
				if self.post == "noop":
					# When we should stop, rename file back to original
					os.rename(locked_filename, filename)
				else:
					# Otherwise rename to ...-failed and continue processing
					os.rename(locked_filename, filename + '-failed')
			except:
				L.exception("Error when finalizing the file '{}'".format(filename))
			return
		finally:
			f.close()

		L.debug("File '{}' processed {}".format(filename, "succefully"))

		# Finalize
		try:
			if self.post == "delete":
				os.unlink(locked_filename)
			elif self.post == "noop":
				os.rename(locked_filename, filename)
			else:
				os.rename(locked_filename, filename + '-processed')
		except BaseException as e:
			L.exception("Error when finalizing the file '{}'".format(filename))
			self.Pipeline.set_error(None, None, e)
			return


	@abc.abstractmethod
	async def read(self, filename, f):
		'''
		Override this method to implement your File Source.
		`f` is an opened file object.
		'''
		raise NotImplemented()
