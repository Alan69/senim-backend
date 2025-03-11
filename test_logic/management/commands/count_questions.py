from django.core.management.base import BaseCommand
from test_logic.models import Product, Test, Question
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Count questions by each Test and Tests by each Product'

    def handle(self, *args, **kwargs):
        # Check if Question model has grade field
        has_grade_field = hasattr(Question, 'grade')
        if not has_grade_field:
            self.stdout.write(self.style.WARNING("Warning: Question model does not have a 'grade' field"))
        
        products = Product.objects.all()

        for product in products:
            self.stdout.write(f"\nProduct: {product.title}")
            tests = Test.objects.filter(product=product)

            for test in tests:
                questions = Question.objects.filter(test=test)
                question_count = questions.count()
                
                # Calculate test grade using more efficient approach
                if has_grade_field:
                    # Try to get the sum using database aggregation
                    total_grade = questions.aggregate(Sum('grade'))['grade__sum'] or 0
                    
                    # If grade is still 0, check a sample of questions to diagnose
                    if total_grade == 0 and question_count > 0:
                        sample = questions[:5]  # Check first 5 questions
                        sample_info = [f"Q{q.id}: grade={getattr(q, 'grade', None)}" for q in sample]
                        self.stdout.write(f"    Sample questions: {', '.join(sample_info)}")
                else:
                    total_grade = 0
                
                self.stdout.write(f"  Test: {test.title} - {question_count} questions, Total Grade: {total_grade}")
