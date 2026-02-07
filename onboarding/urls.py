
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [


    # ПРАВИЛЬНО: путь в кавычках как строка
    path('api/content/', include('content.urls')),

    # CKEditor обычно подключается здесь, в главном файле
    path('ckeditor/', include('ckeditor_uploader.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)