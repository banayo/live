from django.urls import path

from . import views

app_name = "booking"

urlpatterns = [
    path("api/auth/me/", views.auth_me, name="auth_me"),
    path("api/auth/register/", views.auth_register, name="auth_register"),
    path("api/auth/login/", views.auth_login, name="auth_login"),
    path("api/auth/logout/", views.auth_logout, name="auth_logout"),
    path("api/auth/line/authorize/", views.line_authorize, name="line_authorize"),
    path("api/auth/line/callback/", views.line_callback, name="line_callback"),
    path("api/backoffice/auth-check/", views.backoffice_auth_check, name="backoffice_auth_check"),
    path("api/backoffice/users/", views.backoffice_users_list, name="backoffice_users_list"),
    path("api/backoffice/users/<int:user_id>/", views.backoffice_user_update, name="backoffice_user_update"),
    path("api/backoffice/brands/", views.backoffice_brands_list, name="backoffice_brands_list"),
    path("api/backoffice/brands/create/", views.backoffice_brand_create, name="backoffice_brand_create"),
    path("api/backoffice/brands/<int:brand_id>/", views.backoffice_brand_update, name="backoffice_brand_update"),
    path("api/backoffice/channels/", views.backoffice_channels_list, name="backoffice_channels_list"),
    path("api/backoffice/channels/create/", views.backoffice_channel_create, name="backoffice_channel_create"),
    path("api/backoffice/channels/<int:channel_id>/", views.backoffice_channel_update, name="backoffice_channel_update"),
    path("api/schedules/", views.live_schedule_feed, name="live_schedule_feed"),
    path("api/user/book-live-options/", views.user_book_live_options, name="user_book_live_options"),
    path("api/user/live-schedules/", views.user_live_schedule_create, name="user_live_schedule_create"),
]

