from django.contrib import admin
from .models import Test, Question, Option, Result, BookSuggestion, Product, CompletedTest, CompletedQuestion
from accounts.models import User

class OptionInline(admin.TabularInline):
    model = Option
    extra = 1

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'test')
    inlines = [OptionInline]

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class TestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'number_of_questions', 'score', 'date_created')
    search_fields = ('title', 'created_by__username')
    list_filter = ('date_created',)
    inlines = [QuestionInline]

class ResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'student', 'score', 'created', 'is_correct')
    search_fields = ('student__username', 'test__title')
    list_filter = ('created', 'is_correct')

class BookSuggestionAdmin(admin.ModelAdmin):
    list_display = ('book_title', 'question')
    search_fields = ('book_title', 'question__text')
    list_filter = ('question',)

admin.site.register(Product)
admin.site.register(Test, TestAdmin)
# admin.site.register(Question, QuestionAdmin)
admin.site.register(Result, ResultAdmin)
admin.site.register(BookSuggestion, BookSuggestionAdmin)
admin.site.register(CompletedTest)
admin.site.register(CompletedQuestion)
