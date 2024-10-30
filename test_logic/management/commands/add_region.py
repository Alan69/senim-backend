import uuid
from django.core.management.base import BaseCommand
from accounts.models import Region  # Adjust the import path if needed

class Command(BaseCommand):
    help = 'Add predefined regions to the Region model.'

    # List of regions with their types (city or village)
    REGIONS = [
        ("Шымкент", Region.CITY),
        ("Алматинская область", Region.VILLAGE),
        ("Актюбинская область", Region.VILLAGE),
        ("Атырауская область", Region.VILLAGE),
        ("Акмолинская область", Region.VILLAGE),
        ("Западно-Казахстанская область", Region.VILLAGE),
        ("Восточно-Казахстанская область", Region.VILLAGE),
        ("Жамбылская область", Region.VILLAGE),
        ("Карагандинская область", Region.VILLAGE),
        ("Костанайская область", Region.VILLAGE),
        ("Кызылординская область", Region.VILLAGE),
        ("Мангистауская область", Region.VILLAGE),
        ("Северо-Казахстанская область", Region.VILLAGE),
        ("Павлодарская область", Region.VILLAGE),
        ("Туркестанская область", Region.VILLAGE),
        ("Область Абай", Region.VILLAGE),
        ("Область Жетісу", Region.VILLAGE),
        ("Область Ұлытау", Region.VILLAGE),
    ]

    def handle(self, *args, **kwargs):
        added_count = 0

        for name, region_type in self.REGIONS:
            if not Region.objects.filter(name=name).exists():
                # Create and save the region
                Region.objects.create(
                    id=uuid.uuid4(),
                    name=name,
                    region_type=region_type,
                    description=f"Регион {name}"
                )
                added_count += 1
                self.stdout.write(f"Added region: {name}")

        if added_count == 0:
            self.stdout.write("No new regions added. All regions already exist.")
        else:
            self.stdout.write(f"Successfully added {added_count} regions.")
