from django.shortcuts import render

# Create your views here.
# catalog/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponseForbidden
from django.db.models import Q, Avg

from .models import BusinessProfile, Service, Review
from .forms import BusinessProfileForm, ServiceForm, ReviewForm


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
    template_name = 'catalog/business_detail.html'
    context_object_name = 'business'
    slug_field = 'slug'
    
    def get_queryset(self):
        return BusinessProfile.objects.filter(is_active=True).prefetch_related('services', 'reviews')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        business = self.get_object()
        context['average_rating'] = business.reviews.aggregate(Avg('rating'))['rating__avg']
        context['calendar_url'] = business.calendar.get_absolute_url() if business.calendar else None
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


# ===== SERVICES =====

class ServiceCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Dodaj usługę do profilu"""
    model = Service
    form_class = ServiceForm
    template_name = 'catalog/service_form.html'
    
    def test_func(self):
        profile_id = self.kwargs.get('profile_id')
        profile = get_object_or_404(BusinessProfile, id=profile_id)
        return profile.owner == self.request.user
    
    def form_valid(self, form):
        profile_id = self.kwargs.get('profile_id')
        form.instance.profile_id = profile_id
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('catalog:business_edit', kwargs={'pk': self.kwargs['profile_id']})


class ServiceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edytuj usługę"""
    model = Service
    form_class = ServiceForm
    template_name = 'catalog/service_form.html'
    
    def test_func(self):
        service = self.get_object()
        return service.profile.owner == self.request.user
    
    def get_success_url(self):
        return reverse_lazy('catalog:business_edit', kwargs={'pk': self.object.profile.id})


class ServiceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Usuń usługę"""
    model = Service
    template_name = 'catalog/service_confirm_delete.html'
    
    def test_func(self):
        service = self.get_object()
        return service.profile.owner == self.request.user
    
    def get_success_url(self):
        return reverse_lazy('catalog:business_edit', kwargs={'pk': self.object.profile.id})


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
