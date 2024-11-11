from rest_framework import serializers
from .models import RequestTest

class RequestTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestTest
        fields = '__all__'