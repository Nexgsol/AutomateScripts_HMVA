from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.http import JsonResponse
from django.urls import path, include

def health(_): return JsonResponse({"ok": True})

urlpatterns = [ path("admin/", admin.site.urls),
                path("", include("core.urls")),
                path("api/", include("core.urls")),
                path("healthz/", health),
                ]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
