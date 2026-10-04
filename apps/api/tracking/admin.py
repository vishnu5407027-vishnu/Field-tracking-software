from django.contrib import admin

from .models import Geofence, GeofenceEvent, LocationLog, Shift

admin.site.register(Shift)
admin.site.register(Geofence)
admin.site.register(GeofenceEvent)
admin.site.register(LocationLog)
