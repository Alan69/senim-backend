from django.contrib import admin
from .models import Test, Question, Option, Result, BookSuggestion, Product, CompletedTest, CompletedQuestion, Source
from accounts.models import User
from django.contrib import messages

class OptionInline(admin.TabularInline):
    model = Option
    extra = 1

class TestFilter(admin.SimpleListFilter):
    title = 'Test'
    parameter_name = 'test'

    def lookups(self, request, model_admin):
        """
        Display a dropdown of Tests in the filter.
        Dynamically show only Tests associated with the selected Product.
        """
        product_id = request.GET.get('test__product__id__exact')  # Get selected product filter
        if product_id:
            tests = Test.objects.filter(product_id=product_id)
        else:
            tests = Test.objects.all()
        return [(test.id, test.title) for test in tests]

    def queryset(self, request, queryset):
        """
        Filter the queryset based on the selected Test.
        """
        if self.value():
            return queryset.filter(test_id=self.value())
        return queryset


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'test', 'task_type', 'get_product')
    search_fields = ('text', 'test__title', 'test__product__title')
    list_filter = ('test__product', TestFilter)  # Add TestFilter while keeping Product filter
    inlines = [OptionInline]

    def get_product(self, obj):
        """
        Display the Product related to the Question via the Test relationship.
        """
        return obj.test.product.title if obj.test and obj.test.product else 'N/A'

    get_product.short_description = 'Product'


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

    @admin.action(description='Delete Questions with no text')
    def delete_empty_text_questions(self, request, queryset):
        deleted, _ = Question.objects.filter(text__isnull=True).delete()
        messages.success(request, f'Successfully deleted {deleted} question(s) with no text.')

    actions = [delete_empty_text_questions]


class TestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'number_of_questions', 'score', 'grade', 'date_created', 'product')
    search_fields = ('id', 'title', 'product__title', 'grade')
    list_filter = ('date_created', 'product')
    inlines = [QuestionInline]

class ResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'test', 'student', 'score', 'created', 'is_correct')
    search_fields = ('student__username', 'test__title')
    list_filter = ('created', 'is_correct')

class BookSuggestionAdmin(admin.ModelAdmin):
    list_display = ('book_title', 'question')
    search_fields = ('book_title', 'question__text')
    list_filter = ('question',)

class SourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'text')
    search_fields = ('text',)
    
class CompletedTestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'completed_date', 'start_test_time', 'time_spent')
    search_fields = ('user__username', 'product__title')
    list_filter = ('completed_date', 'start_test_time')

admin.site.register(Product)
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Result, ResultAdmin)
admin.site.register(BookSuggestion, BookSuggestionAdmin)
admin.site.register(CompletedTest, CompletedTestAdmin)
admin.site.register(CompletedQuestion)
admin.site.register(Source, SourceAdmin)