from django.urls import path

from . import views

urlpatterns = [
    path('', views.MainView.as_view(), name='index'),
    path('update_db', views.update_db, name='update_db'),
    # path('schedule/<bus>/<direction>/<bus_stop>', views.get_schedule1, name='schedule'),
    # path('schedule2/<bus>/<guiding_bus_stop>/<bus_stop>', views.get_schedule2, name='schedule'),
]
