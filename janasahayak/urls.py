from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # App routes (HTML + REST API)
    path('', include('core.urls')),

    # OpenAPI schema download endpoint
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),

    # Swagger UI  ← open this in browser to explore the API
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
