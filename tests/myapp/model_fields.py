import uuid

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Field
from django.utils import six
from django.utils.translation import ugettext_lazy as _

try:
    from django.db.models import UUIDField
except ImportError:
    class UUIDField(Field):
        """Emulate Django 1.8's django.db.models.fields.UUIDField."""
        default_error_messages = {
            'invalid': _("'%(value)s' is not a valid UUID."),
        }
        description = 'Universally unique identifier'
        empty_strings_allowed = False
    
        def __init__(self, **kwargs):
            kwargs['max_length'] = 32
            super(UUIDField, self).__init__(**kwargs)
    
        def db_type(self):
            # PostGres has a native uuid type
            if connection and 'postgres' in connection.vendor:
                return 'uuid'
            # All other database types are char()
            return 'char(%s)' % self.max_length
    
        def get_db_prep_value(self, value, connection, prepared=False):
            if isinstance(value, uuid.UUID):
                # This doesn't exist until Django 1.8 - wrap it in try: except
                try:
                    if connection.features.has_native_uuid_field:
                        return value
                except AttributeError:
                    return value.hex
            if isinstance(value, six.string_types):
                return value.replace('-', '')
            return value
    
        def to_python(self, value):
            if value and not isinstance(value, uuid.UUID):
                try:
                    return uuid.UUID(value)
                except ValueError:
                    raise exceptions.ValidationError(
                        self.error_messages['invalid'],
                        code='invalid',
                        params={'value': value},
                    )
            return value
    
        def formfield(self, **kwargs):
            try:
                from django.forms import UUIDField as UUIDFormField
            except ImportError:
                class UUIDFormField(CharField):
                    """Emulate Django 1.8's forms.UUIDField."""
                    default_error_messages = {
                        'invalid': _('Enter a valid UUID.'),
                    }
                
                    def prepare_value(self, value):
                        if isinstance(value, uuid.UUID):
                            return value.hex
                        return value
                
                    def to_python(self, value):
                        value = super(UUIDField, self).to_python(value)
                        if value in self.empty_values:
                            return None
                        if not isinstance(value, uuid.UUID):
                            try:
                                value = uuid.UUID(value)
                            except ValueError:
                                raise ValidationError(self.error_messages['invalid'], code='invalid')
                        return value

            defaults = {
                'form_class': UUIDFormField,
            }
            defaults.update(kwargs)
            return super(UUIDField, self).formfield(**defaults)
