from ...abc import Expression


class EVENT(Expression):
	"""
	Returns a current event:

	"""

	def __init__(self, app, *, value):
		super().__init__(app)
		assert(value == "")

	def __call__(self, context, event, *args, **kwargs):
		return event
