import json
import yaml
import importlib
import glob
import os
import logging

import asab

import bspump.analyzer

##

L = logging.getLogger(__name__)

##

asab.Config.add_defaults(
	{
		"SegmentBuilder": {
			"path": "./etc/processors/*",
		},
	}
)


class SegmentBuilder(object):
	"""
	SegmentBuilder is meant to add a new segment to the pipeline,
	that consists of processors such as enrichers, analyzers etc.

	Usage:

		self.SegmentBuilder = bspump.declarative.SegmentBuilder()
		self.SegmentBuilder.construct_segment(self)

	The configuration file:

		pipeline_id: AnalyticsIPPipeline
		processor: |
			--- !DICT
			with: !EVENT
			add:
				local_ip:
					!IF
					is:
						!INSUBNET
						subnet: 192.168.0.0/16
						value:
							!ITEM
							with: !EVENT
							item: CEF.sourceAddress
					then: true
					else: false
	"""

	KEYWORDS = {
		"processor": ("bspump.declarative", "DeclarativeProcessor")
	}

	def __init__(self):
		self.Path = asab.Config["SegmentBuilder"]["path"]
		self.DefinitionsLookups = []
		self.DefinitionsProcessors = []
		file_list = glob.glob(self.Path, recursive=True)
		while len(file_list) > 0:
			file_name = file_list.pop(0)
			if os.path.isfile(file_name):
				with open(file_name) as file:
					if file_name.endswith(".yml"):
						# Read YML file
						definition = yaml.load(file)
					else:
						# Read JSON file
						definition = json.load(file)
					if definition.get("lookup") is not None or definition.get("class", "").endswith("Lookup"):
						self.DefinitionsLookups.append(definition)
					else:
						self.DefinitionsProcessors.append(definition)

	def register_keyword(self, keyword, _module, _class):
		self.KEYWORDS[keyword] = (_module, _class)

	def map_keyword(self, definition):
		for keyword in self.KEYWORDS:
			if keyword in definition:
				_module, _class = self.KEYWORDS[keyword]
				definition["declaration"] = definition[keyword]
				definition["module"] = _module
				definition["class"] = _class
		return definition

	def construct_segment(self, app):
		svc = app.get_service("bspump.PumpService")

		# First create lookups
		for definition in self.DefinitionsLookups:
			pipeline = svc.locate(definition["pipeline_id"])
			lookup = self.construct_lookup(app, pipeline, self.map_keyword(definition))
			svc.add_lookup(lookup)

		# Then create other processors
		for definition in self.DefinitionsProcessors:
			pipeline = svc.locate(definition["pipeline_id"])
			processor = self.construct_processor(app, pipeline, self.map_keyword(definition))
			if processor is not None:
				sink = pipeline.Processors[-1].pop()
				pipeline.append_processor(processor)
				pipeline.append_processor(sink)
				self.build_profiling(pipeline, processor)

	def construct_lookup(self, app, pipeline, definition):
		_module = importlib.import_module(definition["module"])
		_class = getattr(_module, definition["class"])
		lookup = _class.construct(app, definition)
		return lookup

	def construct_processor(self, app, pipeline, definition):
		_module = importlib.import_module(definition["module"])
		_class = getattr(_module, definition["class"])
		processor = _class.construct(app, pipeline, definition)
		return processor

	def build_profiling(self, pipeline, processor):
		pipeline.ProfilerCounter[processor.Id] = pipeline.MetricsService.create_counter(
			'bspump.pipeline.profiler',
			tags={
				'processor': processor.Id,
				'pipeline': pipeline.Id,
			},
			init_values={'duration': 0.0, 'run': 0},
			reset=pipeline.ResetProfiler,
		)
		if isinstance(processor, bspump.analyzer.Analyzer):
			pipeline.ProfilerCounter['analyzer_' + processor.Id] = pipeline.MetricsService.create_counter(
				'bspump.pipeline.profiler',
				tags={
					'analyzer': processor.Id,
					'pipeline': pipeline.Id,
				},
				init_values={'duration': 0.0, 'run': 0},
				reset=pipeline.ResetProfiler,
			)
