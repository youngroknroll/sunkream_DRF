from rest_framework import serializers


class KakaoLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()
