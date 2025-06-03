from django.core.management.base import BaseCommand
from cases.models import Court

class Command(BaseCommand):
    help = 'Загружает начальные данные судов'

    def handle(self, *args, **options):
        courts_data = [
            # Верховный суд РФ
            {
                'name': 'Верховный Суд Российской Федерации',
                'court_type': 'supreme',
                'region': 'Москва',
                'address': 'ул. Поварская, д. 15, Москва, 121260'
            },
            
            # Конституционный суд РФ
            {
                'name': 'Конституционный Суд Российской Федерации',
                'court_type': 'constitutional',
                'region': 'Санкт-Петербург',
                'address': 'Сенатская пл., д. 1, Санкт-Петербург, 190000'
            },
            
            # Арбитражные суды
            {
                'name': 'Арбитражный суд города Москвы',
                'court_type': 'arbitration',
                'region': 'Москва',
                'address': 'ул. Салтыковская, д. 12, Москва, 105066'
            },
            {
                'name': 'Арбитражный суд Московской области',
                'court_type': 'arbitration',
                'region': 'Московская область',
                'address': 'ул. Палиха, д. 13А, стр. 2, Москва, 123022'
            },
            {
                'name': 'Арбитражный суд Санкт-Петербурга и Ленинградской области',
                'court_type': 'arbitration',
                'region': 'Санкт-Петербург',
                'address': 'ул. Смольного, д. 3, Санкт-Петербург, 191060'
            },
            {
                'name': 'Первый арбитражный апелляционный суд',
                'court_type': 'arbitration',
                'region': 'Москва',
                'address': 'ул. Театральная, д. 5, Москва, 109012'
            },
            {
                'name': 'Второй арбитражный апелляционный суд',
                'court_type': 'arbitration',
                'region': 'Санкт-Петербург',
                'address': 'ул. Смольного, д. 3, Санкт-Петербург, 191060'
            },
            
            # Суды общей юрисдикции Москвы
            {
                'name': 'Тверской районный суд города Москвы',
                'court_type': 'general',
                'region': 'Москва',
                'address': 'ул. Огородная слобода, д. 5, Москва, 101000'
            },
            {
                'name': 'Басманный районный суд города Москвы',
                'court_type': 'general',
                'region': 'Москва',
                'address': 'ул. Каланчевская, д. 26, стр. 1, Москва, 107078'
            },
            {
                'name': 'Хамовнический районный суд города Москвы',
                'court_type': 'general',
                'region': 'Москва',
                'address': 'ул. Льва Толстого, д. 5, стр. 3, Москва, 119021'
            },
            {
                'name': 'Московский городской суд',
                'court_type': 'general',
                'region': 'Москва',
                'address': 'ул. Богданка, д. 2, Москва, 109012'
            },
            
            # Суды общей юрисдикции Санкт-Петербурга
            {
                'name': 'Центральный районный суд Санкт-Петербурга',
                'court_type': 'general',
                'region': 'Санкт-Петербург',
                'address': 'ул. Садовая, д. 32-34, Санкт-Петербург, 191025'
            },
            {
                'name': 'Василеостровский районный суд Санкт-Петербурга',
                'court_type': 'general',
                'region': 'Санкт-Петербург',
                'address': 'ул. Железноводская, д. 64, Санкт-Петербург, 199106'
            },
            {
                'name': 'Санкт-Петербургский городской суд',
                'court_type': 'general',
                'region': 'Санкт-Петербург',
                'address': 'ул. Воскресенская наб., д. 16А, Санкт-Петербург, 191014'
            },
            
            # Региональные суды
            {
                'name': 'Арбитражный суд Свердловской области',
                'court_type': 'arbitration',
                'region': 'Свердловская область',
                'address': 'ул. Шарташская, д. 4, Екатеринбург, 620142'
            },
            {
                'name': 'Арбитражный суд Краснодарского края',
                'court_type': 'arbitration',
                'region': 'Краснодарский край',
                'address': 'ул. Рашпилевская, д. 179, Краснодар, 350020'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for court_data in courts_data:
            court, created = Court.objects.get_or_create(
                name=court_data['name'],
                defaults=court_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Создан суд: {court.name}')
                )
            else:
                # Обновляем существующий суд
                for key, value in court_data.items():
                    setattr(court, key, value)
                court.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'🔄 Обновлен суд: {court.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n📋 Загрузка завершена:\n'
                f'• Создано: {created_count} судов\n'
                f'• Обновлено: {updated_count} судов\n'
                f'• Всего в базе: {Court.objects.count()} судов'
            )
        )