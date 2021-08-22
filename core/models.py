from django.db import models
from django.contrib.postgres.fields import ArrayField

TIME_FORMATS = (
    ('time_interval', 'Time interval'),
    ('time', 'Time'),
)


class Bus(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Direction(models.Model):
    name = models.CharField(max_length=100)
    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='directions', blank=True, null=True)

    def __str__(self):
        return self.name


class BusStop(models.Model):
    name = models.CharField(max_length=100)
    direction = models.ForeignKey('Direction', on_delete=models.CASCADE, related_name='bus_stops', blank=True,
                                  null=True)
    schedule = ArrayField(models.DateTimeField(blank=True, null=True), blank=True, null=True)

    def __str__(self):
        return self.name


class YandexUser(models.Model):
    yandex_id = models.CharField(max_length=100)
    main_bus_stop = models.ForeignKey('BusStop', on_delete=models.CASCADE, related_name='+', blank=True, null=True)
    time_format = models.CharField(max_length=13, choices=TIME_FORMATS, default='time_interval')
