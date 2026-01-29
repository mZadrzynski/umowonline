# 🗑️ INSTRUKCJA: Usuwanie Kalendarzy + Integracja z Catalogiem

## CZĘŚĆ 1: DODAJ FUNKCJĘ DELETE W views.py

Dodaj to na **KONIEC** pliku `myschedule/views.py`:

```python
@login_required
def calendar_delete(request, calendar_id):
    """
    Usuną kalendarz (oprócz głównego)
    """
    calendar = get_object_or_404(Calendar, id=calendar_id, user=request.user)
    
    # Nie pozwól usuwać pierwszy kalendarz (id=1 dla każdego usera)
    if request.user.calendars.filter(id__lt=calendar.id).count() == 0:
        messages.error(request, "❌ Nie można usunąć głównego kalendarza!")
        return redirect('calendar_list')
    
    if request.method == 'POST':
        calendar_name = calendar.name
        
        # Jeśli ten kalendarz jest aktywny, przełącz na inny
        if request.session.get('active_calendar_id') == calendar.id:
            new_active = request.user.calendars.exclude(id=calendar.id).first()
            if new_active:
                request.session['active_calendar_id'] = new_active.id
            else:
                request.session.pop('active_calendar_id', None)
        
        # Usuń alias
        calendar.alias_set.all().delete()
        
        # Usuń kalendarz (cascade usunie dostępności, usługi, rezerwacje)
        calendar.delete()
        
        messages.success(request, f"✅ Kalendarz '{calendar_name}' został usunięty!")
        return redirect('calendar_list')
    
    # Sprawdź czy można usunąć
    can_delete = request.user.calendars.filter(id__lt=calendar.id).count() > 0
    
    return render(request, 'myschedule/calendar_confirm_delete.html', {
        'calendar': calendar,
        'can_delete': can_delete
    })
```

## CZĘŚĆ 2: DODAJ URL W urls.py

W `myschedule/urls.py` dodaj ten wiersz:

```python
path('calendars/<int:calendar_id>/delete/', views.calendar_delete, name='calendar_delete'),
```

CalY blok powinien wyglądać tak:

```python
urlpatterns = [
    # Calendar management
    path('calendars/', views.calendar_list, name='calendar_list'),
    path('calendars/create/', views.calendar_create, name='calendar_create'),
    path('calendars/<int:calendar_id>/set-active/', views.calendar_set_active, name='calendar_set_active'),
    path('calendars/<int:calendar_id>/delete/', views.calendar_delete, name='calendar_delete'),  # ← NOWY
    # ... reszta URLs
```

## CZĘŚĆ 3: UTWÓRZ TEMPLATE POTWIERDZENIA

Stwórz plik: `umowonline/templates/myschedule/calendar_confirm_delete.html`

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Usuń kalendarz{% endblock %}

{% block content %}
<div class="container mt-5">
    <div class="row">
        <div class="col-md-6 mx-auto">
            <div class="card border-danger shadow-sm">
                <div class="card-body text-center p-5">
                    <h2 class="mb-4 text-danger"><i class="fas fa-exclamation-triangle"></i> Potwierdzenie usunięcia</h2>
                    
                    {% if can_delete %}
                        <p class="lead mb-4">Czy na pewno chcesz usunąć kalendarz?</p>
                        <p class="text-muted"><strong>{{ calendar.name }}</strong></p>
                        
                        <div class="alert alert-warning" role="alert">
                            <i class="fas fa-exclamation-circle"></i> To usunie wszystkie dostępności, usługi i rezerwacje przypisane do tego kalendarza!
                        </div>
                        
                        <form method="post">
                            {% csrf_token %}
                            <div class="d-grid gap-2 d-sm-flex justify-content-center">
                                <button type="submit" class="btn btn-danger btn-lg">
                                    <i class="fas fa-trash"></i> Usuń na pewno
                                </button>
                                <a href="{% url 'calendar_list' %}" class="btn btn-secondary btn-lg">
                                    <i class="fas fa-arrow-left"></i> Anuluj
                                </a>
                            </div>
                        </form>
                    {% else %}
                        <div class="alert alert-danger" role="alert">
                            <i class="fas fa-lock"></i> <strong>Nie można usunąć!</strong>
                        </div>
                        <p class="text-muted mb-4">Główny kalendarz nie może być usunięty.</p>
                        <a href="{% url 'calendar_list' %}" class="btn btn-secondary btn-lg">
                            <i class="fas fa-arrow-left"></i> Wróć
                        </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## CZĘŚĆ 4: ZAKTUALIZUJ calendar_list.html

W `calendar_list.html` dodaj przycisk delete w pętli:

Znajdź sekcję z przyciskami:

```html
<div class="d-grid gap-2 d-sm-flex">
    <form method="post" action="{% url 'calendar_set_active' calendar.id %}" style="flex: 1;">
        {% csrf_token %}
        <button type="submit" class="btn btn-primary w-100 btn-sm">
            <i class="fas fa-check-circle"></i> Przełącz
        </button>
    </form>
    <a href="{% url 'my_calendar' %}?calendar={{ calendar.id }}" class="btn btn-info btn-sm" style="flex: 1;">
        <i class="fas fa-calendar-alt"></i> Otwórz
    </a>
</div>
```

Zastąp na:

```html
<div class="d-grid gap-2 d-sm-flex">
    <form method="post" action="{% url 'calendar_set_active' calendar.id %}" style="flex: 1;">
        {% csrf_token %}
        <button type="submit" class="btn btn-primary w-100 btn-sm">
            <i class="fas fa-check-circle"></i> Przełącz
        </button>
    </form>
    <a href="{% url 'my_calendar' %}?calendar={{ calendar.id }}" class="btn btn-info btn-sm" style="flex: 1;">
        <i class="fas fa-calendar-alt"></i> Otwórz
    </a>
    {% if forloop.counter > 1 %}
        <a href="{% url 'calendar_delete' calendar.id %}" class="btn btn-danger btn-sm">
            <i class="fas fa-trash"></i> Usuń
        </a>
    {% endif %}
</div>
```

---

# 📱 INTEGRACJA Z CATALOGIEM

## Czego potrzebujesz?

1. **Selektor kalendarzy u góry catalogu** - przełączanie bez opuszczania strony
2. **Nazwa aktywnego kalendarza** - aby wiedzieć dla którego dodajesz
3. **Dostępności/Usługi oddzielne** - każdy kalendarz ma swoje

## Oprócz tego:

### 1. Wyznacz gdzie jest catalog views

```bash
find . -name "views.py" -path "*/catalog/*" | head -1
```

### 2. Pokażemy edytować template

Gdzie jest szablon katalogów? 

```bash
find umowonline/templates -name "*catalog*" -o -name "*business*" | head -5
```

### 3. Dodamy selektor na stronie

```html
<!-- U góry strony -->
<div class="card mb-4">
    <div class="card-body">
        <label>Wybrany kalendarz:</label>
        <form method="post" action="{% url 'calendar_set_active' %}">
            {% csrf_token %}
            <select name="calendar_id" onchange="this.form.submit()" class="form-select">
                {% for cal in user_calendars %}
                    <option value="{{ cal.id }}" {% if cal == current_calendar %}selected{% endif %}>
                        {{ cal.name }}
                    </option>
                {% endfor %}
            </select>
        </form>
    </div>
</div>
```

---

## ✅ Podsumowanie

- ✅ Funkcja `calendar_delete()` - usuwa z zabezpieczeniami
- ✅ Potwierdzenie usunięcia - bezpieczny flow
- ✅ Każdy kalendarz niezależny - własne dostępności/usługi/rezerwacje
- ✅ Główny kalendarz chroniony - nie można usunąć

## 🔧 Następne kroki

Pokaż mi strukturę catalogu, a dodam tam integrację z selectorem kalendarzy!
