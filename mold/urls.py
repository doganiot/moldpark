from django.urls import path
from . import views

app_name = 'mold'

urlpatterns = [
    path('', views.mold_list, name='mold_list'),
    path('create/', views.mold_create, name='mold_create'),
    path('<int:pk>/', views.mold_detail, name='mold_detail'),
    path('<int:pk>/edit/', views.mold_edit, name='mold_edit'),
    path('<int:pk>/delete/', views.mold_delete, name='mold_delete'),
    path('<int:pk>/revision/', views.revision_create, name='revision_create'),
    path('<int:pk>/quality/', views.quality_check, name='quality_check'),
    path('<int:mold_id>/upload-model/', views.upload_model, name='upload_model'),
    path('model/<int:pk>/delete/', views.delete_modeled_mold, name='delete_modeled_mold'),
    
    # Revizyon Talepleri
    path('revision-request/create/', views.revision_request_create, name='revision_request_create'),
    path('<int:mold_id>/revision-request/', views.revision_request_create, name='revision_request_create_for_mold'),
    path('revision-requests/', views.revision_request_list, name='revision_request_list'),
    path('revision-request/<int:pk>/', views.revision_request_detail, name='revision_request_detail'),
    
    # Kalıp Değerlendirmeleri
    path('<int:mold_id>/evaluate/', views.mold_evaluation_create, name='mold_evaluation_create'),
    path('evaluation/<int:pk>/edit/', views.mold_evaluation_edit, name='mold_evaluation_edit'),
    path('evaluations/', views.mold_evaluation_list, name='mold_evaluation_list'),
] 