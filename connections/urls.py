from django.urls import path
from .views import ConnectionsListView, ConnectProviderView, DisconnectProviderView

urlpatterns = [
    path("", ConnectionsListView.as_view(), name="connections-list"),
    path("<str:provider>/connect/", ConnectProviderView.as_view(), name="connections-connect"),
    path("<str:provider>/disconnect/", DisconnectProviderView.as_view(), name="connections-disconnect"),
]
