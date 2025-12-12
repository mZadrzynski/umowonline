from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Avg
from .models import BusinessProfile, Service, Review
from .forms import BusinessProfileForm, ReviewForm
from django.urls import reverse
from django.db.models import Avg
from datetime import date, timedelta

# ===== PUBLIC VIEWS =====

class BusinessListView(ListView):
    """Lista wszystkich firm w katalogu (publiczna)"""
    model = BusinessProfile
    template_name = 'catalog/business_list.html'
    context_object_name = 'businesses'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = BusinessProfile.objects.filter(is_active=True).prefetch_related('services', 'reviews')
        
        # Search
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(business_name__icontains=search) |
                Q(description__icontains=search) |
                Q(owner_name__icontains=search)
            )
        
        # Sorting
        sort = self.request.GET.get('sort', '-is_featured')
        queryset = queryset.order_by(sort, '-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['current_sort'] = self.request.GET.get('sort', '-is_featured')
        return context


class BusinessDetailView(DetailView):
    """Szczegóły profilu firmy (publiczny)"""
    model = BusinessProfile
    template_name = 'myschedule/public_calendar_with_business.html'  # ZMIENIONE
    context_object_name = 'business'
    slug_field = 'slug'
    
    def get_queryset(self):
        return BusinessProfile.objects.filter(is_active=True).prefetch_related('services', 'reviews')
    
    def get_context_data(self, **kwargs):
        from django.urls import reverse
        from datetime import date, timedelta
        from myschedule.views_public import calculate_free_time_slots
        
        context = super().get_context_data(**kwargs)
        business = self.get_object()
        
        # Dane biznesowe
        context['average_rating'] = business.reviews.aggregate(Avg('rating'))['rating__avg']
        
        # DEBUGOWANIE - sprawdzenie czy kalendarz jest przydzielony
        print(f"DEBUG: Business '{business.business_name}' - Calendar: {business.calendar}")
        
        # KALENDARZ (jeśli istnieje)
        if business.calendar:
            calendar = business.calendar
            
            today = date.today()
            week_offset = int(self.request.GET.get('week', 0))
            start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
            end_of_week = start_of_week + timedelta(days=6)
            week_days = [start_of_week + timedelta(days=i) for i in range(7)]

            availabilities = calendar.availabilities.filter(
                date__range=[start_of_week, end_of_week]
            ).order_by('date', 'start_time')

            # Użyj free_slots
            avail_by_day = {day: [] for day in week_days}
            for availability in availabilities:
                free_slots = calculate_free_time_slots(availability)
                avail_by_day[availability.date].append({
                    "availability": availability,
                    "free_slots": free_slots
                })

            context['week_days'] = week_days
            context['selected_week'] = start_of_week
            context['availabilities_by_day_items'] = [(d, avail_by_day[d]) for d in week_days]
            context['calendar_owner'] = calendar.user
            context['week_offset'] = week_offset
            context['services'] = calendar.servicetype_set.all()
        else:
            # Brak kalendarza - DODANE INFO DEBUGOWANIA
            print(f"WARNING: No calendar assigned to business '{business.business_name}'")
            context['week_days'] = []
            context['availabilities_by_day_items'] = []
            context['services'] = []
            context['calendar_owner'] = None
            context['week_offset'] = 0
            context['selected_week'] = None
            context['no_calendar_message'] = "Ta firma nie ma jeszcze przydzielonego kalendarza."
        
        return context


# ===== USER DASHBOARD =====

@login_required
def user_businesses(request):
    """Dashboard - moje profile biznesowe"""
    businesses = request.user.business_profiles.all()
    
    context = {
        'businesses': businesses,
    }
    return render(request, 'catalog/user_businesses.html', context)


# ===== CREATE / EDIT / DELETE =====

class BusinessCreateView(LoginRequiredMixin, CreateView):
    """Dodaj nowy profil biznesowy"""
    model = BusinessProfile
    form_class = BusinessProfileForm
    template_name = 'catalog/business_form.html'
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dodaj profil biznesowy'
        return context


class BusinessUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edytuj profil biznesowy"""
    model = BusinessProfile
    form_class = BusinessProfileForm
    template_name = 'catalog/business_form.html'
    
    def test_func(self):
        business = self.get_object()
        return business.owner == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edytuj profil biznesowy'
        return context


class BusinessDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Usuń profil biznesowy"""
    model = BusinessProfile
    template_name = 'catalog/business_confirm_delete.html'
    success_url = reverse_lazy('catalog:user_businesses')
    
    def test_func(self):
        business = self.get_object()
        return business.owner == self.request.user



# ===== REVIEWS =====

class ReviewCreateView(LoginRequiredMixin, CreateView):
    """Dodaj opinię"""
    model = Review
    form_class = ReviewForm
    template_name = 'catalog/review_form.html'
    
    def form_valid(self, form):
        profile_id = self.kwargs.get('profile_id')
        form.instance.profile_id = profile_id
        form.instance.author = self.request.user
        
        # Sprawdź czy użytkownik już ma opinię
        if Review.objects.filter(profile_id=profile_id, author=self.request.user).exists():
            form.add_error(None, "Już dodałeś opinię do tego profilu")
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('catalog:business_detail', kwargs={'slug': self.object.profile.slug})
