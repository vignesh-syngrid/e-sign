from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create-admin', views.create_admin, name='create_admin'),
    path('login/', views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('upload/', views.upload_document, name='upload_document'),

    path('signature/create/', views.create_signature, name='create_signature'),
    path('document/<uuid:document_id>/sign/', views.sign_document, name='sign_document'),
    path('document/<uuid:document_id>/sign/<uuid:invitation_token>/', views.sign_invited_document, name='sign_invited_document'),
    path('api/get-csrf/', views.get_csrf, name='get_csrf'),
    path('document/<uuid:document_id>/preview/', views.get_document_preview, name='document_preview'),
    path('document/<uuid:document_id>/preview/serve/', views.serve_document_preview, name='serve_document_preview'),
    path('document/<uuid:document_id>/delete/', views.delete_document, name='delete_document'),
    path('signature/<uuid:signature_id>/delete/', views.delete_signature, name='delete_signature'),
    path('api/apply-signature/', views.apply_signature, name='apply_signature'),
    path('download/<uuid:signed_doc_id>/', views.download_signed_document, name='download_signed_document'),
    path('download/<uuid:signed_doc_id>/<str:format>/', views.download_signed_document, name='download_signed_document_with_format'),
]