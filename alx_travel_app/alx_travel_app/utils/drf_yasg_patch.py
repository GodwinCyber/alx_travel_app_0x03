from drf_yasg.inspectors import FieldInspector

class SkipEncoderInspector(FieldInspector):
    """
    Custom FieldInspector to skip the 'encoder' argument
    which DRF >=3.15 does not support.
    """

    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        # Remove unsupported 'encoder' kwarg if present
        if 'encoder' in kwargs:
            kwargs.pop('encoder')
        # Return None to pass the field to the next inspector in the chain
        return None
