"""Serve the reviewed OpenAPI document alongside the upstream REST routes."""

from django.http import FileResponse
from django.urls import path

from .urls import urlpatterns as upstream_urls


def openapi(request):
    return FileResponse(open("/code/openapi.yml", "rb"), content_type="application/yaml")


urlpatterns = [path("openapi.yml", openapi), *upstream_urls]
