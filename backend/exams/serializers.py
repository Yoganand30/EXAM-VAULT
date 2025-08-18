from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Request, FinalPapers, SubjectCode

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ["username", "password", "email", "first_name", "last_name", "course", "semester", "branch", "subject", "role"]

    def create(self, validated_data):
        pwd = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(pwd)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class SubjectCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectCode
        fields = ["id", "s_code", "subject"]

class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = ["id", "tusername", "s_code", "deadline", "status"]

class FinalPaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinalPapers
        fields = ["id", "s_code", "course", "semester", "branch", "subject", "paper"]
