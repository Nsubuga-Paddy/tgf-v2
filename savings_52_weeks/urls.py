from django.urls import path
from . import views

app_name = 'savings_52_weeks'

urlpatterns = [
    path("", views.group_dashboard, name="group_dashboard"),
    path("52wsc-member-dashboard/", views.member_savings, name="member_dashboard"),
    path("52wsc-report/", views.report, name="report"),
    path("52wsc-chat-room/", views.chat_room, name="chat_room"),
]
