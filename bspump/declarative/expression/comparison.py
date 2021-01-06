import operator

from ..abc import SequenceExpression, Expression
from ..declerror import DeclarationError
from .value.valueexpr import VALUE
from .datastructs.itemexpr import ITEM, ITEM_optimized_EVENT_VALUE

from .value.eventexpr import EVENT
from .utility.context import CONTEXT


def _oper_reduce(operator, iterable, context, event, *args, **kwargs):
	it = iter(iterable)

	i = next(it)
	try:
		a = i(context, event, *args, **kwargs)
	except Exception as e:
		raise DeclarationError(original_exception=e, location=i.get_location())

	for i in it:

		try:
			b = i(context, event, *args, **kwargs)
		except Exception as e:
			raise DeclarationError(original_exception=e, location=i.get_location())

		if not operator(a, b):
			return False
		a = b

	return True


class LT(SequenceExpression):
	'''
	Operator '<'
	'''

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.lt, self.Items, context, event, *args, **kwargs)

	def get_outlet_type(self):
		return bool.__name__


class LE(SequenceExpression):
	'''
	Operator '<='
	'''

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.le, self.Items, context, event, *args, **kwargs)

	def get_outlet_type(self):
		return bool.__name__


class EQ(SequenceExpression):
	'''
	Operator '=='
	'''

	Attributes = {
		"Items": [
			'si64', 'si8', 'si16', 'si32', 'si64', 'si128', 'si256',
			'ui8', 'ui16', 'ui32', 'ui64', 'ui128', 'ui256',
			'str'
		]
	}

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.eq, self.Items, context, event, *args, **kwargs)


	def optimize(self):
		if len(self.Items) == 2 and isinstance(self.Items[1], VALUE):

			if isinstance(self.Items[0], ITEM_optimized_EVENT_VALUE):
				return EQ_optimized_EVENT_VALUE(self)

			# The nested objects may not be optimized yet when this parent optimization is called
			if isinstance(self.Items[0], ITEM):
				if isinstance(self.Items[0].With, EVENT) and isinstance(self.Items[0].Item, VALUE):
					return EQ_optimized_EVENT_VALUE(self)
				elif isinstance(self.Items[0].With, CONTEXT) and isinstance(self.Items[0].Item, VALUE) and "." in self.Items[0].Item.Value:
					# Skip nested context from optimization
					return None
				else:
					return EQ_optimized_simple(self)

		return None

	def get_outlet_type(self):
		return bool.__name__


	def get_items_inlet_type(self):
		# Find the first usable type in the items
		for item in self.Items:
			outlet_type = item.get_outlet_type()
			if outlet_type not in frozenset(['^']):
				return outlet_type
		raise NotImplementedError("Cannot decide on items inlet type '{}'".format(self))


	def consult_inlet_type(self, key, child):
		return self.get_items_inlet_type()


class EQ_optimized_simple(EQ):

	def __init__(self, orig):
		super().__init__(orig.App, sequence=orig.Items)
		self.A = self.Items[0]
		assert isinstance(self.A, Expression)

		assert isinstance(self.Items[1], VALUE)
		self.B = self.Items[1].Value
		assert isinstance(self.B, (bool, str, int, float))


	def __call__(self, context, event, *args, **kwargs):
		return self.A(context, event, *args, **kwargs) == self.B


	def optimize(self):
		return None


class EQ_optimized_EVENT_VALUE(EQ):

	# TODO: Attributes = [...]

	def __init__(self, orig):
		super().__init__(orig.App, sequence=orig.Items)
		self.Akey = self.Items[0].Item.Value
		self.Adefault = self.Items[0].Default.Value

		assert isinstance(self.Items[1], VALUE)
		self.B = self.Items[1].Value
		assert isinstance(self.B, (bool, str, int, float))


	def __call__(self, context, event, *args, **kwargs):
		return event.get(self.Akey, self.Adefault) == self.B


	def optimize(self):
		return None


class NE(SequenceExpression):
	'''
	Operator '!='
	'''

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.ne, self.Items, context, event, *args, **kwargs)

	def get_outlet_type(self):
		return bool.__name__


class GE(SequenceExpression):
	"""
	Operator '>='
	"""

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.ge, self.Items, context, event, *args, **kwargs)

	def get_outlet_type(self):
		return bool.__name__


class GT(SequenceExpression):
	"""
	Operator '>'
	"""

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.gt, self.Items, context, event, *args, **kwargs)

	def get_outlet_type(self):
		return bool.__name__


class IS(SequenceExpression):
	"""
	Operator 'is'
	"""

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.is_, self.Items, context, event, *args, **kwargs)

	def get_outlet_type(self):
		return bool.__name__


class ISNOT(SequenceExpression):
	"""
	Operator 'is not'
	"""

	def __call__(self, context, event, *args, **kwargs):
		return _oper_reduce(operator.is_not, self.Items, context, event, *args, **kwargs)

	def get_outlet_type(self):
		return bool.__name__
