from rest_framework import serializers
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from .models import Region
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        
        return token

    def validate(self, attrs):
        # Custom authentication logic to ensure correct user is fetched
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            from django.contrib.auth.models import User
            raise AuthenticationFailed('No active account found with the given credentials')
        
        self.user = user
        # Continue with token generation and user data
        token = super().validate(attrs)
        print(f"Authenticated user: {self.user.username}")  # Debug log
        print(f"User ID: {self.user.id}")  # Add this to see the user ID
        
        # Check if the username that was supplied matches the authenticated user
        if attrs.get('username') != self.user.username:
            print(f"WARNING: Username mismatch! Supplied: {attrs.get('username')}, Authenticated: {self.user.username}")
        
        # Add user data to response
        token['user_data'] = {
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'region': str(self.user.region) if self.user.region else None,
            'school': self.user.school,
            'phone_number': self.user.phone_number,
            'balance': str(self.user.balance),
            'referral_link': self.user.referral_link,
            'referral_bonus': str(self.user.referral_bonus),
            'test_is_started': self.user.test_is_started,
            'is_student': self.user.is_student,
            'is_teacher': self.user.is_teacher
        }
        
        return token

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    region = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), required=False, allow_null=True)
    user_type = serializers.ChoiceField(choices=User.UserType.choices, required=True)
    grade = serializers.ChoiceField(choices=User.Grade.choices, required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'password', 'password2', 'region', 'school', 'user_type', 'grade')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        # Validate that students must select a grade
        if attrs.get('user_type') == User.UserType.STUDENT and not attrs.get('grade'):
            raise serializers.ValidationError({"grade": "Students must select a grade."})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password2', None)
        user_type = validated_data.pop('user_type', User.UserType.STUDENT)
        grade = validated_data.pop('grade', None)
        
        # Set appropriate flags based on user_type
        is_student = user_type == User.UserType.STUDENT
        is_teacher = user_type == User.UserType.TEACHER
        
        # Create the user with other fields
        user = User.objects.create(
            **validated_data,
            is_student=is_student,
            is_teacher=is_teacher,
            user_type=user_type,
            grade=grade
        )
        
        # Set the password
        user.set_password(password)
        user.save()

        return user

class UserSerializer(serializers.ModelSerializer):
    region = RegionSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'region', 'school', 'balance', 'is_staff', 'is_student', 'is_teacher', 'is_principal', 'test_is_started', 'user_type', 'grade']
        read_only_fields = ['id', 'balance', 'is_staff', 'is_student', 'is_teacher', 'is_principal']

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password2 = serializers.CharField(write_only=True, required=True)

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'region_type', 'description']

class UserPUTSerializer(serializers.ModelSerializer):
    # region = RegionSerializer()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'region', 'school', 'referral_link', 'referral_bonus']
        # read_only_fields = ['email']  # Email should not be updated in your form.
