from django.urls import path

from . import views

app_name = 'about'

urlpatterns = [
    path('author/', views.PageAuthor.as_view(), name='author'),
    path('tech/', views.PageTech.as_view(), name='tech'),
]
