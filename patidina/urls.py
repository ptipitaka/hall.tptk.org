from django.urls import path

from . import views

app_name = "patidina"

urlpatterns = [
    path("", views.PatidinaWidgetView.as_view(), name="widget"),
    path("lunar-date-widget/", views.LunarDateWidgetView.as_view(), name="lunar_date_widget"),
    path("solar-date-widget/", views.SolarDateWidgetView.as_view(), name="solar_date_widget"),
    path("moon-phase-widget/", views.MoonPhaseWidgetView.as_view(), name="moon_phase_widget"),
    path(
        "calendar/<int:y>/<int:m>/",
        views.BuddhistCalendarWidgetView.as_view(),
        name="calendar",
    ),
    path(
        "uposatha/",
        views.UposathaDatesWidgetView.as_view(),
        name="uposatha",
    ),
    path(
        "uposatha/<int:y>/",
        views.UposathaDatesWidgetView.as_view(),
        name="uposatha_year",
    ),
]
