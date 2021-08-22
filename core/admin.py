from django.contrib import admin
from .models import Bus, BusStop, Direction, YandexUser


admin.site.register(Bus)
admin.site.register(BusStop)
admin.site.register(Direction)
admin.site.register(YandexUser)
