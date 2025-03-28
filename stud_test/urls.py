"""stud_test URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

from django.views.generic import TemplateView
from drf_yasg.views import get_schema_view 
from drf_yasg import openapi 
from rest_framework import permissions

# Cache the admin index page

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="synaqtest api",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    url='https://api.sapatest.com/',
    # url=f'{settings.APP_URL}/api/v3/',
    patterns=[path('api/', include('api.urls')), ],
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [

    path(  # new
        'swagger-ui/',
        TemplateView.as_view(
            template_name='swaggerui/swaggerui.html',
            extra_context={'schema_url': 'openapi-schema'}
        ),
        name='swagger-ui'),
    path(  # new
        r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json'),

    path('admin/', admin.site.urls),
    path('statistics/', include('dashboard.urls')),
    path('test-logic/', include('test_logic.urls')),
    path('payments/', include('payments.urls')),
    path('api/', include('api.urls')),
    path('request/', include('test_request.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
