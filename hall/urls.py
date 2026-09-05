from coderedcms import admin_urls as crx_admin_urls
from coderedcms import search_urls as crx_search_urls
from coderedcms import urls as crx_urls
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(crx_admin_urls)),
    path("docs/", include(wagtaildocs_urls)),
    path("search/", include(crx_search_urls)),
]

if settings.WAGTAIL_I18N_ENABLED:
    urlpatterns += i18n_patterns(
        path("", include(crx_urls)),
        prefix_default_language=False,
    )
else:
    urlpatterns += [
        path("", include(crx_urls)),
    ]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
