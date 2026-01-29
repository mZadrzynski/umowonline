# 🚀 KOMPLETNY PORADNIK WDROŻENIA - MULTI-CALENDAR SYSTEM

## 📁 WSZYSTKIE PLIKI GOTOWE DO POBRANIA

Pobierz te pliki z GitHub:

### 1. **VIEWS.PY - NAPRAWIONY**
- Link: https://raw.githubusercontent.com/mZadrzynski/umowonline/master/REPAIR_VIEWS_FIXED.py
- **Co robić**: Zamień zawartość `myschedule/views.py` na zawartość tego pliku

### 2. **SZABLONY - GOTOWE**
Uż wbudowane w repo:
- ✅ `calendar_list.html` - lista kalendarzy
- ✅ `calendar_create.html` - tworzenie nowego
- ✅ `calendar_switcher.html` - komponent do integracji

### 3. **INSTRUKCJE - DO WYKONANIA**
Plik: `INSTRUKCJA_USUWANIE_KALENDARZY.md` zawiera kroki dla:
- Funkcja `calendar_delete()` - dodaj do views.py
- Template `calendar_confirm_delete.html` - stwórz
- Update `calendar_list.html` - dodaj przycisk delete

---

## ⚡ SZYBKIE KROKI (15 minut)

### KROK 1: Backup
```bash
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
```

### KROK 2: Pobierz i zamień views.py
```bash
cd ~/umowonline
git pull origin master

# Backup starego
cp myschedule/views.py myschedule/views.py.backup

# Skopiuj naprawiony
cp REPAIR_VIEWS_FIXED.py myschedule/views.py
```

### KROK 3: Dodaj funkcję delete (5 minut)

Otwórz `myschedule/views.py`, przejdź na **KONIEC** pliku i dodaj:

```python
@login_required
def calendar_delete(request, calendar_id):
    """
    Usuń kalendarz (oprócz głównego)
    """
    calendar = get_object_or_404(Calendar, id=calendar_id, user=request.user)
    
    # Nie pozwól usuwać pierwszy kalendarz
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

### KROK 4: Dodaj URL

W `myschedule/urls.py` dodaj tę linię:
```python
path('calendars/<int:calendar_id>/delete/', views.calendar_delete, name='calendar_delete'),
```

### KROK 5: Stwórz template potwierdzenia

Nowy plik: `umowonline/templates/myschedule/calendar_confirm_delete.html`

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

### KROK 6: Update `calendar_list.html`

W `calendar_list.html` znajdź sekcję z przyciskami (w pętli):

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

## 🔗 INTEGRACJA Z CATALOGIEM

### Aby dodać selektor kalendarzy w catalogu:

W szablonie `umowonline/templates/catalog/business_detail.html` (lub gdzie potrzebujesz):

```html
<!-- U góry strony, zaraz za header'em -->
{% include "myschedule/calendar_switcher.html" %}
```

To załaduje komponennt z automatycznym selectorem kalendarzy!

---

## ✅ CHECKLIST WDROŻENIA

- [ ] **Backup**
  ```bash
  python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
  ```

- [ ] **Pobierz zmiany**
  ```bash
  git pull origin master
  ```

- [ ] **Zamień views.py**
  ```bash
  cp REPAIR_VIEWS_FIXED.py myschedule/views.py
  ```

- [ ] **Dodaj funkcję `calendar_delete()` do views.py** (na koniec)

- [ ] **Dodaj URL do urls.py**
  ```python
  path('calendars/<int:calendar_id>/delete/', views.calendar_delete, name='calendar_delete'),
  ```

- [ ] **Stwórz `calendar_confirm_delete.html` template**

- [ ] **Update `calendar_list.html` - dodaj przycisk delete**

- [ ] **Testuj lokalnie**
  ```bash
  python manage.py runserver
  ```

- [ ] **Sprawdzaj funkcjonalność**:
  - [ ] `http://127.0.0.1:8000/myschedule/calendars/` - lista, create, switch
  - [ ] Przycisk delete na każdym (oprócz pierwszego)
  - [ ] Potwierdzenie usunięcia
  - [ ] `/myschedule/calendar_week/` - brak błędu
  - [ ] Dodawanie dostępności - działa
  - [ ] Usługi - niezależne dla każdego kalendarza

---

## 📊 STRUKTURA DANYCH - WYJAŚNIENIE

### Każdy kalendarz ma:
- ✅ **Własne dostępności** (`Availability`) - dny i godziny
- ✅ **Własne usługi** (`ServiceType`) - fryzura, masaż, etc.
- ✅ **Własne rezerwacje** (`Booking`) - wizyty przez publiczny link
- ✅ **Unikalny URL** (`CalendarAlias`) - `/marcin`, `/marcin2`, `/marcin3`
- ✅ **Unikalny share_token** - dla publicznego linku

### Gdy dodajesz dostępność:
1. Wybierasz kalendarz (przełącznik u góry)
2. Dodajesz dniA i godziny
3. Przypisuje się **tylko do wybranego kalendarza**
4. Inni użytkownicy rezerwują przez publiczny link
5. Rezerwacje przypisane są do kalendarza

---

## 🎯 INTEGRACJA Z INNYMI CZĘŚCI APP

### Aby dodać selektor wszędzie:

W każdym szablonie, gdzie chcesz aby użytkownik widział aktywny kalendarz:

```html
{% include "myschedule/calendar_switcher.html" %}
```

Component automatycznie wyświetli:
- 📌 Nazwę aktywnego kalendarza
- 📋 Dropdown z innymi (jeśli >1)
- ⚙️ Link do zarządzania

---

## 🐛 TROUBLESHOOTING

### Błąd: `calendar_delete is not defined`
- ✅ Upewnij się że dodałeś funkcję na **koniec** `views.py`
- ✅ Sprawdź czy indentacja jest poprawna

### Błąd: `No reverse match for 'calendar_delete'`
- ✅ Sprawdź czy URL jest w `urls.py`
- ✅ Uruchom `git pull` żeby mieć najnowsze

### Przycisk delete nie widać
- ✅ Sprawdź czy `calendar_list.html` ma `{% if forloop.counter > 1 %}`
- ✅ Refresh strony (Ctrl+Shift+R)

### Nie mogę usunąć pierwszego kalendarza
- ✅ To jest zamierzone! Główny kalendarz jest chroniony
- ✅ Możesz usuwać tylko dodatkowe (id > 1)

---

## 📞 WSPARCIE

Jeśli coś nie działa:
1. Sprawdź checklist powyżej
2. Sprawdź logs: `tail -f Django_logs.txt`
3. Sprawdź czy masz najnowsze pliki: `git status`

Powodzenia! 💪
