# umowonline/tests/test_booking_flow.py

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date, time

from myschedule.models import Availability, ServiceType, Booking
from account.models import Subscription

User = get_user_model()

class BookingFlowTest(TestCase):
    def setUp(self):
        """
        Przygotuj dane testowe:
        - Tworzenie użytkowników (sygnały automatycznie tworzą subskrypcję i kalendarz)
        - Ustawienie subskrypcji jako aktywnej
        - Pobranie istniejącego kalendarza providera
        - Utworzenie ServiceType i Availability
        """
        # Utwórz provider i klienta
        self.provider = User.objects.create_user(
            username='provider',
            email='provider@test.com',
            password='testpass123'
        )
        self.client_user = User.objects.create_user(
            username='client',
            email='client@test.com',
            password='testpass123'
        )

        # Ustaw istniejące subskrypcje jako aktywne
        provider_sub = self.provider.subscription
        provider_sub.end_date = timezone.now() + timedelta(days=30)
        provider_sub.status = 'active'
        provider_sub.save()

        client_sub = self.client_user.subscription
        client_sub.end_date = timezone.now() + timedelta(days=30)
        client_sub.status = 'active'
        client_sub.save()

        # Pobierz istniejący kalendarz providera
        self.calendar = self.provider.calendar

        # Stwórz typ usługi
        self.service_type = ServiceType.objects.create(
            calendar=self.calendar,
            name='Test Service',
            duration_minutes=60
        )

        # Stwórz dostępność jutro od 10:00 do 18:00
        tomorrow = date.today() + timedelta(days=1)
        self.availability = Availability.objects.create(
            calendar=self.calendar,
            date=tomorrow,
            start_time=time(10, 0),
            end_time=time(18, 0)
        )

        # Klient HTTP
        self.client = Client()

    def test_full_booking_flow(self):
        """Test pełnego procesu rezerwacji: klient → provider"""
        # 1. Klient loguje się
        self.assertTrue(self.client.login(
            username='client@test.com', password='testpass123'
        ))

        # 2. Klient widzi publiczny kalendarz
        public_url = reverse('public_calendar_week', args=[self.calendar.share_token])
        response = self.client.get(public_url)
        self.assertEqual(response.status_code, 200)
        # Publiczny widok pokazuje przycisk rezerwacji, nie nazwę usługi

        # 3. Klient rezerwuje wizytę
        booking_url = reverse('book_availability', args=[self.availability.id])
        response = self.client.post(booking_url, {
            'service_type': self.service_type.id,
            'start_time': '10:00',
            'client_phone': '123456789',
            'client_note': 'Test booking'
        })
        self.assertEqual(response.status_code, 302)

        # 4. Sprawdź czy booking został utworzony
        booking = Booking.objects.get(
            availability=self.availability,
            user=self.client_user
        )
        self.assertEqual(booking.service_type, self.service_type)
        self.assertEqual(booking.status, 'active')

        # 5. Provider widzi booking na stronie „Moje rezerwacje”
        self.client.login(username='provider@test.com', password='testpass123')
        bookings_url = reverse('my_bookings')
        response = self.client.get(bookings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Service')

    def test_booking_cancellation(self):
        """Test anulowania rezerwacji przez klienta"""
        # Utwórz booking ręcznie
        booking = Booking.objects.create(
            availability=self.availability,
            user=self.client_user,
            service_type=self.service_type,
            start_datetime=timezone.now().replace(
                hour=10, minute=0, second=0, microsecond=0
            ) + timedelta(days=1),
            status='active'
        )

        # Klient anuluje wizytę
        self.client.login(username='client@test.com', password='testpass123')
        cancel_url = reverse('cancel_booking', args=[booking.id])
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

    def test_subscription_required(self):
        """Test czy subskrypcja premium jest wymagana dla provider"""
        # Ustaw subskrypcję jako wygasłą
        sub = self.provider.subscription
        sub.status = 'expired'
        sub.end_date = timezone.now() - timedelta(days=1)
        sub.save()

        # Próba dostępu do kalendarza tygodniowego
        self.client.login(username='provider@test.com', password='testpass123')
        response = self.client.get(reverse('my_calendar_week'))
        # Powinno przekierować lub zawierać informację o wygaśnięciu
        content = response.content.decode()
        self.assertTrue(
            response.status_code in (302, 200) and
            ('wygasła' in content or 'subscription_expired' in content)
        )

class SubscriptionTest(TestCase):
    def setUp(self):
        # Utwórz nowego usera (sygnał tworzy subskrypcję)
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_subscription_creation(self):
        """Test tworzenia subskrypcji przez sygnał"""
        sub = self.user.subscription
        # Ustaw datę końca na przyszłość
        sub.end_date = timezone.now() + timedelta(days=30)
        sub.save()
        self.assertTrue(sub.is_active())

    def test_subscription_extension(self):
        """Test przedłużania subskrypcji"""
        sub = self.user.subscription
        sub.end_date = timezone.now() + timedelta(days=5)
        sub.save()
        old_end = sub.end_date
        sub.extend_subscription(30)
        self.assertEqual(sub.end_date, old_end + timedelta(days=30))
