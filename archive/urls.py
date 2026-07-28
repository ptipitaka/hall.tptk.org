"""Citation URL routes (mounted under /cite/)."""

from django.urls import path

from archive import views

app_name = "archive"

urlpatterns = [
    path(
        "<str:collection_code>/<str:edition_code>/<str:cref>/",
        views.cite_edition,
        name="cite_edition",
    ),
    path("<str:token>/", views.cite, name="cite"),
]
