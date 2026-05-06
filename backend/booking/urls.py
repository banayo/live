from django.urls import path

from . import views

app_name = "booking"

urlpatterns = [
    path("api/schedules/", views.live_schedule_feed, name="live_schedule_feed"),
]

