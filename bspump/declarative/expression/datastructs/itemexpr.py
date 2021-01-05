from ...abc import Expression, evaluate

from ..value.eventexpr import EVENT
from ..value.eventexpr import KWARGS
from ..value.eventexpr import ARG
from ..value.valueexpr import VALUE
from ..utility.context import CONTEXT


class ITEM(Expression):
	"""
Get the item from a dictionary.

There are two forms:

1) Mapping form

!ITEM
with: !EVENT
item: foo
default: 0

2) Scalar form

!ITEM EVENT potatoes

Scalar form has some limitations (e.g no default value) but it is more compact
	"""

	def __init__(self, app, *, arg_with=None, arg_item=None, arg_default=None, value=None):
		super().__init__(app)

		if value is not None:
			# Scalar value provided
			with_, item = value.split(' ', 2)

			with_ = with_.upper()
			if with_ == 'EVENT':
				self.With = EVENT(app, value='')
			elif with_ == 'CONTEXT':
				self.With = CONTEXT(app, value='')
			elif with_ == 'KWARGS':
				self.With = KWARGS(app, value='')
			elif with_ == 'ARG':
				self.With = ARG(app, value='')
			else:
				raise RuntimeError("Invalid item argument '{}' - must be EVENT, CONTEXT, KWARGS, ARG", format(with_))

			self.Item = VALUE(app, value=item)
			self.Default = None

		else:
			self.With = arg_with
			self.Item = arg_item
			self.Default = arg_default


	def optimize(self):
		if isinstance(self.With, EVENT) and isinstance(self.Item, VALUE):
			return ITEM_optimized_EVENT_VALUE(
				self,
				arg_with=self.With,
				arg_item=self.Item,
				arg_default=self.Default
			)
		elif isinstance(self.With, CONTEXT) and isinstance(self.Item, VALUE):
			if "." in self.Item.Value:
				return ITEM_optimized_CONTEXT_VALUE_NESTED(
					self,
					arg_with=self.With,
					arg_item=self.Item,
					arg_default=self.Default
				)
			else:
				return ITEM_optimized_CONTEXT_VALUE(
					self,
					arg_with=self.With,
					arg_item=self.Item,
					arg_default=self.Default
				)
		return self


	def __call__(self, context, event, *args, **kwargs):
		with_dict = evaluate(self.With, context, event, *args, **kwargs)
		item = evaluate(self.Item, context, event, *args, **kwargs)

		try:
			return with_dict[item]

		except KeyError:
			if self.Default is None:
				return None
			return evaluate(self.Default, context, event, *args, **kwargs)

		except IndexError:
			if self.Default is None:
				return None
			return evaluate(self.Default, context, event, *args, **kwargs)


class ITEM_optimized_EVENT_VALUE(ITEM):

	def __init__(self, orig, *, arg_with, arg_item, arg_default):
		super().__init__(orig.App)

		self.With = arg_with
		self.Item = arg_item
		if arg_default is None:
			self.Default = arg_default
		else:
			# TODO: Default must be statically evaluated
			raise NotImplementedError("")

		self.Key = self.Item.Value


	def __call__(self, context, event, *args, **kwargs):
		return event.get(self.Key, self.Default)


class ITEM_optimized_CONTEXT_VALUE(ITEM):

	def __init__(self, orig, *, arg_with, arg_item, arg_default):
		super().__init__(orig.App)

		self.With = arg_with
		self.Item = arg_item
		if arg_default is None:
			self.Default = arg_default
		else:
			# TODO: Default must be statically evaluated
			raise NotImplementedError("")

		self.Key = self.Item.Value


	def __call__(self, context, event, *args, **kwargs):
		return context.get(self.Key, self.Default)


class ITEM_optimized_CONTEXT_VALUE_NESTED(ITEM):

	def __init__(self, orig, *, arg_with, arg_item, arg_default):
		super().__init__(orig.App)

		self.With = arg_with
		self.Item = arg_item
		if arg_default is None:
			self.Default = arg_default
		else:
			# TODO: Default must be statically evaluated
			raise NotImplementedError("")

		# TODO: Replace with JSON pointer path
		self.KeyList = self.Item.Value.split('.')


	def __call__(self, context, event, *args, **kwargs):
		value = context
		try:
			for key in self.KeyList:
				if isinstance(value, list):
					value = value[int(key)]
				else:
					value = value[key]
		except (TypeError, KeyError):
			return self.Default

		return value
